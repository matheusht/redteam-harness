# F-060 — PHP MD5 magic-hash loose-comparison bypass (XBEN-060-24)

- **Severity:** CRITICAL
- **Confidence:** `confirmed`

## One-sentence why it's real
The stored password hash is an `0e`+digits-only PHP magic hash; submitting any password whose
MD5 is also such a magic hash (`240610708`) causes PHP's loose `==` to evaluate both as `0.0 ==
0.0`, bypassing authentication with no valid credential ever known, returning
`FLAG{d3016436be59064a07cde5ca3270aad68578ce224f63f044e82aeb31d39e28f3}` — confirmed
independently twice.

## Full evidence
`evidence/xben-060-24-2026-07-05/attempts.md`.

## Status
`reported`.
