# GEPA / Autoresearch Implementation Plan

**Status:** implemented through Phase 10 (blind technique-sensitive behavioral evaluation, simulator backend); the model backend for a real-LM researcher is the next step  
**Date:** 2026-06-26  
**Related:** `docs/decisions/0002-gepa-autoresearch-scope.md`, `docs/architecture-brainstorm-gepa-dspy.html`, `docs/autoresearch-evaluation-rfc.html`, `docs/ROADMAP.md`

## Summary

The harness should take a bigger GEPA slice than a toy prompt demo, but keep every candidate
verifiable. The first campaign may explore multiple tracks, while each candidate mutates exactly one
declared component. GEPA proposes; frozen evaluators gate; humans promote through PR review.

The near-term goal was a **Phase 3A shadow autoresearch loop**:

```text
campaign manifest
  → candidate generation
  → frozen scorers / hermetic evals
  → replay
  → evidence bundle
  → allow / block / probe
  → PR-only human promotion
```

That loop now exists through Phase 8: contracts, scorer, replay, promotion bundle, benchmark
expansion, DSPy spike (shelved), and a standalone GEPA adapter surface. DSPy remains parked, not a
prerequisite. The current limitation is explicit: candidate diffs are generated and gated, but not
yet applied to a temporary orchestrator/session for behavioral measurement.

## Phase 0 — Documentation and roadmap alignment

Purpose: make the accepted architecture explicit before code lands.

Implementation surface:

- `docs/ROADMAP.md`
- `docs/architecture-brainstorm-gepa-dspy.html`
- `docs/decisions/0002-gepa-autoresearch-scope.md`

Work:

- Add a Phase 3A GEPA shadow-autoresearch track.
- Record the rule: multi-track campaigns are allowed, but every candidate mutates one declared
  component.
- Mark DSPy as a later bounded spike.
- Track future-review capabilities:
  - live GEPA;
  - evaluator/oracle co-evolution;
  - autonomous PoC ladder;
  - SSRF pattern card and broader coverage-gap handling.

Acceptance:

- Docs say GEPA first, standalone adapter first.
- DSPy is not a prerequisite.
- Autoresearch still cannot promote automatically.
- Promotion is PR-only.

## Phase 1 — Campaign and candidate contracts

Purpose: make GEPA runs auditable before the optimizer runs.

Implementation surface:

- `schemas/campaign-manifest.schema.json`
- `schemas/candidate-manifest.schema.json`
- `schemas/promotion-bundle.schema.json`
- `tools/check-campaign.py` or a conformance extension

Core artifacts:

```text
campaign-manifest.json   # benchmark set, immutable hashes, budgets, mutable allowlist
candidate-manifest.json  # candidate id, lineage, mutation target, touched files, candidate hash
scores.json              # scorer outputs, cost, replay, protected-case results
evidence-bundle.md       # human/model review surface
candidate.diff           # proposed patch
```

Acceptance:

- Candidate touching undeclared files blocks.
- Budget, scorer, routing gold, casebook, or evaluator hash mismatch blocks.
- Missing evidence bundle blocks.
- Candidate cannot mutate evaluator, oracle, gold, budget, casebooks, or sealed data.

## Phase 2 — First GEPA shadow runner

Purpose: prove GEPA can propose and evaluate candidates without promotion.

Implementation surface:

- `evals/gepa-shadow/`
- `tools/run-gepa-shadow.py`
- `tools/hash-campaign-inputs.py`
- `evals/gepa-shadow/campaigns/<campaign-id>/`

First campaign tracks:

- `task-reframing`;
- `decomposition`;
- one new technique-card candidate.

Rule:

- One candidate equals one mutation target.
- One campaign may include several tracks.
- Candidates are evaluated independently and compared to the incumbent.

Initial benchmark set:

- qualification routing cases;
- false-discovery scorer;
- adversarial-candidate corpus;
- hermetic no-model BOLA target;
- `rotation-case-01-web-api`.

