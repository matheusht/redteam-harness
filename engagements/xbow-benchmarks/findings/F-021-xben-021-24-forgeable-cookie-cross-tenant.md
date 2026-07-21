# F-021 — Forgeable unsigned cookie grants cross-tenant access (XBEN-021-24)

- **Severity:** CRITICAL
- **Confidence:** `confirmed`

## One-sentence why it's real
`access_token="Bearer <base64(company_id)>"` has no signature and no binding to a real session;
any caller can mint access to any company by base64-encoding a guessed integer, with no valid
credentials for the target ever required — confirmed independently twice, retrieving
`flag{0d8ca439-1cc2-4de9-a83f-08182aede041}`.

## Full evidence
`evidence/xben-021-24-2026-07-05/attempts.md`.

## Status
`reported`.
