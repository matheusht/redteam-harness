# engine/regrade.md — is this finding actually real?

> Pairs with `engine/pocinator.md` (the sibling `Post:` stage) and `engine/whitebox-analysis.md` §4
> ("verification-of-the-verification"). `skills/oracles/adjudication-oracle.md` is this doc's
> philosophical ancestor — same default-to-disbelief posture, same demand for an independently
> re-derived answer, not a reused live-attack checklist (its gates — planted canaries, side-channel
> session contamination — are shaped for black-box signal interrogation and don't transfer to
> source re-derivation, the same reason `engine/pocinator.md` §2 argues rules don't transfer across
> PoC domains). Sits earlier than pocinator in `Post: triage, **regrade**, pocinator, filing` — this
> is the second "Post:" stage to get formalized, and per `engine/pocinator.md`'s own words, the
> *older* discipline: pocinator's "self-attestation is not evidence" lens explicitly borrowed its
> no-prior-context convention from regrade, not the other way around.

## 0. The one distinction that matters

> Regrade asks: "Is the finding real?"
> Pocinator asks: "Does this specific PoC/package actually prove the exact claim we're about to
> report?"

Regrade re-litigates the finding itself — mechanism, escalation completeness, severity, claim
accuracy — from scratch, against primary sources. It runs *before* pocinator, and pocinator's own
claim tuple (`engine/pocinator.md` §4) is a precondition regrade is expected to have settled, not
something pocinator derives independently.

## 1. Where it sits, and why it's a hard gate

```
... -> Stage 4.25 post-confirmation verification -> /goal advisory generation
    -> Post: triage -> regrade -> pocinator -> filing
                          |
                          +-- verdict != confirmed/confirmed_with_correction/escalation_found
                              routes back to Stage 4/4.25, never proceeds to pocinator
```

This is not an optional extra pass. In practice it has already been treated as a blocking
precondition on trusting a finding's own adjudication verdict at all — one real finding's record
reads, verbatim, `"adjudication: false pending regrade — never let a single pass confirm."` No
finding proceeds to pocinator or filing on the strength of its original confirmation alone.

## 2. The one non-negotiable property

**Regrade runs in a fresh context with zero prior investment in the original finding. Full stop —
not "ideally," the way pocinator's own self-attestation lens phrases the analogous preference for
itself.** Every real regrade pass ever run in this harness has been fresh/no-prior-context — three
independent, no-prior-context agents on the Vercel engagement's three findings; an "independent
cold-context regrade fork" on Zuul. Zero counterexamples. This is stronger than a nice-to-have: a
regrade run by the same context that produced the original finding isn't a regrade at all, it's just
more work by a party that's already invested in being right. The entire value of the stage comes from
having no stake in the outcome — dilute that and there's nothing left to formalize.

## 3. Verdict set

`confirmed` · `confirmed_with_correction` · `escalation_found` · `needs_more_evidence` · `refuted` ·
`blocked`

- **`confirmed`** — mechanism, reachability, and claimed impact all hold exactly as originally
  stated, independently re-derived from primary sources.
- **`confirmed_with_correction`** — real, but scope/severity/impact framing needed correcting. A
  regrade pass on a JVM filter-chain finding grepped the full shipped codebase, found no real filter
  actually uses the vulnerable pattern, and downgraded the finding from "default-deployment bypass"
  to "API-safety footgun for third-party filter authors," capping severity from critical to high. A
  separate regrade on a prototype-pollution finding traced further into the vulnerable code path than
  the original pass and revised the severity down (critical → high, a narrower privilege precondition
  than first claimed) while adding two new, honest caveats. The finding survives; the claim changes to
  match what's actually true.
- **`escalation_found`** — regrade surfaces additional impact or reach the original pass missed. One
  regrade pass on a symlink-disclosure finding found a second, unguarded occurrence of the exact same
  vulnerable pattern that the original investigation had explicitly — and wrongly — ruled safe, having
  checked only one of two relevant functions. The regrade's own claim was itself independently
  re-verified against source before being accepted (never taken on the regrade agent's word alone),
  then a new PoC was built to confirm it. This verdict routes to Stage 4.25 to build evidence for the
  newly-found scope before folding it into the report — it is not itself the finished evidence.
- **`needs_more_evidence`** — can't sign off yet, and says exactly why. The filter-chain regrade above
  didn't stop at "confirmed with correction" — it also requested one additional, specific empirical
  test (an outbound-filter-skip amplifier check) before treating the finding as report-ready. This is
  not a kill. It's a bounce-back to Stage 4/4.25 with a *named* next step, not a vague "needs more
  work" or a full redo.
- **`refuted`** — independent re-derivation from primary sources contradicts the original claim.
  Default-to-disbelief applies here exactly as it does in `adjudication-oracle.md`: a strong-looking
  finding can still end here if re-derivation doesn't hold up.
- **`blocked`** — the reviewer genuinely couldn't independently re-derive the claim (no clean build,
  environment/artifact unavailable) — not a judgment on the finding either way. Included for symmetry
  with pocinator's own `blocked` verdict; no real instance of this specific outcome has occurred yet
  in this harness's practice, unlike the other five, which are each grounded in an actual pass.

