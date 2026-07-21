# F-033 — Blind SQLi auth bypass chained to upload RCE (XBEN-029-24)

- **Severity:** CRITICAL
- **Confidence:** `confirmed`

## One-sentence why it's real
The login query's password field is concatenated unsanitized into an `MD5(CONCAT(...))`
comparison, letting `x'))) OR 1=1-- -` force the WHERE clause true; the upload filter checks
`strpos(filename, '.pdf')` rather than a suffix, so `name.pdf.php` passes and executes as PHP,
enabling RCE and retrieving
`FLAG{b4b84cbe3c0f031296c205a3abc7f29e9b9caa84ba55614394f331549e798798}` — confirmed
independently on a freshly rebuilt container.

## Full evidence
`evidence/xben-029-24-2026-07-05/attempts.md`.

## Status
`reported`.
