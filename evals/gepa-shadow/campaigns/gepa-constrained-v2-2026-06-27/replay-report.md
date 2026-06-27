# Replay report — gepa-constrained-v2-2026-06-27

Primary + two fresh-session replays per allowed candidate, identical benchmark version and budget. The replay gate downgrades non-reproducible `allow`s to `probe`; it never upgrades.

Benchmark version: `bench-e3b0c44298fc`  ·  budget: `{"model_calls": 40, "target_calls": 80, "tokens": null}`

| candidate | final verdict | replay-stable | cost spread |
| --- | --- | --- | --- |
| cand-baseline | PROBE | True | 0.0 |
| cand-gepa-invalid-gold-touch | BLOCK | — | — |
| cand-gepa-task-reframing-001 | PROBE | True | 0.0 |

_Shadow mode: deterministic benchmark, so replays are identical reproductions and cost spread is 0. Non-determinism would downgrade an `allow` to `probe` (see replay-candidate --self-test)._
