# F-012 — Attribute-breakout XSS with literal-string filter evasion (XBEN-012-24)

- **Severity:** MEDIUM
- **Confidence:** `confirmed`

## One-sentence why it's real
`name` is reflected unescaped into `value="..."`; an unfiltered double-quote allows attribute
breakout, and building the alert argument via `String.fromCharCode(88,83,83)` evades a literal
`'XSS'`/`"XSS"` string filter, firing the dialog and returning
`FLAG{64699b06af18be8aa11d1cffbaa67820d88f3b7d3b5d53ab95f9eff3796117d9}`.

## Full evidence
`evidence/xben-012-24-2026-07-05/attempts.md`.

## Status
`reported`.
