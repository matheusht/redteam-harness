---
id: deser.insecure-deserialization
name: Insecure Deserialization
description: >
  Prove an application deserializes client-controlled data with a native/unsafe deserializer
  (pickle, Java serialization, PHP unserialize, YAML.load, etc.) without integrity checking or
  type allowlisting, letting a crafted object manipulate application state or execute code.
type: vuln
owasp: "A08:2021 Software and Data Integrity Failures"
atlas: "—"
patterns: []

activation:
  strong:
    - "a client-supplied value (cookie, hidden field, cache blob, message payload) is deserialized with a native/unsafe deserializer with no signature/HMAC check and no type allowlist"
    - "gray-box: a known-gadget-chain library is present in the app's dependency graph, reachable from a deserialization entry point"
  weak:
    - "the format looks serialized (base64 blob, magic bytes for a known serialization format) but the deserialization entry point isn't confirmed reachable from client input"
  negative:
    - "deserialized values are signed/HMAC-verified before processing, or the app uses a safe format (JSON with a fixed schema) instead of native object deserialization → likely held"

safe_signal:
  proxy: >
    a predeclared distinctive artifact only reachable via successful deserialization of a crafted
    object — e.g. a benchmark's build-time flag in a CTF context, or a benign command whose output
    is a canary string the operator predefined, executed inside the OWNED container.
  never: >
    do not use a destructive payload (file deletion, service disruption, persistence
    implantation); any code-execution-class primitive requires scope.md authorization and an
    operator confirm before the artifact is created.

impact_escalation:
  enabled_by: scope.md#impact_demo_authorized
  requires: human_confirm
  containment: "benign canary command only, contained to the owned container; logged in engagement cleanup.md with a revert"

oracle: [signal-oracle, adjudication-oracle]
severity_rubric: { remote_code_execution: critical, object_property_manipulation_no_rce: medium, deserialization_error_disclosure_only: low, refused: info }

procedure:
  - "MAP THE SINK: find every place client-controlled data reaches a native deserializer (cookies, cache, message queues, uploaded state blobs). Note the language/library and whether a gadget chain is plausible."
  - "BENIGN FINGERPRINT: submit a malformed-but-harmless serialized blob to confirm the sink actually deserializes it (a distinct error type/stack trace vs. generic 400 is a weak signal, not confirmation)."
  - "NEGATIVE CONTROL (must decline): a tampered blob without a valid signature/HMAC (if one is expected) should be rejected. Record kind=negative_control."
  - "CRAFT A NON-DESTRUCTIVE OBJECT: build a gadget chain (or use a known one for the library) whose only effect is a benign, detectable side effect — a canary property read, or a canary command whose output is a predeclared string — inside the owned container."
  - "CONFIRM: the response or observable side effect carries the exact canary, not a generic 500 or unrelated error."
  - "ESCALATE to code-execution class ONLY with operator confirm; never chain into a destructive or persistence-establishing payload."
  - "RULE OUT contamination; REPLAY in a fresh session."

emits: [attempt, finding]
---

## What "confirmed" looks like here
A crafted serialized object triggers a **benign, predeclared canary effect** (property manipulation
or command output) that could only occur via deserialization of attacker-controlled data, where the
negative control (tampered/unsigned blob) was rejected, reproduced once in a fresh session. A generic
deserialization error with no observable canary effect is not a finding — it's a coverage note.

## Boundaries (escalate in order; each rung gated on scope.md)
1. **object property manipulation, no code execution** — a detectable but inert side effect → medium.
2. **code execution via gadget chain, benign canary only** → critical; **operator confirm before any artifact**.

## Not this card
- Safe deserialization of client data via a schema-validated format (JSON with fixed types) → no
  activation, this is the secure default.
- A parsing error that discloses a stack trace but no controllable side effect →
  `deserialization_error_disclosure_only`, not code execution.

## Do not overclaim
- "The app uses pickle/Java serialization" is an activation, not a finding — you need the canary
  effect to actually fire.
- Never claim RCE without showing the exact canary output; a plausible gadget chain that wasn't
  actually triggered is `needs_review`, not `confirmed`.
