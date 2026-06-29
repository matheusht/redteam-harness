# Tool Family Plan — P4RS3LT0NGV3

**Status:** phased adoption plan — no runtime build authorized\
**Date:** 2026-06-28\
**Source:** <https://github.com/elder-plinius/P4RS3LT0NGV3>\
**Reviewed commit:** `a6cb7c9`\
**License observed:** AGPL-3.0 — acceptable if deliberately adopted; not the primary architecture gate

## Fit summary

P4RS3LT0NGV3 is best treated as a **large transform catalog and decoder family**.

The repo is much more than a single obfuscation skill. It contains:

- a static web app with a tool registry and build-time templates;
- 222 advertised text transforms across case, cipher, concealment, encoding, format, SignWriting,
  symbol, technical, Unicode, and visual categories;
- a Python CLI wrapping a Node bridge for `list`, `inspect`, `encode`, `decode`, `preview`, and
  `auto-decode`;
- a natural-language `agent` planner;
- higher-risk UI tools such as prompt crafting, anticlassifier, tokenade, and fuzzing surfaces.

For our harness, P4 should be the **transform inventory and transform-strategy lab**. The first phases
use deterministic catalog actions. Later phases may adapt the upstream planner, promptcraft,
anticlassifier, tokenade, fuzzer, and random-chain surfaces as proposal/advisory modules, with brokered
evidence required before any claim.

## What should transfer

| Upstream area | Harness use |
| --- | --- |
| Python CLI + Node bridge | Strong candidate for external subprocess adapter |
| `list_transforms` / `inspect_transform` | Build a searchable transform catalog without loading all docs into model context |
| `encode` / `decode` / `auto-decode` | Converter and evidence actions for benign canaries |
| transform categories | Capability taxonomy and routing hints |
| decoder tool | Useful for evidence triage and redaction-friendly decode attempts |

## Advanced surfaces to adapt carefully

These are in scope for eventual adoption, but not as raw first-run tools:

- upstream `agent` natural-language planner;
- promptcraft;
- anticlassifier;
- tokenade;
- fuzzer;
- random mix / transform chains;
- unrestricted transform catalogs as governed datasets;
- deeper vendored/integrated source.

Each must graduate through the shared M0-M6 ladder in
`docs/tool-family-adapter-architecture.md`. The stable rule is that P4 may propose or transform; it does
not decide truth.

## Harness placement

```text
skills/techniques/obfuscation-encoding/
skills/techniques/covert-channel-encoding/
  -> optional family capability: external.p4.transform

tool-families/p4rs3lt0ngv3/
  FAMILY.md
  AGENT.md
  manifest.yaml
  fixtures/
  adapters/
```

## Proposed family actions

### Buildable first

- `list_transforms`
- `inspect_transform`
- `encode_benign`
- `decode_if_possible`
- `auto_decode_evidence`
- `transform_roundtrip`

### Advanced buildable actions

- `rank_transforms_for_defense_shape`
- `small_transform_set_for_card`
- `chain_benign_transforms`
- `promptcraft_proposal`
- `anticlassifier_proposal`
- `tokenade_proposal`
- `fuzzer_plan_proposal`
- `planner_advice`
- `bounded_random_chain`

### Permanently non-authoritative

- any action returning a final harness verdict;
- any action mutating evaluator/gold/budget/sealed data;
- any action executing a chain live without brokered executor authority.

## Phased implementation

**Advancement rule:** a phase earns the next phase only after its acceptance criteria are demonstrated
with a fixture/self-test/hermetic run, conformance is green, touched-file secret scan is clean, and the
phase report states what remains unproven. Advanced modules are in scope, but they must graduate through
the planned gates rather than appearing as raw tools.

### P0 — family profile and category map

**Description:** Create a harness-owned profile that inventories transform categories and maps them to
our technique cards.

**Implementation surface:**

- `tool-families/p4rs3lt0ngv3/FAMILY.md`
- `tool-families/p4rs3lt0ngv3/AGENT.md`
- `tool-families/p4rs3lt0ngv3/manifest.yaml`
- category map from upstream category to harness use

**Acceptance criteria:**

- reviewed commit and AGPL posture recorded;
- transform categories summarized without copying raw catalog text wholesale;
- advanced upstream tools named and assigned a blocked-until gate;
- `AGENT.md` instructs the model to request a specific bounded action, not browse the upstream app;
- conformance rejects advanced entries that lack `blocked_until`, risk tier, scope gates, or
  non-authority language.

### P1 — catalog-only adapter contract

**Description:** Build schema and fixtures for listing and inspecting transforms, without actually running
the external CLI yet.

**Implementation surface:**

- output schema for `list_transforms` and `inspect_transform`;
- fixture catalog with a small representative subset;
- negative fixtures for unknown transform, disallowed category, and verdict leakage.

**Acceptance criteria:**

- valid fixture passes;
- unknown/disallowed transform fails closed;
- no output can claim success/confirmed/verdict;
- agent can select from a compact manifest without loading the full transform list into context.

### P2 — external list/inspect adapter

**Description:** Wire a subprocess adapter to a user-installed P4 checkout/package for read-only catalog
actions.

**Implementation surface:**

- `tool-families/p4rs3lt0ngv3/adapters/p4_catalog_adapter.*`;
- external path/package config;
- command timeout and output-size bounds.

