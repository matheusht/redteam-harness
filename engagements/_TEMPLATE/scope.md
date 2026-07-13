# scope.md — engagement authorization gate

**The loop refuses to run until this is filled and signed.** Copy this `_TEMPLATE/` into the
target's own project repo (Plane 3) per engagement.

## Engagement
- **id:** `<client-YYYY-MM>`
- **target:** `<url / app / surface>`
- **environment:** `<staging | prod | sandbox>`
- **box:** `<black-box | gray-box (+ source location)>`

## Surfaces in scope
- [ ] chat UI
- [ ] document / RAG ingest
- [ ] tools / connectors (list): ___
- [ ] shared / cross-user surfaces: ___

## Active OWASP subset (harness ships all 10; select per engagement)
- [ ] LLM01 prompt injection  [ ] LLM02 sensitive-info  [ ] LLM05 output-handling
- [ ] LLM06 excessive-agency  [ ] LLM07 system-prompt-leak  [ ] other: ___

## Benign safe-objective set (allowlisted win-conditions)
- [ ] system-prompt / instruction disclosure (distinctive token)
- [ ] refusal-flip on a HARMLESS restricted target
- [ ] indirect-injection canary propagation
- [ ] excessive-agency / unsafe render on owned tooling
- [ ] other (must define a benign signal): ___

## Adversarial-input transforms (E-track capabilities)
- **scope_allows_adversarial_input_transforms:** `no`  ← default. If `yes`, the orchestrator may use the
  external encoding/obfuscation/stego/covert-channel capabilities in `capabilities/registry.yaml`
  (sensor-only, benign-canary objectives; the oracle stays authoritative). Each capability is also
  `default: disabled` per card; this flag is the engagement-level enable. GLOSSOPETRAE channels
  additionally require operator review.

## Payload generation (E-track `payload_generator` class)
- **scope_allows_payload_generation:** `no`  ← default. If `yes`, the harness may use `payload_generator`
  capabilities (`capabilities/classes.yaml`) to *propose* candidate artifacts for an approved benign
  objective — **proposal only**: they never execute on a live target, never judge success, never emit a
  verdict; the broker/oracle stay authoritative. Each proposal must carry a declared payload class,
  containment plan, cleanup plan, and a non-authority attestation. Any Zone-2 artifact or live execution
  still requires the impact-demo authorization above + a runtime human-confirm.

## Escalation ceiling
- self → stored/persistent → cross-user: ceiling = `<rung>`

## Impact-demo authorization (Zone-2)
- **impact_demo_authorized:** `no`  ← default. If `yes`, list exactly what artifact classes are
  authorized and the containment required. Even when `yes`, a live human-confirm fires before any
  artifact is created.

## Accounts / fixtures
- accounts (owned, same-org if cross-user): ___
- concurrency: `1`  (raising past 1 requires explicit authorization here)

## Authorization
- Operator: [name]
- Date: [date]
- Signed: [ ]
- Record kernel: `decision-0005-v1`
