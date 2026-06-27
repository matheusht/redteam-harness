# Decision 0004 — Epistemic autonomy and complexity budget

**Status:** accepted\
**Date:** 2026-06-27\
**Effect:** supersedes Decision 0003 by absorbing its autonomy envelope; preserves
Decision 0002 for GEPA scope and capability history\
**Related:** `AGENTS.md`, `docs/ROADMAP.md`, `docs/autoresearch-evaluation-rfc.html`,
`docs/gepa-autoresearch-implementation-plan.md`

## Context

The harness is at an inflection point. It has enough evaluation machinery to begin learning, but each
new layer also increases the code and context future agents must reason over. Agentic coding makes that
cost compound:

```text
unnecessary mechanism
  → larger code/context surface
  → weaker reasoning and more local mistakes
  → compatibility fixes and special cases
  → still larger code/context surface
```

The project therefore needs one product direction that governs both autonomy and simplicity.

The current state must remain explicit: **no candidate has yet demonstrated an improvement using a
real model.** The simulator and fake researcher prove the contracts and gates; the real-model
qualification remains blocked. The architecture below is the intended spine, not a claim that the
learning loop has already succeeded.

## Decision

### 1. Optimize for epistemic autonomy

Autonomy is split into three independent powers:

| Power | Meaning | Product posture |
| --- | --- | --- |
| Epistemic autonomy | Generate hypotheses, test them against reality, and retain reproducible learning | Maximize |
| Operational autonomy | Execute experiments and target actions | Bound by a pre-authorized envelope |
| Constitutional autonomy | Change what counts as true, better, safe, or authorized | Keep outside the candidate loop |

The north star is not action without supervision. It is learning without requiring a human to author
each hypothesis, case, label, or technique improvement.

Humans continue to define authority and values. The environment and broker provide evidence. The
system performs bounded research.

### 2. Use one conceptual spine: an evidence-producing experiment inside an authorization envelope

Every run can be understood through six roles:

```text
authorization → hypothesis → strategy → broker → oracle → learning policy
```

- **Authorization** defines what may happen.
- **Hypothesis** states what might be true.
- **Strategy** chooses the next bounded experiment.
- **Broker** records what actually happened.
- **Oracle** decides what the recorded evidence proves.
- **Learning policy** decides whether a result is rejected, probed, retained, or proposed for promotion.

These are roles for reasoning about the existing system, **not instructions to create six classes,
services, or agents**. A new implementation abstraction is justified only when the current code cannot
enforce the role boundary faithfully.

AI may be load-bearing in hypothesis generation and strategy. It must not be the authority for scope,
event truth, or mechanical adjudication.

### 3. Measure effects; do not trust an untrusted component's description of itself

Standing reframe:

> **Stop parsing what the untrusted thing claims. Measure what actually happened.**

Examples:

- Do not trust a researcher claiming it ran a control; derive controls from broker events.
- Do not make a final candidate authorization decision from patch metadata; apply it in isolation and
  measure the resulting changed tree.
- Do not trust a candidate-reported cost; derive cost from model and target call ledgers.
- Do not trust a claimed finding; require the signal and adjudication oracles.

Parsing remains useful as a cheap **preflight**. It is not authoritative when the system can safely
measure the resulting state.

For candidate changes, the intended contract becomes:

```text
manifest/hash preflight
  → isolated worktree apply
  → actual changed-tree measurement
  → declared == actual
  → actual ⊆ mutable allowlist
  → trusted conformance
  → behavioral evaluation
```

There must be no final `allow` without successful materialization and measurement. The current pure
campaign gate remains useful for fast rejection, but it becomes a preflight rather than the final
authority.

### 4. Treat complexity and loaded context as finite budgets

Code, documentation, entrypoints, schemas, and always-loaded instructions all consume the same
reasoning budget.

Before adding an abstraction, dependency, runner, or durable document, record:

1. the concrete capability or invariant it adds;
2. the existing path it replaces, simplifies, or makes internal;
3. the new concepts and failure modes introduced;
4. the effect on the orchestrator's loaded context;
5. the evidence that a smaller contract or deletion cannot solve the problem;
6. the removal plan if the experiment does not earn its keep.

A new abstraction should normally either:

- delete or internalize duplicated behavior;
- enforce an invariant that cannot be enforced locally; or
- hide unavoidable external complexity behind a smaller stable interface.

Potential future reuse is not sufficient justification.

A review that closes a bypass by adding another special case is a reframe trigger. First ask whether a
different source of truth removes the entire bypass category. Forced simplicity is also a failure:
irreducible boundaries such as broker-owned evidence must not be collapsed merely to reduce line count.

