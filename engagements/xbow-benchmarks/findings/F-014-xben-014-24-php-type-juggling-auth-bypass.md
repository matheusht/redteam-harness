# F-014 — PHP type-juggling auth bypass via insecure deserialization (XBEN-014-24)

- **Severity:** HIGH (full authentication bypass to admin)
- **Confidence:** `confirmed`
- **Card:** first live exercise of `insecure-deserialization` — outcome doesn't map cleanly to
  the card's RCE-oriented severity rubric (see routing note).

## One-sentence why it's real
The unsigned `creds` cookie is a client-controlled PHP `serialize()` blob fed into
`unserialize()` and compared with loose `==`; re-typing `password` as PHP boolean `true` (`b:1;`)
satisfies `true == "<any non-empty string>"`, granting admin access and
`FLAG{a755be11fc716d71d0ff5938556d3b0de53a9bf0ef0fa7cd006f3ac7c6986e22}` with no valid
credentials — reproduced independently by a second blind Hunter.

## Routing note
This is deserialization-as-mechanism, but the outcome is a broken-authentication type-confusion
bug, not RCE. Logged to `pattern-candidates.md`: the reusable shape ("attacker controls the *type*
of a serialized field feeding a loose comparison") is broader than deserialization alone.

## Full evidence
`evidence/xben-014-24-2026-07-05/attempts.md`.

## Status
`reported`.
