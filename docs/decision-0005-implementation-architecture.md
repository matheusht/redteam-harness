# Decision 0005 implementation architecture

**Status:** Slices A–J implemented on `decision-0005/research-kernel`; see
`docs/decision-0005-implementation-report.md`. Conformance is demonstrated, but retrospective parity,
efficacy, artifact replay, and A/B execution are not.
**Governing policy:**
`docs/decisions/0005-reasoning-directed-evidence-constrained-research.md`
**Also governed by:** `AGENTS.md`, Decisions 0001 and 0004, signed engagement scope, and the root
Zone-2 gate
**Purpose:** define the smallest end-to-end architecture that makes Decision 0005 executable, then
specify retrospective and prospective evaluation without claiming efficacy from conformance alone

## 1. Outcome and success definition

The target product is a domain-neutral research kernel in which models retain control of semantic
security work while a small mechanical shell controls authority, evidence, state, and provenance.

```text
signed scope + environment identity
  -> model-directed recon, routing, hypotheses, and experiments
  -> broker/source/runtime-owned observations and immutable artifacts
  -> structured claims and independent adjudication
  -> separate claim, search, and coverage state
  -> regrade and proof-package review
  -> finding-revision-bound internal advisory
  -> operator-owned filing and memory disposition
```

Implementation is successful only when all of the following are true:

1. A fresh orchestrator can reconstruct the engagement from authoritative records without resolving
   contradictions in narrative chronology.
2. Models can reopen, backtrack, split claims, add hypotheses, and change routes without bypassing
   controls or rewriting prior evidence.
3. An operator prior can increase search depth but cannot appear as evidence for a confirmed claim.
4. Attempts and artifacts are immutable; findings are revisioned; reports identify the exact finding
   revision they represent.
5. `coverage_dry` is impossible unless every material hypothesis is closed, explicitly deferred, or
   blocked, and a cold coverage review records the bounded space.
6. Regrade and Pocinator remain distinct, typed, independently reviewable stages.
7. Non-LLM findings do not need fabricated OWASP-LLM fields.
8. Full-funnel telemetry includes eligible, skipped, held, deferred, contaminated, reopened,
   refuted, and confirmed candidates.
9. Safety, cleanup, event truth, and evaluator authority remain outside model override.
10. Historical replay shows contract and behavior parity before any efficacy claim or routing
    optimization is made.

This work does **not** build a scanner, prescribe private reasoning, create an autonomous live-target
controller, permit automatic Plane-1 promotion, authorize Zone-2 activity, or make finding volume the
objective.

## 2. Current-state facts that shape the migration

The implementation must start from the repository as it exists, not from the intended architecture:

- The engagement template currently has `scope.md`, `progress.md`, evidence/findings directories,
  recon signals, pattern candidates, memory, and cleanup, but no tracked `attempts.jsonl`, engagement
  event ledger, state snapshot, review-record directory, or environment-preflight record.
- There are currently 124 structured finding JSON files. All declare `schema_version: 2`.
- 116 of those records contain `base_model`, which the current finding schema forbids through
  `additionalProperties: false`.
- Five Vercel findings use `scope_class: local_source_and_package_safe`, which is not in the current
  schema's `scope_class` enum.
- There are no engagement attempt JSONL files to support faithful reconstruction of historical
  attempt sequences.
- There are 19 Markdown reports across Cosmos, Kubernetes, Matomo, Netflix, and Vercel; several have
  no structured finding record at all.
- Narrative progress records contain valuable decisions but also stale phase labels, status drift,
  and superseded conclusions. They cannot become a machine state authority retroactively.
- `tools/check-conformance.py` performs useful selected checks but is not a complete Draft 2020-12
  JSON Schema validator. The demonstrated campaign-schema drift has the same root cause.

Consequences:

- Migration must preserve old files byte-for-byte as legacy evidence.
- Missing attempts must be marked missing, not inferred from prose and presented as observed fact.
- Historical findings and reports may be backfilled as `needs_review`; confirmation may be restored
  only by reconstructable evidence and independent adjudication.
- A new schema version must coexist with legacy version 2 until migration is explicitly reviewed.
- Full Draft 2020-12 validation should use a maintained validator. Hand-implementing JSON Schema in
  the standard library would create a second, incomplete specification. Adding and pinning that
  dependency is an explicit implementation approval gate, not something this plan silently does.

## 3. Architectural boundaries

### 3.1 Preserve the three planes

| Plane | Existing location | New responsibility |
| --- | --- | --- |
| Methodology | `skills/`, domain manifests | Cards, techniques, oracles, safe signals, domain semantics; read-only during an engagement |
| Orchestration | `engine/`, trusted record tools | Reasoning contracts, gates, validation, append, reduction, view generation; no target-specific belief |
| Engagement | `engagements/<id>/` in the target project | Signed authority, observations, artifacts, events, finding revisions, reviews, derived views, cleanup |

Evaluation under `evals/` remains a separate qualification lane. It must not become a fourth source of
live engagement truth.

### 3.2 One public record/state command, not a workflow framework

Add one canonical public command for engagement records:

```text
python3 tools/run-engagement.py <subcommand> ...
```

Initial subcommands:

```text
init                 attest the signed scope and create records after the scope gate
validate             validate schemas, hashes, references, and transition invariants
register-artifact    hash and append an immutable artifact-manifest entry
append-attempt       validate and append one immutable attempt
append-event         validate and append one transition/decision event
record-review        validate, hash, and write one immutable review plus its commit event
revise-finding       validate, hash, and add one immutable finding revision plus its commit event
bind-report          validate and bind report bytes to an exact finding revision
record-memory        validate and commit the terminal memory disposition
reduce               deterministically rebuild state.snapshot.json
check-resume         compare the tracked snapshot/views with a fresh reduction
render               regenerate progress, coverage, and claim-to-proof views
preflight            record environment identity and advisory Zone classification
close                check cleanup, coverage, report links, and memory disposition
migrate              dry-run-first import of legacy records without rewriting them
```

Internal implementation may begin with three importable modules:

```text
tools/engagement_records.py  # schema validation, canonical JSON, refs, artifact hashes
tools/engagement_state.py    # ledger append, transitions, deterministic reducer
tools/engagement_views.py    # progress/coverage/claim-to-proof/report manifests
tools/run-engagement.py      # thin public CLI
```

Do not add one class or service per role. Split a module only after its responsibility or tests show a
real boundary. This command records and validates research; it does not drive a target or schedule
agents.

### 3.3 Model output is a proposal until trusted code records it

A model may propose a hypothesis, route, experiment, adjudication, finding revision, or coverage
verdict. It may not choose event sequence numbers, fabricate artifact hashes, authorize an action, or
write a `confirmed` event around a failed gate.

The trusted command:

1. validates the proposed record;
2. resolves and hashes referenced artifacts and every authoritative non-ledger record;
3. checks scope, environment, transition, independence, and report-link invariants;
4. appends the record or rejects it with machine-readable reason codes;
5. commits immutable file records by digest in an append-only event;
6. regenerates derived state.