Acceptance:

- GEPA produces candidate artifacts in the required shape.
- Every candidate runs through existing scorers.
- No candidate is promoted.
- At least one intentionally invalid candidate blocks in test mode.
- A baseline/no-op candidate is retained as a control.

## Phase 3 — Scoring and keep/discard policy

Purpose: define “better” before the optimizer optimizes.

Implementation surface:

- `tools/score-candidate.py`
- `schemas/evaluation-result.schema.json`
- `evals/gepa-shadow/README.md`

Eligibility gates:

- conformance passes;
- false-discovery invalid accepts remain zero;
- protected incumbent cases do not regress;
- evidence contract is complete;
- budget is unchanged;
- candidate mutates only the declared component.

Utility rule:

- better if it adds at least one distinct clean confirmed coverage case; or
- better if it preserves coverage and reduces cost by at least 10%; otherwise
- discard or return `probe`.

Verdicts:

```text
allow
block
probe
```

Acceptance:

- False-discovery regression is always `block`.
- Duplicate coverage does not count.
- Equal coverage with less than 10% cost reduction is not accepted.
- Mechanical failures cannot be overridden by an LLM judge.

## Phase 4 — Replay and variance gate

Purpose: prevent one lucky candidate from becoming a promoted technique.

Implementation surface:

- `tools/replay-candidate.py`
- `evals/gepa-shadow/campaigns/<campaign-id>/<candidate-id>/replays/`

Replay policy:

- primary run plus two fresh-session replays;
- identical benchmark versions;
- identical budgets;
- recorded seeds/session identifiers where applicable;
- cost variance recorded.

Acceptance:

- Candidate preserves protected cases across all replays.
- Claimed new coverage reproduces.
- Non-deterministic success becomes `probe`, not `allow`.
- Replay artifacts are included in the evidence bundle.

## Phase 5 — Promotion bundle and PR workflow

Purpose: let a successful candidate promote without losing provenance.

Implementation surface:

- `tools/render-promotion-bundle.py`
- PR template section or checklist

Promotion bundle:

- candidate diff;
- campaign manifest;
- candidate manifest;
- scorer results;
- replay results;
- false-discovery result;
- cost comparison;
- redaction report;
- human review checklist.

Promotion path:

```text
GEPA candidate
  → isolated branch
  → scorers + replay
  → promotion bundle
  → human review
  → PR
  → merge
```

Acceptance:

- No manual copy into `skills/techniques/`.
- No direct-to-main promotion.
- PR identifies the single mutated component.
- Failed and probed candidates remain archived but not promoted.

## Phase 6 — Benchmark expansion before real ratchet

Purpose: make the evaluator broad enough that GEPA cannot simply learn one surface.

Implementation surface:

- `casebooks/rotation-case-02-*`
- `evals/hermetic/targets/*`
- `evals/routing/gold/*`

Build next:

1. SSRF pattern-card decision:
   - either add `pattern.ssrf`; or
   - keep SSRF as a tracked coverage gap until a second case confirms it.
2. Fake-model hermetic targets:
   - LLM05 render escape;
   - LLM06 capability dispatch;
   - LLM07 prompt canary;
   - model-router differential.
3. Second rotated case:
   - preferably AI-agentic or tool-use shaped;
   - not derived from the original live target;
   - no raw public CTF text, flags, or solutions.

Acceptance:

- At least two unrelated rotated casebooks exist.
- At least one no-model hermetic target exists.
- At least one fake-model hermetic target exists.
- Coverage gaps are scored honestly.

## Phase 7 — DSPy spike, only if useful

Purpose: test DSPy without turning it into the harness architecture.

Implementation surface:

- `experiments/dspy-routing-normalizer/` or `experiments/dspy-evaluator-normalizer/`

Best first DSPy target:

- routing-output normalization; or
- evaluator-output normalization.

Acceptance:

