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
    - "an attacker-named class string (wire protocol field, JSON `@type`/`java-class` property, embedded schema property) is resolved via reflection (Class.forName + constructor invocation) and instantiated with no check that the resolved class belongs to an expected type or trusted package (diff-derived: the unchecked `Class.forName(className)` → `constructor.newInstance()` in CVE-2023-46604, the missing Throwable/allowlist check before `@type` resolution in CVE-2022-25845, the unrestricted `stringableClass.getConstructor(String.class)` in CVE-2025-30065)"
  weak:
    - "the format looks serialized (base64 blob, magic bytes for a known serialization format) but the deserialization entry point isn't confirmed reachable from client input"
  negative:
    - "deserialized values are signed/HMAC-verified before processing, or the app uses a safe format (JSON with a fixed schema) instead of native object deserialization → likely held"
    - "a resolved/attacker-named class is checked against an assignability or package-allowlist gate before reflective instantiation → likely held (diff-derived: `Throwable.class.isAssignableFrom(clazz)` in CVE-2023-46604, the `Throwable`/`autoTypeSupport` + `denyHashCodes` check in CVE-2022-25845, the `SERIALIZABLE_PACKAGES` allowlist `checkSecurity()` in CVE-2025-30065)"

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

oracle: [signal-oracle, adjudication-oracle, ghsa-fix-diff]
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

## Real disclosed anchor(s) for this class (fix-diff-derived)
Priors/taxonomy from real disclosed GHSA fix commits — the vulnerable pre-patch shape and the guard
the fix added. Verbatim hunks + primary sources in `skills/oracles/references/ghsa-fix-diff-corpus.md`
(insecure deserialization -> RCE bucket, CWE-502); consult via the `ghsa-fix-diff` oracle. **These are
all *fixed* bugs, not live-bug claims:** a target matching a removed-line shape is a lead to run
through the funnel above, never a confirmation. All three surviving anchors share one guard shape —
`deser-type-filter`: an assignability or trusted-package allowlist check inserted immediately before a
reflective `Class.forName()`/constructor instantiation of an attacker-named class.

**Reflective instantiation of an attacker-named class, no type filter (`deser-type-filter`):**
- **CVE-2023-46604** (Apache ActiveMQ, GHSA-crg9-44h2-xw35, fixed 5.15.16/5.16.7/5.17.6/5.18.3 @
  `3eaf310`): OpenWire's `createThrowable()` resolves an attacker-supplied class name via
  `Class.forName()` and invokes its String constructor with no check it's actually a `Throwable` →
  `OpenWireUtil.validateIsThrowable(clazz)` (`Throwable.class.isAssignableFrom(clazz)`) inserted
  before instantiation. **Pre-auth**, unauthenticated TCP client of the OpenWire transport (default
  port 61616).
- **CVE-2022-25845** (alibaba/fastjson, GHSA-pv7h-hx5h-mgfj, fixed 1.2.83 @ `35db4ad`): a JSON `@type`
  field naming an Exception/Throwable subclass slipped past both the `denyHashCodes` denylist and the
  `autoTypeSupport` rejection → added `Throwable.class.isAssignableFrom(clazz) && !autoTypeSupport`
  check plus `typeName.endsWith("Exception")` rejection and new `denyHashCodes` entries. Reachable
  from any attacker-controlled JSON passed to `JSON.parse()`/`JSON.parseObject()`.
- **CVE-2025-30065** (apache/parquet-java, GHSA-2c59-37c4-qrx5, fixed 1.15.1 @ `680edfa`):
  parquet-avro's `FieldStringableConverter` reflectively instantiates the class named by a Parquet
  file's embedded Avro schema `java-class` property with no restriction → `checkSecurity(clazz)`
  allowlisting against `SERIALIZABLE_PACKAGES` before the constructor call. Triggered purely by
  reading an attacker-supplied Parquet file, no auth involved.

Bucket note: this bucket is THIN (only 3 clean IN anchors, 0 CONTESTED) — most CWE-502 candidates
(Jenkins, PyYAML, Struts/XStream, jackson-databind, Tomcat, Solr, SnakeYAML, H2) were dropped on
mechanism mismatch or an unresolvable/unverifiable fix commit. Treat the 3 anchors above as priors for
the reflective-instantiation sub-shape specifically, not full coverage of the deserialization class —
gadget-chain RCE via `pickle`/PHP `unserialize`/Java native serialization without a named-class
resolution step isn't represented here.

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
- If the class's added-guard shape is already present in the target's source for the reached sink —
  an assignability check or trusted-package allowlist gating the resolved class before reflective
  instantiation, or a signature/HMAC check gating the deserialized blob itself (see the anchors
  above) — this path is patched; do not claim strong activation without a further, specific reason.
  Presence of the guard is a strong held signal, not a soundness proof.
