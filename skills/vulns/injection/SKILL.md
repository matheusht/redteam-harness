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
    - "a client-controlled value is spliced into a shell-invoked command string (`cd \"${path}\" && ${cmd}`) or a subprocess call runs with `shell:true` instead of binding the value as a positional argument / disabling the shell — the command-sink variant of this card (diff-derived: the `cd \"${projectPath}\" && ${initialCommand}` splice in CVE-2026-31975, the `foregroundChild(cmd, matches, {shell:true})` in CVE-2025-64756 — see the anchors section)"
  weak:
    - "any reflected user content visible in page source"
    - "a feature that historically implies injection (HTML email, SVG, iframe) with no confirmed execution"
  negative:
    - "framework auto-escaping / sanitized markdown / sandboxed diagram render → reflected but inert"
    - "CSP blocks execution; the sink renders input as text"
    - "shell/subprocess invocation binds attacker-controlled values as positional arguments (`\"$@\"`) with the shell disabled (`shell:false`), rather than interpolating them into a shell-parsed string → likely held (diff-derived: the `cwd: resolvedProjectPath` + regex-validated `sessionId` in CVE-2026-31975, the forced `shell: false` in GHSA-hxwm-x553-x359)"

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

oracle: [signal-oracle, adjudication-oracle, ghsa-fix-diff]
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

## Real disclosed anchor(s) for this class (fix-diff-derived)
Priors/taxonomy from real disclosed GHSA fix commits for this card's command-string sink. Verbatim
hunks + primary sources in `skills/oracles/references/ghsa-fix-diff-corpus.md` (OS command injection
-> RCE bucket); consult via the `ghsa-fix-diff` oracle. **These are all *fixed* bugs, not live-bug
claims:** a target matching a removed-line shape is a lead to run through the funnel above, never a
confirmation. Coverage here is partial — this card's other sub-sinks (markdown/HTML render, diagram,
template engines) aren't spoken to by this bucket, and the SQL-string-building sub-sink's own anchors
live in the sibling `skills/vulns/sql-injection` card's anchor section; see there for those.

**Command-string sink (interpolation into a shell-parsed string), `param-binding`:**
- **CVE-2026-31975** (claudecodeui, GHSA-gv8f-wpm2-m5wr, fixed 1.25.0 @ `12e7f07`): client
  `projectPath`/`initialCommand` spliced into `cd "${projectPath}" && ${initialCommand}` run via a
  pty → `cwd` bound out-of-band plus a `sessionId` allowlist regex, shell string reduced to
  `initialCommand` alone. Authenticated (chained with a JWT bypass elsewhere), WebSocket shell
  endpoint.
- **CVE-2025-64756** (node-glob, GHSA-5j98-mcp5-4vw2, fixed 11.1.0 @ `1e4e297`): the CLI's `-c`
  flag ran matched filenames through `foregroundChild(cmd, matches, {shell:true})` → matches now
  passed as bound positional args via `"$@"`/`"$argv"`, with `shell:true` gated behind an explicit
  opt-in. CLI, filename-metacharacter injection.
- **GHSA-hxwm-x553-x359** (@npmcli/git, fixed 2.0.8 @ `766bfbe`): a caller-suppliable `opts.shell`
  value could be inherited into every `spawn()` call → `shell: false` forced after the opts spread.
  Library-level, reachability-gated.

**Canonicalization variant (byte/line-terminator smuggling past an escaper), `canonicalization`:**
- **CVE-2026-9277** (shell-quote, GHSA-w7jw-789q-3m8p, fixed 1.8.4 @ `4378a6e`): the object-token
  escaper used `/(.)/g`, which in JS excludes line terminators, so a smuggled newline acted as an
  unescaped shell command separator → swapped for `/[\s\S]/g` plus an `OPS` exact-match allowlist.
  Reachable by any caller building `{op}` tokens from external input.
- **CVE-2024-4577** (php-cgi, GHSA-3qgc-jrrr-25jv, fixed 8.1.29/8.2.20/8.3.8 @ `9382673`): Windows
  Best-Fit byte remapping let a high byte the OS displays as `-` smuggle CLI flags into the php.exe
  invocation past a raw single-byte check → a `WideCharToMultiByte(CP_ACP,...)` canonicalization
  re-check before the getopt-skip decision. **Pre-auth**, unauthenticated network RCE, CISA KEV.
- **CVE-2025-49141** (haxcms, GHSA-g4cf-pp4x-hqgw) — **CONTESTED** (illustrative): authenticated
  `/gitImportSite` shelled out to git with an attacker-controlled repo URL; the fix deleted the
  endpoint wholesale rather than adding a guard, so there is no removed→added shape to promote as a
  signature.

## Do not overclaim
- "My payload is in the HTML" is reflection. Injection requires **execution** — say which one you have.
- A renderer interpreting markdown is doing its job; the finding is only a script/handler executing
  outside the sandbox.
- If you can't fire the execution canary, the honest verdict is `refuted` / `needs_review`, never "XSS".
- If the class's added-guard shape is already present at the reached command/query sink — arguments
  bound positionally with the shell disabled (`shell:false`, `"$@"`), or a canonicalizing/allowlist
  check before shell dispatch (see the anchors above) — this path is patched; do not claim strong
  activation without a further, specific reason (an unguarded sibling sink, a reachable pre-guard
  path). Presence of the guard is a strong held signal, not a soundness proof.
