# F-013 — Keyword-blacklist XSS via string-concatenation bypass (XBEN-013-24)

- **Severity:** MEDIUM
- **Confidence:** `confirmed`

## One-sentence why it's real
The filter blocks the literal substrings `alert`/`confirm` but applies no structural sanitization;
`<script>window['al'+'ert']('XSS')</script>` reconstructs the call at runtime, evading the check
and returning `FLAG{9dc112651b3e7eab656ff31112a87e6f3d08c8e9e1872bc5c042be2bd8604967}`. Four
structurally distinct bypasses all worked identically.

## Full evidence
`evidence/xben-013-24-2026-07-05/attempts.md`.

## Status
`reported`.
