# Phase 10I-11 — Real-LM qualification and first closed-loop GEPA campaign

**Status:** proposed long-running implementation plan\
**Expected duration:** longer focused goal, roughly 3-6 hours if local model/backend setup is available; stop
honestly if the real-LM boundary is blocked.\
**Depends on:** Decisions 0002 and 0004, Phase 10F-10H0, current canonical behavioral campaign.\
**Does not authorize:** live engagements, Zone-2 PoCs, evaluator/gold/oracle/budget mutation, sealed-data
access, direct-to-main promotion, or automatic Plane-1 edits.

## Thesis

This can be a larger phase, but only if it is staged as an earned continuation:

```text
cleanup/current truth
  -> isolated real-LM researcher qualification
  -> real GEPA candidate generation
  -> candidate materialization
  -> broker-owned behavioral evaluation
  -> replay/promotion bundle
  -> archive or PR-only evidence
```

The harness may start testing GEPA on itself only in the narrow Decision-0004 sense: GEPA can propose
technique-card variants and evidence bundles, and the harness can evaluate those variants with a blind
researcher/evaluator loop. GEPA must not optimize the evaluator, oracle, scorer, gold labels, budgets,
campaign truth, or sealed data in this phase. A candidate can learn strategy; it cannot redefine truth.

## Phase 0 — Reconcile current truth before adding capability

1. Inspect `git status --short`.
2. Preserve unrelated dirty files and staged user work.
3. Verify whether Phase 10H0 cleanup is already staged:
   - superseded Phase-8 campaign checks no longer make CI red;
   - stale `apply-candidate-eval.py --backend model` semantics return honest non-success or are clearly
     removed from the model path;
   - docs distinguish clean committed-HEAD conformance from dirty-workspace conformance.
4. Run the existing local validation suite.
5. Commit only the cleanup if it is green and scoped.

Acceptance:

- Required CI self-tests do not intentionally point at superseded drifting artifacts.
- No known-red check is normalized as acceptable background noise.
- ROADMAP and implementation notes agree with Decision 0004 and Phase 10H0 status.

## Phase 1 — Real-LM backend qualification, no GEPA yet

Purpose: prove a real model can act as researcher while the broker/evaluator still owns truth.

Implementation surface:

- `tools/researcher_adapter.py`
- `tools/run-behavioral-eval.py`
- campaign docs under `evals/behavioral/`
- optional local wrapper script outside committed secrets

Requirements:

1. Use the existing provider-neutral subprocess adapter. Do not hardcode a provider-specific SDK unless
   there is already a narrow wrapper boundary.
2. Pass only the blind mediated view: `{card, neutral task, schema, budget}`.
3. Empty or scrub the subprocess cwd/env; record that this is still a transport boundary, not a kernel
   sandbox.
4. Return non-success for missing backend, malformed output exhaustion, timeout, or runtime failure.
5. Run the canonical order:
   - incumbent
   - no-op
   - degraded control
   - task-reframing
   - decomposition
6. Require primary + two fresh-session paired replays, same seed/budget/version, broker-owned events.

Acceptance:

- Missing/unavailable model records `skipped` and exits non-success.
- Runtime failure records `failed` and exits non-success.
- Degraded/control candidate blocks by FDR.
- No-op/probe candidates do not become fake wins.
- Any `allow` is broker-derived, 3/3 replay-stable, and non-promotable until promotion bundle review.
- No model claim can create coverage without matching broker events.

If this phase blocks on lack of isolated backend, stop here after committing any useful adapter hardening.
Do not substitute fake/simulator success.

## Phase 2 — First real GEPA shadow campaign

Purpose: let GEPA propose technique variants, then measure them through the same materialized boundary and
real-LM behavioral evaluator.

Implementation surface:

- `tools/run-gepa-real.py`
- campaign manifests under `evals/gepa-shadow/`
- candidate artifacts under `candidates/<id>/`
- existing materialization/replay/promotion tools

Rules:

1. GEPA may mutate only one declared technique card per candidate.
2. Candidate manifests and diffs must be explicit artifacts.
3. Evaluator, scorer, gold, oracle, casebooks, budgets, route qualification data, and sealed data are
   immutable.
4. GEPA output is never applied to Plane 1. It enters isolated worktree materialization first.
5. Run an incumbent and deterministic/no-op control alongside GEPA candidates.
6. Prefer a small candidate count over a wide search. The first real campaign is a systems test, not a
   leaderboard chase.

Acceptance:

- GEPA-generated candidate artifacts pass the same preflight/materialization policy as hand-authored
  candidates.
- Bad or malformed candidates block with measured reasons.
- Clean but behaviorally neutral candidates remain `probe`.
- Any real `allow` must preserve protected cases, keep FDR at zero, and pass 3/3 replay.
- Simulator-only cost wins are not promotable.
- `autonomous_gap_closure_count` remains `0` unless the run truly discovers and closes a previously
  uncovered behavior without human-authored case/candidate help.

## Phase 3 — Promotion bundle only, no automatic promotion

For every `allow` or interesting `probe`:

1. Render/update evidence bundle.
2. Include materialization tree ids, actual paths, broker events, replay report, redaction report, and
   candidate diff.
3. Mark `promotable=false` unless the run used a real qualified backend and all promotion gates pass.
4. Produce a PR-ready body only; do not edit `skills/techniques/` directly from the campaign.

Acceptance:

- Failed/probed candidates are archived, not silently discarded.
- Promotable candidates identify exactly one mutated component.
- Redaction failure blocks promotion even if behavior improved.

## Phase 4 — Consolidation notes, not a framework rewrite

At the end, write a short note on duplication discovered across:

```text
preflight -> apply -> measure -> score -> replay -> record
```

Only consolidate code if doing so removes a real duplicate authority path. Do not introduce
`Strategy`, `LearningPolicy`, or controller classes just because Decision 0004 names those roles.

Acceptance:

- The final report names complexity deleted, complexity deliberately retained, and the next smallest
  consolidation move.

## Feedback-loop discipline

For every invariant:

1. Reproduce the failure or missing proof.
2. Add/adjust a fixture or run artifact that would catch it.
3. Implement the smallest general fix.
4. Run targeted tests.
5. Run the full relevant suite.
6. Inspect generated reports for self-contradiction or fabricated claims.
7. Commit only green, scoped work.

Never weaken gold, evaluator truth, budgets, or protected cases to produce a pass. If the same external
blocker repeats three times, record it as blocked, commit useful independent hardening, and stop.

## Required validation before final commit

- `python3 tools/check-conformance.py`
- all touched tool `--self-test`s
- behavioral real-model run, or an immutable skipped/failed run proving honest non-success
- GEPA campaign run only if real-LM qualification passed
- promotion-bundle self-test if bundles were touched
- `git diff --check`
- no leaked worktrees, scratch dirs, secrets, or model commands

## Final report template

- Current branch/commits
- Whether Phase 0 cleanup was needed
- Real-LM qualification status: completed/skipped/failed
- GEPA campaign status: not-started/blocked/completed
- Candidate dispositions
- Evidence artifacts
- Tests run
- Complexity deleted vs retained
- `autonomous_gap_closure_count`
- Remaining blockers
- Recommended next phase
