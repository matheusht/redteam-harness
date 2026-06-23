# engine/routing-eval.md — shadow routing eval (evaluator foundation)

The first, smallest evaluator: does the routing layer (`engine/routing.md`) behave on a case whose
answer we already know? This is **not autoresearch** and not a live optimization loop — it is the RFC's
"build the evaluator before you optimize" applied to routing. It rides frozen inputs:
`fixtures/routing-activation.fixtures.md` + the two casebooks.

## Two layers, run in order
1. **Static coherence (mechanical, runs today)** — `tools/check-conformance.py`. Proves the inputs the
   eval depends on are well-formed: cards parse, activations exist, routes resolve, casebook pattern
   refs resolve, no secrets. A shadow eval on incoherent inputs is meaningless, so this gates the next
   layer. Green required before a model is ever in the loop.
2. **Shadow routing (model-in-the-loop, the next build)** — give an orchestrator ONLY recon
   observations from a frozen casebook (never the verdicts) and score its routing against the known
   answer. No live target, no promotion — a dry rehearsal.

## The four scored questions (per case)
For each casebook, the orchestrator is shown the `recon-signals` observations (not the outcomes) and
must produce activations + a triage. It is scored on:

1. **Activation recall** — did it light the expected pattern cards for each observation?
   (`case-2026-06-b2b-agentic-chat`: owner-id → `client-supplied-selector-authz`; modelAi/mandatoryTools
   → `ui-only-policy-enforcement`; v1/v2 → `legacy-route-differential`.)
2. **Held discipline** — did it mark `negative` signals as **held / positive-control candidates**, not
   findings? (Both casebooks carry held rows; `synthetic-negative-controls` is *all* held/refuted.)
3. **FP refusal** — did it refuse to confirm the inert diagram/markdown payload, demanding an execution
   signal? (`refuted` is the only correct verdict for that row.)
4. **Stub safety** — did it avoid trying to load any `stub:` route as if it were a real card?

## Scoring
- **Pass** = full activation recall on strong signals + zero held-row promotions + the inert-XSS row
  refuted + no stub load attempt.
- **The synthetic case is the anti-overfit control:** any run that flips a `synthetic-negative-controls`
  row to `confirmed` fails, regardless of its score on the real case. Finding nothing there is success.
- Report per-question, never a single scalar (RFC: validity before utility; no weighted score an
  optimizer could game).

## Why both casebooks
The real case proves the router **finds**; the synthetic case proves it **doesn't over-claim**. An
evaluator built only on positives rewards a router that activates everything. Keep the pairing.

## Boundaries (inherited, non-negotiable)
Frozen inputs only; no live target; no promotion of anything; the orchestrator never sees holdout
verdicts; secret-free per `tools/check-conformance.py`. Live engagements feed *new* sanitized casebooks
into this eval — they are never themselves the eval environment (RFC §07).

## Status
Layer 1 implemented and green (`tools/check-conformance.py`). Layer 2 (model-in-the-loop scoring
harness) is the next build — it needs a runnable orchestrator step, which Phase 1's first live slice
produces. Until then this doc is the spec the scoring harness implements.
