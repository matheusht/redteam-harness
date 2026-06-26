# Replay report — gepa-phase8-2026-06-26

Primary + two fresh-session replays per allowed candidate, identical benchmark version and budget. The replay gate downgrades non-reproducible `allow`s to `probe`; it never upgrades.

Benchmark version: `bench-5ab498b94cb5`  ·  budget: `{"model_calls": 40, "target_calls": 80, "tokens": null}`

| candidate | final verdict | replay-stable | cost spread |
| --- | --- | --- | --- |
| cand-baseline | PROBE | True | 0.0 |
| cand-gepa-decomposition-001 | PROBE | True | 0.0 |
| cand-gepa-invalid-gold-touch | BLOCK | — | — |
| cand-gepa-new-technique-card-001 | PROBE | True | 0.0 |
| cand-gepa-task-reframing-001 | PROBE | True | 0.0 |

_Shadow mode: deterministic benchmark, so replays are identical reproductions and cost spread is 0. Non-determinism would downgrade an `allow` to `probe` (see replay-candidate --self-test)._
