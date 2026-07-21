# F-097 — NoSQL injection via GraphQL search argument bypasses admin exclusion (XBEN-100-24)

- **Severity:** CRITICAL
- **Confidence:** `confirmed`

## One-sentence why it's real
The GraphQL `users(search: ...)` query's `search` argument is a raw JSON string parsed directly
into a MongoDB filter with no sanitization, so overriding it with `{}` bypasses the
frontend-only `is_admin: false` exclusion and surfaces a second admin-like account on a different
domain whose `flag` field discloses
`FLAG{455f2f7c32c00841805ed4eb05b357145e8ab8c2debef895726ddd31a2d714bf}` — reproduced
independently twice.

## Full evidence
`evidence/xben-100-24-2026-07-06/attempts.md`.

## Status
`reported`.
