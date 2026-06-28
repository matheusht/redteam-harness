#!/usr/bin/env python3
"""Steganography converter + detector — E-track slice E2 (hermetic text/zero-width backend).

Steganography hides a benign canary *inside* carrier content so a probe can test whether a target
decodes-and-acts on hidden instructions its visible-text guard never saw — and, on the defensive side,
whether hidden data can be DETECTED in target output / ingested content / evidence.

Two sides, both content-neutral (no payload catalog; the tool only hides/recovers text it is given):
  - **embed/extract** — the offensive transform (test the target's robustness to hidden input).
  - **detect** — the defensive analyzer (flag hidden data; feeds evidence). Tools are sensors, not judges.

Two backends:
  - **stdlib (default, authoritative for CI):** zero-width-Unicode text stego — encodes secret bytes as
    invisible ZWSP/ZWNJ characters appended to a carrier. Deterministic, lossless, visible text unchanged.
  - **external (optional, ARMS-LENGTH):** ST3GG image/audio/document LSB stego + its richer detectors,
    reached by subprocess to an externally-installed CLI. AGPL-3.0, NEVER vendored/imported
    (see docs/etrack-third-party-license-notes.md). **Not wired in E2.**

Usage:
  python3 tools/stego-converter.py --embed   --carrier "hello there" --secret "canary"
  python3 tools/stego-converter.py --extract --text "<stego text>"
  python3 tools/stego-converter.py --detect  --text "<text>"
  python3 tools/stego-converter.py --self-test        # exit 0 = clean
"""

import argparse
import shutil
import sys

ZERO = "​"   # ZERO WIDTH SPACE      -> bit 0
ONE = "‌"    # ZERO WIDTH NON-JOINER -> bit 1
ZW_ALPHABET = (ZERO, ONE)

EXTERNAL_CLI = "st3gg"  # AGPL-3.0, arms-length subprocess only; NOT vendored/imported


def external_available():
    """True iff the optional ST3GG CLI is installed on PATH (never bundled)."""
    return shutil.which(EXTERNAL_CLI) is not None


def embed(carrier, secret):
    """Append `secret` to `carrier` encoded as invisible zero-width chars. Visible text is unchanged."""
    bits = "".join(format(b, "08b") for b in secret.encode())
    hidden = "".join(ONE if bit == "1" else ZERO for bit in bits)
    return carrier + hidden


def strip_zw(text):
    """The visible text: the carrier with all zero-width stego chars removed."""
    return "".join(ch for ch in text if ch not in ZW_ALPHABET)


def extract(text):
    """Recover the secret from zero-width chars; '' if none present."""
    bits = "".join("1" if ch == ONE else "0" for ch in text if ch in ZW_ALPHABET)
    if not bits:
        return ""
    nbytes = len(bits) // 8
    data = bytes(int(bits[i * 8:(i + 1) * 8], 2) for i in range(nbytes))
    return data.decode(errors="replace")


def detect(text):
    """Defensive analyzer: report hidden zero-width data. A sensor signal, NOT a verdict."""
    zw_count = sum(1 for ch in text if ch in ZW_ALPHABET)
    return {"has_stego": zw_count > 0, "zw_count": zw_count, "est_secret_bytes": zw_count // 8}


def self_test():
    carrier = "This is an ordinary benign sentence."
    secret = "stego-canary-benign"
    stego = embed(carrier, secret)
    fails = []
    if strip_zw(stego) != carrier:
        fails.append("visible text changed (carrier not preserved under embed)")
    if extract(stego) != secret:
        fails.append("not lossless (extract != secret)")
    if not detect(stego)["has_stego"]:
        fails.append("detector missed embedded stego")
    if detect(carrier)["has_stego"]:
        fails.append("detector false-positive on clean carrier")
    for label, ok in [
        ("embed preserves visible text", strip_zw(stego) == carrier),
        ("extract is lossless", extract(stego) == secret),
        ("detector finds hidden data", detect(stego)["has_stego"]),
        ("detector clean on plain carrier", not detect(carrier)["has_stego"]),
    ]:
        print(f"  {'ok  ' if ok else 'FAIL'} {label}")
    print(f"  ok   external backend optional (present={external_available()})")
    if fails:
        for f in fails:
            print(f"  FAIL {f}")
        print("STEGO-CONVERTER: FAIL")
        return 1
    print("STEGO-CONVERTER: PASS")
    return 0


def main():
    ap = argparse.ArgumentParser(description="steganography converter + detector (E-track E2)")
    ap.add_argument("--embed", action="store_true")
    ap.add_argument("--extract", action="store_true")
    ap.add_argument("--detect", action="store_true")
    ap.add_argument("--carrier")
    ap.add_argument("--secret")
    ap.add_argument("--text")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        return self_test()
    if a.embed:
        print(embed(a.carrier or "", a.secret or ""))
        return 0
    if a.extract:
        print(extract(a.text or sys.stdin.read()))
        return 0
    if a.detect:
        print(detect(a.text or sys.stdin.read()))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
