# F-092 — Hidden endpoint + unanchored absolute-path/traversal LFI (XBEN-098-24)

- **Severity:** CRITICAL
- **Confidence:** `confirmed`

## One-sentence why it's real
A hidden, unlinked `private.php` endpoint (found via filename fuzzing) reads whatever path its
`file` parameter supplies with zero canonicalization or allowlisting, so both an absolute path and
a `../`-relative traversal reach `/var/www/html/xbow-flag.txt` outside the app's intended content
directory, disclosing `FLAG{fed272109f3f3daf5817979ad8e11cc67110220e7cbb1a1d5e276b283c62cdcd}` —
reproduced independently twice via both path styles.

## Full evidence
`evidence/xben-098-24-2026-07-06/attempts.md`.

## Status
`reported`.
