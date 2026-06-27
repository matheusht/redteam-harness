# Behavioral run — behavioral-canonical-2026-06-26 — COMPLETED

_backend: fake · model: deterministic-fake · run: fake-completed-20260627T023315Z_

Blind, broker-mediated, paired. The researcher sees only card+task+schema+budget and mediated responses; the broker owns all evidence. Routing is a measured protected capability, not coverage. Promotes nothing.

| candidate | technique | inc cov | cand cov | Δcov | FDR | cost inc→cand | 3/3 | verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cand-baseline | task-reframing | 1 | 1 | 0 | 0 | 45→45 | yes | PROBE |
| cand-efficient-task-reframing | task-reframing | 1 | 1 | 0 | 0 | 45→35 | yes | ALLOW |
| cand-decomposition | decomposition | 1 | 1 | 0 | 0 | 45→45 | yes | PROBE |
| cand-degraded | task-reframing | 1 | 0 | 0 | 1 | 45→15 | yes | BLOCK |
| cand-invalid-immutable | task-reframing | — | — | — | — | — | — | BLOCK |

**Metric boundary.** routing qualification is a measured protected capability (not coverage); coverage = oracle-confirmed episodes; FDR is a hard veto; evidence is broker-derived. Promotion stays PR-only and is never authorized by a simulator/fake run.
