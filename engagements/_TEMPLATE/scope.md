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
- operator: ___   date: ___   **signed:** [ ]
