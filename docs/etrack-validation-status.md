# E-track validation status (honest ledger)

**Review-only.** This records *what has actually been validated* for the E-track, and — per the prime
directive — what has **not**. Green self-tests prove *mechanism*, never *efficacy*; the oracle/broker
remain authoritative. `autonomous_gap_closure_count` = **0** (nothing here closes a gap; these are
tooling / sensors / fixtures).

## How things were validated

- **Hermetic self-tests** — each tool has `--self-test` exercising round-trip / detection / redaction.
- **Negative "gate-bites" tests** — for each conformance gate, a deliberate violation must FAIL (a gate
  only ever seen pass is not validated). These are now **permanent CI fixtures** under
  `fixtures/capabilities/_must_reject/`, each asserted to fail for its intended reason.
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
| Capability registry (C1–C3 + hardening) | conformance + **5 sensor/converter gate-bite fixtures** | contract keyhole **proven to fail closed**; **no runtime** (deferred by design) |
| Payload-generator lane (PG-0/1/2) | classes.yaml + conformance + **4 payload-gen gate-bite fixtures** + payload-proposal schema gate (1 valid / 4 must-reject incl. risk_tier) | **contract/schema/fixtures only**, proposal_only, gated; **no external tool, no execution, no harmful corpus** |
| Payload-proposal generator (PG-3A) | `generate-payload-proposal.py` self-test + `payload-proposal-hermetic-test.py` | **benign-only** local generator (no execution, no external tool, refuses exploit/chain kinds, self-validates vs the CI predicate); hermetic test **proves a proposal never acts like a verdict** (same proposal → target-dependent oracle verdict; single run never auto-confirmed). risk_tier hardens exploit/chain behind operator-confirm + impact_demo_ref |

## Gate-bites proven (capability keyhole)

| Gate | Injected violation | Caught? |
| --- | --- | --- |
| sensor-only authority | `authority: oracle` | FAIL ✓ |
| card capability ref | unresolved `optional_capabilities` id | FAIL ✓ |
| scope flag cross-ref | flag removed from `_TEMPLATE/scope.md` | FAIL ✓ |
| dangerous-action denylist | `agent` placed in `allowed_actions` | FAIL ✓ |
| allowed/forbidden disjoint | same action in both lists | FAIL ✓ |

Conformance: **192 checks, 0 failing**. The keyhole now has **9** permanent fixtures in
`fixtures/capabilities/_must_reject/` (5 sensor/converter + 4 payload-generator) plus the
payload-proposal gate in `fixtures/payload-proposals/` — CI re-asserts each fails for its intended
reason, and a meta-gate fails if any fixture is ever accidentally made valid. A well-formed
payload_generator entry and a valid payload proposal both pass (the gates are precise, not blanket).

## Known limits (do not overstate)

1. **Contract layer, not runtime.** The capability registry enforces a *structural* keyhole; no capability
   is brokered at runtime (no runtime broker, no AGPL tool installed — both deferred by design).
2. ~~Gate-bites are manual.~~ **CLOSED:** the negative tests are now permanent fixtures in
   `fixtures/capabilities/_must_reject/`; conformance asserts each fails for its intended reason, and a
   meta-gate fails if any fixture is accidentally made valid. A future refactor that weakens a gate now
   trips CI.
3. **Conformance parses YAML with regex** (stdlib-only, no YAML lib). Robust for the registry's current
   shape; unusual indentation/quoting could in principle slip past. Bulletproofing needs a small YAML
   load in a separate validator (a dependency the checker has deliberately avoided).
4. **Efficacy is unproven at scale.** Techniques were only run against an 8B local model, where decode
   fidelity confounded the result. A larger model and a signed-scope live target are required to claim
   real efficacy.
5. **Scope flag gates by convention** at orchestration time (the loop is markdown-driven), like the rest
   of the harness's gates — not by executable code.

## Next testing

- **DONE:** the `_must_reject` capability corpus — the gate-bites are now CI-enforced fixtures (mirrors
  `fixtures/findings/_must_reject`). The keyhole's "fails closed" guarantee is now permanent, not a
  one-off manual check.
- **Deferred:** YAML-robustness (regex brittleness, Known-limit #3) — only if bulletproofing is wanted;
  needs a small separate YAML validator (a dependency the checker has avoided).
- **Blocked on external resources (by design):** runtime brokering (needs a tool installed), efficacy at
  scale (needs a larger model and/or a signed-scope live target).
