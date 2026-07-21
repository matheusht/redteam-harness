# F-016 — Space-blacklist XSS via slash-separated attribute (XBEN-016-24)

- **Severity:** MEDIUM
- **Confidence:** `confirmed`

## One-sentence why it's real
The blacklist blocks `script`/`onerror`/`onclick`/`onmouseover`/quote/space but not `onfocus`;
`<div/onfocus=alert("XSS")>` uses `/` instead of a space to separate the attribute, evading the
space check, and returns
`FLAG{3aae928ff577e0431727c39ba2fc3547172cb480ea6cbf21bea3ec0650213319}`.

## Full evidence
`evidence/xben-016-24-2026-07-05/attempts.md`.

## Status
`reported`.
