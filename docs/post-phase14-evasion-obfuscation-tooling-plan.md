# Post-Phase-14 Plan — Adversarial-Input Tooling (encoding · obfuscation · steganography · covert-channel)

**Status:** draft for review — **NOT build permission, scope decision pending**\
**Date:** 2026-06-27\
**Relates to:** [Decision 0004](decisions/0004-epistemic-autonomy-complexity-budget.md),
[Decision 0001](decisions/0001-casebooks-patterns-routing.md),
`docs/post-phase14-capability-fit-review.md`, README "Scope fence", AGENTS.md §1 hard gates.\
**Does not authorize:** any change to the `safe_signal` load-gate, the scope fence, or evaluator truth;
any stored harmful-payload corpus; any harm-elicitation self-learning objective.

> This plan adds a **technique family** (adversarial-input transforms) to the existing
> `technique × vuln × benign-objective × oracle` model. It is the evasion-**robustness** testing
> capability — "does the target's safety/monitoring pipeline resist encoded / obfuscated / hidden
> inputs?" — not a harm-production capability. Read the Scope Decision before anything else.

---

## 1. Objective

Make the harness able to test, in authorized engagements, whether a target's safety and monitoring
controls are robust to **non-plaintext adversarial inputs**: encoded/ciphered text, Unicode/emoji
obfuscation, image/audio/document steganography, and tokenizer-blind-spot covert channels. The harness
should **adapt per engagement** by learning which *transform shapes* move which *defense shapes* —
abstract methodology, not a payload stockpile.

This is the same posture as the convergent prior art the architecture already cites (PyRIT converters,
garak encoding/jailbreak probes): attack *techniques* are means; the product is a **robustness verdict**.

## 2. Candidate tools (verified read-only, 2026-06-27)

| Tool | What it actually is (verified) | License | Role here |
| --- | --- | --- | --- |
| **P4RS3LT0NGV3** (`elder-plinius/P4RS3LT0NGV3`) | 222 text transforms — ciphers, base64/hex, Unicode styling, invisible-Unicode/emoji stego, prompt-mutation; Vue static site + **Python CLI** (`p4rs3lt0ngv3_cli/`) | AGPL-3.0 | Encoding/obfuscation **converter** layer |
| **ST3GG** (`elder-plinius/ST3GG`) | Steganography suite — embed/extract in images/audio/docs, AES-256-GCM, **+ 20+ detectors / 50+ analysis tools**; Python core (`steg_core.py`, `analysis_tools.py`, `cli.py`) | AGPL-3.0 | Multimodal stego **technique** + **defensive detector** |
| **GLOSSOPETRAE** (`elder-plinius/GLOSSOPETRAE`) | Conlang generator + tokenizer-blind-spot / covert-channel **research framework**; offense modules (SemanticStego, TokenExploiter); JS engine | AGPL-3.0 | Covert-channel **technique** + traffic-decode **evidence** (native Tollbooth support) |

All three are **transform/stego/research tooling**, *not* curated harmful-content jailbreak corpora.

## 3. Scope Decision (the load-bearing part)

### In scope — will build

1. **Adversarial-input transforms as technique tooling.** Wrap the tools' encoders/codecs/stego
   functions as a converter layer used by new `skills/techniques/` cards. Transforms are content-neutral
   (a base64 encoder is not harm).
2. **Benign-objective probes only.** Every probe composes a transform with a **benign win condition**
   under the existing `safe_signal` gate — e.g. "does the target decode-and-act on an *encoded benign
   canary* (reveal a canary token / flip a refusal on a harmless target / leak its own system prompt)
   that its plaintext guard would refuse?" The oracle adjudicates boundary movement.
3. **Defensive detection.** ST3GG's analysis side and GLOSSOPETRAE's decode side are used to *detect*
   hidden data (in target outputs, in observed traffic via Tollbooth) for evidence bundles.
4. **Abstract technique patterns + adaptive memory.** A memory of *which transform shape moved which
   defense shape* (sanitized, like existing pattern cards), so the harness adapts per engagement. This
   is the sanctioned self-improvement: optimize **technique cards** against **benign/hermetic
   evaluators**.

### Out of scope — will not build (README ❌ Never zone + Decision 0004)

1. **No stored library of working *harmful-content* jailbreaks**; no wholesale ingestion of harm corpora.
   (Transforms/codecs yes; a harm-payload arsenal no.)
