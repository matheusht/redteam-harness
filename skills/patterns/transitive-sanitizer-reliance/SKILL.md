---
id: pattern.transitive-sanitizer-reliance
name: Sink Trusts An Upstream Sanitizer
description: >
  A sink (renderer / executor / forwarder) trusts that some UPSTREAM layer already sanitized the
  data, so it skips its own check. The assumption breaks when an alternate path reaches the sink
  unsanitized — OR the feared capability is actually neutralized downstream, making it a false
  positive. This card exists as much to KILL bad XSS/injection claims as to find real ones.
type: pattern
owasp: "A03 Injection / LLM05 Improper Output Handling"
also: "the execution-oracle discipline that separates reflection from execution"
atlas: "—"
routes_to: ["stub:vulns/llm05-improper-output-handling", "vulns/injection"]   # stub: = not yet built, do not blind-load

activation:
  strong:
    - "user/model-controlled content flows into a renderer or executor (markdown→HTML, mermaid/diagram, template engine, SQL/string builder, dangerouslySetInnerHTML)"
    - "escaping/validation lives in a DIFFERENT module than the sink, or multiple producers feed one sink"
    - "a 'rich' output surface that interprets its input (charts, diagrams, embeds) rather than displaying it literally"
  weak:
    - "any reflected user content appearing in page source"
    - "a feature that historically implies injection (HTML email, SVG, iframe) without confirmed execution"
  negative:
    - "the sink renders inside a sandbox / strips scripts / framework auto-escapes → reflected but inert"
    - "CSP or framework escaping blocks execution of the injected marker"
---

# Sink trusts an upstream sanitizer

**Idea.** Two failure directions, and you must tell them apart. (1) *Real*: a sink skips its own
escaping because it assumes an upstream layer cleaned the data, and an alternate producer reaches it
dirty. (2) *False positive*: the scary-looking sink (a diagram/markdown renderer) actually neutralizes
the payload downstream, so the reflection never executes. Most "XSS in the chat output" claims are
direction (2).

## Suggested probes
- **Trace every producer to the sink**: which paths reach the renderer/executor, and which one skips
  the escape step.
- **Inject an INERT benign canary**, not a live exploit: a marker that *would* prove execution if it
  ran. **Default to a LOCAL signal** — a `document.title` change, a `console` marker, an observable
  in-page DOM mutation. An **external callback** (a request to a collector you control) causes network
  egress and is **off by default**: use it only with explicit scope / Zone-2 confirmation. Never a
  harmful payload — the point is the execution signal, not impact.
- **Compare producers**: a payload that the escaped path neutralizes, send via the alternate path.

## Required oracle controls — EXECUTION oracle, not reflection
- **Reflection is not confirmation.** The payload appearing in the DOM/source is `needs_review` at
  most. You MUST show it **executed**: the benign callback fired, the script ran, the sandbox was
  escaped. No execution signal → `refuted`, even if it renders.
- **Default to refuted** when the framework sandboxes/escapes (React auto-escape, sanitized markdown,
  diagram libs that render to inert SVG). Prove the bypass, don't assume it.
- **Positive control**: confirm your execution detector works (a known-executing case fires the
  callback) before trusting a negative.
- **Replay** fresh session.

## Counterexamples (the false positives this card is built to block)
- **Diagram/markdown payload reflected but inert** (mermaid, sanitized MD) → REFUTED, not XSS. The
  renderer escaped or sandboxed it; reflection ≠ execution.
- CSP blocks the script; framework auto-escaping renders the payload as text.

## Do not overclaim
- "My payload is in the HTML" is reflection. XSS requires **execution**. State which one you have.
- A renderer interpreting markdown is doing its job; the finding is only if a *script/handler*
  executes outside the sandbox.
- If you can't fire an execution canary, the honest verdict is `refuted` / `needs_review`, never "XSS".
