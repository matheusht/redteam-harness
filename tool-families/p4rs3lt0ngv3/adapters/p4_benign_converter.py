#!/usr/bin/env python3
"""P4RS3LT0NGV3 benign converter (P3) — LOCAL, hermetic, benign-canary-only.

A converter-class keyhole: it transforms a BENIGN CANARY and returns roundtrip evidence. It is NOT the
upstream encoder and does NOT vendor AGPL source — it implements a tiny set of approved, reversible
transforms with the Python stdlib, so encode/decode can be exercised hermetically without any upstream
checkout. It NEVER executes against a target, never decodes arbitrary/raw payloads into Plane 1/2, and
never emits a verdict. The broker runs the canary against the target; the oracle adjudicates.

Guards:
  * benign-canary-only — input must be a short, printable, prefixed canary; anything else is refused.
  * approved-transform-only — only ids in APPROVED (reversible, benign) run.
  * roundtrip + negative control — every result carries plaintext/transformed/decoded/roundtrip_ok and a
    negative control (decoding the un-encoded plaintext must NOT reproduce the canary).
"""

import base64
import codecs

MAX_CANARY_LEN = 256
BENIGN_PREFIXES = ("benign-", "canary-", "p4-canary-")
# approved reversible benign transforms (a small toy set; the real catalog lives behind the adapter)
APPROVED = ("base64", "hex", "rot13", "reverse")


def _envelope(action, available, **rest):
    out = {"action": action, "authority": "sensor_only", "available": bool(available),
           "source": "local_hermetic"}
    out.update(rest)
    return out


def is_benign_canary(s):
    return (isinstance(s, str) and 0 < len(s) <= MAX_CANARY_LEN and s.isprintable()
            and s.lower().startswith(BENIGN_PREFIXES))


def _encode(s, transform):
    if transform == "base64":
        return base64.b64encode(s.encode("utf-8")).decode("ascii")
    if transform == "hex":
        return s.encode("utf-8").hex()
    if transform == "rot13":
        return codecs.encode(s, "rot_13")
    if transform == "reverse":
        return s[::-1]
    raise ValueError("unapproved transform")


def _decode(s, transform):
    try:
        if transform == "base64":
            return base64.b64decode(s.encode("ascii"), validate=True).decode("utf-8")
        if transform == "hex":
            return bytes.fromhex(s).decode("utf-8")
        if transform == "rot13":
            return codecs.decode(s, "rot_13")
        if transform == "reverse":
            return s[::-1]
    except Exception:
        return None
    return None


def _guard(canary, transform, action):
    if transform not in APPROVED:
        return _envelope(action, False, reason=f"transform not approved: {transform}")
    if not is_benign_canary(canary):
        return _envelope(action, False, reason="input is not an approved benign canary")
    return None


def encode_benign(canary, transform):
    bad = _guard(canary, transform, "encode_benign")
    if bad:
        return bad
    return _envelope("encode_benign", True, transform=transform,
                     roundtrip={"plaintext": canary, "transform": transform,
                                "transformed": _encode(canary, transform)})


def decode_if_possible(artifact, transform):
    """Advisory decode evidence — best effort, never a verdict."""
    if transform not in APPROVED:
        return _envelope("decode_if_possible", False, reason=f"transform not approved: {transform}")
    decoded = _decode(artifact, transform)
    return _envelope("decode_if_possible", True, advisory=True,
                     evidence={"transform": transform, "decoded_is_some": decoded is not None})


def transform_roundtrip(canary, transform):
    """Encode then decode a benign canary; emit roundtrip + negative-control evidence."""
    bad = _guard(canary, transform, "transform_roundtrip")
    if bad:
        return bad
    transformed = _encode(canary, transform)
    decoded = _decode(transformed, transform)
    # negative control: decoding the UN-encoded plaintext must NOT reproduce the canary
    nc_decoded = _decode(canary, transform)
    reproduced = nc_decoded == canary
    return _envelope("transform_roundtrip", True,
                     roundtrip={"plaintext": canary, "transform": transform,
                                "transformed": transformed, "decoded": decoded,
                                "roundtrip_ok": decoded == canary,
                                "negative_control": {"ran": True, "reproduced_canary": reproduced,
                                                     "control_holds": not reproduced}})


if __name__ == "__main__":
    import json
    import sys
    c = sys.argv[1] if len(sys.argv) > 1 else "benign-canary-demo"
    t = sys.argv[2] if len(sys.argv) > 2 else "base64"
    print(json.dumps(transform_roundtrip(c, t), indent=2))
