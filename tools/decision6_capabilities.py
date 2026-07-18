#!/usr/bin/env python3
"""Decision-0006 fail-closed command/event capability classification."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Iterable

from engagement_records import RecordError

ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "engine" / "operation-capabilities.json"
TIERS = {"notebook", "authority", "real_world"}
ROLES = {"orchestrator", "hunter", "helper", "reviewer", "operator", "broker", "migration"}
ENTRY_KEYS = {"tier", "allowed_roles", "blocking_scope", "required_evidence", "variants"}


def load_capability_matrix(path: Path = MATRIX_PATH) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RecordError("capability_matrix_invalid", str(exc)) from exc
    problems = validate_capability_matrix(value)
    if problems:
        raise RecordError("capability_matrix_invalid", "; ".join(problems))
    return value


def _validate_entry(name: str, entry: Any) -> list[str]:
    problems: list[str] = []
    if not isinstance(entry, dict) or not set(entry).issubset(ENTRY_KEYS):
        return [f"{name}: invalid/unknown entry fields"]
    tier = entry.get("tier")
    if tier not in TIERS | {"variant_dispatch", "event_dispatch"}:
        problems.append(f"{name}: unknown tier {tier}")
    roles = entry.get("allowed_roles")
    if not isinstance(roles, list) or len(roles) != len(set(roles)) or not set(roles).issubset(ROLES):
        problems.append(f"{name}: invalid allowed roles")
    if entry.get("blocking_scope") not in {"none", "lane_local", "global", "variant_dispatch", "event_dispatch"}:
        problems.append(f"{name}: invalid blocking scope")
    evidence = entry.get("required_evidence")
    if not isinstance(evidence, list) or any(not isinstance(item, str) or not item for item in evidence):
        problems.append(f"{name}: invalid evidence list")
    variants = entry.get("variants")
    if tier == "variant_dispatch":
        if not isinstance(variants, dict) or not variants:
            problems.append(f"{name}: missing variants")
        else:
            for variant, spec in variants.items():
                problems.extend(_validate_entry(f"{name}:{variant}", {"allowed_roles": roles, **spec}))
    elif variants is not None:
        problems.append(f"{name}: variants on fixed tier")
    return problems


def validate_capability_matrix(value: Any, *, public_commands: Iterable[str] | None = None, event_types: Iterable[str] | None = None) -> list[str]:
    if not isinstance(value, dict):
        return ["matrix is not an object"]
    problems: list[str] = []
    if set(value) != {"schema_version", "matrix_id", "tiers", "authority_states", "commands", "events"}:
        problems.append("matrix top-level fields are not closed")
    if value.get("schema_version") != 1 or value.get("matrix_id") != "decision6-operation-capabilities-v1" or set(value.get("tiers", [])) != TIERS:
        problems.append("matrix identity/tiers invalid")
    if value.get("authority_states") != ["pending_authority", "approved", "rejected", "expired", "superseded"]:
        problems.append("authority states invalid")
    commands = value.get("commands", {})
    events = value.get("events", {})
    if not isinstance(commands, dict) or not isinstance(events, dict):
        return problems + ["commands/events must be objects"]
    for name, entry in commands.items():
        problems.extend(_validate_entry(f"command:{name}", entry))
    for name, entry in events.items():
        problems.extend(_validate_entry(f"event:{name}", entry))
    if public_commands is not None:
        missing = sorted(set(public_commands) - set(commands))
        if missing:
            problems.append("unclassified public commands: " + ",".join(missing))
    if event_types is not None:
        missing = sorted(set(event_types) - set(events))
        if missing:
            problems.append("unclassified event types: " + ",".join(missing))
    return problems


def _resolved(entry: dict[str, Any], variant: str | None, operation: str) -> dict[str, Any]:
    if entry["tier"] == "variant_dispatch":
        spec = entry["variants"].get(variant)
        if spec is None:
            raise RecordError("operation_variant_unclassified", f"{operation}:{variant}")
        result = {"operation": operation, "variant": variant, "allowed_roles": list(entry["allowed_roles"]), **copy.deepcopy(spec)}
    elif entry["tier"] == "event_dispatch":
        raise RecordError("event_dispatch_context_required", operation)
    else:
        result = {"operation": operation, "variant": None, **copy.deepcopy(entry)}
    if result["tier"] == "notebook" and "broker" not in result["allowed_roles"]:
        result["allowed_roles"] = [*result["allowed_roles"], "broker"]
    return result


def classify_command(name: str, *, variant: str | None = None, matrix: dict[str, Any] | None = None) -> dict[str, Any]:
    matrix = matrix or load_capability_matrix()
    entry = matrix["commands"].get(name)
    if entry is None:
        raise RecordError("operation_unclassified", f"command:{name}")
    return _resolved(entry, variant, f"command:{name}")


def classify_event(event_type: str, payload: dict[str, Any] | None = None, *, matrix: dict[str, Any] | None = None) -> dict[str, Any]:
    matrix = matrix or load_capability_matrix()
    entry = matrix["events"].get(event_type)
    if entry is None:
        raise RecordError("operation_unclassified", f"event:{event_type}")
    variant = None
    if entry["tier"] == "variant_dispatch" and isinstance(payload, dict):
        variant = payload.get("record_type")
        if event_type == "record.committed" and variant == "review" and payload.get("authority_request_ref"):
            variant = "review-authority"
        if event_type == "artifact.classified":
            variant = "clear_local" if payload.get("advisory_zone") == "clear_local" else "review_required"
    return _resolved(entry, variant, f"event:{event_type}")


def artifact_variant(metadata: dict[str, Any]) -> str:
    """Conservative mechanical floor; caller advisory may escalate but never downgrade it."""
    mechanically_sensitive = (
        metadata.get("contains_executable_capability") is not False
        or metadata.get("acquisition_method") in {"generated_local", "operator", "migration"}
        or metadata.get("sensitivity") == "restricted"
        or metadata.get("redaction_status") == "review_required"
        or metadata.get("media_type") not in {"text/plain", "application/json"}
    )
    return "review_required" if mechanically_sensitive or metadata.get("advisory_zone") != "clear_local" else "clear_local"


def require_actor(capability: dict[str, Any], role: str) -> None:
    if role not in capability.get("allowed_roles", []):
        raise RecordError("actor_capability_invalid", f"{role}:{capability['operation']}:{capability.get('variant')}")


def self_test() -> list[tuple[str, bool, str]]:
    matrix = load_capability_matrix()
    checks: list[tuple[str, bool, str]] = []
    checks.append(("fixed notebook command classifies", classify_command("preflight", matrix=matrix)["tier"] == "notebook", "preflight"))
    checks.append(("record commit dispatches by immutable type", classify_event("record.committed", {"record_type": "review"}, matrix=matrix)["tier"] == "notebook" and classify_event("record.committed", {"record_type": "finding-v3"}, matrix=matrix)["tier"] == "authority", "record.committed"))
    for label, function in (
        ("unknown command fails closed", lambda: classify_command("future-unclassified", matrix=matrix)),
        ("unknown event fails closed", lambda: classify_event("future.unclassified", {}, matrix=matrix)),
        ("unknown variant fails closed", lambda: classify_event("record.committed", {"record_type": "unknown"}, matrix=matrix)),
    ):
        try:
            function(); ok = False; detail = "accepted"
        except RecordError as exc:
            ok = exc.code in {"operation_unclassified", "operation_variant_unclassified"}; detail = exc.code
        checks.append((label, ok, detail))
    forged = classify_event("claim.adjudicated", {}, matrix=matrix)
    try:
        require_actor(forged, "operator"); forged_ok = False
    except RecordError as exc:
        forged_ok = exc.code == "actor_capability_invalid"
    checks.append(("caller role cannot upgrade reviewer capability", forged_ok, "claim.adjudicated"))
    generated = {"advisory_zone": "clear_local", "contains_executable_capability": False, "acquisition_method": "generated_local", "sensitivity": "internal", "redaction_status": "not_needed", "media_type": "text/plain"}
    source = {**generated, "acquisition_method": "source_inspection"}
    checks.append(("caller advisory cannot downgrade mechanical artifact class", artifact_variant(generated) == "review_required" and artifact_variant(source) == "clear_local", str((artifact_variant(generated), artifact_variant(source)))))
    return checks


if __name__ == "__main__":
    failed = []
    for label, ok, detail in self_test():
        print(f"  {'ok  ' if ok else 'FAIL'} {label}" + ("" if ok else f" :: {detail}"))
        if not ok:
            failed.append(label)
    print(f"DECISION-0006 CAPABILITY SELF-TEST: {'PASS' if not failed else 'FAIL'}")
    raise SystemExit(0 if not failed else 1)
