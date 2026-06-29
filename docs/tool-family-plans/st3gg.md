# Tool Family Plan — ST3GG

**Status:** phased adoption plan — no runtime build authorized\
**Date:** 2026-06-28\
**Source:** <https://github.com/elder-plinius/ST3GG>\
**Reviewed commit:** `35f8b2b`\
**License observed:** AGPL-3.0 — acceptable if deliberately adopted; not the primary architecture gate

## Fit summary

ST3GG is best treated as a **multimodal steganography detection and controlled benign-artifact family**.

The repo is broad:

- Python steganography core for image embedding/decoding/capacity/detection;
- analysis functions for image, text, document, archive, network, and code artifacts;
- a subprocess-friendly JSON CLI (`stegg_cli.py`);
- richer TUI/web/UI surfaces;
- examples across many file formats;
- injection/template features that are high-risk for our harness and must remain gated.

For our harness, ST3GG should enter through **detection first**, then benign-canary embedding in
hermetic labs, then higher-risk payload-generation and executor paths once they pass the shared
graduation ladder. The end state can cover the whole toolkit; the authority still comes from the
manifest, broker, and oracle.

## What should transfer

| Upstream area | Harness use |
| --- | --- |
| `stegg_cli.py` JSON CLI | Strong candidate for external subprocess adapter |
| `analysis_tools.py` registry | Detection/sensor actions over files and text artifacts |
| Unicode stego detectors | Evidence for hidden prompt/content channels |
| image capacity/detect/decode | Hermetic benign-canary carrier tests |
| file-type detection | Artifact triage before specialized analysis |

## Advanced surfaces to adapt carefully

These are in scope for eventual adoption, but not as raw first-run tools:

- injector and template actions;
- raw payload extraction;
- conceal/agent modes;
- arbitrary embedding;
- multi-layer or encrypted stealth modes;
- network covert-channel simulation;
- live executor behavior.

Each must graduate through the shared M0-M6 ladder in
`docs/tool-family-adapter-architecture.md`. The stable rule is that ST3GG may detect, propose, embed, or
execute only through its assigned capability class; it never decides truth.

## Harness placement

```text
skills/techniques/steganography/
skills/patterns/indirect-prompt-injection/
skills/techniques/covert-channel-encoding/
  -> optional family capability: external.st3gg.detect

tool-families/st3gg/
  FAMILY.md
  AGENT.md
  manifest.yaml
  fixtures/
  adapters/
```

## Proposed family actions

### Buildable first

- `detect_file_type`
- `analyze_file`
- `detect_unicode_steg`
- `summarize_findings`
- `capacity_inspect`

### Advanced buildable actions

- `decode_canary_if_present`
- `embed_benign_canary`
- `roundtrip_benign_carrier`
- `artifact_digest_for_evidence`
- `extract_payload_redacted`
- `injector_template_proposal`
- `conceal_artifact_proposal`
- `network_channel_simulation`
- `multi_layer_carrier_lab`
- `brokered_live_embed`

### Permanently non-authoritative

- any action returning a final harness verdict;
- any action mutating evaluator/gold/budget/sealed data;
- any action storing raw decoded secrets into Plane 1/2.

## Phased implementation

**Advancement rule:** a phase earns the next phase only after its acceptance criteria are demonstrated
with a fixture/self-test/hermetic run, conformance is green, touched-file secret scan is clean, and the
phase report states what remains unproven. Advanced modules are in scope, but raw extraction,
embedding, concealment, and live execution must graduate through evidence-producing gates.

### S0 — family profile and detection-first AGENT.md

**Description:** Create the harness-owned family profile and quickstart that makes detection the default
path.

**Implementation surface:**

- `tool-families/st3gg/FAMILY.md`
- `tool-families/st3gg/AGENT.md`
- `tool-families/st3gg/manifest.yaml`

**Acceptance criteria:**

- reviewed commit and AGPL posture recorded;
- high-risk upstream surfaces are listed with blocked-until gates, not erased from scope;
- `AGENT.md` says raw extracted payloads are not stored in Plane 1/2;
- conformance rejects injector/templates/conceal entries that lack `blocked_until`, risk tier, scope
  gates, redaction rules, or non-authority language.

### S1 — detection manifest fixtures

**Description:** Add static fixtures for detection results and failure modes before runtime integration.

**Implementation surface:**

- valid `artifact_digest.json` fixture;
- `_must_reject` fixtures for raw payload leakage, verdict fields, missing redaction, and premature
  advanced-action exposure.

**Acceptance criteria:**

- valid digest passes;
- digest with raw payload fails;
- digest with `confirmed`/`success`/`verdict` fails;
- missing redaction metadata fails.

### S2 — external detection adapter

**Description:** Wire a subprocess adapter to user-installed ST3GG for read-only detection actions.

**Implementation surface:**

- `tool-families/st3gg/adapters/st3gg_detect_adapter.*`;
- external command/path config;
- bounded file size and timeout;
- temp directory isolation.

**Acceptance criteria:**

- missing install returns honest non-success;
- `detect_file_type`, `detect_unicode_steg`, and `analyze_file` emit schema-valid redacted digests;
- no raw decoded payload is written unless it is a benign canary match or a hashed/redacted reference;
- adapter cleans temp files.

### S3 — hermetic benign-canary embedding

