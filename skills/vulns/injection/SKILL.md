---
id: inj.injection
name: Injection Into A Rendering / Execution Sink
description: >
  Prove that user- or model-controlled content reaches a sink (renderer, template, query, command)
  and is INTERPRETED rather than treated as data — confirmed only by an EXECUTION signal, never by
  reflection alone. Built to find real injection AND to refute the far more common inert-reflection
  false positive.
type: vuln
owasp: "A03 Injection / LLM05 Improper Output Handling"
atlas: "AML.T0051"
patterns: [pattern.transitive-sanitizer-reliance]

activation:
  strong:
    - "user/model-controlled content flows into a renderer or executor (markdown→HTML, diagram, template engine, dangerouslySetInnerHTML, SQL/command string builder)"
    - "escaping lives in a different module than the sink, or multiple producers feed one sink"
    - "a 'rich' surface that interprets its input (charts, diagrams, embeds) rather than displaying it literally"
  weak:
    - "any reflected user content visible in page source"
    - "a feature that historically implies injection (HTML email, SVG, iframe) with no confirmed execution"
  negative:
    - "framework auto-escaping / sanitized markdown / sandboxed diagram render → reflected but inert"
    - "CSP blocks execution; the sink renders input as text"

safe_signal:
  proxy: >
    a benign INERT execution canary fires at the sink — a LOCAL observable (document.title change,
    console marker, in-page DOM mutation) that can only occur if the injected content EXECUTED. The
    signal is execution, never impact.
  never: >
    no harmful payloads, no data exfiltration, no destructive queries. External network callbacks are
    OFF by default (egress) — allowed only with scope.md authorization and an operator confirm.

impact_escalation:
  enabled_by: scope.md#impact_demo_authorized
  requires: human_confirm
  containment: "inert local canary only; any egress/PoC logged in cleanup.md with a revert"

oracle: [signal-oracle, adjudication-oracle]
severity_rubric: { stored_executes_cross_user: critical, reflected_executes: high, executes_self_only: medium, reflected_but_inert: info, refused: info }

procedure:
  - "TRACE PRODUCERS TO SINK: enumerate every path that reaches the renderer/executor; find which one skips its own escaping (route the shape via pattern.transitive-sanitizer-reliance)."
  - "POSITIVE CONTROL FIRST: prove your EXECUTION detector works — a known-executing case must fire the local canary. A detector you haven't calibrated can only produce false negatives."
  - "INJECT AN INERT CANARY: a benign marker that changes document.title / writes a console token / mutates the DOM ONLY IF it executes. Default LOCAL; never a harmful payload."
  - "REFLECTION IS NOT CONFIRMATION: the payload appearing in DOM/source is at most needs_review. Require the execution canary to fire."
  - "DEFAULT TO REFUTED when the framework sandboxes/escapes (React auto-escape, sanitized MD, diagram→inert SVG). Prove the bypass; don't assume it."
  - "STORED vs REFLECTED: if the sink persists, test whether ANOTHER principal's session executes it (cross-user → critical; gate on scope.md + operator confirm)."
  - "RULE OUT contamination; REPLAY in a fresh session."

emits: [attempt, finding]
---

## What "confirmed" looks like here
The injected content **executed** at the sink — the inert local canary fired (title/console/DOM
changed) — not merely that it was reflected into the page. A stored payload that executes in a
*different* principal's session is critical; reflected-but-inert is `info`, not a finding.

## The reflection-vs-execution line (the load-bearing rule)
| You have | Verdict |
| --- | --- |
| payload appears in page source / DOM | reflection → `needs_review` at most |
| inert canary FIRED (title/console/DOM changed) | execution → candidate finding |
| renderer sandboxed/escaped it, canary never fired | `refuted` (this is the common case) |

Most "XSS in the chat output" claims are inert reflection. Diagram/markdown renderers are frequently
sandboxed by design. Treat a reflection as guilty-of-being-inert until the canary fires.

## Egress discipline
Default the execution canary to a **local** signal. An external callback to a collector you control is
network egress — **off by default**, allowed only with scope.md authorization + operator confirm. The
goal is the execution signal, not reach.

## Sub-sinks (same card, set severity by sink)
markdown/HTML render · diagram/chart (mermaid etc.) · template engines · SQL/command string building.
For server-side sinks (SQL/command) the "execution canary" is a benign provable effect (a harmless
computed value returned), never a destructive statement.

## Do not overclaim
- "My payload is in the HTML" is reflection. Injection requires **execution** — say which one you have.
- A renderer interpreting markdown is doing its job; the finding is only a script/handler executing
  outside the sandbox.
- If you can't fire the execution canary, the honest verdict is `refuted` / `needs_review`, never "XSS".
