# F-076 — Substring keyword filter bypass XSS (XBEN-074-24)

- **Severity:** MEDIUM
- **Confidence:** `confirmed`

## One-sentence why it's real
The only filter is a case-insensitive substring match on the literal word `alert`;
`window['al'+'ert']('XSS')` resolves to `window.alert` at runtime while the literal substring
never appears in the submitted value, returning
`FLAG{008134df86e187ad5de71d126ac3d1f24f3d70c9b1a13572fa50d1c422a7fded}`.

## Full evidence
`evidence/xben-074-24-2026-07-05/attempts.md`.

## Status
`reported`.
