#!/usr/bin/env python3
"""ST3GG family selftest — Phase S1 (inventory adapter, evidence-only).

Hermetic: exercises the inventory adapter with a MOCKED upstream CLI (no real stegg-cli needed) and the
honest unavailable path, validates both against the result schema, and asserts the output can never carry
a verdict/oracle key. Future phases (S2 sensor, S3 converter, S4 proposals) add their own cases here.
"""

import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA = json.load(open(os.path.join(HERE, "schemas", "st3gg-inventory-result.schema.json")))
FORBIDDEN = ("confirmed", "allow", "success", "oracle_verdict")


def _load(path):
    spec = importlib.util.spec_from_file_location("st3gg_inv", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def schema_problems(obj):
    """Minimal stdlib validation against st3gg-inventory-result.schema.json (no jsonschema dep)."""
    p = []
    for k in SCHEMA["required"]:
        if k not in obj:
            p.append(f"missing {k}")
    if set(obj) - set(SCHEMA["properties"]):
        p.append(f"unexpected keys: {sorted(set(obj) - set(SCHEMA['properties']))}")
    if obj.get("family") != "st3gg" or obj.get("runtime") != "stegg-cli":
        p.append("family/runtime const mismatch")
    if obj.get("verdict") not in ("evidence_only", "runtime_unavailable"):
        p.append(f"verdict not in enum: {obj.get('verdict')}")
    if not isinstance(obj.get("available_tools"), list):
        p.append("available_tools must be a list")
    if not isinstance(obj.get("crypto_available"), bool):
        p.append("crypto_available must be a bool")
    p += [f"carries forbidden key {k}" for k in FORBIDDEN if k in obj]
    return p


def main():
    inv = _load(os.path.join(HERE, "adapters", "st3gg_inventory_adapter.py"))
    fails = []

    # 1) honest unavailable path (no CLI, no runner)
    if os.environ.get(inv.CLI_ENV):
        del os.environ[inv.CLI_ENV]
    unavail = inv.inventory(runner=None) if inv.find_cli() is None else dict(inv.UNAVAILABLE)
    if unavail["verdict"] != "runtime_unavailable" or unavail["available_tools"]:
        fails.append("unavailable path did not fail honestly")
    p1 = schema_problems(unavail)

    # 2) mocked upstream CLI -> evidence_only, tools parsed
    def mock_runner(args):
        if args == ["list-tools"]:
            return json.dumps({"tools": ["detect", "analyze", "capacity", "encode", "decode", "inject-exif"]})
        if args == ["crypto-status"]:
            return json.dumps({"crypto_available": True})
        return ""
    ran = inv.inventory(runner=mock_runner)
    p2 = schema_problems(ran)
    if ran["verdict"] != "evidence_only":
        fails.append(f"mocked run verdict should be evidence_only, got {ran['verdict']}")
    if "detect" not in ran["available_tools"]:
        fails.append("mocked run did not parse available_tools")

    for label, ok in [
        ("unavailable path fails honestly + schema-valid", unavail["verdict"] == "runtime_unavailable" and not p1),
        ("mocked CLI -> evidence_only + tools parsed + schema-valid", ran["verdict"] == "evidence_only"
         and "detect" in ran["available_tools"] and not p2),
        ("no result carries a verdict/oracle key", not any(k in unavail or k in ran for k in FORBIDDEN)),
    ]:
        print(f"  {'ok  ' if ok else 'FAIL'} {label}")
        if not ok:
            fails.append(label)

    for prob in p1 + p2:
        print(f"  FAIL schema: {prob}")
    fails += p1 + p2
    if fails:
        print("ST3GG-SELFTEST (S1): FAIL")
        return 1
    print("ST3GG-SELFTEST (S1): PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
