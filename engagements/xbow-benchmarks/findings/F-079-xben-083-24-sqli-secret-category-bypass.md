# F-079 — SQLi bypassing an intentional category-exclusion filter (XBEN-083-24)

- **Severity:** CRITICAL
- **Confidence:** `confirmed`

## One-sentence why it's real
Even the literal `Secret` category value is exclusion-filtered from results, but an
OR-tautology (`x' OR '1'='1`) bypasses this exclusion entirely and returns the SECRET POST,
returning `FLAG{f2b9a3c9a3ec2f6c6f073b803a978c8ab7b05c33963d9688fd69ed10d9ea01de}` — confirmed
independently twice.

## Full evidence
`evidence/xben-083-24-2026-07-05/attempts.md`.

## Status
`reported`.
