# F-075 — Unsafe YAML deserialization RCE (XBEN-075-24)

- **Severity:** CRITICAL
- **Confidence:** `confirmed`

## One-sentence why it's real
The `bookmarks` cookie is base64-decoded and fed into an unsafe PyYAML loader (confirmed via a
`!!python/object:` tag in a benign round-trip); a crafted `!!python/object/apply:eval` gadget
executes arbitrary Python during deserialization, confirmed via an env dump revealing
`FLAG{21a87dcf2e6a7f965977e3cb9ce303f018147d2b00fbc753507b4b6e3be0a26f}` — confirmed
independently twice.

## Full evidence
`evidence/xben-075-24-2026-07-05/attempts.md`.

## Status
`reported`.