The command does not decide whether unfamiliar code is vulnerable. It checks whether the semantic
judgment is supported by the required record types and authority sources.

## 4. Authority map

Authority stays partitioned. No `state.json` may become universal truth.

| Fact | Authoritative record | Mutation policy | Derived consumers |
| --- | --- | --- | --- |
| Authorization, surfaces, accounts, objectives, escalation ceiling | signed `scope.md` | human amendment only; retain prior text/history | preflight, events, attempt authorization refs |
| Target/version/build/runtime identity | immutable environment-preflight revision | append a new revision on drift | attempt/finding provenance, replay |
| What action/inspection occurred and what was observed | immutable attempt plus broker/source/runtime artifact | append-only | signal/adjudication reviews |
| Artifact bytes | file plus append-only artifact-manifest digest | never rewrite under the same artifact ID | attempts, findings, reviews, reports |
| Hypothesis, prior, selection, skip, challenge, reopening, transition | append-only engagement event | append-only | state reducer, telemetry |
| Current claim judgment | immutable finding revision | add revision; never overwrite | state snapshot, reports |
| Regrade/Pocinator/coverage judgment | immutable review record | append a new review | transition events, reports, closure |
| Current engagement state | `state.snapshot.json` | generated only | resume, progress, operator UI |
| Progress, coverage, claim-to-proof matrix | generated Markdown/JSON views | generated only | humans |
| Internal advisory | report plus report manifest bound to finding revision | regenerate or supersede | operator review |
| External submission | operator-owned artifact | receiving-program rules; never auto-file | submission event only |
| Portable memory | scrubbed human-reviewed Plane-1 promotion | PR/human review only | future routing |

### 4.1 Tamper-evident append-only records

`events.jsonl`, `attempts.jsonl`, and `artifacts.jsonl` use monotonically increasing sequence numbers
and a SHA-256 hash chain. Canonical bytes are UTF-8 JSON with sorted keys, no insignificant
whitespace, and the record's own hash omitted during hashing.

Each entry includes:

```json
{
  "sequence": 17,
  "previous_hash": "sha256:...",
  "record_hash": "sha256:..."
}
```

The first entry uses `previous_hash: null`. Validation fails on a sequence gap, changed historical
line, duplicate ID, broken hash, unresolved reference, or unknown schema version. Git remains useful
provenance, but correctness must not depend on a clean worktree or Git history being available.

Concurrency remains one by default. If scope later permits multiple live workers, append operations
must still serialize through this ledger; that requirement does not authorize parallel target work.

The operator account, local OS, and engagement filesystem are the trusted computing base. Hash chains
and committed-file digests detect mutation relative to an observed commitment; they are not digital
signatures and cannot authenticate history against an attacker who can rewrite the scope, every
ledger/file, and all comparison state. Such host compromise is outside this repository-local threat
model and requires external signing/attestation infrastructure. Model output and direct model-role
ledger events remain untrusted even inside that boundary.

### 4.2 Immutable file records and interruption recovery

Environment preflights, finding revisions, reviews, report manifests, memory dispositions, and
migration manifests are canonicalized and hashed. Their creating event records the relative path,
schema version, record ID/revision, and SHA-256 digest. Validation recomputes every committed digest;
editing a file in place fails even if its JSON still validates. A superseding record receives a new
path/revision and commit event. Artifact bytes remain committed through `artifacts.jsonl`.

An append command holds one engagement lock and follows a declared order. Attempts and artifacts are
authoritative in their own hash-chained ledgers and are reduced directly; no mirror event is required
to make them exist. Decision/transition events may reference them only after their ledger append is
fsynced. Immutable file records are written atomically to a new path, fsynced, then committed by an
event. An uncommitted new file is an orphan: validation reports it, reduction ignores it, and an
idempotent retry may commit the identical digest or quarantine it with operator review. An event that
references a missing/unhashed record always fails. Tests interrupt every write boundary and require
the same reduced state after repair/retry; no historical line or committed file is rewritten.

### 4.3 Scope attestation and amendments

The active scope hash is SHA-256 over the exact UTF-8 bytes of `scope.md`; the CLI does not normalize
or rewrite it. `init` requires the template's operator and date fields to be non-placeholder, the
signed checkbox to be checked, and `record_kernel: decision-0005-v1`. It appends a `scope.attested`
event containing the hash, non-secret operator label, signed date, kernel selection, and optional
superseded scope hash. This is a human attestation plus tamper-evident binding, not a cryptographic
identity claim. Any amendment preserves the prior Git/file history externally and appends a new
attestation before records use the new hash. Dependent records cite the exact scope hash; scope drift
blocks new writes until re-attested.

## 5. Engagement record layout

New engagements use this layout. Existing engagements are not moved in place.

```text
engagements/<id>/
  scope.md                              # signed authority
  environment/
    preflight-0001.json                 # immutable fidelity/safety preflight
  attempts.jsonl                        # immutable experiment/inspection records
  artifacts.jsonl                       # immutable artifact metadata and digests
  events.jsonl                          # append-only decisions/transitions
  evidence/                             # artifact bytes; registered before use
  findings/
    <finding-id>/
      rev-0001.json                     # immutable adjudication revision
      rev-0002.json
  reviews/
    <review-id>.json                    # signal/adjudication/coverage/regrade/pocinator
  reports/
    <slug>.md                           # internal view
    <slug>.report.json                  # exact finding revision + content hash
  submissions/                          # optional, operator-owned external text
  memory/
    disposition.json                    # promote | defer | no_novel_lesson
  cleanup.md                            # human ledger; completion checked
  state.snapshot.json                   # deterministic reduction
  progress.md                           # generated view
  coverage.md                           # generated view
  claim-to-proof.md                     # generated view
  legacy/                               # optional migration manifests, never rewritten originals
```

`recon-signals.md`, `pattern-candidates.md`, and other useful notes may remain. The reducer treats them
as notes or registered artifacts, never as current-state authority.

## 6. Core schemas

All new schemas use JSON Schema Draft 2020-12, `additionalProperties: false` at governed boundaries,
stable `$id` values, and explicit `schema_version` constants. Common definitions live in one small
`schemas/research-common.schema.json`; avoid deep `$ref` graphs.

### 6.1 Finding version 3: domain-neutral and revisioned

Add `schemas/finding-v3.schema.json`. Keep `schemas/finding.schema.json` as the legacy version-2
contract until migration is complete; do not mutate version 2 in a way that rewrites historical
meaning.

Required version-3 sections:

```text
identity
  schema_version = 3
  finding_id, engagement_id, revision, supersedes_revision
  recorded_at, change_reason

classification
  domain
  weakness identifiers[] (optional taxonomy namespace + ID)
  severity label/system/vector/rationale (vector optional)

scope and provenance
  signed scope hash
  environment-preflight ref
  target/artifact/version refs
  actor/model/prompt/card/schema versions where applicable

claim state
  supported | confirmed | needs_review | contaminated | refuted

structured claims
  attacker model and preconditions
  mechanism statement
  reachability statement and causal-spine nodes
  impact claims[] marked demonstrated | inferred | not_demonstrated
  uncertainty and conflicting evidence

proof contract
  primary attempt refs
  negative/positive control refs with explicit applicability
  replay refs and fresh-state properties
  contamination disposition
  immutable evidence/artifact refs

adjudication
  claim-adjudication review ref
  one-sentence prime-directive justification

search linkage
  originating candidate/hypothesis refs only
```

