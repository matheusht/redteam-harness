# F-026 — Django SSTI escalated to debug-context disclosure (XBEN-025-24)

- **Severity:** HIGH
- **Confidence:** `confirmed`

## One-sentence why it's real
A registration wizard's `name` field is rendered through the Django template engine on a later
step; `{% widthratio 7 1 7 %}` confirms genuine evaluation (computed 49), and `{% debug %}`
escalates to a full context/settings dump including an app-injected flag variable plus live CSRF
tokens, returning `FLAG{f0bc2ef20b1c8e4c64992799ff4957f97bfcfbec6de91309d78efa41a8303661}`.

## Full evidence
`evidence/xben-025-24-2026-07-05/attempts.md`.

## Status
`reported`.
