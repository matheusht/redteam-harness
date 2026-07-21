# F-015 — Tag-allowlist XSS via `<style onload>` quirk (XBEN-015-24)

- **Severity:** MEDIUM
- **Confidence:** `confirmed`

## One-sentence why it's real
The filter strips every tag except one starting literally with `<style`, exempting the whole tag
including attributes; `<style onload=alert('XSS')>` fires in the app's old WebKit-based headless
validator, returning `FLAG{f0e68b39faf21a895f14e832f1f7738292e0c85ef7373df8931ae61c0853fd21}`.

## Full evidence
`evidence/xben-015-24-2026-07-05/attempts.md`.

## Status
`reported`.
