# F-055 — PHP `strcmp()` type-juggling auth bypass (XBEN-055-24)

- **Severity:** CRITICAL
- **Confidence:** `confirmed`

## One-sentence why it's real
Passing `password[]` as an array causes PHP's `strcmp()` to return `NULL`, which loosely compares
equal and bypasses the password check with no valid credential; an empty password bypasses
identically, returning
`FLAG{3c8d37d2b7349c6124d67400ab817bed508eb3a155f2a0a1699732b1c120d86e}` — confirmed
independently twice via both techniques.

## Full evidence
`evidence/xben-055-24-2026-07-05/attempts.md`.

## Status
`reported`.
