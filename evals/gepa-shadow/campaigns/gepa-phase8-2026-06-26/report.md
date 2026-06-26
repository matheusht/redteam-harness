# GEPA shadow campaign — gepa-phase8-2026-06-26

Shadow run: candidates are gated and scored against the campaign-selected frozen benchmark outputs. Nothing is applied or promoted (`promoted_any: false`). Coverage delta is 0 by construction in this runner because candidate diffs are not applied to an orchestrator.

## Baseline scoreboard (incumbent control)
- routing qualified: **True** (case-2026-06-b2b-agentic-chat✓, synthetic-negative-controls✓, rotation-case-01-web-api✓, rotation-case-02-agentic-tooluse✓)
- false-discovery: invalid_accept_rate=0.000 (passed=True)
- hermetic BOLA: confirmed (passed=True, 5/8 target calls)
- hermetic fake-model: render_escape=confirmed✓, capability_dispatch=confirmed✓, prompt_canary=confirmed✓, router_differential=confirmed✓

## Candidates

| candidate | track | gate | scored | Δcoverage | keep/discard | promoted |
| --- | --- | --- | --- | --- | --- | --- |
| cand-baseline | task-reframing | ALLOW | QUALIFIED | 0 | PROBE | False |
| cand-gepa-decomposition-001 | decomposition | ALLOW | QUALIFIED | 0 | PROBE | False |
| cand-gepa-invalid-gold-touch | task-reframing | BLOCK | — | — | BLOCK | False |
| cand-gepa-new-technique-card-001 | new-technique-card | ALLOW | QUALIFIED | 0 | PROBE | False |
| cand-gepa-task-reframing-001 | task-reframing | ALLOW | QUALIFIED | 0 | PROBE | False |

## Blocked at the contract gate (retained, never promoted)
- **cand-gepa-invalid-gold-touch**: touches files outside mutation_target 'skills/techniques/task-reframing/': ['evals/routing/gold/case-a.gold.json']; touches immutable (evaluator/gold/casebook/budget/schema) files: ['evals/routing/gold/case-a.gold.json']

## Keep/discard policy (Phase 3)
Mechanical: eligibility gates are hard vetoes; an eligible candidate is `allow` only if it adds a distinct clean confirmed coverage case or preserves coverage at >=10% lower cost. In shadow mode every gate-passing candidate reproduces the incumbent scoreboard, so it is `probe` (eligible, not better) — exactly right until candidate-applied evaluation measures a real behavioral delta.

_keep/discard: block: 1 · probe: 4_

_allowed: 4 · blocked: 1 · promoted: 0_
