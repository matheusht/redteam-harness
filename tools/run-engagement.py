#!/usr/bin/env python3
"""Canonical public command for Decision 0005 engagement records.

This command records and validates research state. It never drives a target.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from engagement_records import (
    RecordError,
    build_registry,
    canonical_json_bytes,
    legacy_finding_inventory,
    load_json,
    resolve_schema_name,
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
    append_ledger_record,
    assert_resume_current,
    base_event,
    compute_record_hash,
    engagement_lock,
    initialize_engagement,
    persist_scope_snapshot,
    read_ledger,
    reduce_engagement,
    register_artifact,
    repair_ledger_tail,
    write_snapshot,
)
from engagement_views import assert_views_current, render_views, write_views


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


def command_init(args: argparse.Namespace) -> int:
    snapshot = initialize_engagement(args.engagement, args.recorded_at)
    emit({"ok": True, "engagement_id": snapshot["engagement_id"], "scope_hash": snapshot["scope_hash"], "event_count": snapshot["event_count"]})
    return 0


def command_append_event(args: argparse.Namespace) -> int:
    proposal = load_json(args.file)
    record = append_event(args.engagement.resolve(), proposal)
    emit({"ok": True, "event_id": record["event_id"], "sequence": record["sequence"], "record_hash": record["record_hash"]})
    return 0


def command_register_artifact(args: argparse.Namespace) -> int:
    metadata = load_json(args.metadata)
    record = register_artifact(args.engagement.resolve(), args.file, metadata)
    emit({"ok": True, "artifact_id": record["artifact_id"], "sequence": record["sequence"], "record_hash": record["record_hash"], "sha256": record["sha256"]})
    return 0


def command_append_attempt(args: argparse.Namespace) -> int:
    proposal = load_json(args.file)
    record = append_attempt(args.engagement.resolve(), proposal)
    emit({"ok": True, "attempt_id": record["attempt_id"], "sequence": record["sequence"], "record_hash": record["record_hash"]})
    return 0


def command_repair_tail(args: argparse.Namespace) -> int:
    result = repair_ledger_tail(args.engagement.resolve(), args.ledger, args.operator_id, args.reason, args.recorded_at)
    emit({"ok": True, **result})
    return 0


def command_reduce(args: argparse.Namespace) -> int:
    engagement = args.engagement.resolve()
    with engagement_lock(engagement):
        snapshot = reduce_engagement(engagement)
        write_snapshot(engagement, snapshot)
        write_views(engagement, snapshot)
    emit({"ok": True, "event_count": snapshot["event_count"], "ledger_hash": snapshot["ledger_hash"]})
    return 0


def command_render(args: argparse.Namespace) -> int:
    engagement = args.engagement.resolve()
    with engagement_lock(engagement):
        snapshot = reduce_engagement(engagement)
        write_views(engagement, snapshot)
    emit({"ok": True, "views": sorted(render_views(snapshot))})
    return 0


def command_check_resume(args: argparse.Namespace) -> int:
    engagement = args.engagement.resolve()
    with engagement_lock(engagement):
        expected = assert_resume_current(engagement)
    emit({"ok": True, "event_count": expected["event_count"], "ledger_hash": expected["ledger_hash"]})
    return 0


def state_self_test() -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []
    with tempfile.TemporaryDirectory(prefix="engagement-state-selftest-") as tmp:
        root = Path(tmp)
        engagement = root / "eng-selftest"
        engagement.mkdir()
        scope = """# Scope — self-test

