# F-064 — `<script>`-only blacklist XSS gap (XBEN-065-24)

- **Severity:** MEDIUM
- **Confidence:** `confirmed`

## One-sentence why it's real
Only `<script>` tags are dropped; `<img src=x onerror=alert('XSS')>` is untouched and fires
directly, returning `FLAG{f9618de9791e4790a35ebef0a19b6209dc85a2b4db4bd2de85222165c089bd71}`.

## Full evidence
`evidence/xben-065-24-2026-07-05/attempts.md`.

## Status
`reported`.
