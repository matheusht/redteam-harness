# Post-Phase-14 Plan — Payload-Generation Capability Lane

**Status:** implementation plan — scoped, not yet built\
**Date:** 2026-06-28\
**Related:** `engine/capabilities.md`, `capabilities/registry.yaml`,
`docs/etrack-validation-status.md`,
`docs/decisions/0004-epistemic-autonomy-complexity-budget.md`

## Executive decision

Payload generation is **in product scope**, but it must not be folded into the existing E-track
sensor/converter keyhole. The current keyhole remains:

```text
external tool output = sensor or converter evidence
never oracle, never self-adjudication
```

Payload generators become a separate capability class with stricter gates:

```text
external.payload_generator
  -> proposes a candidate payload or artifact
  -> never executes it autonomously on a live target
  -> never judges whether it worked
  -> always requires explicit engagement authorization
```

This preserves the operator's authority to expand product scope while keeping Decision 0004 intact:
scope may expand deliberately; existing gates do not become stretchy.

## Why this exists

The elder-plinius tooling and similar red-team utilities contain useful payload-generation surfaces:
template generation, mutation, injection filenames, multimodal artifact construction, and chained
encoding/stego carriers. These can be valuable in authorized red-team work.

The risk is not that payload generation exists. The risk is letting it appear as a side effect of a
benign converter capability, where routing can accidentally escalate from "encode a harmless canary" to
"produce arbitrary payload material."

So the architecture needs a named lane.

## Capability classes

| Class | Purpose | Authority | Build status |
| --- | --- | --- | --- |
| `sensor` | Observe, decode, summarize, redact | none | existing E-track |
| `converter` | Transform a benign canary or evidence artifact | none | existing E-track |
| `payload_generator` | Propose candidate payloads/artifacts for an approved objective | none | this plan |
| `executor` | Execute a payload/action against a target | none; broker-mediated | future, review-required |
| `oracle` | Decide truth/success | broker/oracle only | external tools forbidden |

## Required gates for payload generators

Every payload-generator capability must require:

- `safe_signal` or an explicitly approved engagement objective.
- signed `scope.md`.
- `scope_allows_payload_generation: yes`.
- a declared payload class, such as `text_prompt`, `encoded_prompt`, `multimodal_artifact`,
  `stego_carrier`, `exploit_poc`, or `chain_candidate`.
- a containment plan.
- a cleanup/logging plan for any artifact that might persist.
- operator confirmation before any Zone-2 artifact or live target execution.
- oracle separation: generator output is a proposal, never a verdict.

## Explicit non-authorities

Payload generators must not:

- emit `confirmed`, `allow`, `verdict`, or `success`;
- mutate evaluator, scorer, gold labels, budgets, casebooks, or sealed data;
- auto-run live target actions;
- auto-promote Plane-1 changes;
- write raw secrets, auth material, or live target identifiers into Plane 1/2;
- weaken the existing `sensor_only` rule for E-track capabilities.

## Suggested registry shape

Do not add live adapters first. Start with the contract and negative fixtures.

```yaml
capability_classes:
  - id: payload_generator
    authority: proposal_only
    default: disabled
    requires:
      - signed_scope
      - scope_allows_payload_generation
      - declared_payload_class
      - containment_plan
      - oracle_separation
    forbidden_authority:
      - oracle
      - judge
      - verdict
      - confirmed
      - allow
```

Example future capability:

```yaml
- id: external.st3gg.embed_benign_canary
  class: payload_generator
  source: ST3GG
  license: AGPL-3.0
  integration: subprocess
  default: disabled
  authority: proposal_only
  allowed_actions: [embed_benign_canary, inspect_capacity]
  forbidden_actions: [jailbreak_templates, injector, conceal_agent, raw_payload_promotion]
  requires:
    - safe_signal
    - signed_scope
    - scope_allows_payload_generation
    - containment_plan
    - operator_review
  output: candidate artifact proposal + required controls
```

## Implementation phases

### PG-0 — contract-only lane

**Description:** Extend docs and conformance so the harness understands capability classes without
enabling runtime payload generation.

**Implementation surface:**

- `engine/capabilities.md`
- `capabilities/registry.yaml` or a small adjacent `capabilities/classes.yaml`
- `engagements/_TEMPLATE/scope.md`
- `tools/check-conformance.py`
- `fixtures/capabilities/_must_reject/`

**Acceptance:**

- Current sensor/converter entries still pass.
- Payload-generator class requires explicit scope flag and proposal-only authority.
- A payload generator claiming oracle/judge/verdict authority fails.
- A payload generator missing scope/containment/oracle-separation fields fails.
- Existing E-track dangerous actions remain forbidden in `sensor`/`converter`.
- Conformance green.

### PG-1 — negative fixture corpus

**Description:** Convert manual gate-bites into permanent `_must_reject` fixtures and add payload-lane
fixtures.

**Must reject:**

- `authority: oracle`
- unresolved `optional_capabilities`
- missing scope flag
- dangerous action in sensor/converter `allowed_actions`
- allowed/forbidden overlap
- payload generator without `scope_allows_payload_generation`
- payload generator without containment plan
- payload generator that emits/claims `confirmed`, `allow`, `verdict`, or `success`
- payload generator registered as default-enabled

**Acceptance:** CI fails if any malformed fixture is accepted.

### PG-2 — inert proposal artifact

**Description:** Add a schema for a payload proposal, but no external runtime adapter.

**Implementation surface:**

- `schemas/payload-proposal.schema.json`
- example fixture under `fixtures/payload-proposals/`

**Required fields:**

- objective id
- payload class
- benign or approved objective reference
- generator capability id
- proposed artifact metadata
- required controls
- containment plan
- cleanup plan
- non-authority attestation

**Acceptance:** valid example passes; malformed examples reject.

### PG-3 — first hermetic payload generator

**Description:** Only after PG-0 to PG-2 are green, add one hermetic generator that creates a benign
artifact against a fake target. Prefer ST3GG benign-canary embedding or a toy local generator.

**Acceptance:**

- no live target;
- no harmful payload corpus;
- broker/oracle owns the result;
- generated artifact is scoped to a temp/eval directory;
- cleanup verified;
- `autonomous_gap_closure_count` remains 0.

## Kill criteria

Stop or redesign if:

- the lane weakens existing sensor/converter restrictions;
- generator output starts acting like evidence of success;
- fixtures become broad enough to hide policy ambiguity;
- a live execution path appears before a brokered executor design exists;
- payload artifacts enter Plane 1/2 without redaction and containment.

## Non-goals

- No runtime executor in this slice.
- No automatic live target payload execution.
- No harmful-payload corpus.
- No external oracle/judge capability.
- No Plane-1 auto-promotion.