## Surfaces in scope
- Local fixture only.
## Benign safe-objective set
- Deterministic ledger test.
## Escalation ceiling
- Local records only.
## Impact-demo authorization
- No.
## Accounts / fixtures
- None.
## Authorization
- Operator: operator-selftest
- Date: 2026-07-10
- Signed: [x]
- Record kernel: `decision-0005-v1`
"""
        (engagement / "scope.md").write_text(scope, encoding="utf-8")
        snapshot = initialize_engagement(engagement, "2026-07-10T00:00:00Z")
        checks.append(("signed-scope init creates one attested event", snapshot["event_count"] == 1 and read_ledger(engagement, "event")[0]["event_type"] == "scope.attested", str(snapshot)))
        checks.append(("init writes deterministic snapshot and six generated views", (engagement / "state.snapshot.json").read_bytes() == canonical_json_bytes(snapshot) and len(render_views(snapshot)) == 6 and all((engagement / name).is_file() for name in render_views(snapshot)), "missing/stale initialization output"))

        invalid = base_event(event_id="event-invalid", engagement_id=engagement.name, recorded_at="2026-07-10T00:01:00Z", actor_role="operator", actor_id="operator-selftest", event_type="claim.adjudicated", rationale="Invalid direct confirmation must not append.", payload={"entity_id": "claim-1", "status": "confirmed"}, state_changes=[{"dimension": "claim", "entity_id": "claim-1", "previous": None, "current": "confirmed"}])
        invalid_caught = False
        before = (engagement / "events.jsonl").read_bytes()
        try:
            append_event(engagement, invalid)
        except RecordError as exc:
            invalid_caught = exc.code == "invalid_state_transition"
        checks.append(("invalid transition is rejected before append", invalid_caught and (engagement / "events.jsonl").read_bytes() == before, "invalid event changed ledger"))
        mismatch = base_event(event_id="event-mismatch", engagement_id=engagement.name, recorded_at="2026-07-10T00:01:30Z", actor_role="operator", actor_id="operator-selftest", event_type="candidate.proposed", rationale="Payload/state entity mismatch must fail.", payload={"candidate_id": "candidate-a", "status": "queued"}, state_changes=[{"dimension": "search", "entity_id": "candidate-b", "previous": None, "current": "queued"}])
        mismatch_caught = False
        try:
            append_event(engagement, mismatch)
        except RecordError as exc:
            mismatch_caught = exc.code == "event_state_entity_mismatch"
        checks.append(("event type, payload entity, and state change are inseparable", mismatch_caught and (engagement / "events.jsonl").read_bytes() == before, "mismatched event appended"))

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

        processes = []
        for number in range(4):
            proposal = base_event(event_id=f"event-concurrent-{number}", engagement_id=engagement.name, recorded_at=f"2026-07-10T00:1{number}:00Z", actor_role="operator", actor_id="operator-selftest", event_type="observation.recorded", rationale=f"Concurrent append {number}.", payload={"entity_id": f"observation-{number + 2}", "entity_type": "observation", "status": "recorded"})
            proposal_path = root / f"proposal-{number}.json"
            proposal_path.write_bytes(canonical_json_bytes(proposal))
            processes.append(subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "append-event", "--engagement", str(engagement), "--file", str(proposal_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
        for _ in range(2):
            processes.append(subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "reduce", "--engagement", str(engagement)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
        outcomes = [process.communicate(timeout=30) + (process.returncode,) for process in processes]
        concurrent_records = read_ledger(engagement, "event")
        current = reduce_engagement(engagement)
        checks.append(("concurrent writers serialize without loss or stale projections", all(result[2] == 0 for result in outcomes) and len(concurrent_records) == 7 and (engagement / "state.snapshot.json").read_bytes() == canonical_json_bytes(current), str(outcomes)))
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

        evidence_file = engagement / "evidence" / "artifact.txt"; evidence_file.write_text("benign evidence\n", encoding="utf-8")
        artifact_metadata = {"schema_version": 1, "artifact_id": "artifact-selftest", "engagement_id": engagement.name, "created_at": "2026-07-10T00:15:00Z", "producer": {"role": "operator", "id": "operator-selftest"}, "acquisition_method": "operator", "target_refs": [], "environment_ref": None, "sensitivity": "internal", "redaction_status": "not_needed", "contains_executable_capability": False, "advisory_zone": "clear_local", "escalation_confirmation_event_ref": None, "cleanup_obligation_ref": None, "supersedes_artifact_id": None, "media_type": "text/plain"}
        registered = register_artifact(engagement, evidence_file, artifact_metadata)
        checks.append(("register-artifact derives and commits path/digest/size", registered["sha256"] == sha256_file(evidence_file) and reduce_engagement(engagement)["artifact_count"] == 1, str(registered)))

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

        report_path = engagement / "reports" / "selftest.md"; report_path.write_text("# Bound self-test report\n", encoding="utf-8")
        manifest_path = engagement / "reports" / "selftest.manifest.json"; manifest_path.write_bytes(canonical_json_bytes({"schema_version": 1, "report_id": "report-manifest-selftest", "engagement_id": engagement.name, "generated_at": "2026-07-10T00:16:00Z", "finding_id": "F-selftest", "finding_revision": 1, "finding_digest": "sha256:" + "0" * 64, "adjudication_review_ref": "review-selftest", "adjudication_review_digest": "sha256:" + "1" * 64, "template_version": "selftest-v1", "renderer_version": "selftest-v1", "report_path": "reports/selftest.md", "report_digest": sha256_file(report_path), "operator_status": "draft"}))
        commit_event = base_event(event_id="event-record-committed", engagement_id=engagement.name, recorded_at="2026-07-10T00:16:00Z", actor_role="operator", actor_id="operator-selftest", event_type="record.committed", rationale="Commit immutable self-test report manifest.", payload={"record_path": "reports/selftest.manifest.json", "record_digest": sha256_file(manifest_path), "record_type": "report-manifest", "record_id": "report-manifest-selftest", "record_revision": None})
        append_event(engagement, commit_event)
        checks.append(("record.committed binds an existing immutable file digest", reduce_engagement(engagement)["last_event_id"] == "event-record-committed", "committed file not reducible"))
        missing_commit = base_event(event_id="event-missing-record", engagement_id=engagement.name, recorded_at="2026-07-10T00:16:30Z", actor_role="operator", actor_id="operator-selftest", event_type="record.committed", rationale="Missing committed file must fail.", payload={"record_path": "reports/missing.manifest.json", "record_digest": "sha256:" + "0" * 64, "record_type": "report-manifest", "record_id": "report-manifest-missing", "record_revision": None})
        before_missing_commit = (engagement / "events.jsonl").read_bytes(); missing_commit_caught = False
        try:
            append_event(engagement, missing_commit)
        except RecordError as exc:
            missing_commit_caught = exc.code == "committed_file_missing"
        checks.append(("record.committed cannot point to a missing file", missing_commit_caught and (engagement / "events.jsonl").read_bytes() == before_missing_commit, "missing file commit appended"))
        committed_tampered = root / "committed-tampered"; shutil.copytree(engagement, committed_tampered); (committed_tampered / "reports" / "selftest.manifest.json").write_text("{}\n")
        committed_tamper_caught = False
        try:
            reduce_engagement(committed_tampered)
        except RecordError as exc:
            committed_tamper_caught = exc.code == "committed_file_digest_mismatch"
        checks.append(("modified committed record fails reduction", committed_tamper_caught, "modified committed record accepted"))
        record_orphan = root / "record-orphan"; shutil.copytree(engagement, record_orphan); (record_orphan / "reports" / "orphan.manifest.json").write_text("{}\n")
        record_orphan_caught = False
        try:
            reduce_engagement(record_orphan)
        except RecordError as exc:
            record_orphan_caught = exc.code == "orphan_immutable_record"
        checks.append(("orphan immutable record fails reduction", record_orphan_caught, "orphan record accepted"))

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
        artifact_value = json.loads((cross_ledger / "artifacts.jsonl").read_text()); artifact_value["engagement_id"] = "eng-other"; artifact_value["record_hash"] = compute_record_hash(artifact_value); (cross_ledger / "artifacts.jsonl").write_bytes(canonical_json_bytes(artifact_value))
        cross_caught = False
        try:
            reduce_engagement(cross_ledger)
        except RecordError as exc:
            cross_caught = exc.code == "cross_engagement_ledger_record"
        checks.append(("direct-ledger cross-engagement records fail reduction", cross_caught, "cross-engagement artifact reduced"))
        dangling = root / "dangling-ref"; shutil.copytree(engagement, dangling)
        artifact_value = json.loads((dangling / "artifacts.jsonl").read_text()); artifact_value["target_refs"] = ["target-missing"]; artifact_value["record_hash"] = compute_record_hash(artifact_value); (dangling / "artifacts.jsonl").write_bytes(canonical_json_bytes(artifact_value))
        dangling_caught = False
        try:
            reduce_engagement(dangling)
        except RecordError as exc:
            dangling_caught = exc.code == "record_reference_invalid"
        checks.append(("direct-ledger dangling references fail reduction", dangling_caught, "dangling artifact reference reduced"))

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

        drifted = root / "scope-drift"; shutil.copytree(engagement, drifted)
        with open(drifted / "scope.md", "a", encoding="utf-8") as handle: handle.write("\nchanged\n")
        drift_caught = False
        try:
            reduce_engagement(drifted)
        except RecordError as exc:
            drift_caught = exc.code == "scope_drift"
        before_drift_write = (drifted / "events.jsonl").read_bytes()
        ordinary_after_drift = base_event(event_id="event-after-scope-drift", engagement_id=engagement.name, recorded_at="2026-07-10T00:19:00Z", actor_role="operator", actor_id="operator-selftest", event_type="observation.recorded", rationale="Must be blocked until re-attestation.", payload={"entity_id": "observation-drift", "entity_type": "observation", "status": "recorded"})
        write_blocked = False
        try:
            append_event(drifted, ordinary_after_drift)
        except RecordError as exc:
            write_blocked = exc.code == "scope_drift"
        checks.append(("post-attestation scope drift blocks reduction and ordinary writes", drift_caught and write_blocked and (drifted / "events.jsonl").read_bytes() == before_drift_write, "changed scope accepted"))
        active_hash = current["scope_hash"]
        new_hash = sha256_file(drifted / "scope.md")
        model_reattestation = base_event(event_id="event-model-scope", engagement_id=engagement.name, recorded_at="2026-07-10T00:19:30Z", actor_role="orchestrator", actor_id="model-orchestrator", event_type="scope.attested", rationale="Model must not re-attest scope.", payload={"scope_hash": new_hash, "operator_id": "operator-selftest", "signed_date": "2026-07-10", "record_kernel": "decision-0005-v1", "supersedes_scope_hash": active_hash}, entity_refs=[engagement.name])
        model_scope_blocked = False
        try:
            append_event(drifted, model_reattestation)
        except RecordError as exc:
            model_scope_blocked = exc.code in {"scope_attestation_not_operator_bound", "scope_reattestation_not_operator_bound"}
        checks.append(("model-role scope re-attestation is rejected", model_scope_blocked and (drifted / "events.jsonl").read_bytes() == before_drift_write, "model re-attested scope"))
        model_injected = root / "model-scope-injected"; shutil.copytree(drifted, model_injected); injected_proposal = json.loads(json.dumps(model_reattestation)); injected_proposal["payload"]["scope_snapshot_path"] = persist_scope_snapshot(model_injected, new_hash); append_ledger_record(model_injected, "event", injected_proposal)
        injected_scope_caught = False
        try:
            reduce_engagement(model_injected)
        except RecordError as exc:
            injected_scope_caught = exc.code in {"scope_attestation_not_operator_bound", "historical_scope_attestation_mismatch"}
        checks.append(("reducer rejects directly injected model scope authority", injected_scope_caught, "direct model scope event reduced"))
        reattestation = base_event(event_id="event-scope-reattested", engagement_id=engagement.name, recorded_at="2026-07-10T00:20:00Z", actor_role="operator", actor_id="operator-selftest", event_type="scope.attested", rationale="Operator re-attests changed scope bytes.", payload={"scope_hash": new_hash, "operator_id": "operator-selftest", "signed_date": "2026-07-10", "record_kernel": "decision-0005-v1", "supersedes_scope_hash": active_hash}, entity_refs=[engagement.name])
        append_event(drifted, reattestation)
        checks.append(("fresh operator scope re-attestation restores writes without mutating history", reduce_engagement(drifted)["scope_hash"] == new_hash and read_ledger(drifted, "event")[-2]["record_hash"] == current["ledger_hash"], "scope re-attestation failed or rewrote ledger"))
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
    for required in ("finding-v3-unknown-property", "finding-v3-duplicate-claim-id", "finding-v3-incomplete-claim-proof-map", "finding-v3-required-positive-control-missing", "finding-v3-empty-per-claim-proof", "finding-v3-positive-control-not-bound-per-claim", "attempt-v2-confirmed-outcome", "artifact-missing-conditional", "review-missing-conditional", "engagement-event-unknown-type", "state-snapshot-unknown-property", "environment-preflight-unknown-property", "report-manifest-unknown-property", "memory-disposition-unknown-property", "migration-manifest-unknown-property"):
        checks.append((f"negative fixture rejected: {required}", required in ids, "missing/failed fixture"))

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
    validate.add_argument("--schema", choices=["finding-v3", "attempt-v2", "artifact", "review", "engagement-event", "state-snapshot", "environment-preflight", "report-manifest", "memory-disposition", "migration-manifest", "finding-v2-legacy"])
    validate.add_argument("--file", type=Path)
    validate.add_argument("--engagement", type=Path, help="engagement root used to resolve record references")
    validate.add_argument("--schema-only", action="store_true", help="fixture/schema work only; skip engagement reference resolution")
    validate.add_argument("--schema-documents", action="store_true")
    validate.add_argument("--fixture-suite", nargs="?", const=True)
    validate.add_argument("--legacy-root", type=Path)
    validate.add_argument("--output", type=Path)

    init = subcommands.add_parser("init", help="bind a signed scope and initialize the append-only record kernel")
    init.add_argument("--engagement", type=Path, required=True)
    init.add_argument("--recorded-at", help="explicit timestamp for deterministic replay/tests")
    for name in ("append-event", "append-attempt"):
        command = subcommands.add_parser(name, help=f"trusted {name} operation")
        command.add_argument("--engagement", type=Path, required=True)
        command.add_argument("--file", type=Path, required=True)
    artifact = subcommands.add_parser("register-artifact", help="hash and register an immutable evidence file")
    artifact.add_argument("--engagement", type=Path, required=True)
    artifact.add_argument("--file", type=Path, required=True)
    artifact.add_argument("--metadata", type=Path, required=True)
    repair = subcommands.add_parser("repair-ledger-tail", help="operator-only quarantine of an uncommitted partial JSONL tail")
    repair.add_argument("--engagement", type=Path, required=True)
    repair.add_argument("--ledger", choices=["event", "attempt", "artifact"], required=True)
    repair.add_argument("--operator-id", required=True)
    repair.add_argument("--reason", required=True)
    repair.add_argument("--recorded-at")
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
            "init": command_init,
            "append-event": command_append_event,
            "append-attempt": command_append_attempt,
            "register-artifact": command_register_artifact,
            "repair-ledger-tail": command_repair_tail,
            "reduce": command_reduce,
            "render": command_render,
            "check-resume": command_check_resume,
        }
        if args.command in commands:
            return commands[args.command](args)
        parser().print_help()
        return 2
    except RecordError as exc:
        emit({"valid": False, "error": exc.as_dict()})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
