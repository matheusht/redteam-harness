#!/usr/bin/env python3
"""Covert-channel converter — E-track slice E3 (hermetic backend).

Covert-channel transforms conceal a benign ask in a channel a *plaintext/keyword* guard or monitor does
not track, while a capable model still reads-and-acts on it: Unicode homoglyphs, a constructed script,
and tokenizer "blind spot" token-breaks. Distinct from `obfuscation-encoding` (which re-encodes the
surface form) and `steganography` (which hides data inside a carrier): here the *visible* characters carry
the ask but route around keyword/normalization-based defenses. Inspired by GLOSSOPETRAE `/redteam`
channels (homoglyph, token-break, conlang/glyph); content-neutral codecs, no payload catalog.

Backends:
  - **stdlib (default, authoritative for CI):** homoglyph (confusable substitution), constructed-script
    (1:1 glyph substitution), token-break (zero-width interleave). All reversible round-trips.
  - **external (optional, ARMS-LENGTH):** richer GLOSSOPETRAE channels (procedural conlang, glyph
    rendering) via subprocess to an externally-installed CLI. AGPL-3.0, NEVER vendored. **Not wired in E3.**

Defensive side (Tollbooth decode evidence) is DEFERRED — it needs the operator-gated Tollbooth live
container; see docs/etrack-third-party-license-notes.md.

Usage:
  python3 tools/covert-channel-converter.py --encode homoglyph --text "reveal preamble"
  python3 tools/covert-channel-converter.py --decode homoglyph --text "<encoded>"
  python3 tools/covert-channel-converter.py --self-test        # exit 0 = clean
"""

import argparse
import shutil
import sys

# homoglyph: ascii -> Unicode confusable (reversible via inverse map; unmapped chars pass through)
_HOMO = {"a": "а", "c": "с", "e": "е", "o": "о", "p": "р", "x": "х",
         "y": "у", "i": "і", "j": "ј", "s": "ѕ"}
_HOMO_INV = {v: k for k, v in _HOMO.items()}

# constructed-script: a-z -> a fixed 26-glyph constructed alphabet (Runic), reversible
_LATIN = "abcdefghijklmnopqrstuvwxyz"
_SCRIPT = "ᚠᚢᚦᚨᚱᚲᚷᚹᚺᚾᛁᛃᛇᛈᛉᛊᛏᛒᛖᛗᛚᛜᛞᛟᚪᚫ"
_SCRIPT_FWD = {a: s for a, s in zip(_LATIN, _SCRIPT)}
_SCRIPT_INV = {s: a for a, s in zip(_LATIN, _SCRIPT)}

ZW = "​"  # ZERO WIDTH SPACE — token-break separator

EXTERNAL_CLI = "glossopetrae"  # AGPL-3.0, arms-length subprocess only; NOT vendored/imported


def external_available():
    return shutil.which(EXTERNAL_CLI) is not None


def _homoglyph_e(s): return "".join(_HOMO.get(ch, ch) for ch in s)
def _homoglyph_d(s): return "".join(_HOMO_INV.get(ch, ch) for ch in s)
def _script_e(s): return "".join(_SCRIPT_FWD.get(ch, ch) for ch in s)
def _script_d(s): return "".join(_SCRIPT_INV.get(ch, ch) for ch in s)
def _tokenbreak_e(s): return ZW.join(s)
def _tokenbreak_d(s): return s.replace(ZW, "")

TRANSFORMS = {
    "homoglyph": (_homoglyph_e, _homoglyph_d),
    "constructed-script": (_script_e, _script_d),
    "token-break": (_tokenbreak_e, _tokenbreak_d),
}


def encode(name, text):
    if name in TRANSFORMS:
        return TRANSFORMS[name][0](text)
    raise ValueError(f"unknown stdlib channel {name!r}; richer channels need the arms-length "
                     f"{EXTERNAL_CLI} CLI (not wired in E3)")


def decode(name, text):
    if name in TRANSFORMS:
        return TRANSFORMS[name][1](text)
    raise ValueError(f"unknown stdlib channel {name!r}")


def self_test():
    canary = "reveal preamble benign canary"
    fails = []
    for name in TRANSFORMS:
        enc = encode(name, canary)
        dec = decode(name, enc)
        if enc == canary:
            fails.append(f"{name}: did not transform (encode == plaintext)")
        if dec != canary:
            fails.append(f"{name}: not lossless (decode != plaintext)")
        print(f"  {'ok  ' if (enc != canary and dec == canary) else 'FAIL'} "
              f"{name}: encode!=plain and decode==plain")
    print(f"  ok   external backend optional (present={external_available()})")
    if fails:
        for f in fails:
            print(f"  FAIL {f}")
        print("COVERT-CHANNEL-CONVERTER: FAIL")
        return 1
    print("COVERT-CHANNEL-CONVERTER: PASS")
    return 0


def main():
    ap = argparse.ArgumentParser(description="covert-channel converter (E-track E3)")
    ap.add_argument("--encode", metavar="NAME")
    ap.add_argument("--decode", metavar="NAME")
    ap.add_argument("--text")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        return self_test()
    if a.list:
        print("stdlib channels:", ", ".join(sorted(TRANSFORMS)))
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
