---
id: regrade-oracle
type: oracle
description: Post-confirmation layer — is this finding actually real? (fresh-context, no-prior-investment re-derivation)
---

# Regrade oracle — "is this finding actually real?"

Runs before pocinator in `Post: triage, regrade, pocinator, filing`. Regrade re-litigates the finding
itself (mechanism, escalation completeness, severity, claim accuracy); pocinator separately asks
whether a specific PoC proves the claim regrade settles. Full doctrine and worked examples:
`engine/regrade.md`. This card is the terse, invocable version for an agent loading it by id.

## The one non-negotiable precondition
Run this in a fresh context with **zero prior investment** in the original finding. Not a preference —
if you are the agent (or a continuation of the session) that produced the original finding, you cannot
run this oracle; hand off to a genuinely fresh context first. This property has no exceptions in this
harness's practice.

## Verdict set
`confirmed` · `confirmed_with_correction` · `escalation_found` · `needs_more_evidence` · `refuted` ·
`blocked`

- **`confirmed`** — mechanism, reachability, and claimed impact hold exactly as stated, independently
  re-derived.
- **`confirmed_with_correction`** — real, but scope/severity/impact framing needs correcting (e.g. a
  claimed pattern doesn't actually ship in any live caller — cap severity to what's actually
  reachable, not what's theoretically possible).
- **`escalation_found`** — you found additional impact/reach the original pass missed. Re-verify your
  own escalation claim against source before accepting it — don't let this verdict become the thing
  that needed a regrade itself. Routes to Stage 4.25 to build evidence for the new scope.
- **`needs_more_evidence`** — can't sign off yet; name one specific, concrete next empirical step.
  Not a kill, a bounce-back with an action item.
- **`refuted`** — independent re-derivation contradicts the original claim. Default to disbelief; a
  strong-looking finding can still end here.
- **`blocked`** — genuinely couldn't independently re-derive (no clean build, artifact/environment
  unavailable) — not a judgment on the finding either way.

Anything other than `confirmed`/`confirmed_with_correction`/`escalation_found` routes back to Stage
4/4.25 — pocinator does not run on a finding regrade hasn't cleared.

## What "trust nothing, re-derive from primary sources" means in practice
- Re-run the actual test/build yourself, in a fresh environment — don't trust a summary.
- Grep the real shipped codebase for whether the claimed pattern is actually *live*, not just whether
  the vulnerable code exists in principle.
- Re-check the original investigation's own negative control under your own re-derivation.
- Trace one level deeper than the original pass stopped — don't just re-confirm what it already
  checked.
- A named `needs_more_evidence` action item is a legitimate outcome — don't force `confirmed` or
  `refuted` when the honest answer is "one more specific test settles this."

## What this oracle is NOT for
Not a CVSS-metric-precedent research pass — if a report's severity hinges on a single contested CVSS
metric and needs disclosed-CVE precedent research, that's a separate, narrower, later reviewer pattern
(`skills/reporting/hackerone-reports.md`), not a full regrade re-litigation of the finding.

## Naming note
Regrade in this harness has no vendor requirement — every real instance uses a generic
`independent-regrade-agent` label, never a model name. What's non-negotiable is fresh context and zero
prior investment, not which vendor produced the model. Treat cross-vendor as an optional decorrelation
booster, not a substitute for a genuinely fresh context.
