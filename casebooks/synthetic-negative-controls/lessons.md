# Lessons — synthetic-negative-controls

A fully invented calibration case. Its only job: keep the routing layer honest by pairing the *same*
strong activations as the real engagement with the **opposite** verdicts.

## Activation is not a verdict
Every signal here lit a pattern card correctly — owner id in the body, v1/v2 routes, model id in the
body, output through a renderer. And every one resolved to **held** or **refuted**. The card telling
you "look here" is the start of the work, never the finding. A harness that confirms on activation is
a bug generator.

## The three shapes of "no bug" worth remembering
- **Held policy:** the control is applied *unconditionally* (all user classes), so the disallowed
  value is coerced. This is the correct counterpart to a fail-open finding — same activation, opposite
  outcome, decided by whether the policy is loaded for *this* principal.
- **Ignored selector:** the client-supplied id is present but the server resolves authority from the
  session and never trusts it. The canary stays absent from every response.
- **Inert reflection:** the payload renders but does not execute. The execution canary never fires.

## Use
Pair this with `case-2026-06-b2b-agentic-chat` in any routing eval: the real case proves the harness
*finds*; this synthetic case proves it *doesn't over-claim*. A routing pass that flips any row here to
"confirmed" has failed calibration.