Do **not** store current search state, engagement coverage, report status, or mutable review history in
the finding. Those are reduced from events and reviews. This avoids the current failure mode where a
submitted report can coexist with a finding still marked `open`.

Every impact claim is atomic enough to bind evidence separately. “Arbitrary code execution and
cross-tenant takeover” must be split if the proof establishes only one. Severity is revisioned
judgment, not an event-truth field.

A version-3 `legacy_import` profile is conditional on `claim_state: needs_review`. It identifies the
source artifact/hash and represents unavailable scope, environment, attempt, control, replay, or
adjudication facts with typed `missing_legacy_evidence` entries rather than fabricated refs. Such a
revision cannot transition to `supported` or `confirmed`; a later ordinary revision must supply the
full current proof contract. This profile makes transparent migration schema-valid without weakening
the ordinary finding contract.

### 6.2 Attempt version 2: immutable event evidence across domains

Add `schemas/attempt-v2.schema.json`. Required fields:

- attempt and engagement identity;
- timestamp, actor role, model/tool provenance where applicable;
- scope hash, environment ref, and any escalation-confirmation event ref;
- hypothesis/experiment ref;
- target surface and action/inspection summary with redaction attestation;
- observation source: `broker`, `runtime`, `source_inspection`, `operator`, or `model_report`;
- concrete observation and immutable evidence refs;
- attempt kind: primary, negative control, positive control, replay, source trace, or environment
  check;
- control/replay linkage;
- researcher-level assessment only: `suspected_signal`, `no_signal`, `held`, `error`, or
  `inconclusive`;
- contamination observation;
- target/model/tool call and time/cost ledger.

`confirmed` is not an attempt outcome. A `model_report` observation cannot serve as the sole event
truth for confirmation.

### 6.3 Artifact manifest

Add `schemas/artifact.schema.json`. Each artifact entry records:

- stable artifact ID and relative path;
- SHA-256, size, media type, and creation timestamp;
- producer and acquisition method;
- target/environment refs;
- sensitivity/redaction status;
- whether it contains executable capability;
- advisory Zone classification (`clear_local`, `review_required`, or `unknown`);
- fresh `escalation.confirmed` event and cleanup-obligation refs when Zone-2/review-required;
- cleanup-ledger reference where relevant;
- immutable/supersedes relationship.

Registering an artifact does not make it evidence of the claimed mechanism. It only proves which
bytes were reviewed.

### 6.4 Engagement event envelope

Add `schemas/engagement-event.schema.json`. Every event has:

- ID, sequence, timestamp, engagement, actor/role;
- event type and entity refs;
- schema/prompt/model/card provenance where relevant;
- concise rationale, not private chain-of-thought;
- evidence/review refs where required;
- ex ante confidence or ordinal activation strength when the event is pre-adjudication;
- previous and current state fields for transitions;
- hash-chain fields.

Initial event vocabulary:

```text
scope.attested                    environment.preflight_recorded
observation.recorded              routing.assessed
candidate.proposed                candidate.selected
candidate.skipped                 candidate.deferred
operator_prior.recorded           hypothesis.created
hypothesis.status_changed         attempt.recorded
claim.adjudicated                 finding.revised
review.challenge_recorded         review.regrade_completed
review.pocinator_completed        review.coverage_completed
coverage.status_changed           report.generated
operator.review_recorded          submission.recorded
cleanup.updated                   memory.disposition_recorded
escalation.confirmed              legacy.record_imported
engagement.blocked                engagement.reopened
```

The vocabulary should grow only from a demonstrated transition that cannot be represented faithfully.
Unknown event types fail closed until the schema/reducer is deliberately updated.

### 6.5 Review record

Add `schemas/review.schema.json` with conditional fields by `review_type`:

```text
signal | claim_adjudication | coverage | regrade | pocinator | operator
```

Common fields include immutable inputs and hashes, entity/finding revision, evidence refs, concise
rationale, conflicting evidence, verdict, corrections, required next actions, and independence
metadata.

Typed outcomes remain distinct:

- regrade: `confirmed`, `confirmed_with_correction`, `escalation_found`,
  `needs_more_evidence`, `refuted`, `blocked`;
- Pocinator: `verified`, `needs_rework`, `claim_mismatch`, `reward_hacked`, `blocked`;
- coverage: `continue`, `coverage_dry`, `blocked`.

A regrade requires fresh-context metadata: reviewer/run ID, immutable input-set hash, prior-verdict
visibility, fresh-context attestation, reviewer/model identity, and disconfirming objective. Mechanical
validation rejects reuse of the originating or prior review run ID and rejects two purportedly
independent reviews with the same reviewer run and input transcript. It cannot prove cognitive
independence; that residual is explicit reviewer/operator judgment. Control applicability and replay
freshness likewise require typed attempt refs and rationale while semantic applicability remains an
adjudication judgment.

A definite `reward_hacked` outcome on a high-value finding requires a second independent Pocinator
record before terminal treatment. Non-verified Pocinator outcomes route back; they do not automatically
refute the vulnerability.

### 6.6 Environment preflight

Add `schemas/environment-preflight.schema.json`. It records:

- signed-scope hash and owned account identity by non-secret label;
- mode: black-box, gray-box, white-box, binary, package, chain/devnet, or other;
- repository/commit/tag/release/package/binary/deployment identity;
- source-to-built-artifact hashes where relevant;
- build/runtime/tool versions and reproducible command;
- isolation and allowed network/side-effect boundary;
- credential presence booleans, never credential values;
- cleanup obligations and artifact destination;
- known deviations affecting the oracle;
- status: `pass`, `needs_review`, or `blocked`;
- advisory Zone classification: `clear_local`, `review_required`, or `unknown`.

No preflight field may say `authorized`. A target/version drift creates a new preflight revision and
invalidates attempts that claim the old environment while using the new one. An
`escalation.confirmed` event is valid only when created by an operator for the same engagement, active
scope hash, environment ref, bounded action/artifact class, and cleanup obligation. It expires after
the stated one-shot action or explicit time bound and cannot be reused across engagements or scope/
environment revisions.

### 6.7 Report manifest and memory disposition

`schemas/report-manifest.schema.json` binds internal report bytes to:

- finding ID and exact revision;
- structured claim IDs included or intentionally omitted;
- claim-to-proof matrix hash;
- report content hash;
- generator/model provenance;
- operator-review status;
- external-submission policy note.

`schemas/memory-disposition.schema.json` requires exactly one terminal disposition:
`promote`, `defer`, or `no_novel_lesson`, plus rationale, candidate refs, sanitization status, and human
review. Only `promote` can later create a Plane-1 PR, and never directly.

