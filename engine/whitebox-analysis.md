# engine/whitebox-analysis.md — source-available candidate hunting, grading, and anti-reward-hacking verification

> When this applies: **white-box / gray-box** engagements — source code available, target is a
> codebase to audit (an OSS project, a customer's repo) rather than a live black-box surface to
> probe with a browser. Complements `engine/persistence.md` (evidence-licensed exhaustion) and
> `engine/loop.md` (the ladder) — same rigor bar, same gates, adapted to a different attack surface:
> a corpus of source, not a running app. Distilled from the operator's own RE/exploit-dev practice
> ("adopt that stages methodology").

## 0. The mode shift from black-box

Black-box mode establishes a session and drives a live target (`AGENTS.md §2`: orchestrator plans,
Hunter drives). White-box/gray-box mode usually has **no live target to session into at all** — for
programs like Vercel's OSS bounty, testing against production is explicitly forbidden; the work is
standing up the project locally (or in an isolated repro environment) and auditing the source, then
building and running a PoC against *that* local instance. Recon is reading code, not snapshotting a
browser session. The oracle is still two-layer (signal → adjudication), but the signal is now
"the harness/PoC hit the sink and produced the predicted effect," and the adjudication question is
sharper here than anywhere else in this harness: **is that harness faithful to the real program?**
(§3 below.)

## 1. The staged funnel (candidate → confirmed → advisory)

```
corpus
  -> Stage 0    candidate sink-function narrowing
  -> Stage 1    primitive vocabulary / cheap classifier pass
  -> Stage 2    source/sink/path triples
  -> Stage 3    cross-function reachability
  -> Stage 3.5  chain construction / reachable-triple promotion
  -> Stage 4    finding confirmation
  -> Stage 4.25 post-confirmation verification and classification
  -> Stage 5    chainability
  -> Stage 5.25 novelty + paper-review sub-passes
  -> Stage 5.5  reachability dossier enrichment
  -> /goal      advisory generation
  -> Post       triage, regrade, pocinator, filing
```

This is the same shape as `staged-analysis-pipeline` (memory) and `engine/persistence.md`'s funnel,
specialized with source-analysis-specific stage names. **The operator's own framing matters more
than the stage list**: *"stage names show the development progression if anything."* Read literally:

- The numbers are not a protocol to execute top-to-bottom once. They are **where the rigor gates
  sit** (same as `engine/persistence.md` §"the funnel"). A candidate can — and routinely should —
  jump back to Stage 0 (re-narrow, the corpus wasn't fully covered), Stage 2 (the triple was
  mis-shaped), or Stage 1 (the classifier's vocabulary missed a variant), from any later stage.
- The real operating model is: **"LLM grading from top to bottom" + harness rules + human
  double-checking**, where **grading agents manage the pipeline themselves** and don't stop until
  the corpus is exhausted — not a human manually walking a checklist stage by stage. This is a
  natural fit for the `Workflow` tool's `pipeline()`/`parallel()`/loop-until-dry primitives: a finder
  stage feeding a grading panel feeding a verification stage, self-driven, with the operator setting
  the target ("exhaust this corpus") rather than sequencing every step.

**Where the GHSA fix-diff oracle plugs in.** `oracles.ghsa-fix-diff`
(`skills/oracles/ghsa-fix-diff-oracle.md`) supplies real disclosed fix-commit priors to two points in
this funnel: the *removed-line* (vulnerable pre-patch) shape is a Stage-0/Stage-1 candidate-sink
signature, and the pre/post-patch snapshot is the Stage-5.25 novelty discriminator —
patched-historical vs genuine-new-instance vs regression, which a version-string check alone misses
(the ~$6.4M Astroport-on-Terra fix-regression is the canonical miss). Priors and taxonomy only: a
target matching a removed-line shape is a Stage-0 lead to drive through the funnel, never a Stage-4
confirmation, and a matching added-guard is a strong-but-not-absolute held signal that still owes
Stage-3 reachability.

## 2. Why rules alone don't scale to an arbitrary binary/codebase

A rule (regex sink list, taint-rule set, static-analysis query) is a cheap, useful **Stage 1
classifier** — it is not a substitute for judgment at any stage past that. Concretely:

- Rules **misclassify**: a sink-shaped call that isn't actually a sink in context, or vice versa.
- Rules **miss what an LLM would catch**: a variant form, an indirect call, a renamed wrapper, a
  language idiom the rule's author didn't anticipate.
- Rules **overmatch**: broad patterns generate a firehose of candidates with no signal on which
  matter (the classic false-positive flood from any sink-list-driven static scan).
- Rules tuned **against one specific, known binary** work reasonably — you can hand-fit them once you
  know the shape of that program. Rules aimed at **an arbitrary/unfamiliar binary** have no such
  tuning and should not be trusted to carry the classification burden alone.

**Consequence for this harness:** treat static rules as a cheap Stage-1 pre-filter that *narrows*,
never as the thing that *decides*. An LLM classification pass sits downstream of the rule, not
instead of it, and is the thing actually trusted to say yes/no on a candidate — because every
unfamiliar target is effectively a black box to a hand-written rule, even when the source is fully
visible.

## 3. The real hard problem: filtering 9,999 false positives without losing the 1 real one

Finding candidates is comparatively cheap — over-generation costs little (cast Stage 0/1 wide).
**The hard, valuable work in LLM red-teaming is filtering the false candidates down without
discarding the one real one along the way.** This reframes the whole pipeline's purpose: it is not
"find the bug," it is "don't let anything kill the bug before it's proven."

This is an **asymmetric-cost problem**, not a precision/recall balancing act to optimize evenly:

- A false negative (a real candidate wrongly killed at any stage) can cost a critical/high-severity
  bounty outright — for this program, Tier 1 critical is $5,250–$10,000+, with exceptional-impact
  bonuses on top. That is the number that a premature "dry" or "not a sink" call is actually risking.
- A false positive that survives one extra grading round costs a few dollars of model time.

Given that asymmetry, this harness's rule for white-box grading is:

> **Multiple independent rounds of LLM + human grading before killing any candidate.** No single
> classification pass — one rule, one model call, one workflow stage — is ever sufficient grounds to
> discard a candidate. Bias every grading round toward "keep if uncertain," not toward "kill unless
> proven." Only a *converged, multi-round, cross-checked* verdict retires a candidate.

Practically: run the "kill or keep" decision as a **panel**, not a single judge — several
independent graders (varied prompts/lenses, not just N identical votes) evaluate a candidate for
survival, and killing requires their agreement, mirroring the adversarial-verify pattern in
`Workflow` but **inverted in bias**: adversarial-verify (used to confirm a *finding*) is biased
toward refuting a weak claim; this grading panel (used to *not lose* a candidate) is biased toward
keeping an uncertain one alive for another round. Log every kill with the reasoning, so a human can
audit *why* a candidate was dropped, same as `AGENTS.md §4` step 3's override-log requirement for a
strong signal not pursued.

## 4. Verification epistemics — mechanical checks are necessary, not sufficient

"Did the breakpoint hit? Did the stack corrupt? Did the file get written?" — these are real,
checkable facts, and a harness should check them mechanically wherever possible (that is the
signal-oracle layer, `AGENTS.md §0`/`skills/oracles/`). But three problems sit upstream and
downstream of that check, and none of them are mechanical:

1. **What to verify is itself a judgment call.** Given 9,999 candidates, choosing which handful earn
   expensive dynamic verification is a **pre-confirmation triage decision** — distinct from the
   `Post:` pipeline's own triage stage, which sorts already-confirmed, advisory-ready findings for
   reporting order, not candidates for verification budget — not something a rule can make for you
   (§2, §3). Get this wrong and you either burn all your verification budget on noise or never reach
   the one candidate that mattered.
2. **A model's attention doesn't scale to a 6,000-line exploit.** A single model call cannot hold a
   full, faithful mental model of a large, real-world exploit chain — it will lose track of a
   precondition, a version-specific detail, or a control-flow branch somewhere in there. This is an
   argument for **decomposition and long-horizon iteration** (§5), not for trusting a single-pass
   "I read the exploit, it looks right" judgment.
3. **Verification itself can be reward-hacked, including by accident.** A model can build a sink
   harness or emulator that "proves" a candidate is reachable — while silently failing to replicate
   the real program's control flow, environment, or invariants. The harness runs, the assertion
   passes, the model reports `confirmed` — and none of it reproduces on the actual target, because
   the emulator diverged from reality somewhere the model didn't notice or didn't check. **This is
   the single most expensive failure mode in this whole methodology**: it is exactly what turns into
   a wasted report that gets closed as not-reproducible, burns researcher credibility with the
   program, and (per this program's own policy) is explicitly what triggers deprioritization —
   *"Do not submit an AI-generated report without first reviewing and confirming real impact and
   verifying a working Proof-of-Concept."*

**Consequence:** add an explicit gate that does not exist in the black-box loop — **verification-of-
the-verification**. Before a Stage 4 "confirmed" is trusted, a separate pass (ideally a different
model/context than the one that built the harness) must answer, specifically: *does this harness
faithfully replicate the real binary's control flow / environment / invariants, or did it only prove
something about a simplified stand-in?* Where feasible, the confirming PoC should run against the
**real, unmodified target build** (the actual stable release, per the program's version-eligibility
rule), not solely against a hand-built emulator — the emulator is a tool to *find* the path, not the
final proof that it's real. This is the white-box analog of `engine/loop.md`'s "signal oracle vs.
adjudication oracle" split, sharpened: the signal oracle here can be self-deceived by construction,
so the adjudication pass must interrogate the harness's fidelity, not just its output.

## 5. Model role division (learned this session, generalizes across white-box engagements)

Different models have different comparative advantage in this pipeline — assign roles to match, on
top of `AGENTS.md §2`'s Orchestrator/Hunter/Helper split:

- **Orchestrator / triage tier (e.g. Opus).** Planning, triaging candidates, authoring and debugging
  the pipeline/harness code itself, deciding what gets escalated to deep verification. High judgment,
  broad context, but not the role for marathon low-level grinding — left alone on an extremely long,
  tedious, iterative exploit-construction task, this tier is more likely to conclude "not feasible"
  and stop early.
- **Hunter / grunt-execution tier (e.g. Codex).** The actual long-horizon exploit engineering:
  iterating a harness, fixing a crash, re-deriving an offset, rebuilding a PoC — for as long as it
  takes. The operator's own worked example: an exploit that took **eight days of continuous
  iteration** and grew to **tens of thousands of lines** (not bloat — required complexity), produced
  by explicitly invoking persistence framing rather than accepting an early "not feasible": *"it's
  possible, if you give up you're not trying hard enough."* This is `evidence-licensed-persistence`
  (memory) at exploit-development timescale — days and tens of thousands of lines, not a single
  session's worth of probing — and it is the sharpest evidence yet for why persistence framing has
  to be *explicitly and repeatedly invoked* for the grunt-execution tier: left to its own judgment, it
  will call "infeasible" well before the budget the operator is actually willing to spend.
- **Helper tier**, unchanged from `AGENTS.md §2`: cheap, offline-only mechanical work (diffing,
  dedup, log scraping) — never the tier trusted with a kill/keep or confirm/refute verdict.

Put simply: **the planning/triage tier decides what's worth pursuing and builds the harness; the
grunt-execution tier is the one licensed, explicitly and repeatedly, to not give up.** Don't invert
this — asking the planning tier to grind for days is a waste of its comparative advantage, and
letting the grunt-execution tier self-select what's "worth" pursuing skips the judgment step it's not
suited for.

## 6. Relationship to `engine/persistence.md`

Same core inversion (a held vector is a wrong turn, not a stop sign), same "bound the space so dry is
real," same counterweight against tunnel vision — this doc doesn't replace any of that, it specializes
it for source-available work and adds what black-box mode doesn't need:

- The unit of persistence is a **candidate sink surviving a grading panel**, not a live-target lead.
- The timescale can be **days**, not minutes-to-hours, once a candidate reaches deep exploit-dev.
- Verification carries its own reward-hacking risk that a live oracle mostly doesn't (a live target's
  response is real by construction; a self-built harness's "pass" is not).
- Rules are explicitly demoted to Stage-1 pre-filters (§2) — the black-box harness's `skills/vulns/*`
  cards remain useful as **classification vocabulary** (what does an OS-command-injection sink,
  a path-traversal sink, an SSRF sink look like in source), but the LLM grading panel is what actually
  decides survival, not the card's pattern list alone.

## 7. Practical fit with this repo's tools

- `Workflow`'s `pipeline()`/`parallel()` are close to a literal implementation of Stage 0–3.5:
  narrow → cheap-classify → triples → reachability, each stage feeding the next without a barrier
  except where a genuine cross-candidate dedup is needed (e.g. before expensive Stage 4 confirmation,
  dedupe candidates that resolve to the same underlying sink).
- The "keep-biased grading panel" (§3) is the adversarial-verify pattern with the bias flipped —
  same mechanism (N independent graders, require agreement to act), opposite default.
- `engine/gates.md`/`AGENTS.md §1` still govern: no PoC construction against a program's production
  systems (doubly true here — this program forbids it outright), Zone-2 confirmation still needed
  before any artifact with real capability is built, even in a local repro environment.