- DSPy module produces more reliable structured outputs than the current prompt-plus-JSON approach.
- It does not replace scorers.
- It does not become required for GEPA.
- If it does not clearly help, shelve it.

## Phase 8 — Standalone GEPA adapter + first adapter campaign

Purpose: replace hand-authored placeholder candidates with adapter-generated candidate artifacts
while preserving the same immutable evaluator and PR-only promotion path.

Implementation surface:

- `tools/run-gepa-real.py`
- `evals/gepa-shadow/campaigns/gepa-phase8-2026-06-26/`
- `.github/workflows/conformance.yml`
- `evals/gepa-shadow/README.md`

Adapter contract:

- Input: one declared campaign track, current component text read from `HEAD`, evaluator feedback,
  fixed campaign budgets, and frozen benchmark hashes.
- Output:
  - `candidate-manifest.json`;
  - `candidate.diff`;
  - `evidence-bundle.md`;
  - `gepa-trace.json`;
  - `scores.json` after the scoring chain runs.
- Backends:
  - `deterministic` — CI-safe control backend;
  - `gepa` — standalone GEPA `optimize_anything` backend when GEPA + LM config exist;
  - `auto` — GEPA if available, otherwise explicit deterministic fallback.

Acceptance:

- At least one real candidate diff is generated under a single declared mutation target.
- The no-op baseline is retained.
- A deliberately invalid candidate blocks mechanically.
- Scoring, replay, and promotion bundle artifacts render.
- No diff is applied to Plane 1.
- No candidate promotes automatically.

Current result:

- Local environment did not have GEPA installed/configured, so the committed run uses the
  deterministic backend. The GEPA backend path is wired but must be exercised in an environment with
  GEPA and an LM configured.
- All allowed candidates correctly remain `probe`: the frozen scorer gates artifacts but does not
  apply candidate diffs to a live orchestrator/session.

## Phase 9 — Candidate-applied evaluation (DONE)

Purpose: apply a candidate diff in isolation and re-measure model-free signals. Built as
`tools/apply-candidate-eval.py`: gate → `git worktree` apply at HEAD (live tree asserted byte-identical)
→ re-run `check-conformance.py` against the patched workspace → keep/discard. A card variant that breaks
the harness now blocks by MEASUREMENT. Note: the frozen scorers do not read technique cards, so this
phase still cannot produce a behavioral coverage delta — that is Phase 10's job.

Implementation surface:

- temporary workspace/session materializer;
- one-candidate-at-a-time diff application;
- runner that loads the mutated card for a frozen benchmark;
- rollback/cleanup guard;
- score/replay/promotion integration using the same Phase 3–5 machinery.

Acceptance:

- Applies exactly one candidate diff in an isolated temporary workspace.
- Re-runs the frozen benchmark with the mutated component loaded.
- Blocks if the diff touches undeclared or immutable files.
- Produces a candidate-specific scoreboard instead of reproducing the incumbent by construction.
- Still promotes nothing automatically.

## Phase 10 — Blind technique-sensitive behavioral evaluation (DONE)

Purpose: create actual learning pressure by evaluating technique BEHAVIOR, not a routing rerun. A
card-guided researcher chooses probes and adjudicates on hermetic episodes, so the technique wording can
change outcomes. Built as `tools/run-behavioral-eval.py` + `evals/behavioral/`.

- **10A — blind researcher adapter.** A structured input/output contract and a minimal researcher view
  (patched card + neutral task + allowed cards + schema + budget); `assert_blind()` rejects any view
  carrying gold/oracle/class. A deterministic `simulator` backend is the CI control; `--backend model`
  is gated and records a `skipped` NON-SUCCESS result (never a silent pass).
- **10B — technique-sensitive episodes.** `evals/behavioral/episodes/{task-reframing,decomposition}.json`
  with positive / held / refuted / contamination / control cases. A deterministic target answers probes;
  the card's discipline (run controls) and efficiency (probe count) drive behavior.
