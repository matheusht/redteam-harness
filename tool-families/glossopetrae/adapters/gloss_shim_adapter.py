#!/usr/bin/env python3
"""GLOSSOPETRAE G2 shim adapter — deterministic LOCAL backend over the harness toy converter.

This is the G2 keyhole: it proves the family's action/schema/broker SHAPE against the harness's own
`tools/covert-channel-converter.py` (homoglyph / constructed-script / token-break) BEFORE any upstream
AGPL runtime (G3). No license/runtime variables, fully hermetic.

Authority (conformance + manifest enforced):
  - this adapter is sensor/converter ONLY. Its output is evidence: a transformed BENIGN canary, a
    digest, a roundtrip record. It NEVER emits confirmed/allow/verdict/success. The broker records the
    run; the harness oracle decides truth.

Usage:
  python3 gloss_shim_adapter.py --list
  python3 gloss_shim_adapter.py --encode-benign homoglyph --text "benign-preamble-canary"
  python3 gloss_shim_adapter.py --self-test       # hermetic; exit 0 = clean
  python3 gloss_shim_adapter.py --emit-fixture    # print the example evidence JSON
"""

import argparse
import hashlib
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
_CONV_PATH = os.path.join(ROOT, "tools", "covert-channel-converter.py")

# verdict tokens an external family output may NEVER carry (authority belongs to the oracle/broker)
FORBIDDEN_OUTPUT_KEYS = ("confirmed", "allow", "verdict", "success")
DEFAULT_CANARY = "benign-preamble-canary"
MAX_INPUT = 256  # benign-canary discipline: bounded input only