**Acceptance criteria:**

- missing Node/external install returns honest non-success;
- `list_transforms` and `inspect_transform` produce schema-valid output;
- adapter cannot run encode/decode yet;
- no source vendored by accident; if deeper integration is approved, source is isolated and still
  subordinate to the manifest/broker/oracle boundary.

### P3 — bounded encode/decode converter

**Description:** Expose transform execution for benign canaries only.

**Implementation surface:**

- `encode_benign`;
- `decode_if_possible`;
- `auto_decode_evidence`;
- roundtrip fixture corpus.

**Acceptance criteria:**

- only approved transform ids from the manifest run;
- plaintext, transformed canary, negative control, and replay are required by the card/oracle;
- adapter writes only redacted artifacts;
- auto-decode evidence is advisory and cannot confirm impact.

### P4 — transform ranking as advisory memory

**Description:** Use hermetic targets to measure which transform families survive which normalizers. This
is advisory routing memory, not an optimizer verdict.

**Implementation surface:**

- append-only transform outcome ledger;
- defense-shape fixtures such as `nfkc`, `zero_width_strip`, `confusable_skeleton`, `html_escape`;
- ranking helper returns "try next" suggestions.

**Acceptance criteria:**

- rankings cannot change oracle verdicts;
- disabling memory changes no finding outcomes;
- every ranking row has controls and a defense shape;
- no model claim is accepted without broker evidence.

### P5 — small transform-chain proposals

**Description:** Later, allow bounded chains as payload proposals for authorized benign objectives.

**Implementation surface:**

- payload proposal schema extension for transform chains;
- max chain length, max expansion, reversible-only flag;
- operator review if risk tier exceeds benign.

**Acceptance criteria:**

- chain proposals are never executed live without brokered execution design;
- chain must include decode/roundtrip evidence;
- random chains are allowed only when seeded, bounded, reversible/inspectable where possible, and tied
  to a declared objective;
- `autonomous_gap_closure_count` remains 0 unless a real broker/oracle run later confirms a gap.

### P6 — promptcraft / anticlassifier / tokenade as proposal modules

**Description:** Adapt the higher-risk upstream tools as `payload_generator` actions. They create
candidate artifacts or strategy notes for authorized objectives; they do not execute and do not judge.

**Implementation surface:**

- `promptcraft_proposal`;
- `anticlassifier_proposal`;
- `tokenade_proposal`;
- proposal schema fields for transform family, risk tier, intended control, containment, and cleanup;
- `_must_reject` fixtures for missing scope, verdict leakage, raw secret inclusion, and budget
  explosion.

**Acceptance criteria:**

- every proposal is linked to a signed scope objective or hermetic benchmark objective;
- proposals carry required controls and replay plan;
- no proposal is live-executed in this phase;
- conformance rejects proposals that claim success or include raw sensitive data;
- output size and transform expansion are bounded.

### P7 — fuzzer and random-chain lab

**Description:** Adapt fuzzing/random-mix behavior as a hermetic transform-search lab, not an autonomous
live attack loop.

**Implementation surface:**

- `fuzzer_plan_proposal`;
- `bounded_random_chain`;
- fixed seed, max chain length, max expansion, max candidates, and deterministic replay;
- hermetic normalizer/decoder targets.

**Acceptance criteria:**

- repeated run with same seed is deterministic;
- fuzzer cannot choose its own oracle or budget;
- every candidate has plaintext and negative controls;
- duplicate or non-reversible candidates do not count as new coverage unless the oracle says so;
- results update advisory transform memory only.

### P8 — upstream `agent` planner as advisory selector

**Description:** Expose P4's natural-language planner as an advisory selector that proposes transform
plans. The harness deterministic selector remains the control.

**Implementation surface:**

- `planner_advice`;
- strict plan schema;
- comparison against deterministic baseline;
- no execution inside the planner action.

**Acceptance criteria:**

- planner output must be schema-valid before any transform runs;
- planner cannot access gold/evaluator/sealed data;
- planner cannot execute transforms directly;
- planner advice is ignored if it increases invalid accepts or budget without coverage;
- deterministic baseline remains available and measurable.

### P9 — scoped live transform campaign

**Description:** Run one approved advanced P4 module in a signed engagement slice after P6-P8 pass.

**Implementation surface:**

- scope-as-code with allowed transform classes and payload classes;
- one objective, one module family, fixed budget;
- brokered controls, replay, cleanup, evidence bundle.

**Acceptance criteria:**

- no scope/no run;
- no chain exceeds declared bounds;
- live result is evidence-only until oracle adjudication;
- human/operator review remains required for persistent or Zone-2 artifacts.

## Worked example

1. Routing sees that a target may filter exact keywords before semantic interpretation.
2. The active card asks P4 for `list_transforms` in approved categories only.
3. The orchestrator chooses `base64` and one Unicode transform because the defense shape is normalization.
4. Adapter emits transformed benign canaries and roundtrip evidence.
5. Broker runs plaintext, transformed, negative control, and replay.
6. Oracle adjudicates based on target responses, not transform existence.

## Open questions for approval

- Should P4's `auto-decode` be available during live engagements, or only offline against artifacts?
- Should transform chains be capped at length 2 first?
- Should high-expansion transforms default to `probe` unless a budget-specific scope explicitly allows
  them?
