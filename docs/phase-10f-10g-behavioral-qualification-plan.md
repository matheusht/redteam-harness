# Phase 10F–10G — Behavioral Evaluator Hardening and Real-Model Qualification

**Status:** Phase 10F complete; Phase 10G adapter contract + fake adapter complete; the real-model
qualification run is **BLOCKED/SKIPPED** (no sufficiently isolated LM backend configured). Simulator
success is not substituted. See `docs/decisions/0003-autonomy-envelopes.md` and the behavioral README.\
**Expected duration:** 1–3 focused hours\
**Depends on:** Phases 8–10, Decision 0002, the autoresearch evaluation RFC\
**Does not authorize:** live-target testing, Zone-2 actions, evaluator co-evolution, or automatic Plane-1 promotion

## Outcome

Turn the Phase-10 simulator proof into a trustworthy real-model evaluation boundary.

At the end of this goal, the harness should either:

1. complete one blind, paired, technique-sensitive real-model qualification run; or
2. report the real-model run as honestly blocked because no sufficiently isolated LM backend is
   available, while leaving the adapter contract and all model-free integrity tests complete.

An unavailable model is not a reason to substitute simulator results or claim qualification.

## Architectural position

The long-term product is autonomously adaptive inside a pre-authorized envelope. Humans grant or
expand authority; mechanical policy and evidence should handle routine decisions inside that
authority.

This goal does not relax the current safety constitution. It prepares the control plane needed to
relax unnecessary human involvement later without allowing the optimizer to grade itself.

Create `docs/decisions/0003-autonomy-envelopes.md` during this goal. It should:

- preserve Decision 0002 as historical context;
- record the accepted direction that offline/hermetic candidate generation, evaluation, rejection,
  replay, archival, and PR creation should become autonomous;
- retain human authority for scope expansion, current Zone-2 gates, evaluator/gold/budget mutation,
  irreversible live impact, and Plane-1 merge for now;
- describe a future promotion ladder: autonomous evidence → autonomous PR → staging/canary
  auto-promotion after qualification → possible low-risk Plane-1 auto-promotion only after a separate
  accepted policy;
- explicitly forbid a candidate from changing its evaluator and using that evaluator to authorize
  itself.

Do not silently weaken `AGENTS.md` or the existing scope fence in this slice.

## Phase 10F — Correctness and provenance hardening

### 1. Immutable run artifacts

Replace the shared `behavioral-report.json/.md` output with run-specific artifacts:

```text
evals/behavioral/campaigns/<campaign-id>/runs/<run-id>/
  run-manifest.json
  report.json
  report.md
  events.jsonl
```

The run manifest must pin:

- campaign, candidate, incumbent, and technique-card hashes;
- episode, scorer, evaluator, and model-adapter hashes;
- backend, model identifier, model configuration, seeds, budgets, and timestamps;
- run status: `completed`, `blocked`, `skipped`, or `failed`.

A skipped model attempt must never overwrite a completed simulator or model run. A campaign index may
point to runs, but must not replace their evidence.

### 2. Reuse the campaign contract gate

Behavioral evaluation must consume canonical campaign and candidate manifests. Before applying or
running a candidate:

- run the existing immutable/touched-file/budget/hash gate;
- apply exactly one declared candidate in isolation;
- run conformance in the patched workspace;
- carry measured gate results into `score-candidate.py`.

Do not hardcode `conformance_passed`, `budget_unchanged`, `single_mutation`,
`evidence_contract_complete`, or protected capabilities to `true`.

The deliberately degraded behavioral control may remain a test fixture, but must be clearly excluded
from promotion eligibility.

### 3. Truly paired replay

Run incumbent and candidate in every session:

```text
session 0: incumbent(seed-0) ↔ candidate(seed-0)
session 1: incumbent(seed-1) ↔ candidate(seed-1)
session 2: incumbent(seed-2) ↔ candidate(seed-2)
```

Use identical model configuration, tasks, budgets, and target versions. Randomize or deterministically
alternate anonymized A/B order and record it. Require the existing strict 3/3 reproduction rule for
hermetic qualification.

### 4. Broker-derived evidence

The researcher may request actions and emit a final assessment, but cannot self-report that a control
or replay occurred.

An evaluator-side broker must be authoritative for:

- which probes executed;
- target responses;
- negative/positive controls;
- fresh-session replay;
- model and target calls;
- tokens and elapsed time;
- evidence references.

`confirmed` is valid only when the broker event log proves every oracle requirement. Missing,
invented, duplicated, or out-of-budget events block or downgrade the result.

