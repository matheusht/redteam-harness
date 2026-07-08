---
id: ssti.server-side-template-injection
name: Server-Side Template Injection
description: >
  Prove user input is concatenated into a server-side template string BEFORE rendering, such that
  the template engine evaluates attacker-supplied template syntax rather than treating it as inert
  data. Confirmed only via genuine expression EVALUATION (e.g. arithmetic), never mere reflection.
type: vuln
owasp: "A03:2021 Injection (SSTI)"
atlas: "—"
patterns: []

activation:
  strong:
    - "user input is concatenated into a template string (not passed as a template VARIABLE) before the engine renders it"
    - "template-syntax echo (e.g. `{{7*7}}`, `${7*7}`, `#{7*7}`, `<%= 7*7 %>`) returns an EVALUATED result (49) rather than the literal string"
    - "an error response leaks a template-engine name/stack trace (Jinja2, Twig, FreeMarker, Velocity, Handlebars, ERB, etc.)"
  weak:
    - "user input populates a template VARIABLE (the normal, safe use of templating) with no evidence it is ever treated as template source"
    - "a custom/sandboxed template dialect is in use whose expression language is restricted (may still allow a subset of primitives)"
  negative:
    - "user input is only ever passed as a bound template variable, never concatenated into the template source itself → likely held"
    - "the templating engine is fully sandboxed (no filesystem/process access from the expression language) even if expression evaluation is possible"

safe_signal:
  proxy: >
    a predeclared distinctive artifact only reachable via genuine template EVALUATION — e.g. a
    benchmark's build-time flag readable only via the engine's file-read primitive, or (live app)
    an arithmetic/string-transform expression whose evaluated result cannot be explained by simple
    string reflection (e.g. `{{7*7}}` returning `49`, not the literal text `{{7*7}}`).
  never: >
    do not pursue filesystem read/write or remote code execution beyond the planted canary or an
    OWNED disposable fixture; any code-execution-level artifact requires scope.md authorization
    and an operator confirm before creation.

impact_escalation:
  enabled_by: scope.md#impact_demo_authorized
  requires: human_confirm
  containment: "read-only canary/flag retrieval via the engine's own primitives; no persistent write, no shell spawned outside the owned container, logged in engagement cleanup.md"

oracle: [signal-oracle, adjudication-oracle]
severity_rubric: { remote_code_execution: critical, filesystem_read: high, expression_evaluation_only: medium }

procedure:
  - "IDENTIFY THE ENGINE: fingerprint via a polyglot probe covering multiple template dialects' syntax simultaneously; a distinct evaluated result (not an echo) narrows to the specific engine."
  - "FINGERPRINT (benign): send an inert arithmetic expression (`{{7*7}}` / `${7*7}` / equivalent per dialect). Compare against a matched negative control (a literal string with no template syntax) to rule out coincidental reflection."
  - "CONFIRM EVALUATION, NOT ECHO: the response must show the COMPUTED result (49), not the literal payload text. A payload reflected verbatim, even inside `{{ }}`, is not evaluation."
  - "ESCALATE PER ENGINE within scope: move from arithmetic to the engine's documented file-read/introspection primitives (e.g. Jinja2 `__class__.__mro__` chains) only as far as needed to retrieve the planted canary/flag — do not chain to a full shell unless scope and operator confirm authorize it."
  - "RCE-LEVEL ARTIFACTS (spawning a shell, arbitrary file write) are Zone-2: STOP and get operator confirm before creating that artifact, even if scope.md authorizes the category."
  - "RULE OUT a WAF/sandbox that strips expression syntax before it reaches the engine, and REPLAY in a fresh session."

emits: [attempt, finding]
---

## What "confirmed" looks like here
The template engine **evaluated** attacker-supplied syntax — proven by a computed result (not an
echo) or retrieval of the planted canary/flag via the engine's own primitives — reproduced once in
a fresh session with a matched negative control (literal string, no syntax) ruled out as the
explanation.

## Boundaries (escalate in order; each rung gated on the prior + scope.md)
1. **expression evaluation only** (arithmetic/string transform confirmed) — medium.
2. **filesystem read** via engine primitives (canary/flag retrieval) — high.
3. **remote code execution** — critical; **operator confirm before any artifact**.

## Not this card
- Output reflected into HTML that a BROWSER then interprets is `cross-site-scripting`, not SSTI —
  SSTI is evaluated server-side, before the response is ever sent to a client.
- User input passed as a normal template *variable* (the intended, safe use of the templating
  system) with no evidence it's ever treated as template source.

## Do not overclaim
- "The engine name appeared in an error message" is fingerprinting, not a finding — you still need
  evaluation proof.
- Do not assert RCE from expression-evaluation alone; name the exact primitive chain that would
  reach code execution, or stop at "expression evaluation confirmed."