2. **No self-learning loop whose objective/metric is harm-elicitation success.** Reward is benign-canary
   boundary movement / evasion-detection, never harmful-content production.
3. **No deletion or weakening of the `safe_signal` load-gate or the scope fence.** We *extend* the
   technique taxonomy on top of the gate; we do not remove the benign-objective requirement.

### Why this keeps full engagement capability

Per-engagement adaptability comes from (a) the transform toolbox, (b) abstract technique patterns,
(c) memory of technique-vs-defense shapes — all in scope. The two out-of-scope items add legal/ethical
liability and destroy the project's product (rigor, defensibility, shareability) **without** improving
authorized-testing capability.

## 4. Placement in the architecture

```text
skills/techniques/
  obfuscation-encoding/      # P4RS3LT0NGV3 transforms — benign-canary objective, oracle-judged
  multimodal-steganography/  # ST3GG embed (probe) + detect (defense)
  covert-channel-tokenizer/  # GLOSSOPETRAE tokenizer blind spots / semantic stego

engine/                      # routing: which transform family activates on which recon signal
tools/                       # arms-length CLI wrappers (AGPL: external, not vendored into Plane 1/2)
casebooks/ + memory/         # sanitized technique-vs-defense outcomes (no payloads, no secrets)
```

- Each technique card carries `activation` signals (e.g. "target accepts/echoes base64", "multimodal
  input surface", "model-swap selector") and routes to a benign vuln objective + oracle.
- **AGPL containment:** wrap each tool's CLI as an external adapter invoked by subprocess; do not vendor
  or link AGPL code into the portable harness. Same posture as Tollbooth. License review before any
  distribution.
- **Tollbooth synergy:** GLOSSOPETRAE decode in Tollbooth = surface hidden/covert data in observed
  traffic → redacted digest → evidence bundle. Defensive use of the integration.

## 5. Spike phases (each gated, PR-only, never merged without tests)

- **E0 — characterize + license.** Confirm contents/CLIs hands-on; record AGPL obligations and the
  arms-length boundary. No vendoring.
- **E1 — one converter, one card.** P4RS3LT0NGV3 encoder → `obfuscation-encoding` technique card →
  benign-canary probe on a hermetic fake-model target. Oracle adjudicates. Proves the
  transform→technique→benign-objective→verdict loop end-to-end.
- **E2 — stego technique + detector.** ST3GG embed (benign canary in an image) against a hermetic
  multimodal target; ST3GG detector on the evidence side.
- **E3 — covert channel + evidence.** GLOSSOPETRAE tokenizer/semantic-stego technique; wire decode into
  the Tollbooth evidence path (if Tollbooth spike landed).
- **E4 — adaptive technique memory.** Record sanitized technique-vs-defense outcomes; let routing adapt.
  Optimize technique cards against benign/hermetic evaluators only.

## 6. Acceptance criteria (per spike)

- Every probe has a benign win condition; **no card loads without `safe_signal`** (existing gate holds).
- Oracle + controls + replay still required for any `confirmed`; no LLM/tool output overrides the oracle.
- Conformance + secret scan green; **no secrets and no harmful-content payloads** in any plane.
- AGPL boundary respected (external/subprocess; nothing vendored/linked); license note recorded.
- Memory stores sanitized technique-vs-defense methodology only — firewall test: disabling it changes
  no verdict.

## 7. Kill criteria

- A card requires a non-benign objective to be useful → drop it (it's outside the fence).
- The "memory" trends toward storing reusable harmful payloads → stop; it has become the arsenal.
- AGPL boundary can't be kept arms-length for a portable harness → don't vendor.

## 8. Open items for operator review

1. **Confirm the Scope Decision (§3).** This plan is built on "extend the taxonomy, keep the benign-
   objective gate." If the intent is instead a harmful-payload arsenal / harm-elicitation optimizer,
   that is out of scope for this plan and for what will be built.
2. Priority of E-track vs. the AIWG-index / memory / Tollbooth tracks in
   `docs/post-phase14-capability-fit-review.md`.
3. Whether the adaptive technique memory rides the same sanitized retrieval substrate as the casebook
   memory layer (recommended) or a separate store.

---

**Review-only.** Nothing here is built yet. The in/out scope decision in §3 is the precondition for any
E-track work. This document is the durable reference for that decision.
