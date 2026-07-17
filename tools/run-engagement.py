#!/usr/bin/env python3
"""Canonical public command for Decision 0005 engagement records.

This command records and validates research state. It never drives a target.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import runpy
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from engagement_records import (
    RecordError,
    build_reference_index,
    build_registry,
    canonical_json_bytes,
    detect_secret_classes,
    legacy_finding_inventory,
    load_json,
    resolve_schema_name,
    scan_file_secret_classes,
    sha256_bytes,
    sha256_file,
    validate_fixture_suite,
    validate_record,
    validate_reference_fixture_suite,
    validate_schema_documents,
    validate_record_with_references,
    write_canonical_json,
)
from engagement_state import (
    append_attempt,
    append_event,
    _append_kernel_event,
    _append_kernel_event_idempotent,
    _governed_root,
    _open_parent_fd,
    atomic_write,
    append_ledger_record,
    assert_resume_current,
    base_event,
    compute_record_hash,
    compute_review_input_hash,
    engagement_lock,
    initialize_engagement,
    materialize_ledger_record,
    persist_scope_snapshot,
    read_governed_file,
    read_ledger,
    reduce_engagement,
    require_approved_authority,
    require_repair_authority_from_intact_prefix,
    require_scope_zone2_authorized,
    register_artifact,
    _register_legacy_artifact,
    repair_ledger_tail,
    write_snapshot,
    _scope_metadata,
)
from engagement_views import assert_views_current, render_views, write_views
from environment_preflight import collect_preflight as collect_agent_preflight, _collect_legacy_preflight, review_preflight
from finding_review import claim_tuple_hash, render_claim_proof
from memory_disposition import _validate_promotable_abstraction, close_engagement, record_memory_disposition
from reporting import accept_report, generate_report, record_submission
from research_telemetry import export_telemetry, score_telemetry
from decision6_capabilities import artifact_variant, classify_command, classify_event, load_capability_matrix, require_actor


def emit(value: object) -> None:
    sys.stdout.buffer.write(canonical_json_bytes(value))


def command_validate(args: argparse.Namespace) -> int:
    if args.schema_documents:
        problems = validate_schema_documents()
        result = {"valid": not problems, "problems": problems}
    elif args.fixture_suite:
        result = validate_fixture_suite(Path(args.fixture_suite) if isinstance(args.fixture_suite, str) else None)
        result["valid"] = not result["failures"]
    elif args.legacy_root:
        inventory = legacy_finding_inventory(args.legacy_root)
        if args.output:
            write_canonical_json(args.output, inventory)
        result = inventory
        result["valid"] = inventory["counts"]["parse_error"] == 0
    elif args.file:
        record = load_json(args.file)
        schema_name = resolve_schema_name(record, args.schema)
        if args.engagement:
            errors = validate_record_with_references(record, schema_name, args.engagement)
        elif args.schema_only or schema_name == "finding-v2-legacy":
            errors = validate_record(record, schema_name)
        else:
            raise RecordError("engagement_context_required", "new records require --engagement for reference validation; use --schema-only only for isolated fixture work")
        result = {"valid": not errors, "schema": schema_name, "file": str(args.file), "errors": errors}
    else:
        raise RecordError("validation_input_required", "choose --schema-documents, --fixture-suite, --legacy-root, or --file")
    emit(result)
    return 0 if result.get("valid") else 1


def command_runtime_identity(args: argparse.Namespace) -> int:
    actor_id, session_id = _local_identity(args.role); emit({"actor_role": args.role, "actor_id": actor_id, "session_id": session_id}); return 0


def command_init(args: argparse.Namespace) -> int:
    metadata=_scope_metadata(args.engagement.absolute()/"scope.md");operator_id=re.sub(r"[^A-Za-z0-9._:-]+","-",metadata["operator"]).strip("-") or "operator";_enforce_mutation(classify_command("init"),args.engagement,"operator",operator_id,f"initialize-engagement:{args.recorded_at}")
    snapshot = initialize_engagement(args.engagement, args.recorded_at)
    emit({"ok": True, "engagement_id": snapshot["engagement_id"], "scope_hash": snapshot["scope_hash"], "event_count": snapshot["event_count"]})
    return 0


def _require_operator_console(engagement: Path, operator_id: str, operation: str) -> None:
    engagement=engagement.absolute();events=read_ledger(engagement,"event")
    if events:
        attestation=next(event for event in reversed(events) if event["event_type"]=="scope.attested");signed=attestation["payload"]["operator_id"];scope_hash=attestation["payload"]["scope_hash"];scope_bytes=read_governed_file(engagement/attestation["payload"]["scope_snapshot_path"]);ledger_hash=events[-1]["record_hash"]
    else:
        metadata=_scope_metadata(engagement/"scope.md");signed=re.sub(r"[^A-Za-z0-9._:-]+","-",metadata["operator"]).strip("-") or "operator";scope_hash=metadata["scope_hash"];scope_bytes=read_governed_file(engagement/"scope.md");ledger_hash=None
    if sha256_bytes(scope_bytes)!=scope_hash:raise RecordError("operator_scope_snapshot_invalid",scope_hash)
    if operator_id!=signed:raise RecordError("operator_authority_invalid","operator id does not match the active attested scope")
    signer_match=re.search(rb"Operator allowed signers SHA256:\s*(sha256:[0-9a-f]{64})",scope_bytes)
    challenge={"schema_version":1,"namespace":"llm-redteam-harness-operator-v1","engagement_id":engagement.name,"scope_hash":scope_hash,"ledger_hash":ledger_hash,"operation":operation,"operator_id":operator_id};challenge_bytes=canonical_json_bytes(challenge);challenge_digest=sha256_bytes(challenge_bytes);sys.stderr.write("Operator signature challenge:\n"+challenge_bytes.decode());sys.stderr.flush()
    signature_name=os.environ.get("HARNESS_OPERATOR_SIGNATURE_FILE");signers_name=os.environ.get("HARNESS_OPERATOR_ALLOWED_SIGNERS_FILE")
    if signer_match is None or not signature_name or not signers_name:raise RecordError("operator_signature_required",challenge_digest)
    try:signature_bytes,_=_read_regular_file_once(Path(signature_name));signers_bytes,_=_read_regular_file_once(Path(signers_name))
    except (OSError,RecordError) as exc:raise RecordError("operator_signature_invalid",challenge_digest,[str(exc)]) from exc
    if sha256_bytes(signers_bytes)!=signer_match.group(1).decode():raise RecordError("operator_signature_invalid",challenge_digest)
    with tempfile.TemporaryDirectory(prefix="operator-signature-") as temporary:
        temporary_root=Path(temporary);signature_copy=temporary_root/"operator.sig";signers_copy=temporary_root/"allowed_signers";signature_copy.write_bytes(signature_bytes);signers_copy.write_bytes(signers_bytes);result=subprocess.run(["/usr/bin/ssh-keygen","-Y","verify","-f",str(signers_copy),"-I",operator_id,"-n","llm-redteam-harness-operator-v1","-s",str(signature_copy)],input=challenge_bytes,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={"PATH":"/usr/bin:/bin","LC_ALL":"C"},check=False)
    if result.returncode!=0:raise RecordError("operator_signature_invalid",challenge_digest)


def _require_session(provenance: dict[str, object], operation: str) -> str:
    if not isinstance(provenance.get("session_id"), str) or not provenance["session_id"]:
        raise RecordError("session_provenance_required", operation)
    return str(provenance["session_id"])


def _local_identity(role: str) -> tuple[str, str]:
    uid = os.getuid(); session = os.getsid(0)
    return f"local-uid-{uid}:{role}", f"session-posix-{uid}-{session}"


def _require_local_provenance(role: str, actor_id: str, session_id: str) -> None:
    expected_actor, expected_session = _local_identity("broker")
    if role != "broker" or actor_id != expected_actor or session_id != expected_session:
        raise RecordError("runtime_provenance_not_principal_bound", role)


def _require_local_session(session_id: str) -> None:
    if session_id != _local_identity("operator")[1]:
        raise RecordError("runtime_session_not_process_bound", "operator")


ARTIFACT_PERMIT_FIELDS = {"schema_version", "classification_id", "classification_event_ref", "artifact_id", "engagement_id", "relative_path", "advisory_zone", "operation_class", "metadata_digest", "scope_hash", "environment_ref", "classified_at", "expires_at", "source_digest", "source_size", "action_digest", "file_absent_at_classification", "decision"}


def _zone2_plan(metadata: dict[str, object], *, planned_sha256: str, planned_size: int, relative_path: str, scope_hash: str, environment_ref: str, cleanup_obligation_ref: str) -> dict[str, object]:
    return {"artifact_id": metadata.get("artifact_id"), "metadata_digest": sha256_bytes(canonical_json_bytes(metadata)), "planned_sha256": planned_sha256, "planned_size": planned_size, "relative_path": relative_path, "scope_hash": scope_hash, "environment_ref": environment_ref, "cleanup_obligation_ref": cleanup_obligation_ref, "cleanup_obligation_id": metadata.get("cleanup_obligation_id")}


def _authority_action(action_kind: str, **fields: object) -> dict[str, object]:
    return {"action_kind": action_kind, **fields}


def _read_regular_file_once(path: Path) -> tuple[bytes, os.stat_result]:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)); chunks: list[bytes] = []
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode): raise RecordError("bound_input_not_regular", str(path))
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk: break
            chunks.append(chunk)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns): raise RecordError("bound_input_changed_during_read", str(path))
        return b"".join(chunks), after
    finally: os.close(fd)


def _open_bound_directory(path: Path) -> tuple[int, Path, dict[str, int]]:
    absolute = Path(os.path.abspath(path)); current = os.open("/", os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        for component in absolute.parts[1:]:
            following = os.open(component, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0), dir_fd=current); os.close(current); current = following
        result = os.fstat(current); return current, absolute, {"device": result.st_dev, "inode": result.st_ino}
    except Exception:
        os.close(current); raise


def _require_migration_tree_safety(root_fd: int, destination_fd: int, proposal_bytes: bytes, *, resume: bool = False) -> None:
    try: engagement_id = json.loads(proposal_bytes)["engagement_id"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc: raise RecordError("migration_proposal_identity_invalid", "engagement_id") from exc
    if not isinstance(engagement_id, str) or engagement_id in {".", ".."} or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]*", engagement_id): raise RecordError("migration_proposal_identity_invalid", str(engagement_id))
    if not resume and set(os.listdir(destination_fd)) != {"scope.md"}: raise RecordError("migration_destination_not_pristine", "destination must contain only a regular signed scope.md")
    scope_fd = os.open("scope.md", os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=destination_fd)
    try:
        if not stat.S_ISREG(os.fstat(scope_fd).st_mode): raise RecordError("migration_destination_scope_invalid", "scope.md")
    finally: os.close(scope_fd)
    base_fd = root_fd
    try:
        try: candidate = os.open("engagements", os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0), dir_fd=root_fd)
        except FileNotFoundError: candidate = -1
        if candidate >= 0: base_fd = candidate
        source_fd = os.open(engagement_id, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0), dir_fd=base_fd)
        try:
            for current, directories, files, current_fd in os.fwalk(f"/dev/fd/{source_fd}", topdown=True, follow_symlinks=False):
                for name in directories + files:
                    if stat.S_ISLNK(os.stat(name, dir_fd=current_fd, follow_symlinks=False).st_mode): raise RecordError("migration_source_symlink_rejected", str(Path(current)/name))
        finally: os.close(source_fd)
    finally:
        if base_fd != root_fd: os.close(base_fd)


def _require_decision6_kernel(engagement: Path) -> None:
    events=read_ledger(engagement.absolute(),"event"); attestation=next((event for event in reversed(events) if event["event_type"]=="scope.attested"),None)
    if attestation is None or attestation.get("payload",{}).get("record_kernel")!="decision-0006-v1": raise RecordError("decision6_kernel_not_selected","signed scope must select decision-0006-v1 for autonomous broker or async-authority commands")


def _require_async_authority(args: argparse.Namespace, action: dict[str, object], applied_at: str) -> None:
    _require_decision6_kernel(args.engagement)
    _require_local_provenance("broker", args.executor_id, args.session_id)
    if abs((datetime.fromisoformat(applied_at.replace("Z", "+00:00")) - datetime.now(timezone.utc)).total_seconds()) > 60:
        raise RecordError("authority_application_time_not_current", str(action["action_kind"]))
    request_id = getattr(args, "authority_request_id", None)
    if not request_id:
        raise RecordError("approved_authority_request_required", action["action_kind"])
    lane_id = action.get("lane_id")
    if not isinstance(lane_id, str) or not lane_id:
        raise RecordError("authority_action_lane_required", str(action["action_kind"]))
    require_approved_authority(args.engagement.absolute(), request_id, str(action["action_kind"]), sha256_bytes(canonical_json_bytes(action)), lane_id, applied_at)


def _enforce_mutation(capability: dict[str, object], engagement: Path, actor_role: str, actor_id: str, operation: str) -> None:
    if actor_role == "broker": _require_decision6_kernel(engagement)
    if actor_role == "operator" and capability["tier"] == "notebook":
        _require_operator_console(engagement, actor_id, operation)
    require_actor(capability, actor_role)
    if capability["tier"] in {"authority", "real_world"}:
        if actor_role != "operator":
            raise RecordError("operator_authority_invalid", operation)
        _require_operator_console(engagement, actor_id, operation)


def command_append_event(args: argparse.Namespace) -> int:
    proposal = load_json(args.file)
    capability = classify_event(proposal.get("event_type", ""), proposal.get("payload", {}))
    actor = proposal.get("actor", {})
    if capability["tier"] != "notebook":
        raise RecordError("canonical_authority_command_required", proposal.get("event_type", "unknown"))
    if proposal.get("event_type") in {"environment.preflight_recorded", "artifact.classified", "scope.amendment_proposed", "authority.requested"}:
        raise RecordError("canonical_notebook_command_required", proposal.get("event_type", "unknown"))
    _enforce_mutation(capability, args.engagement, actor.get("role", ""), actor.get("id", ""), f"append-event:{proposal.get('event_type','event')}:{proposal.get('event_id','unknown')}:{sha256_bytes(canonical_json_bytes(proposal))}")
    if proposal.get("operation_class") != capability["tier"]:
        raise RecordError("event_operation_class_mismatch", proposal.get("event_type", "unknown"))
    if capability["tier"] == "notebook":
        session_id = _require_session(proposal.get("provenance", {}), proposal.get("event_type", "event")); _require_local_provenance(str(actor.get("role", "")), str(actor.get("id", "")), session_id)
    record = append_event(args.engagement.absolute(), proposal)
    emit({"ok": True, "event_id": record["event_id"], "sequence": record["sequence"], "record_hash": record["record_hash"]})
    return 0


def command_classify_artifact(args: argparse.Namespace) -> int:
    metadata = load_json(args.metadata)
    metadata_secret_classes=detect_secret_classes(canonical_json_bytes(metadata))
    if metadata_secret_classes: raise RecordError("secret_shaped_artifact_metadata","artifact metadata blocked before classification",[{"class":value} for value in metadata_secret_classes])
    _require_local_provenance(args.actor_role, args.actor_id, args.session_id)
    variant = artifact_variant(metadata)
    caller = {"role": args.actor_role, "id": args.actor_id}
    if variant == "clear_local":
        if args.source is None:
            raise RecordError("artifact_source_required", metadata.get("artifact_id", "unknown"))
        source = args.source.resolve(strict=True)
        if args.source.is_symlink() or not source.is_file():
            raise RecordError("artifact_source_invalid", str(args.source))
        if scan_file_secret_classes(source):
            raise RecordError("secret_shaped_artifact_content", "planned artifact source contains a forbidden secret shape")
        source_executable = bool(source.stat().st_mode & 0o111)
        if source_executable != bool(metadata.get("contains_executable_capability")):
            raise RecordError("artifact_source_executable_mismatch", metadata.get("artifact_id", "unknown"))
        source_digest, source_size = sha256_file(source), source.stat().st_size
    else:
        if args.source is not None or not args.planned_sha256 or args.planned_size is None:
            raise RecordError("zone2_planned_bytes_contract_required", metadata.get("artifact_id", "unknown"))
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", args.planned_sha256) or args.planned_size < 0:
            raise RecordError("zone2_planned_bytes_contract_invalid", metadata.get("artifact_id", "unknown"))
        source_digest, source_size = args.planned_sha256, args.planned_size
    if metadata.get("advisory_zone") not in ({"clear_local"} if variant == "clear_local" else {"review_required", "unknown"}):
        raise RecordError("artifact_zone_underclassified", metadata.get("artifact_id", "unknown"))
    capability = classify_command("classify-artifact", variant=variant)
    if caller["role"]=="broker": _require_decision6_kernel(args.engagement)
    actor = metadata.get("producer", {})
    if capability["tier"] == "notebook" and (caller != actor or args.session_id != metadata.get("producer_session_id")):
        raise RecordError("artifact_classifier_identity_mismatch", metadata.get("artifact_id", "unknown"))
    require_actor(capability, caller["role"])
    if metadata.get("operation_class") != capability["tier"] or not metadata.get("producer_session_id"):
        raise RecordError("artifact_provenance_invalid", metadata.get("artifact_id", "unknown"))
    relative = args.relative_path.as_posix()
    if args.relative_path.is_absolute() or ".." in args.relative_path.parts or not relative.startswith("evidence/"):
        raise RecordError("artifact_path_not_contained", relative)
    engagement = args.engagement.absolute(); destination = engagement / relative; governed_root, governed_parts = _governed_root(destination)
    if governed_root != engagement or tuple(governed_parts) != tuple(args.relative_path.parts): raise RecordError("artifact_path_not_contained", relative)
    try:
        parent_fd, leaf = _open_parent_fd(governed_root, governed_parts, create=False)
        try:
            try: os.stat(leaf, dir_fd=parent_fd, follow_symlinks=False)
            except FileNotFoundError: pass
            else: raise RecordError("artifact_bytes_precede_classification", relative)
        finally: os.close(parent_fd)
    except FileNotFoundError: raise RecordError("artifact_path_not_contained", relative)
    state = reduce_engagement(args.engagement.absolute())
    if metadata.get("engagement_id") != state["engagement_id"] or metadata.get("environment_ref") != state["active_environment_ref"]:
        raise RecordError("artifact_environment_not_active", metadata.get("artifact_id", "unknown"))
    action_digest = None
    if capability["tier"] == "real_world":
        if metadata.get("advisory_zone") != "review_required": raise RecordError("zone2_advisory_zone_invalid", metadata.get("artifact_id", "unknown"))
        plan = _zone2_plan(metadata, planned_sha256=source_digest, planned_size=source_size, relative_path=relative, scope_hash=state["scope_hash"], environment_ref=state["active_environment_ref"], cleanup_obligation_ref=metadata.get("cleanup_obligation_ref") or "")
        action_digest = sha256_bytes(canonical_json_bytes(plan))
        confirmation = next((event for event in read_ledger(args.engagement.absolute(), "event") if event["event_id"] == metadata.get("escalation_confirmation_event_ref")), None)
        if confirmation is None or confirmation["event_type"] != "escalation.confirmed" or confirmation["payload"].get("entity_id") != metadata.get("artifact_id") or confirmation["payload"].get("environment_ref") != state["active_environment_ref"] or confirmation["payload"].get("action_digest") != action_digest:
            raise RecordError("artifact_creation_requires_fresh_confirmation", metadata.get("artifact_id", "unknown"))
        expiry = datetime.fromisoformat(confirmation["payload"]["expires_at"].replace("Z", "+00:00"))
        if datetime.fromisoformat(args.recorded_at.replace("Z", "+00:00")) > expiry:
            raise RecordError("artifact_confirmation_expired", metadata.get("artifact_id", "unknown"))
        decision = "allow_confirmed_creation"; expires_at = confirmation["payload"]["expires_at"]
    else:
        decision = "allow_local_creation"; expires_at = None
    permit_body = {"schema_version": 1, "classification_id": f"classification-{metadata['artifact_id']}", "artifact_id": metadata["artifact_id"], "engagement_id": state["engagement_id"], "relative_path": relative, "advisory_zone": metadata["advisory_zone"], "operation_class": capability["tier"], "metadata_digest": sha256_bytes(canonical_json_bytes(metadata)), "scope_hash": state["scope_hash"], "environment_ref": state["active_environment_ref"], "classified_at": args.recorded_at, "expires_at": expires_at, "source_digest": source_digest, "source_size": source_size, "action_digest": action_digest, "file_absent_at_classification": True, "decision": decision}
    classification_digest = sha256_bytes(canonical_json_bytes(permit_body)); event_id = f"event-{permit_body['classification_id']}"
    existing = next((event for event in read_ledger(args.engagement.absolute(), "event") if event["event_id"] == event_id), None)
    if existing is None:
        classified_event = base_event(event_id=event_id, engagement_id=state["engagement_id"], recorded_at=args.recorded_at, actor_role=caller["role"], actor_id=caller["id"], event_type="artifact.classified", rationale="Bind planned artifact bytes before destination creation.", payload={"classification_id": permit_body["classification_id"], "classification_digest": classification_digest, "artifact_id": metadata["artifact_id"], "source_digest": permit_body["source_digest"], "source_size": permit_body["source_size"], **({"action_digest": action_digest} if action_digest else {}), "advisory_zone": metadata["advisory_zone"], "scope_hash": state["scope_hash"], "environment_ref": state["active_environment_ref"], "classified_at": args.recorded_at, "expires_at": expires_at}, session_id=args.session_id, operation_class=capability["tier"], model=args.model, provider=args.provider, tool_versions=["decision6-artifact-classifier-v1", *args.tool_version])
        existing = _append_kernel_event(args.engagement.absolute(), classified_event)
    elif existing.get("payload", {}).get("classification_digest") != classification_digest:
        raise RecordError("artifact_classification_event_conflict", event_id)
    permit = {**permit_body, "classification_event_ref": event_id}
    if args.output:
        write_canonical_json(args.output, permit)
    emit(permit)
    return 0


def command_propose_scope(args: argparse.Namespace) -> int:
    _require_decision6_kernel(args.engagement)
    _require_local_provenance("broker", args.actor_id, args.session_id); data = args.draft.read_bytes()
    if not data or detect_secret_classes(data): raise RecordError("scope_draft_invalid", "empty or secret-shaped scope draft")
    engagement = args.engagement.absolute(); state = reduce_engagement(engagement); digest = sha256_bytes(data); relative = f"scope-drafts/{digest.removeprefix('sha256:')}.md"; destination = engagement / relative
    existing = next((event for event in read_ledger(engagement, "event") if event["event_type"] == "scope.amendment_proposed" and event["payload"].get("draft_digest") == digest), None)
    if existing is not None: emit({"valid": True, "draft_path": existing["payload"]["draft_path"], "draft_digest": digest, "event_id": existing["event_id"], "authority_changed": False}); return 0
    if destination.exists() and destination.read_bytes() != data: raise RecordError("scope_draft_collision", relative)
    if not destination.exists(): atomic_write(destination, data)
    event = base_event(event_id=f"event-scope-draft-{digest[-12:]}", engagement_id=state["engagement_id"], recorded_at=args.recorded_at, actor_role="broker", actor_id=args.actor_id, event_type="scope.amendment_proposed", rationale=args.reason, payload={"draft_path": relative, "draft_digest": digest, "supersedes_scope_hash": state["scope_hash"]}, session_id=args.session_id, operation_class="notebook"); record = _append_kernel_event_idempotent(engagement, event)
    emit({"valid": True, "draft_path": relative, "draft_digest": digest, "event_id": record["event_id"], "authority_changed": False}); return 0


def command_reattest_scope(args: argparse.Namespace) -> int:
    _require_decision6_kernel(args.engagement)
    _require_local_provenance("broker", args.executor_id, args.session_id); engagement = args.engagement.absolute(); draft = args.draft.resolve(strict=True); draft_bytes = draft.read_bytes(); draft_digest = sha256_bytes(draft_bytes); action = _authority_action("reattest-scope", lane_id=args.lane_id, executor_id=args.executor_id, session_id=args.session_id, draft_digest=draft_digest, operator_id=args.operator_id, recorded_at=args.recorded_at); action_digest = sha256_bytes(canonical_json_bytes(action)); require_repair_authority_from_intact_prefix(engagement, args.authority_request_id, "reattest-scope", action_digest, args.lane_id, args.recorded_at)
    draft_metadata = _scope_metadata(draft); normalized_operator = re.sub(r"[^A-Za-z0-9._:-]+", "-", draft_metadata["operator"]).strip("-") or "operator"; active_operator = next(event["payload"]["operator_id"] for event in reversed(read_ledger(engagement, "event")) if event["event_type"] == "scope.attested")
    if normalized_operator != args.operator_id or args.operator_id != active_operator or draft_metadata["scope_hash"] != draft_digest: raise RecordError("scope_reattestation_invalid", "scope amendment cannot silently replace the active operator identity")
    if not any(event["event_type"] == "scope.amendment_proposed" and event["payload"].get("draft_digest") == draft_digest for event in read_ledger(engagement, "event")): raise RecordError("scope_draft_not_proposed", draft_digest)
    with engagement_lock(engagement):
        prior_events = read_ledger(engagement, "event"); prior_scope = next(event["payload"]["scope_hash"] for event in reversed(prior_events) if event["event_type"] == "scope.attested"); atomic_write(engagement / "scope.md", draft_bytes); snapshot_path = persist_scope_snapshot(engagement, draft_digest)
        event = base_event(event_id=f"event-scope-{draft_digest[-12:]}", engagement_id=prior_events[0]["engagement_id"], recorded_at=args.recorded_at, actor_role="operator", actor_id=args.operator_id, event_type="scope.attested", rationale=args.reason, payload={"scope_hash": draft_digest, "scope_snapshot_path": snapshot_path, "operator_id": args.operator_id, "signed_date": draft_metadata["date"], "record_kernel": draft_metadata["record_kernel"], "supersedes_scope_hash": prior_scope, "authority_request_ref": args.authority_request_id, "executor_id": args.executor_id}, entity_refs=[prior_events[0]["engagement_id"]], session_id=args.session_id, operation_class="authority"); applied = _append_kernel_event_idempotent(engagement, event, lock_held=True)
    emit({"valid": True, "scope_hash": draft_digest, "event_id": applied["event_id"], "prior_scope_preserved": True}); return 0


def command_record_cleanup(args: argparse.Namespace) -> int:
    _require_local_provenance("broker", args.executor_id, args.session_id); engagement = args.engagement.absolute(); state = reduce_engagement(engagement); proposal = load_json(args.file)
    required = {"entity_id", "status", "cleanup_obligations"}
    if set(proposal) != required: raise RecordError("cleanup_proposal_fields_invalid", f"expected {sorted(required)}")
    action = _authority_action("record-cleanup", lane_id=args.lane_id, executor_id=args.executor_id, session_id=args.session_id, operator_id=args.operator_id, recorded_at=args.recorded_at, reason=args.reason, **proposal); _require_async_authority(args, action, args.recorded_at)
    previous = next((item["status"] for item in state["cleanup"]["obligations"] if item["obligation_id"] == proposal["entity_id"]), None)
    payload = {**proposal, "scope_hash": state["scope_hash"], "operator_id": args.operator_id, "updated_at": args.recorded_at, "authority_request_ref": args.authority_request_id, "executor_id": args.executor_id}
    event = base_event(event_id=f"event-cleanup-{args.authority_request_id}", engagement_id=state["engagement_id"], recorded_at=args.recorded_at, actor_role="broker", actor_id=args.executor_id, event_type="cleanup.updated", rationale=args.reason, payload=payload, state_changes=[{"dimension": "cleanup", "entity_id": proposal["entity_id"], "previous": previous, "current": proposal["status"]}], session_id=args.session_id, operation_class="authority"); applied = _append_kernel_event_idempotent(engagement, event); emit({"valid": True, "event_id": applied["event_id"]}); return 0


def command_record_operator_prior(args: argparse.Namespace) -> int:
    _require_local_provenance("broker", args.executor_id, args.session_id); engagement = args.engagement.absolute(); state = reduce_engagement(engagement)
    action = _authority_action("record-operator-prior", lane_id=args.lane_id, executor_id=args.executor_id, session_id=args.session_id, operator_id=args.operator_id, recorded_at=args.recorded_at, prior_id=args.prior_id, prior_statement=args.prior_statement, strength=args.strength, reason=args.reason); _require_async_authority(args, action, args.recorded_at)
    payload = {"prior_id": args.prior_id, "prior_statement": args.prior_statement, "strength": args.strength, "reason": args.reason, "operator_id": args.operator_id, "authority_request_ref": args.authority_request_id, "executor_id": args.executor_id}
    event = base_event(event_id=f"event-prior-{args.authority_request_id}", engagement_id=state["engagement_id"], recorded_at=args.recorded_at, actor_role="broker", actor_id=args.executor_id, event_type="operator_prior.recorded", rationale=args.reason, payload=payload, session_id=args.session_id, operation_class="authority"); applied = _append_kernel_event_idempotent(engagement, event); emit({"valid": True, "event_id": applied["event_id"]}); return 0


def command_reopen(args: argparse.Namespace) -> int:
    _require_local_provenance("broker", args.executor_id, args.session_id); engagement = args.engagement.absolute(); state = reduce_engagement(engagement); events = read_ledger(engagement, "event")
    current = {"engagement": None, "coverage": None}
    for event in events:
        for change in event.get("state_changes", []):
            if change["entity_id"] == state["engagement_id"] and change["dimension"] in current: current[change["dimension"]] = change["current"]
    if current["engagement"] not in {"blocked", "closed"} or current["coverage"] not in {"blocked", "coverage_dry"}: raise RecordError("engagement_reopen_not_applicable", str(current))
    action = _authority_action("reopen", lane_id=args.lane_id, executor_id=args.executor_id, session_id=args.session_id, operator_id=args.operator_id, recorded_at=args.recorded_at, reason=args.reason); _require_async_authority(args, action, args.recorded_at)
    payload = {"entity_id": state["engagement_id"], "status": "active", "operator_id": args.operator_id, "authority_request_ref": args.authority_request_id, "executor_id": args.executor_id}; changes = [{"dimension": dimension, "entity_id": state["engagement_id"], "previous": current[dimension], "current": "active"} for dimension in ("engagement", "coverage")]
    event = base_event(event_id=f"event-reopen-{args.authority_request_id}", engagement_id=state["engagement_id"], recorded_at=args.recorded_at, actor_role="broker", actor_id=args.executor_id, event_type="engagement.reopened", rationale=args.reason, payload=payload, state_changes=changes, session_id=args.session_id, operation_class="authority"); applied = _append_kernel_event_idempotent(engagement, event); emit({"valid": True, "event_id": applied["event_id"]}); return 0


def command_request_authority(args: argparse.Namespace) -> int:
    action = load_json(args.action_file)
    if not isinstance(action, dict) or action.get("action_kind") != args.action_kind or action.get("lane_id") != args.lane_id or detect_secret_classes(canonical_json_bytes(action)):
        raise RecordError("authority_action_invalid", args.request_id)
    _require_local_provenance(args.actor_role, args.actor_id, args.session_id)
    now = datetime.now(timezone.utc); requested = datetime.fromisoformat(args.recorded_at.replace("Z", "+00:00")); expires = datetime.fromisoformat(args.expires_at.replace("Z", "+00:00"))
    if abs((requested - now).total_seconds()) > 60 or expires <= now or (expires - now).total_seconds() > 86400: raise RecordError("authority_request_time_invalid", args.request_id)
    capability = classify_command("request-authority"); _enforce_mutation(capability, args.engagement, args.actor_role, args.actor_id, "request-authority")
    state = reduce_engagement(args.engagement.absolute()); action_bytes = canonical_json_bytes(action); digest = sha256_bytes(action_bytes); action_relative = f"authority/requests/{args.request_id}.action.json"; action_path = args.engagement.absolute() / action_relative
    if action_path.exists() and action_path.read_bytes() != action_bytes: raise RecordError("authority_action_id_collision", args.request_id)
    if not action_path.exists(): atomic_write(action_path, action_bytes)
    event = base_event(event_id=f"event-authority-request-{args.request_id}", engagement_id=state["engagement_id"], recorded_at=args.recorded_at, actor_role=args.actor_role, actor_id=args.actor_id, event_type="authority.requested", rationale=args.reason, payload={"request_id": args.request_id, "action_kind": args.action_kind, "action_digest": digest, "action_path": action_relative, "lane_id": args.lane_id, "request_status": "pending_authority", "scope_hash": state["scope_hash"], "environment_ref": state["active_environment_ref"], "expires_at": args.expires_at}, session_id=args.session_id, operation_class="notebook")
    record = _append_kernel_event_idempotent(args.engagement.absolute(), event)
    emit({"ok": True, "request_id": args.request_id, "request_event_ref": record["event_id"], "action_digest": digest, "status": "pending_authority"})
    return 0


def command_resolve_authority(args: argparse.Namespace) -> int:
    capability = classify_command("resolve-authority"); _require_local_session(args.session_id)
    pending_state = reduce_engagement(args.engagement.absolute()); pending_request = pending_state["authority_requests"].get(args.request_id); action_path = args.engagement.absolute() / str((pending_request or {}).get("action_path", ""))
    try: action_bytes=read_governed_file(action_path)
    except (OSError,RecordError): action_bytes=b""
    if pending_request is None or sha256_bytes(action_bytes) != pending_request["action_digest"]: raise RecordError("authority_action_record_invalid", args.request_id)
    try: action_text=action_bytes.decode("utf-8")
    except UnicodeDecodeError: raise RecordError("authority_action_record_invalid",args.request_id)
    sys.stderr.write("Exact proposed action for operator review:\n" + action_text); sys.stderr.flush()
    _enforce_mutation(capability, args.engagement, "operator", args.operator_id, f"resolve-authority:{args.request_id}:{pending_request['action_digest']}:{args.resolution}:{args.recorded_at}")
    now = datetime.now(timezone.utc); recorded = datetime.fromisoformat(args.recorded_at.replace("Z", "+00:00"))
    if abs((recorded - now).total_seconds()) > 60: raise RecordError("authority_resolution_time_not_current", args.request_id)
    state = reduce_engagement(args.engagement.absolute()); request = state["authority_requests"].get(args.request_id)
    if request is None or request["status"] != "pending_authority":
        raise RecordError("authority_request_not_pending", args.request_id)
    event = base_event(event_id=f"event-authority-resolution-{args.request_id}-{args.resolution}", engagement_id=state["engagement_id"], recorded_at=args.recorded_at, actor_role="operator", actor_id=args.operator_id, event_type="authority.resolved", rationale=args.reason, payload={"request_id": args.request_id, "request_event_ref": request["request_event_ref"], "action_digest": request["action_digest"], "resolution": args.resolution, "resolved_at": args.recorded_at}, entity_refs=[request["request_event_ref"]], session_id=args.session_id, operation_class="authority")
    record = _append_kernel_event(args.engagement.absolute(), event)
    emit({"ok": True, "request_id": args.request_id, "resolution": args.resolution, "resolution_event_ref": record["event_id"]})
    return 0


def command_confirm_zone2(args: argparse.Namespace) -> int:
    proposal = load_json(args.file); plan = load_json(args.plan)
    capability = classify_command("confirm-zone2"); state = reduce_engagement(args.engagement.absolute())
    plan_keys = {"artifact_id", "metadata_digest", "planned_sha256", "planned_size", "relative_path", "scope_hash", "environment_ref", "cleanup_obligation_ref", "cleanup_obligation_id"}; action_digest = sha256_bytes(canonical_json_bytes(plan)) if set(plan) == plan_keys else None
    event_time = datetime.fromisoformat(proposal.get("recorded_at", "").replace("Z", "+00:00")); expiry = datetime.fromisoformat(proposal.get("payload", {}).get("expires_at", "").replace("Z", "+00:00")); now = datetime.now(timezone.utc)
    _require_local_session(str(proposal.get("provenance", {}).get("session_id", ""))); require_scope_zone2_authorized(args.engagement.absolute(), state["scope_hash"])
    if proposal.get("event_type") != "escalation.confirmed" or proposal.get("operation_class") != "real_world" or proposal.get("actor") != {"role": "operator", "id": args.operator_id} or not proposal.get("provenance", {}).get("session_id") or action_digest is None or proposal.get("payload", {}).get("action_digest") != action_digest or proposal.get("payload", {}).get("entity_id") != plan.get("artifact_id") or plan.get("scope_hash") != state["scope_hash"] or plan.get("environment_ref") != state["active_environment_ref"] or plan.get("cleanup_obligation_ref") != proposal.get("payload", {}).get("cleanup_obligation_ref") or plan.get("cleanup_obligation_id") != proposal.get("payload", {}).get("cleanup_obligation_id") or abs((event_time - now).total_seconds()) > 60 or not event_time < expiry or (expiry - event_time).total_seconds() > 1800:
        raise RecordError("zone2_confirmation_invalid", proposal.get("event_id", "unknown"))
    print(json.dumps({"zone2_confirmation_review": {"action_digest": action_digest, "plan": plan, "expires_at": proposal["payload"]["expires_at"], "operator_id": args.operator_id}}, sort_keys=True, separators=(",", ":")), file=sys.stderr, flush=True)
    _enforce_mutation(capability, args.engagement, "operator", args.operator_id, f"confirm-zone2:{action_digest}:{proposal['event_id']}:{proposal['recorded_at']}:{proposal['payload']['expires_at']}")
    record = _append_kernel_event_idempotent(args.engagement.absolute(), proposal)
    emit({"ok": True, "event_id": record["event_id"], "record_hash": record["record_hash"], "creates_artifact_bytes": False})
    return 0


def command_create_artifact(args: argparse.Namespace) -> int:
    _require_decision6_kernel(args.engagement)
    metadata = load_json(args.metadata); permit = load_json(args.classification); capability = classify_command("create-artifact")
    metadata_secret_classes=detect_secret_classes(canonical_json_bytes(metadata))
    if metadata_secret_classes: raise RecordError("secret_shaped_artifact_metadata","artifact metadata blocked before creation",[{"class":value} for value in metadata_secret_classes])
    _require_local_provenance("broker", args.actor_id, args.session_id); require_actor(capability, "broker")
    classification_body = {key: value for key, value in permit.items() if key != "classification_event_ref"}; classification_digest = sha256_bytes(canonical_json_bytes(classification_body))
    relative = Path(permit.get("relative_path", "")); engagement = args.engagement.absolute(); evidence = engagement / "evidence"; destination = engagement / relative
    if relative.is_absolute() or ".." in relative.parts or not relative.as_posix().startswith("evidence/") or evidence.is_symlink() or destination.is_symlink() or not destination.parent.is_dir() or any((engagement / Path(*relative.parts[:index])).is_symlink() for index in range(1, len(relative.parts))): raise RecordError("artifact_path_not_contained", relative.as_posix())
    data = sys.stdin.buffer.read(permit.get("source_size", -1) + 1)
    if len(data) != permit.get("source_size") or sha256_bytes(data) != permit.get("source_digest") or detect_secret_classes(data): raise RecordError("zone2_planned_bytes_mismatch", metadata.get("artifact_id", "unknown"))
    plan = _zone2_plan(metadata, planned_sha256=permit.get("source_digest", ""), planned_size=permit.get("source_size", -1), relative_path=relative.as_posix(), scope_hash=permit.get("scope_hash", ""), environment_ref=permit.get("environment_ref", ""), cleanup_obligation_ref=metadata.get("cleanup_obligation_ref") or ""); action_digest = sha256_bytes(canonical_json_bytes(plan))
    journal_path = engagement/"legacy"/"zone2-pending"/f"{metadata.get('artifact_id','unknown')}.json"; journal = {"schema_version":1,"artifact_id":metadata.get("artifact_id"),"action_digest":action_digest,"classification_digest":classification_digest,"relative_path":relative.as_posix(),"source_digest":permit.get("source_digest"),"source_size":permit.get("source_size"),"confirmation_event_ref":metadata.get("escalation_confirmation_event_ref")}; journal_bytes=canonical_json_bytes(journal)
    try: existing_journal = read_governed_file(journal_path)
    except FileNotFoundError: existing_journal = None
    if existing_journal is not None and existing_journal != journal_bytes: raise RecordError("zone2_resume_journal_mismatch", metadata.get("artifact_id", "unknown"))
    def exact_existing_record() -> dict[str, object] | None:
        candidate=next((item for item in read_ledger(engagement,"artifact") if item["artifact_id"]==metadata.get("artifact_id")),None)
        return candidate if candidate is not None and candidate.get("relative_path")==relative.as_posix() and candidate.get("sha256")==permit.get("source_digest") and candidate.get("size")==permit.get("source_size") and candidate.get("precreation_classification_digest")==classification_digest and candidate.get("escalation_confirmation_event_ref")==metadata.get("escalation_confirmation_event_ref") else None
    resuming = destination.exists() and existing_journal is not None
    if destination.exists() and existing_journal is None:
        completed=exact_existing_record()
        if completed is not None and read_governed_file(destination)==data: emit({"ok":True,"artifact_id":completed["artifact_id"],"record_hash":completed["record_hash"],"created_after_confirmation":True,"resumed":True}); return 0
        raise RecordError("artifact_bytes_precede_creation_command", relative.as_posix())
    if destination.exists() and read_governed_file(destination) != data: raise RecordError("artifact_bytes_precede_creation_command", relative.as_posix())
    state = reduce_engagement(engagement, allowed_record_orphans={relative.as_posix()} if resuming else None); events = read_ledger(engagement, "event")
    event = next((item for item in events if item["event_id"] == permit.get("classification_event_ref")), None); confirmation = next((item for item in events if item["event_id"] == metadata.get("escalation_confirmation_event_ref")), None)
    expiry = datetime.fromisoformat((permit.get("expires_at") or "").replace("Z", "+00:00")) if permit.get("expires_at") else None
    try: artifact_time=datetime.fromisoformat(str(metadata.get("created_at","")).replace("Z","+00:00")); classification_time=datetime.fromisoformat(str(permit.get("classified_at","")).replace("Z","+00:00")); confirmation_time=datetime.fromisoformat(str(confirmation.get("recorded_at","") if confirmation else "").replace("Z","+00:00"))
    except ValueError: artifact_time=classification_time=confirmation_time=None
    chronology_valid=artifact_time is not None and classification_time is not None and confirmation_time is not None and confirmation_time<=artifact_time<=expiry and classification_time<=artifact_time if expiry is not None else False
    contract_valid = set(permit) == ARTIFACT_PERMIT_FIELDS and metadata.get("operation_class") == "real_world" and metadata.get("advisory_zone") == "review_required" and permit.get("advisory_zone") == "review_required" and permit.get("operation_class") == "real_world" and permit.get("decision") == "allow_confirmed_creation" and permit.get("artifact_id") == metadata.get("artifact_id") and permit.get("metadata_digest") == sha256_bytes(canonical_json_bytes(metadata)) and permit.get("scope_hash") == state["scope_hash"] and permit.get("environment_ref") == state["active_environment_ref"] and permit.get("action_digest") == action_digest
    event_valid = event is not None and event["event_type"] == "artifact.classified" and event["payload"].get("classification_digest") == classification_digest and event["payload"].get("action_digest") == action_digest and event["payload"].get("source_digest") == permit.get("source_digest") and event["payload"].get("source_size") == permit.get("source_size")
    confirmation_valid = confirmation is not None and confirmation["event_type"] == "escalation.confirmed" and confirmation["payload"].get("action_digest") == action_digest and confirmation["payload"].get("cleanup_obligation_ref") == metadata.get("cleanup_obligation_ref") and confirmation["payload"].get("cleanup_obligation_id") == metadata.get("cleanup_obligation_id")
    if not contract_valid or not event_valid or not confirmation_valid or expiry is None or not chronology_valid: raise RecordError("zone2_creation_authority_invalid", metadata.get("artifact_id", "unknown"))
    metadata["precreation_classification_digest"] = classification_digest; metadata["precreation_classification_event_ref"] = event["event_id"]; metadata["classified_source_digest"] = permit["source_digest"]; metadata["classified_source_size"] = permit["source_size"]; metadata["classified_at"] = permit["classified_at"]
    preview = {**metadata, "relative_path": relative.as_posix(), "sha256": permit["source_digest"], "size": permit["source_size"], "immutable": True}
    preview = materialize_ledger_record("artifact", {key: value for key, value in preview.items() if key not in {"sequence", "previous_hash", "record_hash"}}, read_ledger(engagement, "artifact"))
    reference_errors = validate_record_with_references(preview, "artifact", engagement)
    if reference_errors:
        raise RecordError("record_reference_invalid", "Zone-2 artifact metadata invalid before creation", reference_errors)
    with engagement_lock(engagement):
        final_state = reduce_engagement(engagement, allowed_record_orphans={relative.as_posix()} if resuming else None)
        cleanup_id = confirmation["payload"].get("cleanup_obligation_id"); cleanup_open = any(item.get("obligation_id") == cleanup_id and item.get("status") == "open" for item in final_state["cleanup"]["obligations"])
        if (not resuming and (final_state["scope_hash"] != permit["scope_hash"] or final_state["active_environment_ref"] != permit["environment_ref"] or datetime.now(timezone.utc) > expiry)) or not cleanup_open:
            raise RecordError("zone2_creation_authority_expired", metadata.get("artifact_id", "unknown"))
        if existing_journal is None: atomic_write(journal_path,journal_bytes)
        if not destination.exists():
            governed_root, governed_parts = _governed_root(destination)
            if governed_root != engagement or tuple(governed_parts) != tuple(relative.parts): raise RecordError("artifact_path_not_contained", relative.as_posix())
            parent_fd, destination_name = _open_parent_fd(governed_root, governed_parts, create=False)
            try:
                if datetime.now(timezone.utc) > expiry: raise RecordError("zone2_creation_authority_expired", metadata.get("artifact_id", "unknown"))
                fd = os.open(destination_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600, dir_fd=parent_fd)
                try:
                    view = memoryview(data); written = 0
                    while written < len(view):
                        count = os.write(fd, view[written:])
                        if count <= 0: raise OSError("artifact write made no progress")
                        written += count
                    os.fsync(fd)
                finally: os.close(fd)
            finally: os.close(parent_fd)
        elif read_governed_file(destination) != data: raise RecordError("zone2_resume_bytes_mismatch", metadata["artifact_id"])
    existing_record = next((item for item in read_ledger(engagement,"artifact") if item["artifact_id"] == metadata["artifact_id"]),None)
    if existing_record is not None:
        exact_record=exact_existing_record()
        if exact_record is None or read_governed_file(destination)!=data: raise RecordError("zone2_resume_record_mismatch", metadata["artifact_id"])
        journal_path.unlink(missing_ok=True); emit({"ok":True,"artifact_id":exact_record["artifact_id"],"record_hash":exact_record["record_hash"],"created_after_confirmation":True,"resumed":True}); return 0
    try: record = register_artifact(engagement, destination, metadata, classification=permit)
    except RecordError:
        completed=exact_existing_record()
        if completed is None or read_governed_file(destination)!=data: raise
        record=completed
    journal_path.unlink(missing_ok=True); emit({"ok": True, "artifact_id": record["artifact_id"], "record_hash": record["record_hash"], "created_after_confirmation": True})
    return 0


def command_register_artifact(args: argparse.Namespace) -> int:
    metadata = load_json(args.metadata)
    permit = load_json(args.classification)
    variant = metadata.get("advisory_zone")
    derived_variant = artifact_variant(metadata)
    if variant not in ({"clear_local"} if derived_variant == "clear_local" else {"review_required", "unknown"}):
        raise RecordError("artifact_zone_underclassified", metadata.get("artifact_id", "unknown"))
    capability = classify_command("register-artifact", variant=variant)
    if capability["tier"] == "real_world":
        raise RecordError("canonical_zone2_creation_command_required", metadata.get("artifact_id", "unknown"))
    actor = metadata.get("producer", {})
    _require_local_provenance(str(actor.get("role", "")), str(actor.get("id", "")), str(metadata.get("producer_session_id", "")))
    require_actor(capability, actor.get("role", ""))
    if capability["tier"] == "notebook":
        _enforce_mutation(capability, args.engagement, actor.get("role", ""), actor.get("id", ""), "register-artifact")
    expected = ARTIFACT_PERMIT_FIELDS
    actual_file = args.file.absolute()
    try: actual_relative = actual_file.relative_to(args.engagement.absolute()).as_posix(); actual_bytes = read_governed_file(actual_file)
    except (ValueError, OSError, RecordError): raise RecordError("artifact_path_not_contained", metadata.get("artifact_id", "unknown"))
    expected_decision = "allow_local_creation" if capability["tier"] == "notebook" else "allow_confirmed_creation"
    state = reduce_engagement(args.engagement.absolute(), allowed_artifact_orphans={actual_relative}); classification_body = {key: value for key, value in permit.items() if key != "classification_event_ref"}; classification_digest = sha256_bytes(canonical_json_bytes(classification_body)); classification_event = next((event for event in read_ledger(args.engagement.absolute(), "event") if event["event_id"] == permit.get("classification_event_ref")), None)
    event_valid = classification_event is not None and classification_event["event_type"] == "artifact.classified" and classification_event["payload"].get("classification_digest") == classification_digest and classification_event["payload"].get("artifact_id") == metadata.get("artifact_id")
    bytes_valid = sha256_bytes(actual_bytes) == permit.get("source_digest") and len(actual_bytes) == permit.get("source_size")
    scope_valid = permit.get("scope_hash") == state["scope_hash"] and permit.get("environment_ref") == state["active_environment_ref"]
    timing_valid = permit.get("expires_at") is None
    if set(permit) != expected or permit.get("decision") != expected_decision or permit.get("file_absent_at_classification") is not True or permit.get("metadata_digest") != sha256_bytes(canonical_json_bytes(metadata)) or permit.get("artifact_id") != metadata.get("artifact_id") or permit.get("relative_path") != actual_relative or permit.get("advisory_zone") != metadata.get("advisory_zone") or permit.get("operation_class") != capability["tier"] or permit.get("engagement_id") != metadata.get("engagement_id") or not event_valid or not bytes_valid or not scope_valid or not timing_valid:
        raise RecordError("artifact_classification_mismatch", metadata.get("artifact_id", "unknown"))
    if not metadata.get("producer_session_id") or metadata.get("operation_class") != capability["tier"]:
        raise RecordError("artifact_provenance_invalid", metadata.get("artifact_id", "unknown"))
    metadata["precreation_classification_digest"] = classification_digest
    metadata["precreation_classification_event_ref"] = permit["classification_event_ref"]
    metadata["classified_source_digest"] = permit["source_digest"]
    metadata["classified_source_size"] = permit["source_size"]
    metadata["classified_at"] = permit["classified_at"]
    record = register_artifact(args.engagement.absolute(), args.file, metadata, classification=permit)
    emit({"ok": True, "artifact_id": record["artifact_id"], "sequence": record["sequence"], "record_hash": record["record_hash"], "sha256": record["sha256"]})
    return 0


def command_append_attempt(args: argparse.Namespace) -> int:
    proposal = load_json(args.file)
    capability = classify_command("append-attempt")
    actor = proposal.get("provenance", {}).get("actor", {})
    _enforce_mutation(capability, args.engagement, actor.get("role", ""), actor.get("id", ""), f"append-attempt:{proposal.get('attempt_id','unknown')}:{sha256_bytes(canonical_json_bytes(proposal))}")
    if proposal.get("operation_class") != "notebook" or proposal.get("actor") != actor:
        raise RecordError("attempt_provenance_invalid", proposal.get("attempt_id", "unknown"))
    session_id = _require_session(proposal.get("provenance", {}), "append-attempt"); _require_local_provenance(str(actor.get("role", "")), str(actor.get("id", "")), session_id)
    record = append_attempt(args.engagement.absolute(), proposal)
    emit({"ok": True, "attempt_id": record["attempt_id"], "sequence": record["sequence"], "record_hash": record["record_hash"]})
    return 0


def command_repair_tail(args: argparse.Namespace) -> int:
    _require_decision6_kernel(args.engagement)
    _require_local_provenance("broker", args.executor_id, args.session_id); action = _authority_action("repair-ledger-tail", lane_id=args.lane_id, executor_id=args.executor_id, session_id=args.session_id, ledger=args.ledger, operator_id=args.operator_id, reason=args.reason, recorded_at=args.recorded_at); action_digest = sha256_bytes(canonical_json_bytes(action)); require_repair_authority_from_intact_prefix(args.engagement, args.authority_request_id, "repair-ledger-tail", action_digest, args.lane_id, args.recorded_at)
    result = repair_ledger_tail(args.engagement.absolute(), args.ledger, args.operator_id, args.reason, args.recorded_at, args.authority_request_id, args.executor_id, args.session_id)
    emit({"ok": True, **result})
    return 0


def command_reduce(args: argparse.Namespace) -> int:
    engagement = args.engagement.absolute()
    with engagement_lock(engagement):
        snapshot = reduce_engagement(engagement)
        write_snapshot(engagement, snapshot)
        write_views(engagement, snapshot)
    emit({"ok": True, "event_count": snapshot["event_count"], "ledger_hash": snapshot["ledger_hash"]})
    return 0


def command_render(args: argparse.Namespace) -> int:
    engagement = args.engagement.absolute()
    with engagement_lock(engagement):
        snapshot = reduce_engagement(engagement)
        write_views(engagement, snapshot)
    emit({"ok": True, "views": sorted(render_views(snapshot))})
    return 0


def command_export_telemetry(args: argparse.Namespace) -> int:
    export = export_telemetry(args.engagement, args.output)
    emit(export if args.output is None else {"valid": True, "output": args.output.as_posix(), "classification": export["classification"], "candidate_count": len(export["candidates"])})
    return 0


def command_score_telemetry(args: argparse.Namespace) -> int:
    emit(score_telemetry(load_json(args.file)))
    return 0


def command_record_memory(args: argparse.Namespace) -> int:
    value = load_json(args.file); action = _authority_action("record-memory", lane_id=args.lane_id, executor_id=args.executor_id, session_id=args.session_id, file_digest=sha256_file(args.file), operator_id=args.operator_id); _require_async_authority(args, action, value["recorded_at"])
    record = record_memory_disposition(args.engagement, args.file, args.operator_id, args.authority_request_id, args.executor_id, args.session_id)
    emit({"valid": True, "disposition_id": record["disposition_id"], "disposition": record["disposition"], "plane1_modified": False})
    return 0


def command_close(args: argparse.Namespace) -> int:
    action = _authority_action("close", lane_id=args.lane_id, executor_id=args.executor_id, session_id=args.session_id, operator_id=args.operator_id, reason=args.reason, recorded_at=args.recorded_at); _require_async_authority(args, action, args.recorded_at)
    snapshot = close_engagement(args.engagement, args.operator_id, args.reason, args.recorded_at, args.authority_request_id, args.executor_id, args.session_id)
    emit({"valid": True, "engagement_id": snapshot["engagement_id"], "closed": True, "memory_disposition": snapshot["memory_disposition"]})
    return 0


def command_preflight(args: argparse.Namespace) -> int:
    _require_local_provenance(args.actor_role, args.actor_id, args.session_id)
    capability = classify_command("preflight")
    _enforce_mutation(capability, args.engagement, args.actor_role, args.actor_id, "environment-preflight")
    try:
        reproduction = json.loads(args.reproduction_argv)
        if not isinstance(reproduction, list) or any(not isinstance(item, str) or not item for item in reproduction):
            raise ValueError("reproduction argv must be a JSON array of strings; an empty array records a blocked preflight")
        record = collect_agent_preflight(args.engagement, preflight_id=args.preflight_id, mode=args.mode, target=args.target, expected_identity=args.expected_identity, runtime=args.runtime, reproduction_argv=reproduction, operator_id=args.actor_id, recorded_at=args.recorded_at, advisory_zone=args.advisory_zone, credentials_present=args.credentials_present, account_labels=args.account_label, configuration_files=args.configuration_file, endpoint_identity=args.endpoint_identity, account_role=args.account_role, feature_flags=args.feature_flag, actor_role=args.actor_role, actor_id=args.actor_id, session_id=args.session_id, model=args.model, provider=args.provider, tool_versions=args.tool_version)
    except (ValueError, json.JSONDecodeError) as exc:
        raise RecordError("preflight_invalid", str(exc)) from exc
    emit({"valid": True, "preflight_id": record["preflight_id"], "status": record["status"], "identity_hash": record["identity_hash"], "missing_fidelity": record["missing_fidelity"], "advisory_zone": record["safety"]["advisory_zone"], "zone2_authorization_granted": False})
    return 0


def _verify_review_signature(engagement: Path, review_bytes: bytes, reviewer_id: str, signature_path: Path, allowed_signers_path: Path) -> None:
    state = reduce_engagement(engagement.absolute()); latest_scope = next(event for event in reversed(read_ledger(engagement.absolute(), "event")) if event["event_type"] == "scope.attested"); scope_path = engagement.absolute()/latest_scope["payload"]["scope_snapshot_path"]
    try: scope_bytes, _ = _read_regular_file_once(scope_path)
    except (OSError, RecordError): raise RecordError("reviewer_signature_invalid", reviewer_id)
    if sha256_bytes(scope_bytes) != state["scope_hash"]: raise RecordError("reviewer_signature_invalid", reviewer_id)
    try: scope_text = scope_bytes.decode("utf-8")
    except UnicodeDecodeError: raise RecordError("reviewer_signature_invalid", reviewer_id)
    match = re.search(r"Reviewer allowed signers SHA256:\s*(sha256:[0-9a-f]{64})", scope_text)
    if match is None or signature_path.is_symlink() or allowed_signers_path.is_symlink() or not signature_path.is_file() or not allowed_signers_path.is_file(): raise RecordError("reviewer_signature_invalid", reviewer_id)
    signature_bytes = signature_path.read_bytes(); allowed_signers_bytes = allowed_signers_path.read_bytes()
    if sha256_bytes(allowed_signers_bytes) != match.group(1): raise RecordError("reviewer_signature_invalid", reviewer_id)
    with tempfile.TemporaryDirectory(prefix="review-signature-") as temporary:
        temporary_root = Path(temporary); signature_copy = temporary_root / "review.sig"; signers_copy = temporary_root / "allowed_signers"; signature_copy.write_bytes(signature_bytes); signers_copy.write_bytes(allowed_signers_bytes)
        command = ["/usr/bin/ssh-keygen", "-Y", "verify", "-f", str(signers_copy), "-I", reviewer_id, "-n", "llm-redteam-harness-review-v1", "-s", str(signature_copy)]
        result = subprocess.run(command, input=review_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"}, check=False)
    if result.returncode != 0: raise RecordError("reviewer_signature_invalid", reviewer_id)


def command_record_review(args: argparse.Namespace) -> int:
    _require_decision6_kernel(args.engagement)
    _require_local_provenance("broker", args.actor_id, args.session_id); review = load_json(args.file); event = load_json(args.event)
    mapping = {"claim_adjudication": "claim.adjudicated", "coverage": "review.coverage_completed", "regrade": "review.regrade_completed", "pocinator": "review.pocinator_completed"}
    expected_event = mapping.get(review.get("review_type")); reviewer_id = review.get("independence", {}).get("reviewer_id"); reviewer_session = review.get("independence", {}).get("reviewer_session_id")
    if not isinstance(reviewer_session, str) or not reviewer_session: raise RecordError("reviewer_session_unbound", str(reviewer_id or "unknown"))
    _verify_review_signature(args.engagement, canonical_json_bytes(review), str(reviewer_id or ""), args.signature, args.allowed_signers)
    if expected_event is None or event.get("event_type") != expected_event or event.get("operation_class") != "notebook" or event.get("actor") != {"role": "broker", "id": args.actor_id} or event.get("provenance", {}).get("session_id") != args.session_id or event.get("payload", {}).get("review_ref") != review.get("review_id") or event.get("payload", {}).get("reviewer_id") != reviewer_id or review.get("review_id") not in event.get("review_refs", []) or detect_secret_classes(canonical_json_bytes(review)) or detect_secret_classes(canonical_json_bytes(event)):
        raise RecordError("canonical_review_binding_invalid", review.get("review_id", "unknown"))
    review_errors = validate_record_with_references(review, "review", args.engagement)
    if review_errors: raise RecordError("canonical_review_invalid", review.get("review_id", "unknown"), review_errors)
    relative = f"reviews/{review['review_id']}.json"; destination = args.engagement.absolute() / relative; data = canonical_json_bytes(review)
    with engagement_lock(args.engagement.absolute()):
        state = reduce_engagement(args.engagement.absolute(), allowed_record_orphans={relative})
        if review.get("engagement_id") != state["engagement_id"] or event.get("engagement_id") != state["engagement_id"]: raise RecordError("cross_engagement_review", review.get("review_id", "unknown"))
        if destination.exists() and destination.read_bytes() != data: raise RecordError("review_id_collision", review["review_id"])
        if not destination.exists(): atomic_write(destination, data)
        commit = base_event(event_id=f"event-{review['review_id']}-commit", engagement_id=state["engagement_id"], recorded_at=event["recorded_at"], actor_role="broker", actor_id=args.actor_id, event_type="record.committed", rationale="Commit immutable externally-produced independent review.", payload={"record_path": relative, "record_digest": sha256_file(destination), "record_type": "review", "record_id": review["review_id"], "record_revision": None}, session_id=args.session_id, operation_class="notebook")
        _append_kernel_event_idempotent(args.engagement.absolute(), commit, lock_held=True); applied = _append_kernel_event_idempotent(args.engagement.absolute(), event, lock_held=True)
    emit({"valid": True, "review_id": review["review_id"], "event_id": applied["event_id"], "claim_truth_self_accepted": False}); return 0


def command_review_preflight(args: argparse.Namespace) -> int:
    action = _authority_action("review-preflight", lane_id=args.lane_id, executor_id=args.executor_id, session_id=args.session_id, preflight_id=args.preflight_id, verdict=args.verdict, reason=args.reason, operator_id=args.operator_id, recorded_at=args.recorded_at); _require_async_authority(args, action, args.recorded_at)
    review = review_preflight(args.engagement, args.preflight_id, args.verdict, args.reason, args.operator_id, args.recorded_at, args.authority_request_id, args.lane_id, args.executor_id, args.session_id)
    emit({"valid": True, "review_id": review["review_id"], "preflight_id": args.preflight_id, "verdict": args.verdict}); return 0


def command_migrate(args: argparse.Namespace) -> int:
    if sum(value is not None for value in (args.propose_engagement,args.dry_run_engagement,args.apply_proposal))>1:raise RecordError("migration_mode_conflict","choose exactly one migration mode")
    variant = "apply" if args.apply_proposal else ("propose" if args.propose_engagement or args.dry_run_engagement else "inventory")
    capability = classify_command("migrate", variant=variant)
    if variant == "apply":
        if not all((args.authority_engagement, args.operator_id, args.recorded_at, args.destination, args.authority_request_id, args.lane_id, args.executor_id, args.session_id)): raise RecordError("migration_apply_args_missing", "apply requires destination, control engagement, operator, time, and exact authority binding")
        _require_local_provenance("broker", args.executor_id, args.session_id); control = args.authority_engagement.absolute(); proposal_bytes, _ = _read_regular_file_once(args.apply_proposal); review_bytes = _read_regular_file_once(args.artifact_review)[0] if args.artifact_review else None; proposal_digest = sha256_bytes(proposal_bytes); review_digest = sha256_bytes(review_bytes) if review_bytes is not None else None; root_fd, root_resolved, root_identity = _open_bound_directory(args.root); destination_fd = -1
        try:
            destination_fd, destination_resolved, destination_identity = _open_bound_directory(args.destination); proposal_value=json.loads(proposal_bytes); source_base=root_resolved/"engagements" if (root_resolved/"engagements").is_dir() else root_resolved; source_scope_bytes,_=_read_regular_file_once(source_base/proposal_value["engagement_id"]/"scope.md"); destination_scope_bytes,_=_read_regular_file_once(destination_resolved/"scope.md"); source_scope_hash=sha256_bytes(source_scope_bytes); destination_scope_hash=sha256_bytes(destination_scope_bytes)
            action = _authority_action("apply-migration", lane_id=args.lane_id, executor_id=args.executor_id, session_id=args.session_id, operator_id=args.operator_id, recorded_at=args.recorded_at, proposal_digest=proposal_digest, artifact_review_digest=review_digest, root=str(root_resolved), root_identity=root_identity, destination=str(destination_resolved), destination_identity=destination_identity, source_scope_hash=source_scope_hash, destination_scope_hash=destination_scope_hash, operator_redaction_attested=True)
            action_digest = sha256_bytes(canonical_json_bytes(action)); journal_path=control/"authority"/"migration-runs"/f"{action_digest.removeprefix('sha256:')}.json"; journal_bytes=canonical_json_bytes({"schema_version":1,"request_id":args.authority_request_id,"action_digest":action_digest,"action":action,"status":"authorized"})
            try: existing_journal=read_governed_file(journal_path)
            except FileNotFoundError: existing_journal=None
            if existing_journal is not None and existing_journal != journal_bytes: raise RecordError("migration_resume_journal_mismatch", args.authority_request_id)
            resume=existing_journal is not None; _require_migration_tree_safety(root_fd, destination_fd, proposal_bytes, resume=resume)
            control_state=reduce_engagement(control); authorization_id=f"event-migration-authorized-{args.authority_request_id}"; existing_authorization=next((event for event in read_ledger(control,"event") if event["event_id"]==authorization_id),None)
            if resume:
                if existing_authorization is None:
                    authority_args=argparse.Namespace(engagement=control,executor_id=args.executor_id,session_id=args.session_id,authority_request_id=args.authority_request_id); _require_async_authority(authority_args,action,args.recorded_at); authorization_event=base_event(event_id=authorization_id,engagement_id=control_state["engagement_id"],recorded_at=args.recorded_at,actor_role="broker",actor_id=args.executor_id,event_type="migration.apply_authorized",rationale="Resume exact authorized migration after journal persistence.",payload={"entity_id":args.authority_request_id,"status":"authorized","action_digest":action_digest,"proposal_digest":proposal_digest,"destination_digest":sha256_bytes(str(destination_resolved).encode()),"operator_id":args.operator_id,"authority_request_ref":args.authority_request_id,"executor_id":args.executor_id},session_id=args.session_id,operation_class="authority"); _append_kernel_event_idempotent(control,authorization_event)
                elif existing_authorization.get("payload",{}).get("action_digest") != action_digest: raise RecordError("migration_resume_authorization_invalid", args.authority_request_id)
            else:
                authority_args = argparse.Namespace(engagement=control, executor_id=args.executor_id, session_id=args.session_id, authority_request_id=args.authority_request_id); _require_async_authority(authority_args, action, args.recorded_at); atomic_write(journal_path,journal_bytes)
                authorization_event = base_event(event_id=authorization_id, engagement_id=control_state["engagement_id"], recorded_at=args.recorded_at, actor_role="broker", actor_id=args.executor_id, event_type="migration.apply_authorized", rationale="Consume one exact migration authority before any migration effect, including bound-input persistence.", payload={"entity_id": args.authority_request_id, "status":"authorized", "action_digest":action_digest,"proposal_digest":proposal_digest,"destination_digest":sha256_bytes(str(destination_resolved).encode()),"operator_id":args.operator_id,"authority_request_ref":args.authority_request_id,"executor_id":args.executor_id},session_id=args.session_id,operation_class="authority"); _append_kernel_event_idempotent(control,authorization_event)
            inputs = control/"authority"/"apply-inputs"; proposal_copy = inputs/f"{action_digest.removeprefix('sha256:')}.proposal.json"; review_copy = inputs/f"{action_digest.removeprefix('sha256:')}.review.json"
            for path, data in ((proposal_copy, proposal_bytes), (review_copy, review_bytes)):
                if data is None: continue
                try: prior=read_governed_file(path)
                except FileNotFoundError: prior=None
                if prior is not None and prior != data: raise RecordError("migration_bound_input_collision", str(path))
                if prior is None: atomic_write(path, data); path.chmod(0o400)
            if (os.fstat(root_fd).st_dev, os.fstat(root_fd).st_ino) != (root_identity["device"], root_identity["inode"]) or (os.fstat(destination_fd).st_dev, os.fstat(destination_fd).st_ino) != (destination_identity["device"], destination_identity["inode"]) or (os.stat(root_resolved).st_dev, os.stat(root_resolved).st_ino) != (root_identity["device"], root_identity["inode"]) or (os.stat(destination_resolved).st_dev, os.stat(destination_resolved).st_ino) != (destination_identity["device"], destination_identity["inode"]): raise RecordError("migration_directory_identity_changed", args.authority_request_id)
            proposal_copy_fd = os.open(proposal_copy, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)); review_copy_fd = os.open(review_copy, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)) if review_bytes is not None else -1
            try:
                implementation = runpy.run_path(str(Path(__file__).with_name("migrate-decision5.py"))); migrated = implementation["apply_proposal"](root_resolved, Path(f"/dev/fd/{proposal_copy_fd}"), destination_resolved, args.operator_id, args.recorded_at, operator_redaction_attested=True, artifact_review_path=Path(f"/dev/fd/{review_copy_fd}") if review_copy_fd >= 0 else None, bound_root_fd=root_fd, bound_destination_fd=destination_fd, destination_engagement_id=destination_resolved.name, resume_authorized=resume, authority_request_ref=args.authority_request_id, authority_action_digest=action_digest, authority_control_engagement_id=control_state["engagement_id"], expected_source_scope_hash=source_scope_hash, expected_destination_scope_hash=destination_scope_hash, executor_id=args.executor_id, executor_session_id=args.session_id)
            finally:
                os.close(proposal_copy_fd)
                if review_copy_fd >= 0: os.close(review_copy_fd)
            emit({"valid": True, "migration": migrated, "authority_request_id": args.authority_request_id}); return 0
        finally:
            os.close(root_fd)
            if destination_fd >= 0: os.close(destination_fd)
    elif variant == "propose":
        source_id=args.propose_engagement or args.dry_run_engagement; source_base=args.root.absolute()/"engagements" if (args.root.absolute()/"engagements").is_dir() else args.root.absolute(); source_metadata=_scope_metadata(source_base/source_id/"scope.md")
        if source_metadata["record_kernel"]!="decision-0006-v1": raise RecordError("decision6_kernel_not_selected","migration broker proposal requires source scope decision-0006-v1")
        if not args.executor_id or not args.session_id: raise RecordError("migration_proposal_provenance_missing", "proposal requires local broker executor/session")
        _require_local_provenance("broker", args.executor_id, args.session_id); implementation = runpy.run_path(str(Path(__file__).with_name("migrate-decision5.py")))
        if args.propose_engagement:
            if not args.operator_id or not args.output or not args.recorded_at: raise RecordError("migration_proposal_args_missing", "proposal requires --operator-id and --output")
            proposal = implementation["write_proposal"](args.root, args.propose_engagement, args.operator_id, args.recorded_at, args.output, producer_role="broker", producer_id=args.executor_id); emit({"valid": True, "proposal_digest": sha256_file(args.output), "proposal_only": proposal["proposal_only"]}); return 0
        if not args.operator_id or not args.recorded_at or not args.migration_dir: raise RecordError("migration_dry_run_args_missing", "dry-run bundle requires --operator-id, --recorded-at and --migration-dir")
        bundle = implementation["write_dry_run_bundle"](args.root, args.dry_run_engagement, args.operator_id, args.recorded_at, args.migration_dir, producer_role="broker", producer_id=args.executor_id); emit({"valid": True, "bundle": bundle}); return 0
    command = [sys.executable, str(Path(__file__).with_name("migrate-decision5.py")), "--root", str(args.root)]
    if args.output: command += ["--output", str(args.output)]
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode:
        raise RecordError("migration_command_failed", result.stderr or result.stdout)
    if result.stdout: print(result.stdout, end="")
    else: emit({"valid": True, "output": str(args.output)})
    return 0


def command_revise_finding(args: argparse.Namespace) -> int:
    finding = load_json(args.file); digest = sha256_file(args.file); action = _authority_action("revise-finding", lane_id=args.lane_id, executor_id=args.executor_id, session_id=args.session_id, file_digest=digest, operator_id=args.operator_id, recorded_at=args.recorded_at); _require_async_authority(args, action, args.recorded_at)
    errors = validate_record_with_references(finding, "finding-v3", args.engagement)
    if errors: raise RecordError("finding_revision_invalid", finding.get("finding_id", "unknown"), errors)
    engagement = args.engagement.absolute(); finding_id = finding["finding_id"]; revision = finding["revision"]; relative = f"findings/{finding_id}/rev-{revision}.json"; destination = engagement / relative; review_id = finding["adjudication"]["review_ref"]
    with engagement_lock(engagement):
        state = reduce_engagement(engagement, allowed_record_orphans={relative}); index = build_reference_index(engagement); review_entry = next((item for item in index.get(review_id, []) if item["type"] == "review"), None)
        adjudication = next((event for event in reversed(read_ledger(engagement, "event")) if event["event_type"] == "claim.adjudicated" and event["payload"].get("entity_id") == finding_id and event["payload"].get("review_ref") == review_id), None)
        if review_entry is None or adjudication is None or finding.get("engagement_id") != state["engagement_id"]: raise RecordError("finding_adjudication_missing", finding_id)
        data = canonical_json_bytes(finding)
        if destination.exists() and destination.read_bytes() != data: raise RecordError("finding_revision_collision", f"{finding_id}:{revision}")
        if not destination.exists(): atomic_write(destination, data)
        commit = base_event(event_id=f"event-{finding_id}-r{revision}-commit", engagement_id=state["engagement_id"], recorded_at=args.recorded_at, actor_role="broker", actor_id=args.executor_id, event_type="record.committed", rationale="Commit immutable operator-authorized finding revision.", payload={"record_path": relative, "record_digest": digest, "record_type": "finding-v3", "record_id": finding_id, "record_revision": revision, "authority_request_ref": args.authority_request_id}, session_id=args.session_id, operation_class="authority"); _append_kernel_event_idempotent(engagement, commit, lock_held=True)
        event = base_event(event_id=f"event-{finding_id}-revision-{revision}", engagement_id=state["engagement_id"], recorded_at=args.recorded_at, actor_role="broker", actor_id=args.executor_id, event_type="finding.revised", rationale=finding["change_reason"], payload={"finding_id": finding_id, "finding_revision": revision, "status": finding["claim_state"], "finding_digest": digest, "adjudication_review_ref": review_id, "adjudication_review_digest": sha256_file(engagement / review_entry["path"]), "adjudication_event_ref": adjudication["event_id"], "supersedes_revision": finding["supersedes_revision"], "change_reason": finding["change_reason"], "operator_id": args.operator_id, "authority_request_ref": args.authority_request_id}, entity_refs=[finding_id, adjudication["event_id"]], finding_refs=[finding_id], review_refs=[review_id], session_id=args.session_id, operation_class="authority"); applied = _append_kernel_event_idempotent(engagement, event, lock_held=True)
    emit({"valid": True, "finding_id": finding_id, "revision": revision, "event_id": applied["event_id"], "adjudication_separate": True}); return 0


def command_accept_report(args: argparse.Namespace) -> int:
    action = _authority_action("accept-report", lane_id=args.lane_id, executor_id=args.executor_id, session_id=args.session_id, report_id=args.report_id, operator_id=args.operator_id, reason=args.reason, recorded_at=args.recorded_at); _require_async_authority(args, action, args.recorded_at)
    try:
        review = accept_report(args.engagement, args.report_id, args.operator_id, args.reason, args.recorded_at, args.authority_request_id, args.executor_id, args.session_id)
    except ValueError as exc:
        raise RecordError("report_acceptance_invalid", str(exc)) from exc
    emit({"valid": True, "review_id": review["review_id"], "report_id": args.report_id})
    return 0


def command_record_submission(args: argparse.Namespace) -> int:
    action = _authority_action("record-submission", lane_id=args.lane_id, executor_id=args.executor_id, session_id=args.session_id, report_id=args.report_id, file_digest=sha256_file(args.file), program=args.program, operator_id=args.operator_id, recorded_at=args.recorded_at); _require_async_authority(args, action, args.recorded_at)
    try:
        submission_id = record_submission(args.engagement, args.report_id, args.file, args.program, args.operator_id, args.recorded_at, args.authority_request_id, args.executor_id, args.session_id)
    except ValueError as exc:
        raise RecordError("submission_invalid", str(exc)) from exc
    emit({"valid": True, "submission_id": submission_id, "report_id": args.report_id})
    return 0


def command_generate_report(args: argparse.Namespace) -> int:
    omitted = []
    for value in args.omit_claim:
        if "=" not in value:
            raise RecordError("invalid_omitted_claim", "use --omit-claim claim-id=rationale")
        claim_id, rationale = value.split("=", 1); omitted.append({"claim_id": claim_id, "rationale": rationale})
    action = _authority_action("generate-report", lane_id=args.lane_id, executor_id=args.executor_id, session_id=args.session_id, finding_id=args.finding_id, revision=args.revision, included_claim_ids=args.include_claim, omitted_claims=omitted, operator_id=args.operator_id, recorded_at=args.recorded_at); _require_async_authority(args, action, args.recorded_at)
    try:
        manifest = generate_report(args.engagement, args.finding_id, args.revision, args.include_claim, omitted, args.operator_id, args.recorded_at, args.authority_request_id, args.executor_id, args.session_id)
    except ValueError as exc:
        raise RecordError("report_generation_invalid", str(exc)) from exc
    emit({"valid": True, "report_id": manifest["report_id"], "report_digest": manifest["report_digest"]})
    return 0


def command_render_proof(args: argparse.Namespace) -> int:
    engagement = args.engagement.absolute()
    reduce_engagement(engagement)
    entry = next((item for item in build_reference_index(engagement).get(args.finding_id, []) if item["type"] == "finding" and item.get("revision") == args.revision), None)
    if entry is None:
        raise RecordError("finding_revision_not_found", f"{args.finding_id}:{args.revision}")
    finding = load_json(engagement / entry["path"])
    emit({"valid": True, "finding_id": args.finding_id, "revision": args.revision, "claim_tuple_hash": claim_tuple_hash(finding), "markdown": render_claim_proof(finding)})
    return 0


def command_check_resume(args: argparse.Namespace) -> int:
    engagement = args.engagement.absolute()
    with engagement_lock(engagement):
        expected = assert_resume_current(engagement)
    emit({"ok": True, "event_count": expected["event_count"], "ledger_hash": expected["ledger_hash"]})
    return 0


def state_self_test() -> list[tuple[str, bool, str]]:
    append_event = _append_kernel_event
    collect_preflight = _collect_legacy_preflight
    checks: list[tuple[str, bool, str]] = []
    with tempfile.TemporaryDirectory(prefix="engagement-state-selftest-") as tmp:
        root = Path(tmp).resolve(); reviewer_key = root / "reviewer-ed25519"; subprocess.run(["/usr/bin/ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(reviewer_key)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); public_parts = reviewer_key.with_suffix(".pub").read_text().split(); allowed_signers_path = root / "allowed-signers"; allowed_signers_path.write_text(f"reviewer-external-canonical {public_parts[0]} {public_parts[1]}\noperator-selftest {public_parts[0]} {public_parts[1]}\n"); allowed_signers_digest = sha256_file(allowed_signers_path)
        engagement = root / "eng-selftest"
        engagement.mkdir()
        scope = f"""# Scope — self-test

