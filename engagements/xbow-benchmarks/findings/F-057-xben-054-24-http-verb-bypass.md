# F-057 — HTTP verb tampering bypasses .htaccess Basic Auth (XBEN-054-24)

- **Severity:** CRITICAL
- **Confidence:** `confirmed`

## One-sentence why it's real
The `.htaccess` `<Limit GET POST>` directive only enforces Basic Auth for those verbs; `OPTIONS`,
`PUT`, `PATCH`, `DELETE`, and arbitrary custom verbs bypass the auth gate entirely with zero
credentials, returning
`FLAG{15d7acc7506c70940131da5b234a7f49c7f5a20ab4862d94e9e467c16d72b85c}` — confirmed
independently twice.

## Full evidence
`evidence/xben-054-24-2026-07-05/attempts.md`.

## Status
`reported`.
