# cleanup.md — artifact ledger (chain-of-custody)

Every artifact the harness creates is recorded here with a revert action and status. Unresolved
cleanup **blocks pattern promotion**. Redact secrets always.

| Artifact | Type | Created (when) | Canary id | Revert action | Status |
| --- | --- | --- | --- | --- | --- |
| _example: test skill #x_ | skill | — | — | unshare + delete | pending |

## Canary disposal
Every canary issued gets an id and a disposal state (`live / revoked / expired`). Persistence,
memory-bleed, and residual poisoned content are themselves part of what we measure — track them.