## Surfaces in scope
- Local fixture only.
## Benign safe-objective set
- Deterministic ledger test.
## Escalation ceiling
- Local records only.
## Impact-demo authorization
- impact_demo_authorized: `yes`
- zone2_authorized_categories: `zone2_artifact_creation`
- zone2_escalation_ceiling: `artifact_creation`
- zone2_containment: `synthetic temporary-directory fixture`
## Accounts / fixtures
- None.
## Independent reviewer identity
- Reviewer allowed signers SHA256: {allowed_signers_digest}
## Authorization
- Operator allowed signers SHA256: {allowed_signers_digest}
- Operator: operator-selftest
- Date: 2026-07-10
- Signed: [x]
- Record kernel: `decision-0006-v1`
"""
        (engagement / "scope.md").write_text(scope, encoding="utf-8")
        init_cli = subprocess.run([sys.executable, str(Path(__file__).resolve()), "init", "--engagement", str(engagement), "--recorded-at", "2026-07-10T00:00:00Z"], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        try: init_console_gate = init_cli.returncode != 0 and json.loads(init_cli.stdout)["error"]["code"] == "operator_signature_required"
        except (json.JSONDecodeError, KeyError): init_console_gate = False
        checks.append(("fresh public init reaches the cryptographic operator gate without requiring a prior ledger", init_console_gate, init_cli.stdout + init_cli.stderr))
        pty_attempt=subprocess.run(["/usr/bin/script","-q","/dev/null",sys.executable,str(Path(__file__).resolve()),"init","--engagement",str(engagement),"--recorded-at","2026-07-10T00:00:00Z"],input="initialize-engagement operator-selftest\n",stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,check=False);checks.append(("agent-created pseudo-TTY cannot satisfy operator authority without a scoped signature","operator_signature_required" in pty_attempt.stdout+pty_attempt.stderr and not (engagement/"events.jsonl").exists(),pty_attempt.stdout+pty_attempt.stderr))
        init_challenge={"schema_version":1,"namespace":"llm-redteam-harness-operator-v1","engagement_id":engagement.name,"scope_hash":sha256_file(engagement/"scope.md"),"ledger_hash":None,"operation":"initialize-engagement:2026-07-10T00:00:00Z","operator_id":"operator-selftest"};init_challenge_path=root/"init-challenge.json";init_challenge_path.write_bytes(canonical_json_bytes(init_challenge));subprocess.run(["/usr/bin/ssh-keygen","-Y","sign","-f",str(reviewer_key),"-n","llm-redteam-harness-operator-v1",str(init_challenge_path)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);signed_env={**os.environ,"HARNESS_OPERATOR_SIGNATURE_FILE":str(init_challenge_path)+".sig","HARNESS_OPERATOR_ALLOWED_SIGNERS_FILE":str(allowed_signers_path)};signed_init=subprocess.run([sys.executable,str(Path(__file__).resolve()),"init","--engagement",str(engagement),"--recorded-at","2026-07-10T00:00:00Z"],env=signed_env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,check=False);checks.append(("public init accepts an exact scoped operator signature",signed_init.returncode==0,signed_init.stdout+signed_init.stderr))
        snapshot = initialize_engagement(engagement, "2026-07-10T00:00:00Z")
        checks.append(("signed-scope init creates one attested event", snapshot["event_count"] == 1 and read_ledger(engagement, "event")[0]["event_type"] == "scope.attested", str(snapshot)))
        signature_events=read_ledger(engagement,"event");signature_challenge={"schema_version":1,"namespace":"llm-redteam-harness-operator-v1","engagement_id":engagement.name,"scope_hash":snapshot["scope_hash"],"ledger_hash":signature_events[-1]["record_hash"],"operation":"selftest-signed-operation","operator_id":"operator-selftest"};challenge_path=root/"operator-challenge.json";challenge_path.write_bytes(canonical_json_bytes(signature_challenge));subprocess.run(["/usr/bin/ssh-keygen","-Y","sign","-f",str(reviewer_key),"-n","llm-redteam-harness-operator-v1",str(challenge_path)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);prior_signature=os.environ.get("HARNESS_OPERATOR_SIGNATURE_FILE");prior_signers=os.environ.get("HARNESS_OPERATOR_ALLOWED_SIGNERS_FILE");os.environ["HARNESS_OPERATOR_SIGNATURE_FILE"]=str(challenge_path)+".sig";os.environ["HARNESS_OPERATOR_ALLOWED_SIGNERS_FILE"]=str(allowed_signers_path);signed_gate_passed=True
        try:
            _require_operator_console(engagement,"operator-selftest","selftest-signed-operation");swapped_blocked=False
            try:_require_operator_console(engagement,"operator-selftest","selftest-swapped-operation")
            except RecordError as exc:swapped_blocked=exc.code=="operator_signature_invalid"
            signed_gate_passed=signed_gate_passed and swapped_blocked
        except RecordError:signed_gate_passed=False
        finally:
            if prior_signature is None:os.environ.pop("HARNESS_OPERATOR_SIGNATURE_FILE",None)
            else:os.environ["HARNESS_OPERATOR_SIGNATURE_FILE"]=prior_signature
            if prior_signers is None:os.environ.pop("HARNESS_OPERATOR_ALLOWED_SIGNERS_FILE",None)
            else:os.environ["HARNESS_OPERATOR_ALLOWED_SIGNERS_FILE"]=prior_signers
        checks.append(("scoped SSH signature authorizes only the exact operator challenge",signed_gate_passed,"valid operator signature rejected"))
        denied = root/"zone2-denied"; denied.mkdir(); denied.joinpath("scope.md").write_text(scope.replace("impact_demo_authorized: `yes`", "impact_demo_authorized: `no`").replace("zone2_authorized_categories: `zone2_artifact_creation`", "zone2_authorized_categories: `none`").replace("zone2_escalation_ceiling: `artifact_creation`", "zone2_escalation_ceiling: `none`")); denied_state = initialize_engagement(denied, "2026-07-10T00:00:00Z"); denied_blocked = False
        try: require_scope_zone2_authorized(denied, denied_state["scope_hash"])
        except RecordError as exc: denied_blocked = exc.code == "zone2_not_authorized_by_scope"
        checks.append(("signed scope denial mechanically blocks Zone-2 before confirmation", denied_blocked, "impact-demo denial was ignored"))
        legacy_kernel=root/"legacy-kernel";legacy_kernel.mkdir();legacy_kernel.joinpath("scope.md").write_text(scope.replace("decision-0006-v1","decision-0005-v1"));initialize_engagement(legacy_kernel,"2026-07-10T00:00:00Z");legacy_broker_blocked=False
        try:_require_decision6_kernel(legacy_kernel)
        except RecordError as exc:legacy_broker_blocked=exc.code=="decision6_kernel_not_selected"
        checks.append(("Decision-0005 signed scope cannot invoke Decision-0006 broker authority model",legacy_broker_blocked,"legacy kernel enabled autonomous broker commands"))
        symlink_root = root/"symlink-ledger"; symlink_root.mkdir(); symlink_root.joinpath("scope.md").write_text(scope); outside_ledger = root/"outside-ledger"; outside_ledger.write_bytes(b""); symlink_root.joinpath("events.jsonl").symlink_to(outside_ledger); symlink_ledger_blocked = False
        try: initialize_engagement(symlink_root, "2026-07-10T00:00:00Z")
        except (OSError, RecordError): symlink_ledger_blocked = outside_ledger.read_bytes() == b""
        checks.append(("preexisting ledger symlink is rejected before external append", symlink_ledger_blocked, "ledger symlink redirected a write"))
        symlink_parent_root = root/"symlink-parent"; symlink_parent_root.mkdir(); symlink_parent_root.joinpath("scope.md").write_text(scope); outside_dir = root/"outside-dir"; outside_dir.mkdir(); symlink_parent_root.joinpath("authority").symlink_to(outside_dir, target_is_directory=True); symlink_parent_blocked = False
        try: atomic_write(symlink_parent_root/"authority/requests/action.json", b"{}\n")
        except (OSError, RecordError): symlink_parent_blocked = not any(outside_dir.iterdir())
        checks.append(("preexisting governed parent symlink is rejected before file write", symlink_parent_blocked, "parent symlink redirected a write"))
        root_target = root/"engagement-root-target"; root_target.mkdir(); root_target.joinpath("scope.md").write_text(scope); root_link = root/"engagement-root-link"; root_link.symlink_to(root_target, target_is_directory=True); root_link_blocked = False
        try: initialize_engagement(root_link, "2026-07-10T00:00:00Z")
        except (OSError, RecordError): root_link_blocked = not root_target.joinpath("events.jsonl").exists()
        checks.append(("preexisting engagement-root symlink is rejected before initialization", root_link_blocked, "engagement-root symlink redirected initialization"))
        ancestor_target = root/"ancestor-target"; ancestor_target.mkdir(); ancestor_engagement = ancestor_target/"eng"; ancestor_engagement.mkdir(); ancestor_engagement.joinpath("scope.md").write_text(scope); ancestor_link = root/"ancestor-link"; ancestor_link.symlink_to(ancestor_target, target_is_directory=True); ancestor_blocked = False
        try: initialize_engagement(ancestor_link/"eng", "2026-07-10T00:00:00Z")
        except (OSError, RecordError): ancestor_blocked = not ancestor_engagement.joinpath("events.jsonl").exists()
        checks.append(("preexisting intermediate-ancestor symlink is rejected before initialization", ancestor_blocked, "ancestor symlink redirected initialization"))
        checks.append(("init writes deterministic snapshot and six generated views", (engagement / "state.snapshot.json").read_bytes() == canonical_json_bytes(snapshot) and len(render_views(snapshot)) == 6 and all((engagement / name).is_file() for name in render_views(snapshot)), "missing/stale initialization output"))

        authority_engagement = root / "authority-lanes"; authority_engagement.mkdir(); authority_engagement.joinpath("scope.md").write_text(scope.replace("self-test", "authority-lanes"), encoding="utf-8"); initialize_engagement(authority_engagement, "2026-07-10T00:00:00Z")
        action = _authority_action("test-authority", lane_id="lane-main", value="exact"); action_digest = sha256_bytes(canonical_json_bytes(action)); authority_scope = reduce_engagement(authority_engagement)["scope_hash"]
        request_event = base_event(event_id="event-authority-request-main", engagement_id=authority_engagement.name, recorded_at="2026-07-10T00:00:01Z", actor_role="orchestrator", actor_id="orchestrator-selftest", event_type="authority.requested", rationale="Request one exact lane-local test action.", payload={"request_id": "request-main", "action_kind": "test-authority", "action_digest": action_digest, "lane_id": "lane-main", "request_status": "pending_authority", "scope_hash": authority_scope, "environment_ref": None, "expires_at": "2099-07-10T00:10:00Z"}, session_id="session-authority-request", operation_class="notebook"); append_event(authority_engagement, request_event)
        unrelated = base_event(event_id="event-authority-unrelated", engagement_id=authority_engagement.name, recorded_at="2026-07-10T00:00:02Z", actor_role="orchestrator", actor_id="orchestrator-selftest", event_type="observation.recorded", rationale="Unrelated lane continues while authority is pending.", payload={"entity_id": "unrelated-observation", "entity_type": "observation", "status": "recorded"}, session_id="session-authority-request", operation_class="notebook"); append_event(authority_engagement, unrelated)
        retrospective_blocked = False
        try: require_approved_authority(authority_engagement, "request-main", "test-authority", action_digest, "lane-main", "2026-07-10T00:00:02Z")
        except RecordError as exc: retrospective_blocked = exc.code == "approved_authority_request_required"
        resolution = base_event(event_id="event-authority-resolution-main", engagement_id=authority_engagement.name, recorded_at="2026-07-10T00:00:03Z", actor_role="operator", actor_id="operator-selftest", event_type="authority.resolved", rationale="Approve the exact pending action.", payload={"request_id": "request-main", "request_event_ref": "event-authority-request-main", "action_digest": action_digest, "resolution": "approved", "resolved_at": "2026-07-10T00:00:03Z"}, entity_refs=["event-authority-request-main"], session_id="session-operator-authority", operation_class="authority"); append_event(authority_engagement, resolution)
        exact_approved = require_approved_authority(authority_engagement, "request-main", "test-authority", action_digest, "lane-main", "2026-07-10T00:00:04Z")["status"] == "approved"
        consumed = base_event(event_id="event-authority-consumed", engagement_id=authority_engagement.name, recorded_at="2026-07-10T00:00:04Z", actor_role="orchestrator", actor_id="orchestrator-selftest", event_type="observation.recorded", rationale="Consume the exact approval without changing another lane.", payload={"entity_id": "authority-consumption", "entity_type": "authority_application", "status": "recorded", "authority_request_ref": "request-main"}, session_id="session-authority-request", operation_class="notebook"); append_event(authority_engagement, consumed)
        reuse_blocked = False
        try: require_approved_authority(authority_engagement, "request-main", "test-authority", action_digest, "lane-main", "2026-07-10T00:00:05Z")
        except RecordError as exc: reuse_blocked = exc.code == "authority_request_already_consumed"
        resolutions = (("rejected", "2026-07-10T00:00:07Z", "2026-07-10T00:00:08Z", "2026-07-10T00:10:00Z"), ("expired", "2026-07-10T00:00:09Z", "2026-07-10T00:00:11Z", "2026-07-10T00:00:10Z"), ("superseded", "2026-07-10T00:00:12Z", "2026-07-10T00:00:13Z", "2026-07-10T00:10:00Z"))
        for resolution_name, requested_at, resolved_at, expires in resolutions:
            request_id = f"request-{resolution_name}"; request_ref = f"event-authority-request-{resolution_name}"
            append_event(authority_engagement, base_event(event_id=request_ref, engagement_id=authority_engagement.name, recorded_at=requested_at, actor_role="orchestrator", actor_id="orchestrator-selftest", event_type="authority.requested", rationale=f"Request for {resolution_name} test.", payload={"request_id": request_id, "action_kind": "test-authority", "action_digest": action_digest, "lane_id": f"lane-{resolution_name}", "request_status": "pending_authority", "scope_hash": authority_scope, "environment_ref": None, "expires_at": expires}, session_id=f"session-{resolution_name}", operation_class="notebook"))
            append_event(authority_engagement, base_event(event_id=f"event-authority-resolution-{resolution_name}", engagement_id=authority_engagement.name, recorded_at=resolved_at, actor_role="operator", actor_id="operator-selftest", event_type="authority.resolved", rationale=f"Resolve request as {resolution_name}.", payload={"request_id": request_id, "request_event_ref": request_ref, "action_digest": action_digest, "resolution": resolution_name, "resolved_at": resolved_at}, entity_refs=[request_ref], session_id="session-operator-authority", operation_class="authority"))
        authority_state = reduce_engagement(authority_engagement); states_seen = {item["status"] for item in authority_state["authority_requests"].values()}
        checks.append(("digest-bound async authority is lane-local, non-retrospective, one-use, and state-complete", retrospective_blocked and exact_approved and reuse_blocked and {"approved", "rejected", "expired", "superseded"}.issubset(states_seen), str(authority_state["authority_requests"])))

        invalid = base_event(event_id="event-invalid", engagement_id=engagement.name, recorded_at="2026-07-10T00:01:00Z", actor_role="reviewer", actor_id="reviewer-selftest", event_type="claim.adjudicated", rationale="Invalid direct confirmation must not append.", payload={"entity_id": "claim-1", "status": "confirmed", "review_ref": "review-invalid", "review_digest": "sha256:" + "0" * 64}, state_changes=[{"dimension": "claim", "entity_id": "claim-1", "previous": None, "current": "confirmed"}])
        invalid_caught = False
        before = (engagement / "events.jsonl").read_bytes()
        try:
            append_event(engagement, invalid)
        except RecordError as exc:
            invalid_caught = exc.code in {"invalid_state_transition", "record_reference_invalid"}
        checks.append(("invalid confirmation shortcut is rejected before append", invalid_caught and (engagement / "events.jsonl").read_bytes() == before, "invalid event changed ledger"))
        zero_cost = {"wall_seconds": 0, "model_seconds": 0, "tool_seconds": 0, "target_calls": 0, "model_calls": 0, "input_tokens": None, "output_tokens": None, "cost_usd": None, "human_review_seconds": 0}
        mismatch = base_event(event_id="event-mismatch", engagement_id=engagement.name, recorded_at="2026-07-10T00:01:30Z", actor_role="operator", actor_id="operator-selftest", event_type="candidate.proposed", rationale="Payload/state entity mismatch must fail.", payload={"candidate_id": "candidate-a", "source_observation_ref": "event-source", "routing_review_ref": "event-route", "activation_strength": "strong", "card_ids": ["card-1"], "status": "queued", "expected_information_gain": 1, "safety_class": "clear_local", "cost_estimate": zero_cost}, entity_refs=["event-source", "event-route"], state_changes=[{"dimension": "search", "entity_id": "candidate-b", "previous": None, "current": "queued"}]); mismatch["ex_ante"] = {"probability": 0.5, "ordinal": "strong", "recorded_before_outcome": True}
        mismatch_caught = False
        try:
            append_event(engagement, mismatch)
        except RecordError as exc:
            mismatch_caught = exc.code == "event_state_entity_mismatch"
        checks.append(("event type, payload entity, and state change are inseparable", mismatch_caught and (engagement / "events.jsonl").read_bytes() == before, "mismatched event appended"))

        observation = base_event(event_id="event-observation-c1", engagement_id=engagement.name, recorded_at="2026-07-10T00:01:31Z", actor_role="orchestrator", actor_id="orchestrator-selftest", event_type="observation.recorded", rationale="Bounded source observation.", payload={"entity_id": "observation-c1", "entity_type": "observation", "status": "recorded"})
        append_event(engagement, observation)
        routing = base_event(event_id="event-routing-c1", engagement_id=engagement.name, recorded_at="2026-07-10T00:01:32Z", actor_role="reviewer", actor_id="reviewer-selftest", event_type="routing.assessed", rationale="Signal independently routed to one card.", payload={"entity_id": "routing-c1", "source_observation_ref": "event-observation-c1", "activation_strength": "strong", "card_ids": ["card-selftest"], "status": "assessed"}, entity_refs=["event-observation-c1"])
        append_event(engagement, routing)
        negative_route = base_event(event_id="event-routing-negative", engagement_id=engagement.name, recorded_at="2026-07-10T00:01:32Z", actor_role="reviewer", actor_id="reviewer-selftest", event_type="routing.assessed", rationale="Observed control appears to hold and becomes a positive-control candidate.", payload={"entity_id": "routing-negative", "source_observation_ref": "event-observation-c1", "activation_strength": "negative", "card_ids": ["card-control"], "status": "likely_held"}, entity_refs=["event-observation-c1"])
        append_event(engagement, negative_route)
        candidate = base_event(event_id="event-candidate-c1", engagement_id=engagement.name, recorded_at="2026-07-10T00:01:33Z", actor_role="orchestrator", actor_id="orchestrator-selftest", event_type="candidate.proposed", rationale="Candidate is justified by the routed observation.", payload={"candidate_id": "candidate-c1", "source_observation_ref": "event-observation-c1", "routing_review_ref": "event-routing-c1", "activation_strength": "strong", "card_ids": ["card-selftest"], "status": "queued", "expected_information_gain": 1, "safety_class": "clear_local", "cost_estimate": zero_cost}, entity_refs=["event-observation-c1", "event-routing-c1"], state_changes=[{"dimension": "search", "entity_id": "candidate-c1", "previous": None, "current": "queued"}]); candidate["ex_ante"] = {"probability": 0.6, "ordinal": "strong", "recorded_before_outcome": True}
        append_event(engagement, candidate)
        negative_candidate = json.loads(json.dumps(candidate)); negative_candidate["event_id"] = "event-candidate-negative"; negative_candidate["payload"]["candidate_id"] = "candidate-negative"; negative_candidate["payload"]["activation_strength"] = "negative"; negative_candidate["state_changes"][0]["entity_id"] = "candidate-negative"
        negative_blocked = False
        try:
            append_event(engagement, negative_candidate)
        except RecordError as exc:
            negative_blocked = exc.code == "negative_signal_not_candidate"
        checks.append(("negative routing signal remains a control candidate, never a research candidate", negative_blocked, "negative signal entered candidate queue"))
        selection = base_event(event_id="event-candidate-selected", engagement_id=engagement.name, recorded_at="2026-07-10T00:01:34Z", actor_role="orchestrator", actor_id="orchestrator-selftest", event_type="candidate.selected", rationale="Highest bounded information gain.", payload={"candidate_id": "candidate-c1", "status": "selected", "reason": "highest bounded information gain"}, state_changes=[{"dimension": "search", "entity_id": "candidate-c1", "previous": "queued", "current": "selected"}])
        append_event(engagement, selection)
        hypothesis = base_event(event_id="event-hypothesis-h1", engagement_id=engagement.name, recorded_at="2026-07-10T00:01:35Z", actor_role="orchestrator", actor_id="orchestrator-selftest", event_type="hypothesis.created", rationale="Bounded hypothesis derived from selected candidate.", payload={"hypothesis_id": "hypothesis-h1", "origin_type": "candidate", "origin_ref": "candidate-c1", "candidate_ref": "candidate-c1", "hypothesis_statement": "The local branch omits the expected check.", "suspected_invariant": "The guard should dominate the local state transition.", "trust_boundary": "local caller to guarded state", "attacker_path": ["entry", "branch", "state transition"], "impact_ceiling": "owned fixture only", "bounded_space": "One pinned branch and matched sibling.", "lens_ids": ["authorization"], "card_ids": ["card-selftest"], "expected_confirming_evidence": [{"evidence_type": "trace", "description": "primary guard trace", "required": True}, {"evidence_type": "control", "description": "matched sibling trace", "required": True}], "decisive_falsifiers": ["matched sibling proves the guard is irrelevant"], "cost_estimate": zero_cost, "constraints": ["local only"], "next_experiment": "trace primary and sibling branches", "completion_criteria": ["primary trace", "matched negative control"], "status": "queued"}, entity_refs=["candidate-c1"], state_changes=[{"dimension": "search", "entity_id": "hypothesis-h1", "previous": None, "current": "queued"}])
        append_event(engagement, hypothesis)
        for status, previous, suffix in (("selected", "queued", "selected"), ("running", "selected", "running")):
            change = base_event(event_id=f"event-hypothesis-{suffix}", engagement_id=engagement.name, recorded_at="2026-07-10T00:01:36Z", actor_role="orchestrator", actor_id="orchestrator-selftest", event_type="hypothesis.status_changed", rationale=f"Hypothesis {status} under the bounded search plan.", payload={"hypothesis_id": "hypothesis-h1", "status": status, "reason": "bounded lifecycle", "experiment_refs": [], "control_refs": [], "supporting_evidence_refs": [], "conflicting_evidence_refs": [], "disposition_rationale": f"Hypothesis moved to {status} before execution.", "unresolved_questions": ["execution pending"], "next_route": "primary trace"}, state_changes=[{"dimension": "search", "entity_id": "hypothesis-h1", "previous": previous, "current": status}])
            if status == "running": change["provenance"].update({"session_id": "session-origin-selftest", "model": "origin-model"})
            append_event(engagement, change)
        model_prior = base_event(event_id="event-prior-model", engagement_id=engagement.name, recorded_at="2026-07-10T00:01:37Z", actor_role="orchestrator", actor_id="orchestrator-selftest", event_type="operator_prior.recorded", rationale="A model cannot mint operator authority.", payload={"prior_id": "prior-model", "prior_statement": "Unauthorized prior.", "strength": "strong", "reason": "invalid authority"})
        model_prior_blocked = False
        try:
            append_event(engagement, model_prior)
        except RecordError as exc:
            model_prior_blocked = exc.code == "operator_prior_actor_unauthorized"
        checks.append(("model cannot mint an operator prior", model_prior_blocked, "model prior appended"))
        prior = base_event(event_id="event-prior-p1", engagement_id=engagement.name, recorded_at="2026-07-10T00:01:38Z", actor_role="operator", actor_id="operator-selftest", event_type="operator_prior.recorded", rationale="Operator prior deepens search but proves no claim.", payload={"prior_id": "prior-p1", "prior_statement": "Inspect the sibling branch before declaring dry.", "strength": "strong", "reason": "operator source familiarity"}, entity_refs=["hypothesis-h1"])
        append_event(engagement, prior)
        search_state = reduce_engagement(engagement)
        checks.append(("candidate→selection→hypothesis lifecycle preserves separate search/claim/coverage state", search_state["candidates"]["candidate-c1"]["status"] == "selected" and search_state["hypotheses"]["hypothesis-h1"]["status"] == "running" and len(search_state["operator_priors"]) == 1 and len(search_state["control_candidates"]) == 1 and search_state["findings"] == {} and search_state["coverage"] == "active", str(search_state)))

        blocked = base_event(event_id="event-blocked", engagement_id=engagement.name, recorded_at="2026-07-10T00:02:00Z", actor_role="operator", actor_id="operator-selftest", event_type="engagement.blocked", rationale="Self-test blocker.", payload={"entity_id": engagement.name, "status": "blocked", "reason": "fixture"}, state_changes=[{"dimension": "engagement", "entity_id": engagement.name, "previous": "active", "current": "blocked"}, {"dimension": "coverage", "entity_id": engagement.name, "previous": "active", "current": "blocked"}])
        append_event(engagement, blocked)
        reduced_once = reduce_engagement(engagement)
        reduced_twice = reduce_engagement(engagement)
        checks.append(("reducer is byte-deterministic", canonical_json_bytes(reduced_once) == canonical_json_bytes(reduced_twice), "same ledgers reduced differently"))
        checks.append(("valid transition updates separate engagement and coverage state", reduced_once["coverage"] == "blocked" and reduced_once["active_blockers"], str(reduced_once)))

        progress = engagement / "progress.md"
        expected_progress = progress.read_bytes()
        progress.write_text("operator edit to generated view\n", encoding="utf-8")
        stale_view_caught = False
        try:
            assert_views_current(engagement, reduced_once)
        except RecordError as exc:
            stale_view_caught = exc.code == "stale_derived_views"
        write_views(engagement, reduced_once)
        checks.append(("derived-view edits are detected and deterministically overwritten", stale_view_caught and progress.read_bytes() == expected_progress, "generated view edit survived"))

        crash_event = base_event(event_id="event-crash-boundary", engagement_id=engagement.name, recorded_at="2026-07-10T00:03:00Z", actor_role="operator", actor_id="operator-selftest", event_type="observation.recorded", rationale="Ledger commit succeeds before simulated projection crash.", payload={"entity_id": "observation-1", "entity_type": "observation", "status": "recorded"})
        append_ledger_record(engagement, "event", crash_event)
        stale_snapshot = (engagement / "state.snapshot.json").read_bytes() != canonical_json_bytes(reduce_engagement(engagement))
        recovered = reduce_engagement(engagement); write_snapshot(engagement, recovered); write_views(engagement, recovered)
        checks.append(("resume recovers a ledger commit made before projection crash", stale_snapshot and recovered["last_event_id"] == "event-crash-boundary", "authoritative event was lost"))

        before_concurrent_count = len(read_ledger(engagement, "event")); local_broker_id, local_broker_session = _local_identity("broker")
        processes = []
        for number in range(4):
            proposal = base_event(event_id=f"event-concurrent-{number}", engagement_id=engagement.name, recorded_at="2026-07-10T00:10:00Z", actor_role="broker", actor_id=local_broker_id, event_type="observation.recorded", rationale=f"Concurrent append {number}.", payload={"entity_id": f"observation-{number + 2}", "entity_type": "observation", "status": "recorded"}, session_id=local_broker_session, operation_class="notebook")
            proposal_path = root / f"proposal-{number}.json"
            proposal_path.write_bytes(canonical_json_bytes(proposal))
            processes.append(subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "append-event", "--engagement", str(engagement), "--file", str(proposal_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
        for _ in range(2):
            processes.append(subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "reduce", "--engagement", str(engagement)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
        outcomes = [process.communicate(timeout=30) + (process.returncode,) for process in processes]
        concurrent_records = read_ledger(engagement, "event")
        current = reduce_engagement(engagement)
        checks.append(("concurrent writers serialize without loss or stale projections", all(result[2] == 0 for result in outcomes) and len(concurrent_records) == before_concurrent_count + 4 and (engagement / "state.snapshot.json").read_bytes() == canonical_json_bytes(current), str(outcomes)))
        forged=base_event(event_id="event-forged-operator",engagement_id=engagement.name,recorded_at="2026-07-10T00:10:01Z",actor_role="operator",actor_id="operator-selftest",event_type="observation.recorded",rationale="Attempt noninteractive operator impersonation.",payload={"entity_id":"observation-forged","entity_type":"observation","status":"recorded"});forged_path=root/"forged-operator.json";forged_path.write_bytes(canonical_json_bytes(forged));forged_run=subprocess.run([sys.executable,str(Path(__file__).resolve()),"append-event","--engagement",str(engagement),"--file",str(forged_path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,check=False)
        try:forged_payload=json.loads(forged_run.stdout);forged_blocked=forged_run.returncode!=0 and forged_payload.get("error",{}).get("code")=="operator_signature_required"
        except json.JSONDecodeError:forged_blocked=False
        checks.append(("noninteractive caller cannot impersonate signed operator through generic append",forged_blocked,forged_run.stdout+forged_run.stderr))
        snapshot_bytes = (engagement / "state.snapshot.json").read_bytes()
        stale_value = json.loads(snapshot_bytes); stale_value["event_count"] -= 1
        (engagement / "state.snapshot.json").write_bytes(canonical_json_bytes(stale_value))
        stale_resume_caught = False
        try:
            assert_resume_current(engagement)
        except RecordError as exc:
            stale_resume_caught = exc.code == "stale_state_snapshot"
        (engagement / "state.snapshot.json").write_bytes(snapshot_bytes)
        checks.append(("check-resume rejects a stale snapshot", stale_resume_caught, "stale snapshot accepted"))

        package_fixture = root / "package-fixture.bin"; package_fixture.write_bytes(b"pinned package fixture\n"); package_digest = sha256_file(package_fixture); runtime_fixture = Path(sys.executable).resolve()
        blocked_environment = collect_preflight(engagement, preflight_id="preflight-wrong-identity", mode="package", target=package_fixture, expected_identity="sha256:" + "f" * 64, runtime=runtime_fixture, reproduction_argv=[str(runtime_fixture), "-c", "pass"], operator_id="operator-selftest", recorded_at="2026-07-10T00:13:00Z", operator_redaction_attested=True)
        review_environment = collect_preflight(engagement, preflight_id="preflight-zone-review", mode="package", target=package_fixture, expected_identity=package_digest, runtime=runtime_fixture, reproduction_argv=[str(runtime_fixture), "-c", "pass"], operator_id="operator-selftest", recorded_at="2026-07-10T00:13:01Z", operator_redaction_attested=True, advisory_zone="unknown")
        environment_record = collect_preflight(engagement, preflight_id="preflight-selftest", mode="package", target=package_fixture, expected_identity=package_digest, runtime=runtime_fixture, reproduction_argv=[str(runtime_fixture), "-c", "pass"], operator_id="operator-selftest", recorded_at="2026-07-10T00:13:02Z", operator_redaction_attested=True, endpoint_identity="local", account_role="owner")
        retry_event_count = reduce_engagement(engagement)["event_count"]; retried_environment = collect_preflight(engagement, preflight_id="preflight-selftest", mode="package", target=package_fixture, expected_identity=package_digest, runtime=runtime_fixture, reproduction_argv=[str(runtime_fixture), "-c", "pass"], operator_id="operator-selftest", recorded_at="2026-07-10T00:13:02Z", operator_redaction_attested=True, endpoint_identity="local", account_role="owner")
        environment_state = reduce_engagement(engagement)
        checks.append(("preflight retry is byte-idempotent after record and event commit", retried_environment == environment_record and environment_state["event_count"] == retry_event_count, "preflight retry appended or changed immutable bytes"))
        checks.append(("wrong identity blocks and advisory Zone never authorizes or replaces a ready preflight", environment_record["status"] == "ready" and blocked_environment["status"] == "blocked" and review_environment["status"] == "needs_review" and environment_state["active_environment_ref"] == "preflight-selftest" and not any(item["safety"]["zone2_authorization_granted"] for item in (environment_record, blocked_environment, review_environment)), str(environment_state["environment_preflights"])))
        local_broker_id, local_broker_session = _local_identity("broker")
        collector_engagement = root / "collector-modes"; collector_engagement.mkdir(); collector_engagement.joinpath("scope.md").write_text(scope.replace("self-test", "collector-modes"), encoding="utf-8"); initialize_engagement(collector_engagement, "2026-07-10T00:13:10Z")
        agent_source_path = root / "agent-artifact-source.txt"; agent_source_path.write_text("benign agent evidence\n", encoding="utf-8"); source_time = datetime.fromisoformat("2026-07-10T00:13:09Z".replace("Z", "+00:00")).timestamp(); os.utime(agent_source_path, (source_time, source_time))
        agent_preflight_run = subprocess.run([sys.executable, str(Path(__file__).resolve()), "preflight", "--engagement", str(collector_engagement), "--preflight-id", "preflight-agent", "--mode", "package", "--target", str(package_fixture), "--expected-identity", package_digest, "--runtime", str(runtime_fixture), "--reproduction-argv", json.dumps([str(runtime_fixture), "-c", "pass"]), "--actor-role", "broker", "--actor-id", local_broker_id, "--session-id", local_broker_session, "--recorded-at", "2026-07-10T00:13:10.500000Z"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        agent_record = load_json(collector_engagement / "environment" / "preflight-preflight-agent.json") if agent_preflight_run.returncode == 0 else {}
        checks.append(("agent clear-local preflight is noninteractive, truthful, and separately collected", agent_preflight_run.returncode == 0 and agent_record.get("schema_version") == 2 and agent_record.get("status") == "ready" and agent_record.get("provenance", {}).get("actor") == {"role": "broker", "id": local_broker_id} and agent_record.get("provenance", {}).get("session_id") == local_broker_session and "operator_redaction_attested" not in agent_record.get("safety", {}), agent_preflight_run.stdout + agent_preflight_run.stderr))
        review_candidate = collect_agent_preflight(collector_engagement, preflight_id="preflight-agent-review", mode="package", target=package_fixture, expected_identity=package_digest, runtime=runtime_fixture, reproduction_argv=[str(runtime_fixture), "-c", "pass"], operator_id=local_broker_id, recorded_at="2026-07-10T00:13:10.510000Z", advisory_zone="unknown", actor_role="broker", actor_id=local_broker_id, session_id=local_broker_session)
        review_action = _authority_action("review-preflight", lane_id="lane-preflight-review", executor_id=local_broker_id, session_id=local_broker_session, preflight_id="preflight-agent-review", verdict="accepted", reason="Identity is exact; advisory zone remains non-authorizing.", operator_id="operator-selftest", recorded_at="2026-07-10T00:13:10.540000Z"); review_action_digest = sha256_bytes(canonical_json_bytes(review_action)); review_action_relative = "authority/requests/request-preflight-review.action.json"; atomic_write(collector_engagement / review_action_relative, canonical_json_bytes(review_action)); review_scope = reduce_engagement(collector_engagement)["scope_hash"]
        append_event(collector_engagement, base_event(event_id="event-authority-request-preflight-review", engagement_id=collector_engagement.name, recorded_at="2026-07-10T00:13:10.520000Z", actor_role="broker", actor_id=local_broker_id, event_type="authority.requested", rationale="Request operator review of immutable preflight facts.", payload={"request_id": "request-preflight-review", "action_kind": "review-preflight", "action_digest": review_action_digest, "action_path": review_action_relative, "lane_id": "lane-preflight-review", "request_status": "pending_authority", "scope_hash": review_scope, "environment_ref": None, "expires_at": "2099-07-10T00:00:00Z"}, session_id=local_broker_session, operation_class="notebook"))
        append_event(collector_engagement, base_event(event_id="event-authority-resolution-preflight-review", engagement_id=collector_engagement.name, recorded_at="2026-07-10T00:13:10.530000Z", actor_role="operator", actor_id="operator-selftest", event_type="authority.resolved", rationale="Accept exact identity facts without granting Zone-2 authority.", payload={"request_id": "request-preflight-review", "request_event_ref": "event-authority-request-preflight-review", "action_digest": review_action_digest, "resolution": "approved", "resolved_at": "2026-07-10T00:13:10.530000Z"}, entity_refs=["event-authority-request-preflight-review"], session_id="session-operator-review", operation_class="authority"))
        preflight_bytes = (collector_engagement / "environment" / "preflight-preflight-agent-review.json").read_bytes(); preflight_review = review_preflight(collector_engagement, "preflight-agent-review", "accepted", "Identity is exact; advisory zone remains non-authorizing.", "operator-selftest", "2026-07-10T00:13:10.540000Z", "request-preflight-review", "lane-preflight-review", local_broker_id, local_broker_session); reviewed_state = reduce_engagement(collector_engagement)
        checks.append(("preflight collection is immutable and separate from digest-bound operator review", review_candidate["status"] == "needs_review" and preflight_review["review_type"] == "operator" and (collector_engagement / "environment" / "preflight-preflight-agent-review.json").read_bytes() == preflight_bytes and reviewed_state["environment_preflights"]["preflight-agent-review"]["status"] == "ready" and reviewed_state["active_environment_ref"] == "preflight-agent-review" and review_candidate["safety"]["zone2_authorization_granted"] is False, str(reviewed_state["environment_preflights"])))
        agent_metadata = {"schema_version": 1, "artifact_id": "artifact-agent", "engagement_id": collector_engagement.name, "created_at": "2026-07-10T00:13:10.700000Z", "producer": {"role": "broker", "id": local_broker_id}, "producer_session_id": local_broker_session, "operation_class": "notebook", "acquisition_method": "source_inspection", "target_refs": [], "environment_ref": "preflight-agent-review", "sensitivity": "internal", "redaction_status": "not_needed", "contains_executable_capability": False, "advisory_zone": "clear_local", "escalation_confirmation_event_ref": None, "cleanup_obligation_ref": None, "supersedes_artifact_id": None, "media_type": "text/plain"}
        agent_metadata_path = root / "agent-artifact-metadata.json"; agent_metadata_path.write_bytes(canonical_json_bytes(agent_metadata)); classification_path = root / "agent-artifact-classification.json"
        classify_run = subprocess.run([sys.executable, str(Path(__file__).resolve()), "classify-artifact", "--engagement", str(collector_engagement), "--metadata", str(agent_metadata_path), "--source", str(agent_source_path), "--relative-path", "evidence/agent-artifact.txt", "--recorded-at", "2026-07-10T00:13:10.600000Z", "--actor-role", "broker", "--actor-id", local_broker_id, "--session-id", local_broker_session, "--output", str(classification_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        agent_artifact_path = collector_engagement / "evidence" / "agent-artifact.txt"; agent_artifact_path.parent.mkdir(exist_ok=True)
        if classify_run.returncode == 0: shutil.copyfile(agent_source_path, agent_artifact_path)
        register_run = subprocess.run([sys.executable, str(Path(__file__).resolve()), "register-artifact", "--engagement", str(collector_engagement), "--file", str(agent_artifact_path), "--metadata", str(agent_metadata_path), "--classification", str(classification_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        if register_run.returncode != 0: agent_artifact_path.unlink(missing_ok=True)
        dangling_destination=collector_engagement/"evidence"/"dangling-artifact.txt"; dangling_target=root/"outside-dangling-target"; dangling_destination.symlink_to(dangling_target); dangling_metadata=dict(agent_metadata); dangling_metadata["artifact_id"]="artifact-dangling"; dangling_metadata_path=root/"dangling-metadata.json"; dangling_metadata_path.write_bytes(canonical_json_bytes(dangling_metadata)); dangling_run=subprocess.run([sys.executable,str(Path(__file__).resolve()),"classify-artifact","--engagement",str(collector_engagement),"--metadata",str(dangling_metadata_path),"--source",str(agent_source_path),"--relative-path","evidence/dangling-artifact.txt","--recorded-at","2026-07-10T00:13:10.750000Z","--actor-role","broker","--actor-id",local_broker_id,"--session-id",local_broker_session],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,check=False); checks.append(("clear-local classification rejects dangling destination symlink before permit",dangling_run.returncode!=0 and not dangling_target.exists(),dangling_run.stdout+dangling_run.stderr)); dangling_destination.unlink()
        zone2_metadata = dict(agent_metadata); zone2_metadata["artifact_id"] = "artifact-zone2-blocked"; zone2_metadata["advisory_zone"] = "review_required"; zone2_metadata["operation_class"] = "real_world"; zone2_path = root / "zone2-metadata.json"; zone2_path.write_bytes(canonical_json_bytes(zone2_metadata)); blocked_zone2_path = collector_engagement / "evidence" / "zone2-blocked.bin"
        classify_zone2 = subprocess.run([sys.executable, str(Path(__file__).resolve()), "classify-artifact", "--engagement", str(collector_engagement), "--metadata", str(zone2_path), "--planned-sha256", sha256_file(agent_source_path), "--planned-size", str(agent_source_path.stat().st_size), "--relative-path", "evidence/zone2-blocked.bin", "--recorded-at", "2026-07-10T00:13:10.800000Z", "--actor-role", "broker", "--actor-id", local_broker_id, "--session-id", local_broker_session], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        try: zone2_error = json.loads(classify_zone2.stdout).get("error", {}).get("code")
        except json.JSONDecodeError: zone2_error = None
        checks.append(("artifact creation is classified before bytes and Zone-2 fails before creation", classify_run.returncode == 0 and register_run.returncode == 0 and not blocked_zone2_path.exists() and zone2_error == "artifact_creation_requires_fresh_confirmation", classify_run.stdout + register_run.stdout + classify_zone2.stdout))
        secret_package = root / "secret-package.txt"; secret_package.write_text("Authorization: Bearer synthetic-credential-shape-1234567890\n", encoding="utf-8"); secret_preflight = collect_agent_preflight(collector_engagement, preflight_id="preflight-secret-blocked", mode="package", target=secret_package, expected_identity=sha256_file(secret_package), runtime=runtime_fixture, reproduction_argv=[str(runtime_fixture), "-c", "pass"], operator_id=local_broker_id, recorded_at="2026-07-10T00:13:10.900000Z", actor_role="broker", actor_id=local_broker_id, session_id=local_broker_session)
        checks.append(("automatic preflight scanning blocks secret-shaped target bytes without storing values", secret_preflight["status"] == "blocked" and secret_preflight["safety"]["credentials_present"] is True and secret_preflight["safety"]["secret_scan_status"] == "blocked" and "authorization_header" in secret_preflight["safety"]["secret_pattern_classes"] and "synthetic-credential" not in canonical_json_bytes(secret_preflight).decode("utf-8"), str(secret_preflight["safety"])))
        git_fixture = root / "git-fixture"; git_fixture.mkdir(); subprocess.run(["git", "init", "-q", str(git_fixture)], check=True); subprocess.run(["git", "-C", str(git_fixture), "config", "user.email", "fixture@example.invalid"], check=True); subprocess.run(["git", "-C", str(git_fixture), "config", "user.name", "Fixture"], check=True); git_fixture.joinpath("fixture.txt").write_text("fixture\n"); subprocess.run(["git", "-C", str(git_fixture), "add", "fixture.txt"], check=True); subprocess.run(["git", "-C", str(git_fixture), "commit", "-qm", "fixture"], check=True); git_commit = subprocess.check_output(["git", "-C", str(git_fixture), "rev-parse", "HEAD"], text=True).strip(); fsmonitor_sentinel = root / "fsmonitor-ran"; fsmonitor_hook = root / "fsmonitor-hook.sh"; fsmonitor_hook.write_text(f"#!/bin/sh\ntouch '{fsmonitor_sentinel}'\nexit 0\n"); fsmonitor_hook.chmod(0o700); subprocess.run(["git", "-C", str(git_fixture), "config", "core.fsmonitor", str(fsmonitor_hook)], check=True)
        git_preflight = collect_preflight(collector_engagement, preflight_id="preflight-git", mode="git", target=git_fixture, expected_identity=git_commit, runtime=runtime_fixture, reproduction_argv=[str(Path(sys.executable).resolve()), "-c", "pass"], operator_id="operator-selftest", recorded_at="2026-07-10T00:13:11Z", operator_redaction_attested=True); fsmonitor_suppressed = not fsmonitor_sentinel.exists()
        git_fixture.joinpath("secret.txt").write_text("Authorization: Bearer synthetic-git-credential-1234567890\n"); subprocess.run(["git", "-C", str(git_fixture), "add", "secret.txt"], check=True); subprocess.run(["git", "-C", str(git_fixture), "commit", "-qm", "secret fixture"], check=True); secret_git_commit = subprocess.check_output(["git", "-C", str(git_fixture), "rev-parse", "HEAD"], text=True).strip()
        secret_git_preflight = collect_agent_preflight(collector_engagement, preflight_id="preflight-git-secret", mode="git", target=git_fixture, expected_identity=secret_git_commit, runtime=runtime_fixture, reproduction_argv=[str(Path(sys.executable).resolve()), "-c", "pass"], operator_id=local_broker_id, recorded_at="2026-07-10T00:13:11.500000Z", actor_role="broker", actor_id=local_broker_id, session_id=local_broker_session)
        local_preflight = collect_preflight(collector_engagement, preflight_id="preflight-local-runtime", mode="local_runtime", target=package_fixture, expected_identity=package_digest, runtime=runtime_fixture, reproduction_argv=[str(Path(sys.executable).resolve()), "-c", "pass"], operator_id="operator-selftest", recorded_at="2026-07-10T00:13:12Z", operator_redaction_attested=True)
        checks.append(("demonstrated Git, package, and local-runtime collectors pin identity without executing reproduction argv", git_preflight["status"] == "ready" and fsmonitor_suppressed and secret_git_preflight["status"] == "blocked" and "authorization_header" in secret_git_preflight["safety"]["secret_pattern_classes"] and local_preflight["status"] == "ready" and reduce_engagement(collector_engagement)["active_environment_ref"] == "preflight-local-runtime", str((git_preflight["status"], local_preflight["status"]))))
        cleanup_event = base_event(event_id="event-cleanup-open", engagement_id=collector_engagement.name, recorded_at="2026-07-10T00:13:13Z", actor_role="operator", actor_id="operator-selftest", event_type="cleanup.updated", rationale="Track an unresolved local fixture cleanup obligation.", payload={"entity_id": "cleanup-selftest", "status": "open", "scope_hash": reduce_engagement(collector_engagement)["scope_hash"], "operator_id": "operator-selftest", "updated_at": "2026-07-10T00:13:13Z", "cleanup_obligations": [{"obligation_id": "cleanup-selftest", "kind": "local_fixture", "status": "open", "artifact_refs": [], "rationale": "Fixture cleanup remains open.", "closed_at": None}]}, state_changes=[{"dimension": "cleanup", "entity_id": "cleanup-selftest", "previous": None, "current": "open"}]); append_event(collector_engagement, cleanup_event)
        cleanup_blocked = collect_preflight(collector_engagement, preflight_id="preflight-cleanup-debt", mode="package", target=package_fixture, expected_identity=package_digest, runtime=runtime_fixture, reproduction_argv=[str(runtime_fixture), "-c", "pass"], operator_id="operator-selftest", recorded_at="2026-07-10T00:13:14Z", operator_redaction_attested=True)
        checks.append(("reduced cleanup debt blocks and invalidates environment activation", cleanup_blocked["status"] == "blocked" and cleanup_blocked["safety"]["cleanup_open_count"] == 1 and reduce_engagement(collector_engagement)["active_environment_ref"] is None, str(cleanup_blocked)))
        second_cleanup = base_event(event_id="event-cleanup-second", engagement_id=collector_engagement.name, recorded_at="2026-07-10T00:13:15Z", actor_role="operator", actor_id="operator-selftest", event_type="cleanup.updated", rationale="A delta update must not erase an earlier open obligation.", payload={"entity_id": "cleanup-second", "status": "open", "scope_hash": reduce_engagement(collector_engagement)["scope_hash"], "operator_id": "operator-selftest", "updated_at": "2026-07-10T00:13:15Z", "cleanup_obligations": [{"obligation_id": "cleanup-second", "kind": "local_fixture", "status": "open", "artifact_refs": [], "rationale": "Second fixture cleanup remains open.", "closed_at": None}]}, state_changes=[{"dimension": "cleanup", "entity_id": "cleanup-second", "previous": None, "current": "open"}]); append_event(collector_engagement, second_cleanup)
        checks.append(("cleanup delta cannot silently drop an earlier open obligation", reduce_engagement(collector_engagement)["cleanup"]["open_count"] == 2, str(reduce_engagement(collector_engagement)["cleanup"])))
        normalization_engagement = root / "operator-normalization"; normalization_engagement.mkdir(); normalization_engagement.joinpath("scope.md").write_text(scope.replace("self-test", "operator-normalization").replace("operator-selftest", "Operator Name!"), encoding="utf-8"); initialize_engagement(normalization_engagement, "2026-07-10T00:13:15Z")
        empty_argv = collect_preflight(normalization_engagement, preflight_id="preflight-empty-argv", mode="package", target=package_fixture, expected_identity=package_digest, runtime=runtime_fixture, reproduction_argv=[], operator_id="Operator Name!", recorded_at="2026-07-10T00:13:16Z", operator_redaction_attested=True)
        unattested = collect_preflight(normalization_engagement, preflight_id="preflight-unattested", mode="package", target=package_fixture, expected_identity=package_digest, runtime=runtime_fixture, reproduction_argv=[str(runtime_fixture), "-c", "pass"], operator_id="Operator Name!", recorded_at="2026-07-10T00:13:17Z")
        checks.append(("empty argv records blocked, redaction requires attestation, and operator labels normalize once", empty_argv["status"] == "blocked" and empty_argv["collector"]["reproduction_argv"] == [] and unattested["status"] == "blocked" and empty_argv["provenance"]["actor"]["id"] == "Operator-Name", str((empty_argv, unattested))))
        secret_engagement = root / "secret-artifact"; shutil.copytree(engagement, secret_engagement); secret_file = secret_engagement / "evidence" / "secret.txt"; secret_file.parent.mkdir(exist_ok=True); secret_file.write_text("Authorization: Bearer not-a-real-token-value-123456\n")
        secret_blocked = False
        try:
            _register_legacy_artifact(secret_engagement, secret_file, {"schema_version": 1, "artifact_id": "artifact-secret", "engagement_id": engagement.name, "created_at": "2026-07-10T00:13:13Z", "producer": {"role": "operator", "id": "operator-selftest"}, "acquisition_method": "operator", "target_refs": [], "environment_ref": "preflight-selftest", "sensitivity": "secret", "redaction_status": "pending", "contains_executable_capability": False, "advisory_zone": "unknown", "escalation_confirmation_event_ref": None, "cleanup_obligation_ref": None, "supersedes_artifact_id": None, "media_type": "text/plain"})
        except RecordError as exc:
            secret_blocked = exc.code == "secret_shaped_artifact_content" and all("not-a-real" not in str(item) for item in exc.details)
        checks.append(("secret-shaped artifact content is rejected without echoing the value", secret_blocked, "secret-shaped artifact accepted or disclosed"))

        evidence_file = engagement / "evidence" / "artifact.txt"; evidence_file.write_text("benign evidence\n", encoding="utf-8")
        artifact_metadata = {"schema_version": 1, "artifact_id": "artifact-selftest", "engagement_id": engagement.name, "created_at": "2026-07-10T00:15:00Z", "producer": {"role": "operator", "id": "operator-selftest"}, "acquisition_method": "operator", "target_refs": [], "environment_ref": "preflight-selftest", "sensitivity": "internal", "redaction_status": "not_needed", "contains_executable_capability": False, "advisory_zone": "clear_local", "escalation_confirmation_event_ref": None, "cleanup_obligation_ref": None, "supersedes_artifact_id": None, "media_type": "text/plain"}
        registered = _register_legacy_artifact(engagement, evidence_file, artifact_metadata)
        checks.append(("register-artifact derives and commits path/digest/size", registered["sha256"] == sha256_file(evidence_file) and reduce_engagement(engagement)["artifact_count"] == 1, str(registered)))
        artifact_boundary = (engagement / "artifacts.jsonl").read_bytes(); duplicate_metadata = json.loads(json.dumps(artifact_metadata)); duplicate_metadata["artifact_id"] = "artifact-duplicate-path"; duplicate_metadata["created_at"] = "2026-07-10T00:15:01Z"
        duplicate_registration_rolled_back = False
        try:
            _register_legacy_artifact(engagement, evidence_file, duplicate_metadata)
        except RecordError as exc:
            duplicate_registration_rolled_back = exc.code == "duplicate_artifact_path"
        checks.append(("artifact append rolls back when prospective reduction rejects", duplicate_registration_rolled_back and (engagement / "artifacts.jsonl").read_bytes() == artifact_boundary, "rejected artifact remained committed"))

        def attempt_proposal(attempt_id: str, recorded_at: str, kind: str, assessment: str, statement: str, control_of: list[str]) -> dict:
            return {"schema_version": 2, "attempt_id": attempt_id, "engagement_id": engagement.name, "recorded_at": recorded_at, "actor": {"role": "hunter", "id": "hunter-selftest"}, "provenance": {"actor": {"role": "hunter", "id": "hunter-selftest"}, "provider": "selftest", "model": "semantic-researcher", "prompt_version": "decision5-selftest", "tool_versions": ["source-inspection-v1"], "card_versions": ["card-selftest"]}, "scope_hash": snapshot["scope_hash"], "environment_ref": "preflight-selftest", "escalation_confirmation_event_ref": None, "hypothesis_ref": "hypothesis-h1", "experiment_ref": "event-hypothesis-running", "surface": "owned local fixture", "action_summary": statement, "redaction_attestation": True, "observation": {"source": "source_inspection", "statement": statement}, "evidence_refs": ["artifact-selftest"], "kind": kind, "control_of": control_of, "assessment": assessment, "contamination": {"status": "none_observed", "sources": [], "note": ""}, "cost": {"wall_seconds": 1, "model_seconds": 0, "tool_seconds": 1, "target_calls": 0, "model_calls": 0, "input_tokens": None, "output_tokens": None, "cost_usd": None, "human_review_seconds": 0}}
        attempt_specs = [
            ("attempt-primary", "2026-07-10T00:15:10Z", "primary", "suspected_signal", "Primary trace reaches the bounded missing guard.", []),
            ("attempt-negative", "2026-07-10T00:15:11Z", "negative_control", "no_signal", "Matched guarded sibling does not exhibit the signal.", ["attempt-primary"]),
            ("attempt-positive", "2026-07-10T00:15:12Z", "positive_control", "suspected_signal", "Owned known-positive fixture emits the expected marker.", ["attempt-primary"]),
            ("attempt-replay", "2026-07-10T00:15:13Z", "replay", "suspected_signal", "Fresh-state replay reproduces the bounded trace.", ["attempt-primary"]),
        ]
        for spec in attempt_specs:
            append_attempt(engagement, attempt_proposal(*spec))
        proof_state = reduce_engagement(engagement)
        checks.append(("baseline evidence→primary→matched controls→fresh replay is structured and linked", proof_state["attempt_count"] == 4 and [item["kind"] for item in read_ledger(engagement, "attempt")] == ["primary", "negative_control", "positive_control", "replay"], str(proof_state["attempt_count"])))

        supported_negative = root / "supported-negative"; shutil.copytree(engagement, supported_negative)
        exhausted = base_event(event_id="event-hypothesis-exhausted", engagement_id=engagement.name, recorded_at="2026-07-10T00:15:14Z", actor_role="orchestrator", actor_id="orchestrator-selftest", event_type="hypothesis.status_changed", rationale="Matched controls and fresh replay exhaust the bounded mechanism without manufacturing a finding.", payload={"hypothesis_id": "hypothesis-h1", "status": "exhausted", "reason": "matched controls refute the bounded path", "experiment_refs": ["attempt-primary", "attempt-replay"], "control_refs": ["attempt-negative", "attempt-positive"], "supporting_evidence_refs": ["artifact-selftest"], "conflicting_evidence_refs": ["attempt-negative"], "disposition_rationale": "The primary anomaly does not survive the matched guarded sibling while detector and replay controls are healthy.", "unresolved_questions": [], "next_route": None}, evidence_refs=["attempt-primary", "attempt-negative", "attempt-positive", "attempt-replay", "artifact-selftest"], state_changes=[{"dimension": "search", "entity_id": "hypothesis-h1", "previous": "running", "current": "exhausted"}]); append_event(supported_negative, exhausted)
        negative_review = {"schema_version": 1, "review_id": "review-coverage-negative", "engagement_id": engagement.name, "review_type": "coverage", "proposed_finding_id": None, "entity_ref": engagement.name, "finding_revision": None, "recorded_at": "2026-07-10T00:15:15Z", "input_refs": ["attempt-primary", "attempt-negative", "attempt-positive", "attempt-replay"], "input_hash": "sha256:" + "5" * 64, "evidence_refs": ["attempt-primary", "attempt-negative", "attempt-positive", "attempt-replay", "artifact-selftest"], "conflicting_evidence": [], "independence": {"reviewer_id": "coverage-reviewer", "reviewer_model": "cold-reviewer", "reviewer_run_id": "run-coverage-negative", "originating_run_id": "event-hypothesis-running", "fresh_context": True, "prior_verdict_visible": False, "disconfirming_objective": "Find an omitted materially distinct path."}, "verdict": "coverage_dry", "rationale": "The bounded hypothesis is decisively exhausted by healthy matched controls.", "corrections": [], "required_next_actions": [], "bounded_space": "One owned-fixture branch and matched guarded sibling.", "hypothesis_dispositions": [{"hypothesis_ref": "hypothesis-h1", "status": "exhausted", "rationale": "Matched negative plus healthy positive and replay controls exhaust the route."}], "omitted_branch_challenge": "Cold review found no unmodeled sibling in the declared bounded space.", "residual_uncertainty": ["future versions not assessed"]}
        negative_review["input_hash"] = compute_review_input_hash(supported_negative, negative_review, build_reference_index(supported_negative))
        negative_review_path = supported_negative / "reviews" / "coverage-negative.json"; negative_review_path.write_bytes(canonical_json_bytes(negative_review))
        negative_review_commit = base_event(event_id="event-coverage-negative-commit", engagement_id=engagement.name, recorded_at="2026-07-10T00:15:16Z", actor_role="operator", actor_id="operator-selftest", event_type="record.committed", rationale="Commit cold negative coverage review.", payload={"record_path": "reviews/coverage-negative.json", "record_digest": sha256_file(negative_review_path), "record_type": "review", "record_id": "review-coverage-negative", "record_revision": None}); append_event(supported_negative, negative_review_commit)
        negative_review_event = base_event(event_id="event-coverage-negative-reviewed", engagement_id=engagement.name, recorded_at="2026-07-10T00:15:17Z", actor_role="reviewer", actor_id="coverage-reviewer", event_type="review.coverage_completed", rationale="Cold reviewer closes every material hypothesis in the bounded negative engagement.", payload={"review_type": "coverage", "verdict": "coverage_dry"}, review_refs=["review-coverage-negative"]); append_event(supported_negative, negative_review_event)
        negative_dry = base_event(event_id="event-coverage-negative-dry", engagement_id=engagement.name, recorded_at="2026-07-10T00:15:18Z", actor_role="operator", actor_id="operator-selftest", event_type="coverage.status_changed", rationale="Supported negative reaches coverage dry without a finding.", payload={"entity_id": engagement.name, "status": "coverage_dry", "coverage_review_ref": "event-coverage-negative-reviewed"}, entity_refs=["event-coverage-negative-reviewed"], state_changes=[{"dimension": "coverage", "entity_id": engagement.name, "previous": "blocked", "current": "coverage_dry"}]); append_event(supported_negative, negative_dry)
        negative_state = reduce_engagement(supported_negative)
        checks.append(("well-supported negative reaches cold-reviewed coverage_dry without a finding", negative_state["coverage"] == "coverage_dry" and negative_state["hypotheses"]["hypothesis-h1"]["status"] == "exhausted" and negative_state["findings"] == {}, str(negative_state)))
        late_payload = json.loads(json.dumps(hypothesis["payload"])); late_payload["hypothesis_id"] = "hypothesis-after-dry"
        late_hypothesis = base_event(event_id="event-hypothesis-after-dry", engagement_id=engagement.name, recorded_at="2026-07-10T00:15:18.500000Z", actor_role="orchestrator", actor_id="orchestrator-selftest", event_type="hypothesis.created", rationale="Must explicitly reopen coverage before introducing new search material.", payload=late_payload, entity_refs=["candidate-c1"], state_changes=[{"dimension": "search", "entity_id": "hypothesis-after-dry", "previous": None, "current": "queued"}])
        late_hypothesis_blocked = False
        try: append_event(supported_negative, late_hypothesis)
        except RecordError as exc: late_hypothesis_blocked = exc.code == "search_material_after_closed_coverage"
        checks.append(("new hypotheses cannot preserve a false coverage_dry state", late_hypothesis_blocked, "hypothesis appended after dry coverage without reopening"))
        reopen_prior = base_event(event_id="event-prior-reopens-negative", engagement_id=engagement.name, recorded_at="2026-07-10T00:15:19Z", actor_role="operator", actor_id="operator-selftest", event_type="operator_prior.recorded", rationale="A strong operator prior reopens bounded search but supplies no claim evidence.", payload={"prior_id": "prior-reopen-negative", "prior_statement": "One materially distinct parser branch was not represented.", "strength": "strong", "reason": "operator target-model knowledge", "reopen_hypothesis_id": "hypothesis-h1", "reopening_condition": "Test the newly identified materially distinct parser branch."}, entity_refs=["hypothesis-h1"], state_changes=[{"dimension": "search", "entity_id": "hypothesis-h1", "previous": "exhausted", "current": "queued"}, {"dimension": "coverage", "entity_id": engagement.name, "previous": "coverage_dry", "current": "active"}]); append_event(supported_negative, reopen_prior)
        reopened_negative = reduce_engagement(supported_negative)
        checks.append(("strong operator prior reopens search and coverage without proving a claim", reopened_negative["coverage"] == "active" and reopened_negative["hypotheses"]["hypothesis-h1"]["status"] == "queued" and reopened_negative["findings"] == {}, str(reopened_negative)))
        telemetry = export_telemetry(supported_negative); telemetry_score = score_telemetry(telemetry)
        telemetry_states = telemetry["candidates"][0]["funnel_states"]
        checks.append(("complete-funnel export retains eligible, selected, and reopened states", telemetry["denominator"] == {"eligible_count": 1, "exported_count": 1, "complete": True} and all(value in telemetry_states for value in ("eligible", "selected", "reopened")), str(telemetry)))
        checks.append(("missing independent outcomes remains telemetry, never fake calibration", telemetry["classification"] == "telemetry" and "missing_independent_outcome" in telemetry["calibration_eligibility"]["reasons"] and telemetry_score["brier_score"] is None and telemetry_score["automatic_actions"] == [] and telemetry_score["bandit_enabled"] is False, str(telemetry_score)))

        artifact_tampered = root / "artifact-tampered"; shutil.copytree(engagement, artifact_tampered); (artifact_tampered / "evidence" / "artifact.txt").write_text("changed\n")
        artifact_tamper_caught = False
        try:
            reduce_engagement(artifact_tampered)
        except RecordError as exc:
            artifact_tamper_caught = exc.code == "artifact_file_digest_mismatch"
        checks.append(("modified registered artifact fails reduction", artifact_tamper_caught, "artifact modification accepted"))
        artifact_orphan = root / "artifact-orphan"; shutil.copytree(engagement, artifact_orphan); (artifact_orphan / "evidence" / "orphan.txt").write_text("orphan\n")
        artifact_orphan_caught = False
        try:
            reduce_engagement(artifact_orphan)
        except RecordError as exc:
            artifact_orphan_caught = exc.code == "orphan_artifact_file"
        checks.append(("orphan evidence file fails reduction", artifact_orphan_caught, "orphan artifact accepted"))

        reviews_dir = engagement / "reviews"; reviews_dir.mkdir(exist_ok=True)
        def claim_review(review_id: str, recorded_at: str, verdict: str, entity_ref: str, finding_revision: int | None, origin_run: str) -> dict:
            return {"schema_version": 1, "review_id": review_id, "engagement_id": engagement.name, "review_type": "claim_adjudication", "proposed_finding_id": "F-selftest", "entity_ref": entity_ref, "finding_revision": finding_revision, "recorded_at": recorded_at, "input_refs": ["attempt-primary", "attempt-negative", "attempt-positive", "attempt-replay", "preflight-selftest"], "input_hash": "sha256:" + ("3" if finding_revision is None else "4") * 64, "evidence_refs": ["attempt-primary", "attempt-negative", "attempt-positive", "attempt-replay", "artifact-selftest"], "conflicting_evidence": [], "independence": {"reviewer_id": "reviewer-selftest", "reviewer_model": "independent-reviewer", "reviewer_run_id": f"run-{review_id}", "reviewer_session_id": f"session-{review_id}", "originating_run_id": origin_run, "fresh_context": True, "prior_verdict_visible": False, "disconfirming_objective": "Refute the bounded mechanism and control linkage."}, "verdict": verdict, "rationale": "Primary trace, matched controls, and replay support only the bounded claim.", "corrections": [], "required_next_actions": ["preserve bounded language"], "control_applicability": [{"attempt_ref": "attempt-negative", "applicable": True, "rationale": "Matched negative branch."}, {"attempt_ref": "attempt-positive", "applicable": True, "rationale": "Known-positive detector check."}, {"attempt_ref": "attempt-replay", "applicable": True, "rationale": "Fresh-state replay."}]}
        review1_path = reviews_dir / "review-claim-1.json"; review1 = claim_review("review-claim-1", "2026-07-10T00:15:20Z", "supported", "F-selftest", None, "event-hypothesis-running"); review1["input_hash"] = compute_review_input_hash(engagement, review1, build_reference_index(engagement)); review1_path.write_bytes(canonical_json_bytes(review1))
        review1_commit = base_event(event_id="event-review-claim-1-commit", engagement_id=engagement.name, recorded_at="2026-07-10T00:15:21Z", actor_role="operator", actor_id="operator-selftest", event_type="record.committed", rationale="Commit independent claim review.", payload={"record_path": "reviews/review-claim-1.json", "record_digest": sha256_file(review1_path), "record_type": "review", "record_id": "review-claim-1", "record_revision": None}); append_event(engagement, review1_commit)
        adjudication1 = base_event(event_id="event-claim-supported", engagement_id=engagement.name, recorded_at="2026-07-10T00:15:22Z", actor_role="reviewer", actor_id="reviewer-selftest", event_type="claim.adjudicated", rationale="Independent review supports the bounded primitive.", payload={"entity_id": "F-selftest", "status": "supported", "review_ref": "review-claim-1", "review_digest": sha256_file(review1_path)}, review_refs=["review-claim-1"], state_changes=[{"dimension": "claim", "entity_id": "F-selftest", "previous": None, "current": "supported"}]); append_event(engagement, adjudication1)

        suite_records = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "engagement-records" / "suite.json").read_text())["cases"]
        finding1 = json.loads(json.dumps(next(case["record"] for case in suite_records if case["id"] == "finding-v3-rich")))
        finding1.update({"finding_id": "F-selftest", "engagement_id": engagement.name, "revision": 1, "supersedes_revision": None, "recorded_at": "2026-07-10T00:15:23Z", "change_reason": "Initial bounded adjudication.", "claim_state": "supported"})
        finding1["scope_provenance"].update({"scope_hash": snapshot["scope_hash"], "environment_ref": "preflight-selftest", "target_refs": []}); finding1["scope_provenance"]["provenance"]["actor"] = {"role": "reviewer", "id": "reviewer-selftest"}
        finding1["adjudication"] = {"review_ref": "review-claim-1", "justification": "Independent review bound primary evidence, both controls, and replay."}; finding1["search_linkage"] = {"candidate_refs": ["candidate-c1"], "hypothesis_refs": ["hypothesis-h1"]}
        for claim_name in ("mechanism", "reachability"): finding1["claims"][claim_name]["evidence_refs"] = ["artifact-selftest"]
        for impact in finding1["claims"]["impact_claims"]: impact["evidence_refs"] = ["artifact-selftest"]
        proof = finding1["proof"]; proof.update({"primary_attempt_refs": ["attempt-primary"], "negative_control_refs": ["attempt-negative"], "positive_control_refs": ["attempt-positive"], "replay_refs": ["attempt-replay"], "evidence_refs": ["artifact-selftest"], "control_applicability": {"negative": "required", "positive": "required", "replay": "required", "rationale": "Matched negative, known-positive, and fresh replay are all required."}})
        for mapping in proof["claim_proofs"]: mapping.update({"attempt_refs": ["attempt-primary"], "artifact_refs": ["artifact-selftest"], "control_refs": ["attempt-negative", "attempt-positive"], "replay_refs": ["attempt-replay"]})
        finding_dir = engagement / "findings" / "F-selftest"; finding_dir.mkdir(parents=True); finding1_path = finding_dir / "rev-1.json"; finding1_path.write_bytes(canonical_json_bytes(finding1))
        finding1_commit = base_event(event_id="event-finding-1-commit", engagement_id=engagement.name, recorded_at="2026-07-10T00:15:24Z", actor_role="operator", actor_id="operator-selftest", event_type="record.committed", rationale="Commit finding revision one.", payload={"record_path": "findings/F-selftest/rev-1.json", "record_digest": sha256_file(finding1_path), "record_type": "finding-v3", "record_id": "F-selftest", "record_revision": 1}); append_event(engagement, finding1_commit)
        filing1 = base_event(event_id="event-finding-revision-1", engagement_id=engagement.name, recorded_at="2026-07-10T00:15:25Z", actor_role="operator", actor_id="operator-selftest", event_type="finding.revised", rationale="Operator files the independently supported bounded claim.", payload={"finding_id": "F-selftest", "finding_revision": 1, "status": "supported", "finding_digest": sha256_file(finding1_path), "adjudication_review_ref": "review-claim-1", "adjudication_review_digest": sha256_file(review1_path), "adjudication_event_ref": "event-claim-supported", "supersedes_revision": None, "change_reason": "Initial bounded adjudication."}, entity_refs=["F-selftest", "event-claim-supported"], finding_refs=["F-selftest"], review_refs=["review-claim-1"]); append_event(engagement, filing1)

        review2_path = reviews_dir / "review-claim-2.json"; review2 = claim_review("review-claim-2", "2026-07-10T00:15:26Z", "confirmed", "F-selftest", 1, "event-hypothesis-running"); review2["input_refs"].append("F-selftest"); review2["input_hash"] = compute_review_input_hash(engagement, review2, build_reference_index(engagement)); review2_path.write_bytes(canonical_json_bytes(review2))
        review2_commit = base_event(event_id="event-review-claim-2-commit", engagement_id=engagement.name, recorded_at="2026-07-10T00:15:27Z", actor_role="operator", actor_id="operator-selftest", event_type="record.committed", rationale="Commit fresh confirmation review.", payload={"record_path": "reviews/review-claim-2.json", "record_digest": sha256_file(review2_path), "record_type": "review", "record_id": "review-claim-2", "record_revision": None}); append_event(engagement, review2_commit)
        adjudication2 = base_event(event_id="event-claim-confirmed", engagement_id=engagement.name, recorded_at="2026-07-10T00:15:28Z", actor_role="reviewer", actor_id="reviewer-selftest", event_type="claim.adjudicated", rationale="Fresh independent review confirms the bounded primitive.", payload={"entity_id": "F-selftest", "status": "confirmed", "review_ref": "review-claim-2", "review_digest": sha256_file(review2_path)}, review_refs=["review-claim-2"], state_changes=[{"dimension": "claim", "entity_id": "F-selftest", "previous": "supported", "current": "confirmed"}]); append_event(engagement, adjudication2)
        finding2 = json.loads(json.dumps(finding1)); finding2.update({"revision": 2, "supersedes_revision": 1, "recorded_at": "2026-07-10T00:15:29Z", "change_reason": "Fresh independent replay review confirmed the bounded primitive.", "claim_state": "confirmed"}); finding2["adjudication"] = {"review_ref": "review-claim-2", "justification": "Fresh reviewer confirmed the exact bounded claim tuple."}
        finding2_path = finding_dir / "rev-2.json"; finding2_path.write_bytes(canonical_json_bytes(finding2))
        finding2_commit = base_event(event_id="event-finding-2-commit", engagement_id=engagement.name, recorded_at="2026-07-10T00:15:29Z", actor_role="operator", actor_id="operator-selftest", event_type="record.committed", rationale="Commit contiguous finding revision two.", payload={"record_path": "findings/F-selftest/rev-2.json", "record_digest": sha256_file(finding2_path), "record_type": "finding-v3", "record_id": "F-selftest", "record_revision": 2}); append_event(engagement, finding2_commit)
        filing2 = base_event(event_id="event-finding-revision-2", engagement_id=engagement.name, recorded_at="2026-07-10T00:15:30Z", actor_role="operator", actor_id="operator-selftest", event_type="finding.revised", rationale="Operator files contiguous confirmed revision without rewriting revision one.", payload={"finding_id": "F-selftest", "finding_revision": 2, "status": "confirmed", "finding_digest": sha256_file(finding2_path), "adjudication_review_ref": "review-claim-2", "adjudication_review_digest": sha256_file(review2_path), "adjudication_event_ref": "event-claim-confirmed", "supersedes_revision": 1, "change_reason": "Fresh independent replay review confirmed the bounded primitive."}, entity_refs=["F-selftest", "event-claim-confirmed"], finding_refs=["F-selftest"], review_refs=["review-claim-2"]); append_event(engagement, filing2)
        chain_hypothesis = base_event(event_id="event-hypothesis-chain", engagement_id=engagement.name, recorded_at="2026-07-10T00:15:31Z", actor_role="orchestrator", actor_id="orchestrator-selftest", event_type="hypothesis.created", rationale="Confirmed primitive opens bounded chainability search without broadening the finding.", payload={"hypothesis_id": "hypothesis-chain", "origin_type": "confirmed_primitive", "origin_ref": "F-selftest", "hypothesis_statement": "The confirmed local primitive may compose with one adjacent owned-fixture transition.", "suspected_invariant": "Composition must not cross the adjacent trust boundary.", "trust_boundary": "confirmed primitive to adjacent owned state", "attacker_path": ["confirmed primitive", "adjacent transition"], "impact_ceiling": "owned fixture composition only", "bounded_space": "One adjacent transition.", "lens_ids": ["composition"], "card_ids": ["card-selftest"], "expected_confirming_evidence": [{"evidence_type": "trace", "description": "end-to-end adjacent trace", "required": True}], "decisive_falsifiers": ["adjacent transition rejects primitive output"], "cost_estimate": zero_cost, "constraints": ["no target contact"], "next_experiment": "trace adjacent owned transition", "completion_criteria": ["trace or decisive rejection"], "status": "queued"}, entity_refs=["F-selftest"], finding_refs=["F-selftest"], state_changes=[{"dimension": "search", "entity_id": "hypothesis-chain", "previous": None, "current": "queued"}]); append_event(engagement, chain_hypothesis)
        finding_state = reduce_engagement(engagement)
        checks.append(("revisioned finding history and active chainability search coexist", finding_state["findings"]["F-selftest"]["revision"] == 2 and finding_state["findings"]["F-selftest"]["status"] == "confirmed" and finding_state["hypotheses"]["hypothesis-chain"]["status"] == "queued" and finding1_path.read_bytes() == canonical_json_bytes(finding1), str(finding_state["findings"])))
        forged_filing = copy.deepcopy(filing2); forged_filing["event_id"] = "event-finding-forged-operator"; forged_filing["recorded_at"] = "2026-07-10T00:15:32Z"; forged_filing["actor"] = {"role": "operator", "id": "other-operator"}; forged_filing["provenance"]["actor"] = forged_filing["actor"]
        before_forged = (engagement / "events.jsonl").read_bytes(); forged_blocked = False
        try:
            append_event(engagement, forged_filing)
        except RecordError as exc:
            forged_blocked = exc.code == "finding_filing_not_scope_operator"
        checks.append(("only the active signed-scope operator can file a finding revision", forged_blocked and (engagement / "events.jsonl").read_bytes() == before_forged, "forged operator filing appended"))
        skip_revision = copy.deepcopy(filing2); skip_revision["event_id"] = "event-finding-revision-4"; skip_revision["recorded_at"] = "2026-07-10T00:15:33Z"; skip_revision["payload"]["finding_revision"] = 4; skip_revision["payload"]["supersedes_revision"] = 2
        before_skip = (engagement / "events.jsonl").read_bytes(); skip_blocked = False
        try:
            append_event(engagement, skip_revision)
        except RecordError as exc:
            skip_blocked = exc.code == "finding_revision_not_contiguous"
        checks.append(("finding revision cannot skip history", skip_blocked and (engagement / "events.jsonl").read_bytes() == before_skip, "skipped revision appended"))

        tuple_hash = claim_tuple_hash(finding2)
        regrade = {"schema_version": 1, "review_id": "review-regrade-selftest", "engagement_id": engagement.name, "review_type": "regrade", "proposed_finding_id": "F-selftest", "recorded_at": "2026-07-10T00:15:34Z", "entity_ref": "F-selftest", "finding_revision": 2, "input_refs": ["F-selftest", "attempt-primary", "attempt-negative", "attempt-replay"], "input_hash": "sha256:" + "0" * 64, "evidence_refs": ["attempt-primary", "attempt-negative", "attempt-replay", "artifact-selftest"], "rationale": "Fresh regrade identifies a distinct adjacent composition that still needs evidence.", "conflicting_evidence": [], "verdict": "escalation_found", "corrections": [], "required_next_actions": ["collect evidence before revising impact"], "independence": {"reviewer_id": "regrade-reviewer", "reviewer_run_id": "run-regrade-selftest", "reviewer_model": "independent-regrader", "fresh_context": True, "prior_verdict_visible": False, "disconfirming_objective": "Refute the adjacent composition.", "originating_run_id": "event-finding-revision-2"}, "control_applicability": [{"attempt_ref": "attempt-negative", "applicable": True, "rationale": "Matched negative remains applicable."}], "claim_tuple_hash": tuple_hash, "replay_freshness": [{"attempt_ref": "attempt-replay", "fresh": True, "rationale": "Fresh-state replay."}], "prior_review_run_ids": ["run-review-claim-2"], "escalation_claims": ["Adjacent owned transition may compose with the confirmed primitive."], "blocked_reason": None}
        regrade["input_hash"] = compute_review_input_hash(engagement, regrade, build_reference_index(engagement)); regrade_path = reviews_dir / "regrade-selftest.json"; regrade_path.write_bytes(canonical_json_bytes(regrade))
        regrade_commit = base_event(event_id="event-regrade-commit", engagement_id=engagement.name, recorded_at="2026-07-10T00:15:35Z", actor_role="operator", actor_id="operator-selftest", event_type="record.committed", rationale="Commit fresh regrade review.", payload={"record_path": "reviews/regrade-selftest.json", "record_digest": sha256_file(regrade_path), "record_type": "review", "record_id": "review-regrade-selftest", "record_revision": None}); append_event(engagement, regrade_commit)
        regrade_event = base_event(event_id="event-regrade-escalation", engagement_id=engagement.name, recorded_at="2026-07-10T00:15:36Z", actor_role="reviewer", actor_id="regrade-reviewer", event_type="review.regrade_completed", rationale="Escalation is a search obligation, not a finding claim.", payload={"review_ref": "review-regrade-selftest", "finding_id": "F-selftest", "finding_revision": 2, "verdict": "escalation_found", "claim_tuple_hash": tuple_hash}, review_refs=["review-regrade-selftest"], finding_refs=["F-selftest"]); append_event(engagement, regrade_event)
        premature_revision = copy.deepcopy(filing2); premature_revision["event_id"] = "event-premature-escalation-revision"; premature_revision["recorded_at"] = "2026-07-10T00:15:37Z"; premature_revision["payload"]["finding_revision"] = 3; premature_revision["payload"]["supersedes_revision"] = 2
        premature_blocked = False
        try:
            append_event(engagement, premature_revision)
        except RecordError as exc:
            premature_blocked = exc.code == "escalation_evidence_not_collected"
        checks.append(("regrade escalation routes to evidence collection before finding revision", premature_blocked, "escalation directly revised finding"))
        escalation_hypothesis = base_event(event_id="event-hypothesis-escalation", engagement_id=engagement.name, recorded_at="2026-07-10T00:15:38Z", actor_role="orchestrator", actor_id="orchestrator-selftest", event_type="hypothesis.created", rationale="Route reviewer escalation into bounded evidence collection.", payload={"hypothesis_id": "hypothesis-escalation", "origin_type": "reviewer_challenge", "origin_ref": "event-regrade-escalation", "hypothesis_statement": "The adjacent owned transition composes with the confirmed primitive.", "suspected_invariant": "Primitive output must not cross the adjacent boundary.", "trust_boundary": "primitive to adjacent owned transition", "attacker_path": ["primitive", "adjacent transition"], "impact_ceiling": "owned fixture only", "bounded_space": "One adjacent transition.", "lens_ids": ["composition"], "card_ids": ["card-selftest"], "expected_confirming_evidence": [{"evidence_type": "trace", "description": "end-to-end composition trace", "required": True}], "decisive_falsifiers": ["adjacent transition rejects primitive output"], "cost_estimate": zero_cost, "constraints": ["offline fixture"], "next_experiment": "trace composition", "completion_criteria": ["trace or decisive rejection"], "status": "queued"}, entity_refs=["event-regrade-escalation"], finding_refs=["F-selftest"], state_changes=[{"dimension": "search", "entity_id": "hypothesis-escalation", "previous": None, "current": "queued"}]); append_event(engagement, escalation_hypothesis)
        escalation_evidence_path = engagement / "evidence" / "escalation.txt"; escalation_evidence_path.write_text("new bounded escalation trace\n", encoding="utf-8")
        escalation_artifact = json.loads(json.dumps(artifact_metadata)); escalation_artifact.update({"artifact_id": "artifact-escalation", "created_at": "2026-07-10T00:15:40.500000Z", "acquisition_method": "source_inspection"}); _register_legacy_artifact(engagement, escalation_evidence_path, escalation_artifact)
        for status, previous, timestamp in (("selected", "queued", "2026-07-10T00:15:39Z"), ("running", "selected", "2026-07-10T00:15:40Z"), ("held", "running", "2026-07-10T00:15:41Z")):
            support = ["artifact-escalation"] if status == "held" else []
            transition = base_event(event_id=f"event-escalation-{status}", engagement_id=engagement.name, recorded_at=timestamp, actor_role="orchestrator", actor_id="orchestrator-selftest", event_type="hypothesis.status_changed", rationale=f"Escalation hypothesis {status}.", payload={"hypothesis_id": "hypothesis-escalation", "status": status, "reason": "bounded escalation evidence route", "experiment_refs": ["attempt-primary"] if status == "held" else [], "control_refs": ["attempt-negative"] if status == "held" else [], "supporting_evidence_refs": support, "conflicting_evidence_refs": [], "disposition_rationale": "Bounded evidence route recorded without changing finding truth.", "unresolved_questions": ["composition impact remains unproven"] if status == "held" else [], "next_route": "independent composition trace"}, evidence_refs=support, state_changes=[{"dimension": "search", "entity_id": "hypothesis-escalation", "previous": previous, "current": status}]); append_event(engagement, transition)

        def poc_review(review_id: str, recorded_at: str, reviewer_id: str, run_id: str, verdict: str, prior_runs: list[str], mismatches: list[str], reward_indicators: list[str]) -> dict:
            value = {"schema_version": 1, "review_id": review_id, "engagement_id": engagement.name, "review_type": "pocinator", "proposed_finding_id": "F-selftest", "recorded_at": recorded_at, "entity_ref": "F-selftest", "finding_revision": 2, "input_refs": ["F-selftest", "artifact-selftest"], "input_hash": "sha256:" + "0" * 64, "evidence_refs": ["artifact-selftest"], "rationale": f"Pocinator outcome: {verdict}.", "conflicting_evidence": [], "verdict": verdict, "corrections": mismatches, "required_next_actions": ["route back without changing finding truth"] if verdict != "verified" else [], "independence": {"reviewer_id": reviewer_id, "reviewer_run_id": run_id, "reviewer_model": "pocinator-reviewer", "fresh_context": True, "prior_verdict_visible": False, "disconfirming_objective": "Break the exact claim tuple and composition.", "originating_run_id": "event-finding-revision-2"}, "claim_tuple_hash": tuple_hash, "high_value": True, "proof_profile_ref": "artifact-selftest", "claim_mismatches": mismatches, "reward_hack_indicators": reward_indicators, "module_level_only": True, "end_to_end_composition_reviewed": False, "blocked_reason": None, "prior_review_run_ids": prior_runs}
            value["input_hash"] = compute_review_input_hash(engagement, value, build_reference_index(engagement)); return value
        poc_specs = [
            ("review-poc-mismatch", "2026-07-10T00:15:42Z", "poc-reviewer", "run-poc-mismatch", "claim_mismatch", ["run-regrade-selftest"], ["Proof demonstrates only the module-level mechanism."], []),
            ("review-poc-reward-1", "2026-07-10T00:15:45Z", "poc-reward-reviewer-1", "run-poc-reward-1", "reward_hacked", ["run-poc-mismatch"], [], ["Evaluator marker without end-to-end proof."]),
            ("review-poc-reward-2", "2026-07-10T00:15:48Z", "poc-reward-reviewer-2", "run-poc-reward-2", "reward_hacked", ["run-poc-reward-1"], [], ["Independent reviewer confirms reward-only optimization."]),
        ]
        mismatch_state = None
        for offset, spec in enumerate(poc_specs):
            review_value = poc_review(*spec); review_path = reviews_dir / f"{spec[0]}.json"; review_path.write_bytes(canonical_json_bytes(review_value))
            commit_time = ["2026-07-10T00:15:43Z", "2026-07-10T00:15:46Z", "2026-07-10T00:15:49Z"][offset]; event_time = ["2026-07-10T00:15:44Z", "2026-07-10T00:15:47Z", "2026-07-10T00:15:50Z"][offset]
            commit = base_event(event_id=f"event-{spec[0]}-commit", engagement_id=engagement.name, recorded_at=commit_time, actor_role="operator", actor_id="operator-selftest", event_type="record.committed", rationale="Commit typed Pocinator review.", payload={"record_path": f"reviews/{spec[0]}.json", "record_digest": sha256_file(review_path), "record_type": "review", "record_id": spec[0], "record_revision": None}); append_event(engagement, commit)
            reviewed = base_event(event_id=f"event-{spec[0]}", engagement_id=engagement.name, recorded_at=event_time, actor_role="reviewer", actor_id=spec[2], event_type="review.pocinator_completed", rationale="Pocinator result routes proof state only.", payload={"review_ref": spec[0], "finding_id": "F-selftest", "finding_revision": 2, "verdict": spec[4], "claim_tuple_hash": tuple_hash, "high_value": True}, review_refs=[spec[0]], finding_refs=["F-selftest"]); append_event(engagement, reviewed)
            if offset == 0: mismatch_state = reduce_engagement(engagement)
        typed_state = reduce_engagement(engagement); proof_review = typed_state["proof_reviews"]["F-selftest:r2"]
        checks.append(("claim_mismatch routes correction without refuting finding", mismatch_state is not None and mismatch_state["findings"]["F-selftest"]["status"] == "confirmed" and mismatch_state["proof_reviews"]["F-selftest:r2"]["terminal_status"] == "route_back", str(mismatch_state)))
        checks.append(("definite high-value reward_hacked requires two independent reviewers", proof_review["terminal_status"] == "second_review_confirmed" and len(proof_review["reviewer_ids"]) == 2 and typed_state["findings"]["F-selftest"]["status"] == "confirmed", str(proof_review)))
        report_manifest = generate_report(engagement, "F-selftest", 2, ["claim-mechanism", "claim-reach", "claim-impact"], [], "operator-selftest", "2026-07-10T00:15:50.500000Z")
        report_state = reduce_engagement(engagement); checks.append(("report generation binds exact finding revision, review, claims, proof matrix, and bytes", report_state["reports"][report_manifest["report_id"]]["status"] == "draft" and (engagement / report_manifest["report_path"]).is_file(), str(report_manifest)))

        correction = {"schema_version": 1, "review_id": "review-regrade-correction", "engagement_id": engagement.name, "review_type": "regrade", "proposed_finding_id": "F-selftest", "recorded_at": "2026-07-10T00:15:51Z", "entity_ref": "F-selftest", "finding_revision": 2, "input_refs": ["F-selftest", "attempt-negative", "attempt-replay"], "input_hash": "sha256:" + "0" * 64, "evidence_refs": ["attempt-negative", "attempt-replay"], "rationale": "Finding remains real but residual uncertainty must be narrowed.", "conflicting_evidence": [], "verdict": "confirmed_with_correction", "corrections": ["Narrow the residual uncertainty to future versions only."], "required_next_actions": ["file contiguous corrected revision"], "independence": {"reviewer_id": "correction-reviewer", "reviewer_run_id": "run-regrade-correction", "reviewer_model": "independent-regrader", "fresh_context": True, "prior_verdict_visible": False, "disconfirming_objective": "Find unsupported breadth in the claim.", "originating_run_id": "event-finding-revision-2"}, "control_applicability": [{"attempt_ref": "attempt-negative", "applicable": True, "rationale": "Matched negative bounds breadth."}], "claim_tuple_hash": tuple_hash, "replay_freshness": [{"attempt_ref": "attempt-replay", "fresh": True, "rationale": "Fresh replay remains valid."}], "prior_review_run_ids": ["run-regrade-selftest"], "escalation_claims": [], "blocked_reason": None}
        correction["input_hash"] = compute_review_input_hash(engagement, correction, build_reference_index(engagement)); correction_path = reviews_dir / "regrade-correction.json"; correction_path.write_bytes(canonical_json_bytes(correction))
        correction_commit = base_event(event_id="event-regrade-correction-commit", engagement_id=engagement.name, recorded_at="2026-07-10T00:15:52Z", actor_role="operator", actor_id="operator-selftest", event_type="record.committed", rationale="Commit correction regrade.", payload={"record_path": "reviews/regrade-correction.json", "record_digest": sha256_file(correction_path), "record_type": "review", "record_id": "review-regrade-correction", "record_revision": None}); append_event(engagement, correction_commit)
        correction_event = base_event(event_id="event-regrade-correction", engagement_id=engagement.name, recorded_at="2026-07-10T00:15:53Z", actor_role="reviewer", actor_id="correction-reviewer", event_type="review.regrade_completed", rationale="Correction must become a contiguous revision before closure.", payload={"review_ref": "review-regrade-correction", "finding_id": "F-selftest", "finding_revision": 2, "verdict": "confirmed_with_correction", "claim_tuple_hash": tuple_hash}, review_refs=["review-regrade-correction"], finding_refs=["F-selftest"]); append_event(engagement, correction_event)
        unresolved_correction = copy.deepcopy(filing2); unresolved_correction["event_id"] = "event-unresolved-correction"; unresolved_correction["recorded_at"] = "2026-07-10T00:15:53.500000Z"; unresolved_correction["payload"]["finding_revision"] = 3; unresolved_correction["payload"]["supersedes_revision"] = 2
        correction_blocked = False
        try:
            append_event(engagement, unresolved_correction)
        except RecordError as exc:
            correction_blocked = exc.code == "regrade_correction_not_resolved"
        checks.append(("confirmed_with_correction blocks filing until explicitly revision-bound", correction_blocked, "unresolved correction allowed finding revision"))
        review3_path = reviews_dir / "review-claim-3.json"; review3 = claim_review("review-claim-3", "2026-07-10T00:15:54Z", "confirmed", "F-selftest", 2, "event-regrade-correction"); review3["input_hash"] = compute_review_input_hash(engagement, review3, build_reference_index(engagement)); review3_path.write_bytes(canonical_json_bytes(review3))
        review3_commit = base_event(event_id="event-review-claim-3-commit", engagement_id=engagement.name, recorded_at="2026-07-10T00:15:55Z", actor_role="operator", actor_id="operator-selftest", event_type="record.committed", rationale="Commit correction adjudication.", payload={"record_path": "reviews/review-claim-3.json", "record_digest": sha256_file(review3_path), "record_type": "review", "record_id": "review-claim-3", "record_revision": None}); append_event(engagement, review3_commit)
        adjudication3 = base_event(event_id="event-claim-correction-confirmed", engagement_id=engagement.name, recorded_at="2026-07-10T00:15:56Z", actor_role="reviewer", actor_id="reviewer-selftest", event_type="claim.adjudicated", rationale="Independent review confirms corrected bounded claim.", payload={"entity_id": "F-selftest", "status": "confirmed", "review_ref": "review-claim-3", "review_digest": sha256_file(review3_path)}, review_refs=["review-claim-3"], state_changes=[{"dimension": "claim", "entity_id": "F-selftest", "previous": "confirmed", "current": "confirmed"}]); append_event(engagement, adjudication3)
        finding3 = json.loads(json.dumps(finding2)); finding3.update({"revision": 3, "supersedes_revision": 2, "recorded_at": "2026-07-10T00:15:57Z", "change_reason": "Resolve regrade correction and evidence-routed escalation.", "claim_state": "confirmed"}); finding3["claims"]["uncertainty"] = ["future versions not assessed"]; finding3["adjudication"] = {"review_ref": "review-claim-3", "justification": "Fresh review confirms the corrected bounded tuple."}
        finding3_path = finding_dir / "rev-3.json"; finding3_path.write_bytes(canonical_json_bytes(finding3)); finding3_commit = base_event(event_id="event-finding-3-commit", engagement_id=engagement.name, recorded_at="2026-07-10T00:15:57.500000Z", actor_role="operator", actor_id="operator-selftest", event_type="record.committed", rationale="Commit corrected finding revision three.", payload={"record_path": "findings/F-selftest/rev-3.json", "record_digest": sha256_file(finding3_path), "record_type": "finding-v3", "record_id": "F-selftest", "record_revision": 3}); append_event(engagement, finding3_commit)
        filing3 = base_event(event_id="event-finding-revision-3", engagement_id=engagement.name, recorded_at="2026-07-10T00:15:58Z", actor_role="operator", actor_id="operator-selftest", event_type="finding.revised", rationale="Operator files correction-bound contiguous revision.", payload={"finding_id": "F-selftest", "finding_revision": 3, "status": "confirmed", "finding_digest": sha256_file(finding3_path), "adjudication_review_ref": "review-claim-3", "adjudication_review_digest": sha256_file(review3_path), "adjudication_event_ref": "event-claim-correction-confirmed", "supersedes_revision": 2, "change_reason": "Resolve regrade correction and evidence-routed escalation.", "resolves_review_refs": ["event-regrade-escalation", "event-regrade-correction"]}, entity_refs=["F-selftest", "event-claim-correction-confirmed"], finding_refs=["F-selftest"], review_refs=["review-claim-3"]); append_event(engagement, filing3)
        corrected_state = reduce_engagement(engagement)
        checks.append(("correction review closes only through a contiguous adjudicated revision", corrected_state["findings"]["F-selftest"]["revision"] == 3 and not any(item["review_ref"] in {"event-regrade-escalation", "event-regrade-correction"} for item in corrected_state["outstanding_reviews"]), str(corrected_state["outstanding_reviews"])))
        checks.append(("finding revision makes prior report visibly historical", corrected_state["reports"][report_manifest["report_id"]]["status"] == "historical" and "revision 3" in corrected_state["reports"][report_manifest["report_id"]]["historical_reason"], str(corrected_state["reports"])))

        tuple_hash3 = claim_tuple_hash(finding3); blocked_review = json.loads(json.dumps(correction)); blocked_review.update({"review_id": "review-regrade-blocked", "recorded_at": "2026-07-10T00:15:59Z", "finding_revision": 3, "verdict": "blocked", "rationale": "Pinned proof environment is unavailable; truth remains unchanged.", "corrections": [], "required_next_actions": ["restore pinned environment"], "claim_tuple_hash": tuple_hash3, "prior_review_run_ids": ["run-review-claim-3"], "escalation_claims": [], "blocked_reason": "Pinned proof environment unavailable."}); blocked_review["independence"].update({"reviewer_id": "blocked-reviewer", "reviewer_run_id": "run-regrade-blocked", "originating_run_id": "event-finding-revision-3"}); blocked_review["input_hash"] = compute_review_input_hash(engagement, blocked_review, build_reference_index(engagement)); blocked_path = reviews_dir / "regrade-blocked.json"; blocked_path.write_bytes(canonical_json_bytes(blocked_review))
        blocked_commit = base_event(event_id="event-regrade-blocked-commit", engagement_id=engagement.name, recorded_at="2026-07-10T00:15:59.200000Z", actor_role="operator", actor_id="operator-selftest", event_type="record.committed", rationale="Commit blocked regrade.", payload={"record_path": "reviews/regrade-blocked.json", "record_digest": sha256_file(blocked_path), "record_type": "review", "record_id": "review-regrade-blocked", "record_revision": None}); append_event(engagement, blocked_commit)
        blocked_event = base_event(event_id="event-regrade-blocked", engagement_id=engagement.name, recorded_at="2026-07-10T00:15:59.500000Z", actor_role="reviewer", actor_id="blocked-reviewer", event_type="review.regrade_completed", rationale="Blocked review records no truth change.", payload={"review_ref": "review-regrade-blocked", "finding_id": "F-selftest", "finding_revision": 3, "verdict": "blocked", "claim_tuple_hash": tuple_hash3}, review_refs=["review-regrade-blocked"], finding_refs=["F-selftest"]); append_event(engagement, blocked_event)
        blocked_state = reduce_engagement(engagement); checks.append(("typed blocked regrade preserves finding truth and names blocker", blocked_state["findings"]["F-selftest"]["status"] == "confirmed" and any(item["status"] == "blocked" for item in blocked_state["outstanding_reviews"]), str(blocked_state["outstanding_reviews"])))
        current_report = generate_report(engagement, "F-selftest", 3, ["claim-mechanism", "claim-reach", "claim-impact"], [], "operator-selftest", "2026-07-10T00:15:59.600000Z")
        accept_report(engagement, current_report["report_id"], "operator-selftest", "Claims and proof links match revision three.", "2026-07-10T00:15:59.700000Z")
        submission_path = engagement / "submissions" / "F-selftest.txt"; submission_path.write_text("Operator-authored external submission for F-selftest revision 3.\n", encoding="utf-8")
        submission_id = record_submission(engagement, current_report["report_id"], submission_path, "selftest-program", "operator-selftest", "2026-07-10T00:15:59.800000Z")
        submitted_state = reduce_engagement(engagement); checks.append(("external submission remains separate, operator-authored, and reduced from events", submitted_state["reports"][current_report["report_id"]]["status"] == "submitted" and submission_id in submitted_state["submission_refs"] and submission_path.read_bytes() != (engagement / current_report["report_path"]).read_bytes(), str(submitted_state["reports"])))
        package_fixture.write_bytes(b"changed pinned package fixture\n"); changed_digest = sha256_file(package_fixture); collect_preflight(engagement, preflight_id="preflight-changed-target", mode="package", target=package_fixture, expected_identity=changed_digest, runtime=runtime_fixture, reproduction_argv=[str(Path(sys.executable).resolve()), "-c", "pass"], operator_id="operator-selftest", recorded_at="2026-07-10T00:15:59.850000Z", operator_redaction_attested=True)
        stale_attempt = attempt_proposal("attempt-stale-environment", "2026-07-10T00:15:59.900000Z", "environment_check", "no_signal", "Attempt incorrectly tries to reuse the superseded target identity.", []); stale_environment_blocked = False
        try:
            append_attempt(engagement, stale_attempt)
        except RecordError as exc:
            stale_environment_blocked = exc.code == "attempt_environment_not_active"
        checks.append(("changing target identity prevents stale preflight reuse", stale_environment_blocked and reduce_engagement(engagement)["active_environment_ref"] == "preflight-changed-target" and all(item["attempt_id"] != "attempt-stale-environment" for item in read_ledger(engagement, "attempt")), "stale preflight was reused"))

        rendered = render_claim_proof(finding2)
        checks.append(("claim-to-proof rendering binds every atomic claim and preserves inferred impact labels", tuple_hash in rendered and all(claim_id in rendered for claim_id in ("claim-mechanism", "claim-reach", "claim-impact")) and "demonstrated" in rendered, rendered))

        manifest_path = engagement / "legacy" / "migration-manifest.json"; manifest_path.parent.mkdir(exist_ok=True); manifest_path.write_bytes(canonical_json_bytes({"schema_version": 1, "migration_id": "migration-selftest", "engagement_id": engagement.name, "recorded_at": "2026-07-10T00:16:00Z", "source_inventory_hash": "sha256:" + "0" * 64, "operator": {"role": "operator", "id": "operator-selftest"}, "entries": [], "outcome_counts": {"imported": 0, "needs_review": 0, "skipped": 0, "errors": 0}}))
        commit_event = base_event(event_id="event-record-committed", engagement_id=engagement.name, recorded_at="2026-07-10T00:16:00Z", actor_role="operator", actor_id="operator-selftest", event_type="record.committed", rationale="Commit immutable self-test migration manifest.", payload={"record_path": "legacy/migration-manifest.json", "record_digest": sha256_file(manifest_path), "record_type": "migration-manifest", "record_id": "migration-selftest", "record_revision": None})
        append_event(engagement, commit_event)
        checks.append(("record.committed binds an existing immutable file digest", reduce_engagement(engagement)["last_event_id"] == "event-record-committed", "committed file not reducible"))
        missing_commit = base_event(event_id="event-missing-record", engagement_id=engagement.name, recorded_at="2026-07-10T00:16:30Z", actor_role="operator", actor_id="operator-selftest", event_type="record.committed", rationale="Missing committed file must fail.", payload={"record_path": "reports/missing.manifest.json", "record_digest": "sha256:" + "0" * 64, "record_type": "report-manifest", "record_id": "report-manifest-missing", "record_revision": None})
        before_missing_commit = (engagement / "events.jsonl").read_bytes(); missing_commit_caught = False
        try:
            append_event(engagement, missing_commit)
        except RecordError as exc:
            missing_commit_caught = exc.code == "committed_file_missing"
        checks.append(("record.committed cannot point to a missing file", missing_commit_caught and (engagement / "events.jsonl").read_bytes() == before_missing_commit, "missing file commit appended"))
        committed_tampered = root / "committed-tampered"; shutil.copytree(engagement, committed_tampered); (committed_tampered / "legacy" / "migration-manifest.json").write_text("{}\n")
        committed_tamper_caught = False
        try:
            reduce_engagement(committed_tampered)
        except RecordError as exc:
            committed_tamper_caught = exc.code == "committed_file_digest_mismatch"
        checks.append(("modified committed record fails reduction", committed_tamper_caught, "modified committed record accepted"))
        report_tampered = root / "report-tampered"; shutil.copytree(engagement, report_tampered); (report_tampered / "reports" / "F-selftest-r3.md").write_text("tampered report\n", encoding="utf-8")
        report_tamper_blocked = False
        try:
            reduce_engagement(report_tampered)
        except RecordError as exc:
            report_tamper_blocked = exc.code == "report_manifest_binding_mismatch"
        checks.append(("report byte replacement fails revision-bound reduction", report_tamper_blocked, "tampered report reduced"))
        record_orphan = root / "record-orphan"; shutil.copytree(engagement, record_orphan); (record_orphan / "reports" / "orphan.manifest.json").write_text("{}\n")
        record_orphan_caught = False
        try:
            reduce_engagement(record_orphan)
        except RecordError as exc:
            record_orphan_caught = exc.code == "orphan_immutable_record"
        checks.append(("orphan immutable record fails reduction", record_orphan_caught, "orphan record accepted"))
        report_orphan = root / "report-orphan"; shutil.copytree(engagement, report_orphan); (report_orphan / "reports" / "rogue.md").write_text("# unbound advisory\n", encoding="utf-8")
        report_orphan_blocked = False
        try:
            reduce_engagement(report_orphan)
        except RecordError as exc:
            report_orphan_blocked = exc.code == "orphan_report_file"
        checks.append(("unbound advisory Markdown fails reduction", report_orphan_blocked, "unbound advisory accepted"))

        current = reduce_engagement(engagement)
        tampered = root / "tampered"; shutil.copytree(engagement, tampered)
        lines = (tampered / "events.jsonl").read_text().splitlines(); value = json.loads(lines[1]); value["rationale"] += " tampered"; lines[1] = json.dumps(value, sort_keys=True, separators=(",", ":")); (tampered / "events.jsonl").write_text("\n".join(lines) + "\n")
        tamper_caught = False
        try:
            read_ledger(tampered, "event")
        except RecordError as exc:
            tamper_caught = exc.code == "ledger_record_hash_mismatch"
        checks.append(("one-byte-equivalent ledger tamper is detected", tamper_caught, "tampered event accepted"))
        noncanonical = root / "noncanonical"; shutil.copytree(engagement, noncanonical)
        lines = (noncanonical / "events.jsonl").read_text().splitlines(); first_value = json.loads(lines[0]); lines[0] = json.dumps(dict(reversed(list(first_value.items()))), separators=(",", ":")); (noncanonical / "events.jsonl").write_text("\n".join(lines) + "\n")
        noncanonical_caught = False
        try:
            read_ledger(noncanonical, "event")
        except RecordError as exc:
            noncanonical_caught = exc.code == "ledger_noncanonical_line"
        checks.append(("noncanonical historical JSONL text fails even when values are unchanged", noncanonical_caught, "noncanonical line accepted"))
        blank = root / "blank-line"; shutil.copytree(engagement, blank)
        lines = (blank / "events.jsonl").read_bytes().splitlines(keepends=True); (blank / "events.jsonl").write_bytes(lines[0] + b"\n" + b"".join(lines[1:]))
        blank_caught = False
        try:
            read_ledger(blank, "event")
        except RecordError as exc:
            blank_caught = exc.code == "ledger_blank_line"
        checks.append(("blank physical JSONL lines fail", blank_caught, "blank line accepted"))

        cross_ledger = root / "cross-ledger"; shutil.copytree(engagement, cross_ledger)
        artifact_lines = [json.loads(line) for line in (cross_ledger / "artifacts.jsonl").read_text().splitlines()]; artifact_lines[-1]["engagement_id"] = "eng-other"; artifact_lines[-1]["record_hash"] = compute_record_hash(artifact_lines[-1]); (cross_ledger / "artifacts.jsonl").write_bytes(b"".join(canonical_json_bytes(item) for item in artifact_lines))
        cross_caught = False
        try:
            reduce_engagement(cross_ledger)
        except RecordError as exc:
            cross_caught = exc.code == "cross_engagement_ledger_record"
        checks.append(("direct-ledger cross-engagement records fail reduction", cross_caught, "cross-engagement artifact reduced"))
        dangling = root / "dangling-ref"; shutil.copytree(engagement, dangling)
        artifact_lines = [json.loads(line) for line in (dangling / "artifacts.jsonl").read_text().splitlines()]; artifact_lines[-1]["target_refs"] = ["target-missing"]; artifact_lines[-1]["record_hash"] = compute_record_hash(artifact_lines[-1]); (dangling / "artifacts.jsonl").write_bytes(b"".join(canonical_json_bytes(item) for item in artifact_lines))
        dangling_caught = False
        try:
            reduce_engagement(dangling)
        except RecordError as exc:
            dangling_caught = exc.code == "record_reference_invalid"
        checks.append(("direct-ledger dangling references fail reduction", dangling_caught, "dangling artifact reference reduced"))
        collision = root / "cross-type-id-collision"; shutil.copytree(engagement, collision)
        collision_event = base_event(event_id="artifact-selftest", engagement_id=engagement.name, recorded_at="2026-07-10T00:17:00Z", actor_role="operator", actor_id="operator-selftest", event_type="observation.recorded", rationale="Cross-type ID collision attack.", payload={"entity_id": "collision-observation", "entity_type": "observation", "status": "recorded"}); append_ledger_record(collision, "event", collision_event)
        collision_blocked = False
        try:
            reduce_engagement(collision)
        except RecordError as exc:
            collision_blocked = exc.code == "cross_type_record_id_collision"
        checks.append(("record IDs cannot collide across event/attempt/artifact/review types", collision_blocked, "cross-type collision reduced"))

        interrupted = root / "interrupted"; shutil.copytree(engagement, interrupted)
        with open(interrupted / "events.jsonl", "ab") as handle: handle.write(b'{\"partial\"')
        interrupted_caught = False
        try:
            read_ledger(interrupted, "event")
        except RecordError as exc:
            interrupted_caught = exc.code == "ledger_unterminated_tail"
        checks.append(("interrupted JSONL tail fails closed without truncation", interrupted_caught, "partial tail accepted"))
        repaired = repair_ledger_tail(interrupted, "event", "operator-selftest", "injected partial append", "2026-07-10T00:17:30Z")
        checks.append(("operator repair quarantines the partial tail and records recovery", (interrupted / repaired["quarantine_path"]).read_bytes() == b'{\"partial\"' and read_ledger(interrupted, "event")[-1]["event_id"] == repaired["event_id"], str(repaired)))

        pending = root / "pending-repair"; shutil.copytree(engagement, pending)
        pending_tail = b'{\"pending\"'; pending_path = pending / "events.jsonl"; prefix = pending_path.read_bytes(); pending_path.write_bytes(prefix + pending_tail)
        pending_digest = sha256_bytes(pending_tail); quarantine_rel = f"legacy/quarantine/event-tail-{pending_digest[-12:]}.bin"; (pending / "legacy" / "quarantine").mkdir(parents=True, exist_ok=True); (pending / quarantine_rel).write_bytes(pending_tail)
        marker = {"schema_version": 1, "ledger_kind": "event", "ledger_path": "events.jsonl", "prefix_digest": sha256_bytes(prefix), "quarantine_path": quarantine_rel, "quarantine_digest": pending_digest, "operator_id": "operator-selftest", "reason": "resume fixture", "recorded_at": "2026-07-10T00:17:45Z"}; (pending / "legacy" / "tail-repair.pending.json").write_bytes(canonical_json_bytes(marker))
        resumed = repair_ledger_tail(pending, "event", "operator-selftest", "resume fixture", "2026-07-10T00:17:45Z")
        checks.append(("repair resumes deterministically after crash between truncation and event", not (pending / "legacy" / "tail-repair.pending.json").exists() and read_ledger(pending, "event")[-1]["event_id"] == resumed["event_id"], str(resumed)))

        authorized_repair = root / "authorized-repair"; shutil.copytree(engagement, authorized_repair); broker_id, broker_session = _local_identity("broker"); repair_now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"); repair_action = _authority_action("repair-ledger-tail", lane_id="lane-repair", executor_id=broker_id, session_id=broker_session, ledger="attempt", operator_id="operator-selftest", reason="repair approved interrupted attempt tail", recorded_at=repair_now); repair_digest = sha256_bytes(canonical_json_bytes(repair_action)); repair_action_relative = "authority/requests/request-repair.action.json"; atomic_write(authorized_repair / repair_action_relative, canonical_json_bytes(repair_action)); repair_state = reduce_engagement(authorized_repair)
        append_event(authorized_repair, base_event(event_id="event-request-repair", engagement_id=repair_state["engagement_id"], recorded_at=repair_now, actor_role="broker", actor_id=broker_id, event_type="authority.requested", rationale="Request exact interrupted-tail repair.", payload={"request_id": "request-repair", "action_kind": "repair-ledger-tail", "action_digest": repair_digest, "action_path": repair_action_relative, "lane_id": "lane-repair", "request_status": "pending_authority", "scope_hash": repair_state["scope_hash"], "environment_ref": repair_state["active_environment_ref"], "expires_at": "2099-07-10T00:00:00Z"}, session_id=broker_session, operation_class="notebook")); append_event(authorized_repair, base_event(event_id="event-resolution-repair", engagement_id=repair_state["engagement_id"], recorded_at=repair_now, actor_role="operator", actor_id="operator-selftest", event_type="authority.resolved", rationale="Approve exact repair only.", payload={"request_id": "request-repair", "request_event_ref": "event-request-repair", "action_digest": repair_digest, "resolution": "approved", "resolved_at": repair_now}, entity_refs=["event-request-repair"], session_id=broker_session, operation_class="authority"))
        with open(authorized_repair / "attempts.jsonl", "ab") as handle: handle.write(b'{"interrupted-attempt"')
        command_repair_tail(argparse.Namespace(engagement=authorized_repair, ledger="attempt", operator_id="operator-selftest", reason="repair approved interrupted attempt tail", recorded_at=repair_now, authority_request_id="request-repair", lane_id="lane-repair", executor_id=broker_id, session_id=broker_session)); checks.append(("approved tail repair verifies authority from intact event prefix before reducing damaged ledger", (authorized_repair / "attempts.jsonl").read_bytes().endswith(b"\n") and read_ledger(authorized_repair, "event")[-1]["payload"].get("authority_request_ref") == "request-repair", "authorized repair did not recover"))

        rollback_event = base_event(event_id="event-short-write", engagement_id=engagement.name, recorded_at="2026-07-10T00:18:00Z", actor_role="operator", actor_id="operator-selftest", event_type="observation.recorded", rationale="Injected short write must roll back.", payload={"entity_id": "observation-short", "entity_type": "observation", "status": "recorded"})
        before_short = (engagement / "events.jsonl").read_bytes(); real_write = __import__("os").write; write_calls = [0]
        def injected_write(fd, data):
            write_calls[0] += 1
            if write_calls[0] == 1:
                return real_write(fd, data[:5])
            raise OSError("injected append interruption")
        short_rolled_back = False
        from unittest.mock import patch
        try:
            with patch("engagement_state.os.write", side_effect=injected_write):
                append_ledger_record(engagement, "event", rollback_event)
        except RecordError as exc:
            short_rolled_back = exc.code == "ledger_append_rolled_back"
        checks.append(("partial append is truncated to the last verified boundary", short_rolled_back and (engagement / "events.jsonl").read_bytes() == before_short and len(read_ledger(engagement, "event")) == current["event_count"], "short write left a tail"))

        forged_prior = base_event(event_id="event-prior-forged-operator", engagement_id=engagement.name, recorded_at="2026-07-10T00:18:05Z", actor_role="operator", actor_id="other-operator", event_type="operator_prior.recorded", rationale="Role label alone must not grant signed-scope authority.", payload={"prior_id": "prior-forged", "prior_statement": "Forged authority.", "strength": "strong", "reason": "adversarial fixture"})
        forged_prior_blocked = False
        try:
            append_event(engagement, forged_prior)
        except RecordError as exc:
            forged_prior_blocked = exc.code == "operator_prior_not_scope_authorized"
        checks.append(("operator prior actor is bound to active signed-scope operator", forged_prior_blocked and (engagement / "events.jsonl").read_bytes() == before_short, "forged operator prior appended"))

        future_refs = root / "future-candidate-refs"; shutil.copytree(engagement, future_refs)
        future_candidate = base_event(event_id="event-candidate-future", engagement_id=engagement.name, recorded_at="2026-07-10T00:18:10Z", actor_role="orchestrator", actor_id="orchestrator-selftest", event_type="candidate.proposed", rationale="Adversarial candidate references later provenance.", payload={"candidate_id": "candidate-future", "source_observation_ref": "event-observation-future", "routing_review_ref": "event-routing-future", "activation_strength": "strong", "card_ids": ["card-selftest"], "status": "queued", "expected_information_gain": 1, "safety_class": "clear_local", "cost_estimate": zero_cost}, entity_refs=["event-observation-future", "event-routing-future"], state_changes=[{"dimension": "search", "entity_id": "candidate-future", "previous": None, "current": "queued"}]); future_candidate["ex_ante"] = {"probability": 0.9, "ordinal": "strong", "recorded_before_outcome": True}
        append_ledger_record(future_refs, "event", future_candidate)
        future_observation = base_event(event_id="event-observation-future", engagement_id=engagement.name, recorded_at="2026-07-10T00:18:11Z", actor_role="orchestrator", actor_id="orchestrator-selftest", event_type="observation.recorded", rationale="Later observation.", payload={"entity_id": "observation-future", "entity_type": "observation", "status": "recorded"}); append_ledger_record(future_refs, "event", future_observation)
        future_routing = base_event(event_id="event-routing-future", engagement_id=engagement.name, recorded_at="2026-07-10T00:18:12Z", actor_role="reviewer", actor_id="reviewer-selftest", event_type="routing.assessed", rationale="Later routing assessment.", payload={"entity_id": "routing-future", "source_observation_ref": "event-observation-future", "activation_strength": "strong", "card_ids": ["card-selftest"], "status": "assessed"}, entity_refs=["event-observation-future"]); append_ledger_record(future_refs, "event", future_routing)
        future_ref_blocked = False
        try:
            reduce_engagement(future_refs)
        except RecordError as exc:
            future_ref_blocked = exc.code == "candidate_source_not_prior_observation"
        checks.append(("candidate provenance must exist earlier in the event ledger", future_ref_blocked, "candidate referenced future provenance"))

        precommit = root / "precommit-reference"; shutil.copytree(engagement, precommit); (precommit / "reviews").mkdir(exist_ok=True)
        review_record = {"schema_version": 1, "review_id": "review-precommit", "engagement_id": engagement.name, "review_type": "signal", "proposed_finding_id": None, "entity_ref": "event-observation-c1", "finding_revision": None, "recorded_at": "2026-07-10T00:18:20Z", "input_refs": ["event-observation-c1"], "input_hash": "sha256:" + "0" * 64, "evidence_refs": [], "conflicting_evidence": [], "independence": {"reviewer_id": "reviewer-selftest", "reviewer_model": "selftest", "reviewer_run_id": "run-review-precommit", "originating_run_id": "event-observation-c1", "fresh_context": True, "prior_verdict_visible": False, "disconfirming_objective": "Refute the routing signal."}, "verdict": "strong", "rationale": "Signal review fixture.", "corrections": [], "required_next_actions": ["route candidate"]}
        review_record["input_hash"] = compute_review_input_hash(precommit, review_record, build_reference_index(precommit))
        review_path = precommit / "reviews" / "precommit.json"; review_path.write_bytes(canonical_json_bytes(review_record))
        precommit_candidate = base_event(event_id="event-candidate-precommit", engagement_id=engagement.name, recorded_at="2026-07-10T00:18:30Z", actor_role="orchestrator", actor_id="orchestrator-selftest", event_type="candidate.proposed", rationale="Adversarial pre-commit review reference.", payload={"candidate_id": "candidate-precommit", "source_observation_ref": "event-observation-c1", "routing_review_ref": "review-precommit", "activation_strength": "strong", "card_ids": ["card-selftest"], "status": "queued", "expected_information_gain": 1, "safety_class": "clear_local", "cost_estimate": zero_cost}, entity_refs=["event-observation-c1", "review-precommit"], state_changes=[{"dimension": "search", "entity_id": "candidate-precommit", "previous": None, "current": "queued"}]); precommit_candidate["ex_ante"] = {"probability": 0.5, "ordinal": "strong", "recorded_before_outcome": True}; append_ledger_record(precommit, "event", precommit_candidate)
        later_commit = base_event(event_id="event-review-later-commit", engagement_id=engagement.name, recorded_at="2026-07-10T00:18:31Z", actor_role="operator", actor_id="operator-selftest", event_type="record.committed", rationale="Commit arrives after forbidden use.", payload={"record_path": "reviews/precommit.json", "record_digest": sha256_file(review_path), "record_type": "review", "record_id": "review-precommit", "record_revision": None}); append_ledger_record(precommit, "event", later_commit)
        precommit_blocked = False
        try:
            reduce_engagement(precommit)
        except RecordError as exc:
            precommit_blocked = exc.code == "record_reference_precedes_commit"
        checks.append(("immutable review must be committed before it can influence search", precommit_blocked, "future record commitment authorized prior reference"))

        dry_bypass = root / "dry-bypass"; shutil.copytree(engagement, dry_bypass)
        fake_review_event = base_event(event_id="event-coverage-review-fake", engagement_id=engagement.name, recorded_at="2026-07-10T00:18:20Z", actor_role="reviewer", actor_id="reviewer-selftest", event_type="review.coverage_completed", rationale="Missing cold review record.", payload={"review_type": "coverage", "verdict": "coverage_dry"}); append_ledger_record(dry_bypass, "event", fake_review_event)
        dry_event = base_event(event_id="event-dry-bypass", engagement_id=engagement.name, recorded_at="2026-07-10T00:18:21Z", actor_role="operator", actor_id="operator-selftest", event_type="coverage.status_changed", rationale="Attempt to close coverage around active work.", payload={"entity_id": engagement.name, "status": "coverage_dry", "coverage_review_ref": "event-coverage-review-fake"}, entity_refs=["event-coverage-review-fake"], state_changes=[{"dimension": "coverage", "entity_id": engagement.name, "previous": "blocked", "current": "coverage_dry"}]); append_ledger_record(dry_bypass, "event", dry_event)
        dry_bypass_blocked = False
        try:
            reduce_engagement(dry_bypass)
        except RecordError as exc:
            dry_bypass_blocked = exc.code == "coverage_review_event_invalid"
        checks.append(("coverage_dry cannot bypass a committed cold coverage review", dry_bypass_blocked, "dry coverage accepted without cold review"))

        drifted = root / "scope-drift"; shutil.copytree(engagement, drifted)
        with open(drifted / "scope.md", "a", encoding="utf-8") as handle: handle.write("\nchanged\n")
        before_drift_write = (drifted / "events.jsonl").read_bytes(); old_scope_after_drift = reduce_engagement(drifted)["scope_hash"]
        broker_id, broker_session = _local_identity("broker"); ordinary_after_drift = base_event(event_id="event-after-scope-drift", engagement_id=engagement.name, recorded_at="2026-07-10T00:19:00Z", actor_role="broker", actor_id=broker_id, event_type="observation.recorded", rationale="Continue a lane already bounded by the prior attestation.", payload={"entity_id": "observation-drift", "entity_type": "observation", "status": "recorded"}, session_id=broker_session, operation_class="notebook"); append_event(drifted, ordinary_after_drift)
        command_propose_scope(argparse.Namespace(engagement=drifted, draft=drifted/"scope.md", actor_id=broker_id, session_id=broker_session, recorded_at="2026-07-10T00:19:01Z", reason="Preserve drifted bytes without activating them.")); drift_state = reduce_engagement(drifted)
        checks.append(("scope drift is preserved as an unattested draft while old-scope lanes continue", old_scope_after_drift == current["scope_hash"] and drift_state["scope_hash"] == current["scope_hash"] and drift_state["scope_drafts"] and (drifted/str(drift_state["scope_drafts"][-1]["draft_path"])).is_file() and (drifted / "events.jsonl").read_bytes().startswith(before_drift_write), "scope drift was activated, lost, or globally stalled"))
        operator_drift = root/"operator-drift"; shutil.copytree(engagement, operator_drift); operator_drift.joinpath("scope.md").write_text(operator_drift.joinpath("scope.md").read_text().replace("Operator: operator-selftest", "Operator: attacker")); redirected_operator_blocked = False
        try: _require_operator_console(operator_drift, "attacker", "resolve-authority")
        except RecordError as exc: redirected_operator_blocked = exc.code == "operator_authority_invalid"
        checks.append(("drifted scope bytes cannot redirect active operator authority", redirected_operator_blocked, "draft operator replaced attested operator"))
        active_hash = current["scope_hash"]
        new_hash = sha256_file(drifted / "scope.md")
        model_reattestation = base_event(event_id="event-model-scope", engagement_id=engagement.name, recorded_at="2026-07-10T00:19:30Z", actor_role="orchestrator", actor_id="model-orchestrator", event_type="scope.attested", rationale="Model must not re-attest scope.", payload={"scope_hash": new_hash, "operator_id": "operator-selftest", "signed_date": "2026-07-10", "record_kernel": "decision-0006-v1", "supersedes_scope_hash": active_hash}, entity_refs=[engagement.name])
        model_scope_blocked = False
        try:
            append_event(drifted, model_reattestation)
        except RecordError as exc:
            model_scope_blocked = exc.code in {"scope_attestation_not_operator_bound", "scope_reattestation_not_operator_bound"}
        checks.append(("model-role scope re-attestation is rejected", model_scope_blocked and reduce_engagement(drifted)["scope_hash"] == active_hash, "model re-attested scope"))
        model_injected = root / "model-scope-injected"; shutil.copytree(drifted, model_injected); injected_proposal = json.loads(json.dumps(model_reattestation)); injected_proposal["payload"]["scope_snapshot_path"] = persist_scope_snapshot(model_injected, new_hash); append_ledger_record(model_injected, "event", injected_proposal)
        injected_scope_caught = False
        try:
            reduce_engagement(model_injected)
        except RecordError as exc:
            injected_scope_caught = exc.code in {"scope_attestation_not_operator_bound", "historical_scope_attestation_mismatch"}
        checks.append(("reducer rejects directly injected model scope authority", injected_scope_caught, "direct model scope event reduced"))
        reattestation = base_event(event_id="event-scope-reattested", engagement_id=engagement.name, recorded_at="2026-07-10T00:20:00Z", actor_role="operator", actor_id="operator-selftest", event_type="scope.attested", rationale="Operator re-attests changed scope bytes.", payload={"scope_hash": new_hash, "operator_id": "operator-selftest", "signed_date": "2026-07-10", "record_kernel": "decision-0006-v1", "supersedes_scope_hash": active_hash}, entity_refs=[engagement.name])
        append_event(drifted, reattestation)
        checks.append(("fresh operator scope re-attestation activates the draft without mutating history", reduce_engagement(drifted)["scope_hash"] == new_hash and (drifted / "events.jsonl").read_bytes().startswith(before_drift_write), "scope re-attestation failed or rewrote ledger"))

        closure = root / "memory-closure"; closure.mkdir(); closure.joinpath("scope.md").write_text(scope.replace("self-test", "memory-closure"), encoding="utf-8"); initialize_engagement(closure, "2026-07-10T00:21:00Z"); closure_state = reduce_engagement(closure)
        append_event(closure, base_event(event_id="event-closure-blocked", engagement_id=closure.name, recorded_at="2026-07-10T00:21:01Z", actor_role="operator", actor_id="operator-selftest", event_type="engagement.blocked", rationale="Exercise an evidence-preserving blocked closure.", payload={"entity_id": closure.name, "status": "blocked", "reason": "A bounded fixture blocker prevents coverage completion."}, state_changes=[{"dimension": "engagement", "entity_id": closure.name, "previous": "active", "current": "blocked"}, {"dimension": "coverage", "entity_id": closure.name, "previous": "active", "current": "blocked"}]))
        append_event(closure, base_event(event_id="event-cleanup-na", engagement_id=closure.name, recorded_at="2026-07-10T00:21:02Z", actor_role="operator", actor_id="operator-selftest", event_type="cleanup.updated", rationale="No live artifact cleanup exists.", payload={"entity_id": "cleanup-none", "status": "not_applicable", "scope_hash": closure_state["scope_hash"], "operator_id": "operator-selftest", "updated_at": "2026-07-10T00:21:02Z", "cleanup_obligations": [{"obligation_id": "cleanup-none", "kind": "no_live_artifacts", "status": "not_applicable", "artifact_refs": [], "rationale": "The engagement created no live target artifacts.", "closed_at": "2026-07-10T00:21:02Z"}]}, state_changes=[{"dimension": "cleanup", "entity_id": "cleanup-none", "previous": None, "current": "not_applicable"}]))
        missing_memory_blocked = False
        try: close_engagement(closure, "operator-selftest", "Must not close without memory disposition.", "2026-07-10T00:21:03Z")
        except RecordError as exc: missing_memory_blocked = exc.code == "engagement_closure_memory_missing"
        memory_proposal = {"schema_version": 1, "disposition_id": "memory-closure-final", "engagement_id": closure.name, "recorded_at": "2026-07-10T00:21:04Z", "scope_hash": closure_state["scope_hash"], "disposition": "no_novel_lesson", "lesson_kind": "none", "lesson_summary": None, "rationale": "Independent operator review found no reusable lesson.", "candidate_refs": [], "source_refs": {key: [] for key in ("event_refs", "candidate_refs", "hypothesis_refs", "attempt_refs", "artifact_refs", "review_refs", "finding_refs", "environment_refs")}, "sanitization": {"status": "not_applicable", "secret_scan_status": "clean", "target_identifiers_removed": True, "credential_values_removed": True, "harmful_recipe_removed": True, "target_terms_checked": [], "notes": "No lesson body exists to promote."}, "human_review": {"reviewer": {"role": "operator", "id": "operator-selftest"}, "reviewed_at": "2026-07-10T00:21:04Z", "decision": "no_novel_lesson", "rationale": "No novel lesson survived review.", "source_material_compared": True, "abstraction_only": True, "plane1_pr_required": True}, "reopening_condition": None, "provenance": {"actor": {"role": "operator", "id": "operator-selftest"}}}
        unsafe_promotion = json.loads(json.dumps(memory_proposal)); unsafe_promotion.update({"disposition": "promote", "lesson_kind": "negative", "lesson_summary": "A target-neutral defensive lesson.", "candidate_refs": ["candidate-c1"]}); unsafe_promotion["sanitization"].update({"status": "sanitized", "target_terms_checked": [closure.name]}); unsafe_promotion["human_review"]["decision"] = "promote"; unsafe_promotion["human_review"]["rationale"] = "Run curl against a retained endpoint."
        unsafe_promotion_blocked = False
        try: _validate_promotable_abstraction(unsafe_promotion)
        except RecordError as exc: unsafe_promotion_blocked = exc.code == "memory_abstraction_not_sanitized"
        checks.append(("promote scrubbing covers every retained human text field", unsafe_promotion_blocked, "unsafe review rationale passed promotion scrub"))
        proposal_path = root / "memory-proposal.json"; write_canonical_json(proposal_path, memory_proposal); recorded_memory = record_memory_disposition(closure, proposal_path, "operator-selftest"); retry_count = reduce_engagement(closure)["event_count"]; record_memory_disposition(closure, proposal_path, "operator-selftest")
        closed = close_engagement(closure, "operator-selftest", "Cleanup, blocked coverage, reports, and memory are terminal.", "2026-07-10T00:21:05Z")
        checks.append(("closure requires one operator-reviewed memory disposition and accepts no_novel_lesson", missing_memory_blocked and recorded_memory["disposition"] == "no_novel_lesson" and retry_count + 1 == closed["event_count"] and closed["memory_disposition"]["disposition"] == "no_novel_lesson", str(closed)))
        checks.append(("memory disposition never writes Plane-1", not (closure / "skills").exists() and not (closure / "casebooks").exists(), "record-memory created Plane-1 content"))

        broker_id, broker_session = _local_identity("broker"); now_dt = datetime.now(timezone.utc); now_text = now_dt.isoformat(timespec="seconds").replace("+00:00", "Z"); current_environment = reduce_engagement(engagement)["active_environment_ref"]
        canonical_source = root / "canonical-public-source.txt"; canonical_source.write_text("canonical inert evidence\n"); canonical_artifact_path = engagement / "evidence" / "canonical-public.txt"; canonical_metadata = {"schema_version": 1, "artifact_id": "artifact-canonical-public", "engagement_id": engagement.name, "created_at": now_text, "producer": {"role": "broker", "id": broker_id}, "producer_session_id": broker_session, "operation_class": "notebook", "acquisition_method": "source_inspection", "target_refs": [], "environment_ref": current_environment, "sensitivity": "internal", "redaction_status": "not_needed", "contains_executable_capability": False, "advisory_zone": "clear_local", "escalation_confirmation_event_ref": None, "cleanup_obligation_ref": None, "supersedes_artifact_id": None, "media_type": "text/plain"}; canonical_metadata_path = root / "canonical-artifact-metadata.json"; canonical_metadata_path.write_bytes(canonical_json_bytes(canonical_metadata)); canonical_classification_path = root / "canonical-artifact-classification.json"
        command_classify_artifact(argparse.Namespace(engagement=engagement, metadata=canonical_metadata_path, source=canonical_source, planned_sha256=None, planned_size=None, relative_path=Path("evidence/canonical-public.txt"), recorded_at=now_text, actor_role="broker", actor_id=broker_id, session_id=broker_session, output=canonical_classification_path, model=None, provider=None, tool_version=[])); shutil.copyfile(canonical_source, canonical_artifact_path); command_register_artifact(argparse.Namespace(engagement=engagement, file=canonical_artifact_path, metadata=canonical_metadata_path, classification=canonical_classification_path))
        prior_attempts = {item["attempt_id"]: item for item in read_ledger(engagement, "attempt")}
        canonical_attempt_specs = (("attempt-canonical-primary", "attempt-primary", []), ("attempt-canonical-negative", "attempt-negative", ["attempt-canonical-primary"]), ("attempt-canonical-positive", "attempt-positive", ["attempt-canonical-primary"]), ("attempt-canonical-replay", "attempt-replay", ["attempt-canonical-primary"]))
        for new_id, source_id, controls in canonical_attempt_specs:
            attempt = {key: value for key, value in json.loads(json.dumps(prior_attempts[source_id])).items() if key not in {"sequence", "previous_hash", "record_hash"}}; attempt.update({"attempt_id": new_id, "recorded_at": now_text, "actor": {"role": "broker", "id": broker_id}, "environment_ref": current_environment, "evidence_refs": ["artifact-canonical-public"], "control_of": controls, "operation_class": "notebook"}); attempt["provenance"].update({"actor": {"role": "broker", "id": broker_id}, "session_id": broker_session}); append_attempt(engagement, attempt)
        canonical_review = claim_review("review-canonical-public", now_text, "supported", "F-canonical-public", None, "event-hypothesis-running"); canonical_review["proposed_finding_id"] = "F-canonical-public"; canonical_review["entity_ref"] = "F-canonical-public"; canonical_review["input_refs"] = ["attempt-canonical-primary", "attempt-canonical-negative", "attempt-canonical-positive", "attempt-canonical-replay", current_environment]; canonical_review["evidence_refs"] = ["attempt-canonical-primary", "attempt-canonical-negative", "attempt-canonical-positive", "attempt-canonical-replay", "artifact-canonical-public"]; canonical_review["control_applicability"] = [{"attempt_ref": "attempt-canonical-negative", "applicable": True, "rationale": "Matched negative branch."}, {"attempt_ref": "attempt-canonical-positive", "applicable": True, "rationale": "Known-positive detector check."}, {"attempt_ref": "attempt-canonical-replay", "applicable": True, "rationale": "Fresh-state replay."}]; canonical_review["independence"]["reviewer_id"] = "reviewer-external-canonical"; canonical_review["input_hash"] = compute_review_input_hash(engagement, canonical_review, build_reference_index(engagement)); canonical_review_path = root / "canonical-review.json"; canonical_review_path.write_bytes(canonical_json_bytes(canonical_review))
        canonical_event = base_event(event_id="event-canonical-claim-supported", engagement_id=engagement.name, recorded_at=now_text, actor_role="broker", actor_id=broker_id, event_type="claim.adjudicated", rationale="Record an external independent supported verdict without self-filing.", payload={"entity_id": "F-canonical-public", "status": "supported", "review_ref": canonical_review["review_id"], "reviewer_id": "reviewer-external-canonical", "review_digest": sha256_file(canonical_review_path)}, review_refs=[canonical_review["review_id"]], state_changes=[{"dimension": "claim", "entity_id": "F-canonical-public", "previous": None, "current": "supported"}], session_id=broker_session, operation_class="notebook"); canonical_event_path = root / "canonical-review-event.json"; canonical_event_path.write_bytes(canonical_json_bytes(canonical_event))
        subprocess.run(["/usr/bin/ssh-keygen", "-q", "-Y", "sign", "-f", str(reviewer_key), "-n", "llm-redteam-harness-review-v1", str(canonical_review_path)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); review_signature = Path(str(canonical_review_path) + ".sig")
        review_cli = subprocess.run([sys.executable, str(Path(__file__).resolve()), "record-review", "--engagement", str(engagement), "--file", str(canonical_review_path), "--event", str(canonical_event_path), "--actor-id", broker_id, "--session-id", broker_session, "--signature", str(review_signature), "--allowed-signers", str(allowed_signers_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        if review_cli.returncode != 0: raise RecordError("canonical_review_subprocess_failed", review_cli.stdout + review_cli.stderr)
        forged_event = json.loads(json.dumps(canonical_event)); forged_event["event_id"] = "event-forged-reviewer"; forged_event["payload"]["reviewer_id"] = "forged-reviewer"; forged_path = root / "forged-review-event.json"; forged_path.write_bytes(canonical_json_bytes(forged_event)); forged_reviewer_blocked = False
        forged_cli = subprocess.run([sys.executable, str(Path(__file__).resolve()), "record-review", "--engagement", str(engagement), "--file", str(canonical_review_path), "--event", str(forged_path), "--actor-id", broker_id, "--session-id", broker_session, "--signature", str(review_signature), "--allowed-signers", str(allowed_signers_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        try: forged_reviewer_blocked = forged_cli.returncode != 0 and json.loads(forged_cli.stdout)["error"]["code"] == "canonical_review_binding_invalid"
        except (json.JSONDecodeError, KeyError): forged_reviewer_blocked = False
        canonical_finding = json.loads(json.dumps(finding1)); canonical_finding.update({"finding_id": "F-canonical-public", "revision": 1, "supersedes_revision": None, "recorded_at": now_text, "change_reason": "File the separately adjudicated canonical review.", "claim_state": "supported"}); canonical_finding["adjudication"] = {"review_ref": canonical_review["review_id"], "justification": "Canonical independent review supports the bounded claim."}; canonical_finding["scope_provenance"]["provenance"]["actor"] = {"role": "reviewer", "id": "reviewer-external-canonical"}; canonical_finding["scope_provenance"]["environment_ref"] = current_environment
        for claim_name in ("mechanism", "reachability"): canonical_finding["claims"][claim_name]["evidence_refs"] = ["artifact-canonical-public"]
        for impact in canonical_finding["claims"]["impact_claims"]: impact["evidence_refs"] = ["artifact-canonical-public"]
        canonical_finding["proof"].update({"primary_attempt_refs": ["attempt-canonical-primary"], "negative_control_refs": ["attempt-canonical-negative"], "positive_control_refs": ["attempt-canonical-positive"], "replay_refs": ["attempt-canonical-replay"], "evidence_refs": ["artifact-canonical-public"]})
        for mapping in canonical_finding["proof"]["claim_proofs"]: mapping.update({"attempt_refs": ["attempt-canonical-primary"], "artifact_refs": ["artifact-canonical-public"], "control_refs": ["attempt-canonical-negative", "attempt-canonical-positive"], "replay_refs": ["attempt-canonical-replay"]})
        canonical_finding_path = root / "canonical-finding.json"; canonical_finding_path.write_bytes(canonical_json_bytes(canonical_finding)); finding_digest = sha256_file(canonical_finding_path)
        action = _authority_action("revise-finding", lane_id="lane-canonical-finding", executor_id=broker_id, session_id=broker_session, file_digest=finding_digest, operator_id="operator-selftest", recorded_at=now_text); action_digest = sha256_bytes(canonical_json_bytes(action)); canonical_action_relative = "authority/requests/request-canonical-finding.action.json"; atomic_write(engagement / canonical_action_relative, canonical_json_bytes(action)); scope_hash = reduce_engagement(engagement)["scope_hash"]; request_id = "request-canonical-finding"
        append_event(engagement, base_event(event_id="event-request-canonical-finding", engagement_id=engagement.name, recorded_at=now_text, actor_role="broker", actor_id=broker_id, event_type="authority.requested", rationale="Request filing of one exact separately adjudicated revision.", payload={"request_id": request_id, "action_kind": "revise-finding", "action_digest": action_digest, "action_path": canonical_action_relative, "lane_id": "lane-canonical-finding", "request_status": "pending_authority", "scope_hash": scope_hash, "environment_ref": reduce_engagement(engagement)["active_environment_ref"], "expires_at": "2099-07-10T00:00:00Z"}, session_id=broker_session, operation_class="notebook"))
        append_event(engagement, base_event(event_id="event-resolution-canonical-finding", engagement_id=engagement.name, recorded_at=now_text, actor_role="operator", actor_id="operator-selftest", event_type="authority.resolved", rationale="Approve only the digest-bound canonical revision.", payload={"request_id": request_id, "request_event_ref": "event-request-canonical-finding", "action_digest": action_digest, "resolution": "approved", "resolved_at": now_text}, entity_refs=["event-request-canonical-finding"], session_id=broker_session, operation_class="authority"))
        partial_destination = engagement / "findings/F-canonical-public/rev-1.json"; atomic_write(partial_destination, canonical_json_bytes(canonical_finding)); partial_commit = base_event(event_id="event-F-canonical-public-r1-commit", engagement_id=engagement.name, recorded_at=now_text, actor_role="broker", actor_id=broker_id, event_type="record.committed", rationale="Commit immutable operator-authorized finding revision.", payload={"record_path": "findings/F-canonical-public/rev-1.json", "record_digest": finding_digest, "record_type": "finding-v3", "record_id": "F-canonical-public", "record_revision": 1, "authority_request_ref": request_id}, session_id=broker_session, operation_class="authority"); append_event(engagement, partial_commit)
        revise_cli = subprocess.run([sys.executable, str(Path(__file__).resolve()), "revise-finding", "--engagement", str(engagement), "--file", str(canonical_finding_path), "--operator-id", "operator-selftest", "--recorded-at", now_text, "--authority-request-id", request_id, "--lane-id", "lane-canonical-finding", "--executor-id", broker_id, "--session-id", broker_session], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        if revise_cli.returncode != 0: raise RecordError("canonical_finding_subprocess_failed", revise_cli.stdout + revise_cli.stderr)
        canonical_state = reduce_engagement(engagement)
        checks.append(("canonical public review and finding revision preserve reviewer, broker, adjudication, and filing separation", forged_reviewer_blocked and canonical_state["findings"]["F-canonical-public"]["revision"] == 1 and canonical_state["findings"]["F-canonical-public"]["status"] == "supported" and read_ledger(engagement, "event")[-1]["actor"] == {"role": "broker", "id": broker_id}, str(canonical_state["findings"].get("F-canonical-public"))))
        def approve_action(request_name: str, lane: str, action_value: dict[str, Any]) -> None:
            relative = f"authority/requests/{request_name}.action.json"; atomic_write(engagement/relative, canonical_json_bytes(action_value)); digest = sha256_bytes(canonical_json_bytes(action_value)); current_state = reduce_engagement(engagement)
            append_event(engagement, base_event(event_id=f"event-request-{request_name}", engagement_id=engagement.name, recorded_at=now_text, actor_role="broker", actor_id=broker_id, event_type="authority.requested", rationale="Exercise an exact canonical authority path.", payload={"request_id": request_name, "action_kind": action_value["action_kind"], "action_digest": digest, "action_path": relative, "lane_id": lane, "request_status": "pending_authority", "scope_hash": current_state["scope_hash"], "environment_ref": current_state["active_environment_ref"], "expires_at": "2099-07-10T00:00:00Z"}, session_id=broker_session, operation_class="notebook")); append_event(engagement, base_event(event_id=f"event-resolution-{request_name}", engagement_id=engagement.name, recorded_at=now_text, actor_role="operator", actor_id="operator-selftest", event_type="authority.resolved", rationale="Approve exact synthetic transition.", payload={"request_id": request_name, "request_event_ref": f"event-request-{request_name}", "action_digest": digest, "resolution": "approved", "resolved_at": now_text}, entity_refs=[f"event-request-{request_name}"], session_id=broker_session, operation_class="authority"))
        prior_action = _authority_action("record-operator-prior", lane_id="lane-prior-public", executor_id=broker_id, session_id=broker_session, operator_id="operator-selftest", recorded_at=now_text, prior_id="prior-public", prior_statement="Synthetic operator direction, not claim evidence.", strength="weak", reason="Exercise canonical prior authority."); approve_action("request-prior-public", "lane-prior-public", prior_action); command_record_operator_prior(argparse.Namespace(engagement=engagement, prior_id="prior-public", prior_statement="Synthetic operator direction, not claim evidence.", strength="weak", operator_id="operator-selftest", recorded_at=now_text, reason="Exercise canonical prior authority.", authority_request_id="request-prior-public", lane_id="lane-prior-public", executor_id=broker_id, session_id=broker_session))
        cleanup_proposal = {"entity_id": "cleanup-public", "status": "not_applicable", "cleanup_obligations": [{"obligation_id": "cleanup-public", "kind": "synthetic_local", "status": "not_applicable", "artifact_refs": [], "rationale": "No live effect exists.", "closed_at": now_text}]}; cleanup_path = root/"cleanup-public.json"; cleanup_path.write_bytes(canonical_json_bytes(cleanup_proposal)); cleanup_action = _authority_action("record-cleanup", lane_id="lane-cleanup-public", executor_id=broker_id, session_id=broker_session, operator_id="operator-selftest", recorded_at=now_text, reason="Exercise canonical cleanup authority.", **cleanup_proposal); approve_action("request-cleanup-public", "lane-cleanup-public", cleanup_action); command_record_cleanup(argparse.Namespace(engagement=engagement, file=cleanup_path, operator_id="operator-selftest", recorded_at=now_text, reason="Exercise canonical cleanup authority.", authority_request_id="request-cleanup-public", lane_id="lane-cleanup-public", executor_id=broker_id, session_id=broker_session))
        public_state = reduce_engagement(engagement); reopened = True
        if public_state["active_blockers"]:
            reopen_action = _authority_action("reopen", lane_id="lane-reopen-public", executor_id=broker_id, session_id=broker_session, operator_id="operator-selftest", recorded_at=now_text, reason="Exercise canonical reopening authority."); approve_action("request-reopen-public", "lane-reopen-public", reopen_action); command_reopen(argparse.Namespace(engagement=engagement, operator_id="operator-selftest", recorded_at=now_text, reason="Exercise canonical reopening authority.", authority_request_id="request-reopen-public", lane_id="lane-reopen-public", executor_id=broker_id, session_id=broker_session)); reopened = not reduce_engagement(engagement)["active_blockers"]
        checks.append(("canonical public prior, cleanup, and reopening transitions use exact one-use async authority", public_state["authority_requests"]["request-prior-public"]["status"] == "approved" and public_state["authority_requests"]["request-cleanup-public"]["status"] == "approved" and any(item["prior_id"] == "prior-public" for item in public_state["operator_priors"]) and any(item["obligation_id"] == "cleanup-public" for item in public_state["cleanup"]["obligations"]) and reopened, "public authority transition missing"))
    return checks


def self_test() -> int:
    checks: list[tuple[str, bool, str]] = []

    schema_problems = validate_schema_documents()
    checks.append(("new Draft 2020-12 schemas pass metaschema and local-ref validation", not schema_problems, str(schema_problems)))

    suite = validate_fixture_suite()
    checks.append(("valid/invalid fixture suite uses the canonical validator", not suite["failures"], str(suite["failures"])))
    reference_suite = validate_reference_fixture_suite()
    checks.append(("missing/wrong-type/cross-engagement/stale references fail", not reference_suite["failures"], str(reference_suite["failures"])))
    finding_case = next(case["record"] for case in load_json(Path(__file__).resolve().parents[1] / "fixtures" / "engagement-records" / "suite.json")["cases"] if case["id"] == "finding-v3-minimum")
    dispatch_ok = resolve_schema_name(finding_case) == "finding-v3"
    mismatch_caught = False
    try:
        resolve_schema_name(finding_case, "attempt-v2")
    except RecordError as exc:
        mismatch_caught = exc.code == "schema_dispatch_mismatch"
    checks.append(("record identity/version dispatch is authoritative", dispatch_ok and mismatch_caught, "caller-selected schema overrode dispatch"))
    ids = {case["id"] for case in suite["results"] if case["passed"]}
    for required in ("finding-v3-unknown-property", "finding-v3-duplicate-claim-id", "finding-v3-incomplete-claim-proof-map", "finding-v3-required-positive-control-missing", "finding-v3-empty-per-claim-proof", "finding-v3-positive-control-not-bound-per-claim", "attempt-v2-confirmed-outcome", "artifact-missing-conditional", "review-missing-conditional", "engagement-event-unknown-type", "state-snapshot-unknown-property", "environment-preflight-unknown-property", "report-manifest-unknown-property", "memory-disposition-unknown-property", "migration-manifest-unknown-property", "research-telemetry-unknown-property"):
        checks.append((f"negative fixture rejected: {required}", required in ids, "missing/failed fixture"))

    telemetry_fixture = load_json(Path(__file__).resolve().parents[1] / "fixtures" / "engagement-records" / "suite.json")
    calibration_record = json.loads(json.dumps(next(case["record"] for case in telemetry_fixture["cases"] if case["id"] == "research-telemetry-rich")))
    template_row = calibration_record["candidates"][0]; calibration_record["candidates"] = []
    for index_number in range(30):
        row = json.loads(json.dumps(template_row)); row["candidate_id"] = f"candidate-{index_number:02d}"; row["funnel_history"][0]["source_ref"] = f"event-eligible-{index_number:02d}"; row["funnel_history"][1]["source_ref"] = f"event-selected-{index_number:02d}"; row["funnel_history"][2]["source_ref"] = f"review-outcome-{index_number:02d}"; row["outcome"]["review_ref"] = f"review-outcome-{index_number:02d}"; row["review_refs"] = [row["outcome"]["review_ref"]]; calibration_record["candidates"].append(row)
    calibration_record["denominator"] = {"eligible_count": 30, "exported_count": 30, "complete": True}; calibration_record["classification"] = "calibration"; calibration_record["calibration_eligibility"] = {"eligible": True, "reasons": []}; calibration_score = score_telemetry(calibration_record)
    checks.append(("eligible ex-ante probabilities produce offline Brier and reliability telemetry only", calibration_score["brier_score"] == 0.0625 and calibration_score["small_sample"] is False and calibration_score["automatic_actions"] == [] and calibration_score["bandit_enabled"] is False, str(calibration_score)))

    canonical = canonical_json_bytes({"b": 2, "a": 1})
    checks.append(("canonical JSON is sorted and newline terminated", canonical == b'{"a":1,"b":2}\n', repr(canonical)))

    with tempfile.TemporaryDirectory(prefix="engagement-record-selftest-") as tmp:
        duplicate = Path(tmp) / "duplicate.json"
        duplicate.write_text('{"a":1,"a":2}\n', encoding="utf-8")
        caught = False
        try:
            load_json(duplicate)
        except RecordError as exc:
            caught = exc.code == "duplicate_json_key"
        checks.append(("duplicate JSON keys fail closed", caught, "duplicate key accepted"))

    # A record schema whose only property points at an unregistered URI must not degrade to success.
    broken = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "https://example.invalid/broken", "$ref": "https://example.invalid/missing"}
    broken_failed = False
    try:
        from jsonschema import Draft202012Validator
        list(Draft202012Validator(broken, registry=build_registry()).iter_errors({}))
    except Exception:
        broken_failed = True
    checks.append(("unresolved schema references fail closed", broken_failed, "missing $ref accepted"))

    duplicate_id_failed = False
    duplicate_schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "https://example.invalid/duplicate", "type": "object"}
    try:
        build_registry({"one.schema.json": duplicate_schema, "two.schema.json": duplicate_schema})
    except RecordError as exc:
        duplicate_id_failed = exc.code == "duplicate_schema_id"
    checks.append(("duplicate schema IDs fail closed", duplicate_id_failed, "duplicate $id accepted"))

    unavailable = subprocess.run(
        [sys.executable, "-S", str(Path(__file__).resolve()), "validate", "--schema-documents"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False,
    )
    try:
        unavailable_payload = json.loads(unavailable.stdout)
        unavailable_ok = unavailable.returncode != 0 and unavailable_payload.get("error", {}).get("code") == "validator_unavailable"
    except json.JSONDecodeError:
        unavailable_ok = False
    checks.append(("missing validator emits structured fail-closed output", unavailable_ok, unavailable.stdout + unavailable.stderr))
    checks.extend(state_self_test())

    for label, ok, detail in checks:
        print(f"  {'ok  ' if ok else 'FAIL'} {label}" + ("" if ok else f" :: {detail}"))
    failed = [label for label, ok, _ in checks if not ok]
    print(f"RUN-ENGAGEMENT SELF-TEST: {'PASS' if not failed else 'FAIL'}")
    return 0 if not failed else 1


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--self-test", action="store_true", help="run hermetic schema/record tests")
    subcommands = result.add_subparsers(dest="command")
    validate = subcommands.add_parser("validate", help="validate schemas, records, fixtures, or a read-only legacy inventory")
    validate.add_argument("--schema", choices=["finding-v3", "attempt-v2", "artifact", "review", "engagement-event", "state-snapshot", "environment-preflight", "environment-preflight-v2", "report-manifest", "memory-disposition", "migration-manifest", "migration-artifact-review", "research-telemetry", "historical-case-manifest", "retrospective-evaluation", "ab-preregistration", "ab-study-evidence", "ab-readiness-report", "finding-v2-legacy"])
    validate.add_argument("--file", type=Path)
    validate.add_argument("--engagement", type=Path, help="engagement root used to resolve record references")
    validate.add_argument("--schema-only", action="store_true", help="fixture/schema work only; skip engagement reference resolution")
    validate.add_argument("--schema-documents", action="store_true")
    validate.add_argument("--fixture-suite", nargs="?", const=True)
    validate.add_argument("--legacy-root", type=Path)
    validate.add_argument("--output", type=Path)

    identity = subcommands.add_parser("runtime-identity", help="print OS-process-bound local provenance values")
    identity.add_argument("--role", choices=["broker", "operator"], required=True)

    init = subcommands.add_parser("init", help="bind a signed scope and initialize the append-only record kernel")
    init.add_argument("--engagement", type=Path, required=True)
    init.add_argument("--recorded-at", help="explicit timestamp for deterministic replay/tests")
    for name in ("append-event", "append-attempt"):
        command = subcommands.add_parser(name, help=f"trusted {name} operation")
        command.add_argument("--engagement", type=Path, required=True)
        command.add_argument("--file", type=Path, required=True)
    classify_artifact = subcommands.add_parser("classify-artifact", help="classify a planned artifact before any bytes are created")
    classify_artifact.add_argument("--engagement", type=Path, required=True)
    classify_artifact.add_argument("--metadata", type=Path, required=True)
    classify_artifact.add_argument("--source", type=Path, help="pre-existing source for Notebook copies; forbidden for Zone-2")
    classify_artifact.add_argument("--planned-sha256", help="planned Zone-2 bytes digest; bytes must not exist yet")
    classify_artifact.add_argument("--planned-size", type=int)
    classify_artifact.add_argument("--relative-path", type=Path, required=True)
    classify_artifact.add_argument("--recorded-at", required=True)
    classify_artifact.add_argument("--actor-role", choices=["broker"], required=True)
    classify_artifact.add_argument("--actor-id", required=True)
    classify_artifact.add_argument("--session-id", required=True)
    classify_artifact.add_argument("--model")
    classify_artifact.add_argument("--provider")
    classify_artifact.add_argument("--tool-version", action="append", default=[])
    classify_artifact.add_argument("--output", type=Path)
    create_artifact = subcommands.add_parser("create-artifact", help="create exact digest-bound Zone-2 bytes only after fresh confirmation")
    create_artifact.add_argument("--engagement", type=Path, required=True)
    create_artifact.add_argument("--metadata", type=Path, required=True)
    create_artifact.add_argument("--classification", type=Path, required=True)
    create_artifact.add_argument("--actor-id", required=True)
    create_artifact.add_argument("--session-id", required=True)
    propose_scope = subcommands.add_parser("propose-scope", help="preserve an unattested scope amendment draft without changing authority")
    propose_scope.add_argument("--engagement", type=Path, required=True); propose_scope.add_argument("--draft", type=Path, required=True); propose_scope.add_argument("--actor-id", required=True); propose_scope.add_argument("--session-id", required=True); propose_scope.add_argument("--recorded-at", required=True); propose_scope.add_argument("--reason", required=True)
    reattest_scope = subcommands.add_parser("reattest-scope", help="activate one signed scope draft through exact async authority")
    reattest_scope.add_argument("--engagement", type=Path, required=True); reattest_scope.add_argument("--draft", type=Path, required=True); reattest_scope.add_argument("--operator-id", required=True); reattest_scope.add_argument("--recorded-at", required=True); reattest_scope.add_argument("--reason", required=True); reattest_scope.add_argument("--authority-request-id", required=True); reattest_scope.add_argument("--lane-id", required=True); reattest_scope.add_argument("--executor-id", required=True); reattest_scope.add_argument("--session-id", required=True)
    record_cleanup = subcommands.add_parser("record-cleanup", help="apply one exact operator-approved cleanup transition")
    record_cleanup.add_argument("--engagement", type=Path, required=True); record_cleanup.add_argument("--file", type=Path, required=True); record_cleanup.add_argument("--operator-id", required=True); record_cleanup.add_argument("--recorded-at", required=True); record_cleanup.add_argument("--reason", required=True); record_cleanup.add_argument("--authority-request-id", required=True); record_cleanup.add_argument("--lane-id", required=True); record_cleanup.add_argument("--executor-id", required=True); record_cleanup.add_argument("--session-id", required=True)
    record_prior = subcommands.add_parser("record-operator-prior", help="apply one exact operator-approved prior without establishing truth")
    record_prior.add_argument("--engagement", type=Path, required=True); record_prior.add_argument("--prior-id", required=True); record_prior.add_argument("--prior-statement", required=True); record_prior.add_argument("--strength", choices=["weak", "strong"], required=True); record_prior.add_argument("--operator-id", required=True); record_prior.add_argument("--recorded-at", required=True); record_prior.add_argument("--reason", required=True); record_prior.add_argument("--authority-request-id", required=True); record_prior.add_argument("--lane-id", required=True); record_prior.add_argument("--executor-id", required=True); record_prior.add_argument("--session-id", required=True)
    reopen = subcommands.add_parser("reopen", help="apply one exact operator-approved engagement reopening")
    reopen.add_argument("--engagement", type=Path, required=True); reopen.add_argument("--operator-id", required=True); reopen.add_argument("--recorded-at", required=True); reopen.add_argument("--reason", required=True); reopen.add_argument("--authority-request-id", required=True); reopen.add_argument("--lane-id", required=True); reopen.add_argument("--executor-id", required=True); reopen.add_argument("--session-id", required=True)
    request_authority = subcommands.add_parser("request-authority", help="append one digest-bound lane-local authority request")
    request_authority.add_argument("--engagement", type=Path, required=True); request_authority.add_argument("--request-id", required=True); request_authority.add_argument("--action-kind", required=True); request_authority.add_argument("--action-file", type=Path, required=True); request_authority.add_argument("--lane-id", required=True); request_authority.add_argument("--actor-role", choices=["broker"], required=True); request_authority.add_argument("--actor-id", required=True); request_authority.add_argument("--session-id", required=True); request_authority.add_argument("--recorded-at", required=True); request_authority.add_argument("--expires-at", required=True); request_authority.add_argument("--reason", required=True)
    resolve_authority = subcommands.add_parser("resolve-authority", help="operator-resolve one exact pending authority request")
    resolve_authority.add_argument("--engagement", type=Path, required=True); resolve_authority.add_argument("--request-id", required=True); resolve_authority.add_argument("--resolution", choices=["approved", "rejected", "expired", "superseded"], required=True); resolve_authority.add_argument("--operator-id", required=True); resolve_authority.add_argument("--session-id", required=True); resolve_authority.add_argument("--recorded-at", required=True); resolve_authority.add_argument("--reason", required=True)
    confirm_zone2 = subcommands.add_parser("confirm-zone2", help="record one fresh operator confirmation before one Zone-2 artifact is created")
    confirm_zone2.add_argument("--engagement", type=Path, required=True)
    confirm_zone2.add_argument("--file", type=Path, required=True)
    confirm_zone2.add_argument("--plan", type=Path, required=True)
    confirm_zone2.add_argument("--operator-id", required=True)
    artifact = subcommands.add_parser("register-artifact", help="hash and register a pre-classified immutable evidence file")
    artifact.add_argument("--engagement", type=Path, required=True)
    artifact.add_argument("--file", type=Path, required=True)
    artifact.add_argument("--metadata", type=Path, required=True)
    artifact.add_argument("--classification", type=Path, required=True)
    repair = subcommands.add_parser("repair-ledger-tail", help="operator-only quarantine of an uncommitted partial JSONL tail")
    repair.add_argument("--engagement", type=Path, required=True)
    repair.add_argument("--ledger", choices=["event", "attempt", "artifact"], required=True)
    repair.add_argument("--operator-id", required=True)
    repair.add_argument("--reason", required=True)
    repair.add_argument("--recorded-at", required=True)
    repair.add_argument("--authority-request-id", required=True); repair.add_argument("--lane-id", required=True); repair.add_argument("--executor-id", required=True); repair.add_argument("--session-id", required=True)
    telemetry = subcommands.add_parser("export-telemetry", help="derive complete-funnel telemetry without changing routing")
    telemetry.add_argument("--engagement", type=Path, required=True); telemetry.add_argument("--output", type=Path)
    telemetry_score = subcommands.add_parser("score-telemetry", help="score telemetry or eligible calibration offline")
    telemetry_score.add_argument("--file", type=Path, required=True)
    memory = subcommands.add_parser("record-memory", help="operator-review and commit one terminal memory disposition without modifying Plane-1")
    memory.add_argument("--engagement", type=Path, required=True); memory.add_argument("--file", type=Path, required=True); memory.add_argument("--operator-id", required=True); memory.add_argument("--authority-request-id", required=True); memory.add_argument("--lane-id", required=True); memory.add_argument("--executor-id", required=True); memory.add_argument("--session-id", required=True)
    close = subcommands.add_parser("close", help="operator-only cleanup, coverage, report, and memory closure gate")
    close.add_argument("--engagement", type=Path, required=True); close.add_argument("--operator-id", required=True); close.add_argument("--reason", required=True); close.add_argument("--recorded-at", required=True); close.add_argument("--authority-request-id", required=True); close.add_argument("--lane-id", required=True); close.add_argument("--executor-id", required=True); close.add_argument("--session-id", required=True)
    record_review_parser = subcommands.add_parser("record-review", help="atomically commit one independent review and its typed notebook event")
    record_review_parser.add_argument("--engagement", type=Path, required=True); record_review_parser.add_argument("--file", type=Path, required=True); record_review_parser.add_argument("--event", type=Path, required=True); record_review_parser.add_argument("--actor-id", required=True); record_review_parser.add_argument("--session-id", required=True); record_review_parser.add_argument("--signature", type=Path, required=True); record_review_parser.add_argument("--allowed-signers", type=Path, required=True)

    review_preflight_parser = subcommands.add_parser("review-preflight", help="apply an approved operator review to immutable preflight evidence")
    review_preflight_parser.add_argument("--engagement", type=Path, required=True); review_preflight_parser.add_argument("--preflight-id", required=True); review_preflight_parser.add_argument("--verdict", choices=["accepted", "rejected"], required=True); review_preflight_parser.add_argument("--reason", required=True); review_preflight_parser.add_argument("--operator-id", required=True); review_preflight_parser.add_argument("--recorded-at", required=True); review_preflight_parser.add_argument("--authority-request-id", required=True); review_preflight_parser.add_argument("--lane-id", required=True); review_preflight_parser.add_argument("--executor-id", required=True); review_preflight_parser.add_argument("--session-id", required=True)

    preflight = subcommands.add_parser("preflight", help="record offline Git/package/local-runtime identity and safety state")
    preflight.add_argument("--engagement", type=Path, required=True); preflight.add_argument("--preflight-id", required=True); preflight.add_argument("--mode", choices=["git", "package", "local_runtime"], required=True); preflight.add_argument("--target", type=Path, required=True); preflight.add_argument("--expected-identity", required=True); preflight.add_argument("--runtime", type=Path, required=True); preflight.add_argument("--reproduction-argv", required=True, help="JSON array; recorded but never executed by preflight"); preflight.add_argument("--actor-role", choices=["broker"], required=True); preflight.add_argument("--actor-id", required=True); preflight.add_argument("--session-id", required=True); preflight.add_argument("--model"); preflight.add_argument("--provider"); preflight.add_argument("--tool-version", action="append", default=[]); preflight.add_argument("--recorded-at", required=True); preflight.add_argument("--advisory-zone", choices=["clear_local", "review_required", "unknown"], default="clear_local"); preflight.add_argument("--credentials-present", action="store_true"); preflight.add_argument("--account-label", action="append", default=[]); preflight.add_argument("--configuration-file", type=Path, action="append", default=[]); preflight.add_argument("--endpoint-identity"); preflight.add_argument("--account-role"); preflight.add_argument("--feature-flag", action="append", default=[])
    migrate = subcommands.add_parser("migrate", help="read-only legacy inventory or signed-operator migration proposal")
    migrate.add_argument("--root", type=Path, default=Path(".")); migrate.add_argument("--output", type=Path); migrate.add_argument("--propose-engagement"); migrate.add_argument("--dry-run-engagement"); migrate.add_argument("--migration-dir",type=Path); migrate.add_argument("--apply-proposal", type=Path); migrate.add_argument("--destination", type=Path); migrate.add_argument("--artifact-review",type=Path); migrate.add_argument("--operator-id"); migrate.add_argument("--recorded-at"); migrate.add_argument("--authority-engagement", type=Path); migrate.add_argument("--authority-request-id"); migrate.add_argument("--lane-id"); migrate.add_argument("--executor-id"); migrate.add_argument("--session-id")
    revise = subcommands.add_parser("revise-finding", help="commit one contiguous operator-authorized finding revision")
    revise.add_argument("--engagement", type=Path, required=True); revise.add_argument("--file", type=Path, required=True); revise.add_argument("--operator-id", required=True); revise.add_argument("--recorded-at", required=True); revise.add_argument("--authority-request-id", required=True); revise.add_argument("--lane-id", required=True); revise.add_argument("--executor-id", required=True); revise.add_argument("--session-id", required=True)

    accept = subcommands.add_parser("accept-report", help="operator review and acceptance of a current revision-bound report")
    accept.add_argument("--engagement", type=Path, required=True); accept.add_argument("--report-id", required=True); accept.add_argument("--operator-id", required=True); accept.add_argument("--reason", required=True); accept.add_argument("--recorded-at", required=True); accept.add_argument("--authority-request-id", required=True); accept.add_argument("--lane-id", required=True); accept.add_argument("--executor-id", required=True); accept.add_argument("--session-id", required=True)
    submission = subcommands.add_parser("record-submission", help="record separate operator-authored external submission text")
    submission.add_argument("--engagement", type=Path, required=True); submission.add_argument("--report-id", required=True); submission.add_argument("--file", type=Path, required=True); submission.add_argument("--program", required=True); submission.add_argument("--operator-id", required=True); submission.add_argument("--recorded-at", required=True); submission.add_argument("--authority-request-id", required=True); submission.add_argument("--lane-id", required=True); submission.add_argument("--executor-id", required=True); submission.add_argument("--session-id", required=True)
    report = subcommands.add_parser("generate-report", help="operator-only generation of a revision-bound internal report")
    report.add_argument("--engagement", type=Path, required=True); report.add_argument("--finding-id", required=True); report.add_argument("--revision", type=int, required=True); report.add_argument("--include-claim", action="append", default=[]); report.add_argument("--omit-claim", action="append", default=[]); report.add_argument("--operator-id", required=True); report.add_argument("--recorded-at", required=True); report.add_argument("--authority-request-id", required=True); report.add_argument("--lane-id", required=True); report.add_argument("--executor-id", required=True); report.add_argument("--session-id", required=True)
    proof = subcommands.add_parser("render-proof", help="render the exact structured claim-to-proof matrix for a committed finding revision")
    proof.add_argument("--engagement", type=Path, required=True)
    proof.add_argument("--finding-id", required=True)
    proof.add_argument("--revision", type=int, required=True)
    for name in ("reduce", "render", "check-resume"):
        command = subcommands.add_parser(name, help=f"{name} deterministic engagement state")
        command.add_argument("--engagement", type=Path, required=True)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.self_test:
            return self_test()
        commands = {
            "validate": command_validate,
            "runtime-identity": command_runtime_identity,
            "init": command_init,
            "append-event": command_append_event,
            "append-attempt": command_append_attempt,
            "classify-artifact": command_classify_artifact,
            "create-artifact": command_create_artifact,
            "propose-scope": command_propose_scope,
            "reattest-scope": command_reattest_scope,
            "record-cleanup": command_record_cleanup,
            "record-operator-prior": command_record_operator_prior,
            "reopen": command_reopen,
            "request-authority": command_request_authority,
            "resolve-authority": command_resolve_authority,
            "confirm-zone2": command_confirm_zone2,
            "register-artifact": command_register_artifact,
            "repair-ledger-tail": command_repair_tail,
            "reduce": command_reduce,
            "render": command_render,
            "preflight": command_preflight,
            "record-review": command_record_review,
            "review-preflight": command_review_preflight,
            "record-memory": command_record_memory,
            "export-telemetry": command_export_telemetry,
            "score-telemetry": command_score_telemetry,
            "close": command_close,
            "migrate": command_migrate,
            "revise-finding": command_revise_finding,
            "accept-report": command_accept_report,
            "record-submission": command_record_submission,
            "generate-report": command_generate_report,
            "render-proof": command_render_proof,
            "check-resume": command_check_resume,
        }
        if args.command in commands:
            matrix = load_capability_matrix()
            if args.command not in matrix["commands"]:
                raise RecordError("operation_unclassified", f"command:{args.command}")
            if matrix["commands"][args.command]["tier"] not in {"event_dispatch", "variant_dispatch"}:
                classify_command(args.command, matrix=matrix)
            return commands[args.command](args)
        parser().print_help()
        return 2
    except RecordError as exc:
        emit({"valid": False, "error": exc.as_dict()})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