## 7. State model and reducer

### 7.1 State dimensions remain independent

The reducer tracks:

```text
claim:      supported | confirmed | needs_review | contaminated | refuted
search:     unexplored | active | held | locally_exhausted | deferred
coverage:   active | blocked | coverage_dry
```

It also tracks report, review, cleanup, and memory lifecycle, but does not collapse those into claim
state. A confirmed Low primitive can coexist with active chainability hypotheses and active coverage.

### 7.2 Snapshot shape

`state.snapshot.json` contains only reduced current state and integrity metadata:

```text
schema and engagement ID
scope hash and active environment ref
last event ID, event count, ledger hash
active blockers
candidate routing/selection state
operator priors
material hypotheses and search state
finding IDs and current revisions/claim states
outstanding regrade/Pocinator actions
coverage state and latest coverage review
report/submission refs
cleanup state
memory disposition
integrity errors (empty for a valid snapshot)
```

The snapshot never embeds artifact bodies, report prose, or rewritten attempts. It is safe to delete
and regenerate. Canonical key/list ordering is specified by the reducer, and snapshots/views contain
source-ledger hashes rather than wall-clock generation timestamps. `check-resume` fails if the
committed snapshot or generated views differ from a fresh reduction.

### 7.3 Transition invariants

Mechanical invariants include:

- an operator prior may create/reopen hypotheses but cannot transition a claim to `confirmed`;
- routing may select a card but cannot emit claim adjudication;
- confirmation requires a valid claim-adjudication review, primary evidence, applicable controls,
  replay policy, and a passing environment ref;
- a model report cannot be the only evidence authority;
- contamination cannot be silently changed to ruled out without a new attempt/review;
- a finding revision must supersede the current revision exactly;
- a report must reference the current or explicitly selected historical finding revision;
- a submission event requires operator review and the receiving program's authorship/disclosure note;
- `coverage_dry` requires a valid cold coverage review and no unexplained active material hypothesis;
- a deferred hypothesis needs a reason and reopening condition;
- a confirmed primitive needs a chainability disposition where meaningful, or explicit
  `not_applicable` rationale;
- a non-verified Pocinator result prevents advisory-ready state but does not change finding truth by
  itself;
- scope/environment changes invalidate only dependent current decisions; they do not rewrite history;
- engagement closure requires cleanup disposition and memory disposition;
- `cleanup.updated` carries structured obligation IDs, statuses, operator/date, active scope hash, and
  artifact refs; `close` requires every live-artifact obligation to be `completed`, `not_applicable`
  with rationale, or explicitly `blocked`, while `cleanup.md` remains the human ledger;
- any review-required/Zone-2 artifact requires a same-engagement, active-scope/environment, unexpired
  `escalation.confirmed` event created before artifact registration, plus a cleanup obligation.

These rules validate evidence obligations and state coherence. They do not decide whether a call graph
is realistic, whether a protocol invariant is violated, or whether impact is novel.

## 8. Material-hypothesis and persistence architecture

A material hypothesis is created from an observation, activation signal, confirmed primitive,
operator prior, reviewer challenge, or newly learned target model. Its creation event records:

- origin and rationale;
- suspected invariant/trust-boundary failure;
- attacker path and possible impact ceiling;
- applicable cards/lenses;
- ex ante confidence or ordinal strength;
- expected confirming evidence and decisive falsifiers;
- budget/constraints and next experiment.

Status transitions append:

- experiments and controls performed;
- supporting/conflicting evidence;
- why a route held or was exhausted;
- unresolved questions;
- next route or decisive falsifier.

Persistence mode is a routing state, not a prompt that requires success. It activates from a
confirmed primitive, strong signal, credible anomaly, operator prior, or reviewer-identified omission.
The coverage view groups hypotheses by materially different mechanism or composition, not payload
spelling. Repeated cosmetic variants do not increase coverage.

A `coverage_dry` review must state:

1. the bounded objective/surface space;
2. the material hypothesis set and origin of each;
3. decisive closures, explicit deferrals, and blockers;
4. unexpected observations and their explanations;
5. chainability disposition for confirmed primitives;
6. known out-of-scope or forbidden prerequisites;
7. cold-review independence and omitted-branch challenge;
8. residual uncertainty.

The model remains free to decide which hypotheses are material and what tests discriminate them. The
record lets another reviewer challenge that decision.

## 9. Oracle and review separation in operation

No service or permanent model assignment is required. Each responsibility emits a different record:

| Responsibility | Input | Output | Forbidden authority |
| --- | --- | --- | --- |
| Router | observations, cards, priors | `routing.assessed` event | cannot confirm a claim |
| Signal grader | attempts/artifacts | signal review | cannot establish impact |
| Evidence authority | source/runtime/broker/operator observation | attempt/artifact | cannot self-adjudicate meaning |
| Claim adjudicator | primary evidence + controls | adjudication review + finding revision | cannot invent event truth |
| Coverage grader | full hypothesis ledger | coverage review | cannot lower proof standard |
| Regrade | primary evidence in fresh context | typed regrade review | escalation still needs new evidence |
| Pocinator | fixed claim tuple + exact package | typed proof review | does not decide novelty or general finding truth |
| Operator | scope, escalation, consequential review, filing/promotion | signed/operator events | cannot turn intuition into evidence |

The record contract requires role and independence metadata. Different invocations are not treated as
independent merely because they have different IDs. Fresh context, primary evidence, prior-verdict
visibility, reviewer identity/model, and disconfirming objective are recorded explicitly.

## 10. Generated views and reporting

### 10.1 Human-readable views

`render` deterministically creates:

- `progress.md`: active scope/environment, current findings, active hypotheses, blockers, next routes;
- `coverage.md`: material hypothesis ledger and closure evidence;
- `claim-to-proof.md`: each atomic claim mapped to attempts, artifacts, controls, replay, and reviews.

A human may add narrative notes elsewhere, but direct edits to generated views fail `check-resume`.
This removes stale-stage and contradictory-status drift without erasing narrative history.

### 10.2 Internal advisory gate

A model may draft internal prose only after the report manifest can bind it to a finding revision.
The renderer/gate checks:

- every included mechanism/reachability/impact sentence maps to a structured claim ID;
- demonstrated and inferred impact are visibly distinguished;
- the target/version and preconditions match the finding revision;
- controls and replay are linked;
- regrade is terminally acceptable;
- Pocinator is `verified` when required, or an explicit operator skip record exists;
- no artifact digest drift exists;
- the report has no secret-bearing refs.

The gate checks linkage and consistency, not literary quality or semantic truth.

### 10.3 External submission boundary

External filing remains outside model authority. A submission event records only program, operator,
date, referenced finding/report revision, and outcome. It never stores auth material. If the program
forbids AI-authored text, as in the Cosmos engagement, the operator must personally re-author the
submission. Internal generated prose is evidence-dossier input, not submission text.

Duplicate outcomes are tracked but do not refute the mechanism or serve as a direct efficacy score.

## 11. Domain packs without a core rewrite

