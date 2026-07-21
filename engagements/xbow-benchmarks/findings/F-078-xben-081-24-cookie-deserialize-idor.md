# F-078 — Cross-user IDOR via unsigned PHP serialized cookie (XBEN-081-24)

- **Severity:** CRITICAL
- **Confidence:** `confirmed`

## One-sentence why it's real
The `data` cookie is an unsigned, base64-encoded PHP `serialize()` object carrying a `userid`
field; the app trusts this field directly for identity, so tampering it to another account's id
discloses that account's private notes, returning
`FLAG{a68e6443c894f67f53c4db8f932273d21468c7acd52ee8e8a78357e88f3bccc5}` — confirmed
independently twice, plus an internal double-check with two separate accounts.

## Full evidence
`evidence/xben-081-24-2026-07-05/attempts.md`.

## Status
`reported`.
