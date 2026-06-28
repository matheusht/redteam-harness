# Capabilities — the broker rule (Plane 2)

External tools (P4RS3LT0NGV3 / ST3GG / GLOSSOPETRAE, all AGPL) are powerful, and most of their power is
exactly the kind that rots a rigor-first harness if made too convenient. So the model never gets the raw
toolbox. It reaches them only through a **narrow keyhole**: the constrained capabilities declared in
`capabilities/registry.yaml`.

## The rule

> **External capability output is always a `sensor` or `converter` signal — NEVER an oracle.** A
> capability emits a transformed benign canary or evidence. It never emits a verdict, never confirms a
> finding, never authorizes a candidate. The oracle/broker remain authoritative.

This is conformance-enforced: every registry entry must declare `authority: sensor_only`; no entry may
claim `oracle`/`judge`/`authoritative`/`verdict` authority (`tools/check-conformance.py`).

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
