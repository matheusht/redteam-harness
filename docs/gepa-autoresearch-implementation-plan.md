# GEPA / Autoresearch Implementation Plan

**Status:** implementation plan; not yet implemented  
**Date:** 2026-06-26  
**Related:** `docs/decisions/0002-gepa-autoresearch-scope.md`, `docs/architecture-brainstorm-gepa-dspy.html`, `docs/autoresearch-evaluation-rfc.html`, `docs/ROADMAP.md`

## Summary

The harness should take a bigger GEPA slice than a toy prompt demo, but keep every candidate
verifiable. The first campaign may explore multiple tracks, while each candidate mutates exactly one
declared component. GEPA proposes; frozen evaluators gate; humans promote through PR review.

The near-term goal is a **Phase 3A shadow autoresearch loop**:

```text
campaign manifest
  → candidate generation
  → frozen scorers / hermetic evals
  → replay
  → evidence bundle
  → allow / block / probe
  → PR-only human promotion
```

DSPy remains a future spike, not a prerequisite.

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

## Phase 8 — Future review tracks

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

1. Add campaign, candidate, and promotion schemas.
2. Add campaign hash/check tooling.
3. Add GEPA shadow runner with baseline/no-op candidate support.
4. Run first GEPA campaign over three independent tracks:
   - `task-reframing`;
   - `decomposition`;
   - one new technique candidate.
5. Add replay gate.
6. Add promotion bundle renderer.
7. Expand fake-model hermetic targets and/or make the SSRF card decision.
