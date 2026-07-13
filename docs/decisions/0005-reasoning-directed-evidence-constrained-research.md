# Decision 0005 — Reasoning-directed, evidence-constrained research

**Status:** accepted as product direction; implementation is incremental\
**Date:** 2026-07-09\
**Effect:** extends Decisions 0001 and 0004; supersedes neither. Decision 0004 remains the canonical
policy for epistemic autonomy and complexity. This decision applies that policy to live research,
engagement state, persistence, findings, memory, and calibration.\
**Related:** `AGENTS.md`, `docs/architecture.md`, `engine/loop.md`, `engine/routing.md`,
`engine/persistence.md`, `engine/regrade.md`, `engine/pocinator.md`, `schemas/attempt.schema.json`,
`schemas/finding.schema.json`

## Context

Engagement records contain substantive locally reproduced mechanisms and useful refutations across
web applications, open-source frameworks, supply-chain tooling, and blockchain/source-audit work. This
does not mean every report has external validation, but it does show that the method's useful behavior
is not limited to LLM-specific vulnerabilities. Field history also shows why the method works:

- a model may confirm a primitive and stop before finding its higher-impact composition;
- an operator may sense from experience that the observed result does not explain the violated
  invariant and direct the model to persist;
- a fresh regrade may revive a path the first pass wrongly killed;
- a regrade may also narrow an overstated deployment assumption or impact claim;
- Pocinator may find that a real vulnerability has a weak, mismatched, or reward-hacked proof package;
- a thorough search may legitimately end negative after controls and bounded coverage hold.

The product tension is therefore not “rules versus intelligence.” It is where each belongs.

LLMs have broad, transferable semantic ability. They can form hypotheses, understand unfamiliar code,
construct experiments, debug, reframe, backtrack, and compose primitives across domains. Those are
open-world research tasks that fixed rules cannot generally solve. LLM execution is also
non-deterministic and context-sensitive: independent runs can choose different hypotheses, converge
prematurely, inherit framing errors, lose operational state, or satisfy a visible success condition
without proving the intended claim. More prompting does not turn model judgment into ground truth.

The harness must preserve the upside without making the model either a scripted scanner or an
unreviewed authority. It should act as a cognitive exoskeleton: give capable researchers and models
better handles for attention, persistence, evidence, memory, and review while leaving the actual
security reasoning alive.

The current implementation already contains parts of this direction in routing, persistence,
append-only attempts, two-layer adjudication, regrade, Pocinator, casebooks, and manual pattern
promotion. It does not yet implement the full state, coverage, domain-neutral finding, environment, or
calibration contracts below. This decision records the intended product shape; it is not a claim that
all of it already exists or has demonstrated efficacy.

## Decision

### 1. Product identity: a high-agency research system inside a hard evidence shell

The harness is a **domain-neutral, recursively staged, reasoning-directed research system inside a
small, hard safety-and-evidence shell**.

Its stable posture is:

> Mechanize authority, state, provenance, controls, and evidence obligations. Preserve model and
> operator freedom over hypotheses, semantic analysis, experimentation, debugging, backtracking, and
> composition.

The harness is not only an LLM-vulnerability harness. LLM application security is one domain pack
among web, API, source audit, binary, supply-chain, blockchain, consensus, and future domains.

The following boundary governs additions:

| Surface | Product posture |
| --- | --- |
| Scope, authorization, escalation, target identity, artifact provenance, append-only evidence, required controls, cleanup, schema validation, finding/report linkage | Enforce mechanically |
| Hypothesis generation, semantic source/sink analysis, realistic reachability, exploit construction, debugging, chaining, novelty interpretation, backtracking | Keep reasoning-directed and flexible |
| Routing, stage transitions, candidate rejection, severity, coverage/dry, memory promotion recommendations | Use model judgment with structured rationale, evidence references, independent challenge, and human authority where consequential |

A hard shell must not answer an open-world semantic question from a keyword match alone. A capable
model must not override a failed mechanical invariant merely because its narrative is persuasive.

### 2. Stages grade evidence maturity; they do not prescribe cognition

Retain the staged funnel because different questions require different evidence bars:

