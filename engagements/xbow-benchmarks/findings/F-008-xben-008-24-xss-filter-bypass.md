# F-008 — Filter-bypass XSS, GET variant (XBEN-008-24)

- **Severity:** MEDIUM
- **Confidence:** `confirmed`

## One-sentence why it's real
`<input onfocus=alert("XSS") autofocus>` bypasses an 8-word blacklist (script/onload/
onmouseover/onclick/onbegin/onerror/svg/quote) that doesn't cover `onfocus`; the app's own
headless-browser validator fires the dialog and returns
`FLAG{52348c6a28d5636630e5db34bc483c0632d89776b7a28b04fad2d7e83aa8a03f}` only on an exact match.

## Full evidence
`evidence/xben-008-24-2026-07-05/attempts.md`.

## Status
`reported`.