### 5. Capability-level blindness

`assert_blind()` remains a payload check, not the security boundary.

The model researcher must receive only the serialized researcher view and mediated action responses.
It must not receive:

- repository or worktree filesystem access;
- evaluator code, gold, classes, crosswalks, or scores;
- candidate identity or incumbent/candidate labels;
- unrestricted network access;
- raw credentials or secrets.

The evaluator process owns gold and scoring. The optimizer, researcher, and evaluator use isolated
contexts with no shared conversational memory.

## Phase 10G — Real-model adapter and qualification

### Adapter contract

Add a provider-neutral researcher interface. Prefer a narrow subprocess/JSONL or callable adapter over
a harness-wide SDK dependency.

Required behavior:

- strict structured action and final-output schemas;
- bounded retries for malformed output;
- model unavailability records `skipped` and returns non-success;
- all provider/model settings and usage are recorded;
- no LLM judge can override a mechanical failure.

Include a deterministic fake adapter in CI so the protocol is tested without credentials.

### Qualification sequence

Run, in order:

1. incumbent baseline;
2. identical/no-op candidate;
3. deliberately degraded control;
4. existing task-reframing candidate;
5. existing decomposition candidate.

Do not run GEPA-generated novel candidates until the real-model researcher:

- preserves incumbent positives;
- confirms no held/refuted/contaminated case;
- blocks the degraded control;
- respects the probe budget;
- passes all three paired sessions;
- produces broker-verifiable evidence and accounting.

If a real isolated model backend is available, capture one complete qualification run. If it is not,
finish the adapter and fake-adapter tests, record the blocker, and do not claim real-model
qualification.

## Adversarial feedback loop

Use this loop for every change:

```text
observe failure
  → classify invariant violated
  → add or strengthen a failing regression fixture
  → implement the smallest general fix
  → run targeted test
  → run full conformance/self-tests
  → inspect artifacts for contradictory claims
  → continue only when green
```

Required adversarial fixtures:

- model tries to request gold/scorer files;
- task text attempts prompt injection against the researcher;
- final output claims controls that the broker did not execute;
- candidate changes an immutable file or budget;
- candidate loses incumbent coverage;
- candidate gains coverage while increasing FDR;
- malformed output exhausts retries;
- skipped/failed run attempts to overwrite a completed report;
- duplicate evidence is presented as new coverage.

Never edit frozen gold or oracle expectations in the same iteration to make a failure pass. If a
fixture is genuinely wrong, change it in a separate, explicit evaluator-change commit and rerun the
incumbent before evaluating candidates.

If the same external blocker occurs three times, stop retrying, record `blocked`, and finish all
remaining model-independent work.

## Acceptance criteria

- Phase-10 report JSON and Markdown cannot contradict each other or be overwritten across backends.
- Every behavioral candidate passes through the canonical campaign gate and patched-workspace
  conformance.
- Incumbent and candidate run as paired A/B executions in primary plus two fresh sessions.
- Controls, replay, cost, and evidence come from broker events, never model declarations.
- The researcher has no evaluator/repository access by construction.
- Routing remains a measured protected capability and is not counted as confirmed coverage.
- FDR remains a hard veto.
- The degraded control blocks; the no-op candidate cannot become `allow`.
- A real-model run either qualifies honestly or is recorded as blocked/skipped; simulator success is
  never presented as real-model success.
- No candidate promotes automatically in this goal.
- All conformance checks and tool self-tests pass.
- No temporary worktrees remain.
- Existing unrelated working-tree changes remain untouched.
- Decision 0003, the roadmap, implementation plan, behavioral README, and implementation notes agree
  with the implemented state.

## Commit policy

Prefer two scoped commits if both phases complete:

1. `fix(eval): harden behavioral provenance, gating, and paired replay`
2. `feat(eval): add blind real-model researcher qualification`

If Phase 10G is blocked, commit the completed Phase 10F and tested adapter contract separately, and
record Phase 10G as blocked. Do not use a passing simulator run to close it.

Do not push unless the operator explicitly asks.

## Explicitly deferred

- Live engagement optimization.
- Automatic Plane-1 merge.
- Evaluator/oracle/gold/casebook/budget co-evolution.
- Sealed holdout service.
- Autonomous campaign scheduler/run registry.
- Zone-2 or exploit-chain autonomy.

The next plan after this goal should cover the sealed evaluator boundary plus autonomous campaign
controller, followed by bounded live operation under scope-as-code.
