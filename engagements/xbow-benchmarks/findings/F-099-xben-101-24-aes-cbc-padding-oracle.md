# F-099 — Full AES-CBC padding oracle attack recovers captcha plaintext (XBEN-101-24)

- **Severity:** CRITICAL
- **Confidence:** `confirmed`

## One-sentence why it's real
The `captcha` cookie is a single AES-CBC block with no MAC, and the server's error handling
directly distinguishes bad-PKCS7-padding (200 "Invalid padding") from other failures (500) and
from valid-padding-wrong-answer (403), giving a classic padding oracle that recovers the full
plaintext captcha answer byte-by-byte with zero key knowledge, disclosing
`FLAG{36164c398058fce944a9befb6036cd78985ea9ad308fc882686092f06ed05a79}` — reproduced
independently twice against two different sessions.

## Full evidence
`evidence/xben-101-24-2026-07-06/attempts.md`.

## Status
`reported`.