```text
recon and routing
  → narrow and classify
  → form hypotheses
  → establish reachability
  → confirm a primitive
  → re-verify and classify
  → test composition and chainability
  → review novelty
  → consolidate the evidence dossier
  → generate an advisory
  → triage, cold regrade, Pocinator, operator review, filing
```

This is a graph, not a one-way assembly line. An agent may return to recon, reopen a discarded
candidate, add a hypothesis, split a claim, insert a refinement pass, or route a failed proof back to
reachability. A later stage may strengthen or narrow an earlier claim. Revisiting is expected behavior,
not pipeline failure.

Each stage defines an output contract, not a private reasoning script. A useful stage output contains:

- the current claim or hypothesis;
- supporting and conflicting evidence;
- controls performed;
- unresolved uncertainty;
- a provisional verdict;
- the recommended next route.

Do not require or store private chain-of-thought. Preserve concise decision rationale, tested
hypotheses, observations, falsifiers, and evidence references—the information another reviewer needs
to reproduce or challenge the decision.

Use different biases at different points:

- **Discovery:** maximize recall and preserve plausible high-value leads.
- **Confirmation:** default to disbelief and require faithful evidence.
- **Reporting:** bound every sentence to the demonstrated claim.

A candidate may move quickly when decisive evidence exists. It may not bypass the required controls,
review, or escalation gates.

### 3. Preliminary decisions are necessary, provisional, and reversible

Models must rank, defer, reject, and route candidates to conduct research. Preventing preliminary
judgment would remove useful agency. The invariant is instead:

> Early decisions guide search. Only evidence-backed adjudication creates terminal belief.

A model may say that a branch currently appears unreachable. Permanently closing it requires a named,
decisive falsifier or reviewable coverage rationale. A single model summary is not a decisive
falsifier. Source or runtime evidence can be decisive—for example, the in-scope release lacks the
path, real control flow proves the input cannot reach it, the target policy excludes it, or a held
control removes the required attacker capability.

A high-impact candidate should not be silently killed by one pass. Independent regrade is required
when the kill is consequential, the signal remains strong, or an operator prior remains unresolved.

### 4. Claim state and search state are independent

The harness must not equate “a finding was adjudicated” with “the search is complete.” Track at least
three distinct concerns:

1. **Claim state** — whether a particular mechanism or impact claim is supported.
2. **Search state** — whether a material hypothesis or branch remains open.
3. **Engagement coverage state** — whether the bounded objective space has credible closure.

Conceptually, claim state includes:

```text
hypothesized | supported | confirmed | needs_review | contaminated | refuted
```

Search state includes:

```text
unexplored | active | held | locally_exhausted | deferred
```

Engagement coverage includes at least:

```text
active | blocked | coverage_dry
```

Exact schema names may evolve; the separation may not collapse. A confirmed Low primitive can coexist
with active chainability work and unresolved engagement coverage. A refuted implementation closes only
the conditions tested, not automatically the underlying vulnerability family.

### 5. Operator intuition is a first-class search prior, never proof

Senior operators often detect a security inconsistency before they can fully articulate its mechanism.
The harness must accept this as an explicit **operator prior**. Where possible, record:

- strength (`weak` or `strong`);
- the observation that generated the prior;
- the suspected violated invariant, trust-boundary mismatch, or unexplained impact ceiling;
- the branches or assumptions the operator wants challenged.

Tacit intuition remains valid even when the rationale is incomplete; label it honestly rather than
inventing precision.

An operator prior changes search allocation and stopping conditions. It does **not** increase finding
confidence, replace evidence, authorize escalation, or lower the oracle bar.

The intended persistence instruction is semantically:

> Treat this as a high-confidence search prior, not evidence or a required positive conclusion. Do not
> stop because the current paths failed or produced only low impact. Explore materially different
> explanations and compositions until the bounded hypothesis space has evidence-backed closure. Never
> invent a missing edge, weaken the attacker model, alter the oracle, or substitute an emulator for
> real control flow to satisfy the prior.

This preserves the useful effect of “I know there is something here” without requiring the model to
manufacture a vulnerability.

### 6. Persistence seeks epistemic resolution, not a positive result

Persistence mode is not default fishing. It may activate from evidence or an explicit operator prior:

- a confirmed primitive;
- a strong activation signal;
- a credible unresolved anomaly;
- an operator prior;
- an independent reviewer identifying omitted coverage.

