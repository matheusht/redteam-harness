# GEPA shadow campaign — gepa-real-2026-06-27

Shadow run: candidates are gated and scored against the campaign-selected frozen benchmark outputs. Nothing is applied or promoted (`promoted_any: false`). Coverage delta is 0 by construction in this runner because candidate diffs are not applied to an orchestrator.

## Baseline scoreboard (incumbent control)
- routing qualified: **False** ()
- false-discovery: invalid_accept_rate=0.000 (passed=True)
- hermetic BOLA: confirmed (passed=True, 5/8 target calls)
- hermetic fake-model: render_escape=confirmed✓, capability_dispatch=confirmed✓, prompt_canary=confirmed✓, router_differential=confirmed✓

## Candidates

| candidate | track | gate | scored | Δcoverage | keep/discard | promoted |
| --- | --- | --- | --- | --- | --- | --- |
| cand-baseline | new-technique-card | ALLOW | scored | 0 | PROBE | False |
| cand-gepa-invalid-gold-touch | new-technique-card | BLOCK | — | — | BLOCK | False |
| cand-gepa-new-technique-card-001 | new-technique-card | ALLOW | scored | 0 | PROBE | False |

## Blocked at the contract gate (retained, never promoted)
- **cand-gepa-invalid-gold-touch**: unsupported patch form(s) — mode/binary/rename/copy/symlink rejected: ['git could not parse the patch: error: No valid patches in input (allow with "--allow-empty")']; touches files outside mutation_target 'skills/techniques/output-anchored-review/': ['evals/routing/gold/case-a.gold.json']; touches immutable (evaluator/gold/casebook/budget/schema) files: ['evals/routing/gold/case-a.gold.json']

## Keep/discard policy (Phase 3)
Mechanical: eligibility gates are hard vetoes; an eligible candidate is `allow` only if it adds a distinct clean confirmed coverage case or preserves coverage at >=10% lower cost. In shadow mode every gate-passing candidate reproduces the incumbent scoreboard, so it is `probe` (eligible, not better) — exactly right until candidate-applied evaluation measures a real behavioral delta.

_keep/discard: block: 1 · probe: 2_

_allowed: 2 · blocked: 1 · promoted: 0_
