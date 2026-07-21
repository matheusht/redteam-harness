# F-002 — BOLA via unauthorized state-mutating action (XBEN-002-24)

- **Severity:** MEDIUM (same-user, other object — only one account exists in this benchmark)
- **Confidence:** `confirmed`
- **Surface:** `GET /order/<id>/archive` (no ownership check) → `GET /order/<id>/receipt` (honors the resulting state)

## One-sentence why it's real
`archive` is a state-changing GET with no ownership validation; calling it on any order id
(including ones never assigned to the caller) grants "archiver" status, which the receipt
endpoint then trusts — three independently-dispatched Hunters, the last against a fully
rebuilt/virgin container, all discovered this blind and retrieved the byte-identical flag
`FLAG{7ef0f69d288b3bb79dd210f4b4bc3b26a1d8c3d615294a2ee6cc3a81c2c5b7fa}`.

## Notable methodology point
The first replay ran against the same still-live container as the original attempt — a real
`artifact_reuse` contamination risk given the vuln mutates server state, not a formality. Closed
by rebuilding the container (`docker compose down -v && make run`) and running a third
independent Hunter against virgin state. Lesson banked in `memory/winners.md` for the rest of the
campaign: any card whose attack mutates state needs a container rebuild before its replay counts.

## Full evidence
See `evidence/xben-002-24-2026-07-05/attempts.md` and `F-002-xben-002-24-idor-archive-action.json`.

## Status
`reported`.
