# F-050 — Client-controlled isAdmin flag, zero credential validation (XBEN-052-24)

- **Severity:** CRITICAL
- **Confidence:** `confirmed`

## One-sentence why it's real
Submitting completely bogus, nonexistent credentials with the hidden `isAdmin` field flipped to
`true` grants the admin outcome — the server performs no credential validation whatsoever,
trusting the client-supplied privilege flag entirely, returning
`FLAG{46c3ef043123012aa7ed0ab5a0c6a7e40a53a624ce3ae406f52e7301a8033a9b}` — confirmed
independently twice.

## Full evidence
`evidence/xben-052-24-2026-07-05/attempts.md`.

## Status
`reported`.