Do not move all existing cards. Add optional domain manifests only after the core schemas work:

```text
domains/<domain-id>/manifest.json
```

A manifest lists:

- domain ID/version and applicable environment profiles;
- existing vuln/pattern/technique card IDs;
- domain terminology and taxonomy namespaces;
- safe-signal and escalation defaults;
- expected control/falsifier families;
- impact-model and proof-profile references.

Initial manifests may cover `llm-application`, `web-api`, `source-audit`, `supply-chain`, and
`blockchain-consensus`, while referring to existing `skills/` cards. A pack proposes semantic
vocabulary; it does not become an oracle. Unknown domains can still use the core finding contract with
free domain identifiers and structured claims. Version 1 keeps governed core records closed: a domain
pack may add namespaced taxonomy/schema references and separate registered artifacts, not arbitrary
unchecked keys inside the core record. A demonstrated need for inline extension data requires a later
versioned schema contract; it may not bypass `additionalProperties: false`.

## 12. Safety and operational controls

The new machinery must make existing gates harder to bypass, never broader:

- No command runs until `scope.md` is filled and signed.
- No vuln card without a benign `safe_signal` loads.
- The orchestrator still does not drive the target beyond establishing a session; a bounded Hunter
  performs authorized target actions and returns attempts.
- Before any Zone-2 artifact is **created**, stop for fresh explicit human confirmation and append the
  confirmation/cleanup refs. Engagement-local standing language cannot override the root gate. The
  record kernel can reject registration/use of an unconfirmed artifact but cannot prevent bytes made
  outside it; pre-creation prevention remains an orchestrator/action-broker responsibility.
- Review remains required before moving self -> stored/persistent -> cross-user.
- Advisory Zone output is only `clear_local`, `review_required`, or `unknown`, never `authorized`.
- Credentials may be present for a run but are represented only as booleans/non-secret account labels.
- Cookies, JWTs, Authorization headers, signed URLs, and passwords never enter records.
- Artifact registration scans for known secret shapes, but a clean scan is not a guarantee; operator
  redaction remains required.
- Cleanup closure is a hard engagement-completion gate.
- Existing capability adapters remain sensors/proposers. They cannot emit confirmation.

## 13. Implementation program: thin vertical slices

Every slice must add an invariant, remove or internalize an ambiguity, and close with tests. No slice
claims improved vulnerability discovery merely because it passes. Before implementation, each slice
records the invariant, authority path replaced/internalized, new failure modes and loaded-context cost,
smaller alternative considered, and removal/rollback path. This is the Decision-0004 complexity gate,
not post-hoc accounting.

### Slice A — Authority and full schema validation

**Files:**

- add version-3 finding, version-2 attempt, artifact, review, and common schemas;
- add `tools/engagement_records.py` and the `validate` subset of `tools/run-engagement.py`;
- add valid/invalid fixtures under `fixtures/engagement-records/`;
- update `tools/check-conformance.py` to call the complete validator for new records;
- update CI to install one approved, exactly pinned Draft 2020-12 validator.

**Dependency gate:** obtain explicit approval before adding the validator dependency. If approval is
withheld, do not claim full JSON Schema conformance and do not hand-roll a partial substitute.

**Acceptance:**

- unknown fields, wrong enums, missing conditionals, and broken refs fail;
- current legacy drift is reported in a migration inventory, not hidden or made a new CI failure by
  surprise;
- new findings contain no mandatory LLM-specific field;
- the existing 116 `base_model` and five scope-enum mismatches are surfaced by deterministic tests;
- selected duplicate checks are deleted from `check-conformance.py` once schema parity is proven.

### Slice B — Append-only events and deterministic resume

**Files:**

- add event and snapshot schemas;
- add `tools/engagement_state.py` and append/reduce/check-resume commands;
- add hash-chain and transition fixtures;
- extend `_TEMPLATE` with empty ledgers/directories initialized by `init`;
- make `progress.md` a generated view for newly initialized engagements.

**Acceptance:**

- identical ledgers reduce byte-identically across fresh runs;
- changed historical lines, bad hashes, unknown events, duplicate IDs, stale snapshots, invalid
  transitions, modified committed file records, and orphan/missing commit records fail;
- interruption after every ledger/file/event write boundary resumes to the same state through
  idempotent retry or explicit orphan handling;
- original attempts and artifacts are never rewritten during reduction;
- current narrative-only engagements remain readable and untouched.

### Slice C — Findings, hypotheses, operator priors, and coverage

**Files:**

- implement finding revision and hypothesis/prior/coverage event transitions;
- add coverage review conditionals;
- generate `coverage.md`;
- update `engine/persistence.md`, `engine/loop.md`, and the engagement template to point to the
  machine contract without prescribing model reasoning.

**Acceptance:**

- a strong operator prior reopens search but cannot confirm a claim;
- a refuted implementation may leave a broader mechanism hypothesis active;
- a confirmed primitive may coexist with active chainability work;
- `coverage_dry` fails with an active/unexplained material hypothesis or missing cold review;
- a well-supported negative engagement closes successfully.

### Slice D — Review contracts and structured proof

**Files:**

- complete review-schema conditionals;
- update `engine/regrade.md`, `engine/pocinator.md`, and oracle docs with record outputs;
- implement claim-to-proof rendering;
- add fixtures for corrections, escalation, claim mismatch, reward hacking, and blocked review.

**Acceptance:**

- regrade truth and Pocinator proof validity cannot overwrite one another;
- `escalation_found` routes to evidence collection before a finding revision claims the escalation;
- `claim_mismatch` routes to claim/report correction rather than false refutation;
- definite high-value `reward_hacked` requires second independent review;
- module-level proof cannot substitute for end-to-end composition review.

### Slice E — Report gate and transparent historical backfill

**Files:**

- add report-manifest schema and report rendering/link checks;
- implement report lifecycle in the reducer;
- add migration dry-run inventory for all current reports/findings;
- create per-engagement migration proposals only after operator review.

**Acceptance:**

- no new advisory can exist without finding ID and revision;
- changing a finding revision makes the old report visibly historical, not silently current;
- narrative-only historical reports become `needs_review` unless evidence is reconstructable;
- external submission text remains separate and operator-owned;
- submitted/reported state is reduced from events, removing the stale `status: open` conflict.

### Slice F — Environment fidelity and safety preflight

**Files:**

- add environment-preflight schema and `preflight` command;
- add target identity collectors only for demonstrated modes (begin with Git/package/local runtime);
- add scope-hash, credential-redaction, cleanup, and advisory-Zone checks.

**Acceptance:**

- wrong commit/release/package, missing runtime, non-reproducible command, or unexplained deviation
  yields `blocked`/`needs_review`;
- changing target identity cannot reuse a stale preflight;
- no preflight authorizes Zone-2;
- no secret value appears in output.

### Slice G — Memory disposition

**Files:**

- add memory-disposition schema and closure gate;
- update pattern-candidate and winners guidance;
- permit positive and negative lessons with provenance/sanitization metadata.

**Acceptance:**

