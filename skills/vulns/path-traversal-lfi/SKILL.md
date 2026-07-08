---
id: patht.path-traversal-lfi
name: Path Traversal / Local File Inclusion
description: >
  Prove a user-supplied filename/path parameter reaches a filesystem read or include operation
  without canonicalization and an allowlist, letting the caller escape the intended directory
  (../ sequences, encoded/double-encoded traversal, null-byte tricks) to read or include a file
  the app never intended to expose.
type: vuln
owasp: "A01:2021 Broken Access Control (Path Traversal) / A05 LFI"
atlas: "—"
patterns: []

activation:
  strong:
    - "a request field (filename, path, template, page, file, doc) is concatenated or joined into a filesystem read/include call without canonicalizing and re-validating against a base directory"
    - "traversal sequences (../, encoded %2e%2e/, double-encoded, backslash variants) are accepted unmodified in that field"
    - "an include/render/template-load feature accepts a caller-influenced path (LFI-to-RCE surface via log poisoning, session file inclusion, or wrapper abuse)"
  weak:
    - "the field is partially templated (a fixed prefix/suffix around caller input) — escape depends on how much of the path the caller controls"
    - "extension is appended after caller input, narrowing but not eliminating reachable files"
  negative:
    - "the path is canonicalized (resolved to an absolute path) and checked to remain within an allowlisted base directory before the read → likely held"
    - "the value is an opaque id resolved server-side, never a real path fragment"

safe_signal:
  proxy: >
    a predeclared distinctive artifact only reachable via successful traversal/inclusion — e.g. a
    benchmark's build-time flag in a CTF context, or an operator-planted canary file placed inside
    the OWNED container/test path in a live app — returned verbatim in the response.
  never: >
    do not traverse to real host secrets, credentials, or paths outside the sandbox/owned
    container; escalation past the app's own directory boundary to the underlying host requires
    scope.md authorization AND an operator confirm before any artifact.

impact_escalation:
  enabled_by: scope.md#impact_demo_authorized
  requires: human_confirm
  containment: "read-only within the owned container; no writes; logged in engagement cleanup.md"

oracle: [signal-oracle, adjudication-oracle]
severity_rubric: { arbitrary_file_read_rce_chain: critical, arbitrary_file_read: high, restricted_directory_read: medium, refused: info }

procedure:
  - "MAP THE SINK: find every field that names or influences a filesystem path passed to a read/include/template call. Note any prefix/suffix templating around it."
  - "BENIGN FINGERPRINT: request a KNOWN-SAFE file the operator controls, or a canary planted inside the same container, using a single '../' to confirm the sink is reachable at all before trying to escape further."
  - "NEGATIVE CONTROL (must decline): the same request with the traversal sequence stripped/encoded-normalized should NOT return content outside the intended base directory. Record kind=negative_control."
  - "ESCALATE ENCODING: if raw '../' is filtered, try percent-encoded, double-encoded, and null-byte variants — only to the point of confirming the canary, not to enumerate the host."
  - "CONFIRM: the response must carry the PLANTED canary's exact content, not a generic error or an in-bounds file."
  - "STOP at the scope.md ceiling — do not pursue LFI-to-RCE (log poisoning, wrapper abuse) without explicit scope and operator confirm; note it as a routed escalation, not an assumed finding."
  - "RULE OUT contamination (the canary value cached/known some other way); REPLAY in a fresh session."

emits: [attempt, finding]
---

## What "confirmed" looks like here
A request with a traversal/inclusion payload returns the **planted canary's exact content** from
outside the intended base directory, where the **matched negative control declined** (same request,
traversal normalized/stripped, stays in-bounds), reproduced once in a fresh session with
contamination ruled out. A 200 with in-bounds content is not this vuln. A 404 or a sanitized path on
the traversal attempt is the secure outcome.

## Escalation (gated on scope.md, in order)
1. **in-app file read** — a file the app itself manages but shouldn't expose via this field → medium/high.
2. **arbitrary file read within the container** — reaches files outside the app's own directory but still inside the sandbox → high.
3. **LFI-to-RCE chain** (log poisoning, php://filter/wrapper abuse, session file inclusion) → critical; **operator confirm before any artifact**, and only a benign canary command, never a real payload.

## Not this card
- A field that only selects among a fixed, server-enumerated set of files (no path fragment reaches the caller) → no traversal surface.
- SSRF via a URL-shaped field, not a filesystem path → route to `pattern.ssrf-server-side-fetch` instead.

## Do not overclaim
- "The traversal sequence wasn't stripped" proves nothing until the canary's content actually comes back.
- Name the exact directory boundary crossed in one sentence, or it isn't confirmed.
