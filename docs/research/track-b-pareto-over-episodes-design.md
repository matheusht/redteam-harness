# Track B Design — Pareto Over Episodes

Status: design only. Do not implement parent selection until broker-derived feedback, runtime-gaming
fixtures, held split pinning, and replay reporting all pass.

## Invariant

Coverage niches must be evaluator-owned. A candidate may win on an episode, but it may not define the
episode axis, the niche label, the held split, or the scoring function that records the win.

## Proposed Shape

- The behavioral evaluator emits per-episode broker-owned outcomes.
- A campaign-level archive stores `{episode_id, oracle_class, candidate_id, cost, replay_stable}`.
- Parent sampling may choose from candidates that win at least one evaluator-owned episode, instead of
  only the aggregate incumbent.
- Eligibility gates remain unchanged: conformance, FDR 0, immutable evaluator, single mutation,
  held-split clean, and 3/3 replay stability.

## Anti-Cheat Risks

- **Self-defined niche:** candidate adds a new axis or episode label and claims new coverage.
- **Visible-only overfit:** candidate improves on train/reflection episodes but loses the held sibling.
- **Cost gaming:** candidate reports cheaper cost without broker ledger support.
- **FDR tradeoff:** candidate adds coverage while confirming non-findings.

All four are vetoes. The archive is advisory until a later decision accepts it as a selector.

## Stop Condition

Do not build Pareto selection if the runtime-gaming corpus catches any accepted non-broker claim, if a
held split is absent, or if replay variance shows a candidate is not stable. If K frontier samples add
no distinct broker-confirmed held episode at equal or lower cost, fall back to the current
incumbent-vs-one loop.
