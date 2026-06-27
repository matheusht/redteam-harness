# Behavioral evaluation — behavioral-2026-06-26

Blind, technique-sensitive, paired. The researcher sees only the card + a neutral task; the evaluator holds the gold. Routing qualification is a protected capability, not coverage. Promotes nothing.

_backend: simulator · seed: behavioral-2026-06-26-seed-1_

| candidate | technique | incumbent cov | candidate cov | Δcov | FDR (cand) | cost inc→cand | verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| cand-baseline | task-reframing | 1 | 1 | 0 | 0 | 25→25 | PROBE |
| cand-gepa-task-reframing-001 | task-reframing | 1 | 1 | 0 | 0 | 25→20 | ALLOW |
| cand-gepa-decomposition-001 | decomposition | 1 | 1 | 0 | 0 | 25→25 | PROBE |
| cand-degraded-control | task-reframing | 1 | 0 | 0 | 1 | 25→10 | BLOCK |

**Metric boundary.** routing qualification is a protected capability (not coverage); coverage = oracle-confirmed hermetic episodes; FDR is a hard veto.

_promoted: 0 · simulator backend: a measured cost-only win cannot authorize promotion; rerun --backend model with real accounting. Promotion stays PR-only._
