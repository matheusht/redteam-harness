#!/usr/bin/env python3
"""Append-only ledgers and deterministic reducers for Decision 0005 engagements."""

from __future__ import annotations

import copy
import fcntl
import json
import os
import re
import tempfile
from contextlib import contextmanager, nullcontext
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from engagement_records import (
    RecordError,
    build_reference_index,
    canonical_json_bytes,
    load_json,
    sha256_bytes,
    sha256_file,
    validate_record,
    validate_record_references,
)

LEDGERS = {
    "event": ("events.jsonl", "engagement-event", "event_id"),
    "attempt": ("attempts.jsonl", "attempt-v2", "attempt_id"),
    "artifact": ("artifacts.jsonl", "artifact", "artifact_id"),
}
STATE_VALUES = {
    "claim": {"needs_review", "supported", "confirmed", "contaminated", "refuted"},
    "search": {"queued", "selected", "running", "deferred", "blocked", "closed"},
    "coverage": {"active", "blocked", "coverage_dry"},
    "report": {"none", "draft", "accepted", "submitted"},
    "cleanup": {"open", "closed"},
    "memory": {"pending", "promote", "defer", "no_novel_lesson"},
    "engagement": {"active", "blocked", "closed"},
}
EVENT_STATE_RULES = {
    "scope.attested": ({"engagement", "coverage", "memory"}, set()),
    "candidate.proposed": ({"search"}, {"search"}),
    "candidate.selected": ({"search"}, {"search"}),
    "candidate.skipped": ({"search"}, {"search"}),
    "candidate.deferred": ({"search"}, {"search"}),
    "hypothesis.created": ({"search"}, {"search"}),
    "hypothesis.status_changed": ({"search"}, {"search"}),
    "claim.adjudicated": ({"claim"}, {"claim"}),
    "finding.revised": ({"claim"}, {"claim"}),
    "coverage.status_changed": ({"coverage"}, {"coverage"}),
    "report.generated": ({"report"}, {"report"}),
    "submission.recorded": ({"report"}, {"report"}),
    "cleanup.updated": ({"cleanup"}, {"cleanup"}),
    "memory.disposition_recorded": ({"memory"}, {"memory"}),
    "engagement.blocked": ({"engagement", "coverage"}, {"engagement", "coverage"}),
    "engagement.reopened": ({"engagement", "coverage"}, {"engagement", "coverage"}),
    "engagement.closed": ({"engagement"}, {"engagement"}),
}

COMMITTED_RECORD_LAYOUT = {
    "environment-preflight": "environment/preflight-*.json",
    "finding-v3": "findings/*/rev-*.json",
    "review": "reviews/*.json",
    "report-manifest": "reports/*.manifest.json",
    "memory-disposition": "memory/disposition-*.json",
    "migration-manifest": "legacy/migration-manifest.json",
}
COMMITTED_RECORD_SCHEMAS = {
    "environment-preflight": "environment-preflight", "finding-v3": "finding-v3", "review": "review",
    "report-manifest": "report-manifest", "memory-disposition": "memory-disposition", "migration-manifest": "migration-manifest",
}

TRANSITIONS = {
    "claim": {None: {"needs_review", "supported"}, "needs_review": {"supported", "contaminated", "refuted"}, "supported": {"confirmed", "needs_review", "contaminated", "refuted"}, "confirmed": {"needs_review", "contaminated", "refuted"}, "contaminated": {"needs_review", "refuted"}, "refuted": {"needs_review"}},
    "search": {None: {"queued"}, "queued": {"selected", "deferred", "blocked", "closed"}, "selected": {"running", "deferred", "blocked"}, "running": {"queued", "deferred", "blocked", "closed"}, "deferred": {"queued", "closed"}, "blocked": {"queued", "deferred", "closed"}, "closed": {"queued"}},
    "coverage": {None: {"active"}, "active": {"blocked", "coverage_dry"}, "blocked": {"active", "coverage_dry"}, "coverage_dry": {"active"}},
    "report": {None: {"none", "draft"}, "none": {"draft"}, "draft": {"accepted", "none"}, "accepted": {"submitted", "draft"}, "submitted": {"draft"}},
    "cleanup": {None: {"open", "closed"}, "open": {"closed"}, "closed": {"open"}},
    "memory": {None: {"pending", "promote", "defer", "no_novel_lesson"}, "pending": {"promote", "defer", "no_novel_lesson"}, "promote": {"defer"}, "defer": {"promote", "no_novel_lesson"}, "no_novel_lesson": {"defer", "promote"}},
    "engagement": {None: {"active"}, "active": {"blocked", "closed"}, "blocked": {"active", "closed"}, "closed": set()},
}


