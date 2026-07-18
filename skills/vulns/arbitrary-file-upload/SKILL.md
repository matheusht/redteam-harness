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
    - "the stored file's extension/type is derived directly from client-supplied metadata (e.g. a `type.substring(\"image/\".length())` cut off a spoofable Content-Type header) with no fixed mapping, or an extension-allowlist assignment silently targets a property/variable the upload library never actually reads, so the check is a no-op (diff-derived: the Content-Type-substring extension in CVE-2024-24809, the `allowExts` vs `exts` dead-property mismatch in CVE-2025-0520)"
    - "an uploaded archive (zip) is extracted via `extractTo()` or similar with no per-entry filename validation, or a client-controlled destination path is concatenated raw into a write/mkdir call with no containment check, letting an embedded or relocated webshell land at a web-reachable path (diff-derived: GHSA-rf6j-xgqp-wjxg Open eClass, CVE-2026-24897 Erugo)"
  weak:
    - "content-type/magic-byte validation exists but the storage path or serving behavior hasn't been confirmed to execute uploaded content"
  negative:
    - "uploads are stored outside the web root, served with a forced content-type/Content-Disposition, and validated by content sniffing (not just extension) → likely held"
    - "extension/type is mapped through a fixed switch/allowlist keyed off the actual property the upload library reads (not a client-controlled substring or a dead/mismatched property name), and any archive extraction or path-controlled write validates each entry/destination against a containment check before writing → likely held (diff-derived: the MIME->extension switch-allowlist in CVE-2024-24809, the `allowExts`→`exts` property fix in CVE-2025-0520, the per-entry `validateUploadedFile()` loop before `extractTo()` in GHSA-rf6j-xgqp-wjxg, the `realpath()` prefix-containment check in CVE-2026-24897)"

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

oracle: [signal-oracle, adjudication-oracle, ghsa-fix-diff]
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

## Real disclosed anchor(s) for this class (fix-diff-derived)
Priors/taxonomy from real disclosed GHSA fix commits — the vulnerable pre-patch shape and the guard
the fix added. Verbatim hunks + primary sources in `skills/oracles/references/ghsa-fix-diff-corpus.md`
(Unrestricted file upload -> RCE bucket); consult via the `ghsa-fix-diff` oracle. **These are all
*fixed* bugs, not live-bug claims:** a target matching a removed-line shape is a lead to run through
the funnel above, never a confirmation. The bucket is THIN (3 clean IN + 3 CONTESTED across six
products) and splits by guard sub-shape.

**Metadata-derived extension/type swapped for a fixed mapping, `denylist-to-safe-api`:**
- **CVE-2024-24809** (Traccar, GHSA-vhrw-72f6-gwp5, fix commit `1c29f3a`): raw
  `type.substring("image/".length())` taken off a client-spoofable Content-Type header → fixed
  MIME→extension switch-allowlist that throws on unknown types. Authenticated device-image upload
  (advisory separately notes device-id path traversal). `denylist-to-safe-api`.
- **CVE-2025-32028** (haxcms-php, GHSA-vj5q-3jv2-cg5p, fixed 10.0.3 @ `0cde0ae`) — **CONTESTED**
  (illustrative; guard verified but the fix commit is a 22-file, +427/-262 entangled diff): a 4-item
  `strpos()` denylist (`.php`/`.sh`/`.js`/`.css`) fails open on any other server-executable extension
  → `preg_match()` fixed allowlist of safe extensions. Authenticated file-manager upload.

**Allowlist assignment silently bypassed or absent, `exact-match-swap`:**
- **CVE-2025-0520** (ShowDoc, GHSA-6jmr-r7p6-f5wr, fixed 2.8.7 @ `189b6ce`): `$upload->allowExts =
  [...]` set a property the upload library never reads (`exts` is the real one), so the extension
  check was a silent no-op → property renamed to `$upload->exts`, making the allowlist actually
  enforced. Unauthenticated webshell upload + direct execution.
- **CVE-2023-23607** (Dasherr, GHSA-6rgc-2x44-7phq, fixed 1.05.00 @ `445325c`) — **CONTESTED**
  (misattributed fix, illustrative only): unauthenticated `fopen()`/`fwrite()` to a fully
  client-controlled destination path; at the actually-affected tag there was NO extension check at
  all, and the cited "fix" commit is a safe→safe `substr` refinement, not the real closure.

**Archive-extraction / path-controlled-write containment, `allowlist`/`canonicalization`:**
- **GHSA-rf6j-xgqp-wjxg** (Open eClass, fix commit `3f9d267`): admin theme-import ZIP extracted via
  `extractTo()` with no per-entry filename inspection → per-entry `statIndex()` +
  `validateUploadedFile()` loop inserted before extraction. Admin-gated.
- **CVE-2026-24897** (Erugo, GHSA-336w-hgpq-6369, fixed 0.2.15 @ `256bc63`) — **CONTESTED**
  (illustrative; guard verified but entangled across three controllers in one commit): a
  client-controlled `filePaths` segment concatenated raw into a `mkdir()`/write destination → a
  `sanitizePath()` call plus a `realpath()` prefix-containment check gating the write. Reachable by
  any authenticated user regardless of privilege.

## Not this card
- An upload accepted and stored outside the web root with no path to direct request → no
  activation (the storage itself isn't the vuln without reachability).
- Validation that inspects actual file content (magic bytes) rather than just extension/MIME,
  and effectively rejects mismatches → held, not this card.

## Do not overclaim
- "The extension filter was bypassed" is not a finding until the file is fetched and the marker
  comes back.
- Do not claim code execution without the marker being processed by the server, not merely stored.
- If the class's added-guard shape is already present in the target's source for the reached sink —
  a fixed extension/MIME mapping keyed off the property the upload library actually reads, or a
  per-entry filename validation / `realpath()`-containment check gating archive extraction or a
  path-controlled write (see the anchors above) — this path is patched; do not claim strong
  activation without a further, specific reason. Presence of the guard is a strong held signal, not
  a soundness proof.
