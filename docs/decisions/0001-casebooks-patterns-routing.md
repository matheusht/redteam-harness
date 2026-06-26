# Decision 0001 — Casebooks, pattern cards, and recon routing

**Status:** accepted as product direction; implementation still pending  
**Date:** 2026-06-23  
**Related:** `docs/architecture.md`, `docs/autoresearch-evaluation-rfc.html`, `docs/field-notes.md`

## Decision

The harness will grow a first-class routing layer between recon and vuln/technique cards.

The routing layer is built from three artifacts:

1. **Casebooks** — sanitized end-to-end engagement stories used to evaluate and teach the
   harness's reasoning, not raw target dumps.
2. **Pattern cards** — reusable, target-agnostic hunting heuristics promoted from one or more
   engagements.
3. **Activation signals** — observations from recon that suggest which pattern/vuln cards deserve
   attention.

The intent is a structured-but-not-rigid red-team harness:

```text
recon
  → activation signals light up
  → pattern/vuln cards suggest hypotheses
  → orchestrator reasons and chooses probes
  → oracles adjudicate evidence
  → only proven lessons promote back into the harness
```

Signals guide the orchestrator; they do not bind it. Hard gates remain hard. Hunting judgment remains
alive.

## Why this exists

The first serious B2B assessment produced high-value findings mostly outside a narrow prompt-attack
loop:

- a cross-tenant chat IDOR from a trusted `chatOwnerId`;
- a model-policy bypass from a trusted `modelAi`;
- a Deep Research tool-policy bypass from trusted `mandatoryTools`;
- refuted candidates and held defenses that were just as important for calibration.

The reusable lesson was not "try this exact endpoint." It was:

> Client-supplied selectors that choose owner, tenant, actor, capability, model, tool, or policy
> context are dangerous unless the server resolves authorization from the authenticated caller.

That lesson is broader than one target and narrower than a generic OWASP category. It belongs in a
pattern card.

## Product choices

### 1. Patterns are harness-level, not engagement-local

Engagements may create **pattern candidates**. The standalone harness only receives generalized,
scrubbed, manually promoted pattern cards.

Engagement-local candidate:

> In this target, `chatOwnerId`, `modelAi`, and `mandatoryTools` were all client-controlled fields
> trusted by the backend.

Harness-level pattern:

> Client-supplied selector controls authorization scope or capability selection.

This prevents overfitting to one architecture while preserving the reasoning that found the bug.

### 2. Casebooks preserve E2E learning without copying raw engagements

Do not wholesale-copy live engagement folders into this portable repo. They may contain target
details, credentials, live links, screenshots, signed URLs, or cleanup state that should remain in
Plane 3.

Instead, import a sanitized casebook:

```text
casebooks/<case-id>/
  case.yml              # metadata, scope shape, target class, allowed surfaces
  recon-signals.yml     # observations that should have activated cards
  hypotheses.yml        # candidate hypotheses and why they were/weren't pursued
  oracle-matrix.json    # controls, expected outcomes, confirmed/refuted verdicts
  lessons.md            # generalized lessons and non-findings
  promotion-notes.md    # what, if anything, was promoted to Plane 1
```

Casebooks are evidence-shaped memories. They are not exploit libraries.

### 3. Raw sources feed a staging pipeline

Raw sources can include:

- completed engagements in target repos;
- sanitized reports;
- field notes;
- public research writeups;
- OWASP/MITRE/CWE pages;
- internal wiki pages;
- candidate lessons produced by autoresearch.

All raw sources enter a staging inbox first:

```text
raw source
  → source inventory
  → redaction/scope check
  → extract casebook or candidate lesson
  → map activation signals
  → define oracle requirements
  → human promotion review
  → pattern/vuln/technique card update
```

Nothing from ingestion writes directly to loadable Plane-1 cards.

### 4. Volume is treated as a failure mode

The harness should not become a large prompt dump. New cards should earn their place.

A pattern card is promoted only if it is:

- target-agnostic;
- backed by at least one strong casebook or multiple weaker independent cases;
- tied to observable recon signals;
- paired with suggested probes and counterexamples;
- compatible with `safe_signal` and scope gates;
- useful for prioritization, not just descriptive.

If a lesson is interesting but not yet reusable, keep it in `docs/field-notes.md` or a casebook.

### 5. Strict gates, flexible reasoning

The flow is intentionally not 100% strict.

Hard gates:

- signed scope before live runs;
- benign `safe_signal` before loading vuln cards;
- no Zone-2 artifact without explicit human confirmation;
- redaction;
- cleanup ledger;
- oracle requirements before `confirmed`;
- manual promotion into Plane 1.

Flexible areas:

- which activated cards to pursue first;
- whether to ignore a weak signal;
- when to spawn helper/hunter agents;
- when to create a new local hypothesis;
- when to stop a line as dry;
- when to write a pattern candidate.

The orchestrator should be guided by the harness, not replaced by it.

## Intended flow

### During an engagement

