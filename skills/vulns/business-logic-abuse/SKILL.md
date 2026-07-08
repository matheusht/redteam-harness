---
id: bizlogic.business-logic-abuse
name: Business Logic Abuse
description: >
  Prove a multi-step process (checkout, coupon redemption, workflow state machine) can be skipped,
  reordered, or replayed because a transition is enforced only client-side or only assumed from
  prior client state, never re-validated server-side. The objective — confirmed only against a
  precisely-named broken invariant, not a general "the flow felt off."
type: vuln
owasp: "OWASP Top 10 (no single CWE) — workflow/logic flaws"
atlas: "—"
patterns: []

activation:
  strong:
    - "a step's completion is trusted from a client-supplied flag/state rather than re-checked server-side"
    - "a one-time token/coupon/discount can be replayed because redemption isn't atomically consumed"
    - "quantities, prices, or totals accept negative, zero, or overflow values the UI wouldn't offer"
    - "a check-then-use sequence (validate balance, then debit) has an exploitable window between the two"
  weak:
    - "the UI hides a step but the underlying endpoint's server-side enforcement is unconfirmed either way"
  negative:
    - "the server independently re-validates state transitions regardless of client-supplied flags → likely held"
    - "redemption/consumption is atomic (locked or single-use enforced server-side) → likely held"

safe_signal:
  proxy: >
    a predeclared distinctive artifact only reachable by completing the broken transition out of
    order or more than once — e.g. a benchmark's flag revealed by skipping a step, or a planted
    canary discount/balance state in an owned test account. Never a real financial or entitlement
    change in a live account you don't own.
  never: >
    do not exploit a real discount/balance/entitlement bypass beyond the minimum needed to prove
    the invariant broke; revert any state change in cleanup.md.

impact_escalation:
  enabled_by: scope.md#impact_demo_authorized
  requires: human_confirm
  containment: "synthetic/owned account only; revert any state change; log in engagement cleanup.md"

oracle: [signal-oracle, adjudication-oracle]
severity_rubric: { financial_or_entitlement_bypass: critical, workflow_step_skip_no_financial_impact: medium, cosmetic_state_inconsistency: low }

procedure:
  - "MAP THE STATE MACHINE: enumerate the intended step order and what each transition is supposed to require."
  - "CLASSIFY EACH TRANSITION: for each step, determine whether the server re-validates prior-state independently, or trusts a client-supplied flag/sequence."
  - "NEGATIVE CONTROL: attempt the normal, in-order flow first and confirm it behaves as intended — you need a baseline before claiming a bypass."
  - "ATTACK: replay, skip, or reorder the minimum steps needed to reach the marker (planted canary or flag) without satisfying the real precondition."
  - "NAME THE BROKEN INVARIANT precisely — 'coupon reusable' or 'checkout completable with balance unchecked' — not 'the flow has issues.'"
  - "Default to needs_review unless the broken invariant and its reproduction are both stated exactly; logic findings are highly context-specific and easy to overclaim."
  - "REPLAY in a fresh session; revert any state change made in the process."

emits: [attempt, finding]
---

## What "confirmed" looks like here
A named state-machine invariant (a step, a limit, a single-use guard) is broken by a client-driven
skip/reorder/replay, proven by reaching the planted marker without satisfying the real
precondition, reproduced once, with the normal in-order flow behaving correctly as a baseline.

## Not this card
- A UI-only affordance that hides a step, where the underlying endpoint independently re-validates
  → the guard holds; not a finding just because the client could ask.
- A rate-limit or fair-use complaint with no broken invariant named → route elsewhere, not this card.

## Do not overclaim
- "I sent requests out of the expected order" is not a finding until you show what state the
  server should have rejected and didn't.
- A single ambiguous state inconsistency without a clear before/after is `needs_review`, never
  `confirmed`.
