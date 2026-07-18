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
    - "a client-controlled compile-time option, helper/path name, or template-author field (a Handlebars helper/path name, an EJS `outputFunctionName`/`localsName` view-option, a Pug `pretty` option, a Smarty `{function name=...}` tag) is spliced unescaped into the compiler's generated source string before it becomes executable code (diff-derived: the raw `name`/`opts.outputFunctionName`/`this.pp` string concatenation in CVE-2021-23369, CVE-2022-29078, CVE-2021-21353, CVE-2021-26120 — see the anchors section)"
    - "the server exposes its Twig/Jinja rendering environment unsandboxed (a plain `Twig_Environment`/`jinja2.Environment()` with no SecurityPolicy/SandboxedEnvironment, or an internal Twig extension chain reachable from template source) to a template-author or config-value role (diff-derived: the bare `Twig_Environment` in CVE-2023-43661, the unsandboxed `jinja2.Environment()` in CVE-2026-33154, the exposed `core.setEscaper` extension chain in CVE-2024-28119)"
  weak:
    - "user input populates a template VARIABLE (the normal, safe use of templating) with no evidence it is ever treated as template source"
    - "a custom/sandboxed template dialect is in use whose expression language is restricted (may still allow a subset of primitives)"
  negative:
    - "user input is only ever passed as a bound template variable, never concatenated into the template source itself → likely held"
    - "the templating engine is fully sandboxed (no filesystem/process access from the expression language) even if expression evaluation is possible"
    - "identifier-like compile-time fields (helper names, output-function names, pretty-print flags, `{function name=...}`) are validated against a strict identifier regex or escaped/JSON-stringified before being spliced into generated source, AND/OR rendering runs inside a sandbox with an explicit tags/filters/functions/methods allowlist → likely held (diff-derived: the `_JS_IDENTIFIER` regex in CVE-2022-29078, the `JSON.stringify(name)` swap in CVE-2021-23369, the Twig `SecurityPolicy`/`SandboxExtension` in CVE-2023-43661, the `SandboxedEnvironment` swap in CVE-2026-33154)"

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

oracle: [signal-oracle, adjudication-oracle, ghsa-fix-diff]
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

## Real disclosed anchor(s) for this class (fix-diff-derived)
Priors/taxonomy from real disclosed GHSA fix commits — the vulnerable pre-patch shape and the guard
the fix added. Verbatim hunks + primary sources in `skills/oracles/references/ghsa-fix-diff-corpus.md`
(Server-side template injection -> RCE bucket); consult via the `ghsa-fix-diff` oracle. **These are
all *fixed* bugs, not live-bug claims:** a target matching a removed-line shape is a lead to run
through the funnel above, never a confirmation. The class splits bimodally by where the untrusted
value enters.

**Value spliced into compiler-generated source (fix: escape/canonicalize or identifier-allowlist the
value before it is concatenated), `canonicalization` / `identifier-allowlist`:**
- **CVE-2021-23369** (handlebars.js, GHSA-f2jv-r9rf-7988, fixed 4.7.7 @ `f058970`): a helper/path
  `name` spliced raw into `container.lookup(depths, "<name>")` inside the compiled function body →
  `JSON.stringify(name)`. Reached via `Handlebars.compile(untrustedTemplateSource)`.
- **CVE-2022-29078** (ejs, GHSA-phwq-j96m-2c2q, fixed 3.1.7 @ `15ee698`): `opts.outputFunctionName`
  (and localsName/destructuredLocals) concatenated unescaped into the compiled function's prelude →
  `_JS_IDENTIFIER` regex allowlist before splice. Reachable when Express view-options are populated
  from request data.
- **CVE-2021-21353** (pug-code-gen, GHSA-p493-635q-r6gr, fixed 2.0.3/3.0.2 @ `991e78f`): the compile
  option `pretty` concatenated into `pug_indent.push('...')` inside a single-quoted JS literal →
  whitespace-only validation + `stringify(...)`.
- **CVE-2021-26120** (smarty, GHSA-3rpf-5rqv-689q, fixed 3.1.39 @ `165f1bd`): a `{function name=...}`
  tag's raw name compiled directly into a generated PHP function definition → identifier regex
  `^[a-zA-Z0-9_\x80-\xff]+$` rejects non-identifier names before compilation. Multi-tenant template
  authors.
- **CVE-2022-21686** (PrestaShop, GHSA-mrq4-7ch7-2465, fixed 1.7.8.3 @ `d02b469`): legacy admin `.tpl`
  layout content `str_replace`-spliced back into Twig source and compiled verbatim → `escapeSmarty()`
  wraps it as a raw string literal (`{{ '<escaped-content>' | raw }}`) so it is never parsed as Twig.
  Authenticated admin session.

**Rendering environment left unsandboxed for a template-author/config role (fix: wrap render in a
sandbox/security-policy or denylist dangerous constructs), `template-sandbox` / `denylist-to-safe-api`:**
- **CVE-2023-43661** (cachet, GHSA-hv79-p62r-wg3p, fixed 2.4 @ `6fb043e`): an authenticated user's
  incident `template` field rendered by a bare `Twig_Environment` (no sandbox) → Twig
  `SecurityPolicy`/`SandboxExtension` with an empty methods/functions allowlist. Authenticated,
  non-admin API token sufficient.
- **CVE-2026-33154** (dynaconf, GHSA-pxrr-hq57-q35p, fixed 3.2.13 @ `2fbb45e`): the `@jinja` config
  resolver rendered attacker-influenced config values with a plain `jinja2.Environment()` →
  `jinja2.sandbox.SandboxedEnvironment()` swap, catching `SecurityError`. Config-source triggered
  (env var / .env / CI secrets), no auth needed.
- **CVE-2024-28119** (Grav, GHSA-2m7x-c7px-hp58, fixed 1.7.45 @ `de1ccfa`): the internal Twig
  environment was reachable from page/front-matter Twig with no restriction, letting
  `core.setEscaper('system','system')` redefine the escaper to `system` → a regex denylist
  (`Security::cleanDangerousTwig`) comments out `core.setEscaper`/`call_user_func`/etc. before render.
  Weaker denylist-only guard; admin/editor-authored content.
- **CVE-2026-33938** (handlebars.js, GHSA-3mfm-83xf-c92r, fixed 4.7.9 @ `68d8df5`) — **CONTESTED**
  (illustrative only): a helper-mutated `@partial-block` data-frame carrying a type-confused
  pre-parsed AST node let a crafted `PathExpression.depth` splice into generated JS →
  `validateInputAst`/`isValidDepth` type-checks the AST before trusting it. Genuine guard but the
  fix SHA is a multi-CVE omnibus with a non-contiguous hunk, so not promoted as a clean signature.

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
- If the class's added-guard shape is already present in the target's source for the reached sink —
  an identifier-regex/escape/canonicalization check on the value before it is spliced into generated
  template source, or the render call is wrapped in a sandbox with an explicit tags/filters/
  functions/methods allowlist (see the anchors above) — this path is patched; do not claim strong
  activation without a further, specific reason (an unguarded sibling sink, a reachable pre-guard
  path). Presence of the guard is a strong held signal, not a soundness proof.