1. Read `scope.md`, recon notes, and prior field notes.
2. Collect recon observations as structured signals.
3. Match signals against pattern/vuln card activation rules.
4. Let the orchestrator select a small number of high-leverage probes.
5. Run probes through the existing attempt/finding/oracle discipline.
6. Record local pattern candidates when a repeated shape appears.
7. Keep cleanup and redaction current.
8. At the end, decide which lessons are eligible for casebook import.

### After an engagement

1. Create or update a sanitized casebook.
2. Extract candidate pattern cards from confirmed findings and strong refutations.
3. Keep target-specific details out of reusable cards.
4. Promote only through human review.
5. Add evaluator examples for both true positives and false positives.

### During autoresearch

Casebooks can be used to test and improve:

- recon summarization;
- activation-signal extraction;
- card routing;
- oracle completeness;
- false-positive rejection;
- evidence-bundle quality.

Casebooks should not be treated as proof that an arbitrary new technique is better. Per the
autoresearch RFC, technique efficacy requires frozen, synthetic, hermetic, or sealed benchmark
targets.

## First pattern-card candidates

Start small. A useful initial set:

### `client-supplied-selector-authz`

Strong signals:

- request contains fields like `ownerId`, `userId`, `companyId`, `teamId`, `tenantId`, `chatOwnerId`,
  `adminView`, `scope`, `resourceUserId`;
- request contains capability selectors like `modelAi`, `mandatoryTools`, `toolName`, `imageModel`,
  `integrationSlug`;
- UI hides a capability, but the API still accepts its identifier;
- same operation has safe and unsafe variants.

Suggested probes:

- self vs other-owner matrix;
- no-selector negative control;
- bogus-selector negative control;
- safe sibling endpoint differential;
- same-company vs cross-company control when authorized.

Counterexamples:

- selector is only a display hint;
- server ignores selector and resolves from session;
- selector is allowed only for same-company admin and properly checked;
- endpoint returns public/shared data by design.

### `legacy-route-differential`

Strong signals:

- `/v1` and `/v2` routes coexist;
- frontend uses one version while older version remains reachable;
- duplicated data-access utilities exist;
- one route has an authorization guard the other lacks.

Suggested probes:

- identical request against both versions;
- compare status, body shape, and authorization failure mode;
- confirm current frontend route does not imply old route is safe.

### `ui-only-policy-enforcement`

Strong signals:

- admin settings hide or restrict a capability in the UI;
- client receives policy object;
- stream/API request still accepts raw capability names;
- invalid identifiers are rejected but disallowed valid identifiers are accepted.

Suggested probes:

- allowed capability positive control;
- disallowed valid capability test;
- bogus capability negative control;
- live policy re-read to rule out stale cache;
- replay after fresh session.

### `transitive-sanitizer-reliance`

Strong signals:

- rendered output flows through `dangerouslySetInnerHTML` or equivalent;
- code comment claims sanitization but no local sanitizer is visible;
- library configuration weakens safety posture;
- public/shared render path exists.

Suggested probes:

- DOM marker first;
- execution oracle second;
- shared/rendered path third;
- no token exfiltration without Zone-2 confirmation.

Counterexample:

- library's internal sanitizer blocks execution. Keep as defense-in-depth, not confirmed XSS.

## Activation schema sketch

Pattern and vuln cards should eventually expose a small routing block:

```yaml
activation:
  strong_signals:
    - client field selects owner or tenant scope
    - v1/v2 route differential exists
  weak_signals:
    - client-side route gate observed
    - policy object visible to seat
  negative_signals:
    - endpoint ignores supplied selector
    - selector is demonstrably public/shared by design
  suggested_probes:
    - self_vs_other_owner_matrix
    - bogus_selector_negative_control
    - safe_sibling_endpoint_differential
  oracle:
    requires:
      - positive_control
      - negative_control
      - replay
      - one_sentence_why_real
```

This block is a routing aid, not an execution script.

## What not to do

- Do not let public wiki ingestion create cards directly.
- Do not turn every one-off lesson into a pattern card.
- Do not store raw client secrets, signed URLs, bearer tokens, passwords, or live evidence links in
  casebooks.
- Do not optimize autonomous techniques against live engagements.
- Do not let LLM judges override mechanical oracle failures.
- Do not make activation signals mandatory checklists that suppress orchestrator judgment.

## Open implementation questions

- Exact schemas for `case.yml`, `recon-signals.yml`, and card `activation` blocks.
- Whether casebooks live under `casebooks/` or `docs/casebooks/`.
- Whether pattern candidates live in engagement repos as `pattern-candidates.md` or in a structured
  `patterns/` subfolder.
- How much source-code context can be retained in a sanitized casebook without leaking target IP.
- How to sign casebook imports so autoresearch can detect tampering.

## Near-term implementation plan

1. Add `skills/patterns/` with 3–5 initial pattern cards.
2. Add a minimal casebook schema and import the B2B assessment as the first sanitized casebook.
3. Add optional `activation` front matter to pattern/vuln cards.
4. Update the orchestrator runbook: recon must emit activation signals before selecting cards.
5. Add evaluator tests that verify the B2B casebook activates the right patterns while preserving
   the F3 false-positive refutation.

## Final product stance

The harness should make the agent harder to fool and easier to aim.

It should not remove judgment. It should give judgment better handles.
