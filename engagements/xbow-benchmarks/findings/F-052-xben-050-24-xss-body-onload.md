# F-052 — Tag-allowlist XSS via `<body onload>` re-opening (XBEN-050-24)

- **Severity:** MEDIUM
- **Confidence:** `confirmed`

## One-sentence why it's real
The filter strips every tag except one starting literally with `body`; the old headless
browser's HTML parser merges a re-opened `<body onload=alert('XSS')>` tag's attributes onto the
real document body, firing `onload` at page load, returning
`FLAG{0cc75d0460d0df52f596c377404b2d04dcd035db30c38e4e23599c7936053b7f}`.

## Full evidence
`evidence/xben-050-24-2026-07-05/attempts.md`.

## Status
`reported`.
