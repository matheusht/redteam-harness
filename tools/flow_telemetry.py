#!/usr/bin/env python3
"""Deterministic, non-authoritative Decision-0006 flow export and runtime adapters."""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from decision6_capabilities import artifact_variant, classify_event
from engagement_records import RecordError, canonical_json_bytes, detect_secret_classes, load_json, sha256_bytes, sha256_file, validate_record
from engagement_state import atomic_write, read_ledger, reduce_engagement

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "evals/research-kernel/decision6/measurement-contract.json"
CAPABILITIES = ROOT / "engine/operation-capabilities.json"
OBSERVATION_FIELDS = {
    "schema_version", "document_type", "engagement_id", "run_id", "session_id", "runtime_name", "runtime_version",
    "recorded_at", "observation_kind", "operation_id", "candidate_id", "hypothesis_id", "attempt_id",
    "duration_seconds", "input_tokens", "output_tokens", "cost_usd",
}
FORBIDDEN_KEYS = {"prompt", "response", "tool_arguments", "arguments", "command", "command_line", "environment", "environment_values", "env", "file_contents", "credentials", "payload", "target_payload", "target_payloads"}
STAGES = ("recon", "routing", "search", "adjudication", "review", "cleanup", "unknown")
RUNTIME_DIMS = ("turns", "model_calls", "tool_calls", "input_tokens", "output_tokens", "cost_usd", "active_seconds", "runtime_wait_seconds")
KERNEL_DIMS = ("kernel_wall_seconds", "kernel_model_seconds", "kernel_tool_seconds", "kernel_human_review_seconds", "kernel_input_tokens", "kernel_output_tokens", "kernel_cost_usd", "dependency_blocked_seconds")
ACTION_STAGES = {"review-preflight": "recon", "repair-ledger-tail": "recon", "record-operator-prior": "search", "reopen": "search", "revise-finding": "adjudication", "record-review": "review", "generate-report": "review", "accept-report": "review", "record-submission": "review", "record-cleanup": "cleanup", "record-memory": "cleanup", "close": "cleanup", "reattest-scope": "unknown"}


def _reject_forbidden(value: Any) -> None:
    if isinstance(value, dict):
        forbidden = FORBIDDEN_KEYS.intersection(value)
        if forbidden: raise RecordError("flow_telemetry_forbidden_field", ",".join(sorted(forbidden)))
        for child in value.values(): _reject_forbidden(child)
    elif isinstance(value, list):
        for child in value: _reject_forbidden(child)
    elif isinstance(value, str) and detect_secret_classes(value.encode("utf-8", errors="replace")):
        raise RecordError("flow_telemetry_secret_shape", "runtime observation contains a forbidden secret shape")


def _validate_observation(value: dict[str, Any]) -> dict[str, Any]:
    _reject_forbidden(value)
    if set(value) != OBSERVATION_FIELDS:
        raise RecordError("flow_observation_fields_invalid", f"missing={sorted(OBSERVATION_FIELDS-set(value))}; extra={sorted(set(value)-OBSERVATION_FIELDS)}")
    errors = validate_record(value, "flow-telemetry")
    if errors: raise RecordError("flow_observation_invalid", value.get("run_id", "unknown"), errors)
    return value


def normalize_generic(value: Any) -> list[dict[str, Any]]:
    records = value if isinstance(value, list) else [value]
    if not records or any(not isinstance(item, dict) for item in records): raise RecordError("flow_observation_input_invalid", "expected one object or a non-empty array")
    return sorted((_validate_observation(dict(item)) for item in records), key=lambda item: (item["recorded_at"], item["run_id"], item["session_id"], item["observation_kind"], item.get("operation_id") or ""))


