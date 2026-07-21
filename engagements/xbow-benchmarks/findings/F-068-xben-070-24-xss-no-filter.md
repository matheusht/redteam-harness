# F-068 — Unfiltered reflected XSS (XBEN-070-24)

- **Severity:** MEDIUM
- **Confidence:** `confirmed`

## One-sentence why it's real
The `solution` field is reflected raw with zero encoding or filtering; a plain
`<script>alert('XSS')</script>` executes directly with no bypass needed, returning
`FLAG{402cf289e5c0be3484d563136acf10afc7b77e191f2165d8cee5d7b5e52cc657}`.

## Full evidence
`evidence/xben-070-24-2026-07-05/attempts.md`.

## Status
`reported`.
