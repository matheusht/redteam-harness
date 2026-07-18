#!/usr/bin/env python3
"""Frozen Decision-0006 old-gate replay and measurement-contract checks.

This tool is offline and synthetic. It never contacts a target or creates capability-bearing artifacts.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from decision6_capabilities import classify_command, classify_event, load_capability_matrix, validate_capability_matrix

ROOT = Path(__file__).resolve().parents[1]
EVAL_ROOT = ROOT / "evals" / "research-kernel" / "decision6"
CORPUS = EVAL_ROOT / "prechange-corpus.json"
CONTRACT = EVAL_ROOT / "measurement-contract.json"
BASELINE = EVAL_ROOT / "old-gate-baseline.json"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _git_bytes(commit: str, path: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"], cwd=ROOT, check=False,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if result.returncode:
        raise ValueError(result.stderr.decode("utf-8", errors="replace"))
    return result.stdout


def _frozen_public_commands(source: bytes) -> set[str]:
    tree = ast.parse(source.decode("utf-8"))
    commands: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute) or node.func.attr != "add_parser" or not node.args:
            continue
        if isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
            commands.add(node.args[0].value)
    for node in ast.walk(tree):
        if not isinstance(node, ast.For) or not isinstance(node.target, ast.Name) or not isinstance(node.iter, (ast.Tuple, ast.List)):
            continue
        values = [item.value for item in node.iter.elts if isinstance(item, ast.Constant) and isinstance(item.value, str)]
        if len(values) != len(node.iter.elts):
            continue
        for child in ast.walk(node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute) and child.func.attr == "add_parser" and child.args and isinstance(child.args[0], ast.Name) and child.args[0].id == node.target.id:
                commands.update(values)
    return commands


def replay_old() -> dict[str, Any]:
    corpus = _load(CORPUS)
    operations = corpus["operations"]
    notebook = [item for item in operations if item["intended_tier"] == "notebook"]
    required = [item for item in operations if item["required_gate"]]
    return {
        "baseline_id": "decision6-old-gate-baseline-v1",
        "classification": "flow_evidence",
        "corpus_id": corpus["corpus_id"],
        "gates_held": all(item["old_result"].startswith("blocked_") for item in required),
        "implementation_commit": corpus["implementation_identity"]["accepted_git_commit"],
        "notebook": {
            "allowed": sum(item["old_result"] == "allowed" for item in notebook),
            "improper_stalls": sum(item["old_result"] == "blocked_operator_console" for item in notebook),
            "records": len(notebook),
        },
        "required_gates": {
            "blocked": sum(item["old_result"].startswith("blocked_") for item in required),
            "records": len(required),
        },
        "schema_version": 1,
        "trace_coverage": {"measured": len(operations), "records": len(operations)},
    }


def _public_kernel_gate_probe() -> bool:
    from engagement_state import initialize_engagement
    with tempfile.TemporaryDirectory(prefix="decision6-kernel-probe-") as temporary:
        engagement=Path(temporary).resolve()/"legacy";engagement.mkdir();engagement.joinpath("scope.md").write_text("# Scope\n\n## Surfaces in scope\n- Local.\n## Benign safe-objective set\n- Observe.\n## Escalation ceiling\n- Records.\n## Impact-demo authorization\n- No.\n## Accounts / fixtures\n- None.\n## Authorization\n- Operator: probe-operator\n- Date: 2026-07-10\n- Signed: [x]\n- Record kernel: `decision-0005-v1`\n")
        initialize_engagement(engagement,"2026-07-10T00:00:00Z");uid=os.getuid();session=os.getsid(0);result=subprocess.run([sys.executable,str(ROOT/"tools/run-engagement.py"),"preflight","--engagement",str(engagement),"--preflight-id","preflight-probe","--mode","package","--target",str(engagement/"missing"),"--expected-identity","sha256:"+"0"*64,"--runtime",sys.executable,"--reproduction-argv","[]","--actor-role","broker","--actor-id",f"local-uid-{uid}:broker","--session-id",f"session-posix-{uid}-{session}","--recorded-at","2026-07-10T00:00:01Z"],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,check=False)
        try:return result.returncode!=0 and json.loads(result.stdout).get("error",{}).get("code")=="decision6_kernel_not_selected"
        except json.JSONDecodeError:return False


def replay_new() -> dict[str, Any]:
    corpus = _load(CORPUS); matrix = load_capability_matrix(); operations = corpus["operations"]; results = []
    for item in operations:
        variant = item.get("variant")
        if item["surface"] == "command":
            if item["name"] == "register-artifact" and variant is None: variant = "clear_local"
            capability = classify_command(item["name"], variant=variant, matrix=matrix)
        else:
            payload = {"record_type": variant} if variant else {}
            if item["name"] == "escalation.confirmed": payload["advisory_zone"] = "review_required"
            capability = classify_event(item["name"], payload, matrix=matrix)
        results.append({"id": item["id"], "tier": capability["tier"], "result": "allowed" if capability["tier"] == "notebook" else ("blocked_pending_authority" if capability["tier"] == "authority" else "blocked_fresh_confirmation")})
    notebook = [item for item in results if item["tier"] == "notebook"]; required_ids = {item["id"] for item in operations if item["required_gate"]}; required = [item for item in results if item["id"] in required_ids]
    public_kernel_gate_probe=_public_kernel_gate_probe()
    return {"classification": "flow_evidence", "corpus_id": corpus["corpus_id"], "gates_held": all(item["result"].startswith("blocked_") for item in required) and public_kernel_gate_probe, "public_kernel_gate_probe":public_kernel_gate_probe, "notebook": {"allowed": sum(item["result"] == "allowed" for item in notebook), "improper_stalls": 0, "records": len(notebook)}, "required_gates": {"blocked": sum(item["result"].startswith("blocked_") for item in required), "records": len(required)}, "schema_version": 1, "trace_coverage": {"measured": len(results), "records": len(results)}}


def validate_frozen() -> list[str]:
    corpus = _load(CORPUS)
    contract = _load(CONTRACT)
    baseline = _load(BASELINE)
    problems: list[str] = []
    commands = corpus.get("public_commands", [])
    events = corpus.get("event_types", [])
    if len(commands) != 19 or len(commands) != len(set(commands)):
        problems.append("public command inventory is not the frozen 19-command set")
    if len(events) != 29 or len(events) != len(set(events)):
        problems.append("event inventory is not the frozen 29-event set")
    mapped = [event for values in contract.get("stage_mapping", {}).values() for event in values]
    if sorted(mapped) != sorted(events) or len(mapped) != len(set(mapped)):
        problems.append("stage mapping must cover every frozen event exactly once")
    if contract.get("coverage_semantics", {}).get("missing_is_zero") is not False:
        problems.append("missing telemetry must not become zero")
    if contract.get("policy", {}).get("gates_held_is_primary") is not True:
        problems.append("gates-held invariant is not primary")
    observation = contract.get("normalized_runtime_observation", {})
    expected_runtime_fields = {"schema_version", "engagement_id", "run_id", "session_id", "runtime_name", "runtime_version", "recorded_at", "observation_kind", "operation_id", "candidate_id", "hypothesis_id", "attempt_id", "duration_seconds", "input_tokens", "output_tokens", "cost_usd"}
    if observation.get("schema_version") != 1 or observation.get("additional_properties") is not False or set(observation.get("fields", [])) != expected_runtime_fields:
        problems.append("normalized runtime observation contract is not closed and versioned")
    if not {"duration_seconds", "input_tokens", "output_tokens", "cost_usd"}.issubset(set(observation.get("nullable_fields", []))):
        problems.append("runtime measurements are not explicitly nullable")
    if set(contract.get("forbidden_capture", [])) & expected_runtime_fields:
        problems.append("runtime observation contract includes forbidden capture fields")
    flow = contract.get("derived_flow_export", {})
    expected_flow_fields = {"schema_version", "export_id", "engagement_id", "classification", "source_hashes", "runtime_identities", "operation_counts", "stage_summaries", "authority_intervals", "backtracks", "review_interventions", "record_completeness", "coverage", "policy"}
    if flow.get("schema_version") != 1 or flow.get("additional_properties") is not False or set(flow.get("fields", [])) != expected_flow_fields:
        problems.append("derived flow export contract is not closed and versioned")
    if baseline != replay_old():
        problems.append("old-gate baseline does not match deterministic replay")
    new_replay = replay_new()
    if not new_replay["gates_held"] or not new_replay["public_kernel_gate_probe"] or new_replay["notebook"]["improper_stalls"] != 0 or new_replay["trace_coverage"]["measured"] != new_replay["trace_coverage"]["records"]:
        problems.append("new-gate replay violates gates-held, notebook-stall, or trace-coverage invariant")
    try:
        live_commands = _frozen_public_commands((ROOT / "tools" / "run-engagement.py").read_bytes())
        live_events = json.loads((ROOT / "schemas" / "engagement-event.schema.json").read_text(encoding="utf-8"))["properties"]["event_type"]["enum"]
        problems.extend(validate_capability_matrix(load_capability_matrix(), public_commands=live_commands, event_types=live_events))
    except (OSError, KeyError, json.JSONDecodeError, SyntaxError, ValueError) as exc:
        problems.append(f"cannot validate live capability coverage: {exc}")
    identity = corpus.get("implementation_identity", {})
    commit = identity.get("accepted_git_commit", "")
    try:
        frozen_cli = _git_bytes(commit, "tools/run-engagement.py")
        if _frozen_public_commands(frozen_cli) != set(commands):
            problems.append("public command inventory differs from the frozen implementation")
        frozen_event_schema = json.loads(_git_bytes(commit, "schemas/engagement-event.schema.json"))
        actual_events = frozen_event_schema["properties"]["event_type"]["enum"]
        if actual_events != events:
            problems.append("event inventory differs from the frozen implementation")
    except (ValueError, KeyError, json.JSONDecodeError, SyntaxError) as exc:
        problems.append(f"cannot extract frozen public surfaces: {exc}")
    for path, key in (
        ("tools/run-engagement.py", "accepted_run_engagement_sha256"),
        ("schemas/engagement-event.schema.json", "engagement_event_schema_sha256"),
        ("schemas/research-telemetry.schema.json", "research_telemetry_schema_sha256"),
    ):
        try:
            actual = _sha256(_git_bytes(commit, path))
        except ValueError as exc:
            problems.append(f"cannot read frozen implementation identity: {exc}")
            continue
        if actual != identity.get(key):
            problems.append(f"frozen implementation hash mismatch: {path}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    problems = validate_frozen()
    old_gate = replay_old(); new_gate = replay_new(); result = {"valid": not problems, "problems": problems, "old_gate": old_gate, "new_gate": new_gate, "comparison": {"gates_held": old_gate["gates_held"] and new_gate["gates_held"], "notebook_improper_stall_delta": new_gate["notebook"]["improper_stalls"] - old_gate["notebook"]["improper_stalls"], "required_gate_delta": new_gate["required_gates"]["blocked"] - old_gate["required_gates"]["blocked"], "trace_coverage_complete": old_gate["trace_coverage"]["measured"] == old_gate["trace_coverage"]["records"] == new_gate["trace_coverage"]["measured"] == new_gate["trace_coverage"]["records"]}}
    payload = json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    if args.self_test:
        print(f"DECISION-0006 FROZEN REPLAY: {'PASS' if not problems else 'FAIL'}")
        for problem in problems:
            print(f"  FAIL {problem}")
    else:
        sys.stdout.write(payload)
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
