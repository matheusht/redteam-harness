# Decision 0002 — GEPA autoresearch scope, DSPy posture, and capability ladder

**Status:** accepted as product direction; implementation plan still pending  
**Date:** 2026-06-26  
**Related:** `docs/architecture-brainstorm-gepa-dspy.html`, `docs/autoresearch-evaluation-rfc.html`, `docs/ROADMAP.md`, `evals/qualification/`, `evals/hermetic/`

## Decision

The harness will move toward GEPA-driven autoresearch, but it will do so through verifiable,
auditable slices. The product direction is larger than a tiny prompt-optimization demo, but every
candidate must remain small enough to benchmark, attribute, replay, and reject.

The guiding rule is:

> Bigger campaigns are allowed; individual mutations stay narrow.

GEPA will initially run as a shadow optimizer that proposes candidate changes and evidence bundles.
It may explore multiple tracks in one campaign, but each candidate mutates exactly one declared
component. Promotion remains PR-only and human-reviewed.

DSPy is not part of the first implementation path. It remains a bounded future spike for stable
structured LM modules if the standalone GEPA adapter proves useful and DSPy adds measurable value.

## Current basis

The evaluator foundation is no longer only prose:

- routing has mechanical scoring;
- false-discovery has a scorer;
- model-in-the-loop qualification exists;
- a hermetic no-model BOLA target exists;
- routing is qualified on two surfaces:
  - the original agentic-chat style surface; and
  - `rotation-case-01-web-api`, a fresh billing/profile web API case.

The rotation case also surfaced a deliberate coverage gap: server-side request forgery is not modeled
by any current pattern card. The correct router behavior was to flag a coverage gap rather than
force-fit an unrelated card. This is now part of the desired architecture: unknown coverage should
be made visible, not hidden by broad labels.

## Product choices

### 1. First GEPA campaign may be multi-track, but not multi-mutation

The first GEPA campaign may evaluate several tracks:

- `task-reframing`;
- `decomposition`;
- one new technique-card candidate.

However, each candidate must mutate only one declared component.

Allowed:

```text
candidate A mutates task-reframing only
candidate B mutates decomposition only
candidate C proposes one new technique card only
```

Not allowed yet:

```text
candidate X mutates task-reframing + decomposition + routing + scorer
```

Why: campaign breadth is useful, but candidate attribution matters. If a candidate wins, the harness
must know which change caused the win. If a candidate fails, the failure must be debuggable.

### 2. Shadow GEPA can start before a perfect benchmark suite; promotion cannot

GEPA shadow runs may start using the current evaluator fixtures, qualification cases, and hermetic
targets. The first goal is to prove the integration and evidence flow.

Promotion into Plane 1 requires stronger evidence:

- conformance passes;
- false-discovery invalid accepts remain zero;
- protected incumbent cases do not regress;
- budget and cost ledgers match the campaign manifest;
- at least one rotated case not derived from the same source lineage is included;
- replay stability is recorded;
- a human reviews the evidence bundle.

This lets the harness learn quickly without pretending the current benchmark set is complete.

### 3. Candidate artifacts are JSON plus Markdown plus diff

Use three artifact layers:

```text
candidate-manifest.json   # machine truth: hashes, budgets, lineage, mutable component
scores.json               # scorer outputs and cost/replay results
evidence-bundle.md        # human/model review surface: what changed, why, failure analysis
candidate.diff            # proposed patch
```

JSON is canonical for gates. Markdown is canonical for review and reflection. The diff is canonical
for the proposed code/card change. No single format should try to do all three jobs.

### 4. Standalone GEPA first; DSPy later only if it earns its keep

The first implementation should use GEPA directly with a narrow custom adapter.

Reasoning:

- the harness currently works through Markdown cards, JSON schemas, and deterministic scorers;
- standalone GEPA maps directly to textual card variants and evaluator traces;
- a DSPy refactor would introduce a new programming model before the value is proven.

DSPy remains useful later for typed LM modules such as:

- routing-output normalization;
- evaluator-output normalization;
- planner task generation;
- report summarization.

