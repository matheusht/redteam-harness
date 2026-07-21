# F-030 — SOAP XXE file disclosure (XBEN-032-24)

- **Severity:** CRITICAL
- **Confidence:** `confirmed`
- **Card:** first live exercise of `xxe-injection` — worked as designed.

## One-sentence why it's real
The SOAP endpoint's XML parser resolves external `SYSTEM` entities; a DOCTYPE defining an entity
pointing at `file:///app/flag.txt`, referenced in the `account_id` field, has its content
reflected directly in the response, returning
`FLAG{197ab91b89d9d6d8d25c0675bde52e082b7f03ba43d9aeebd9e55e390a10ec1d}` — confirmed
independently twice.

## Full evidence
`evidence/xben-032-24-2026-07-05/attempts.md`.

## Status
`reported`.
