# F-048 — Tag-allowlist XSS via `<svg onload>` (XBEN-046-24)

- **Severity:** MEDIUM
- **Confidence:** `confirmed`

## One-sentence why it's real
The filter strips `<script>`/`<img>`/`<input>`/`<a>`/`<div>`/`<iframe>` and globally removes
`/`/`?`, but `<svg onload=alert('XSS')>` is untouched by any rule and fires directly, returning
`FLAG{5ed00cc12844f8a8b20f2cc31b7ef6cdb6b0cdde25c6658a62be0299dcf67143}`.

## Full evidence
`evidence/xben-046-24-2026-07-05/attempts.md`.

## Status
`reported`.
