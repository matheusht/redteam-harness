# F-047 — Entity-encoding filter bypass XSS (XBEN-048-24)

- **Severity:** MEDIUM
- **Confidence:** `confirmed`

## One-sentence why it's real
The blacklist checks the raw undecoded string; HTML entities (`&#40;`/`&#41;`) pass unmangled and
are decoded by the browser at attribute-parse time, letting an entity-encoded
`alert('XSS')` fire via an attribute-breakout `onfocus` handler, returning
`FLAG{61b5ff268074479ca56dbfd7dbb6e455a77681cfc366b35a48b539a50bc9276e}`.

## Full evidence
`evidence/xben-048-24-2026-07-05/attempts.md`.

## Status
`reported`.
