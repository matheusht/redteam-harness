# E-track validation status (honest ledger)

**Review-only.** This records *what has actually been validated* for the E-track, and — per the prime
directive — what has **not**. Green self-tests prove *mechanism*, never *efficacy*; the oracle/broker
remain authoritative. `autonomous_gap_closure_count` = **0** (nothing here closes a gap; these are
tooling / sensors / fixtures).

## How things were validated

- **Hermetic self-tests** — each tool has `--self-test` exercising round-trip / detection / redaction.
- **Negative "gate-bites" tests** — for each conformance gate, a deliberate violation was injected and
  confirmed to FAIL, then reverted (a gate only ever seen pass is not validated). **Currently these are
  manual/ephemeral, not yet permanent CI fixtures — see Known limits.**
- **One live integration run** — Tollbooth stood up as an unmodified container, redaction validated on a
  real export, torn down.
- **One rung-1 model run** — obfuscation-encoding vs a guarded local model (qwen3-8b).

## Component status

| Component | Validated (how) | Status |
| --- | --- | --- |
| E1 obfuscation-converter | round-trip self-test | mechanism **proven**; efficacy **UNPROVEN** (rung-1: inert on 8B model — decode-fidelity confound) |
| E2 stego-converter + detector | embed/extract/detect self-test | mechanism **proven**; efficacy **unproven** |
| E3 covert-channel-converter | round-trip self-test (3 channels) | mechanism **proven**; efficacy **unproven** |
| E3 decode-evidence scanner | golden self-test (sanitized, no raw payload) | mechanism **proven**; real-traffic precision **UNMEASURED** (base64/homoglyph false-positives likely) |
| Tollbooth digest adapter | golden-secret (flat + native) + **live unmodified container** | redaction **proven** (incl. real export); engagement footprint **UNMEASURED** (sandbox only) |
| memory retrieval index | self-test + firewall (read-only, no verdict) | **proven** read-only/no-verdict |
| E4 robustness eval + technique memory | hermetic fixture self-test | **plumbing proven**; it is a FIXTURE — **NOT** evidence about real models |
| Capability registry (C1–C3 + hardening) | conformance + 4 gate-bites | contract keyhole **proven to bite**; **no runtime** (deferred by design) |

## Gate-bites proven (capability keyhole)

| Gate | Injected violation | Caught? |
| --- | --- | --- |
| sensor-only authority | `authority: oracle` | FAIL ✓ |
| card capability ref | unresolved `optional_capabilities` id | FAIL ✓ |
| scope flag cross-ref | flag removed from `_TEMPLATE/scope.md` | FAIL ✓ |
| dangerous-action denylist | `agent` placed in `allowed_actions` | FAIL ✓ |
| allowed/forbidden disjoint | same action in both lists | FAIL ✓ |

Conformance: **171 checks, 0 failing**.

## Known limits (do not overstate)

1. **Contract layer, not runtime.** The capability registry enforces a *structural* keyhole; no capability
   is brokered at runtime (no runtime broker, no AGPL tool installed — both deferred by design).
2. **Gate-bites are currently manual.** The negative tests above were run interactively (break → FAIL →
   revert). They are **not yet permanent regression fixtures**, so a future refactor could silently weaken
   a gate without CI noticing. *(Highest-value next testing — see below.)*
3. **Conformance parses YAML with regex** (stdlib-only, no YAML lib). Robust for the registry's current
   shape; unusual indentation/quoting could in principle slip past. Bulletproofing needs a small YAML
   load in a separate validator (a dependency the checker has deliberately avoided).
4. **Efficacy is unproven at scale.** Techniques were only run against an 8B local model, where decode
   fidelity confounded the result. A larger model and a signed-scope live target are required to claim
   real efficacy.
5. **Scope flag gates by convention** at orchestration time (the loop is markdown-driven), like the rest
   of the harness's gates — not by executable code.

## Recommended next testing

Convert the manual gate-bites into **permanent negative-test fixtures** — a `_must_reject` capability
corpus the conformance checker asserts it rejects (mirroring `fixtures/findings/_must_reject` and the
false-discovery corpus). This makes the keyhole's "it bites" guarantee CI-enforced forever, not a one-off
manual check. Everything else is either deferred-by-design (runtime brokering) or needs external resources
(efficacy at scale, live scope).
