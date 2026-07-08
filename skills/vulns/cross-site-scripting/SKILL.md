---
id: xss.cross-site-scripting
name: Cross-Site Scripting
description: >
  Prove attacker-controlled input reaches a browser execution sink (HTML/JS/attribute context)
  and actually EXECUTES, not merely that it appears unescaped in a response. Covers reflected,
  stored, and DOM-based variants. Confirmed only via a benign canary script that demonstrably ran.
type: vuln
owasp: "A03:2021 Injection (XSS)"
atlas: "—"
patterns: []

activation:
  strong:
    - "user input is reflected into an HTML/JS/attribute/URL context without contextual output encoding"
    - "user input reaches a client-side sink (innerHTML, document.write, eval, location assignment) via a traceable source"
    - "stored input (comment, profile field, filename, message) is rendered back to OTHER users without encoding"
  weak:
    - "input is encoded in one context (e.g. HTML-entity-encoded) but reachable in a different context (attribute, JS string, URL) where that encoding is insufficient"
    - "a Content-Security-Policy is present but permissive (unsafe-inline, wide script-src) — reduces but does not eliminate exploitability"
  negative:
    - "output is contextually encoded for the sink it lands in, and CSP additionally blocks inline/eval execution → likely held"
    - "the input never reaches a render or DOM-sink path (e.g. used only server-side, or strictly typed/numeric)"

safe_signal:
  proxy: >
    a benign canary payload that provably EXECUTES — e.g. a script that calls back to an
    operator-controlled endpoint you own, or sets a distinctive, otherwise-unreachable DOM/global
    marker you can read back programmatically. Payload appearing unescaped in raw HTML/response
    body is NOT the signal by itself — see "Do not overclaim".
  never: >
    do not deliver payloads to real other users outside an owned test account; do not exfiltrate
    real session tokens/cookies; any cross-user execution demo requires scope.md authorization and
    an operator confirm before the artifact is created.

impact_escalation:
  enabled_by: scope.md#impact_demo_authorized
  requires: human_confirm
  containment: "benign canary execution only, no cookie/token exfiltration, no third-party callback infra, logged in engagement cleanup.md"

oracle: [signal-oracle, adjudication-oracle]
severity_rubric: { stored_any_user: critical, dom_based_reachable: high, stored_self_only: medium, reflected_requires_interaction: medium }

procedure:
  - "MAP THE SINK: for each candidate input, identify where it lands — server-rendered HTML, an HTML attribute, a JS string literal, a URL, or a client-side sink (innerHTML/eval/document.write) reached from a traceable source."
  - "FINGERPRINT (benign): a distinctive, inert marker string (not a script) to confirm the input reaches the sink at all and observe what encoding, if any, is applied to `<`, `>`, `\"`, `'`."
  - "CONFIRM EXECUTION, NOT REFLECTION: swap the marker for a benign canary that performs an observable action on execution (operator-owned callback hit, or a readable DOM/global side effect). Encoded/escaped output in the raw response is not evidence of execution — do not stop at 'I see my payload in the HTML'."
  - "STORED VARIANT: verify the canary executes when the page is loaded by a SECOND principal/session you control (not just the one that submitted it) before calling it 'any-user' severity; if it only ever fires for the submitting account, it's self-XSS, not full stored XSS."
  - "DOM-BASED VARIANT: trace the full source→sink path client-side (e.g. `location.hash` → `innerHTML`) and confirm execution without any server round-trip needed."
  - "CHECK CSP: note whether a Content-Security-Policy would have blocked the canary in a realistic browser configuration; a payload that only fires with CSP disabled is a weaker claim — say so."
  - "RULE OUT contamination (browser extension, dev-tools-injected script) and REPLAY in a fresh session/profile."

emits: [attempt, finding]
---

## What "confirmed" looks like here
A benign canary demonstrably **executed** in a real page-render/DOM context — proven by an
operator-owned callback hit or a readable side effect — not merely that the payload string
survived unescaped into the response body. Reproduced once in a fresh session with contamination
(extensions, dev tools) ruled out.

## Boundaries (escalate in order; each rung gated on the prior + scope.md)
1. **reflected, requires victim interaction** (click a crafted link) — medium.
2. **self-stored** (only the submitting account ever sees it execute) — medium.
3. **stored, any viewer** or **DOM-based, reachable from an untrusted source** — high/critical;
   cross-user execution demo needs **operator confirm before any artifact**.

## Not this card
- Server-side template evaluation of attacker input (`{{7*7}}` → `49`) is `server-side-template-injection`,
  not XSS, even though both are injection-into-rendering bugs.
- A payload visible in a JSON API response that is never rendered into a browser DOM by any
  client — no execution path, no XSS.

## Do not overclaim
- "My payload appears in the page source, unescaped" is an activation, not a finding — many
  browsers/frameworks won't execute it as-is. Prove execution or it's `needs_review`.
- A reflected XSS with no realistic victim-interaction path (e.g. requires POST body only the
  attacker can set) is a weak claim — name the actual delivery vector or don't call it exploitable.
