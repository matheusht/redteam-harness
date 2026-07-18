---
id: infodisc.information-disclosure
name: Information Disclosure
description: >
  Prove the app leaks internal state — stack traces, debug/admin surfaces, source control or
  backup artifacts, directory listings, or version banners — that a caller should never see. The
  objective — confirmed only when the disclosed content carries a distinctive, verifiably-internal
  marker, not generic boilerplate.
type: vuln
owasp: "A01:2021/A05:2021 Security Misconfiguration"
atlas: "—"
patterns: []

activation:
  strong:
    - "an error response includes a stack trace, file path, or internal exception type"
    - "a debug endpoint, admin panel, or diagnostics route is reachable without authentication"
    - "source control or backup artifacts are exposed (.git, .env, .bak, ~, .swp, config dumps)"
    - "directory listing is enabled on a path that should be opaque"
    - "a server-side fetch to a caller-influenced URL/hostname returns the raw upstream response body (or a downstream cloud-metadata/internal-service reply) straight to the caller with no destination check — the fetch-and-echo variant (diff-derived: the raw `file_get_contents($url); echo $result` in CVE-2024-36414, the unguarded `http.Get(originUrl)` reaching the metadata endpoint in CVE-2025-59146)"
  weak:
    - "a version/banner header discloses a component version without further reachable detail"
  negative:
    - "errors are caught and rendered as generic messages with no internal detail → likely held"
    - "diagnostic/debug routes require the same auth as the rest of the app → likely held"
    - "a destination allowlist/filter (or response-format constraint) sits between a caller-supplied URL/hostname and the outbound fetch, so raw responses from arbitrary or internal hosts are never returned to the caller → likely held (diff-derived: the `ValidateURLWithFetchSetting(...)` guard inserted before `http.Get(originUrl)` in CVE-2025-59146; the vulnerable fetch-and-echo handler deleted outright rather than gated in CVE-2024-36414)"

safe_signal:
  proxy: >
    a predeclared distinctive artifact only reachable via successful exploitation of this
    vulnerability class — e.g. a benchmark's build-time flag in a CTF context, or an internal path,
    filename, or config key that only exists server-side in a live app. The signal is the
    artifact's presence in a captured response, never a vibe about "too much detail."
  never: >
    do not store or persist any REAL secret/credential/key surfaced this way — if one appears
    unexpectedly, treat it as a Zone-2 event: redact immediately, do not log the value, get
    operator confirm before any further step.

impact_escalation:
  enabled_by: scope.md#impact_demo_authorized
  requires: human_confirm
  containment: "no real secret is ever stored; redact and confirm before any artifact referencing it"

oracle: [signal-oracle, adjudication-oracle, ghsa-fix-diff]
severity_rubric: { credentials_or_keys_disclosed: critical, internal_source_or_stacktrace: high, version_banner_only: low }

procedure:
  - "PASSIVE FIRST: unlike attack-shaped cards, disclosure is often triggered just by normal use or a malformed request — check error pages, common backup/debug paths, and response headers before attempting anything adversarial."
  - "IDENTIFY THE MARKER: the disclosed content must contain something a caller could not otherwise know — an internal path, a real filename, a stack frame, a version string tied to a known component."
  - "NEGATIVE CONTROL: confirm the same request path/verb without the triggering condition (malformed input, missing auth) does NOT disclose the same detail."
  - "RULE OUT boilerplate: a generic 'Internal Server Error' or a public-facing version string with no further reachable surface is not a finding — it's coverage."
  - "IF A REAL SECRET APPEARS: stop, redact, do not store the value, escalate to operator confirm before continuing."
  - "REPLAY in a fresh session/request to rule out a one-off fluke."

emits: [attempt, finding]
---

## What "confirmed" looks like here
A response (error page, debug route, exposed file, directory listing) contains a distinctive,
verifiably-internal marker — not generic boilerplate — reproduced on replay, with a matched
negative control (the non-triggering request) declining to show the same detail.

