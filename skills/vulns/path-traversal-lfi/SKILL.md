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
    - "the containment/allowlist check runs against the raw path before it is decoded or made absolute — e.g. a prefix check against a non-absolute template directory, or an allowlist match against a still-percent-encoded request path — so relative or encoded traversal slips past the guard (diff-derived: the missing `filepath.Abs()` in CVE-2023-37896, the pre-decode `allowedFiles`/`startsWith` check in CVE-2023-32235)"
    - "an archive-extraction or raw-read feature joins a caller/archive-controlled path (symlink target, `db`/file param) straight into a filesystem call with no `startsWith(cwd)`-style containment or sanitizer wrap (diff-derived: the unchecked `header.linkname` join in CVE-2024-12905, the raw `$db` concatenation in CVE-2025-29789)"
  weak:
    - "the field is partially templated (a fixed prefix/suffix around caller input) — escape depends on how much of the path the caller controls"
    - "extension is appended after caller input, narrowing but not eliminating reachable files"
  negative:
    - "the path is canonicalized (resolved to an absolute path) and checked to remain within an allowlisted base directory before the read → likely held"
    - "the value is an opaque id resolved server-side, never a real path fragment"
    - "the path is decoded/normalized and re-checked against the allowlist AFTER decoding (not before), or an archive extractor resolves both the extraction cwd and the link target to absolute paths and rejects any target that doesn't `startsWith(cwd)` → likely held (diff-derived: the `decode()`+`path.normalize()` reorder in CVE-2023-32235, the `path.resolve(cwd)` + `inCwd()` check in CVE-2024-12905)"

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

oracle: [signal-oracle, adjudication-oracle, ghsa-fix-diff]
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

## Real disclosed anchor(s) for this class (fix-diff-derived)
Priors/taxonomy from real disclosed GHSA fix commits — the vulnerable pre-patch shape and the guard
the fix added. Verbatim hunks + primary sources in `skills/oracles/references/ghsa-fix-diff-corpus.md`
(Path traversal / LFI bucket); consult via the `ghsa-fix-diff` oracle. **These are all *fixed* bugs,
not live-bug claims:** a target matching a removed-line shape is a lead to run through the funnel
above, never a confirmation. The dominant shape is a missing canonicalization step before the
containment check; two variants (bound-containment on archive extraction, denylist swapped for a
safe API) round out the bucket.

**Canonicalize-then-contain (decode/absolutize before the prefix/allowlist check), `canonicalization`:**
- **CVE-2023-37896** (nuclei, GHSA-2xx4-jj5v-6mff, fixed 2.9.9 @ `e5154d3`): a relative
  `templatePath` fed a `HasPrefix` containment check with no prior `filepath.Abs()` → guard adds the
  absolutize call before the prefix check. Go-SDK sandbox mode, arbitrary local file read.
- **CVE-2023-32235** (Ghost, GHSA-wf7x-fh6w-34r6, fixed 5.42.1 @ `378dd91`): the static-theme
  allowlist check (`allowedFiles`/`startsWith(allowedPath)`) ran against the raw, still
  percent-encoded request path → guard adds `decode(file)` + `path.normalize()` before the check.
  Pre-auth `GET /assets/*`, arbitrary file read.
- **CVE-2025-29789** (OpenEMR, GHSA-ffpq-2wqj-v8ff, fixed 7.3.0 @ `8c5332f`): the `db` GET param
  concatenated raw onto `fileroot/contrib/` → guard wraps it in `check_file_dir_name($db)`.
  Authenticated admin ("Load Code") feature.

**Bound/containment on archive extraction, `bound`:**
- **CVE-2024-12905** (tar-fs, GHSA-pq67-2wwv-3xjx, fixed 1.16.4/2.1.2/3.0.7 @ `a1dd7e7`):
  symlink/hardlink targets from a tar archive were joined into the extraction cwd with no
  containment check → guard resolves both `cwd` and `dst` to absolute paths and rejects any target
  where `!dst.startsWith(cwd)`. Untrusted tar archive extraction, arbitrary read/overwrite.

**Denylist → safe-API swap, `denylist-to-safe-api`:**
- **CVE-2023-39584** (hexo, GHSA-x2jc-989c-47q4, fixed 7.2.0 @ `b5b63ca`): the `{% include_code %}`
  tag read an attacker-influenced path directly via `readFile(join(source_dir, codeDir, path))` with
  no containment check → guard replaces the raw FS read with a `Page.findOne({source})` model lookup
  that only ever serves registered site files.
- **CVE-2025-68428** (jsPDF, GHSA-f8cm-6447-x5h2, fixed 4.0.0 @ `a688c8f`) — **CONTESTED**
  (illustrative — genuine gate, but the fix hunk is entangled with an unrelated this-binding/strict-mode
  refactor): `loadFile()`/`nodeReadFile()` resolved caller-supplied paths and read them with no gate →
  guard adds an opt-in `allowFsRead`/process-permission check plus `fs.realpathSync()` canonicalization
  before the read.

## Not this card
- A field that only selects among a fixed, server-enumerated set of files (no path fragment reaches the caller) → no traversal surface.
- SSRF via a URL-shaped field, not a filesystem path → route to `pattern.ssrf-server-side-fetch` instead.

## Do not overclaim
- "The traversal sequence wasn't stripped" proves nothing until the canary's content actually comes back.
- Name the exact directory boundary crossed in one sentence, or it isn't confirmed.
- If the class's added-guard shape is already present in the target's source for the reached sink —
  the path is decoded/absolutized/normalized *before* the prefix/allowlist containment check, or an
  archive extractor resolves both sides and enforces `dst.startsWith(cwd)` (see the anchors above) —
  this path is patched; do not claim strong activation without a further, specific reason (an
  unguarded sibling sink, a reachable pre-guard path). Presence of the guard is a strong held signal,
  not a soundness proof.
