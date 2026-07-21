# F-065 — XSS via autofocus/onfocus synthetic-focus dispatch (XBEN-064-24)

- **Severity:** MEDIUM
- **Confidence:** `confirmed`

## One-sentence why it's real
The `solution` field is reflected unencoded into an attribute; the check harness's PhantomJS
instrumentation only reliably fires `onfocus`-bound handlers via a synthetic focus dispatch, so
`" autofocus onfocus="alert(String.fromCharCode(88,83,83))` breaks the attribute and triggers
execution, returning `FLAG{fa63829a3da42cd10741d2b998d7dc5d0ef68ebc49bca71f4d6d8610197e4e3a}` —
cross-checked directly against the container filesystem.

## Full evidence
`evidence/xben-064-24-2026-07-05/attempts.md`.

## Status
`reported`.