- every completed engagement records one disposition;
- `no_novel_lesson` is valid and promotion is never forced;
- no model writes Plane-1 memory directly;
- refutations, reward-hacked proof patterns, and environment failures can be proposed as lessons.

### Slice H — Full-funnel telemetry and calibration export

**Files:**

- derive telemetry from events/reviews/attempt cost records;
- add a versioned export schema and offline scorer under `evals/research-kernel/`;
- add missing-denominator and post-outcome-confidence traps.

**Acceptance:**

- eligible, selected, skipped, overridden, held, deferred, contaminated, reopened, refuted, and
  confirmed candidates are all representable;
- ex ante confidence is timestamped before adjudication;
- data without ex ante probability is labeled routing/performance telemetry, not calibration;
- wall time, model/tool time, target calls, tokens/cost, and human-review time remain separate;
- no metric automatically deletes cards or enables a bandit.

### Slice I — Historical migration and retrospective replay

Implement the migration and replay protocol in Sections 14-16. Migration runs dry first and never
rewrites raw records. Each engagement is reviewed independently.

### Slice J — Blinded efficacy qualification and A/B readiness

Only after Slices A-I pass may the new kernel be frozen as an experimental arm. Qualification follows
Section 17. No live routing optimization or automatic promotion is authorized by this slice.

## 14. Migration architecture

### 14.1 Import, do not rewrite

For each existing engagement, `migrate --dry-run` emits:

```text
migration/inventory.json
migration/proposed-events.jsonl
migration/proposed-finding-revisions/
migration/unresolved.json
```

The inventory hashes every source file and classifies it as structured-valid, structured-drifted,
narrative-only, artifact, report, submission-like, or unknown. Applying an approved migration:

1. registers the original file as an immutable legacy artifact;
2. appends `legacy.record_imported` provenance through the versioned migration event;
3. creates a version-3 finding revision only from reconstructable fields;
4. marks unavailable attempt history and controls as missing;
5. defaults claim state to `needs_review` when adjudication cannot be reconstructed;
6. binds reports to the imported revision or marks them unresolved;
7. leaves original paths and bytes unchanged.

No attempt IDs are invented from a paragraph that says a test was run. The paragraph can be an
artifact ref; it is not transformed into broker-owned event truth.

### 14.2 Migration cohorts

Migrate in increasing ambiguity:

1. current structured findings with complete local evidence and PoCs (Netflix/Vercel examples);
2. benchmark findings with known target/grade manifests (Cybench/XBOW), while preserving benchmark
   provenance and avoiding false live-validation claims;
3. structured but deferred/needs-review live findings (Duplogreenengine);
4. narrative reports with strong local artifacts (Matomo/Cosmos/Kubernetes);
5. dry/refuted narrative-only coverage records (Netflix Atlas/Spectator, Vercel `ms`, ALSCO);
6. incomplete or environmentally blocked engagements.

A migration completion report counts unresolved fields and `needs_review` records. A lower migrated
finding count is acceptable; fabricated completeness is not.

## 15. Test architecture

### 15.1 Unit and schema tests

Required fixture classes:

- one valid minimum and one valid rich record for every schema/version;
- unknown property, wrong enum, missing conditional field, wrong revision, unresolved ref;
- attempt that claims `confirmed`;
- model-report-only confirmation;
- operator prior used as proof;
- router self-adjudication;
- missing/failed controls and contaminated replay;
- target/preflight hash drift;
- report bound to stale or nonexistent finding revision;
- regrade/Pocinator verdict confusion;
- `coverage_dry` with active, unexplained, or silently skipped hypotheses;
- missing memory/cleanup disposition;
- secret-shaped content and unsafe artifact metadata;
- malformed, truncated, reordered, duplicated, and tampered JSONL.

Use deterministic randomized transition sequences to test reducer invariants without adding a
property-testing dependency initially. Add such a dependency only if the deterministic corpus reveals
a real coverage wall.

### 15.2 Integration tests: Decision 0005 acceptance scenarios

Create frozen synthetic engagements for all eight policy scenarios:

1. two confirmed Low primitives, strong prior, active composition search, then supported closure;
2. consequential kill reopened by cold regrade;
3. real finding with claim-mismatched PoC routed for correction;
4. fresh-orchestrator exact resume from records;
5. non-LLM finding with no fake LLM taxonomy;
6. credible `coverage_dry` with bounded closures and cold review;
7. complete-funnel telemetry including skipped/reopened/contaminated candidates;
8. telemetry-supported card/prompt change blocked until isolated evaluation and replay.

Each fixture asserts both allowed transitions and forbidden shortcuts.

### 15.3 Adversarial state tests

Add explicit attacks against the shell:

- edit an old attempt then recompute only the last event hash;
- replace artifact bytes after report review;
- create a new finding revision that skips one revision;
- claim fresh context while reusing an identical reviewer run ID/input transcript;
- use an operator-confirmation event from another engagement;
- reuse an environment preflight after target version drift;
- mark every untested branch `deferred` with empty rationale;
- split one root cause into many findings to inflate metrics;
- record confidence after seeing the oracle result;
- generate a report from an inferred impact while labeling it demonstrated;
- use a scanner verdict as event truth;
- mark cleanup complete while live artifacts remain in the ledger.

### 15.4 CI sequence

After implementation, CI should run in this order:

```text
full schema/record fixtures
engagement state/reducer self-test
view/report-link self-test
legacy migration dry-run regression
existing conformance and evaluator self-tests
historical replay scorer self-test
canonical behavioral campaign hash check
git diff whitespace and generated-view consistency checks
```

Existing experiment-lifecycle tests remain independent. Passing engagement-state tests does not make a
GEPA candidate promotable, and passing GEPA tests does not validate live engagement state.

## 16. Retrospective evaluation on past engagements

Historical evaluation has three distinct layers. Their conclusions must not be blended.

### 16.1 Layer 1 — Record reconstruction

**Question:** can the new architecture represent what the final historical record says happened?

This is offline migration/conformance. It tests state, provenance, finding revision, typed review, and
report linkage. It does **not** test whether a model would rediscover the finding.

Acceptance metrics:

- authoritative facts reconstructed without rewriting source records;
- unresolved/contradictory facts explicitly counted;
- final claim/search/coverage states match the independently curated historical adjudication;
- report/finding revision linkage complete;
- no invented attempts or controls;
- exact resume from the migrated ledger.

### 16.2 Layer 2 — Artifact replay

**Question:** do preserved local PoCs, controls, and proof packages still produce the adjudicated
result in a faithful pinned environment?

Rules:

- rebuild from exact target commit/release/package where available;
- use clean worktrees/containers or documented equivalent isolation;
- verify source/artifact fidelity before execution;
- run negative controls and required fresh-state replays;
- compare the exact claim tuple, not only exit code/marker;
- re-run Pocinator against the packaged artifact;
- require fresh human confirmation before any Zone-2 artifact creation or impact-demonstration step;
- never contact old live targets under stale scope.

A missing environment yields `blocked`, not a failed finding or a synthetic pass.

### 16.3 Layer 3 — Blinded research rerun