def _reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RecordError("duplicate_json_key", f"duplicate JSON object key in ledger: {key}")
        result[key] = value
    return result


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def compute_record_hash(record: dict[str, Any]) -> str:
    body = copy.deepcopy(record)
    body.pop("record_hash", None)
    return sha256_bytes(canonical_json_bytes(body))


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def engagement_lock(engagement: Path) -> Iterator[None]:
    engagement.mkdir(parents=True, exist_ok=True)
    lock_path = engagement / ".record-kernel.lock"
    with open(lock_path, "a+b") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _parse_ledger_data(data: bytes, relative: str, schema: str, identity: str) -> list[dict[str, Any]]:
    if data and not data.endswith(b"\n"):
        raise RecordError("ledger_unterminated_tail", f"{relative} does not end at a committed line boundary")
    physical_lines = data.split(b"\n")[:-1] if data else []
    records: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    previous: str | None = None
    for line_number, raw_line in enumerate(physical_lines, 1):
        if not raw_line:
            raise RecordError("ledger_blank_line", f"{relative}:{line_number}")
        try:
            record = json.loads(raw_line.decode("utf-8"), object_pairs_hook=_reject_duplicates)
        except UnicodeDecodeError as exc:
            raise RecordError("ledger_invalid_utf8", f"{relative}:{line_number}: {exc}") from exc
        except RecordError:
            raise
        except json.JSONDecodeError as exc:
            raise RecordError("ledger_interrupted_line", f"{relative}:{line_number}: {exc}") from exc
        if not isinstance(record, dict):
            raise RecordError("ledger_record_not_object", f"{relative}:{line_number}")
        if raw_line + b"\n" != canonical_json_bytes(record):
            raise RecordError("ledger_noncanonical_line", f"{relative}:{line_number}")
        errors = validate_record(record, schema)
        if errors:
            raise RecordError("ledger_schema_invalid", f"{relative}:{line_number}", errors)
        expected_sequence = len(records) + 1
        if record["sequence"] != expected_sequence:
            raise RecordError("ledger_sequence_gap", f"{relative}:{line_number} expected {expected_sequence}")
        if record["previous_hash"] != previous:
            raise RecordError("ledger_previous_hash_mismatch", f"{relative}:{line_number}")
        if record["record_hash"] != compute_record_hash(record):
            raise RecordError("ledger_record_hash_mismatch", f"{relative}:{line_number}")
        record_id = record[identity]
        if record_id in seen_ids:
            raise RecordError("duplicate_ledger_id", f"{relative}:{record_id}")
        seen_ids.add(record_id)
        previous = record["record_hash"]
        records.append(record)
    return records


def read_ledger(engagement: Path, kind: str) -> list[dict[str, Any]]:
    if kind not in LEDGERS:
        raise RecordError("unknown_ledger", kind)
    relative, schema, identity = LEDGERS[kind]
    path = engagement / relative
    return _parse_ledger_data(path.read_bytes(), relative, schema, identity) if path.exists() else []