def _load_converter():
    spec = importlib.util.spec_from_file_location("covert_channel_converter", _CONV_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_CONV = _load_converter()
APPROVED_CHANNELS = sorted(_CONV.TRANSFORMS)


def _digest(s):
    return "sha256:" + hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def list_channels():
    return {"action": "list_channels", "evidence_role": "sensor",
            "channels": APPROVED_CHANNELS,
            "redaction": {"raw_payload_stored": False, "notes": "inventory only"}}


def inspect_channel(channel):
    if channel not in _CONV.TRANSFORMS:
        return {"action": "inspect_channel", "channel_id": channel, "evidence_role": "sensor",
                "result": "unsupported_channel",
                "error": f"unknown local channel {channel!r}; richer channels need the G3 external adapter"}
    return {"action": "inspect_channel", "channel_id": channel, "evidence_role": "sensor",
            "result": "profiled", "reversible": True,
            "redaction": {"raw_payload_stored": False, "notes": "profile only"}}


def encode_benign(channel, text=DEFAULT_CANARY):
    """Encode a BENIGN canary through a local channel. Returns evidence (digests + roundtrip), no raw."""
    if channel not in _CONV.TRANSFORMS:
        return {"action": "encode_benign", "channel_id": channel, "evidence_role": "converter",
                "result": "unsupported_channel",
                "error": f"unknown local channel {channel!r}; not wired in the G2 shim"}
    if not isinstance(text, str) or not (0 < len(text) <= MAX_INPUT):
        return {"action": "encode_benign", "channel_id": channel, "evidence_role": "converter",
                "result": "rejected_input", "error": f"input must be 1..{MAX_INPUT} chars (benign canary)"}
    encoded = _CONV.encode(channel, text)
    recovered = _CONV.decode(channel, encoded)
    bytes_in = len(text.encode("utf-8"))
    bytes_out = len(encoded.encode("utf-8"))
    return {
        "action": "encode_benign",
        "channel_id": channel,
        "evidence_role": "converter",
        "result": "encoded",
        "input_ref": _digest(text),
        "artifact_ref": _digest(encoded),
        "roundtrip": {"attempted": True, "recovered_equals_input": recovered == text},
        "cost": {"bytes_in": bytes_in, "bytes_out": bytes_out,
                 "expansion_ratio": round(bytes_out / bytes_in, 3) if bytes_in else 0},
        "redaction": {"raw_payload_stored": False,
                      "notes": "digests only; raw artifact not written to Plane 1/2"},
    }


def decode_if_possible(channel, artifact):
    if channel not in _CONV.TRANSFORMS:
        return {"action": "decode_if_possible", "channel_id": channel, "evidence_role": "converter",
                "result": "unsupported_channel", "error": f"unknown local channel {channel!r}"}
    recovered = _CONV.decode(channel, artifact)
    return {"action": "decode_if_possible", "channel_id": channel, "evidence_role": "converter",
            "result": "decoded", "recovered_ref": _digest(recovered),
            "redaction": {"raw_payload_stored": False, "notes": "decoded digest only"}}


def roundtrip_check(channel, text=DEFAULT_CANARY):
    out = encode_benign(channel, text)
    return {"action": "roundtrip_check", "channel_id": channel, "evidence_role": "sensor",
            "result": out.get("result"),
            "roundtrip": out.get("roundtrip", {"attempted": False, "recovered_equals_input": False})}


# ---- authority guards (the G2 acceptance proofs) ----

def _walk_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _walk_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_keys(v)


def output_has_verdict_key(output):
    """A consumer must NOT be able to read a verdict out of this evidence."""
    keys = {str(k).lower() for k in _walk_keys(output)}
    return bool(keys & set(FORBIDDEN_OUTPUT_KEYS))


def would_be_treated_as_finding(output):
    """Broker/oracle test: GLOSS output is evidence, never a finding. A finding needs a verdict; this
    output has none, so a consumer cannot promote it to a finding on the adapter's say-so."""
    return output_has_verdict_key(output)


def example_evidence():
    return encode_benign("homoglyph", DEFAULT_CANARY)


def self_test():
    fails = []
    outputs = []

    # 1. every approved channel round-trips the benign canary AND actually transforms it
    for ch in APPROVED_CHANNELS:
        out = encode_benign(ch, DEFAULT_CANARY)
        outputs.append(out)
        if out.get("result") != "encoded":
            fails.append(f"{ch}: expected encoded, got {out.get('result')}")
        if not out.get("roundtrip", {}).get("recovered_equals_input"):
            fails.append(f"{ch}: roundtrip did not recover input")
        if out.get("input_ref") == out.get("artifact_ref"):
            fails.append(f"{ch}: artifact digest equals input digest (no transform)")
        print(f"  {'ok  ' if out.get('result') == 'encoded' else 'FAIL'} encode_benign {ch}: "
              f"roundtrip={out.get('roundtrip', {}).get('recovered_equals_input')}")

    # 2. malformed channel fails CLOSED (honest non-success, no exception, no verdict)
    bad = encode_benign("definitely-not-a-channel", DEFAULT_CANARY)
    outputs.append(bad)
    closed = bad.get("result") == "unsupported_channel"
    fails += [] if closed else ["malformed channel did not fail closed"]
    print(f"  {'ok  ' if closed else 'FAIL'} malformed channel fails closed -> {bad.get('result')}")

    # 3. oversize input rejected (benign-canary bound)
    big = encode_benign("homoglyph", "x" * (MAX_INPUT + 1))
    rej = big.get("result") == "rejected_input"
    fails += [] if rej else ["oversize input not rejected"]
    print(f"  {'ok  ' if rej else 'FAIL'} oversize input rejected -> {big.get('result')}")

    # 4. NO output may carry a verdict key, and none may be treated as a finding
    for out in outputs:
        if output_has_verdict_key(out):
            fails.append(f"{out.get('action')}/{out.get('channel_id')}: output carries a verdict key")
        if would_be_treated_as_finding(out):
            fails.append(f"{out.get('action')}/{out.get('channel_id')}: evidence treated as finding")
    print(f"  {'ok  ' if not any('verdict' in f or 'finding' in f for f in fails) else 'FAIL'} "
          f"no output carries a verdict / is treated as a finding")

    if fails:
        for f in fails:
            print(f"  FAIL {f}")
        print("GLOSS-SHIM-ADAPTER: FAIL")
        return 1
    print("GLOSS-SHIM-ADAPTER: PASS")
    return 0


def main():
    ap = argparse.ArgumentParser(description="GLOSSOPETRAE G2 shim adapter (local, hermetic)")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--encode-benign", metavar="CHANNEL")
    ap.add_argument("--decode-if-possible", metavar="CHANNEL")
    ap.add_argument("--text")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--emit-fixture", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        return self_test()
    if a.emit_fixture:
        print(json.dumps(example_evidence(), indent=2, ensure_ascii=True))
        return 0
    if a.list:
        print(json.dumps(list_channels(), indent=2))
        return 0
    if a.encode_benign:
        print(json.dumps(encode_benign(a.encode_benign, a.text or DEFAULT_CANARY), indent=2))
        return 0
    if a.decode_if_possible:
        print(json.dumps(decode_if_possible(a.decode_if_possible, a.text or ""), indent=2))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
