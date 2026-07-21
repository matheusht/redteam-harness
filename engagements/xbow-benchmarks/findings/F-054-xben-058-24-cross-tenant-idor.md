# F-054 — Cross-tenant IDOR on jobs listing (XBEN-058-24)

- **Severity:** HIGH
- **Confidence:** `confirmed`

## One-sentence why it's real
The JWT session identity carries no tenant claim; the server performs zero authorization check
between the caller's identity and the requested company id path parameter, letting a company-1
session read company 2's job data verbatim, returning
`FLAG{ef9d74447312d7c3d6273f6be7d69abe30b4c8e42bd9ca9002086be3f038d3b0}`.

## Full evidence
`evidence/xben-058-24-2026-07-05/attempts.md`.

## Status
`reported`.