def normalize_claude_code(value: Any, engagement_id: str) -> list[dict[str, Any]]:
    records = value if isinstance(value, list) else [value]
    allowed = {"run_id", "session_id", "runtime_version", "timestamp", "kind", "operation_id", "candidate_id", "hypothesis_id", "attempt_id", "duration_ms", "input_tokens", "output_tokens", "cost_usd"}
    normalized: list[dict[str, Any]] = []
    for item in records:
        if not isinstance(item, dict) or not set(item).issubset(allowed) or not {"run_id", "session_id", "timestamp", "kind"}.issubset(item):
            raise RecordError("claude_code_observation_fields_invalid", "adapter accepts sanitized metric fields only")
        _reject_forbidden(item)
        normalized.append({
            "schema_version": 1, "document_type": "runtime_observation", "engagement_id": engagement_id,
            "run_id": item["run_id"], "session_id": item["session_id"], "runtime_name": "claude-code",
            "runtime_version": item.get("runtime_version"), "recorded_at": item["timestamp"], "observation_kind": item["kind"],
            "operation_id": item.get("operation_id"), "candidate_id": item.get("candidate_id"), "hypothesis_id": item.get("hypothesis_id"), "attempt_id": item.get("attempt_id"),
            "duration_seconds": None if item.get("duration_ms") is None else item["duration_ms"] / 1000,
            "input_tokens": item.get("input_tokens"), "output_tokens": item.get("output_tokens"), "cost_usd": item.get("cost_usd"),
        })
    return normalize_generic(normalized)


def _load_observations(path: Path | None, engagement_id: str) -> list[dict[str, Any]]:
    if path is None: return []
    text = path.read_text(encoding="utf-8"); stripped = text.strip()
    if not stripped: return []
    try: value = json.loads(stripped)
    except json.JSONDecodeError: value = [json.loads(line) for line in text.splitlines() if line.strip()]
    observations = normalize_generic(value)
    if any(item["engagement_id"] != engagement_id for item in observations): raise RecordError("flow_observation_cross_engagement", engagement_id)
    return observations


def _coverage(values: list[float | int | None]) -> dict[str, Any]:
    measured = [value for value in values if value is not None]
    return {"value": sum(measured) if measured else None, "records": len(values), "measured": len(measured)}


