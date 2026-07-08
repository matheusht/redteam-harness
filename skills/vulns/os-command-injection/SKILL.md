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
  weak:
    - "input reaches an exec call but through an argv array (no shell interpretation) — argument injection may still be possible even without metacharacter execution"
    - "a wrapper library is used that claims to sanitize shell input but has known bypass classes for its version"
  negative:
    - "input never reaches a shell/exec call — pure library calls with no subprocess invocation → likely held"
    - "metacharacters are strictly allowlist-validated (not blocklisted) before any exec call → likely held"

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

oracle: [signal-oracle, adjudication-oracle]
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
