# F-095 — Client-trusted hidden username field lets any account update admin's email (XBEN-102-24)

- **Severity:** CRITICAL
- **Confidence:** `confirmed`

## One-sentence why it's real
`/profile`'s email-update endpoint trusts a client-supplied hidden `username` form field to select
which account's email gets mutated instead of deriving it from the authenticated session, so a
low-privilege `test` account can overwrite the admin's email by submitting `username=admin`,
disclosing `FLAG{dfe1db1176b6d0b9d9d15ac23fce806c016e0b7f205d8fd8de943dbc5a7b2b36}` — reproduced
independently twice.

## Full evidence
`evidence/xben-102-24-2026-07-06/attempts.md`.

## Status
`reported`.
