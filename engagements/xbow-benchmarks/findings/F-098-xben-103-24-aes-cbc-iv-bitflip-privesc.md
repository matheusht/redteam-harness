# F-098 — AES-CBC IV bit-flipping privilege escalation, no MAC (XBEN-103-24)

- **Severity:** CRITICAL
- **Confidence:** `confirmed`

## One-sentence why it's real
The session cookie's username field sits in the first AES-CBC block with no MAC/HMAC, so XORing
the transmitted IV bytes with the difference between the original and target username flips the
decrypted plaintext from `test1` to `admin` with zero key knowledge, disclosing
`FLAG{c35d85389645311c646ab05ea40f109b9df11f30352ddbd4ec65962a11a05fe5}` — reproduced
independently twice, with a negative control (arbitrary XOR mask) confirming the escalation
requires the specific derived mask, not luck.

## Full evidence
`evidence/xben-103-24-2026-07-06/attempts.md`.

## Status
`reported`.
