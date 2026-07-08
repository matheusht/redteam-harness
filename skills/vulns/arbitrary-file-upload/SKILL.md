---
id: upload.arbitrary-file-upload
name: Arbitrary File Upload
description: >
  Prove an upload endpoint accepts a client-controlled filename/extension/content-type without
  effective server-side validation, letting a caller store a file in a web-reachable path that
  the app should not have accepted — the precondition for code execution or content spoofing.
type: vuln
owasp: "A04:2021 Insecure Design / OWASP File Upload"
atlas: "—"
patterns: []

activation:
  strong:
    - "an upload endpoint accepts a client-controlled filename/extension/content-type and stores the file in a path reachable by direct HTTP request, with validation limited to client-supplied metadata (extension string, MIME header) rather than actual content"
    - "a naive extension allowlist/blocklist is bypassable via double extensions, case variation, null-byte tricks, or trailing characters"
  weak:
    - "content-type/magic-byte validation exists but the storage path or serving behavior hasn't been confirmed to execute uploaded content"
  negative:
    - "uploads are stored outside the web root, served with a forced content-type/Content-Disposition, and validated by content sniffing (not just extension) → likely held"

safe_signal:
  proxy: >
    a predeclared distinctive artifact only reachable by requesting the uploaded file directly —
    e.g. a benchmark's build-time flag in a CTF context, or a benign marker string the operator
    predefined — returned when the stored file is fetched or (if reachable) executed.
  never: >
    do not upload a webshell with real command capability beyond echoing the benign marker; any
    code-execution-class confirmation requires scope.md authorization and an operator confirm
    before the artifact is created.

impact_escalation:
  enabled_by: scope.md#impact_demo_authorized
  requires: human_confirm
  containment: "benign marker file only, contained to the owned container; logged in engagement cleanup.md with a revert (delete the uploaded artifact)"

oracle: [signal-oracle, adjudication-oracle]
severity_rubric: { web_reachable_code_execution: critical, arbitrary_file_stored_reachable_no_exec: high, filter_bypass_no_reachability_confirmed: medium, refused: info }

procedure:
  - "MAP THE UPLOAD PATH: identify the endpoint, what metadata it validates (extension, MIME, magic bytes), and where uploaded files are stored/served from."
  - "BENIGN FINGERPRINT: upload a harmless file with a suspicious extension (e.g. a server-side-executable extension for the stack in use) containing only a benign marker string, no functional payload."
  - "NEGATIVE CONTROL (must decline): an upload with an extension clearly outside any allowlist should be rejected. Record kind=negative_control."
  - "BYPASS ATTEMPTS (benign content only): double extensions, case variation, null-byte/trailing-character tricks, content-type header spoofing — still carrying only the benign marker."
  - "CONFIRM REACHABILITY: request the uploaded file directly. A finding requires the response to carry the exact benign marker — not just a successful upload response."
  - "IF EXECUTABLE: confirm execution via the marker being processed (e.g. reflected via a benign server-side print), not a functional command; escalate to code-execution class only with operator confirm."
  - "RULE OUT contamination (marker guessed or cached elsewhere); REPLAY in a fresh session. CLEAN UP: delete the uploaded artifact and log it in cleanup.md."

emits: [attempt, finding]
---

## What "confirmed" looks like here
An uploaded file with a bypassed or absent server-side validation is **directly reachable** and
returns the **planted benign marker** — either as static content or via execution — where the
negative control (an out-of-allowlist upload) was rejected, reproduced once in a fresh session. A
successful upload response with no confirmed reachability of the stored file is not a finding.

## Boundaries (escalate in order; each rung gated on scope.md)
1. **file stored, reachable, no execution** (e.g. an SVG/HTML file served as-is, content-spoofing risk) → high.
2. **file stored, reachable, executes as code** (e.g. a script extension served by the app server) → critical; **operator confirm before any artifact**, benign marker only.

## Not this card
- An upload accepted and stored outside the web root with no path to direct request → no
  activation (the storage itself isn't the vuln without reachability).
- Validation that inspects actual file content (magic bytes) rather than just extension/MIME,
  and effectively rejects mismatches → held, not this card.

## Do not overclaim
- "The extension filter was bypassed" is not a finding until the file is fetched and the marker
  comes back.
- Do not claim code execution without the marker being processed by the server, not merely stored.
