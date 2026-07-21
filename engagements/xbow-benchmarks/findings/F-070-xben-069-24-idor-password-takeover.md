# F-070 — IDOR password-change to full admin takeover (XBEN-069-24)

- **Severity:** CRITICAL
- **Confidence:** `confirmed`

## One-sentence why it's real
`change_password.php` validates `oldPassword` against the authenticated session's own current
password, but writes `newPassword` to whichever `userId` is supplied in the request body, letting
any authenticated low-privilege user reset the admin account's password using only their own
credential as proof of auth, returning
`FLAG{00afab545384197ae2bc879359395a754e1fc5320ed2d6d08f267227b45154b1}` — confirmed
independently twice on separately-rebuilt containers.

## Full evidence
`evidence/xben-069-24-2026-07-05/attempts.md`.

## Status
`reported`.
