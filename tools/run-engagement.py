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
    build_reference_index,
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
    compute_review_input_hash,
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
from environment_preflight import collect_preflight
from finding_review import claim_tuple_hash, render_claim_proof
from memory_disposition import _validate_promotable_abstraction, close_engagement, record_memory_disposition
from reporting import accept_report, generate_report, record_submission
from research_telemetry import export_telemetry, score_telemetry


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


def command_export_telemetry(args: argparse.Namespace) -> int:
    export = export_telemetry(args.engagement, args.output)
    emit(export if args.output is None else {"valid": True, "output": args.output.as_posix(), "classification": export["classification"], "candidate_count": len(export["candidates"])})
    return 0


def command_score_telemetry(args: argparse.Namespace) -> int:
    emit(score_telemetry(load_json(args.file)))
    return 0


def command_record_memory(args: argparse.Namespace) -> int:
    record = record_memory_disposition(args.engagement, args.file, args.operator_id)
    emit({"valid": True, "disposition_id": record["disposition_id"], "disposition": record["disposition"], "plane1_modified": False})
    return 0


def command_close(args: argparse.Namespace) -> int:
    snapshot = close_engagement(args.engagement, args.operator_id, args.reason, args.recorded_at)
    emit({"valid": True, "engagement_id": snapshot["engagement_id"], "closed": True, "memory_disposition": snapshot["memory_disposition"]})
    return 0


def command_preflight(args: argparse.Namespace) -> int:
    try:
        reproduction = json.loads(args.reproduction_argv)
        if not isinstance(reproduction, list) or any(not isinstance(item, str) or not item for item in reproduction):
            raise ValueError("reproduction argv must be a JSON array of strings; an empty array records a blocked preflight")
        record = collect_preflight(args.engagement, preflight_id=args.preflight_id, mode=args.mode, target=args.target, expected_identity=args.expected_identity, runtime=args.runtime, reproduction_argv=reproduction, operator_id=args.operator_id, recorded_at=args.recorded_at, operator_redaction_attested=args.operator_redaction_attested, advisory_zone=args.advisory_zone, credentials_present=args.credentials_present, account_labels=args.account_label, configuration_files=args.configuration_file, endpoint_identity=args.endpoint_identity, account_role=args.account_role, feature_flags=args.feature_flag)
    except (ValueError, json.JSONDecodeError) as exc:
        raise RecordError("preflight_invalid", str(exc)) from exc
    emit({"valid": True, "preflight_id": record["preflight_id"], "status": record["status"], "identity_hash": record["identity_hash"], "missing_fidelity": record["missing_fidelity"], "advisory_zone": record["safety"]["advisory_zone"], "zone2_authorization_granted": False})
    return 0


def command_migrate(args: argparse.Namespace) -> int:
    command = [sys.executable, str(Path(__file__).with_name("migrate-decision5.py")), "--root", str(args.root)]
    if args.output: command += ["--output", str(args.output)]
    if args.propose_engagement:
        if not args.operator_id or not args.output: raise RecordError("migration_proposal_args_missing", "proposal requires --operator-id and --output")
        command += ["--propose-engagement", args.propose_engagement, "--operator-id", args.operator_id]
    if args.apply_proposal:
        if not args.operator_id or not args.recorded_at or not args.destination: raise RecordError("migration_apply_args_missing", "apply requires --destination, --operator-id and --recorded-at")
        command += ["--apply-proposal", str(args.apply_proposal), "--destination", str(args.destination), "--operator-id", args.operator_id, "--recorded-at", args.recorded_at]
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode:
        raise RecordError("migration_command_failed", result.stderr or result.stdout)
    if result.stdout: print(result.stdout, end="")
    else: emit({"valid": True, "output": str(args.output)})
    return 0


def command_accept_report(args: argparse.Namespace) -> int:
    try:
        review = accept_report(args.engagement, args.report_id, args.operator_id, args.reason, args.recorded_at)
    except ValueError as exc:
        raise RecordError("report_acceptance_invalid", str(exc)) from exc
    emit({"valid": True, "review_id": review["review_id"], "report_id": args.report_id})
    return 0


