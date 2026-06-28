#!/usr/bin/env python3
"""Obfuscation/encoding converter — E-track slice E1 (content-neutral transforms).

A converter applies a *reversible, content-neutral* transform to text so a probe can test whether a
target's safety/monitoring pipeline still classifies an **encoded benign canary** the way it classifies
the plaintext. It is the "how" used by the `obfuscation-encoding` technique card; it carries NO payloads
and makes NO judgement (the oracle adjudicates). A transform is just a codec: base64/hex/rot13/etc.

Two backends:
  - **stdlib (default, authoritative for CI):** base64, base32, hex, rot13 — deterministic, lossless,
    no dependency. The `--self-test` exercises only these so CI is hermetic.
  - **external (optional, ARMS-LENGTH):** the richer P4RS3LT0NGV3 transform set, reached by *subprocess*
    to an externally-installed CLI. It is AGPL-3.0 and is NEVER vendored or imported into this repo
    (see docs/etrack-third-party-license-notes.md). Absent → the converter still works on the stdlib set.

Scope fence: transforms are codecs, not a harmful-content catalog. This tool only encodes/decodes text it
is given; it neither stores nor ships any payload corpus.

Usage:
  python3 tools/obfuscation-converter.py --list
  python3 tools/obfuscation-converter.py --encode base64 --text "EVIDENCE-CANARY"
  python3 tools/obfuscation-converter.py --decode base64 --text "RVZJREVOQ0UtQ0FOQVJZ"
  python3 tools/obfuscation-converter.py --self-test        # exit 0 = clean
"""

import argparse
import base64
import codecs
import shutil
import sys

# ---- stdlib transforms: (encode, decode), all lossless round-trips on UTF-8 text ----

def _b64_e(s): return base64.b64encode(s.encode()).decode()
def _b64_d(s): return base64.b64decode(s.encode()).decode()
def _b32_e(s): return base64.b32encode(s.encode()).decode()
def _b32_d(s): return base64.b32decode(s.encode()).decode()
def _hex_e(s): return s.encode().hex()
def _hex_d(s): return bytes.fromhex(s).decode()
def _rot13_e(s): return codecs.encode(s, "rot_13")
def _rot13_d(s): return codecs.decode(s, "rot_13")

STDLIB_TRANSFORMS = {
    "base64": (_b64_e, _b64_d),
    "base32": (_b32_e, _b32_d),
    "hex":    (_hex_e, _hex_d),
    "rot13":  (_rot13_e, _rot13_d),
}

EXTERNAL_CLI = "p4rs3lt0ngv3"  # AGPL-3.0, arms-length subprocess only; NOT vendored/imported


def external_available():
    """True iff the optional external transform CLI is installed on PATH (never bundled)."""
    return shutil.which(EXTERNAL_CLI) is not None


def encode(name, text):
    if name in STDLIB_TRANSFORMS:
        return STDLIB_TRANSFORMS[name][0](text)
    raise ValueError(
        f"unknown stdlib transform {name!r}; external transforms require the arms-length "
        f"{EXTERNAL_CLI} CLI and are not wired in E1 (see license notes)"
    )


def decode(name, text):
    if name in STDLIB_TRANSFORMS:
        return STDLIB_TRANSFORMS[name][1](text)
    raise ValueError(f"unknown stdlib transform {name!r}")


def self_test():
    """Round-trip every stdlib transform on a benign canary; assert it actually obfuscates and is lossless."""
    canary = "EVIDENCE-CANARY-benign-objective-proof"
    fails = []
    for name in STDLIB_TRANSFORMS:
        enc = encode(name, canary)
        dec = decode(name, enc)
        if enc == canary:
            fails.append(f"{name}: did not transform (encode == plaintext)")
        if dec != canary:
            fails.append(f"{name}: not lossless (decode != plaintext)")
        print(f"  ok   {name}: encode!=plain and decode==plain")
    # the external backend must be OPTIONAL: its absence is not a failure
    print(f"  ok   external backend optional (present={external_available()})")
    if fails:
        for f in fails:
            print(f"  FAIL {f}")
        print("OBFUSCATION-CONVERTER: FAIL")
        return 1
    print("OBFUSCATION-CONVERTER: PASS")
    return 0


def main():
    ap = argparse.ArgumentParser(description="content-neutral obfuscation/encoding converter (E-track E1)")
    ap.add_argument("--encode", metavar="NAME")
    ap.add_argument("--decode", metavar="NAME")
    ap.add_argument("--text")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        return self_test()
    if a.list:
        print("stdlib transforms:", ", ".join(sorted(STDLIB_TRANSFORMS)))
        print(f"external backend ({EXTERNAL_CLI}, AGPL, arms-length): "
              f"{'available' if external_available() else 'not installed'}")
        return 0
    if a.encode:
        print(encode(a.encode, a.text or sys.stdin.read().rstrip("\n")))
        return 0
    if a.decode:
        print(decode(a.decode, a.text or sys.stdin.read().rstrip("\n")))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
