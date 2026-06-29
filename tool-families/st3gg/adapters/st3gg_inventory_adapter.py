#!/usr/bin/env python3
"""ST3GG runtime inventory adapter — Phase S1 (presence-detect, evidence-only).

Proves we can reach the arms-length upstream ST3GG CLI (`stegg-cli` / `stegg_cli.py`) and report what
it exposes, WITHOUT ever adjudicating. The broker runs this; the oracle decides truth. Output conforms
to schemas/st3gg-inventory-result.schema.json.

Arms-length: the AGPL upstream is invoked as an external subprocess (never vendored). When the CLI is
absent the adapter fails HONESTLY as `runtime_unavailable` — it never fabricates tools.

HONESTY NOTE: the upstream CLI is not installed in this workspace, so the `list-tools` / `crypto-status`
output PARSER below is written against an ASSUMED shape (JSON lines, or a `tools:`/`crypto:` json blob)
and is exercised only via a mocked runner in selftest.py. Verify the real shape against an installed
upstream before trusting live output. Resolve the CLI via $ST3GG_CLI or PATH.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys

CLI_ENV = "ST3GG_CLI"
UNAVAILABLE = {"family": "st3gg", "runtime": "stegg-cli", "available_tools": [],
               "crypto_available": False, "runtime_digest": None, "verdict": "runtime_unavailable"}


def find_cli():
    p = os.environ.get(CLI_ENV)
    if p and os.path.isfile(p):
        return p
    for name in ("stegg-cli", "stegg_cli.py"):
        w = shutil.which(name)
        if w:
            return w
    return None


def _digest(path):
    try:
        return hashlib.sha256(open(path, "rb").read()).hexdigest()
    except Exception:
        return None


def _parse_tools(out):
    """Best-effort: a JSON {"tools":[...]} or {"available_tools":[...]} blob, else newline-listed names."""
    try:
        d = json.loads(out)
        if isinstance(d, dict):
            return list(d.get("tools") or d.get("available_tools") or [])
        if isinstance(d, list):
            return [str(x) for x in d]
    except Exception:
        pass
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def _parse_crypto(out):
    try:
        d = json.loads(out)
        if isinstance(d, dict):
            return bool(d.get("crypto_available", d.get("available", False)))
    except Exception:
        pass
    return "available" in out.lower() and "unavailable" not in out.lower()


def inventory(runner=None):
    """Return a schema-valid inventory result. `runner(args)->stdout` is injectable for hermetic tests."""
    cli = find_cli()
    if cli is None and runner is None:
        return dict(UNAVAILABLE)

    def _default_runner(args):
        return subprocess.run([sys.executable, cli] + args, capture_output=True, text=True, timeout=30).stdout

    run = runner or _default_runner
    try:
        tools = _parse_tools(run(["list-tools"]))
        crypto = _parse_crypto(run(["crypto-status"]))
    except Exception:
        return dict(UNAVAILABLE)
    return {"family": "st3gg", "runtime": "stegg-cli", "available_tools": tools,
            "crypto_available": crypto, "runtime_digest": _digest(cli) if cli else "mock",
            "verdict": "evidence_only"}


def main():
    ap = argparse.ArgumentParser(description="ST3GG runtime inventory adapter (S1, evidence-only)")
    ap.add_argument("--json", action="store_true", help="print the inventory result as JSON")
    ap.parse_args()
    print(json.dumps(inventory(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