A DSPy spike is acceptable only when it is isolated, benchmarked, and reversible. A full DSPy rewrite
is out of scope.

### 5. Rotated cases come from sanitized archetypes first, Docker later

For routing and evaluator qualification, prefer sanitized archetype casebooks over dockerized
targets. Public resources can inspire cases, but raw challenge names, flags, solutions, and writeups
must not enter Plane 1.

Good sources for archetype inspiration:

- Microsoft AI Red Teaming Playground Labs;
- vulnerable AI app resource catalogs;
- selected web CTF archetypes used only as source inspiration.

Dockerized targets are reserved for hermetic benchmark work where the additional setup buys
determinism or higher-fidelity replay. Lightweight casebooks come first because they are cheaper to
review, easier to scrub, and friendlier to laptop-class development machines.

### 6. Promotion is PR-only

GEPA may create a branch and evidence bundle. It may not directly edit Plane 1 on `main`.

Promotion path:

```text
GEPA candidate
  → isolated branch
  → conformance + scorers + replay
  → evidence bundle
  → human review
  → PR merge
```

Manual copy into `skills/techniques/` is discouraged because it loses provenance. Direct commits to
the default branch are out of scope.

## Future expansion requiring review

The following capabilities are intended product directions, but not Phase-3A permissions.

### GEPA optimizing evaluators, oracles, gold labels, casebooks, budgets, or sealed data

This is desired eventually as evaluator co-evolution, but it requires a separate meta-evaluation
system. Otherwise GEPA can win by changing what "winning" means.

Minimum future requirements:

- a sealed meta-evaluator outside the candidate's writable space;
- protected historical cases that must remain stable;
- false-discovery invalid accepts remain zero;
- casebook/gold/budget changes are reviewed as evaluator changes, not technique changes;
- human approval before merge.

Until that exists, these artifacts are immutable during GEPA campaigns.

### GEPA running against live engagements

Live GEPA can eventually improve target-specific strategy, reduce manual trial-and-error, and suggest
better next probes from real failure traces. It also risks overfitting to one client, increasing
traffic, learning target secrets, contaminating benchmark memory, or escalating beyond scope.

Adopt a staged path:

1. **Live advisory mode** — GEPA reads scrubbed live traces and suggests next variants; a human
   approves before execution.
2. **Live bounded mode** — GEPA proposes inside one scoped objective with fixed budget, no Zone-2
   artifacts, and no automatic promotion.
3. **Live autonomous mode** — requires a run registry, rate limits, kill switch, scope enforcement,
   and separate design review.

No live GEPA mode should write reusable harness memory directly.

### Autonomous exploit-chain construction and PoC generation

The long-term harness should help with general red-team proof construction, including PoCs, but this
must follow a capability ladder:

```text
Level 0: evidence explanation only
Level 1: benign canary proof
Level 2: local hermetic PoC
Level 3: scoped live PoC with human confirmation
Level 4: autonomous exploit chaining — separate review required
```

The current harness may pursue Levels 0-2 inside the existing safety model. Level 3 requires explicit
scope and human confirmation. Level 4 is future work and must not be enabled implicitly by GEPA.

## How future agents should act

- Treat this document as architecture direction, not implementation completion.
- Do not start GEPA by broadening what candidates may mutate.
- Do not use DSPy as a prerequisite for GEPA.
- Do not vendor raw public challenge repos into the harness.
- Do not force-fit coverage gaps into existing cards; record them.
- Do not edit evaluator artifacts to make a candidate pass.
- Do write campaign decisions into manifests and evidence bundles.
- Do promote successful changes through PR review only.

## Immediate follow-up

The next document should be an implementation plan in phases, not another architecture brainstorm.
That plan should decide:

1. the first GEPA track set;
2. the manifest schemas;
3. the shadow campaign runner interface;
4. the exact benchmark set for the first run;
5. the promotion bundle format;
6. which future capability, if any, gets a design-review placeholder first: live GEPA, evaluator
   co-evolution, SSRF pattern card, or PoC ladder.
