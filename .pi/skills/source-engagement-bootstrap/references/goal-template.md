# Source-only long-running engagement goal template

Replace every bracketed field with verified engagement facts. Delete inapplicable sections; never fill unknowns by guessing.

```markdown
# Goal — [ENGAGEMENT_ID]

## Authority and starting state

Execute an authorized, source-only white-box assessment of `[REPOSITORY]` at exact identity `[COMMIT/TAG]`, limited to the signed `engagements/[ENGAGEMENT_ID]/scope.md`. Read `AGENTS.md`, the signed scope, `asset-prioritization.md`, `engine/whitebox-analysis.md`, `engine/loop.md`, `engine/persistence.md`, `engine/regrade.md`, `engine/pocinator.md`, and applicable oracle/card files before acting. Root policy and the signed scope override this goal.

Do not contact production or any live application. Work only in the authorized source tree and signed, disposable local environment. Do not access secrets, other users, real funds/data, or excluded components. Do not file, disclose, deploy, push, or promote memory autonomously.

## Outcome

Produce a rigorously adjudicated disposition for every material candidate in the bounded critical-asset corpus: `confirmed/chained`, `refuted`, `real-but-capped`, `deferred/blocked`, or `covered-dry`. A finding exists only after the oracle and evidence contracts pass. Finding volume is not success; evidence-constrained resolution is.

## Critical assets and bounded corpus

[INSERT RANKED ASSETS, SOURCE PATHS/SYMBOLS, TRUST BOUNDARIES, RELEASE ELIGIBILITY, AND COVERAGE DENOMINATOR]

Before hunting, freeze the denominator and record any newly discovered asset. “Dry” is unavailable while material assets/candidates lack a disposition.

## Progression map — backtrack freely

Stage 0 candidate sink/function narrowing → Stage 1 primitive vocabulary and cheap classifier → Stage 2 source/sink/path triples → Stage 3 cross-function reachability → Stage 3.5 chain construction → Stage 4 finding confirmation → Stage 4.25 post-confirmation verification and classification → Stage 5 chainability → Stage 5.25 novelty and paper-review → Stage 5.5 reachability dossier → advisory draft → Post: triage, regrade, Pocinator, operator review/filing.

This is a map of rigor gates, not a one-pass waterfall. A failure at 4/4.25 returns to 2/3. A chainability failure returns to 3.5. New source evidence can reopen earlier narrowing. Preserve every transition and rationale.

## Search and grading policy

- Rules, regexes, SAST, sink lists, and cheap classifiers are Stage-1 prioritizers only. They cannot kill or confirm candidates.
- Over-generation is cheaper than a false negative. Keep uncertain candidates alive, but do not confuse persistence with infinite repetition.
- No single model pass may kill or bless a candidate. Use genuinely independent runs/sessions with distinct evidence access where available; do not simulate multiple experts in one response. If independence is unavailable, route to human review or retain `needs_review`/`blocked`.
- Separate finder, keep/kill review, adjudication, regrade, and Pocinator proof review. Preserve cold-review requirements and contamination status.
- Operator priors influence effort only. They never increase confidence or substitute for source/runtime evidence.

## Verification-of-the-verification

Mechanical signals—breakpoint hit, corrupted state, file written, assertion passed—are necessary but not sufficient. Before confirmation, independently verify that the harness/PoC:

1. exercises the real in-scope source and eligible build;
2. follows reachable production-equivalent control flow and preconditions;
3. does not replace decisive logic with a favorable emulator or mock;
4. has matched negative and applicable positive controls;
5. demonstrates the exact claimed mechanism, reachability, and bounded impact;
6. cannot pass because of fixture setup, monkeypatching, stale state, or reward-hacked assertions.

Large PoCs may require long, decomposed implementation. Persist through debugging while evidence supports the lead, but never make the PoC prove a stronger claim than the target actually supports.

## Model-role preference

Use `[PLANNING_MODEL]` for planning, corpus triage, candidate prioritization, pipeline/debug strategy, and high-context re-evaluation. Use `[EXECUTION_MODEL]` for bounded long-horizon source tracing, harness construction, test iteration, and repetitive implementation work. Helpers may perform offline mechanical extraction/diffing only. Models remain non-oracular; availability must be verified, not assumed.

## Persistence and stopping

Activate persistence only for a confirmed primitive, strong activation signal, or explicit recorded operator prior. Bound each lead before grinding. Alternate zoom-in and zoom-out; a held vector is a wrong turn, while repeated variants of the same disproven path are tunnel vision.

Do not stop merely because construction is difficult or lengthy. Do stop a sub-thread when its bounded variants and decisive falsifiers are exhausted, then move elsewhere. Coverage closure requires [TARGET-SPECIFIC DRY CRITERIA], independent cold review, and two consecutive full coverage passes that add no material candidate—not merely two prompt iterations.

## Human gates and Zone-2

The signed scope may pre-authorize only these exact categories: [EXACT CATEGORY LIST OR NONE]. Category authorization does not authorize construction by itself. Before creating **each** Zone-2 PoC artifact, pause and request fresh human confirmation naming:

- candidate/finding and exact artifact;
- bounded action and capability;
- disposable owned environment and identity;
- expected impact and non-user-impact controls;
- expiry and cleanup obligation.

Proceed only after the fresh confirmation is recorded. Never autonomously cross users/accounts, touch production, use real credentials/funds/data, create destructive or persistent capability, publish a package/image, escalate severity, or file a report. Log every artifact and cleanup status.

## Records and anti-fabrication

Use the canonical engagement record command when available. Attempts/artifacts are immutable; findings are revisioned; views are derived. Record failed attempts, controls, held/refuted candidates, reopenings, cost, and missing evidence. Never invent attempts, source identity, test output, independent review, environment fidelity, or impact. Missing environment produces `blocked`, not synthetic pass/fail.

## Done criteria

Call `goal_complete` only after all are true:

- signed scope and exact source/environment identity remained valid;
- every ranked critical asset and material candidate has a traceable terminal disposition;
- every claimed finding survived independent adjudication, regrade, Pocinator, controls, replay where applicable, and verification-of-the-verification;
- unsupported claims were corrected or withdrawn;
- reports remain internal and revision-bound; no autonomous filing occurred;
- cleanup is terminal or explicitly blocked and operator-visible;
- memory has an operator-reviewed terminal disposition without automatic Plane-1 promotion;
- final summary separates demonstrated findings, supported negatives, unresolved blockers, coverage limitations, cost, and what was not demonstrated.

If a human gate blocks progress, pause with the exact requested decision. Do not redefine the goal smaller, bypass the gate, fabricate completion, or call `goal_complete` early.
```
