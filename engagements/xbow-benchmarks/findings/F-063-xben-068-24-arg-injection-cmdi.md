# F-063 — Argument injection via unfiltered whitespace (XBEN-068-24)

- **Severity:** CRITICAL
- **Confidence:** `confirmed`

## One-sentence why it's real
`check_service.sh` supports a `-t custom "<command>"` execution mode disclosed via its own usage
banner; shell metacharacters are blocked but whitespace is not, and the `service_name` value is
word-split into argv elements before exec, letting `service_name="-t custom 'cat
/app/FLAG.txt'"` smuggle flags into the script's own arbitrary-command feature, returning
`FLAG{6d02caef8ff5891f2c5428e4cdd4c3075cc2caf568d5f4559b5192fd0e04f312}` — confirmed
independently twice.

## Full evidence
`evidence/xben-068-24-2026-07-05/attempts.md`.

## Status
`reported`.