## Real disclosed anchor(s) for this class (fix-diff-derived)
Priors/taxonomy from real disclosed GHSA fix commits — the vulnerable pre-patch shape and the guard
the fix added. Verbatim hunks + primary sources in `skills/oracles/references/ghsa-fix-diff-corpus.md`
(SSRF bucket, CWE-918); consult via the `ghsa-fix-diff` oracle. **These are all *fixed* bugs, not
live-bug claims:** a target matching a removed-line shape is a lead to run through the funnel above,
never a confirmation. The SSRF bucket is a **partial/umbrella match** for this card — it also grounds
the narrower `skills/patterns/ssrf-server-side-fetch` pattern card, so only the anchors below where the
fix's core defect is the outbound response (or the credentials it carries) being handed back to the
caller are cited here; the routing/redirect-only variants in that bucket (host-header confusion,
protocol-relative-URL bypass) belong to the SSRF pattern card, not this one.

**Fetch-and-echo (the raw upstream response body is returned to the caller), `canonicalization`/other:**
- **CVE-2020-13379** (grafana, GHSA-wc9w-wvq2-ffm9, fixed 6.7.4 / 7.0.2 @ `ba953be`): unauthenticated
  avatar handler took the path-derived value verbatim as the fetch target and echoed the response →
  32-hex-char MD5 format regex applied before the fetch. Unauthenticated; enables internal-network
  reconnaissance via the echoed reply. `canonicalization`.
- **CVE-2024-36414** (SuiteCRM, GHSA-wg74-772c-8gr7, fixed 7.14.4 / 8.6.1 @ `504d6f0`) — **CONTESTED**
  (illustrative): `action_CallRest` took a fully caller-supplied `url`, only checked the scheme, then
  `file_get_contents($url)` and echoed the body straight back to the client → the vulnerable handler
  body was deleted outright (no replacement guard to promote). Authenticated fetch-and-echo proxy.

**Destination reaches a credential-bearing internal service (metadata endpoint), `bound`:**
- **CVE-2025-59146** (new-api, GHSA-xxv6-m6fx-vfhh, fixed 0.9.0.5 @ `ef63416`): any authenticated user
  could hand the LLM-gateway a URL to fetch with no destination check, reaching the cloud metadata
  endpoint (169.254.169.254) and disclosing credentials → `ValidateURLWithFetchSetting(...)`
  destination-filter (private-IP/domain/IP allowlist) inserted immediately before the `http.Get`
  sink. Authenticated; critical impact is the metadata credential theft, not the fetch itself.
- **CVE-2025-64430** (parse-server, GHSA-x4qj-2f4q-r4rx, fixed 7.5.4 / 8.4.0-alpha.1 @ `8bbe3ef`) —
  **CONTESTED** (illustrative): a file-upload's `_source.uri` was fetched server-side via `http.get`
  with no destination check and the response stored/returned as the file's content → the URI-fetch
  code path and its call site were deleted outright (no added guard). Authenticated upload path.

## Not this card
- A generic error message with no internal detail → no signal.
- A version banner alone, with no further reachable debug/admin surface → weak activation only,
  route to known-cve-exploitation if a matching CVE exists, don't claim disclosure by itself.

## Do not overclaim
- "There was a stack trace" is not a finding until you name the specific internal detail it
  revealed and show a caller without the triggering condition does not see it.
- A real secret surfacing is not a bigger "win" — it's an immediate containment obligation.
- If the class's added-guard shape is already present in the target's source for the reached
  fetch/proxy sink — a destination allowlist/filter, a response-format constraint, or the vulnerable
  fetch-and-echo path removed outright (see the anchors above) — this path is patched; do not claim
  strong activation without a further, specific reason (an unguarded sibling sink, a reachable
  pre-guard path). Presence of the guard is a strong held signal, not a soundness proof.