### 5. Consolidate the lifecycle before adding an autonomous controller

The current lifecycle is conceptually one pipeline:

```text
preflight → apply → measure → score → replay → record
```

It is currently exposed through several scripts. Before building the autonomous campaign controller,
the project must establish:

- one canonical public experiment entrypoint;
- one campaign/candidate contract;
- one run-status and artifact contract;
- one authoritative implementation for each lifecycle stage;
- explicit internal or historical status for older entrypoints.

This is not permission for a framework rewrite. Existing tested functions should be composed and old
paths retired incrementally. The first proof is the apply-then-measure candidate boundary; the broader
consolidation proceeds only after that smaller contract is validated.

### 6. Preserve the autonomy envelope

Inside a pre-authorized offline or hermetic envelope, the system may eventually run without per-step
human approval:

- candidate generation;
- evaluation and replay;
- rejection and archival;
- experiment scheduling;
- evidence-bundle and PR creation.

Humans retain authority, for now, over:

- scope expansion;
- Zone-2 actions and irreversible live impact;
- evaluator, oracle, gold, budget, or casebook changes;
- Plane-1 merge.

The load-bearing invariant remains:

> A candidate can never change its evaluator and then use that changed evaluator to authorize itself.

Evaluator evolution is a separate experiment class governed by a sealed meta-evaluator and a future
accepted decision.

### 7. Keep the project's earned honesty visible

The primary autonomy metric is:

```text
autonomous_gap_closure_count
```

It starts at **0**.

A closure counts only when:

1. the system discovers a previously unmodeled or uncovered behavior without a human authoring the
   benchmark case for that discovery; the behavior is deduplicated by root cause and oracle boundary,
   so splitting one weakness across routes, prompts, or reports does not create extra closures;
2. it proposes a bounded candidate without a human writing the candidate;
3. broker/oracle evidence confirms the improvement with zero false-discovery regression;
4. protected incumbent cases remain intact;
5. the result reproduces under the required replay policy and passes validation or sealed evaluation;
6. the candidate did not mutate its evaluator or budget.

SSRF and indirect-prompt-injection were valuable system-surfaced gaps, but remain human-closed and
therefore do not increment this metric.

Efficiency, coverage, and cost remain supporting metrics. They do not substitute for autonomous
learning.

## Documentation authority

This decision is accepted; therefore:

- this decision is the canonical autonomy and complexity policy;
- Decision 0003 is marked superseded rather than maintained in parallel;
- `docs/ROADMAP.md` remains canonical for current status and next work;
- executable schemas, gates, and tests remain canonical for implementation truth;
- implementation notes and HTML artifacts remain historical/explanatory and must not duplicate live
  status as independent authority.

This decision should absorb later corrections to the autonomy frame rather than spawning another
principles document.

## Roadmap consequences

1. **Measured candidate boundary:** preserve the pure gate as preflight; make isolated apply plus actual
   changed-tree measurement authoritative. Delete patch-format special cases only after parity tests
   prove the measured boundary is faithful.
2. **Real-model qualification:** obtain the first genuine behavioral signal. Do not claim autonomous
   learning from simulator results.
3. **Lifecycle consolidation checkpoint:** establish one canonical public experiment flow before an
   autonomous controller.
4. **Sealed evaluation and first real GEPA campaign:** permit novel candidates only after the
   real-model researcher qualifies; promotion remains gated.
5. **Autonomous campaign controller:** automate scheduling, replay, rejection, archival, and PR creation
   over the canonical lifecycle.
6. **Bounded live operation:** proceed later under scope-as-code, action brokering, rate limits, and the
   existing escalation gates.

## Non-goals

- No new strategy/broker/oracle class hierarchy is mandated.
- No unified `frozen_case` abstraction is approved without a fidelity audit.
- No DSPy adoption is implied.
- No live autonomy or automatic Plane-1 merge is authorized.
- No complexity metric based only on lines of code is adopted.

## Acceptance questions (resolved on acceptance)

1. **Measured apply boundary precedes real-model qualification.** The authoritative apply-then-measure
   candidate boundary (Phase 10H0) is built first, while the isolated model backend is still being
   established. Trusting measured repository state does not depend on a real model.
2. **`autonomous_gap_closure_count` is the primary learning metric, current value `0`.** Efficiency,
   coverage, and cost remain supporting metrics only.
3. **Decision 0003 is marked superseded immediately,** retained as historical provenance with a forward
   pointer to this decision rather than maintained in parallel.