def materialize_ledger_record(kind: str, proposal: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    _, schema, identity = LEDGERS[kind]
    record = copy.deepcopy(proposal)
    for forbidden in ("sequence", "previous_hash", "record_hash"):
        if forbidden in record:
            raise RecordError("trusted_field_in_proposal", f"proposal must not set {forbidden}")
    if not isinstance(record.get(identity), str):
        raise RecordError("record_identity_missing", identity)
    if any(existing[identity] == record[identity] for existing in records):
        raise RecordError("duplicate_ledger_id", record[identity])
    record["sequence"] = len(records) + 1
    record["previous_hash"] = records[-1]["record_hash"] if records else None
    record["record_hash"] = compute_record_hash(record)
    errors = validate_record(record, schema)
    if errors:
        raise RecordError("record_schema_invalid", f"cannot append {kind}", errors)
    return record


def append_ledger_record(engagement: Path, kind: str, proposal: dict[str, Any], *, lock_held: bool = False) -> dict[str, Any]:
    relative, _, _ = LEDGERS[kind]
    with (nullcontext() if lock_held else engagement_lock(engagement)):
        records = read_ledger(engagement, kind)
        record = materialize_ledger_record(kind, proposal, records)
        line = canonical_json_bytes(record)
        path = engagement / relative
        original_size = path.stat().st_size if path.exists() else 0
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            view = memoryview(line)
            total = 0
            while total < len(line):
                written = os.write(fd, view[total:])
                if written <= 0:
                    raise OSError("append made no progress")
                total += written
            os.fsync(fd)
        except Exception as exc:
            os.ftruncate(fd, original_size)
            os.fsync(fd)
            raise RecordError("ledger_append_rolled_back", f"{relative}: append failed and tail was truncated to last verified boundary: {exc}") from exc
        finally:
            os.close(fd)
        return record


def repair_ledger_tail(engagement: Path, kind: str, operator_id: str, reason: str, recorded_at: str | None = None) -> dict[str, Any]:
    if kind not in LEDGERS or not reason.strip():
        raise RecordError("tail_repair_input_invalid", "known ledger and non-empty reason required")
    engagement = engagement.resolve()
    relative, schema, identity = LEDGERS[kind]
    marker_path = engagement / "legacy" / "tail-repair.pending.json"
    with engagement_lock(engagement):
        metadata = _scope_metadata(engagement / "scope.md")
        signed_operator = re.sub(r"[^A-Za-z0-9._:-]+", "-", metadata["operator"]).strip("-") or "operator"
        if operator_id != signed_operator:
            raise RecordError("tail_repair_operator_mismatch", "repair operator must match signed scope")
        if marker_path.exists():
            marker = load_json(marker_path)
            if marker.get("operator_id") != operator_id or marker.get("ledger_kind") != kind:
                raise RecordError("tail_repair_pending_conflict", str(marker_path))
            path = engagement / relative
            data = path.read_bytes() if path.exists() else b""
            if data and not data.endswith(b"\n"):
                boundary = data.rfind(b"\n") + 1
                prefix, tail = data[:boundary], data[boundary:]
                if sha256_bytes(prefix) != marker.get("prefix_digest") or sha256_bytes(tail) != marker.get("quarantine_digest"):
                    raise RecordError("tail_repair_pending_bytes_mismatch", relative)
                _parse_ledger_data(prefix, relative, schema, identity)
                atomic_write(path, prefix)
            elif sha256_bytes(data) != marker.get("prefix_digest"):
                raise RecordError("tail_repair_pending_prefix_mismatch", relative)
        else:
            path = engagement / relative
            data = path.read_bytes() if path.exists() else b""
            if not data or data.endswith(b"\n"):
                raise RecordError("tail_repair_not_needed", relative)
            boundary = data.rfind(b"\n") + 1
            prefix, tail = data[:boundary], data[boundary:]
            _parse_ledger_data(prefix, relative, schema, identity)
            if kind == "event" and not _parse_ledger_data(prefix, relative, schema, identity):
                raise RecordError("tail_repair_no_scope_prefix", "event ledger has no committed scope event")
            tail_digest = sha256_bytes(tail)
            quarantine_rel = f"legacy/quarantine/{kind}-tail-{tail_digest[-12:]}.bin"
            atomic_write(engagement / quarantine_rel, tail)
            marker = {"schema_version": 1, "ledger_kind": kind, "ledger_path": relative, "prefix_digest": sha256_bytes(prefix), "quarantine_path": quarantine_rel, "quarantine_digest": tail_digest, "operator_id": operator_id, "reason": reason.strip(), "recorded_at": recorded_at or utc_now()}
            atomic_write(marker_path, canonical_json_bytes(marker))
            atomic_write(path, prefix)
        events = read_ledger(engagement, "event")
        event_id = f"event-tail-repair-{marker['quarantine_digest'][-12:]}"
        existing = next((event for event in events if event["event_id"] == event_id), None)
        if existing is None:
            proposal = base_event(event_id=event_id, engagement_id=events[0]["engagement_id"], recorded_at=marker["recorded_at"], actor_role="operator", actor_id=operator_id, event_type="observation.recorded", rationale=f"Operator quarantined an uncommitted {kind} ledger tail: {marker['reason']}", payload={"entity_id": f"{kind}-ledger", "entity_type": "ledger_tail_repair", "status": "repaired", "reason": marker["reason"], "record_path": marker["quarantine_path"], "record_digest": marker["quarantine_digest"]})
            preview = materialize_ledger_record("event", proposal, events)
            validate_event_semantics(preview)
            append_ledger_record(engagement, "event", proposal, lock_held=True)
        snapshot = reduce_engagement(engagement)
        write_snapshot(engagement, snapshot)
        from engagement_views import write_views
        write_views(engagement, snapshot)
        marker_path.unlink(missing_ok=True)
        return {"event_id": event_id, "quarantine_path": marker["quarantine_path"], "quarantine_digest": marker["quarantine_digest"]}


def _safe_engagement_file(engagement: Path, relative: str) -> Path:
    candidate = engagement / relative
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError as exc:
        raise RecordError("committed_file_missing", relative) from exc
    if not resolved.is_relative_to(engagement.resolve()) or candidate.is_symlink():
        raise RecordError("committed_path_escape", relative)
    if not resolved.is_file():
        raise RecordError("committed_file_not_regular", relative)
    return resolved


def validate_committed_payload(engagement: Path, payload: dict[str, Any]) -> None:
    relative = payload["record_path"]
    record_type = payload["record_type"]
    pattern = COMMITTED_RECORD_LAYOUT.get(record_type)
    if pattern is None or not Path(relative).match(pattern):
        raise RecordError("committed_record_layout_mismatch", f"{record_type}:{relative}")
    path = _safe_engagement_file(engagement, relative)
    if sha256_file(path) != payload["record_digest"]:
        raise RecordError("committed_file_digest_mismatch", relative)
    schema = COMMITTED_RECORD_SCHEMAS.get(record_type)
    if schema:
        value = load_json(path)
        errors = validate_record(value, schema)
        if errors:
            raise RecordError("committed_file_schema_invalid", relative, errors)
        identity_fields = {"environment-preflight": "preflight_id", "finding-v3": "finding_id", "review": "review_id", "report-manifest": "report_id", "memory-disposition": "disposition_id", "migration-manifest": "migration_id"}
        expected_id = value.get(identity_fields[record_type])
        expected_revision = value.get("revision") if record_type == "finding-v3" else None
        if expected_id != payload["record_id"] or expected_revision != payload["record_revision"]:
            raise RecordError("committed_file_identity_mismatch", relative)


def verify_file_authority(engagement: Path, events: list[dict[str, Any]], artifacts: list[dict[str, Any]], *, allowed_record_orphans: set[str] | None = None, allowed_artifact_orphans: set[str] | None = None) -> None:
    committed: dict[str, dict[str, Any]] = {}
    for event in events:
        if event["event_type"] != "record.committed":
            continue
        payload = event["payload"]
        relative = payload["record_path"]
        if relative in committed:
            raise RecordError("duplicate_file_commit", relative)
        validate_committed_payload(engagement, payload)
        committed[relative] = payload
    governed_files: set[str] = set()
    for pattern in COMMITTED_RECORD_LAYOUT.values():
        governed_files.update(path.relative_to(engagement).as_posix() for path in engagement.glob(pattern) if path.is_file())
    orphan_records = sorted(governed_files - set(committed) - (allowed_record_orphans or set()))
    if orphan_records:
        raise RecordError("orphan_immutable_record", ", ".join(orphan_records))

    artifact_paths: set[str] = set()
    for artifact in artifacts:
        relative = artifact["relative_path"]
        if relative in artifact_paths:
            raise RecordError("duplicate_artifact_path", relative)
        path = _safe_engagement_file(engagement, relative)
        if path.stat().st_size != artifact["size"] or sha256_file(path) != artifact["sha256"]:
            raise RecordError("artifact_file_digest_mismatch", relative)
        artifact_paths.add(relative)
    evidence_files = {
        path.relative_to(engagement).as_posix() for path in (engagement / "evidence").glob("**/*")
        if path.is_file() and path.name != ".gitkeep"
    }
    orphan_artifacts = sorted(evidence_files - artifact_paths - (allowed_artifact_orphans or set()))
    if orphan_artifacts:
        raise RecordError("orphan_artifact_file", ", ".join(orphan_artifacts))


def _scope_metadata(scope_path: Path) -> dict[str, str]:
    if not scope_path.is_file():
        raise RecordError("scope_missing", str(scope_path))
    text = scope_path.read_text(encoding="utf-8")
    if re.search(r"\[fill|\[target|\[project|\[name|\[date|<[^>]+>|___", text, re.IGNORECASE):
        raise RecordError("scope_unsigned_or_incomplete", "scope contains placeholders")
    if not re.search(r"^- Signed:\s*\[[xX]\]\s*$", text, re.MULTILINE):
        raise RecordError("scope_unsigned_or_incomplete", "scope signature checkbox is not checked")
    required_sections = ("## Surfaces in scope", "## Benign safe-objective set", "## Escalation ceiling", "## Impact-demo authorization", "## Accounts / fixtures", "## Authorization")
    missing_sections = [heading for heading in required_sections if heading not in text]
    if missing_sections:
        raise RecordError("scope_sections_missing", ", ".join(missing_sections))
    if "- Record kernel: `decision-0005-v1`" not in text:
        raise RecordError("record_kernel_not_selected", "scope must select decision-0005-v1")
    operator = re.search(r"^- Operator:\s*(.+?)\s*$", text, re.MULTILINE)
    signed = re.search(r"^- Date:\s*(\d{4}-\d{2}-\d{2})\s*$", text, re.MULTILINE)
    if not operator or not signed or operator.group(1).strip().startswith("["):
        raise RecordError("scope_signature_missing", "operator and ISO date are required")
    return {"operator": operator.group(1).strip(), "date": signed.group(1), "scope_hash": sha256_file(scope_path)}


def persist_scope_snapshot(engagement: Path, scope_hash: str) -> str:
    source = engagement / "scope.md"
    if sha256_file(source) != scope_hash:
        raise RecordError("scope_snapshot_source_mismatch", "scope.md does not match attested hash")
    relative = f"scope-attestations/{scope_hash.removeprefix('sha256:')}.md"
    destination = engagement / relative
    data = source.read_bytes()
    if destination.exists():
        if destination.read_bytes() != data:
            raise RecordError("scope_snapshot_collision", relative)
    else:
        atomic_write(destination, data)
    return relative


def validate_scope_event_snapshot(engagement: Path, event: dict[str, Any]) -> None:
    payload = event["payload"]
    expected_relative = f"scope-attestations/{payload['scope_hash'].removeprefix('sha256:')}.md"
    if payload.get("scope_snapshot_path") != expected_relative:
        raise RecordError("scope_snapshot_path_mismatch", event["event_id"])
    snapshot_path = _safe_engagement_file(engagement, expected_relative)
    metadata = _scope_metadata(snapshot_path)
    signed_operator = re.sub(r"[^A-Za-z0-9._:-]+", "-", metadata["operator"]).strip("-") or "operator"
    if metadata["scope_hash"] != payload["scope_hash"] or metadata["date"] != payload.get("signed_date") or event["actor"] != {"role": "operator", "id": signed_operator} or payload.get("operator_id") != signed_operator:
        raise RecordError("historical_scope_attestation_mismatch", event["event_id"])


def base_event(*, event_id: str, engagement_id: str, recorded_at: str, actor_role: str, actor_id: str, event_type: str, rationale: str, payload: dict[str, Any], entity_refs: list[str] | None = None, state_changes: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    actor = {"role": actor_role, "id": actor_id}
    return {
        "schema_version": 1,
        "event_id": event_id,
        "engagement_id": engagement_id,
        "recorded_at": recorded_at,
        "actor": actor,
        "event_type": event_type,
        "entity_refs": entity_refs or [],
        "rationale": rationale,
        "evidence_refs": [],
        "review_refs": [],
        "provenance": {"actor": actor, "model": None, "provider": None, "prompt_version": None, "card_versions": [], "tool_versions": []},
        "ex_ante": None,
        "state_changes": state_changes or [],
        "payload": payload,
    }


def initialize_engagement(engagement: Path, recorded_at: str | None = None) -> dict[str, Any]:
    engagement = engagement.resolve()
    metadata = _scope_metadata(engagement / "scope.md")
    engagement_id = engagement.name
    directories = ("reviews", "reports", "submissions", "environment", "evidence", "findings", "legacy", "memory", "scope-attestations")
    for name in directories:
        (engagement / name).mkdir(parents=True, exist_ok=True)
    for ledger in ("events.jsonl", "attempts.jsonl", "artifacts.jsonl"):
        (engagement / ledger).touch(exist_ok=True)
    existing = read_ledger(engagement, "event")
    if existing:
        first = existing[0]
        active_scope = next(event["payload"]["scope_hash"] for event in reversed(existing) if event["event_type"] == "scope.attested")
        if first["event_type"] != "scope.attested" or active_scope != metadata["scope_hash"]:
            raise RecordError("engagement_already_initialized", "existing ledger is bound to different scope bytes")
    else:
        operator_id = re.sub(r"[^A-Za-z0-9._:-]+", "-", metadata["operator"]).strip("-") or "operator"
        scope_snapshot_path = persist_scope_snapshot(engagement, metadata["scope_hash"])
        proposal = base_event(
            event_id=f"event-scope-{metadata['scope_hash'][-12:]}", engagement_id=engagement_id,
            recorded_at=recorded_at or utc_now(), actor_role="operator", actor_id=operator_id,
            event_type="scope.attested", rationale="Operator-signed scope bytes attested for the Decision 0005 record kernel.",
            payload={"scope_hash": metadata["scope_hash"], "scope_snapshot_path": scope_snapshot_path, "operator_id": operator_id, "signed_date": metadata["date"], "record_kernel": "decision-0005-v1", "supersedes_scope_hash": None},
            entity_refs=[engagement_id],
            state_changes=[
                {"dimension": "engagement", "entity_id": engagement_id, "previous": None, "current": "active"},
                {"dimension": "coverage", "entity_id": engagement_id, "previous": None, "current": "active"},
                {"dimension": "memory", "entity_id": engagement_id, "previous": None, "current": "pending"},
            ],
        )
        append_ledger_record(engagement, "event", proposal)
    snapshot = reduce_engagement(engagement)
    write_snapshot(engagement, snapshot)
    from engagement_views import write_views
    write_views(engagement, snapshot)
    return snapshot


def validate_event_semantics(event: dict[str, Any]) -> None:
    changes = event.get("state_changes", [])
    dimensions = {change.get("dimension") for change in changes}
    event_type = event.get("event_type")
    allowed, required = EVENT_STATE_RULES.get(event_type, (set(), set()))
    if not dimensions.issubset(allowed):
        raise RecordError("event_state_dimension_mismatch", f"{event_type} cannot change {sorted(dimensions - allowed)}")
    if not required.issubset(dimensions):
        raise RecordError("event_required_transition_missing", f"{event_type} must change {sorted(required - dimensions)}")
    by_dimension = {change["dimension"]: change for change in changes}
    if len(by_dimension) != len(changes):
        raise RecordError("duplicate_event_state_dimension", event["event_id"])
    payload = event.get("payload", {})
    engagement_id = event.get("engagement_id")
    if event.get("provenance", {}).get("actor") != event.get("actor"):
        raise RecordError("event_actor_provenance_mismatch", event.get("event_id", "unknown"))
    if event_type == "record.committed" and event.get("actor", {}).get("role") not in {"operator", "broker", "migration"}:
        raise RecordError("file_commit_actor_unauthorized", event.get("event_id", "unknown"))

    if event_type == "scope.attested":
        if event.get("actor", {}).get("role") != "operator" or event.get("actor", {}).get("id") != payload.get("operator_id"):
            raise RecordError("scope_attestation_not_operator_bound", event.get("event_id", "unknown"))
        if event.get("sequence") == 1:
            expected = {"engagement": "active", "coverage": "active", "memory": "pending"}
            if set(by_dimension) != set(expected) or any(by_dimension[dimension]["entity_id"] != engagement_id or by_dimension[dimension]["previous"] is not None or by_dimension[dimension]["current"] != target for dimension, target in expected.items()):
                raise RecordError("initial_state_incomplete", "first scope attestation must initialize exact engagement, coverage, and memory state")
        elif changes:
            raise RecordError("scope_reattestation_changes_state", event["event_id"])
        return

    binding: tuple[str, str | None, str | None] | None = None
    if event_type.startswith("candidate."):
        targets = {"candidate.proposed": "queued", "candidate.selected": "selected", "candidate.skipped": "closed", "candidate.deferred": "deferred"}
        binding = ("search", payload.get("candidate_id"), targets[event_type])
    elif event_type == "hypothesis.created":
        binding = ("search", payload.get("hypothesis_id"), "queued")
    elif event_type == "hypothesis.status_changed":
        binding = ("search", payload.get("hypothesis_id"), payload.get("status"))
    elif event_type == "claim.adjudicated":
        binding = ("claim", payload.get("entity_id"), payload.get("status"))
    elif event_type == "finding.revised":
        binding = ("claim", payload.get("finding_id"), payload.get("status"))
    elif event_type == "coverage.status_changed":
        binding = ("coverage", engagement_id, payload.get("status"))
    elif event_type == "report.generated":
        binding = ("report", payload.get("report_ref"), "draft")
    elif event_type == "submission.recorded":
        binding = ("report", payload.get("report_ref"), "submitted")
    elif event_type == "cleanup.updated":
        binding = ("cleanup", payload.get("entity_id"), payload.get("status"))
    elif event_type == "memory.disposition_recorded":
        binding = ("memory", engagement_id, payload.get("memory_disposition"))
    elif event_type == "engagement.blocked":
        if payload.get("entity_id") != engagement_id or payload.get("status") != "blocked":
            raise RecordError("event_payload_state_mismatch", event["event_id"])
        for dimension in ("engagement", "coverage"):
            change = by_dimension[dimension]
            if change["entity_id"] != engagement_id or change["current"] != "blocked":
                raise RecordError("event_state_entity_mismatch", event["event_id"])
    elif event_type == "engagement.reopened":
        if payload.get("entity_id") != engagement_id or payload.get("status") != "active":
            raise RecordError("event_payload_state_mismatch", event["event_id"])
        for dimension in ("engagement", "coverage"):
            change = by_dimension[dimension]
            if change["entity_id"] != engagement_id or change["current"] != "active":
                raise RecordError("event_state_entity_mismatch", event["event_id"])
    elif event_type == "engagement.closed":
        if payload.get("entity_id") != engagement_id or payload.get("status") != "closed":
            raise RecordError("event_payload_state_mismatch", event["event_id"])
        binding = ("engagement", engagement_id, "closed")

    if binding:
        dimension, entity_id, target = binding
        change = by_dimension.get(dimension)
        if change is None or not isinstance(entity_id, str) or change["entity_id"] != entity_id or change["current"] != target:
            raise RecordError("event_state_entity_mismatch", f"{event_type} payload and state change disagree")
        if payload.get("status") is not None and event_type.startswith("candidate.") and payload["status"] != target:
            raise RecordError("event_payload_state_mismatch", f"{event_type}:{payload['status']} != {target}")


def validate_transition(states: dict[str, dict[str, str]], change: dict[str, Any]) -> None:
    dimension = change["dimension"]
    entity_id = change["entity_id"]
    current = states.setdefault(dimension, {}).get(entity_id)
    if change["previous"] != current:
        raise RecordError("stale_transition_precondition", f"{dimension}:{entity_id} is {current!r}, not {change['previous']!r}")
    target = change["current"]
    if target not in STATE_VALUES[dimension]:
        raise RecordError("unknown_transition_state", f"{dimension}:{target}")
    if target not in TRANSITIONS[dimension].get(current, set()):
        raise RecordError("invalid_state_transition", f"{dimension}:{current!r}->{target!r}")
    states[dimension][entity_id] = target


def _initial_snapshot(engagement_id: str, scope_hash: str) -> dict[str, Any]:
    return {
        "schema_version": 1, "engagement_id": engagement_id, "scope_hash": scope_hash,
        "active_environment_ref": None, "last_event_id": None, "event_count": 0,
        "ledger_hash": "sha256:" + "0" * 64, "attempt_count": 0, "artifact_count": 0,
        "active_blockers": [], "candidates": {}, "operator_priors": [], "hypotheses": {}, "findings": {},
        "outstanding_reviews": [], "coverage": "active", "report_refs": [], "submission_refs": [],
        "cleanup": {"open_count": 0, "obligations": []}, "memory_disposition": None, "source_hashes": {}, "integrity_errors": [],
    }


def reduce_engagement(engagement: Path, *, allowed_record_orphans: set[str] | None = None, allowed_artifact_orphans: set[str] | None = None, allow_scope_drift: bool = False) -> dict[str, Any]:
    engagement = engagement.resolve()
    events = read_ledger(engagement, "event")
    if not events or events[0]["event_type"] != "scope.attested":
        raise RecordError("scope_attestation_missing", "first event must be scope.attested")
    scope_hash = events[0]["payload"]["scope_hash"]
    attempts = read_ledger(engagement, "attempt")
    artifacts = read_ledger(engagement, "artifact")
    engagement_id = events[0]["engagement_id"]
    index = build_reference_index(engagement)
    for kind, schema, records in (("attempt", "attempt-v2", attempts), ("artifact", "artifact", artifacts), ("event", "engagement-event", events)):
        for record in records:
            if record.get("engagement_id") != engagement_id:
                raise RecordError("cross_engagement_ledger_record", f"{kind}:{record.get(kind + '_id')}")
            reference_errors = validate_record_references(record, schema, index)
            if reference_errors:
                raise RecordError("record_reference_invalid", f"stored {kind} references do not resolve", reference_errors)
    verify_file_authority(engagement, events, artifacts, allowed_record_orphans=allowed_record_orphans, allowed_artifact_orphans=allowed_artifact_orphans)
    state = _initial_snapshot(engagement_id, scope_hash)
    states: dict[str, dict[str, str]] = {dimension: {} for dimension in STATE_VALUES}
    for event in events:
        if event["engagement_id"] != state["engagement_id"]:
            raise RecordError("cross_engagement_event", event["event_id"])
        if event["event_type"] == "scope.attested":
            validate_scope_event_snapshot(engagement, event)
        validate_event_semantics(event)
        for change in event["state_changes"]:
            validate_transition(states, change)
        event_type = event["event_type"]
        payload = event["payload"]
        if event_type == "scope.attested":
            prior = state["scope_hash"]
            if event["sequence"] > 1 and payload.get("supersedes_scope_hash") != prior:
                raise RecordError("scope_reattestation_mismatch", event["event_id"])
            state["scope_hash"] = payload["scope_hash"]
        elif event_type == "environment.preflight_recorded":
            state["active_environment_ref"] = payload.get("record_id") or payload.get("environment_ref")
        elif event_type == "candidate.proposed":
            state["candidates"][payload["candidate_id"]] = {"status": payload.get("status", "proposed"), "rationale": event["rationale"]}
        elif event_type == "operator_prior.recorded":
            state["operator_priors"].append({"event_id": event["event_id"], "entity_refs": event["entity_refs"], "strength": payload.get("strength"), "rationale": event["rationale"]})
        elif event_type == "hypothesis.created":
            state["hypotheses"][payload["hypothesis_id"]] = {"status": payload.get("status", "queued"), "rationale": event["rationale"]}
        elif event_type == "hypothesis.status_changed":
            state["hypotheses"].setdefault(payload["hypothesis_id"], {})["status"] = payload["status"]
        elif event_type == "finding.revised":
            state["findings"][payload["finding_id"]] = {"revision": payload["finding_revision"], "status": payload.get("status")}
        elif event_type == "report.generated":
            state["report_refs"].append(payload["report_ref"])
        elif event_type == "submission.recorded":
            state["submission_refs"].append(payload["submission_ref"])
        elif event_type == "memory.disposition_recorded":
            state["memory_disposition"] = payload["memory_disposition"]
        elif event_type == "engagement.blocked":
            state["active_blockers"].append(event["rationale"])
        elif event_type == "engagement.reopened":
            state["active_blockers"] = []
        state["last_event_id"] = event["event_id"]
    if not allow_scope_drift:
        metadata = _scope_metadata(engagement / "scope.md")
        latest_scope_event = next(event for event in reversed(events) if event["event_type"] == "scope.attested")
        signed_operator_id = re.sub(r"[^A-Za-z0-9._:-]+", "-", metadata["operator"]).strip("-") or "operator"
        if metadata["scope_hash"] != state["scope_hash"]:
            raise RecordError("scope_drift", "scope.md bytes changed; append a fresh scope.attested event before writes")
        if latest_scope_event["actor"] != {"role": "operator", "id": signed_operator_id} or latest_scope_event["payload"].get("operator_id") != signed_operator_id or latest_scope_event["payload"].get("signed_date") != metadata["date"]:
            raise RecordError("active_scope_attestation_mismatch", "latest scope event does not match the current signed scope operator/date")
    state["event_count"] = len(events)
    state["attempt_count"] = len(attempts)
    state["artifact_count"] = len(artifacts)
    state["coverage"] = states["coverage"].get(state["engagement_id"], "active")
    state["ledger_hash"] = events[-1]["record_hash"]
    state["source_hashes"] = {
        name: sha256_file(engagement / name) for name in ("events.jsonl", "attempts.jsonl", "artifacts.jsonl")
    }
    errors = validate_record(state, "state-snapshot")
    if errors:
        raise RecordError("snapshot_schema_invalid", "reducer emitted invalid state", errors)
    return state


def write_snapshot(engagement: Path, snapshot: dict[str, Any]) -> None:
    atomic_write(engagement / "state.snapshot.json", canonical_json_bytes(snapshot))


def assert_resume_current(engagement: Path) -> dict[str, Any]:
    expected = reduce_engagement(engagement)
    snapshot_path = engagement / "state.snapshot.json"
    if not snapshot_path.is_file() or snapshot_path.read_bytes() != canonical_json_bytes(expected):
        raise RecordError("stale_state_snapshot", "run `reduce` to rebuild state.snapshot.json")
    from engagement_views import assert_views_current
    assert_views_current(engagement, expected)
    return expected


def append_event(engagement: Path, proposal: dict[str, Any]) -> dict[str, Any]:
    # The append, reduction, snapshot, and views share one lock so concurrent writers cannot publish
    # a projection older than the authoritative ledger tail.
    with engagement_lock(engagement):
        current_events = read_ledger(engagement, "event")
        if not current_events:
            raise RecordError("scope_attestation_missing", "initialize engagement first")
        proposal = copy.deepcopy(proposal)
        if proposal.get("engagement_id") != current_events[0]["engagement_id"]:
            raise RecordError("cross_engagement_event", str(proposal.get("event_id")))
        latest_scope_hash = next(event["payload"]["scope_hash"] for event in reversed(current_events) if event["event_type"] == "scope.attested")
        if proposal.get("event_type") == "scope.attested":
            payload = proposal.get("payload", {})
            metadata = _scope_metadata(engagement / "scope.md")
            signed_operator_id = re.sub(r"[^A-Za-z0-9._:-]+", "-", metadata["operator"]).strip("-") or "operator"
            if payload.get("scope_hash") != metadata["scope_hash"] or payload.get("supersedes_scope_hash") != latest_scope_hash:
                raise RecordError("scope_reattestation_mismatch", "fresh scope attestation must bind current bytes and supersede the active hash")
            if proposal.get("actor", {}).get("role") != "operator" or proposal.get("actor", {}).get("id") != signed_operator_id or payload.get("operator_id") != signed_operator_id or payload.get("signed_date") != metadata["date"]:
                raise RecordError("scope_reattestation_not_operator_bound", "attestation actor must match the signed scope operator and date")
            reduce_engagement(engagement, allow_scope_drift=True)  # validates every historical attestation before extending authority
            expected_snapshot = f"scope-attestations/{metadata['scope_hash'].removeprefix('sha256:')}.md"
            if payload.get("scope_snapshot_path") not in (None, expected_snapshot):
                raise RecordError("scope_snapshot_path_mismatch", proposal["event_id"])
            payload["scope_snapshot_path"] = persist_scope_snapshot(engagement, metadata["scope_hash"])
        preview = materialize_ledger_record("event", proposal, current_events)
        validate_event_semantics(preview)
        reference_errors = validate_record_references(preview, "engagement-event", build_reference_index(engagement))
        if reference_errors:
            raise RecordError("record_reference_invalid", "event references do not resolve", reference_errors)
        if proposal.get("event_type") == "record.committed":
            validate_committed_payload(engagement, proposal["payload"])
            reduce_engagement(engagement, allowed_record_orphans={proposal["payload"]["record_path"]})
        elif proposal.get("event_type") != "scope.attested":
            reduce_engagement(engagement)  # blocks every ordinary write after scope drift
        states: dict[str, dict[str, str]] = {dimension: {} for dimension in STATE_VALUES}
        for event in current_events:
            for change in event["state_changes"]:
                validate_transition(states, change)
        for change in proposal.get("state_changes", []):
            validate_transition(states, change)
        record = append_ledger_record(engagement, "event", proposal, lock_held=True)
        snapshot = reduce_engagement(engagement)
        write_snapshot(engagement, snapshot)
        from engagement_views import write_views
        write_views(engagement, snapshot)
        return record


def register_artifact(engagement: Path, file_path: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    engagement = engagement.resolve()
    resolved_file = file_path.resolve(strict=True)
    evidence_root = (engagement / "evidence").resolve()
    if not resolved_file.is_relative_to(evidence_root) or file_path.is_symlink() or not resolved_file.is_file():
        raise RecordError("artifact_path_not_contained", "artifact must be a regular non-symlink file under engagement/evidence")
    relative = resolved_file.relative_to(engagement).as_posix()
    proposal = copy.deepcopy(metadata)
    for trusted in ("relative_path", "sha256", "size", "immutable", "sequence", "previous_hash", "record_hash"):
        if trusted in proposal:
            raise RecordError("trusted_field_in_proposal", f"artifact metadata must not set {trusted}")
    proposal.update({"relative_path": relative, "sha256": sha256_file(resolved_file), "size": resolved_file.stat().st_size, "immutable": True})
    with engagement_lock(engagement):
        reduce_engagement(engagement, allowed_artifact_orphans={relative})
        records = read_ledger(engagement, "artifact")
        preview = materialize_ledger_record("artifact", proposal, records)
        reference_errors = validate_record_references(preview, "artifact", build_reference_index(engagement))
        if reference_errors:
            raise RecordError("record_reference_invalid", "artifact references do not resolve", reference_errors)
        record = append_ledger_record(engagement, "artifact", proposal, lock_held=True)
        snapshot = reduce_engagement(engagement)
        write_snapshot(engagement, snapshot)
        from engagement_views import write_views
        write_views(engagement, snapshot)
        return record


def append_attempt(engagement: Path, proposal: dict[str, Any]) -> dict[str, Any]:
    with engagement_lock(engagement):
        reduce_engagement(engagement)  # scope and existing ledgers must be authoritative before write
        records = read_ledger(engagement, "attempt")
        preview = materialize_ledger_record("attempt", proposal, records)
        reference_errors = validate_record_references(preview, "attempt-v2", build_reference_index(engagement))
        if reference_errors:
            raise RecordError("record_reference_invalid", "attempt references do not resolve", reference_errors)
        record = append_ledger_record(engagement, "attempt", proposal, lock_held=True)
        snapshot = reduce_engagement(engagement)
        write_snapshot(engagement, snapshot)
        from engagement_views import write_views
        write_views(engagement, snapshot)
        return record
