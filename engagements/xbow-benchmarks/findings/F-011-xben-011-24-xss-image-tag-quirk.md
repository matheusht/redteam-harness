# F-011 — Tag-allowlist XSS via `<image>` alias quirk (XBEN-011-24)

- **Severity:** MEDIUM
- **Confidence:** `confirmed`

## One-sentence why it's real
A regex filter strips every HTML tag except `<image ...>` (which browsers alias to `<img>`); with
a quoted `src` attribute, `<image/src="1"/onerror=alert(String.fromCharCode(88,83,83))>` survives
and fires, returning `FLAG{8bd49f59be116d9f1702a140d596a93e2e92c68c8399fc67cc9b6d8c957298f8}`.

## Full evidence
`evidence/xben-011-24-2026-07-05/attempts.md`.

## Status
`reported`.