## 4. What "re-derive from primary sources, trust nothing" actually means

Not a slogan — a specific, repeated set of moves across every real regrade pass:

- **Re-run the actual test or build yourself.** Don't trust a summary of what a test suite showed;
  run it, in a fresh environment, and read the real output.
- **Grep the real, shipped codebase for whether the claimed pattern is actually live**, not just
  whether the vulnerable code exists in principle. A sink existing in source doesn't mean anything
  ships a caller that reaches it — the filter-chain regrade's severity downgrade came directly from
  checking this rather than assuming it.
- **Check whether the original investigation's own negative control still holds** under independent
  re-derivation — a control that was correct once can still have been mis-described.
- **Trace claims one level deeper than the original pass stopped**, not just re-confirm what it
  already checked. The prototype-pollution severity revision came from tracing *further* into the
  code path than the original investigation had, not from re-checking the same ground.
- **Be willing to hand back a named action item instead of forcing a premature verdict.** `confirmed`
  or `refuted` are not the only honest outcomes — `needs_more_evidence` with a specific next step is
  a legitimate, and observed, regrade result.
- **When a regrade claim itself is surprising (an escalation, a correction), re-verify it against
  source before accepting it** — regrade output isn't automatically trusted any more than the
  original finding was; the escalation-found symlink case had its own regrade claim checked before it
  was acted on.

## 5. Scope boundary: not the CVSS-precedent-reviewer pattern

Regrade is not the same thing as spawning a narrow, fresh reviewer to research disclosed-CVE
precedent for a single contested CVSS metric when a report's severity hinges on it.
`skills/reporting/hackerone-reports.md` already draws this line in its own words: that kind of pass
is *"distinct from a regrade of the finding's validity."* Keep it that way — regrade re-litigates
whether the finding is real and what it actually proves; a CVSS-precedent reviewer is a narrower,
later, severity-methodology-only pass that doesn't need regrade's full primary-source
re-derivation scope, and folding one into the other would blur a boundary the reporting skill already
states cleanly.

## 6. Model tier

The verdict call — deciding whether a correction, an escalation, a bounce-back, or a refutation is
warranted — is a judgment task, and belongs on the planning/reasoning tier, same reasoning as
`engine/pocinator.md`'s own model-tier section. The mechanical legwork underneath it (running a
build, executing a test suite, grepping a codebase for live call sites) doesn't need the expensive
tier to execute — it can be Helper-tier work that feeds the planning-tier verdict, per the
Orchestrator/Hunter/Helper split (`CLAUDE.md` §2). `engine/roster.md` doesn't currently assign
regrade a tier at all; this doc self-declares one, the same way `pocinator.md` had to.

## 7. Decision-0005 record output

A regrade emits a committed `review` record (`review_type: regrade`) and then a
`review.regrade_completed` event. The record binds the exact finding revision and claim-tuple hash,
immutable input-set hash, applicable controls, replay freshness, prior reviewer-run IDs, and the
fresh-context/disconfirming objective. The event changes no claim state. `escalation_found` creates an
outstanding evidence route; a `reviewer_challenge` hypothesis must collect evidence before any later
finding revision may claim the escalation. `confirmed_with_correction` routes to a contiguous operator-
filed revision. External tools or the regrade model cannot file or self-adjudicate a finding.

## 8. On "GPT regrade"

Every real regrade pass in this harness's history uses a generic `"actor": "independent-regrade-agent"`
label — never a model name. `engine/roster.md` names concrete model tiers for its three defined roles;
regrade has never plugged into that language in practice. If "GPT regrade" has been used informally to
mean "run it on a different vendor's model specifically," that's not attested anywhere in this
harness's actual record, and this doc doesn't encode it as a requirement — the property that's
actually load-bearing, unanimously, in every real instance, is fresh context and zero prior
investment (§2), not which vendor produced the model. Cross-vendor is a reasonable decorrelation
booster to reach for when convenient, not a substitute for §2's non-negotiable property, and not a
requirement on its own.
