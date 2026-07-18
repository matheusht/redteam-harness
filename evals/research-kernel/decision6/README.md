# Decision 0006 frozen operation replay

This directory contains inert, synthetic Slice-0 evidence. It freezes the accepted Decision-0005
implementation identity at `23fc4f6`, all 19 public commands, all 29 event types, a ten-operation
old-gate corpus, the stage/measurement contract, and the deterministic old-gate result.

The local `_AGENT_NOTEBOOK_OPS` / `HARNESS_AGENT_ATTESTED` experiment is deliberately excluded from
the accepted baseline. It was never authority and is removed by Decision 0006.

Run:

```sh
.venv/bin/python tools/decision6_replay.py --self-test
```

The replay is architecture evidence only. It contacts no target, creates no Zone-2 bytes, and makes
no vulnerability-discovery efficacy claim. `gates_held` is primary; required authority pauses are not
counted as stalls.
