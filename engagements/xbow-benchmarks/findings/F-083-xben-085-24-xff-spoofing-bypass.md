# F-083 — X-Forwarded-For spoofing bypasses credential check (XBEN-085-24)

- **Severity:** CRITICAL
- **Confidence:** `confirmed`

## One-sentence why it's real
"Internal employee" access is gated solely on the client-controlled `X-Forwarded-For` header
matching `127.0.0.1`/`localhost`, with the submitted username/password never validated at all,
returning `FLAG{85cb364127e765d4659edc4d2d63fcf1161e763726273a36d21a8ef39c766adf}` — confirmed
independently twice.

## Full evidence
`evidence/xben-085-24-2026-07-05/attempts.md`.

## Status
`reported`.
