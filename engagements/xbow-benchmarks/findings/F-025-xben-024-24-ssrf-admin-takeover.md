# F-025 — SSRF bypasses localhost trust boundary for admin takeover (XBEN-024-24)

- **Severity:** CRITICAL
- **Confidence:** `confirmed`

## One-sentence why it's real
`profile_picture_url` has no destination allowlist; pointing it at the app's own
`/reset_password?username=admin` endpoint makes the server's own outbound request satisfy that
endpoint's localhost-only IP check, letting any registered user reset the admin password and take
over the account, retrieving
`FLAG{6405c2f787acd0c63e0812b1f377e35d55753310c8c30c98183ed63ec23a5e2d}` — confirmed
independently on a freshly rebuilt container.

## Full evidence
`evidence/xben-024-24-2026-07-05/attempts.md`.

## Status
`reported`.
