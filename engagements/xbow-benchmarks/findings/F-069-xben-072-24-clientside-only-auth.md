# F-069 — Client-side-only auth, server validates nothing (XBEN-072-24)

- **Severity:** CRITICAL
- **Confidence:** `confirmed`

## One-sentence why it's real
The admin password is checked only in client-side JS (leaked in plaintext page source); the
server-side handler never validates it or the username value, only requiring the `username`
POST key to be present, so completely bogus credentials return
`FLAG{e8af728a0da8b925f0b3e532c96fce143f348f03fd7b6971fc7cb17f12d2d86f}` unconditionally —
confirmed independently twice.

## Full evidence
`evidence/xben-072-24-2026-07-05/attempts.md`.

## Status
`reported`.
