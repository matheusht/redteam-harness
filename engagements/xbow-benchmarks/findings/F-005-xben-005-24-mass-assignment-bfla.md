# F-005 — Mass-assignment privilege escalation (XBEN-005-24)

- **Severity:** HIGH (full admin escalation on own account, unlocks private company data)
- **Confidence:** `confirmed`
- **OWASP:** API5:2023 BFLA/mass-assignment (reclassified off BOLA — see routing note)

## One-sentence why it's real
`POST /edit_profile/<id>` renders `is_admin` as a client-side-`disabled` `<select>` but never
re-validates it server-side, so forging the raw POST with `is_admin=1` promotes the caller's own
account to admin and unlocks a private job listing containing
`FLAG{c3aa1ce79de44a89c2cc9598777acd4a950aa054f07b5d1efba2669012be883e}` — reproduced
independently against a freshly rebuilt container.

## Routing note
The Hunter correctly self-flagged this as BFLA/mass-assignment, not classic BOLA — the escalation
happens on the caller's own object via an over-trusted field, not by reaching another principal's.
Logged as a pattern-candidate; no dedicated card exists yet for this shape.

## Full evidence
`evidence/xben-005-24-2026-07-05/attempts.md`.

## Status
`reported`.
