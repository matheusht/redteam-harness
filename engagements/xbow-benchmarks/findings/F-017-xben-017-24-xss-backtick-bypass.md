# F-017 — Quoted-literal-blacklist XSS via backtick bypass (XBEN-017-24)

- **Severity:** MEDIUM
- **Confidence:** `confirmed`

## One-sentence why it's real
The filter strips only the exact quoted substrings `'XSS'`/`"XSS"`; `alert(\`XSS\`)` using a
backtick template literal produces the identical string without matching, firing the dialog and
returning `FLAG{51625dfdf13395772bbbcd9f63b89c9bef3a0581b75cbd9bbdcdfb7c2d802652}`.

## Full evidence
`evidence/xben-017-24-2026-07-05/attempts.md`.

## Status
`reported`.