**Question:** under matched budgets, does the new harness change discovery, correction, persistence,
coverage, or cost?

For each case create a frozen case manifest containing:

- case ID/domain and contamination class;
- target source and exact version/hash;
- signed hermetic scope and allowed actions;
- initial recon packet only;
- withheld historical findings, reports, progress, PoCs, and case-derived memory;
- target/build commands and budget;
- expected root causes, legitimate negative closures, and claim boundaries in a sealed judge packet;
- scoring rules and independent adjudicators.

Run two isolated arms with identical model/provider versions, tools, target copies, call/time budget,
and starting information:

- **A — staged baseline:** the pre-Decision-0005 live-research method frozen by tree/file hashes;
- **B — new kernel:** the implemented Decision-0005 records, persistence, review, and coverage
  contracts.

Use independent sessions and no shared notes. Randomize anonymized arm labels. Freeze outputs before
opening the judge packet. Historical cases that directly shaped Decision 0005 are regression cases,
not unbiased efficacy holdouts; report them separately.

### 16.4 Historical case matrix

| Case | What it exercises | Replay tier | Expected comparison |
| --- | --- | --- | --- |
| Vercel Skills symlink disclosure | original negative overturned by fresh regrade; escalation then new PoC | reconstruction + local artifact + blinded rerun | preserve reopening/history and recover the second path without erasing the first mistake |
| Netflix Zuul `stopFilterProcessing` | real mechanism narrowed from default bypass to third-party API footgun; extra empirical test requested | all three | fewer unsupported deployment claims while preserving the real finding |
| Cosmos IAVL negative-version state sync | real end-to-end crash, chainability escalation, Pocinator rework, later retry-state correction | reconstruction; local replay only after gate; blinded source rerun | exact staged corrections and proof-package routing |
| Matomo CoreUpdater | regrade expanded reach from low privilege to unauthenticated while narrowing pending-update precondition and impact language | reconstruction; local replay only after gate | recover stronger reach without broadening the precondition |
| Cosmos CometBFT stuck-peer and mempool leads | strong-looking candidates refuted or sharply capped by independent regrade | reconstruction + blinded source rerun | lower unsupported-claim/severity rate; preserve legitimate negatives |
| Vercel Flags prototype pollution | severity critical -> high after independent precondition review | reconstruction + local replay | correct claim and severity boundaries |
| Vercel workflow token predictability | PoC corrected to full RNG order and stable-version behavior | reconstruction + local artifact replay | Pocinator catches simplified-model proof gaps |
| ALSCO Royal CMS/upload | SQLi refuted with self-owned control; detector bypass real but reachability capped/environment blocked | reconstruction only unless freshly reauthorized | distinguish refuted, real-but-capped, blocked, and coverage dry |
| Duplogreenengine 97-RPC sweep | one BFLA among many held siblings, deferred cross-user/paywall work | reconstruction only; no old live replay | complete-funnel accounting and operator-prior persistence without forced positives |
| Netflix Atlas/Spectator and Vercel `ms` | legitimate dry/policy-excluded outcomes | reconstruction + source rerun | credible negative closure and no finding manufacturing |
| Cybench/XBOW subsets | known-vulnerable, multi-domain benchmark tasks | hermetic blinded rerun | root-cause recall and cost under known truth |
| false-discovery corpus and known-clean fixtures | echoed canaries, inert reflections, missing replay, duplicate coverage | hermetic | zero invalid accepts remains a hard veto |

Case manifests must state whether current cards, prompts, or model context already contain the lesson.
Such cases measure regression/conformance, not independent discovery.

### 16.5 Metrics

Score atomic root causes and claims, deduplicated by mechanism and oracle boundary.

**Hard gates:**

- safety violations: 0;
- secrets stored: 0;
- known-clean/false-discovery invalid accepts: 0;
- reports without valid finding revision: 0;
- artifact/hash/provenance violations: 0;
- unsupported confirmed impact claims: no regression.

**Rigor and correction:**

- independently confirmed precision;
- contamination and unsupported-claim rate;
- regrade correction, kill-reversal, and reopening capture;
- Pocinator issue detection by typed outcome;
- demonstrated-vs-inferred impact accuracy;
- valid negative-control and replay completion;
- valid coverage-closure rate;
- resume/state-consistency failures.

**Discovery and resolution:**

- independently confirmed root-cause recall on known-vulnerable cases;
- persistence recovery rate after an initial held/kill decision;
- decisive negative closure on known-clean cases;
- material-hypothesis eligibility, selection, and skip coverage;
- time/cost to confirmation or decisive closure;
- target/model/tool calls and human-review time;
- chainability review completion without severity inflation.

**Calibration:**

- Brier score and reliability tables only for ex ante probabilities recorded before adjudication;
- ordinal activation precision/recall when only weak/strong signals exist;
- no use of terminal-only confidence as calibration;
- report small-sample uncertainty rather than fitting a confident curve.

Do not use raw finding count, summed severity, bounty amount, or duplicate/non-duplicate status as the
primary metric.

### 16.6 Analysis and release gate

Use paired case-level deltas and publish every case, including ties and blocked runs. With small
samples, report exact counts and paired differences; do not manufacture statistical significance.
Use bootstrap intervals only when the cohort is large enough to support them.

Release the new kernel for prospective testing only if:

1. all hard gates pass;
2. known-vulnerable root-cause recall is non-inferior to baseline;
3. known-clean invalid accepts remain zero;
4. state/resume/report-link acceptance scenarios all pass;
5. observed correction/persistence gains are not caused by leaked historical answers;
6. cost increases, if any, are explicit and operator-acceptable;
7. blocked environments and unresolved migrations are reported, not imputed.

A successful retrospective establishes regression confidence and a basis for prospective evaluation.
It does not alone prove general real-world efficacy because the design was informed by these cases.

## 17. Prospective A/B plan for new targets

### 17.1 Experimental question

Does the implemented Decision-0005 kernel, compared with the frozen staged baseline, improve
independently adjudicated root-cause discovery or decisive closure without increasing false
discovery, unsupported claims, safety violations, or cost beyond the declared bound?

### 17.2 Three evaluation lanes

1. **Sealed known-truth lane:** blinded known-vulnerable and known-clean local targets not used to
   write the new contracts. This supports causal recall/FDR measurement.
2. **Fresh pinned-source lane:** new OSS/package targets in isolated environments with independent
   expert adjudication. This tests transfer but has incomplete ground truth.
3. **Authorized live/organic lane:** real engagements under signed scope. This measures operational
   usability and external validity, but cannot estimate false negatives from findings alone.

Results stay separated by lane. Organic finding counts cannot substitute for sealed ground truth.

### 17.3 Unit of assignment and isolation

Prefer paired, independent arm runs on cloned local target/objective slices:

- one frozen target version per pair;
- independent model sessions and filesystem/environment copies;
- no shared memory, transcripts, artifacts, or target state;
- identical allowed tools, domain packs, budgets, and model/provider versions;
- anonymized A/B labels for adjudicators.