def export_flow(engagement: Path, observations_path: Path | None = None) -> dict[str, Any]:
    engagement = Path(os.path.abspath(engagement)); state = reduce_engagement(engagement); events = read_ledger(engagement, "event"); attempts = read_ledger(engagement, "attempt"); artifacts = read_ledger(engagement, "artifact"); observations = _load_observations(observations_path, state["engagement_id"])
    contract = load_json(CONTRACT); stage_by_event = {event_type: stage for stage, event_types in contract["stage_mapping"].items() for event_type in event_types}
    event_stage = {event["event_id"]: stage_by_event.get(event["event_type"], "unknown") for event in events}; candidate_stage = {key: "routing" for key in state["candidates"]}; hypothesis_stage = {key: "search" for key in state["hypotheses"]}; attempt_stage = {item["attempt_id"]: "search" for item in attempts}
    operation_counts = {tier: 0 for tier in ("notebook", "authority", "real_world")}; event_tiers: dict[str, str] = {}
    for event in events:
        capability = classify_event(event["event_type"], event.get("payload", {})); tier = capability["tier"]; operation_counts[tier] += 1; event_tiers[event["event_id"]] = tier
    operation_counts["notebook"] += len(attempts)
    for artifact in artifacts:
        tier = artifact.get("operation_class") or ("notebook" if artifact_variant(artifact) == "clear_local" else "real_world"); operation_counts[tier] += 1
    stage_observations = {stage: [] for stage in STAGES}
    for observation in observations:
        stage = event_stage.get(observation.get("operation_id")) or candidate_stage.get(observation.get("candidate_id")) or hypothesis_stage.get(observation.get("hypothesis_id")) or attempt_stage.get(observation.get("attempt_id")) or "unknown"; stage_observations[stage].append(observation)
    blocked_by_stage: dict[str, list[float | None]] = {stage: [] for stage in STAGES}
    for request in state["authority_requests"].values():
        start = datetime.fromisoformat(request["requested_at"].replace("Z", "+00:00")); end = datetime.fromisoformat(request["resolved_at"].replace("Z", "+00:00")) if request["resolved_at"] else None; blocked_by_stage[ACTION_STAGES.get(request["action_kind"], "unknown")].append(None if end is None else (end-start).total_seconds())
    summaries: dict[str, Any] = {}
    for stage in STAGES:
        rows = stage_observations[stage]; model_rows = [row for row in rows if row["observation_kind"] == "model_call"]; stage_attempts = attempts if stage == "search" else []
        summaries[stage] = {
            "operation_count": sum(value == stage for value in event_stage.values()) + (len(attempts) if stage == "search" else 0) + (len(artifacts) if stage == "unknown" else 0),
            "turns": _coverage([1 for row in rows if row["observation_kind"] == "turn"]),
            "model_calls": _coverage([1 for row in model_rows]), "tool_calls": _coverage([1 for row in rows if row["observation_kind"] == "tool_call"]),
            "input_tokens": _coverage([row["input_tokens"] for row in model_rows]), "output_tokens": _coverage([row["output_tokens"] for row in model_rows]), "cost_usd": _coverage([row["cost_usd"] for row in model_rows]),
            "active_seconds": _coverage([row["duration_seconds"] for row in rows if row["observation_kind"] != "runtime_wait"]),
            "runtime_wait_seconds": _coverage([row["duration_seconds"] for row in rows if row["observation_kind"] == "runtime_wait"]),
            "kernel_wall_seconds": _coverage([item["cost"]["wall_seconds"] for item in stage_attempts]), "kernel_model_seconds": _coverage([item["cost"]["model_seconds"] for item in stage_attempts]), "kernel_tool_seconds": _coverage([item["cost"]["tool_seconds"] for item in stage_attempts]), "kernel_human_review_seconds": _coverage([item["cost"]["human_review_seconds"] for item in stage_attempts]),
            "kernel_input_tokens": _coverage([item["cost"].get("input_tokens") for item in stage_attempts]), "kernel_output_tokens": _coverage([item["cost"].get("output_tokens") for item in stage_attempts]), "kernel_cost_usd": _coverage([item["cost"].get("cost_usd") for item in stage_attempts]), "dependency_blocked_seconds": _coverage(blocked_by_stage[stage]),
        }
    intervals = []
    for request_id, request in sorted(state["authority_requests"].items()):
        start = datetime.fromisoformat(request["requested_at"].replace("Z", "+00:00")); end = datetime.fromisoformat(request["resolved_at"].replace("Z", "+00:00")) if request["resolved_at"] else None
        in_interval = lambda stamp: datetime.fromisoformat(stamp.replace("Z", "+00:00")) >= start and (end is None or datetime.fromisoformat(stamp.replace("Z", "+00:00")) <= end)
        overlap = sum(event_tiers[event["event_id"]] == "notebook" and event.get("payload", {}).get("authority_request_ref") != request_id and in_interval(event["recorded_at"]) for event in events) + sum(in_interval(item["recorded_at"]) for item in attempts) + sum((item.get("operation_class") or ("notebook" if artifact_variant(item) == "clear_local" else "real_world")) == "notebook" and in_interval(item["created_at"]) for item in artifacts)
        runtime_overlap = sum(in_interval(item["recorded_at"]) for item in observations)
        intervals.append({"request_id": request_id, "lane_id": request["lane_id"], "status": request["status"], "requested_at": request["requested_at"], "resolved_at": request["resolved_at"], "duration_seconds": None if end is None else (end-start).total_seconds(), "overlapping_notebook_operations": overlap, "overlapping_runtime_observations": runtime_overlap})
    identities = sorted({(row["runtime_name"], row["runtime_version"], row["run_id"], row["session_id"]) for row in observations}, key=lambda item: tuple("" if value is None else value for value in item))
    coverage = {dimension: {"records": sum(summary[dimension]["records"] for summary in summaries.values()), "measured": sum(summary[dimension]["measured"] for summary in summaries.values())} for dimension in RUNTIME_DIMS + KERNEL_DIMS}
    linked_runtime = sum(bool((item.get("operation_id") in event_stage) or (item.get("candidate_id") in candidate_stage) or (item.get("hypothesis_id") in hypothesis_stage) or (item.get("attempt_id") in attempt_stage)) for item in observations); coverage["runtime_record_binding"] = {"records": len(observations), "measured": linked_runtime}
    complete_events = sum(event.get("actor") == event.get("provenance", {}).get("actor") and bool(event.get("operation_class")) and bool(event.get("provenance", {}).get("session_id")) for event in events); complete_attempts = sum(item.get("actor") == item.get("provenance", {}).get("actor") and bool(item.get("operation_class")) and bool(item.get("provenance", {}).get("session_id")) for item in attempts); complete_artifacts = sum(bool(item.get("operation_class")) and bool(item.get("producer_session_id")) and bool(item.get("precreation_classification_event_ref")) for item in artifacts)
    result = {
        "schema_version": 1, "document_type": "flow_export", "export_id": f"flow-{state['engagement_id']}-v1", "engagement_id": state["engagement_id"], "classification": "flow_telemetry",
        "source_hashes": {"events": sha256_file(engagement/"events.jsonl"), "attempts": sha256_file(engagement/"attempts.jsonl"), "artifacts": sha256_file(engagement/"artifacts.jsonl"), "capability_matrix": sha256_file(CAPABILITIES), "measurement_contract": sha256_file(CONTRACT), "runtime_observations": sha256_file(observations_path) if observations_path else sha256_bytes(canonical_json_bytes([]))},
        "runtime_identities": [{"runtime_name": item[0], "runtime_version": item[1], "run_id": item[2], "session_id": item[3], "trust": "advisory"} for item in identities], "operation_counts": operation_counts, "stage_summaries": summaries, "authority_intervals": intervals,
        "backtracks": sum(event["event_type"] == "engagement.reopened" or (event["event_type"] == "operator_prior.recorded" and bool(event["payload"].get("reopen_hypothesis_id"))) or (event["event_type"] == "hypothesis.status_changed" and event["payload"].get("status") == "queued") for event in events),
        "review_interventions": sum(event["event_type"].startswith("review.") or event["event_type"] in {"claim.adjudicated", "operator.review_recorded", "environment.review_recorded"} for event in events),
        "record_completeness": {"records": len(events)+len(attempts)+len(artifacts), "complete": complete_events+complete_attempts+complete_artifacts}, "coverage": coverage,
        "policy": {"gates_held_is_primary": True, "required_gates_are_stalls": False, "automatic_authority_changes": False, "automatic_tier_changes": False, "automatic_truth_changes": False, "automatic_routing_changes": False, "automatic_severity_changes": False, "automatic_report_changes": False, "live_causal_claims": False, "cross_runtime_average": False},
    }
    errors = validate_record(result, "flow-telemetry")
    if errors: raise RecordError("flow_export_invalid", state["engagement_id"], errors)
    return result


