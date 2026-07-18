---
id: cmdi.os-command-injection
name: OS Command Injection
description: >
  Prove user input reaches a shell/exec call such that argument or metacharacter injection alters
  what command runs, including injected arguments to a shell-invoking SSH/exec wrapper. Confirmed
  only via an observable side effect that could only occur from actual command execution.
type: vuln
owasp: "A03:2021 Injection (OS Command)"
atlas: "—"
patterns: []

activation:
  strong:
    - "user input is passed to a shell invocation (system/exec/popen/backticks) or a wrapper around one (e.g. an SSH/exec-invoking feature) without strict allowlisting"
    - "metacharacters (`;`, `|`, `&&`, backticks, `$()`) in input are not rejected/escaped before reaching the shell"
    - "a feature exposes a raw command-line-shaped argument to the client (filename passed to an image/pdf converter, hostname passed to ping/traceroute, etc.)"
    - "a client-controlled path or argument is spliced directly into a shell-invoked command string instead of bound as a positional argument with the shell disabled (diff-derived: the removed `cd \"${projectPath}\" && ${initialCommand}` splice in CVE-2026-31975, the `foregroundChild(cmd, matches, { shell: true })` in CVE-2025-64756, the inheritable truthy `shell` option in GHSA-hxwm-x553-x359 — see the anchors section)"
    - "an escape or allowlist check operates on raw bytes/characters without accounting for platform- or encoding-level canonicalization, so a blocked character can still reach the shell after reinterpretation (diff-derived: the Windows Best-Fit high-byte-to-`-` remap bypassing the CGI flag check in CVE-2024-4577, the `/(.)/g` escape regex not matching line terminators in CVE-2026-9277)"
  weak:
    - "input reaches an exec call but through an argv array (no shell interpretation) — argument injection may still be possible even without metacharacter execution"
    - "a wrapper library is used that claims to sanitize shell input but has known bypass classes for its version"
  negative:
    - "input never reaches a shell/exec call — pure library calls with no subprocess invocation → likely held"
    - "metacharacters are strictly allowlist-validated (not blocklisted) before any exec call → likely held"
    - "shell-invoking calls bind user input as positional arguments with the shell explicitly disabled (`shell: false`, `\"$@\"`/argv passing, `cwd` set out-of-band) rather than splicing into a command string, and any character check accounts for platform byte-canonicalization → likely held (diff-derived: the forced `shell: false` in GHSA-hxwm-x553-x359, the `foregroundChild(SHELL, cmdArg)` positional-arg binding in CVE-2025-64756, the `WideCharToMultiByte(CP_ACP,...)` canonicalization re-check in CVE-2024-4577)"

safe_signal:
  proxy: >
    a predeclared distinctive artifact only reachable via actual command execution — e.g. a
    benchmark's build-time flag readable only by executing a command inside the container, or (live
    app) a benign canary side effect: a file written to a scratch path inside an OWNED, disposable
    container, or a measurable, reproducible time delay from an injected sleep command versus a
    matched negative-control baseline (for blind variants).
  never: >
    do not pursue actions beyond the owned/disposable target container — no lateral movement, no
    host escape, no network egress from the injected command; any artifact beyond the planted
    canary/flag requires scope.md authorization and an operator confirm before creation.

impact_escalation:
  enabled_by: scope.md#impact_demo_authorized
  requires: human_confirm
  containment: "canary/flag read only within the owned container; no persistent implant, no outbound network from the injected command, logged in engagement cleanup.md"

oracle: [signal-oracle, adjudication-oracle, ghsa-fix-diff]
severity_rubric: { full_shell_rce: critical, blind_command_exec_confirmed: high, argument_injection_no_exec_confirmed: medium }

procedure:
  - "IDENTIFY THE SINK: any feature that shells out — file conversion, network diagnostics (ping/traceroute/nslookup), archive extraction, an SSH/exec wrapper — is a candidate."
  - "FINGERPRINT (benign, in-band): inject a benign, easily-attributable marker command (e.g. `echo <distinctive-string>`) via a metacharacter and compare output/behavior to a matched negative control (the metacharacter escaped/rejected)."
  - "CONFIRM VIA SIDE EFFECT, NOT ABSENCE OF ERROR: 'the request didn't 500' is not a signal. Require the marker to actually appear in output, or a canary file to appear at a known scratch path inside the OWNED container."
  - "BLIND VARIANT: use a time-delay injection (e.g. `sleep 5`) and require a reproducible, statistically significant delta against a negative-control baseline — a single slow response is noise."
  - "SSH/EXEC-WRAPPER VARIANT: if the sink is argv-based (no shell), test for ARGUMENT injection (e.g. smuggling an extra flag/option) even where metacharacter/shell injection fails — note this separately, it's a distinct primitive from full shell execution."
  - "ESCALATE ONLY within the owned container to retrieve the planted canary/flag. Full RCE artifacts (reverse shell, persistent implant) are Zone-2: STOP and get operator confirm before creating one."
  - "RULE OUT contamination (a generic 500 handler, unrelated slow endpoint) and REPLAY in a fresh session."

emits: [attempt, finding]
---

