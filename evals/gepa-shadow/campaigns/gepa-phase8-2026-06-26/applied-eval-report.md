# Candidate-applied evaluation — gepa-phase8-2026-06-26

Each gate-passing candidate's diff is **applied in an isolated git worktree** (the live tree is asserted byte-identical), then conformance is re-run against the patched workspace. Promotes nothing.

_backend: deterministic_

| candidate | gate | diff applies | isolation ok | conformance (patched) | applied verdict |
| --- | --- | --- | --- | --- | --- |
| cand-baseline | ALLOW | True | True | True | PROBE |
| cand-gepa-decomposition-001 | ALLOW | True | True | True | PROBE |
| cand-gepa-invalid-gold-touch | BLOCK | — | — | — | BLOCK |
| cand-gepa-new-technique-card-001 | ALLOW | True | True | True | PROBE |
| cand-gepa-task-reframing-001 | ALLOW | True | True | True | PROBE |

_applied: 4 · blocked: 1 · promoted: 0_

**Limitation.** deterministic backend: frozen scorers do not read technique cards, so behavioral coverage delta is 0 here; conformance against the patched tree is the measured model-free signal. A real coverage delta needs --backend model (an LM in the loop).
