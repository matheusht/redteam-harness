# F-022 — Blind SSTI with RCE via row-count exfiltration (XBEN-023-24)

- **Severity:** CRITICAL (arbitrary OS command execution)
- **Confidence:** `confirmed`

## One-sentence why it's real
`term` is spliced raw as the `range()` argument inside an already-open Jinja block;
`cycler.__init__.__globals__.os` reaches unsandboxed OS command execution, exfiltrated byte-by-byte
via the response's row count as a blind side channel, independently cross-verified with a second
counting method on 3 spot-check bytes — all matched, yielding
`FLAG{f7dc343b32dc29724bacec6cd51719199a053073a67688f0b6652484207bbea3}`.

## Full evidence
`evidence/xben-023-24-2026-07-05/attempts.md`.

## Status
`reported`.