- **10C — paired evaluation.** Incumbent and candidate cards run through the SAME episodes, budget, and
  seed. Routing qualification is a PROTECTED capability, not coverage.
- **10D — mechanical scoring + replay.** Coverage = oracle-confirmed positives; FDR (any non-positive
  confirmed) is a hard veto; protected-case regression blocks; primary + two fresh-session replays gate
  stability; real accounting (model/target calls, model id, seed, elapsed).
- **10E — first behavioral campaign.** `evals/behavioral/campaigns/behavioral-canonical-2026-06-26/` over the
  existing hand-authored Phase-8 candidates + a degraded control. Result: baseline probe, an efficiency
  candidate allow (cost, marked non-promotable for the simulator), decomposition probe, degraded control
  block. A simulator cost-only win cannot authorize promotion; promotion stays PR-only.

Acceptance met: a candidate affects behavior without seeing gold; a deliberately degraded card blocks;
baseline is stable; held/refuted/contamination never become confirmed; an `allow` needs new
oracle-confirmed coverage or ≥10% measured cost reduction; nothing auto-promotes.

The remaining model-dependent step is wiring a real LM into `--backend model` so an `allow` comes from a
real researcher's measured behavior and accounting, not the deterministic simulator.

### Phase 10F–10G — provenance/integrity hardening + real-model adapter (DONE; real run BLOCKED)

Per `docs/phase-10f-10g-behavioral-qualification-plan.md`: replaced researcher self-reporting with an
evaluator-side **broker** (authoritative for probes/controls/replay/responses/evidence/cost); made the
behavioral evaluator consume canonical campaign/candidate manifests with **measured** gating + isolated
apply + patched-workspace conformance (no hardcoded eligibility); paired incumbent/candidate across a
primary + two fresh sessions with recorded anonymized A/B and strict 3/3; wrote **immutable**
`runs/<run-id>/` artifacts (no overwrite, hash-pinned); enforced capability blindness for the `model`
adapter (jailed subprocess). Added a provider-neutral researcher adapter (`tools/researcher_adapter.py`)
with strict action/final schemas, bounded malformed-output retries, usage accounting, and an honest
`skipped`/non-success on model unavailability, plus a deterministic fake CLI for CI. The real-model
qualification run is BLOCKED (no isolated LM backend); the adapter + all model-free integrity tests are
complete. Autonomy direction recorded in Decision 0003.

## Phase 11 — Future review tracks (post-behavioral qualification)

These are approved directions, not current implementation permissions.

### Live GEPA

Stages:

1. Advisory mode:
   - reads scrubbed live traces;
   - suggests next probe;
   - human approves.
2. Bounded mode:
   - one scoped objective;
   - fixed budget;
   - no Zone-2 artifacts;
   - no automatic memory promotion.
3. Autonomous mode:
   - requires kill switch, rate limits, run registry, and scope enforcement.

### Evaluator co-evolution

GEPA may eventually propose evaluator/oracle changes only with:

- sealed meta-evaluator;
- protected historical cases;
- zero invalid accepts;
- explicit evaluator-change PR;
- human review.

### Autonomous PoC / exploit-chain ladder

Capability levels:

```text
0. evidence explanation only
1. benign canary proof
2. local hermetic PoC
3. scoped live PoC with human confirmation
4. autonomous exploit chaining — separate review
```

Levels 0-2 fit the current safety model. Level 3 requires explicit scope and human confirmation.
Level 4 requires a separate design review.

## Recommended immediate build order

1. Build candidate-applied evaluation in an isolated temporary workspace.
2. Run the Phase 8 campaign through candidate-applied evaluation with deterministic backend first.
3. Install/configure GEPA and run `tools/run-gepa-real.py --backend gepa` on the same frozen campaign.
4. Compare deterministic control vs GEPA-generated candidates.
5. Promote only if a candidate becomes replay-stable `allow` and passes the existing PR-only bundle.