def self_test() -> int:
    checks: list[tuple[str, bool]] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve(); fixture = root/"engagement"; fixture.mkdir(); (fixture/"scope.md").write_text("# Scope\n\n## Surfaces in scope\n- Local.\n## Benign safe-objective set\n- Observe.\n## Escalation ceiling\n- None.\n## Impact-demo authorization\n- No.\n## Accounts / fixtures\n- None.\n## Authorization\n- Operator: operator-flow\n- Date: 2026-07-10\n- Signed: [x]\n- Record kernel: `decision-0005-v1`\n")
        from engagement_state import initialize_engagement
        initialize_engagement(fixture, "2026-07-10T00:00:00Z")
        observation = {"schema_version":1,"document_type":"runtime_observation","engagement_id":"engagement","run_id":"run-flow","session_id":"session-flow","runtime_name":"claude-code","runtime_version":"2.1.211","recorded_at":"2026-07-10T00:00:01Z","observation_kind":"model_call","operation_id":None,"candidate_id":None,"hypothesis_id":None,"attempt_id":None,"duration_seconds":None,"input_tokens":0,"output_tokens":None,"cost_usd":None}
        path=root/"observations.json"; path.write_bytes(canonical_json_bytes([observation])); first=export_flow(fixture,path); second=export_flow(fixture,path)
        checks.append(("byte deterministic export", canonical_json_bytes(first)==canonical_json_bytes(second)))
        unknown=first["stage_summaries"]["unknown"]; checks.append(("null never becomes zero", unknown["active_seconds"]=={"value":None,"records":1,"measured":0} and unknown["input_tokens"]["value"]==0 and unknown["input_tokens"]["measured"]==1))
        checks.append(("telemetry policy is non-authoritative", all(first["policy"][key] is False for key in first["policy"] if key!="gates_held_is_primary") and first["classification"]=="flow_telemetry"))
        forged_evidence = dict(first); forged_evidence["classification"] = "flow_evidence"; checks.append(("live export cannot claim flow evidence", bool(validate_record(forged_evidence, "flow-telemetry"))))
        checks.append(("trace completeness is coverage, not assumed perfection", first["record_completeness"]["complete"] < first["record_completeness"]["records"]))
        blocked=False
        try: normalize_claude_code({"run_id":"run-x","session_id":"session-x","timestamp":"2026-07-10T00:00:00Z","kind":"turn","prompt":"forbidden"},"engagement")
        except RecordError: blocked=True
        checks.append(("Claude adapter rejects transcript content", blocked))
        smuggled = dict(observation); smuggled["runtime_version"] = "this is free form transcript content"; checks.append(("runtime identity labels cannot smuggle free text", bool(validate_record(smuggled, "flow-telemetry"))))
    for name, passed in checks: print(f"  {'ok  ' if passed else 'FAIL'} {name}")
    print(f"FLOW TELEMETRY SELF-TEST: {'PASS' if all(value for _,value in checks) else 'FAIL'}")
    return 0 if all(value for _,value in checks) else 1


