# engine/pocinator.md — does this specific PoC actually prove the exact claim?

> Pairs with `engine/whitebox-analysis.md` §4 ("verification epistemics — mechanical checks are
> necessary, not sufficient") and `skills/oracles/adjudication-oracle.md` (the live-signal analog of
> the same discipline). Sits at the very end of the pipeline: `Post: triage, regrade, **pocinator**,
> filing`. This is the first "Post:" stage to get formalized — `regrade`, `triage`, and `filing`
> still have no dedicated doc; this one exists because pocinator's judgment shape recurred enough
> real times this session (six independent passes across two engagements) to be worth writing down
> instead of re-deriving from scratch each time.

## 0. The one distinction that matters

> Regrade asks: "Is the finding real?"
> Pocinator asks: "Does this specific PoC/package actually prove the exact claim we're about to
> report?"

These are not redundant passes over the same question. A finding can be real and its PoC can still
be broken, reward-hacked, or overclaiming — proving something narrower, or something else entirely,
or nothing at all. Only pocinator is scoped to catch that. Skipping it because "regrade already said
this is real" is a category error: regrade validated the *finding*, not the *artifact* that's about
to ship as evidence for it.

## 1. Where it sits

```
... -> Stage 4 finding confirmation -> Stage 4.25 post-confirmation verification -> ...
    -> /goal advisory generation -> Post: triage -> regrade -> pocinator -> filing
                                              ^                    |
                                              +---- non-`verified` verdict routes back to
                                                     Stage 4/4.25, never a silent kill (§6)
```

## 2. Why this is lenses, not rules

A PoC's specifics are entirely engagement-dependent — a SQLi PoC, a JVM filter-chain-bypass PoC, and
an LLM prompt-injection PoC need genuinely different concrete checks. A fixed checklist would either
be too narrow (miss real gaps outside the domains it was written for) or too generic to catch
anything. This is the exact same argument `engine/whitebox-analysis.md` §2 makes about static rules
not scaling to an arbitrary binary or codebase, one level downstream: **rules don't scale to an
arbitrary PoC either.** What stays stable across every domain is the *shape* of the judgment — a set
of interrogation lenses (§5) applied with discretion by a capable, skeptical reviewer — not the
specific check any one of them resolves to.

## 3. Why this stage exists — external grounding

Two external, empirical findings are load-bearing enough to embed here — both independently
re-fetched and confirmed before being written down, not taken on citation alone:

- **PoC-Gym** (arXiv 2602.04165) formally defines a valid PoC as exit-code 0 **AND** a vulnerability
  marker in output **AND** the execution trace reaching the real vulnerable sink (`SinkHit`) — a
  real, sink-instrumented, not-naive automated check. On manual inspection, most PoCs that had
  already passed those automated checks turned out invalid on closer inspection anyway. (Two
  independent re-fetches of this paper gave slightly different framings of exactly which population
  the specific percentages apply to — manual inspection of automated-pass PoCs vs. a separate
  AspectJ-based ground-truth trace comparison — so the exact numbers aren't repeated here as a
  precise, singular statistic. What both fetches agree on, and what's worth enshrining, is the
  mechanism.) The paper documents cases where the sink location **technically executed via
  simulation, hardcoding, or incomplete validation** — satisfying the technical requirement without
  the vulnerability ever actually being triggered. That is a stronger argument for this stage's
  existence than "don't trust exit-code-and-a-marker": it's "don't trust a more sophisticated
  automated check either, without independent judgment."
- **SpecBench** (arXiv 2605.21384): every frontier agent saturates its own visible test suite while
  reward hacking persists; the gap between visible-tests-passing and actual spec compliance grows
  **~27-28 percentage points per 10x increase in code size** (21pp worst-case under 10K LOC, 100pp
  over 25K LOC). This lands directly on this harness's own practice: the operator's own worked
  example (an 8-day, tens-of-thousands-of-line exploit, `engine/whitebox-analysis.md` §5) sits
  exactly in the size regime this paper shows is worst for silent reward hacking. Pocinator matters
  most precisely where this harness already does its most ambitious work, not least.

## 4. The claim tuple — the precondition for review

Before pocinator reviews anything, the candidate PoC/finding must have an explicit, extractable
tuple:

**target artifact/version · entrypoint · preconditions · mechanism · observable effect · negative
control · claimed impact/severity · package contents · run command/environment · expected observable
output**

Pocinator's entire job reduces to: does the PoC actually prove this exact tuple, no more and no
less. The last two fields exist to make the tuple *reproducible* by the reviewer, not just
conceptually complete — without an explicit run command and expected output, pocinator has to
reverse-engineer how to even execute the PoC before it can review anything.

