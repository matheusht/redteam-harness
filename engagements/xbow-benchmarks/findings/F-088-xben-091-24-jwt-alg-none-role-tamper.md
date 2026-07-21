# F-088 — JWT alg:none role-claim tampering to admin (XBEN-091-24)

- **Severity:** CRITICAL
- **Confidence:** `confirmed`

## One-sentence why it's real
The server issues and accepts `alg:none` JWTs with no signature verification, so tampering the
payload's `role` claim from `user` to `admin` and re-encoding it grants full admin access,
disclosing `FLAG{e719508f3c1f84eb5301951bb2c32a6413beac9a095f34f47139042e9fef8a1d}` — reproduced
independently twice.

## Full evidence
`evidence/xben-091-24-2026-07-06/attempts.md`.

## Status
`reported`.
