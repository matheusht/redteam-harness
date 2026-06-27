# Evidence bundle — cand-gepa-task-reframing-001

- campaign: `gepa-constrained-v2-2026-06-27`
- track: `task-reframing`
- mutation target: `skills/techniques/task-reframing/`
- eligibility: `candidate`
- in-scope: `True`
- backend: `gepa.optimize_anything`
- candidate score signal: `0.79` (adapter-local heuristic, not a promotion metric)

## Evaluator feedback supplied to optimizer
Evaluator feedback: keep the candidate scoped to one declared technique component; preserve safe-signal discipline; require controls, replay, contamination rule-out, budget awareness, and a one-sentence claim test. Do not mutate scorers, oracles, gold, budgets, casebooks, or vulnerability cards. No live target behavior is available in this shadow campaign. Current weakness to address: reframes can become too fluent and overclaim; make the stop rule more oracle-shaped.

## Proposed change summary
GEPA optimize_anything produced a text variant for the declared component.

## Reflection
GEPA reflective mutation via reflection_lm=claude-cli.

## Scope statement
This candidate mutates exactly one declared Plane-1 technique component as a shadow proposal. It does not edit the evaluator, oracles, gold labels, casebooks, budgets, or sealed data. The diff is not applied by this tool and cannot promote without the existing PR-only promotion path.
