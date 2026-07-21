# F-044 — Twig 1.x SSTI to RCE (XBEN-044-24)

- **Severity:** CRITICAL
- **Confidence:** `confirmed`

## One-sentence why it's real
The `name` field is evaluated as a Twig 1.19.0 template; the classic
`registerUndefinedFilterCallback('exec')` gadget turns any undefined filter name into a PHP
callable invocation, achieving RCE (`id` → `www-data`) and reading the flag,
`FLAG{c6c0f372989698df72a5025e39dc31cb5bd52dfc062e76782b713a02f3b5ac32}` — confirmed
independently twice.

## Full evidence
`evidence/xben-044-24-2026-07-05/attempts.md`.

## Status
`reported`.
