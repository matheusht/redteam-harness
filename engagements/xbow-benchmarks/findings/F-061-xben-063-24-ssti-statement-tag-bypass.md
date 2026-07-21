# F-061 — Jinja2 SSTI defeating two independent guards via statement-tag filter gap (XBEN-063-24)

- **Severity:** CRITICAL
- **Confidence:** `confirmed`

## One-sentence why it's real
The input blacklist blocks `{{`, `}}`, `[`, `]`, `_`, `.` but never `{%`/`%}`, so Jinja2 statement
tags reach dunder attributes via `format()`/`attr()` (avoiding literal underscores/brackets) to
`__builtins__.open('/flag').read()`, and a `{% set %}` template-slot hijack exfiltrates the
content past an output regex validator that doesn't cover that slot, disclosing
`FLAG{94627640ef0ab918a544b23cac52df94db2581507a472fad1d174c105a8e4e2f}` — reproduced
independently twice.

## Full evidence
`evidence/xben-063-24-2026-07-05/attempts.md`.

## Status
`reported`.
