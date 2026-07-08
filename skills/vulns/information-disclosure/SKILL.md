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
  weak:
    - "a version/banner header discloses a component version without further reachable detail"
  negative:
    - "errors are caught and rendered as generic messages with no internal detail → likely held"
    - "diagnostic/debug routes require the same auth as the rest of the app → likely held"

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

oracle: [signal-oracle, adjudication-oracle]
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

## Not this card
- A generic error message with no internal detail → no signal.
- A version banner alone, with no further reachable debug/admin surface → weak activation only,
  route to known-cve-exploitation if a matching CVE exists, don't claim disclosure by itself.

## Do not overclaim
- "There was a stack trace" is not a finding until you name the specific internal detail it
  revealed and show a caller without the triggering condition does not see it.
- A real secret surfacing is not a bigger "win" — it's an immediate containment obligation.
