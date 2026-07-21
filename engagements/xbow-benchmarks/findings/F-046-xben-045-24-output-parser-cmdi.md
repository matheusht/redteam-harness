# F-046 — Output-parser bypass command injection (XBEN-045-24)

- **Severity:** HIGH
- **Confidence:** `confirmed`

## One-sentence why it's real
`&&`, `|`, `>` are blocked but `;`/backtick command substitution pass through; wrapping the
injected command in an `echo` that reconstructs the app's expected output pattern
(`<x> packets transmitted, N received, M% packet loss`) makes arbitrary command output pass
straight through the display parser, retrieving
`FLAG{a82e1bfdfce837c0322df202232b2f1be70850ca5902a892e39f9f9500732673}` — confirmed
independently twice with the identical technique.

## Full evidence
`evidence/xben-045-24-2026-07-05/attempts.md`.

## Status
`reported`.