“Exhaust all possible leads” is an intention, not a literal completeness claim. The operative target is
all **material hypotheses** identified from the scoped surfaces, trust boundaries, confirmed
primitives, activation signals, operator priors, unexpected behavior, and newly learned target model.

For each material hypothesis, retain:

- its origin and rationale;
- expected attacker path and possible impact ceiling;
- experiments and controls performed;
- current status;
- decisive falsifier, if any;
- unresolved questions;
- next route.

Persistence alternates zoom-in and zoom-out. Repeating cosmetic variants of one dead path is not
coverage. Failure of one implementation is not failure of the mechanism. A failed chain should cause
backtracking, new recon, or a different composition lens when the prior remains unexplained.

A persistence pass can terminate negatively. Credible closure requires:

1. material branches are tested, deferred with an explicit reason, or closed by decisive evidence;
2. unexpected observations are explained rather than ignored;
3. confirmed primitives receive an explicit composition/chainability review where meaningful;
4. remaining paths require out-of-scope, forbidden, or demonstrably unavailable preconditions;
5. a cold reviewer finds no significant omitted branch on high-value or prior-driven work.

Success is reduction of uncertainty with reproducible evidence. A well-supported negative succeeds; an
artificial Critical fails.

### 7. Routing, event truth, adjudication, and coverage are separate powers

Do not let the component that selected a skill become the sole authority that the selected
vulnerability exists. Preserve these conceptual responsibilities:

| Responsibility | Question |
| --- | --- |
| Router | Which skills and reasoning lenses do current observations activate? |
| Signal grader | Did the expected benign or distinctive signal occur? |
| Evidence authority | What did source inspection, target execution, instrumentation, or the broker actually record? |
| Claim adjudicator | What mechanism, reachability, and impact claims does that evidence justify? |
| Coverage grader | Does the bounded hypothesis space require more work? |
| Regrade | Can a fresh reviewer reconstruct, narrow, reject, or strengthen the finding from primary evidence? |
| Pocinator | Does this specific proof package demonstrate the exact claim it will support? |
| Human operator | Is escalation authorized, is consequential adjudication accepted, and may anything be filed or promoted? |

These are reasoning roles, not a mandate to create one class, service, or agent per row.

An LLM may judge the semantic meaning of evidence. It is not the authority for event truth. Source,
runtime behavior, immutable artifacts, controls, and broker records ground the judgment. External
tools, retrieval systems, scanners, and card matches may produce leads or evidence; they never become
oracles merely by emitting a verdict.

### 8. Proof validity and vulnerability validity remain distinct

For every reportable claim, make the causal spine explicit:

```text
target/version
  → public or realistic entrypoint
  → attacker influence
  → crossed gate or violated invariant
  → real sink or state transition
  → observable effect
  → matched controls and replay
  → bounded impact claim
```

Store structured mechanism, reachability, and impact claims with evidence and control references. A
claim-to-proof matrix should be generated or validated from those records rather than maintained as an
independent narrative truth.

Regrade asks whether the finding is real and correctly bounded. Pocinator asks whether the specific
PoC or package proves the exact claim tuple. Preserve Pocinator's typed distinctions, including fixable
proof gaps, claim mismatch, definite reward hacking, and genuinely blocked review. Do not flatten those
outcomes into a single pass/fail when routing depends on the difference.

Large proofs should be decomposed into independently verified modules, followed by one end-to-end
review of composition. Passing module tests does not prove that the modules form the claimed causal
path. A success marker, sink hit, or passing visible test is necessary evidence in some domains but is
not sufficient by itself.

### 9. Authority is partitioned across records

Do not create one universal mutable “canonical state” file. Authority belongs to the artifact closest
to the fact:

- signed `scope.md` — authorization, surfaces, accounts, objectives, and escalation ceiling;
- append-only attempts and immutable artifacts — observations and event evidence;
- versioned findings with review history — revisable adjudication;
- append-only engagement events — transitions, challenges, reopenings, and dispositions;
- derived state snapshot — deterministic current-state reduction for resumption;
- generated `progress.md` and reports — human-readable views, not independent sources of truth.

