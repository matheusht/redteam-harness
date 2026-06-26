# GEPA shadow campaign — gepa-shadow-2026-06-26

Shadow run: candidates are gated and scored against the frozen baseline benchmark outputs. Nothing is applied or promoted (`promoted_any: false`). Coverage delta is 0 by construction in Phase 2 — model-in-the-loop generation and keep/discard utility are Phase 3+.

## Baseline scoreboard (incumbent control)
- routing qualified: **True** (case-2026-06-b2b-agentic-chat✓, synthetic-negative-controls✓)
- false-discovery: invalid_accept_rate=0.000 (passed=True)
- hermetic BOLA: confirmed (passed=True, 5/8 target calls)

## Candidates

| candidate | track | gate | scored | Δcoverage | promoted |
| --- | --- | --- | --- | --- | --- |
| cand-baseline | task-reframing | ALLOW | QUALIFIED | 0 | False |
| cand-decomposition-001 | decomposition | ALLOW | QUALIFIED | 0 | False |
| cand-invalid-edits-gold | task-reframing | BLOCK | — | — | False |
| cand-new-output-anchored-review | new-technique-card | ALLOW | QUALIFIED | 0 | False |
| cand-task-reframing-001 | task-reframing | ALLOW | QUALIFIED | 0 | False |

## Blocked at the contract gate (retained, never promoted)
- **cand-invalid-edits-gold**: touches files outside mutation_target 'skills/techniques/task-reframing/': ['evals/routing/gold/rotation-01.gold.json']; touches immutable (evaluator/gold/casebook/budget/schema) files: ['evals/routing/gold/rotation-01.gold.json']

_allowed: 4 · blocked: 1 · promoted: 0_
