#!/usr/bin/env python3
"""P4RS3LT0NGV3 catalog adapter (P2) — READ-ONLY list/inspect, arms-length.

The harness owns authority; this adapter only emits a sensor-only catalog signal. It NEVER encodes,
decodes, executes, or emits a verdict. Two modes:

  * external  — subprocess to a user-installed upstream checkout ($P4_HOME) via Node. If Node or the
    checkout is missing, returns an HONEST non-success ({"available": false, "reason": ...}). Bounded by
    timeout and output size. (Upstream is AGPL and NOT vendored — this only shells out to a local install.)
  * offline   — serve a compact catalog from the family fixtures, so the agent gets list/inspect access
    without loading the entire upstream doc set into context.

`prefer="auto"` uses external when available, else offline. No action here can run encode/decode — that
is the separate benign converter (P3), gated to benign canaries.
"""

import json
import os
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
FAMILY_DIR = os.path.dirname(HERE)
FIXTURES = os.path.join(FAMILY_DIR, "fixtures")

TIMEOUT_S = 10
MAX_OUTPUT_BYTES = 1_000_000
MAX_TRANSFORMS = 64
_ADVANCED_STEMS = ("agent", "promptcraft", "anticlassifier", "tokenade", "fuzzer",
                   "random", "planner", "chain", "rank_", "proposal")


def _envelope(action, available, source, **rest):
    out = {"action": action, "authority": "sensor_only", "available": bool(available), "source": source}
    out.update(rest)
    return out


def _is_advanced(name):
    return isinstance(name, str) and any(s in name for s in _ADVANCED_STEMS)


def _node_available():
    return shutil.which("node") is not None


def _external_cli(p4_home):
    if not p4_home or not os.path.isdir(p4_home):
        return None
    for cand in ("cli/index.js", "bin/p4.js", "index.js"):
        fp = os.path.join(p4_home, cand)
        if os.path.isfile(fp):
            return fp
    return None


def _external_unavailable_reason(p4_home):
    if not p4_home:
        return "no P4_HOME configured (upstream checkout not provided)"
    if not os.path.isdir(p4_home):
        return f"P4_HOME does not exist: {p4_home}"
    if not _node_available():
        return "node runtime not found on PATH"
    if _external_cli(p4_home) is None:
        return "no recognizable P4 CLI entrypoint in P4_HOME"
    return None


def _run_external(cli, args):
    try:
        proc = subprocess.run(["node", cli, *args], capture_output=True, text=True,
                              timeout=TIMEOUT_S, cwd=os.path.dirname(cli))
    except (subprocess.TimeoutExpired, OSError) as e:
        return None, f"external invocation failed: {type(e).__name__}"
    if proc.returncode != 0:
        return None, f"external CLI exit {proc.returncode}"
    raw = (proc.stdout or "")[:MAX_OUTPUT_BYTES]
    try:
        return json.loads(raw), None
    except json.JSONDecodeError:
        return None, "external CLI output was not valid JSON"


def _offline_catalog():
    with open(os.path.join(FIXTURES, "list_transforms.example.json")) as fh:
        return json.load(fh).get("transforms", [])


def list_transforms(prefer="auto", p4_home=None, category=None):
    """Return a compact catalog (sensor-only). Honest non-success if external requested but unavailable."""
    p4_home = p4_home or os.environ.get("P4_HOME")
    use_external = prefer == "external" or (prefer == "auto" and _external_unavailable_reason(p4_home) is None)
    if use_external:
        reason = _external_unavailable_reason(p4_home)
        if reason:
            return _envelope("list_transforms", False, "external_checkout", reason=reason)
        data, err = _run_external(_external_cli(p4_home), ["list", "--json"])
        if err:
            return _envelope("list_transforms", False, "external_checkout", reason=err)
        items = [t for t in data if isinstance(t, dict) and not _is_advanced(t.get("id"))][:MAX_TRANSFORMS]
        return _envelope("list_transforms", True, "external_checkout", transforms=items)
    items = [t for t in _offline_catalog() if not _is_advanced(t.get("id"))]
    if category:
        items = [t for t in items if t.get("category") == category]
    return _envelope("list_transforms", True, "offline_fixture", transforms=items[:MAX_TRANSFORMS])


def inspect_transform(transform_id, prefer="auto", p4_home=None):
    """Inspect one transform. Fail closed (available:false + reason) on unknown/advanced id."""
    if _is_advanced(transform_id):
        return _envelope("inspect_transform", False, "offline_fixture",
                         reason="advanced module is not an inspectable transform (blocked_until gate)")
    p4_home = p4_home or os.environ.get("P4_HOME")
    use_external = prefer == "external" or (prefer == "auto" and _external_unavailable_reason(p4_home) is None)
    if use_external:
        reason = _external_unavailable_reason(p4_home)
        if reason:
            return _envelope("inspect_transform", False, "external_checkout", reason=reason)
        data, err = _run_external(_external_cli(p4_home), ["inspect", str(transform_id), "--json"])
        if err:
            return _envelope("inspect_transform", False, "external_checkout", reason=err)
        if not isinstance(data, dict) or not data.get("id"):
            return _envelope("inspect_transform", False, "external_checkout", reason="unknown transform id")
        return _envelope("inspect_transform", True, "external_checkout", transform=data)
    match = next((t for t in _offline_catalog() if t.get("id") == transform_id), None)
    if not match:
        return _envelope("inspect_transform", False, "offline_fixture", reason="unknown transform id")
    enriched = dict(match)
    enriched.setdefault("expansion", 1.0)
    return _envelope("inspect_transform", True, "offline_fixture", transform=enriched)


if __name__ == "__main__":
    import sys
    act = sys.argv[1] if len(sys.argv) > 1 else "list_transforms"
    if act == "inspect_transform":
        print(json.dumps(inspect_transform(sys.argv[2] if len(sys.argv) > 2 else ""), indent=2))
    else:
        print(json.dumps(list_transforms(), indent=2))
