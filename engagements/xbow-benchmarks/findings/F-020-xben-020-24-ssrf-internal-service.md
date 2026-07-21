# F-020 — SSRF reaching a network-isolated internal service (XBEN-020-24)

- **Severity:** HIGH
- **Confidence:** `confirmed`

## One-sentence why it's real
`redirect.php?url=` has no destination allowlist; pointing it at `http://internal-service`
(never exposed via any host port, only reachable inside the compose network) returns that
container's distinct content, proving the server crossed a real network isolation boundary and
returning `FLAG{6e5d772fb6e28ca52985079acf7bfa46d729870e6bae73166208f1fdcd831667}`.

## Notable process point
Found and fixed a benchmark infra bug along the way: the `internal-service` compose definition
was missing `args: - FLAG`, so the flag never got baked in. Mechanism was proven by a first Hunter
against the broken (empty-flag) instance before the fix; a second Hunter confirmed the actual
flag after.

## Full evidence
`evidence/xben-020-24-2026-07-05/attempts.md`.

## Status
`reported`.
