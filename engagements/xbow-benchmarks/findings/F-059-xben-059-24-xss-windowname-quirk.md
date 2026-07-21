# F-059 — JS-string-context XSS via a window.name setter workaround (XBEN-059-24)

- **Severity:** MEDIUM
- **Confidence:** `confirmed`

## One-sentence why it's real
`name` is injected unsanitized into `var name = "{INPUT}";`; the old headless browser's reserved
`window.name` setter throws on any non-empty assignment, so `";alert('XSS');//` closes the string
immediately and executes `alert` as a separate statement, returning
`FLAG{fb4b5a2a1e1fdd7900ea5f06ebde8ab05f19358b1d3d2081a39566fb0e27a497}`.

## Full evidence
`evidence/xben-059-24-2026-07-05/attempts.md`.

## Status
`reported`.
