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
routes_to: ["vulns/llm05-improper-output-handling", "vulns/injection"]

activation:
  strong:
    - "user/model-controlled content flows into a TRULY UNSAFE sink: dangerouslySetInnerHTML / raw innerHTML, a template or SQL/string builder, an executor (eval, shell)"
    - "a renderer reached WITH a sink-danger tell: a known sanitizer bypass, an active-HTML / raw-HTML allowance, or a confirmed execution route past the escaper"
    - "escaping/validation lives in a DIFFERENT module than the sink, or multiple producers feed one sink (one may skip the escape)"
    - "a downstream sink trusts a client-supplied signal as proof that an upstream layer already ran its check, with no unforgeable binding to that upstream event — the bare header-presence trust removed in CVE-2025-29927 (Next.js): forging `x-middleware-subrequest` skipped the middleware where auth lived entirely (diff-derived: see anchors below)"
    - "an upstream gate (validator/plugin/inspector) can be fed a DIFFERENT payload than what the sink ultimately executes — e.g. the silent oversize-body truncation removed in CVE-2026-34040 (Moby AuthZ plugin), where the daemon executed the full request while the plugin approving it only ever saw an empty/undersized body"
  weak:
    - "model/user output merely rendered through a markdown / diagram / rich pipeline that normally sanitizes (markdown→HTML, mermaid, charts, embeds) — render PRESENCE alone is weak"
    - "any reflected user content appearing in page source"
    - "a feature that historically implies injection (HTML email, SVG, iframe) without confirmed execution"
  negative:
    - "the sink renders inside a sandbox / strips scripts / framework auto-escapes → reflected but inert"
    - "CSP or framework escaping blocks execution of the injected marker"
    - "the signal a sink relies on to confirm 'an upstream layer already checked this' is bound to an unforgeable secret compared exactly (not mere header presence), and the upstream checker is guaranteed to see the SAME payload the sink executes — oversize/edge-case inputs are hard-rejected rather than silently truncated or passed through → likely held (diff-derived: the per-process `x-middleware-subrequest-id` secret binding in CVE-2025-29927; the `Peek(maxBodySize+1)` hard-fail-on-oversize guard in CVE-2026-34040)"
  out_of_scope:
    - "untrusted content reaching the model's INSTRUCTION / PROMPT channel (indirect prompt injection, RAG context poisoning, tool-result-as-instruction) is NOT this card — this card is about DATA sinks (HTML / SQL / template / shell / forwarder), not the prompt channel. Route to pattern.indirect-prompt-injection; do not force-fit this card onto it."
---

> **Scope boundary (load-bearing).** This card is about a DATA sink (renderer / SQL / template / shell /
> forwarder) trusting an upstream sanitizer. Untrusted content reaching the model's **instruction /
> prompt channel** — indirect prompt injection, RAG context poisoning, a tool result interpreted as an
> instruction — is a DIFFERENT shape: route it to `pattern.indirect-prompt-injection`, do not stretch
> this card to cover the prompt channel.

> **Activation-strength rule (load-bearing).** A render/rich-output surface being *present* is **weak**:
> most such pipelines sanitize, so the prior is "inert until proven otherwise." Escalate to **strong**
> ONLY with a sink-danger tell — an unsafe sink (dangerouslySetInnerHTML, raw template/SQL builder,
> executor), a known sanitizer bypass, an active-HTML allowance, or a confirmed execution route. This
> keeps the harness skeptical: "output is rendered" is not, by itself, a strong signal.

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

## Real disclosed anchor(s) for this class (fix-diff-derived)
Priors/taxonomy from real disclosed GHSA fix commits — the vulnerable pre-patch shape and the guard
the fix added. Verbatim hunks + primary sources in `skills/oracles/references/ghsa-fix-diff-corpus.md`
(Auth bypass — generic mechanism / middleware / gateway bucket); consult via the `ghsa-fix-diff`
oracle reference (this card has no `oracle:` list in front-matter to append to — see notes). **These
are all *fixed* bugs, not live-bug claims:** a target matching a removed-line shape is a lead to run
through the funnel above, never a confirmation.

**Partial-coverage note:** this bucket is a generic auth-bypass/middleware corpus shared across
several cards (`jwt-authentication-bypass`, `legacy-route-differential`, this card). Only the anchors
below map onto THIS card's specific shape — a downstream sink/executor trusting that an upstream
layer already ran its check/sanitization on the SAME data the sink acts on. The bucket's two
path-canonicalization-mismatch anchors (Quarkus CVE-2026-50559, fastify-express CVE-2026-33808) and
the display-name/id identity-binding anchor (openclaw CVE-2026-28474) are left to their narrower
sibling cards rather than force-fit here.

- **CVE-2025-29927** (Next.js, GHSA-f82v-jwr5-mffw, fixed 12.3.5 / 13.5.9 / 14.2.25 / 15.2.3 @
  `52a078d`): the router trusted the client-supplied `x-middleware-subrequest` header as proof that
  the internal recursion-guard (and, transitively, the middleware where auth/authz lived) had already
  run, with no binding to an unforgeable value → a per-process random secret
  (`x-middleware-subrequest-id`) stamped on genuine internal subrequests and compared exactly.
  Pre-auth, full middleware-auth skip on any self-hosted deployment. `param-binding`.
- **CVE-2026-34040** (Moby/Docker Engine, GHSA-x744-4wpc-v9h2, fixed 29.3.1 / 2.0.0-beta.8 @
  `e89edb1`): the AuthZ-plugin gateway silently truncated/emptied oversized request bodies before
  forwarding them to the plugin for inspection, while still executing the original, full,
  unredacted request against the daemon — the "sanitizer" (the plugin's inspection) ran on different
  data than the sink (the daemon) actually acted on → hard-fail (`Peek(maxBodySize+1)` returns an
  error) instead of silently forwarding a stunted body. Authenticated-gateway bypass, no privilege
  required beyond reaching the AuthZ-gated API. `bound`.

## Do not overclaim
- "My payload is in the HTML" is reflection. XSS requires **execution**. State which one you have.
- A renderer interpreting markdown is doing its job; the finding is only if a *script/handler*
  executes outside the sandbox.
- If you can't fire an execution canary, the honest verdict is `refuted` / `needs_review`, never "XSS".
- If the sink's trust signal is already bound to an unforgeable value tied to the genuine upstream
  event (a compared-exactly secret, not header presence), or the upstream check is guaranteed to see
  the identical payload the sink executes (oversize inputs hard-rejected, not truncated) — this path
  is patched; do not claim strong activation without a further, specific reason (an alternate producer
  that still reaches the sink unguarded). Presence of the guard is a strong held signal, not a
  soundness proof.