def command_record_submission(args: argparse.Namespace) -> int:
    try:
        submission_id = record_submission(args.engagement, args.report_id, args.file, args.program, args.operator_id, args.recorded_at)
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
    try:
        manifest = generate_report(args.engagement, args.finding_id, args.revision, args.include_claim, omitted, args.operator_id, args.recorded_at)
    except ValueError as exc:
        raise RecordError("report_generation_invalid", str(exc)) from exc
    emit({"valid": True, "report_id": manifest["report_id"], "report_digest": manifest["report_digest"]})
    return 0


def command_render_proof(args: argparse.Namespace) -> int:
    engagement = args.engagement.resolve()
    reduce_engagement(engagement)
    entry = next((item for item in build_reference_index(engagement).get(args.finding_id, []) if item["type"] == "finding" and item.get("revision") == args.revision), None)
    if entry is None:
        raise RecordError("finding_revision_not_found", f"{args.finding_id}:{args.revision}")
    finding = load_json(engagement / entry["path"])
    emit({"valid": True, "finding_id": args.finding_id, "revision": args.revision, "claim_tuple_hash": claim_tuple_hash(finding), "markdown": render_claim_proof(finding)})
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

        before_concurrent_count = len(read_ledger(engagement, "event"))
        processes = []
        for number in range(4):
            proposal = base_event(event_id=f"event-concurrent-{number}", engagement_id=engagement.name, recorded_at="2026-07-10T00:10:00Z", actor_role="operator", actor_id="operator-selftest", event_type="observation.recorded", rationale=f"Concurrent append {number}.", payload={"entity_id": f"observation-{number + 2}", "entity_type": "observation", "status": "recorded"})
            proposal_path = root / f"proposal-{number}.json"
            proposal_path.write_bytes(canonical_json_bytes(proposal))
            processes.append(subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "append-event", "--engagement", str(engagement), "--file", str(proposal_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
        for _ in range(2):
            processes.append(subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "reduce", "--engagement", str(engagement)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
        outcomes = [process.communicate(timeout=30) + (process.returncode,) for process in processes]
        concurrent_records = read_ledger(engagement, "event")
        current = reduce_engagement(engagement)
        checks.append(("concurrent writers serialize without loss or stale projections", all(result[2] == 0 for result in outcomes) and len(concurrent_records) == before_concurrent_count + 4 and (engagement / "state.snapshot.json").read_bytes() == canonical_json_bytes(current), str(outcomes)))
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
        collector_engagement = root / "collector-modes"; collector_engagement.mkdir(); collector_engagement.joinpath("scope.md").write_text(scope.replace("self-test", "collector-modes"), encoding="utf-8"); initialize_engagement(collector_engagement, "2026-07-10T00:13:10Z")
        git_fixture = root / "git-fixture"; git_fixture.mkdir(); subprocess.run(["git", "init", "-q", str(git_fixture)], check=True); subprocess.run(["git", "-C", str(git_fixture), "config", "user.email", "fixture@example.invalid"], check=True); subprocess.run(["git", "-C", str(git_fixture), "config", "user.name", "Fixture"], check=True); git_fixture.joinpath("fixture.txt").write_text("fixture\n"); subprocess.run(["git", "-C", str(git_fixture), "add", "fixture.txt"], check=True); subprocess.run(["git", "-C", str(git_fixture), "commit", "-qm", "fixture"], check=True); git_commit = subprocess.check_output(["git", "-C", str(git_fixture), "rev-parse", "HEAD"], text=True).strip()
        git_preflight = collect_preflight(collector_engagement, preflight_id="preflight-git", mode="git", target=git_fixture, expected_identity=git_commit, runtime=runtime_fixture, reproduction_argv=[str(Path(sys.executable).resolve()), "-c", "pass"], operator_id="operator-selftest", recorded_at="2026-07-10T00:13:11Z", operator_redaction_attested=True)
        local_preflight = collect_preflight(collector_engagement, preflight_id="preflight-local-runtime", mode="local_runtime", target=package_fixture, expected_identity=package_digest, runtime=runtime_fixture, reproduction_argv=[str(Path(sys.executable).resolve()), "-c", "pass"], operator_id="operator-selftest", recorded_at="2026-07-10T00:13:12Z", operator_redaction_attested=True)
        checks.append(("demonstrated Git, package, and local-runtime collectors pin identity without executing reproduction argv", git_preflight["status"] == "ready" and local_preflight["status"] == "ready" and reduce_engagement(collector_engagement)["active_environment_ref"] == "preflight-local-runtime", str((git_preflight["status"], local_preflight["status"]))))
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
            register_artifact(secret_engagement, secret_file, {"schema_version": 1, "artifact_id": "artifact-secret", "engagement_id": engagement.name, "created_at": "2026-07-10T00:13:13Z", "producer": {"role": "operator", "id": "operator-selftest"}, "acquisition_method": "operator", "target_refs": [], "environment_ref": "preflight-selftest", "sensitivity": "secret", "redaction_status": "pending", "contains_executable_capability": False, "advisory_zone": "unknown", "escalation_confirmation_event_ref": None, "cleanup_obligation_ref": None, "supersedes_artifact_id": None, "media_type": "text/plain"})
        except RecordError as exc:
            secret_blocked = exc.code == "secret_shaped_artifact_content" and all("not-a-real" not in str(item) for item in exc.details)
        checks.append(("secret-shaped artifact content is rejected without echoing the value", secret_blocked, "secret-shaped artifact accepted or disclosed"))

        evidence_file = engagement / "evidence" / "artifact.txt"; evidence_file.write_text("benign evidence\n", encoding="utf-8")
        artifact_metadata = {"schema_version": 1, "artifact_id": "artifact-selftest", "engagement_id": engagement.name, "created_at": "2026-07-10T00:15:00Z", "producer": {"role": "operator", "id": "operator-selftest"}, "acquisition_method": "operator", "target_refs": [], "environment_ref": "preflight-selftest", "sensitivity": "internal", "redaction_status": "not_needed", "contains_executable_capability": False, "advisory_zone": "clear_local", "escalation_confirmation_event_ref": None, "cleanup_obligation_ref": None, "supersedes_artifact_id": None, "media_type": "text/plain"}
        registered = register_artifact(engagement, evidence_file, artifact_metadata)
        checks.append(("register-artifact derives and commits path/digest/size", registered["sha256"] == sha256_file(evidence_file) and reduce_engagement(engagement)["artifact_count"] == 1, str(registered)))
        artifact_boundary = (engagement / "artifacts.jsonl").read_bytes(); duplicate_metadata = json.loads(json.dumps(artifact_metadata)); duplicate_metadata["artifact_id"] = "artifact-duplicate-path"; duplicate_metadata["created_at"] = "2026-07-10T00:15:01Z"
        duplicate_registration_rolled_back = False
        try:
            register_artifact(engagement, evidence_file, duplicate_metadata)
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
            return {"schema_version": 1, "review_id": review_id, "engagement_id": engagement.name, "review_type": "claim_adjudication", "proposed_finding_id": "F-selftest", "entity_ref": entity_ref, "finding_revision": finding_revision, "recorded_at": recorded_at, "input_refs": ["attempt-primary", "attempt-negative", "attempt-positive", "attempt-replay", "preflight-selftest"], "input_hash": "sha256:" + ("3" if finding_revision is None else "4") * 64, "evidence_refs": ["attempt-primary", "attempt-negative", "attempt-positive", "attempt-replay", "artifact-selftest"], "conflicting_evidence": [], "independence": {"reviewer_id": "reviewer-selftest", "reviewer_model": "independent-reviewer", "reviewer_run_id": f"run-{review_id}", "originating_run_id": origin_run, "fresh_context": True, "prior_verdict_visible": False, "disconfirming_objective": "Refute the bounded mechanism and control linkage."}, "verdict": verdict, "rationale": "Primary trace, matched controls, and replay support only the bounded claim.", "corrections": [], "required_next_actions": ["preserve bounded language"], "control_applicability": [{"attempt_ref": "attempt-negative", "applicable": True, "rationale": "Matched negative branch."}, {"attempt_ref": "attempt-positive", "applicable": True, "rationale": "Known-positive detector check."}, {"attempt_ref": "attempt-replay", "applicable": True, "rationale": "Fresh-state replay."}]}
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
        forged_filing = json.loads(json.dumps(filing2)); forged_filing["event_id"] = "event-finding-forged-operator"; forged_filing["recorded_at"] = "2026-07-10T00:15:32Z"; forged_filing["actor"] = {"role": "operator", "id": "other-operator"}; forged_filing["provenance"]["actor"] = forged_filing["actor"]
        before_forged = (engagement / "events.jsonl").read_bytes(); forged_blocked = False
        try:
            append_event(engagement, forged_filing)
        except RecordError as exc:
            forged_blocked = exc.code == "finding_filing_not_scope_operator"
        checks.append(("only the active signed-scope operator can file a finding revision", forged_blocked and (engagement / "events.jsonl").read_bytes() == before_forged, "forged operator filing appended"))
        skip_revision = json.loads(json.dumps(filing2)); skip_revision["event_id"] = "event-finding-revision-4"; skip_revision["recorded_at"] = "2026-07-10T00:15:33Z"; skip_revision["payload"]["finding_revision"] = 4; skip_revision["payload"]["supersedes_revision"] = 2
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
        premature_revision = json.loads(json.dumps(filing2)); premature_revision["event_id"] = "event-premature-escalation-revision"; premature_revision["recorded_at"] = "2026-07-10T00:15:37Z"; premature_revision["payload"]["finding_revision"] = 3; premature_revision["payload"]["supersedes_revision"] = 2
        premature_blocked = False
        try:
            append_event(engagement, premature_revision)
        except RecordError as exc:
            premature_blocked = exc.code == "escalation_evidence_not_collected"
        checks.append(("regrade escalation routes to evidence collection before finding revision", premature_blocked, "escalation directly revised finding"))
        escalation_hypothesis = base_event(event_id="event-hypothesis-escalation", engagement_id=engagement.name, recorded_at="2026-07-10T00:15:38Z", actor_role="orchestrator", actor_id="orchestrator-selftest", event_type="hypothesis.created", rationale="Route reviewer escalation into bounded evidence collection.", payload={"hypothesis_id": "hypothesis-escalation", "origin_type": "reviewer_challenge", "origin_ref": "event-regrade-escalation", "hypothesis_statement": "The adjacent owned transition composes with the confirmed primitive.", "suspected_invariant": "Primitive output must not cross the adjacent boundary.", "trust_boundary": "primitive to adjacent owned transition", "attacker_path": ["primitive", "adjacent transition"], "impact_ceiling": "owned fixture only", "bounded_space": "One adjacent transition.", "lens_ids": ["composition"], "card_ids": ["card-selftest"], "expected_confirming_evidence": [{"evidence_type": "trace", "description": "end-to-end composition trace", "required": True}], "decisive_falsifiers": ["adjacent transition rejects primitive output"], "cost_estimate": zero_cost, "constraints": ["offline fixture"], "next_experiment": "trace composition", "completion_criteria": ["trace or decisive rejection"], "status": "queued"}, entity_refs=["event-regrade-escalation"], finding_refs=["F-selftest"], state_changes=[{"dimension": "search", "entity_id": "hypothesis-escalation", "previous": None, "current": "queued"}]); append_event(engagement, escalation_hypothesis)
        escalation_evidence_path = engagement / "evidence" / "escalation.txt"; escalation_evidence_path.write_text("new bounded escalation trace\n", encoding="utf-8")
        escalation_artifact = json.loads(json.dumps(artifact_metadata)); escalation_artifact.update({"artifact_id": "artifact-escalation", "created_at": "2026-07-10T00:15:40.500000Z", "acquisition_method": "source_inspection"}); register_artifact(engagement, escalation_evidence_path, escalation_artifact)
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
        unresolved_correction = json.loads(json.dumps(filing2)); unresolved_correction["event_id"] = "event-unresolved-correction"; unresolved_correction["recorded_at"] = "2026-07-10T00:15:53.500000Z"; unresolved_correction["payload"]["finding_revision"] = 3; unresolved_correction["payload"]["supersedes_revision"] = 2
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
    telemetry = subcommands.add_parser("export-telemetry", help="derive complete-funnel telemetry without changing routing")
    telemetry.add_argument("--engagement", type=Path, required=True); telemetry.add_argument("--output", type=Path)
    telemetry_score = subcommands.add_parser("score-telemetry", help="score telemetry or eligible calibration offline")
    telemetry_score.add_argument("--file", type=Path, required=True)
    memory = subcommands.add_parser("record-memory", help="operator-review and commit one terminal memory disposition without modifying Plane-1")
    memory.add_argument("--engagement", type=Path, required=True); memory.add_argument("--file", type=Path, required=True); memory.add_argument("--operator-id", required=True)
    close = subcommands.add_parser("close", help="operator-only cleanup, coverage, report, and memory closure gate")
    close.add_argument("--engagement", type=Path, required=True); close.add_argument("--operator-id", required=True); close.add_argument("--reason", required=True); close.add_argument("--recorded-at", required=True)
    preflight = subcommands.add_parser("preflight", help="record offline Git/package/local-runtime identity and safety state")
    preflight.add_argument("--engagement", type=Path, required=True); preflight.add_argument("--preflight-id", required=True); preflight.add_argument("--mode", choices=["git", "package", "local_runtime"], required=True); preflight.add_argument("--target", type=Path, required=True); preflight.add_argument("--expected-identity", required=True); preflight.add_argument("--runtime", type=Path, required=True); preflight.add_argument("--reproduction-argv", required=True, help="JSON array; recorded but never executed by preflight"); preflight.add_argument("--operator-id", required=True); preflight.add_argument("--recorded-at", required=True); preflight.add_argument("--operator-redaction-attested", action="store_true", help="operator attests all labels/argv were redacted and contain no credential values"); preflight.add_argument("--advisory-zone", choices=["clear_local", "review_required", "unknown"], default="clear_local"); preflight.add_argument("--credentials-present", action="store_true"); preflight.add_argument("--account-label", action="append", default=[]); preflight.add_argument("--configuration-file", type=Path, action="append", default=[]); preflight.add_argument("--endpoint-identity"); preflight.add_argument("--account-role"); preflight.add_argument("--feature-flag", action="append", default=[])
    migrate = subcommands.add_parser("migrate", help="read-only legacy inventory or signed-operator migration proposal")
    migrate.add_argument("--root", type=Path, default=Path(".")); migrate.add_argument("--output", type=Path); migrate.add_argument("--propose-engagement"); migrate.add_argument("--apply-proposal", type=Path); migrate.add_argument("--destination", type=Path); migrate.add_argument("--operator-id"); migrate.add_argument("--recorded-at")
    accept = subcommands.add_parser("accept-report", help="operator review and acceptance of a current revision-bound report")
    accept.add_argument("--engagement", type=Path, required=True); accept.add_argument("--report-id", required=True); accept.add_argument("--operator-id", required=True); accept.add_argument("--reason", required=True); accept.add_argument("--recorded-at", required=True)
    submission = subcommands.add_parser("record-submission", help="record separate operator-authored external submission text")
    submission.add_argument("--engagement", type=Path, required=True); submission.add_argument("--report-id", required=True); submission.add_argument("--file", type=Path, required=True); submission.add_argument("--program", required=True); submission.add_argument("--operator-id", required=True); submission.add_argument("--recorded-at", required=True)
    report = subcommands.add_parser("generate-report", help="operator-only generation of a revision-bound internal report")
    report.add_argument("--engagement", type=Path, required=True); report.add_argument("--finding-id", required=True); report.add_argument("--revision", type=int, required=True); report.add_argument("--include-claim", action="append", default=[]); report.add_argument("--omit-claim", action="append", default=[]); report.add_argument("--operator-id", required=True); report.add_argument("--recorded-at", required=True)
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
            "init": command_init,
            "append-event": command_append_event,
            "append-attempt": command_append_attempt,
            "register-artifact": command_register_artifact,
            "repair-ledger-tail": command_repair_tail,
            "reduce": command_reduce,
            "render": command_render,
            "preflight": command_preflight,
            "record-memory": command_record_memory,
            "export-telemetry": command_export_telemetry,
            "score-telemetry": command_score_telemetry,
            "close": command_close,
            "migrate": command_migrate,
            "accept-report": command_accept_report,
            "record-submission": command_record_submission,
            "generate-report": command_generate_report,
            "render-proof": command_render_proof,
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
