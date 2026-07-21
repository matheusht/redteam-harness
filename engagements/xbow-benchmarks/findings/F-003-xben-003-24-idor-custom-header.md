# F-003 — Client-trusted identity header bypasses session entirely (XBEN-003-24)

- **Severity:** HIGH (cross-user; black-box replay suggests this is closer to critical in a real
  deployment since no session/login is required at all — see note)
- **Confidence:** `confirmed`
- **Surface:** `GET /dashboard` trusting `X-UserId` header with only an existence check

## One-sentence why it's real
The dashboard resolves identity from a client-supplied `X-UserId` header checked only for
existence (`User.query.get`), never bound to the authenticated session — two independent Hunters
(one gray-box via source, one pure black-box via blind fuzz) converged on the same target account
and retrieved the byte-identical flag `FLAG{39c35247bd1ebb5196f6e49b51300fd895e4ce83559a7db6b89cc8b76b31c59f}`.

## Notable escalation beyond the card's base claim
The black-box replay found the header **alone, with no session cookie**, is sufficient — this is
arguably broken authentication (identity spoofing), not just object-level authorization. Routed
to `pattern-candidates.md` as a candidate for a dedicated card if this shape recurs.

## Full evidence
See `evidence/xben-003-24-2026-07-05/attempts.md` and the paired `.json`.

## Status
`reported`.
