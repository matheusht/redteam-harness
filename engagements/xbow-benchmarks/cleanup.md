# cleanup.md — artifact ledger (chain-of-custody)

Every artifact the harness creates is recorded here with a revert action and status. Unresolved
cleanup **blocks pattern promotion**. Redact secrets always.

| Artifact | Type | Created (when) | Canary id | Revert action | Status |
| --- | --- | --- | --- | --- | --- |
| _example: test skill #x_ | skill | — | — | unshare + delete | pending |
| 104 XBOW benchmark Docker stacks (containers/networks/volumes) | infra | 2026-07-05/06, entire campaign | n/a | `make stop` (compose down) per benchmark, run immediately after each Hunter/replay pair completed | **resolved** — verified via `docker ps -a` after the final benchmark (XBEN-104): zero running containers, all exited/removed |
| Canary accounts + planted marker strings (e.g. `canaryalice`/`canarybob`, unique UUID-style content markers) | account/data | throughout, per-benchmark, wherever the BOLA/IDOR card's methodology called for them | n/a (ephemeral, scoped to one benchmark's container lifetime) | none needed beyond container teardown — canary accounts lived only in each benchmark's own (now-destroyed) DB/session store, never persisted outside it | **resolved** — disposal is implicit in container teardown; no canary outlived its container |
| Local Dockerfile/compose patches in the gitignored `upstream/benchmarks/` clone (archive.debian.org apt fixes, Composer `--no-blocking`, Node 14→18 bump, XBEN-096 port remap) | infra fix | throughout campaign, reactively | n/a | none — these are build-environment fixes to a gitignored clone, never touch the harness repo or upstream XBOW source; left in place intentionally so the clone remains buildable for any future re-run | **resolved / intentionally retained**, documented in `progress.md` |
| Recovered real credentials (XBEN-095 admin password, XBEN-102 disclosed test password) | secret | 2026-07-06 | n/a | never written to any plane — omitted from evidence/finding files per CLAUDE.md redaction policy from the moment of discovery | **resolved** — verified via a post-campaign grep audit of `findings/` and `evidence/` (0 hits) |

## Canary disposal
Every canary issued gets an id and a disposal state (`live / revoked / expired`). Persistence,
memory-bleed, and residual poisoned content are themselves part of what we measure — track them.

**Campaign-wide disposal note (2026-07-06):** every canary account/marker created during the
104-benchmark XBOW campaign was scoped to a single benchmark's own Docker container stack, which
was torn down (`make stop`) immediately after that benchmark's Hunter and any replay completed —
before moving to the next benchmark. State: `expired` for all — no canary from this campaign
persists in any live system. No cross-benchmark persistence or memory-bleed was possible by
construction (fresh containers, fresh Hunters, no forking).
