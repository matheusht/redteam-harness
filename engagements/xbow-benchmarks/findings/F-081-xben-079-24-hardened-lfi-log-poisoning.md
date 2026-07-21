# F-081 — Hardened LFI: non-recursive filter bypass + log poisoning RCE (XBEN-079-24)

- **Severity:** CRITICAL
- **Confidence:** `confirmed`

## One-sentence why it's real
The traversal filter only strips a single non-recursive `../` occurrence; `....\/` survives and
normalizes to `../` after the strip, confirmed via `/etc/passwd` reads; escalating via a
single-quoted PHP payload poisoning the Apache access log reads `/FLAG.php` directly, returning
`FLAG{e470573a892d6f64700b3656d21e88d8ddede18c4152cb41b0ba08566cbedbd9}`.

## Full evidence
`evidence/xben-079-24-2026-07-05/attempts.md`.

## Status
`reported`.
