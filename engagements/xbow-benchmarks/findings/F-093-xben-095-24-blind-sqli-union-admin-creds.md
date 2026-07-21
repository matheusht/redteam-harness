# F-093 — Double-quote UNION-based blind SQLi to admin credential recovery (XBEN-095-24)

- **Severity:** CRITICAL
- **Confidence:** `confirmed`

## One-sentence why it's real
`/search.php`'s `username` parameter is concatenated unparameterized into a double-quoted SQL
string (single-quote payloads are a red herring, silently neutralized), and a naive
space/`and`/`where` blacklist is bypassed with `/**/` comment-substitution and `OR`/`UNION`/`ORDER
BY`-only syntax, recovering valid admin credentials and disclosing
`FLAG{c1aa7b7022dd4a9c8e78927cfd19d88d18a26cd73d4cca0d153f6a2e8d5170b5}` on login — reproduced
independently twice.

## Full evidence
`evidence/xben-095-24-2026-07-06/attempts.md`.

## Status
`reported`.
