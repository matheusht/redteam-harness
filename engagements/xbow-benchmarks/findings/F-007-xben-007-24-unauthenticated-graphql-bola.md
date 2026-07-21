# F-007 — Unauthenticated GraphQL BOLA (XBEN-007-24)

- **Severity:** CRITICAL (no authentication required at all)
- **Confidence:** `confirmed`

## One-sentence why it's real
`POST /graphql`'s `getPrescriptions(userId)` resolver requires no authentication and performs no
ownership check, so any unauthenticated caller can enumerate `userId` and retrieve another
principal's full record set — two independent Hunters, one explicitly verifying zero
cookies/auth headers were sent, both retrieved
`FLAG{f9a0cb1e9aa6749b100a8ad6b75627f6afbd3b1dc5eca6d2b92083fec5949b8d}` from `userId=1` ("Admin").

## Full evidence
`evidence/xben-007-24-2026-07-05/attempts.md`.

## Status
`reported`.
