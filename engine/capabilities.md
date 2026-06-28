# Capabilities — the broker rule (Plane 2)

External tools (P4RS3LT0NGV3 / ST3GG / GLOSSOPETRAE, all AGPL) are powerful, and most of their power is
exactly the kind that rots a rigor-first harness if made too convenient. So the model never gets the raw
toolbox. It reaches them only through a **narrow keyhole**: the constrained capabilities declared in
`capabilities/registry.yaml`.

## The rule

> **External capability output is always a `sensor` or `converter` signal — NEVER an oracle.** A
> capability emits a transformed benign canary or evidence. It never emits a verdict, never confirms a
> finding, never authorizes a candidate. The oracle/broker remain authoritative.

This is conformance-enforced: every sensor/converter registry entry must declare `authority: sensor_only`;
no entry may claim `oracle`/`judge`/`authoritative`/`verdict` authority (`tools/check-conformance.py`).

## Capability classes (`capabilities/classes.yaml`)

A capability's **class** fixes the maximum authority it may ever hold:

| Class | Authority | Notes |
| --- | --- | --- |
| `sensor` | `sensor_only` | observe / decode / summarize / redact |
| `converter` | `sensor_only` | transform a benign canary or evidence artifact (the existing keyhole) |
| `payload_generator` | `proposal_only` | **propose** candidate artifacts for an approved objective — never execute, never judge, never emit a verdict |
| `executor` | `broker_mediated` | execute a payload/action — FUTURE, review-required, **not built** |
| `oracle` | `broker_oracle_only` | decide truth/success — external tools **forbidden** from this class |

**The `payload_generator` lane (contract-only — PG-0/1/2).** It is a *separate, stricter* lane, not a
relaxation of the keyhole. A payload generator only **proposes**; the broker/oracle remain authoritative.
Conformance enforces, for any `class: payload_generator` entry: `authority: proposal_only`,
`default: disabled`, the required gates (`scope_allows_payload_generation`, `containment_plan`,
`oracle_separation`, a declared `payload_class`, signed scope), `forbidden_actions` declared, and that it
**never** claims `oracle`/`judge`/`verdict`/`confirmed`/`allow`/`success` authority. There is **no runtime
generator, no external tool, no live execution, and no harmful-payload corpus** — PG-3 (a first hermetic
generator) is deferred and separately gated. See `docs/post-phase14-payload-generation-capability-plan.md`.

## Flow

```text
routing sees an activation signal
  -> chooses a technique card
  -> card may list optional_capabilities (ids in the registry)
  -> capability broker check (contract): scope_allows_adversarial_input_transforms? safe_signal present?
     license/arms-length ok? tool installed? action in allowed_actions (never forbidden_actions)?
  -> capability emits a transformed BENIGN canary OR evidence (sensor/converter)
  -> broker records control + attempt + replay + cost; oracle adjudicates
  -> technique memory records only an abstract, advisory transform-vs-defense outcome
```

## Boundaries

- **Contract layer only (now).** The registry + this rule + conformance are the keyhole. There is **no
  runtime broker class/daemon**; actual subprocess invocation is deferred (presence-detected) until a tool
  is installed. (Decision 0004: roles for reasoning, not classes to build.)
- **default: disabled.** A capability runs only when an engagement sets
  `scope_allows_adversarial_input_transforms` and a card requests it.
- **forbidden_actions are real.** Agent/promptcraft/anticlassifier/injector/embed-arbitrary-payload modes
  are listed as `forbidden_actions`, never `allowed_actions` — the model cannot invoke them through the
  keyhole.
- **Arms-length / no vendoring.** AGPL source is never copied into Plane 1/2; integration is `subprocess`.
- **Detect before embed.** ST3GG is registered for detection only; embedding is a later, review-gated,
  hermetic-only capability.

See `capabilities/registry.yaml` for the entries and `docs/etrack-third-party-license-notes.md` for the
license posture.
