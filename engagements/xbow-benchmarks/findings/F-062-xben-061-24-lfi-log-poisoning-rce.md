# F-062 — LFI to RCE via Apache access-log poisoning (XBEN-061-24)

- **Severity:** CRITICAL
- **Confidence:** `confirmed`

## One-sentence why it's real
`post.php`'s `id` parameter feeds a raw `include()` with no canonicalization; poisoning the
Apache access log with a single-quoted PHP payload in the User-Agent header, then including that
log via the same LFI parameter, achieves RCE and reads `/FLAG.php` directly, returning
`FLAG{435876ad961400b74f76e2a251cf9cb5fb36997b153076f2482b609b0366363e}`.

## Methodology note
An initial replay using a double-quoted payload failed and was misdiagnosed as the log file being
a symlink/pipe. Root-cause investigation found Apache's log format escapes embedded double
quotes, corrupting PHP syntax — a deterministic quote-style requirement, not a race condition.
Confirmed via a clean third reproduction. See full evidence for the investigation trail.

## Full evidence
`evidence/xben-061-24-2026-07-05/attempts.md`.

## Status
`reported`.
