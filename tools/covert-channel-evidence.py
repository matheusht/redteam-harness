#!/usr/bin/env python3
"""Covert-channel decode-evidence scanner — E-track E3 (defensive / evidence side, hermetic core).

The defensive mirror of E1/E2/E3: given RAW captured flow text (ephemeral, pre-redaction, inside the
Tollbooth boundary), detect hidden/covert/encoded channels and surface a SANITIZED evidence signal —
which channel was present, and whether decoding surfaces an EXPECTED BENIGN canary. It emits NO raw
content and NO secrets; only the channel type + a boolean. It is a SENSOR, never a judge (no verdict
key); the oracle/broker adjudicate.

This is the hermetic core of "E3 Tollbooth decode evidence". Only the live traffic SOURCE (the
operator-gated Tollbooth container) is external; here it is exercised with synthetic flows. Richer
covert decoding (GLOSSOPETRAE conlang/glyph) would attach arms-length later. Decoders are reused from
the harness's own stdlib converters.

Usage:
  python3 tools/covert-channel-evidence.py --self-test
  python3 tools/covert-channel-evidence.py --flows raw_flows.json --expect-canary benign-preamble-canary
"""

import argparse
import importlib.util
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(modname, filename):
    path = os.path.join(ROOT, "tools", filename)
    spec = importlib.util.spec_from_file_location(modname, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_obf = _load("_obf", "obfuscation-converter.py")
_cov = _load("_cov", "covert-channel-converter.py")
_steg = _load("_steg", "stego-converter.py")

ZW_CHARS = {"​", "‌", "‍", "﻿"}
B64_RE = re.compile(r"[A-Za-z0-9+/]{16,}={0,2}")
FORBIDDEN_KEYS = ("verdict", "confirmed", "allow", "authorizes")


def detect_channels(text):
    ch = []
    if any(c in ZW_CHARS for c in text):
        ch.append("zero-width")
    if any(c in _cov._HOMO_INV for c in text):
        ch.append("homoglyph")
    if any(c in _cov._SCRIPT_INV for c in text):
        ch.append("constructed-script")
    for m in B64_RE.findall(text):
        try:
            if _obf.decode("base64", m).isprintable():
                ch.append("base64-likely")
                break
        except Exception:
            pass
    return ch


def _decode_candidates(text):
    cands = [text]
    try:
        cands.append(_steg.extract(text))
    except Exception:
        pass
    for name in ("homoglyph", "token-break", "constructed-script"):
        try:
            cands.append(_cov.decode(name, text))
        except Exception:
            pass
    for name in ("base64", "base32", "hex", "rot13"):
        try:
            cands.append(_obf.decode(name, text))
        except Exception:
            pass
    for m in B64_RE.findall(text):
        try:
            cands.append(_obf.decode("base64", m))
        except Exception:
            pass
    return cands


def scan_flow(flow, expect_canary):
    """Return a SANITIZED evidence record for one raw flow — no raw text, no secrets."""
    text = flow.get("text", "")
    decoded_present = any(expect_canary in c for c in _decode_candidates(text)) if expect_canary else None
    return {
        "kind": "covert_evidence",       # sensor signal, NON-authoritative
        "authoritative": False,
        "flow_ref": flow.get("ref"),
        "channels_detected": detect_channels(text),
        "decoded_expected_canary_present": decoded_present,
    }


def scan(flows, expect_canary):
    return [scan_flow(f, expect_canary) for f in flows]


def _golden_flows(canary):
    return [
        {"ref": "f1", "text": _cov.encode("homoglyph", f"see {canary}")},
        {"ref": "f2", "text": _steg.embed("an ordinary carrier", canary)},
        {"ref": "f3", "text": _obf.encode("base64", f"see {canary}")},
        {"ref": "f4", "text": "ordinary clean text nothing hidden here at all"},
    ]


def self_test():
    canary = "benign-preamble-canary"
    results = scan(_golden_flows(canary), canary)
    by = {r["flow_ref"]: r for r in results}
    checks = [
        ("homoglyph flow detected + decoded", "homoglyph" in by["f1"]["channels_detected"]
         and by["f1"]["decoded_expected_canary_present"]),
        ("zero-width stego flow detected + decoded", "zero-width" in by["f2"]["channels_detected"]
         and by["f2"]["decoded_expected_canary_present"]),
        ("base64 flow detected + decoded", "base64-likely" in by["f3"]["channels_detected"]
         and by["f3"]["decoded_expected_canary_present"]),
        ("clean flow is clean", by["f4"]["channels_detected"] == []
         and not by["f4"]["decoded_expected_canary_present"]),
    ]
    blob = json.dumps(results)
    sanitized = (canary not in blob                      # no raw decoded payload echoed
                 and "carrier" not in blob               # no raw flow text echoed
                 and not any(k in blob for k in FORBIDDEN_KEYS))
    fails = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"  {'ok  ' if ok else 'FAIL'} {name}")
    print(f"  {'ok  ' if sanitized else 'FAIL'} evidence is sanitized (no raw text/canary, no judge key)")
    if fails or not sanitized:
        print("COVERT-CHANNEL-EVIDENCE: FAIL")
        return 1
    print("COVERT-CHANNEL-EVIDENCE: PASS")
    return 0


def main():
    ap = argparse.ArgumentParser(description="covert-channel decode-evidence scanner (E-track E3)")
    ap.add_argument("--flows", help="path to a raw-flows JSON (ephemeral; pre-redaction)")
    ap.add_argument("--expect-canary")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        return self_test()
    if a.flows:
        with open(a.flows) as fh:
            flows = json.load(fh).get("flows", [])
        print(json.dumps(scan(flows, a.expect_canary), indent=2))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
