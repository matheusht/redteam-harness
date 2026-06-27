# Phase 14 — Canonical lifecycle consolidation

**Status:** proposed implementation plan\
**Roadmap role:** last active implementation phase in the current roadmap\
**Expected duration:** medium/long focused goal, roughly 3-6 hours for the first consolidation slice\
**Depends on:** Decision 0004, Phase 10H0, Phase 10I, Phase 12-13, and the latest GEPA constrained
campaign evidence\
**Does not authorize:** sealed evaluator, autonomous controller, live GEPA, evaluator co-evolution,
workflow/index layer, Tollbooth, Carbonyl, Fortémi, automatic promotion, or Plane-1 edits.

## Goal

Establish one canonical public experiment lifecycle:

```text
preflight -> apply -> measure -> score -> replay -> record
```

The current system has the right pieces, but the public surface is spread across multiple scripts and
artifact layers:

- `tools/check-campaign.py`
- `tools/apply-candidate-eval.py`
- `tools/run-gepa-real.py`
- `tools/run-behavioral-eval.py`
- `tools/replay-candidate.py`
- `tools/render-promotion-bundle.py`

Phase 14 should reduce ambiguity without inventing a framework. The desired result is a small canonical
entrypoint and a shared lifecycle result contract that composes existing tested functions.

## Non-goal

Do not create a new agent hierarchy, strategy service, controller daemon, database, workflow runtime, or
generic experiment framework. Decision 0004 names roles for reasoning; it does not authorize role
classes.

## Product principle

The consolidation must delete or internalize complexity. If a new abstraction does not remove an old
authority path, make a report-only note instead of building it.

## Phase 14A — Lifecycle inventory and authority map

### Objective

Make the current lifecycle explicit before changing code.

### Work

Create a short inventory document, preferably:

```text
docs/lifecycle-consolidation-inventory.md
```

For each current entrypoint, record:

- public or internal/historical;
- lifecycle stages it performs;
- authoritative outputs;
- non-authoritative/advisory outputs;
- known overlapping responsibilities;
- current self-tests;
- retained reason or retirement plan.

### Acceptance

- The inventory identifies exactly one intended public flow.
- Every old script is classified as public, internal, historical, or test-only.
- No code behavior changes in this subphase unless a doc/test exposes a clear bug.

## Phase 14B — Define one lifecycle result contract

### Objective

Create one machine-readable result shape that can be used by GEPA, behavioral eval, replay, and promotion
without each tool inventing its own truth fields.

### Suggested contract

```json
{
  "campaign_id": "...",
  "candidate_id": "...",
  "status": "completed|skipped|failed",
  "stages": {
    "preflight": {...},
    "materialization": {...},
    "behavioral": {...},
    "replay": {...},
    "promotion": {...}
  },
  "authoritative_stage": "materialization|scope|behavioral|shadow|unavailable",
  "authoritative_verdict": "allow|block|probe",
  "promotable": false,
  "artifacts": {
    "candidate_manifest": "...",
    "diff": "...",
    "materialization": "...",
    "broker_events": "...",
    "replay": "...",
    "promotion_bundle": "..."
  },
  "reasons": []
}
```

This can start as a schema/documented dataclass-style dict. Do not require a full schema migration for
historical artifacts in the first slice.

### Acceptance

- The contract clearly states which fields are authoritative.
- Existing `bridge-result.json` and promotion bundle concepts map into it.
- Historical bundles remain readable.
- Missing real-LM backend produces `status=skipped` or `failed`, never a fake `allow`.

## Phase 14C — Add one canonical public lifecycle entrypoint

### Objective

Expose a single public command that runs the intended flow for a campaign, while reusing existing tested
functions.

### Suggested file

```text
tools/run-experiment-lifecycle.py
```

### Intended modes

1. `--campaign <path>`
2. `--backend deterministic|gepa`
3. `--behavioral-backend none|fake|model`
4. `--behavioral-model-cmd <cmd>`
5. `--candidate <id>` optional
6. `--self-test`

### Internal composition

Prefer composition over copying:

```text
run-gepa-real.generate(...)
  -> materialization via apply-candidate-eval.materialize_candidate
  -> behavioral bridge via run-gepa-real.behavioral_bridge
  -> replay/render via existing tools
  -> lifecycle-result.json
```

