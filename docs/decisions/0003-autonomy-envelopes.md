# Decision 0003 — Autonomy envelopes

**Status:** superseded by [Decision 0004 — Epistemic autonomy and complexity budget](0004-epistemic-autonomy-complexity-budget.md)\
**Date:** 2026-06-27\
**Supersedes:** nothing. **Preserves:** Decision 0002 (GEPA autoresearch scope) as historical context;
this decision extends it, it does not relax it.\
**Related:** `AGENTS.md`, `docs/phase-10f-10g-behavioral-qualification-plan.md`,
`docs/gepa-autoresearch-implementation-plan.md`, `docs/autoresearch-evaluation-rfc.html`

> **Superseded.** Decision 0004 absorbs this autonomy envelope unchanged and adds the complexity-budget
> and "measure effects, do not parse claims" policy. The load-bearing invariant below — a candidate can
> never change its evaluator and then use it to authorize itself — is retained verbatim by 0004 and
> remains in force. This document is kept as historical provenance for the Phase 10F–10G control plane;
> for current autonomy and complexity policy, read Decision 0004.

## Context

The long-term product is **autonomously adaptive inside a pre-authorized envelope**: humans grant or
expand authority, and mechanical policy + broker-verified evidence handle routine decisions inside that
authority. The danger this decision guards against is an optimizer that grades its own homework. Phase
10F–10G built the control plane (broker-authoritative evidence, immutable runs, canonical measured
gating, capability-blind researcher, a real-model adapter contract) that makes bounded autonomy safe to
reason about. This decision records the envelope; it does **not** turn autonomy on for anything gated
below, and it does **not** weaken any `AGENTS.md` gate.

## Decision

### The load-bearing invariant

> **A candidate can never change its own evaluator and then use that changed evaluator to authorize
> itself.** Evaluator, oracle, gold, scorers, budgets, and casebooks are immutable during candidate
> evaluation. Any change to them is an explicit, separately-reviewed **evaluator-change** action that
> re-runs the incumbent before any candidate is judged — never folded into a candidate's own run. The
> contract gate (`tools/check-campaign.py`) and the broker enforce this mechanically; the autonomy
> envelope never includes the evaluator.

### Inside the envelope — may become autonomous (offline / hermetic only)

Within a pre-authorized, hermetic envelope, the following may run without per-step human approval:

- candidate **generation** (one declared component per candidate);
- **evaluation** through the canonical gate + patched-workspace conformance + the blind,
  broker-mediated behavioral evaluator;
- **replay** (primary + two fresh sessions, strict 3/3 reproduction);
- **rejection and archival** of `block`/`probe` candidates (immutable run dirs; nothing overwritten);
- **PR creation** carrying the evidence bundle + run manifest for human review.

Autonomy here means: the machine may produce evidence and a PR. It may not merge.

### Outside the envelope — humans retained (for now)

Human authority is still required for:

- **scope expansion** (any new surface, account, or objective — `scope.md` is human-signed);
- **Zone-2 actions** and any impact-demo PoC artifact (`AGENTS.md` §1.3 stands, unchanged);
- **evaluator / gold / oracle / budget / casebook mutation** (reviewed as evaluator changes);
- **irreversible or live impact** of any kind;
- **Plane-1 merge** (promotion is PR-only and human-approved; no direct-to-main, no manual copy).

This decision does not move any of these inside the envelope.

### Future promotion ladder (each rung needs a separate accepted policy)

```
1. autonomous evidence            (here: broker-verified runs + immutable artifacts)        — prepared
2. autonomous PR                  (machine opens a PR; human merges)                         — prepared
3. staging/canary auto-promotion  (after a real-model qualification passes, into a non-Plane-1
                                    staging/canary lane with rollback)                       — future policy
4. low-risk Plane-1 auto-promotion (narrowly scoped, reversible, post-qualification)         — future policy
```

Rungs 3–4 require: a real-model behavioral qualification that passes (Phase 10G, currently blocked on an
isolated LM backend); a sealed evaluator boundary; protected historical cases; zero invalid accepts; and
a separate accepted policy per rung. None are authorized by this decision.

## How future agents should act

- Treat this as direction, not permission to enable autonomy now.
- Never let a candidate run mutate the evaluator/gold/scorers/budget and then score against the mutated
  version; if a fixture is genuinely wrong, fix it as a separate evaluator-change commit and re-run the
  incumbent first.
- Keep the researcher capability-blind: card + neutral task + schema + budget + mediated responses only.
- Keep promotion PR-only and human-merged until a future policy explicitly opens a higher rung.
- Do not weaken `AGENTS.md` or the scope fence to make autonomy more convenient.

## Explicitly out of scope for this decision

Live-engagement optimization, automatic Plane-1 merge, evaluator/oracle/gold/casebook/budget
co-evolution, sealed-holdout service, an autonomous campaign scheduler/run registry, and Zone-2 or
exploit-chain autonomy. The next decision should cover the sealed evaluator boundary plus an autonomous
campaign controller, followed by bounded live operation under scope-as-code.