**Description:** Add a payload-generator action for local fake targets only: embed a known benign canary in
a generated/local carrier, then verify roundtrip.

**Implementation surface:**

- `external.st3gg.embed_benign_canary` as `payload_generator`;
- carrier fixtures in `evals/hermetic/`;
- ledger entry with proposal id, artifact hash, cleanup path, and oracle controls.

**Acceptance criteria:**

- no live target;
- no arbitrary payload;
- generated artifact remains in temp/eval dir;
- roundtrip and cleanup are verified;
- proposal does not act as verdict;
- single run cannot confirm a finding.

### S4 — brokered engagement dry-run

**Description:** Run a signed local/hermetic engagement where ST3GG generates or detects a benign canary
artifact and the broker/oracle adjudicates.

**Implementation surface:**

- `engagements/<hermetic-id>/scope.md` with `scope_allows_payload_generation: yes`;
- payload proposal ledger;
- brokered probe against a local fake/guarded model or artifact processor.

**Acceptance criteria:**

- scope is signed and local/hermetic;
- operator-review checkpoint is recorded before execution;
- attempt/finding ledger distinguishes proposal, execution, and verdict;
- cleanup ledger has no dangling artifacts;
- `autonomous_gap_closure_count` remains 0 unless a real authorized target later produces a brokered
  confirmed gap.

### S5 — redacted decode and extraction lane

**Description:** Allow controlled extraction from suspected stego artifacts without leaking raw payloads
into Plane 1/2.

**Implementation surface:**

- `extract_payload_redacted`;
- hash-only output mode;
- canary-match output mode;
- operator-secured raw-export path for explicitly scoped cases;
- `_must_reject` fixtures for raw secret storage and verdict leakage.

**Acceptance criteria:**

- default output is hash/canary boolean, not raw extracted text;
- raw export requires signed scope, risk tier, containment, and cleanup;
- extraction result remains evidence only;
- disabling extraction changes no oracle rule.

### S6 — injector/templates/conceal as proposal modules

**Description:** Adapt injector/template/conceal surfaces as `payload_generator` actions. They propose
candidate artifacts for approved objectives; they do not execute live or judge impact.

**Implementation surface:**

- `injector_template_proposal`;
- `conceal_artifact_proposal`;
- proposal schema extensions for carrier type, payload class, risk tier, containment, and expected
  controls;
- hermetic fixtures only.

**Acceptance criteria:**

- every proposal has signed/hermetic objective, containment, cleanup, and controls;
- no proposal includes raw live secrets;
- no proposal is automatically executed;
- generated artifacts are temp/eval scoped and cleanup-verified;
- proposal output cannot include final verdict fields.

### S7 — network and multi-layer stego hermetic lab

**Description:** Adapt network covert-channel and multi-layer carrier capabilities as local simulations
first.

**Implementation surface:**

- `network_channel_simulation`;
- `multi_layer_carrier_lab`;
- synthetic PCAP/archive/image fixtures;
- broker event logs for embed, detect, decode, and cleanup.

**Acceptance criteria:**

- no external network traffic;
- deterministic synthetic artifacts;
- detector and decoder evidence are recorded separately;
- false-positive controls included;
- single run cannot confirm a vulnerability.

### S8 — brokered engagement dry-run for advanced modules

**Description:** Run one advanced ST3GG proposal module in a signed local/hermetic engagement, then
broker/oracle adjudicates.

**Implementation surface:**

- `engagements/<hermetic-id>/scope.md` with explicit advanced-module permission;
- payload proposal ledger;
- brokered probe against a local fake/guarded processor.

**Acceptance criteria:**

- scope is signed and local/hermetic;
- operator-review checkpoint is recorded before execution;
- attempt/finding ledger distinguishes proposal, execution, and verdict;
- cleanup ledger has no dangling artifacts;
- `autonomous_gap_closure_count` remains 0 unless a real authorized target later produces a brokered
  confirmed gap.

### S9 — live-capable executor lane

**Description:** After S0-S8 pass, expose live execution support for approved engagement objectives under
the brokered executor class.

**Implementation surface:**

- executor capability class;
- scope-as-code;
- OS isolation/remote service;
- strict artifact containment;
- human confirmation for Zone-2 or persistent artifacts.

**Acceptance criteria:**

- no executor can run without signed scope and broker mediation;
- every live artifact has cleanup and impact bounds;
- extracted data is redacted at capture;
- external tool remains non-authoritative.

## Worked example

1. An engagement includes a model-generated image artifact.
2. Routing activates steganography/indirect-prompt-injection concern.
3. Orchestrator reads `tool-families/st3gg/AGENT.md`.
4. Manifest permits `analyze_file`, not embedding.
5. Adapter emits a redacted digest:
   file type, detector ids, suspicious indicators, confidence, raw-payload-present boolean, hashes.
6. Oracle uses that as evidence for "hidden channel suspected," but does not claim model impact.
7. If decode is needed, a second gate decides whether to extract only canary-matched/redacted content.

## Open questions for approval

- Should first runtime integration be text/Unicode-only before image analysis?
- Should decoded payloads default to hash-only unless a benign canary matches, with raw export reserved
  for explicitly scoped evidence handling?
- Should benign embedding use a generated carrier only, or allow operator-supplied local carriers?
