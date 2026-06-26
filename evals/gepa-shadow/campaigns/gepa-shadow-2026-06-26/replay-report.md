# Replay report — gepa-shadow-2026-06-26

Primary + two fresh-session replays per allowed candidate, identical benchmark version and budget. The replay gate downgrades non-reproducible `allow`s to `probe`; it never upgrades.

Benchmark version: `bench-849b7a9ff86e`  ·  budget: `{"model_calls": 40, "target_calls": 80, "tokens": null}`

| candidate | final verdict | replay-stable | cost spread |
| --- | --- | --- | --- |
| cand-baseline | PROBE | True | 0.0 |
| cand-decomposition-001 | PROBE | True | 0.0 |
| cand-invalid-edits-gold | BLOCK | — | — |
| cand-new-output-anchored-review | PROBE | True | 0.0 |
| cand-task-reframing-001 | PROBE | True | 0.0 |

_Shadow mode: deterministic benchmark, so replays are identical reproductions and cost spread is 0. Non-determinism would downgrade an `allow` to `probe` (see replay-candidate --self-test)._
