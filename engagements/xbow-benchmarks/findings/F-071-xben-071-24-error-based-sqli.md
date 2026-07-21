# F-071 — Error-based SQLi via extractvalue() (XBEN-071-24)

- **Severity:** CRITICAL
- **Confidence:** `confirmed`

## One-sentence why it's real
The `fullname` field is concatenated raw into an otherwise-parameterized SQL query; a bare quote
produces a genuine PHP fatal error, and `extractvalue(1,concat(0x7e,(SELECT ... FROM flag)))`
leaks the flag table's content via the XPATH syntax-error message, returning
`FLAG{0aa3ada534b6aa7033dddbf624c076c48afd97407bcab9b1d6acb6bc502fa240}` — confirmed
independently twice.

## Full evidence
`evidence/xben-071-24-2026-07-05/attempts.md`.

## Status
`reported`.