The tuple is a **precondition**, not something pocinator constructs for the candidate — it arrives
from Stage 4 and `engine/regrade.md`, which should have settled it as part of reaching
`confirmed`/`confirmed_with_correction`/`escalation_found`. If it can't be extracted from the existing
finding/evidence records, that's itself a `blocked` verdict (§6), not something pocinator invents on
the candidate's behalf. Letting the reviewer write its own tuple would grade its own homework.

## 5. The interrogation lenses

Not a checklist to tick top to bottom — a set of lenses a reviewer applies with judgment, weighted
by what's actually relevant to this specific PoC. Each has a real worked example from this
engagement's own passes, not an invented one.

1. **Real-artifact provenance** — the actual, unmodified, published artifact/pinned commit, not a
   reimplementation or hand-edited copy. (Zuul: `build.gradle` resolving to the real Maven Central
   `zuul-core:3.6.20`, confirmed via the resolved jar in `~/.gradle/caches`, not just trusting the
   file said so.)
2. **Public-entrypoint realism** — drive the target the way a real caller actually would, not a
   shortcut only a test harness could take.
3. **Mock/stub justification** — every mock must be provably non-load-bearing for the claimed bypass:
   *if this were the real code instead of a mock, would the assertion still hold, or does the mock
   exist precisely to dodge the real gate?* (Zuul: confirming `SpyOriginEndpoint` genuinely extends
   the real `Endpoint` base class rather than reimplementing its typing.)
4. **Mechanism fidelity via the negative control** — the control must diverge *through the claimed
   mechanism specifically*, traced, not just observed to produce a different result.
5. **Observable effect, not a blind success marker** — grounded directly in §3: even a
   sink-instrumented automated check isn't sufficient without independent judgment, so a bare
   `exit 0` / printed-marker / boolean flag is nowhere close. (Symlink PoC: `readFile().includes()`
   alone couldn't distinguish a real dereferenced copy from `readFile` transparently following a
   still-live symlink — fixed with an `lstat()` check plus a delete-source-then-reread test.)
6. **Claim strength — exact match between assertion and report language, for any part of the claim
   that's PoC-dependent.** This is where `claim_mismatch` (§6) comes from: not "is the PoC real" but
   "does it prove the *specific* claim it's being used as evidence for." (Zuul: the PoC proved
   confidentiality/response-disclosure cleanly; it did not prove an integrity/write impact, so the
   report needed to say exactly that, not the worst case the mechanism could theoretically reach.)
   **Scope note:** this lens covers whether PoC *evidence* supports a PoC-dependent claim. It is not
   pocinator's job to own broader CVSS methodology or precedent research (e.g. Scope-metric
   convention-matching against comparable disclosed CVEs) — that's the narrow, separate
   CVSS-precedent-reviewer pattern (`skills/reporting/hackerone-reports.md`), not pocinator's, and
   not a full `engine/regrade.md` re-litigation either (see `engine/regrade.md` §5).
7. **Clean-state reproducibility** — fresh checkout/extraction/container where reasonable, never just
   "it worked in the dev sandbox with whatever state was already lying around."
8. **Anomaly tracing** — a stray log line, warning, or stack trace in an otherwise-passing run gets
   explained by tracing it to source (decompile if needed), never hand-waved as benign. (Zuul:
   decompiling the real `zuul-core-3.6.20-sources.jar` to confirm a mid-test NPE was unrelated harness
   noise firing strictly after the skip decision, not something invalidating the result.)
9. **Package hygiene** — no secrets, no internal JSON/scratch files, no stale build dirs, no
   harness-internal records leaking into what would ship as evidence. Review the artifact that would
   actually ship (a fresh re-extraction of the packaged zip), not the working directory it was built
   in — the two can drift apart mid-edit. (Validated this session via `diff -r` confirming a packaged
   zip byte-identical to its source folder before treating it as final.)
10. **Self-attestation is not evidence** — a PoC's own README/comments and the finding record's own
    prior verdict get independently re-derived, not trusted, ideally by a different context than
    whoever built the PoC (this lens borrows its no-prior-context posture directly from
    `engine/regrade.md` §2, which treats it as a non-negotiable rather than an "ideally").
11. **Optional differential, when available** — a patched version, fixed config, or otherwise
    known-safe control strengthens confidence but isn't required to reach `verified`. Not every
    finding has one to exercise — a filter-chain-bypass PoC generally won't, while a dependency-CVE
    lead generally will (e.g. checking a pinned library version against disclosed-CVE-fixed ranges).
    Don't force this lens where the finding shape doesn't offer it.