## What "confirmed" looks like here
An injected command demonstrably **executed** — proven by an observable side effect (marker
output, canary file, or a reproducible timing delta against a negative-control baseline) that
cannot be explained by normal application behavior — reproduced once in a fresh session with
contamination ruled out.

## Boundaries (escalate in order; each rung gated on the prior + scope.md)
1. **argument injection, no execution confirmed** (argv-based sink accepts smuggled flags) — medium.
2. **blind command execution confirmed** (timing/out-of-band signal only) — high.
3. **full shell RCE** (arbitrary command output/canary retrieval) — critical; **operator confirm
   before any artifact**.

## Real disclosed anchor(s) for this class (fix-diff-derived)
Priors/taxonomy from real disclosed GHSA fix commits — the vulnerable pre-patch shape and the guard
the fix added. Verbatim hunks + primary sources in `skills/oracles/references/ghsa-fix-diff-corpus.md`
(OS command injection bucket); consult via the `ghsa-fix-diff` oracle. **These are all *fixed* bugs,
not live-bug claims:** a target matching a removed-line shape is a lead to run through the funnel
above, never a confirmation. The class splits bimodally by fix shape.

**Param-binding (stop interpolating into a shell-parsed string; bind as a positional argument or
disable the shell), `param-binding`:**
- **CVE-2026-31975** (claudecodeui, GHSA-gv8f-wpm2-m5wr, fixed 1.25.0 @ `12e7f07`): client
  `projectPath`/`initialCommand` spliced into `cd "${projectPath}" && ${initialCommand}` run via a
  pty → `shellCommand = initialCommand` with `projectPath` bound out-of-band via
  `cwd: resolvedProjectPath` plus a session-id allowlist regex. Chained with an auth-bypass
  elsewhere in the advisory; WebSocket handler, no shell-metacharacter sanitization pre-fix.
- **CVE-2025-64756** (node-glob, GHSA-5j98-mcp5-4vw2, fixed 11.1.0 @ `1e4e297`): CLI `-c`/`--cmd`
  ran matched filenames through `foregroundChild(cmd, matches, { shell: true })` → matches passed as
  bound positional args via `"$@"`/`"$argv"`, with `shell:true` gated behind an explicit opt-in
  flag. CLI/library vector, attacker-filename-dependent.
- **GHSA-hxwm-x553-x359** (@npmcli/git, fixed 2.0.8 @ `766bfbe`): `gitOpts()` left a caller-supplied
  `shell` option inheritable (spread after defaults) → `shell: false` forced after the spread, so
  spawn always binds git args literally instead of routing through a shell. Library-level,
  reachability-gated on a user-influenced repo/target path.

**Canonicalization (an escape/allowlist check misses a platform- or encoding-level
reinterpretation), `canonicalization`:**
- **CVE-2024-4577** (php-cgi, GHSA-3qgc-jrrr-25jv, fixed 8.1.29/8.2.20/8.3.8 @ `9382673`): on
  Windows, php-cgi's CLI-flag-smuggle check inspected only the raw first byte of `QUERY_STRING` →
  a `WideCharToMultiByte(CP_ACP,...)` remap re-checks the byte the way the OS will before the
  getopt-skip decision. **Pre-auth**, unauthenticated network RCE, CISA KEV.
- **CVE-2026-9277** (shell-quote, GHSA-w7jw-789q-3m8p, fixed 1.8.4 @ `4378a6e`): `quote()` escaped
  object-token `.op` fields with `/(.)/g`, which does not match line terminators (`\n`, `\r`,
  U+2028/2029) → escape regex swapped to `/[\s\S]/g` plus an `OPS` exact-match allowlist and a
  line-terminator guard on glob patterns. Library-level; reachable by any caller quoting an
  attacker-shaped token later run through a shell.

**CONTESTED (illustrative, no promotable guard delta):**
- **CVE-2025-49141** (haxcms-nodejs, GHSA-g4cf-pp4x-hqgw, fixed 11.0.3 @ `5131fea`): the
  authenticated `/gitImportSite` route passed a minimally-validated `site.git.url` into
  `repo.set_remote()`/`repo.pull()`, which shells out via `proc_open()`. The fix deleted the entire
  endpoint rather than adding a sanitizer — a real fix, but there is no removed→added guard shape
  to pattern-match on.

## Not this card
- Template-syntax evaluation inside a sandboxed templating engine, with no shell/exec call
  involved, is `server-side-template-injection`, not this card — even if it can eventually chain
  to code execution.
- A feature that shells out but with the user input strictly allowlist-validated (numeric IDs
  only, enum values only) before it ever reaches the exec call — no injection surface.

## Do not overclaim
- "The request took longer" without a repeatable delta against a negative-control baseline is
  noise, not a blind-command-injection oracle.
- Do not claim "full RCE" from argument injection alone — name the exact primitive (which argument,
  which flag) that would need to chain further, or stop at the rung you actually proved.
- If the class's added-guard shape is already present in the target's source for the reached sink —
  user input bound as a positional argument with the shell disabled, or an allowlist/escape check
  that accounts for platform-level byte canonicalization (see the anchors above) — this path is
  patched; do not claim strong activation without a further, specific reason (an unguarded sibling
  sink, a reachable pre-guard path). Presence of the guard is a strong held signal, not a soundness
  proof.