For live targets where actions or state can leak across arms, randomize at the target/environment or
account cluster, not the candidate level. Do not run paired live arms unless separate owned sandboxes
and cleanup paths make interference impossible.

Never switch the same model context from A to B on one target; discovery in the first period
contaminates the second. A post-study rescue pass may investigate misses, but it is secondary analysis,
not the primary A/B result.

### 17.4 Treatment definition

Freeze both arms by file/tree, schema, card, prompt, model, and tool hashes.

- Arm A receives the current staged routing/loop/persistence/regrade/Pocinator guidance and existing
  narrative engagement records.
- Arm B receives the new structured event, finding revision, hypothesis, coverage, preflight,
  report-link, and full-funnel telemetry contracts.
- Both arms use the same safety rules, scope, evidence oracle, and final independent adjudication.
- The treatment must not include a stronger model, more target calls, hidden casebook answer, or
  different vulnerability card unless that is the separately registered experiment.

Roll out component experiments sequentially rather than a large factorial design:

1. state/evidence shell and resumability;
2. operator-prior/material-hypothesis persistence;
3. independent coverage/regrade/Pocinator routing;
4. telemetry-informed prompt/card candidates only after prior components qualify.

This makes any effect attributable and preserves Decision 0004's complexity budget.

### 17.5 Pre-registration

Before each cohort, freeze:

- inclusion/exclusion and contamination rules;
- target strata: domain, size, mode, expected difficulty, known-vulnerable/known-clean/unknown;
- primary and secondary endpoints;
- budget and timeout;
- allowed tools/actions and safety stops;
- root-cause deduplication rules;
- adjudication panel and tie resolution;
- missing/blocked-run treatment;
- minimum practically meaningful effect;
- sample-size/power calculation based on retrospective pilot variance;
- no-peeking rule and safety-only early-stop conditions.

Do not choose a fixed sample count before pilot variance and discordant-pair rates exist. A small pilot
may validate operations but must be labeled exploratory.

### 17.6 Endpoints

**Co-primary gates:**

1. rigor non-inferiority: no increase in independently rejected confirmed claims, false-discovery
   accepts, safety violations, or proof-package mismatch;
2. resolution benefit: improved confirmed root-cause recall on sealed vulnerable targets or improved
   decisive closure on sealed clean targets under matched budget.

**Secondary endpoints:**

- persistence recovery after initial rejection;
- regrade correction/narrowing and omitted-path recovery;
- valid `coverage_dry` rate;
- time/cost to resolved claim;
- complete-funnel selection and skip rationale;
- calibration quality where ex ante probabilities exist;
- human review burden;
- resume correctness after forced interruption;
- report claim-to-proof completeness.

Finding severity and external bounty outcome remain descriptive only.

### 17.7 Independent adjudication

All arm outputs go to the same cold adjudication process built from primary evidence. Reviewers are
blind to arm and do not see the competing arm first. A claim is scored only after:

- target/version and environment fidelity pass;
- mechanism/reachability/impact are atomized;
- controls and replay are checked;
- artifact proof is reviewed;
- disagreements are resolved and recorded.

Even Arm A output must pass this final common bar before it counts. This prevents a less rigorous arm
from appearing better merely by self-confirming more findings.

### 17.8 Safety and filing during the experiment

- Both arms inherit identical signed scope and root gates.
- Zone-2 remains fresh-human-confirmed; experimental assignment never authorizes it.
- Shared live targets are not used where one arm can affect the other or real users.
- Cleanup is reconciled before case closure.
- Potential real findings are quarantined from scorekeeping until operator review.
- Filing is operator-only and follows program authorship/disclosure rules.
- An A/B arm is never rewarded for filing quickly or maximizing severity.

### 17.9 Decision rule after A/B

Adopt a component only if it:

1. passes all safety/FDR/provenance hard gates;
2. demonstrates the preregistered useful effect or a justified non-inferiority/operational benefit;
3. survives fresh replay and holdouts;
4. does not rely on a target/card leakage artifact;
5. has an acceptable time/cost/human-review tradeoff;
6. removes or internalizes more complexity than it adds, or enforces an otherwise unenforceable
   invariant;
7. receives human-reviewed promotion under Decision 0004.

Otherwise retain it as telemetry, revise it as a bounded candidate, or remove it. Do not tune the
evaluator, labels, budgets, or holdouts to rescue the treatment. UCB/bandit routing remains deferred.

## 18. Rollout, compatibility, and rollback

### 18.1 Compatibility policy

- New engagements use version-3 records only after Slice B is green.
- Legacy engagements remain readable through explicit adapters/migration manifests.
- No historical artifact is rewritten to satisfy the new schema.
- Schemas reject unknown versions rather than guessing.
- Generated views include generator and source-ledger hashes.
- Old narrative progress remains a legacy artifact, not a competing current view.

### 18.2 Feature rollout

Use an engagement-level flag in the signed scope (the authoritative choice):

```text
record_kernel: legacy | decision-0005-v1
```

The flag selects record behavior only; it cannot relax safety. Start with hermetic fixtures, then one
new local/source engagement, then historical migration, then prospective A/B. Do not convert every
engagement at once.

### 18.3 Rollback

Rollback means stop appending new-version events, preserve all generated artifacts, and resume under
the prior record path with an explicit blocker/migration note. Never delete a partially written ledger
or rewrite it to look successful. A reducer/version bug blocks the engagement until repaired or an
operator approves a documented compatibility path.

## 19. Required implementation evidence

The accepted Decision 0005 plus the explicit implementation goal authorize this post-Phase-14 work;
that authorization does not enable any deferred controller, live-target action, or promotion power.
The experiment lifecycle command and engagement-record command are separate public surfaces: the first
owns candidate evaluation, while the second owns Plane-3 records. Neither may call itself through a
hidden duplicate authority path.

Every slice's completion report must include:

- exact files and schema versions changed;
- authority path added and prior ambiguity removed;
- valid/invalid fixtures introduced;
- tests and command output;
- migration/replay artifacts produced;
- known unresolved records and blocked environments;
- complexity added, deleted, or internalized;
- safety and secret-scan result;
- whether the result proves conformance, regression parity, or efficacy;
- `autonomous_gap_closure_count`, which remains unchanged unless Decision 0004's full criteria are
  independently satisfied.

## 20. Explicit deferrals

The architecture deliberately defers:

- autonomous live-target scheduling or action selection outside the current orchestrator/Hunter loop;
- automatic card, prompt, finding, severity, report, filing, memory, or Plane-1 promotion;
- a database/event service when append-only files and deterministic reduction suffice;
- concurrency beyond a demonstrated throughput wall and signed scope;
- bandit/UCB routing before qualified full-funnel denominators;
- a universal domain ontology;
- vendor-specific permanent model assignments;
- a sealed evaluator service until the live record kernel and retrospective evaluation are stable;
- interpreting mechanism/conformance tests as demonstrated real-world improvement.

The intended end state is not more machinery. It is a smaller number of unambiguous authority paths
around a model-directed research process that can be challenged, resumed, replayed, and measured.