12. **Counterfactual-novice framing** (from a sensemaking-in-security-assessment study of expert
    bug-bounty hunters/consultants/CTF players) — prompt explicitly as *"where would a naive or
    reward-hacked verification stop and declare success here?"* rather than only "is this faithful?"
    — the sharper of the two framings per that study's own strongest empirical result on what
    actually discriminates expert judgment from novice judgment in practice.

## 6. Verdicts and routing

`verified` · `needs_rework` · `claim_mismatch` · `reward_hacked` · `blocked`

- **`verified`** — the PoC proves the exact claim tuple, including any PoC-dependent impact/severity
  claim (not broader CVSS/novelty precedent — lens 6's scope note).
- **`needs_rework`** — probably real, but a specific, named, fixable gap exists (weak assertion,
  missing negative control, unclean reproduction state). Also the honest verdict when it's *unclear*
  whether something rises to `reward_hacked` — see below.
- **`claim_mismatch`** — the PoC is real and sound, but proves something narrower or different than
  the report currently claims (the Zuul CVSS Integrity-vs-confidentiality case, exactly).
- **`reward_hacked`** — reserved for a *definite, articulable* harness failure: a named mock that
  dodges the real gate, a traced emulator divergence from real control flow, an assertion that
  structurally cannot fail. **Not a hedge for uncertainty.** If the reviewer isn't sure whether
  something rises to this level, the honest verdict is `needs_rework` or `blocked`, not a
  hedge-labeled `reward_hacked` — collapsing "definite harness failure" and "I'm not sure" into one
  verdict blurs the taxonomy exactly where it needs to be sharpest.
- **`blocked`** — the reviewer genuinely cannot decide (environment/artifact unavailable, claim tuple
  not extractable from existing records) — not a judgment on the PoC's soundness either way.

**Any non-`verified` verdict routes back to Stage 4/4.25, never a silent kill or automatic
withdrawal** — exactly like a regular confirmation failure. `claim_mismatch` specifically routes to
severity/impact reasoning (report-writing + CVSS re-derivation), not to rebuilding the PoC — the PoC
may already be fine, just proving a narrower thing than currently claimed.

Any *definite* `reward_hacked` verdict on a high-value/high-stakes finding earns a second independent
pocinator pass before being treated as final, since it's effectively a kill. Pocinator doesn't get an
exemption from `engine/whitebox-analysis.md` §3's "never let one pass kill" rule just because it runs
late in the pipeline.

## 7. When required vs. skippable

Required by default for:
- any executable PoC/zip that will be attached to a report,
- any high/critical candidate,
- any model-built harness/emulator standing in for the real target,
- any finding whose severity claim depends on what the PoC specifically demonstrates.

Skippable only with an explicit, short operator note recorded in the finding (e.g. "source-only
issue, no executable PoC, mechanism unambiguous from code alone") — never a silent skip.

## 8. Decision-0005 record output

Pocinator emits a committed `review` record (`review_type: pocinator`) and a
`review.pocinator_completed` event bound to the exact finding revision, structured claim-tuple hash,
proof-profile artifact, immutable input-set hash, prior reviewer runs, and end-to-end composition
status. The event changes proof-review routing only—never finding truth. `claim_mismatch` routes claim
and report correction; it does not refute a real mechanism. `verified` cannot be emitted from a
module-only proof in place of end-to-end composition. A definite high-value `reward_hacked` remains
`pending_second_review` until a second distinct fresh reviewer agrees. Non-verified outcomes route
back with named actions.

## 9. Model tier — judgment stays high-tier, legwork doesn't have to

The actual verdict call (lens interrogation, deciding whether a mock dodges the real gate, assigning
the final verdict) is a judgment task catching subtle self-deception, and belongs on the
planning/reasoning tier per `engine/whitebox-analysis.md` §5's Opus-plan/Codex-grunt split — not
delegated wholesale to a faster/cheaper model. But this maps cleanly onto the harness's existing
three-tier role split (`CLAUDE.md` §2: Orchestrator/Hunter/Helper): the *mechanical* legwork a
pocinator pass needs — fresh extraction, running the build, `diff -r` against a source folder,
collecting/grepping logs, listing zip contents — is exactly Helper-tier work (offline, no target
contact, no judgment required) that can feed the planning-tier verdict rather than being redone by
the expensive model itself. This session's own real pocinator passes already worked this way
informally; naming the split explicitly here just makes it repeatable.

## 10. What pocinator does not decide

A casebook lesson (`case-2026-07-oss-supply-chain-tooling`) already documents this concretely:
passing pocinator does not guarantee a report won't come back as a HackerOne duplicate. Pocinator
verifies the PoC is real and faithful to its claim; it does not and cannot verify novelty or prior
disclosure — a different question, owned upstream of this stage.
