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
    - "a value is written directly into an HTML-rendering call (template interpolation, a `<span>` build-up, a DOM highlight helper) with no escaping function anywhere in that code path — a bare `${value}` splice or a `// todo: sanitize` marker that was never implemented (diff-derived: the unescaped `${errorCode}` interpolation in GHSA-9x4v-xfq5-m8x5 better-auth, the `// todo: sanitize` no-op in CVE-2022-2022 NocoDB — see the anchors section)"
    - "an HTML sanitizer's denylist/allowlist match on attribute or tag names skips case/whitespace canonicalization before comparing, so a trailing-space or case-variant attribute name slips a dangerous value past the filter (diff-derived: the untrimmed `attr->nodeValue` compare in CVE-2024-37383 Roundcube)"
  weak:
    - "input is encoded in one context (e.g. HTML-entity-encoded) but reachable in a different context (attribute, JS string, URL) where that encoding is insufficient"
    - "a Content-Security-Policy is present but permissive (unsafe-inline, wide script-src) — reduces but does not eliminate exploitability"
  negative:
    - "output is contextually encoded for the sink it lands in, and CSP additionally blocks inline/eval execution → likely held"
    - "the input never reaches a render or DOM-sink path (e.g. used only server-side, or strictly typed/numeric)"
    - "the value passes an explicit escape/sanitize call (HTML-entity encoding, `DOMPurify.sanitize()`) immediately before the sink, or an identifier-like value is bound/allowlisted (`intval()` + exact-match) before it is ever stored or rendered → likely held (diff-derived: `sanitize()` in GHSA-9x4v-xfq5-m8x5 better-auth, `DOMPurify.sanitize()` in CVE-2022-2022 NocoDB, `intval()` + `{1,2}` allowlist in GHSA-rrr4-h2pc-57g6 Talishar, the `trim()`'d denylist compare in CVE-2024-37383 Roundcube)"

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

oracle: [signal-oracle, adjudication-oracle, ghsa-fix-diff]
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

## Real disclosed anchor(s) for this class (fix-diff-derived)
Priors/taxonomy from real disclosed GHSA fix commits — the vulnerable pre-patch shape and the guard
the fix added. Verbatim hunks + primary sources in `skills/oracles/references/ghsa-fix-diff-corpus.md`
(Cross-site scripting bucket); consult via the `ghsa-fix-diff` oracle. **These are all *fixed* bugs,
not live-bug claims:** a target matching a removed-line shape is a lead to run through the funnel
above, never a confirmation. The dominant guard shape is escape-before-sink; two secondary shapes
cover values that can't be simply HTML-escaped (identifier-like fields, sanitizer denylist matches).

**Escape-before-sink (`escape`):**
- **GHSA-9x4v-xfq5-m8x5** (better-auth, fixed 1.1.16 @ `7ae340e2`): unauthenticated `error` query
  param spliced raw as `${errorCode}` into the HTML error page → `sanitize()` HTML-entity-encode
  wrapper at the interpolation site. Reflected, requires victim click.
- **GHSA-ff9r-ww9c-43x8 / CVE-2026-25759** (Statamic, fixed 6.2.3 @ `6ed4f65f`): admin Command
  Palette rendered raw content titles via fuzzysort `.highlight()` with no escaping → `escapeHtml()`
  applied before the highlight call. Stored, content-creator payload executes for a higher-privileged
  searcher (stored-XSS-to-privesc).
- **CVE-2023-36656** (json-markup, a Jaeger UI dependency, fixed 1.1.4 @ `e7fb4df7`): JSON object
  key string-concatenated raw into a `<span>` used via `dangerouslySetInnerHTML` → `escape(key)`
  wrap at the concatenation site. Stored, any viewer of the trace.

**Denylist → safe-API sanitizer (`sanitizer-swap`):**
- **CVE-2022-2022** (NocoDB, fixed 0.91.7 @ `ffad5a31`): project title/slug stored with only a
  `// todo: sanitize` marker and no actual sanitization → `DOMPurify.sanitize(projectBody.title)`
  before store. Authenticated, stored for every viewer of the project dashboard.

**Param-binding + exact-match allowlist (`exact-match-swap`, for identifier-like fields that
can't be HTML-escaped):**
- **CVE-2026-25144 / GHSA-rrr4-h2pc-57g6** (Talishar, commit-pinned @ `09dd00e5`): `playerID` GET
  param used and rendered verbatim in a shared game page `<span>` → `intval()` bind + `{1,2}`
  exact-match allowlist. Stored, rendered for every game participant.

**Canonicalization-before-denylist-match (`canonicalize-then-match`):**
- **CVE-2024-37383 / GHSA-8j3w-26mp-75xh** (Roundcube, fixed 1.5.7 / 1.6.7 @ `43aaaa52`): HTML
  sanitizer's SVG `<animate attributeName>` denylist compare skipped whitespace trimming, so a
  trailing-space `href ` slipped a `javascript:` URI past the filter → `trim()` added before the
  `strtolower()` compare. Triggered when a victim opens a crafted HTML email.
- **GHSA-65mj-f7p4-wggq / CVE-2025-66309** (Grav admin plugin, fixed 1.8.0-beta.27 @ `99f65329`)
  — **CONTESTED** (illustrative; squashed multi-GHSA release bundle, non-promotable): Selectize
  admin multi-select fields rendered option/item text with no default escaping → new `SafeRender`
  default render functions HTML-escaping option/item text. Requires authenticated attacker plus
  admin interaction.

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
- If the class's added-guard shape is already present in the target's source for the reached sink —
  an escape/sanitize call immediately before the HTML sink, or a bind/allowlist check for an
  identifier-like value (see the anchors above) — this path is patched; do not claim strong
  activation without a further, specific reason. Presence of the guard is a strong held signal, not
  a soundness proof.
