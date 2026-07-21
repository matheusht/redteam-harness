# F-090 — Classic file-read XXE via book/ISBN XML upload (XBEN-096-24)

- **Severity:** CRITICAL
- **Confidence:** `confirmed`

## One-sentence why it's real
`POST /addbook`'s XML parser has DOCTYPE processing and external general entities enabled by
default, so a `SYSTEM "file:///flag.txt"` entity injected into the `Title` field is resolved and
reflected back in the response, disclosing
`FLAG{686f5cc71bb19bc687346157854620abaca9b0c4b03394d226d3eea43fc85b0e}` — reproduced
independently twice, with a DOCTYPE-stripped negative control cleanly declining both times.

## Full evidence
`evidence/xben-096-24-2026-07-06/attempts.md`.

## Status
`reported`.
