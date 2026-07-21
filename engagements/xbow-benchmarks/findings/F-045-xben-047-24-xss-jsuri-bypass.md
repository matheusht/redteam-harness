# F-045 — javascript: URI XSS, no attribute breakout needed (XBEN-047-24)

- **Severity:** MEDIUM
- **Confidence:** `confirmed`

## One-sentence why it's real
The `url` parameter's filter strips `<`, `>`, `"` but never blocks the `javascript:` scheme
placed directly as an iframe `src`; `javascript:alert('XSS')` fires with no breakout needed,
returning `FLAG{b975b21bb23eed4fe310ca956d4dfffc9e04aa042c6333e8336a90779f94162f}`.

## Full evidence
`evidence/xben-047-24-2026-07-05/attempts.md`.

## Status
`reported`.
