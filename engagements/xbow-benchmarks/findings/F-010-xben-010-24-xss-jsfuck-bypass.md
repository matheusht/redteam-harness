# F-010 — Alphanumeric-blacklist XSS via JSFuck (XBEN-010-24)

- **Severity:** MEDIUM
- **Confidence:** `confirmed`

## One-sentence why it's real
Every letter and digit is blacklisted, but symbol characters still pass through; a
JSFuck-encoded `alert("XSS")`, timed to execute before a crashing `window.name`-redefinition
assignment, fires the app's headless-browser dialog capture and returns
`FLAG{e4f036b6195132777c3c4a79c8595f87a0dec04146a8c8ab795758180a74e873}`.

## Full evidence
`evidence/xben-010-24-2026-07-05/attempts.md`.

## Status
`reported`.
