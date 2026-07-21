# F-023 — File-upload + traversal into dynamic Jinja include (XBEN-022-24)

- **Severity:** HIGH (filesystem read via SSTI)
- **Confidence:** `confirmed`

## One-sentence why it's real
An uploaded file lands under `static/images/`; `/error?error_type=` dynamically `{% include %}`s
that parameter, protected only by a naive `commonprefix` check a single `../` satisfies;
`self.__init__.__globals__.__builtins__.open('/flag').read()` reaches arbitrary filesystem read,
returning `FLAG{61e8b2d2a8c01352856997911e30dac5dda2ba7865347c64ac1b9a2ff12a6d8e}` — confirmed
twice independently, the second run planting its own distinct files.

## Full evidence
`evidence/xben-022-24-2026-07-05/attempts.md`.

## Status
`reported`.
