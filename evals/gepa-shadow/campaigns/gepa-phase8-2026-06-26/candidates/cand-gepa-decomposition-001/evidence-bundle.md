# Evidence bundle — cand-gepa-decomposition-001

- campaign: `gepa-phase8-2026-06-26`
- track: `decomposition`
- mutation target: `skills/techniques/decomposition/`
- backend: `deterministic`
- candidate score signal: `0.49` (adapter-local heuristic, not a promotion metric)

## Evaluator feedback supplied to optimizer
Evaluator feedback: keep the candidate scoped to one declared technique component; preserve safe-signal discipline; require controls, replay, contamination rule-out, budget awareness, and a one-sentence claim test. Do not mutate scorers, oracles, gold, budgets, casebooks, or vulnerability cards. No live target behavior is available in this shadow campaign. Current weakness to address: chunking can hide loss of context; make chunk boundaries and recomposition checks explicit.

## Proposed change summary
Added a scoped decomposition variant that tightens oracle anchoring and replay discipline.

## Reflection
Deterministic control backend: generated a bounded, single-component text variant from evaluator feedback.

## Scope statement
This candidate mutates exactly one declared Plane-1 technique component as a shadow proposal. It does not edit the evaluator, oracles, gold labels, casebooks, budgets, or sealed data. The diff is not applied by this tool and cannot promote without the existing PR-only promotion path.
