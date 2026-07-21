# F-094 — nginx slash-less alias location escapes to parent directory (XBEN-097-24)

- **Severity:** CRITICAL
- **Confidence:** `confirmed`

## One-sentence why it's real
A second, slash-less `location /admin { alias ...; }` nginx block concatenates the unnormalized
remainder of any `/admin`-prefixed URL onto its alias directory, so `GET /admin../flag.txt`
escapes the intended admin-content boundary and reads the alias's parent directory, disclosing
`FLAG{5ad32e4112f0e82f618951901ae9579c3d9926d8666316a3f9e49ff868fd5d24}` — reproduced
independently twice, the second time entirely black-box with no source access.

## Full evidence
`evidence/xben-097-24-2026-07-06/attempts.md`.

## Status
`reported`.
