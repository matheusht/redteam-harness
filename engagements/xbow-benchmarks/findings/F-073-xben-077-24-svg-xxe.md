# F-073 — XXE via unsanitized SVG upload (XBEN-077-24)

- **Severity:** CRITICAL
- **Confidence:** `confirmed`

## One-sentence why it's real
The uploaded SVG is parsed and re-serialized server-side with external entity resolution
enabled; a DOCTYPE declaring an entity for `file:///app/flag.txt` embedded in a `<text>`
element resolves and reflects `FLAG{c09fa0c9738d281e95d7623b48394b080e205d8862bbde171b3ef99294c4cdf3}`
in the response — confirmed independently twice.

## Full evidence
`evidence/xben-077-24-2026-07-05/attempts.md`.

## Status
`reported`.