def _reject_governed_output(path: Path) -> None:
    absolute=Path(os.path.abspath(path))
    for parent in (absolute.parent,*absolute.parents[1:]):
        try: marker=parent/"scope.md"
        except OSError: continue
        if marker.exists() or marker.is_symlink(): raise RecordError("flow_output_governed_path_forbidden", str(absolute))


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--self-test",action="store_true"); sub=parser.add_subparsers(dest="command")
    normalize=sub.add_parser("normalize"); normalize.add_argument("--adapter",choices=["generic","claude-code"],required=True); normalize.add_argument("--input",type=Path,required=True); normalize.add_argument("--engagement-id"); normalize.add_argument("--output",type=Path,required=True)
    export=sub.add_parser("export"); export.add_argument("--engagement",type=Path,required=True); export.add_argument("--observations",type=Path); export.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    try:
        if args.self_test:return self_test()
        if args.command=="normalize":
            value=load_json(args.input); records=normalize_generic(value) if args.adapter=="generic" else normalize_claude_code(value,args.engagement_id or "")
            _reject_governed_output(args.output); atomic_write(args.output.absolute(),canonical_json_bytes(records)); return 0
        if args.command=="export":
            engagement=Path(os.path.abspath(args.engagement)); output=Path(os.path.abspath(args.output))
            try: output.relative_to(engagement)
            except ValueError: pass
            else: raise RecordError("flow_output_governed_path_forbidden", str(output))
            atomic_write(output,canonical_json_bytes(export_flow(engagement,args.observations))); return 0
        parser.error("choose normalize or export")
    except (RecordError,ValueError,OSError,json.JSONDecodeError) as exc:
        error=exc.as_dict() if isinstance(exc,RecordError) else {"code":"flow_telemetry_error","message":str(exc),"details":[]}; print(canonical_json_bytes({"valid":False,"error":error}).decode(),end=""); return 1
    return 2

if __name__=="__main__": raise SystemExit(main())
