# SUPERSEDED / archived — gepa-phase8-2026-06-26

This is a **historical shadow campaign** (GEPA Phase 8, deterministic adapter). It is retained as
provenance and is **not** gated by CI. Do not run candidates against it and do not re-pin it.

## Why its integrity checks drift

Its `frozen_inputs` pin the **Phase-8-era** hashes of orchestrator tools (`check-campaign.py`,
`replay-candidate.py`, `render-promotion-bundle.py`). Later evaluator hardening legitimately changed
those tools — Phase 10F/10G (`69c30c4`, `89616a0`, `32bb93d`, `8d1a973`) and Phase 10H0
(`d49fc96`, the authoritative measured candidate boundary). So `hash-campaign-inputs.py --check` and
`render-promotion-bundle.py --verify` against this campaign report drift. **That is the drift detector
working as designed** (a candidate valid against an old evaluator must not silently re-validate against a
newer one), not a regression.

## What NOT to do

Do **not** re-pin this campaign's `frozen_inputs` to current tool hashes to make CI green. That would
rewrite superseded history and erase the lineage signal. Per Decision 0003/0004, an evaluator change
produces a **new** campaign revision; prior revisions are append-only.

## Where integrity is gated now

- Frozen-input integrity is gated in CI against the current canonical campaign
  (`evals/behavioral/campaigns/behavioral-canonical-v2-2026-06-27/`).
- The promotion-bundle hash-pin / `verify_drift` machinery is exercised by
  `tools/render-promotion-bundle.py --self-test`.
- Candidate authorization is the Phase 10H0 measured boundary
  (`apply-candidate-eval.materialize_candidate`): applied repository state, not patch syntax.
