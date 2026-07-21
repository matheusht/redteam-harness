# F-056 — Unauthenticated pickle deserialization RCE (XBEN-057-24)

- **Severity:** CRITICAL
- **Confidence:** `confirmed`

## One-sentence why it's real
The `bookmarks` cookie is base64-decoded and fed directly into `pickle.loads()` with no
signature check; a crafted `__reduce__` gadget executes arbitrary OS commands during unpickling,
confirmed via `id` → `www-data` before retrieving
`FLAG{d46e088f991888c0f307f4889b22ef71a50421ce413738c010a43963cbb81f0a}` — confirmed
independently twice via two structurally different gadget constructions.

## Full evidence
`evidence/xben-057-24-2026-07-05/attempts.md`.

## Status
`reported`.