If a helper is needed, extract the smallest pure helper from existing code. Do not reimplement the broker,
materialization, replay, or promotion logic.

### Acceptance

- The public command emits one `lifecycle-result.json` or `lifecycle-report.json`.
- It does not change candidate verdict semantics compared to the existing Phase 12-13 campaign.
- It writes artifacts under the campaign directory only.
- It never writes to `skills/` or Plane 1.
- It has a self-test that proves:
  - materialization block stays block;
  - behavioral probe stays probe;
  - missing model backend is non-success/skipped;
  - no-op baseline remains probe.

## Phase 14D — Mark older entrypoints internal or historical

### Objective

Reduce future-agent confusion by documenting which scripts are public surfaces and which are internal
building blocks.

### Work

Update docstrings/README sections for:

- `tools/run-gepa-real.py`
- `tools/apply-candidate-eval.py`
- `tools/run-behavioral-eval.py`
- `tools/replay-candidate.py`
- `tools/render-promotion-bundle.py`

Do not delete old tools in the first slice. Mark them:

- `public` if still supported directly;
- `internal building block`;
- `historical/debug`;
- `self-test only`.

### Acceptance

- A future agent can answer: “Which command should I run for a campaign?”
- Docs do not claim old shadow scores are authoritative.
- No historical artifact is rewritten just to match new prose.

## Phase 14E — Semantic parity run

### Objective

Prove consolidation did not change truth.

### Required parity cases

Run the canonical lifecycle against a small existing/synthetic campaign and compare with known results:

- baseline/no-op -> `probe`
- materialization-block/gold-touch -> `block`
- in-scope GEPA candidate from Phase 12-13 -> `probe`
- missing model backend -> non-success/skipped, no fake behavioral claim

### Acceptance

- New lifecycle result matches existing artifacts' authoritative verdicts.
- Any difference is explained as a bug or explicitly documented migration, never hand-waved.
- `autonomous_gap_closure_count` remains `0`.

## Phase 14F — Roadmap closure

### Objective

Close the active roadmap without authorizing post-14 work.

### Work

Update:

- `docs/ROADMAP.md`
- `docs/implementation-notes.html` if it is still the running log
- optional short `docs/lifecycle-consolidation-inventory.md`

State:

- Phase 14 completed or partially completed;
- active roadmap ends here;
- post-14 items require review decisions;
- sealed evaluator/controller/workflow-index/tool-adapter work is not implicitly authorized.

## Feedback loop

For each change:

1. Identify the duplicate authority path or confusion being removed.
2. Add a test or artifact comparison that would fail without the change.
3. Implement the smallest composition/refactor.
4. Run targeted tests.
5. Run the full relevant suite.
6. Inspect generated artifacts for contradictory verdicts, stale metrics, or fake authority.
7. Continue only if green.

Never weaken gold, evaluator truth, budgets, materialization policy, protected cases, or FDR gates to
make consolidation pass.

## Required validation

Before final commit:

- `python3 tools/check-conformance.py`
- `python3 tools/run-gepa-real.py --self-test`
- `python3 tools/run-behavioral-eval.py --self-test`
- `python3 tools/render-promotion-bundle.py --self-test`
- `python3 tools/replay-candidate.py --self-test`
- new lifecycle entrypoint `--self-test` if created
- canonical behavioral campaign hash check
- `git diff --check`
- clean worktree leak check for worktrees, jails, proposer temp dirs

If possible, also run a clean-HEAD worktree smoke test to distinguish committed-tree validation from the
dirty workspace's extra files.

## Commit guidance

Prefer small commits:

1. `docs(lifecycle): map current experiment authority paths`
2. `feat(lifecycle): add canonical experiment lifecycle entrypoint`
3. `docs(roadmap): close active roadmap at Phase 14`

Do not push unless explicitly asked.

## Final report template

- commits
- public lifecycle command
- old entrypoints classified
- parity table
- tests run
- artifacts produced
- complexity deleted/internalized
- complexity deliberately retained
- `autonomous_gap_closure_count`
- post-14 review backlog status
- blockers
