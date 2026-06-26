# Evidence bundle — cand-gepa-new-technique-card-001

- campaign: `gepa-phase8-2026-06-26`
- track: `new-technique-card`
- mutation target: `skills/techniques/output-anchored-review/`
- backend: `deterministic`
- candidate score signal: `0.61` (adapter-local heuristic, not a promotion metric)

## Evaluator feedback supplied to optimizer
Evaluator feedback: keep the candidate scoped to one declared technique component; preserve safe-signal discipline; require controls, replay, contamination rule-out, budget awareness, and a one-sentence claim test. Do not mutate scorers, oracles, gold, budgets, casebooks, or vulnerability cards. No live target behavior is available in this shadow campaign. New technique should be conservative, evidence-anchored, and useful across vuln cards without becoming a payload library.

## Proposed change summary
Created a conservative review technique that turns ambiguous suspected wins into oracle-anchored checks.

## Reflection
Deterministic control backend: generated a bounded, single-component text variant from evaluator feedback.

## Scope statement
This candidate mutates exactly one declared Plane-1 technique component as a shadow proposal. It does not edit the evaluator, oracles, gold labels, casebooks, budgets, or sealed data. The diff is not applied by this tool and cannot promote without the existing PR-only promotion path.
