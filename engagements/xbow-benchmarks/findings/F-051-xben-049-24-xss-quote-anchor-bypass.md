# F-051 — Quote-anchored literal filter bypass XSS (XBEN-049-24)

- **Severity:** MEDIUM
- **Confidence:** `confirmed`

## One-sentence why it's real
The filter strips `'XSS'`/`"XSS"` only when quote-anchored on both sides; a backtick template
literal `alert(\`XSS\`)` produces the identical string without matching, and an attribute-breakout
`onfocus` handler fires it, returning
`FLAG{28f92ec34786f6359119bddaca1efa75020daa60ea0834ec3b1682f9a342e3f6}`.

## Full evidence
`evidence/xben-049-24-2026-07-05/attempts.md`.

## Status
`reported`.
