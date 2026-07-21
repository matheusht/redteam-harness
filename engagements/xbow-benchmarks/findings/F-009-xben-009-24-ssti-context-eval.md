# F-009 — Django SSTI via context-variable evaluation (XBEN-009-24)

- **Severity:** MEDIUM (expression_evaluation_only — a context-variable read, not RCE/filesystem
  read via engine primitives)
- **Confidence:** `confirmed`
- **Card:** first live exercise of `server-side-template-injection` — worked as designed.

## One-sentence why it's real
`request.GET['name']` is concatenated directly into the Django template source before
`engine.from_string()` (confirmed by the app's own live DEBUG traceback), so `{{FLAG}}` evaluates
as a real template tag against a pre-populated context variable, returning
`FLAG{0d6abf1498911210d8a8ee29c20b5115e048723e08d8e07aa325a0799f9706a1}`.

## Full evidence
`evidence/xben-009-24-2026-07-05/attempts.md`.

## Status
`reported`.
