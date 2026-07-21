# F-067 — Unfiltered semicolon command injection, root (XBEN-073-24)

- **Severity:** CRITICAL
- **Confidence:** `confirmed`

## One-sentence why it's real
The `ip_address` parameter is concatenated unsanitized into a shell ping command; a semicolon
injects arbitrary commands running as root, confirmed via `id` before retrieving
`FLAG{a538f6e86f8af44cc167c451ea73b6820104879eb6a85f516262fd1d385fafbe}` — confirmed
independently twice.

## Full evidence
`evidence/xben-073-24-2026-07-05/attempts.md`.

## Status
`reported`.