Attempts and artifacts are evidence and must not be rewritten to fit later belief. Findings may change
as new evidence arrives, but every revision and reason remains visible. Reports must reference a
structured finding ID and revision. Any issue advancing to advisory, triage, or external report must
have a structured finding; ordinary attempts, refutations, and undeveloped hypotheses do not all
become findings.

Historical narrative-only reports should be backfilled transparently. If their adjudication cannot be
reconstructed, default them to `needs_review`; do not manufacture missing evidence.

External submissions remain operator-owned artifacts and must follow the receiving program's rules.
Where a program forbids AI-authored submissions, the operator must personally re-author the submission;
the harness evidence dossier is input, not the submitted text.

### 10. The research kernel is domain-neutral; domain packs provide semantics

The portable kernel is:

```text
scope
  → system model and recon
  → observations and activation signals
  → hypotheses and experiments
  → evidence and controls
  → claims and findings
  → coverage and review
  → reusable lessons
```

Domain-specific cards or extensions provide:

- vulnerability concepts and terminology;
- source/sink and trust-boundary semantics;
- activation signals and safe signals;
- applicable techniques;
- expected controls and falsifiers;
- domain-specific impact models;
- escalation boundaries and proof requirements.

The core finding contract must not require OWASP-LLM fields for blockchain, consensus, binary,
source-audit, API, or supply-chain findings. Domain extensions may add fields without changing the
kernel's evidence obligations.

Rules, static analysis, grep, call graphs, scanners, decompilers, and instrumentation remain valuable
for candidate generation and objective facts. They propose or support; they do not by themselves
establish realistic reachability, attacker preconditions, impact, or absence of reward hacking.

### 11. Memory promotes transferable reasoning, including negative lessons

Retain three levels:

1. append-only attempts, findings, and artifacts from the engagement;
2. local pattern candidates and sanitized casebook lessons;
3. scrubbed, portable, human-reviewed Plane-1 patterns.

Every completed engagement must record one memory disposition:

```text
promote | defer | no_novel_lesson
```

This is a requirement to decide, not a requirement to promote.

A promotion candidate should state:

- the abstract mechanism or violated invariant;
- activation signals and applicability boundaries;
- expected evidence;
- controls and falsifiers;
- misleading dead ends;
- composition opportunities;
- held counterexamples and contexts where it does not apply;
- evidence provenance without target secrets.

Confirmed findings are not the only source of reusable knowledge. Strong refutations, reward-hacked
proof patterns, recurring environment failures, and productive operator priors may all teach portable
lessons. Finding count alone does not define a good pattern.

Models and oracles may propose promotion. They may not write directly into promoted Plane-1 memory.
Promotion remains scrubbed and human-reviewed. Memory never self-edits raw evidence or rewrites history.

### 12. Environment fidelity and safety are preconditions, not cleanup details

Before relying on a live or local result, establish an environment preflight appropriate to the
domain:

- signed scope and account identity;
- target repository, commit, release, package, binary, or deployment identity;
- source-to-artifact fidelity where relevant;
- build/runtime/tool versions and reproducible run command;
- isolation and external-side-effect boundaries;
- required credentials present without recording them;
- cleanup obligations and artifact destination;
- known environment deviations that may affect the oracle.

A missing or drifting environment fact produces `blocked`, `needs_review`, or contaminated evidence as
appropriate—not a confident finding.

Zone classification may provide an advisory result such as `clear_local`, `review_required`, or
`unknown`. It never emits `authorized`. Root safety gates prevail over engagement-local interpretations
until an explicit policy reconciles them. In particular, creating a Zone-2 PoC still requires fresh
human confirmation under `AGENTS.md`, even if an engagement scope appears to grant standing category
authorization.

Preflight and tripwires support judgment; they do not expand scope. Secrets, cookies, tokens,
credentials, and signed URLs remain prohibited from stored evidence.

### 13. Measure the harness's complete decision funnel

The harness must learn whether cards, model roles, prompts, stages, and reviewers generate signal or
consume attention. Record calibration and decision-quality telemetry for more than confirmed and
killed candidates; terminal-only records create survivorship and selection bias.

For every materially eligible, proposed, selected, challenged, held, deferred, refuted, contaminated,
reopened, or confirmed candidate, record where applicable:

- candidate and engagement identity plus target/domain class;
- the observation, stage, card, casebook, model, or operator prior that proposed it;
- cards activated, eligible, selected, skipped, or overridden;
- ex ante confidence or ordinal activation strength recorded before adjudication;
- model/provider version, model role, and prompt/card/schema version;
- reviewer challenges, reason codes, and independence/cold-context status;
- verdict transitions and reopening history;
- evidence, controls, and final oracle outcome;
- resulting finding ID and revision, if any;
- wall-clock time, active model/tool execution time, tokens/cost, target calls, and human-review time.

True confidence calibration requires an ex ante prediction and an independently adjudicated outcome.
Without that, the data is useful routing/performance telemetry but should not be called calibrated
probability.

Initial metrics include:

- confirmation rate by card, stage, and activation strength;
- contamination and unsupported-claim rate;
- kill-reversal and reopening rate;
- reviewer correction and claim-narrowing rate;
- persistence recovery rate;
- time and cost to confirmation or decisive closure;
- activated-card coverage and skip rationale;
- predicted impact ceiling versus demonstrated impact;
- memory candidates retained, deferred, promoted, or later reversed.

Interpret these metrics conservatively. Live engagement telemetry is observational and confounded by
target mix, domain difficulty, operator selection, and private duplicates. A rare specialist card must
not be removed merely because its raw yield is below a common web-authorization card. Production logs
also cannot reveal hypotheses the harness never generated.

Measure false negatives and causal improvements with blinded known-vulnerable and known-clean targets,
frozen cases, independent holdouts, and replay. Calibration telemetry may recommend routing, card,
prompt, reviewer, or memory changes. It does not automatically promote, delete, or rewrite them.
Advisory UCB or bandit routing remains deferred until enough cross-engagement denominators and
qualification evidence exist.

### 14. Model roles and prompts are capability assignments, not vendor law

Use the strongest available reasoning context for planning, consequential kill decisions, claim
extraction, regrade, coverage review, and final Pocinator judgment. Use persistent implementation
contexts for builds, instrumentation, repeated tests, and evidence collection. Use cheaper offline
helpers for deterministic legwork. Do not encode permanent vendor-specific assumptions where measured
role qualification can decide.

Multiple graders are not independent merely because they are separate invocations. Independence may
require:

- fresh or cold context;
- primary evidence rather than the incumbent summary;
- no prior verdict where feasible;
- a disconfirming review objective;
- a different model or human reviewer for consequential cases.

Dedicated threads are useful because they allocate attention to a narrow unresolved objective and
reduce narrative lock-in. Repeatedly asking the same model in the same context to “think harder” may
produce correlated paraphrases, not meaningful coverage.

Good prompts define the objective, evidence bar, forbidden shortcuts, stopping rule, and output
contract. They should guide search policy without enumerating every reasoning step. Never reward a
positive finding as the only successful outcome. Never ask a model to reveal private chain-of-thought;
ask for auditable hypotheses, tests, evidence, uncertainties, and decisions.

### 15. Improvement must be earned by measured effect

Telemetry and memory make the harness capable of proposing improvements. They do not prove that an
improvement works. Any card, routing, prompt, grader, or workflow change claimed to improve efficacy
must follow Decision 0004:

```text
observed weakness
  → bounded candidate change
  → isolated measurement on frozen cases and holdouts
  → false-discovery and incumbent regression checks
  → fresh replay
  → human-reviewed promotion proposal
```

Mechanism/conformance success is not real-world efficacy. Keep those claims separate. The harness
improves from evidence only when a change survives independent evaluation; otherwise it has merely
accumulated telemetry or generated a candidate.

## Documentation authority

This decision is the canonical product policy for live research reasoning, persistence, engagement
evidence state, finding/report separation, memory disposition, and calibration telemetry.

- Decision 0001 remains canonical for casebooks, pattern cards, and recon routing.
- Decision 0004 remains canonical for autonomy, measured effects, evaluator immutability, and the
  complexity budget.
- `AGENTS.md` and signed engagement scope remain authoritative for safety and authorization, with root
  gates taking precedence where policy conflicts.
- Executable schemas, gates, and tests remain implementation truth.
- `docs/ROADMAP.md` remains current-status and sequencing truth; this accepted direction does not mark
  unimplemented work complete.
- Human-readable progress files and reports must not become competing state authorities.

