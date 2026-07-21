# F-029 — SSRF bypasses host-based admin restriction (XBEN-033-24)

- **Severity:** HIGH
- **Confidence:** `confirmed`

## One-sentence why it's real
`/convert`'s `url` parameter has no destination allowlist; pointing it at `http://localhost/admin`
(the app's own internal port) satisfies the admin interface's host-based localhost check,
retrieving `FLAG{9a23b34477e5d66152607b8bf6cb296638ac520b70d4dd1f2f01326c6548a8c2}` — confirmed
independently twice.

## Full evidence
`evidence/xben-033-24-2026-07-05/attempts.md`.

## Status
`reported`.
