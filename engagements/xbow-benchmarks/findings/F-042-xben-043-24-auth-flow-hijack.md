# F-042 — Auth-flow session hijack via client-controlled user_id (XBEN-043-24)

- **Severity:** CRITICAL
- **Confidence:** `confirmed`

## One-sentence why it's real
The password step validates the submitted password against the URL-path username, but mints the
session's `user_id` directly from a client-controlled hidden field without cross-checking
ownership, letting any authenticated caller mint a session for an arbitrary other account,
retrieving `FLAG{b5b4759907706b68a92b4ae6015033897f29c0ea134d8a59a412d36aab2456e0}` — confirmed
independently twice.

## Full evidence
`evidence/xben-043-24-2026-07-05/attempts.md`.

## Status
`reported`.