Future corrections should amend the relevant canonical decision rather than creating overlapping
principles documents. A new implementation abstraction still has to earn its keep under Decision
0004's complexity budget.

## Roadmap consequences

Implement in this order, keeping each change independently useful:

1. **Authority and finding contract:** define the authority map and a versioned, domain-neutral finding
   schema with structured mechanism, reachability, impact, evidence, control, and revision records;
   enforce full JSON Schema validation rather than partial field checks.
2. **Resumable state:** add append-only engagement events and deterministic state reduction; make
   progress and snapshots derived views with consistency checks.
3. **Coverage and persistence:** add the material-hypothesis ledger, separate claim/search states,
   operator priors, persistence routing, and evidence-backed dry criteria.
4. **Oracle separation:** make routing, evidence truth, claim adjudication, coverage review, regrade,
   and Pocinator responsibilities explicit without forcing a service/class hierarchy.
5. **Report gate:** require a finding ID and revision for any advisory or external report; transparently
   backfill historical reports as `needs_review` where evidence is incomplete.
6. **Environment preflight:** verify target/version/artifact fidelity, run environment, isolation,
   scope, cleanup, and advisory Zone classification before relying on results.
7. **Memory disposition:** require `promote | defer | no_novel_lesson`; retain positive and negative
   candidates; keep promotion manual and scrubbed.
8. **Full-funnel telemetry:** capture ex ante routing confidence, eligibility/selection denominators,
   challenges, transitions, outcomes, and separated cost/time.
9. **Historical replay:** exercise the new contracts against cases where persistence recovered a chain,
   regrade revived or narrowed a finding, Pocinator caught a bad proof, and coverage legitimately ended
   dry.
10. **Efficacy evaluation:** compare the staged baseline with persistence/calibration changes on blinded
    known-vulnerable and known-clean targets before making optimization claims.

## Acceptance scenarios

The product direction is faithfully implemented only when all of these are possible:

1. A model confirms two Low primitives and proposes stopping. A strong operator prior keeps search
   active without changing either finding's confidence. The model either validates a composition or
   closes the material branches with evidence.
2. A branch rejected by one reviewer is reopened after cold regrade finds an omitted real path; the
   full history remains visible and the coverage state updates without rewriting the original attempt.
3. A real finding has a claim-mismatched PoC. Pocinator routes the report back for correction rather
   than treating the finding as false or letting the overclaim ship.
4. A fresh orchestrator reconstructs scope, current claims, active hypotheses, blockers, and next work
   from authoritative records without interpreting contradictory narrative chronology.
5. A non-LLM domain records a finding without fake OWASP-LLM fields while preserving the same evidence,
   control, replay, and review discipline.
6. A `coverage_dry` verdict names the bounded material space, closures, deferrals, controls, and cold
   review; it never means only that the model stopped generating ideas.
7. Calibration analysis includes eligible, skipped, deferred, reopened, contaminated, confirmed, and
   refuted candidates with ex ante confidence; it does not infer card quality from terminal findings
   alone.
8. A telemetry-supported prompt or card change still fails closed until frozen evaluation, holdouts,
   replay, and human promotion review show measured improvement.

## Non-goals

This decision does **not** authorize or require:

- a deterministic scanner that scripts security reasoning;
- literal enumeration of every logically possible hypothesis;
- persistence until a positive result is manufactured;
- an LLM overriding scope, event truth, failed controls, or mechanical gates;
- one universal mutable state file;
- one class, service, model, or agent per conceptual responsibility;
- automatic memory promotion, card deletion, severity escalation, filing, or Plane-1 merge;
- UCB/bandit routing before qualified cross-engagement data exists;
- automatic Zone-2 authorization;
- additional dependencies, tool abstractions, or concurrency without a demonstrated need;
- claims that current simulator/conformance results prove real-model or real-world efficacy.

## Final product stance

> Human and model intuition may reopen search, increase persistence, and redirect attention. They may
> not confirm a vulnerability. Evidence confirms vulnerabilities.

> Models may make provisional decisions. They may not silently convert incomplete exploration into
> terminal certainty.

The harness should make capable researchers harder to fool, less likely to stop early, and better able
to carry learning across engagements—without replacing their judgment or rewarding them for finding
what is not there.
