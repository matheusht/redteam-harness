---
id: httpabuse.http-protocol-abuse
name: HTTP Protocol-Semantics Abuse (Smuggling / Method Tamper / Race)
description: >
  Three related HTTP-semantics abuses, documented as variants of one card because each exploits a
  gap between how the app THINKS a request will be parsed/sequenced and how it actually is:
  request smuggling/desync (front-end/back-end parsing disagreement), HTTP method tampering (a
  check written for one verb, bypassed via another), and race conditions (a check-then-use
  operation not made atomic). Each variant needs its own confirm — do not conflate them.
type: vuln
owasp: "A05:2021 Security Misconfiguration / HTTP Request Smuggling"
atlas: "—"

activation:
  strong:
    - "smuggling: a reverse proxy sits in front of an origin server and the pair's handling of Content-Length vs Transfer-Encoding (or duplicate/malformed headers) is not obviously unified"
    - "method tampering: an authz or validation check is implemented against one specific HTTP method (e.g. only checked on POST) while the same route/action is reachable via another verb (GET/HEAD/PUT/TRACE) or via an override header (X-HTTP-Method-Override)"
    - "race: a single-use or capacity-limited resource (coupon, invite, balance, stock count) follows a read-check-then-write pattern with no visible lock/transaction/idempotency key"
  weak:
    - "a proxy/origin pair of unknown vendor combination with no yet-observed parsing disagreement"
    - "a resource has a stated limit but concurrency has not yet been attempted"
  negative:
    - "proxy and origin agree on a single canonical parsing of length/framing headers → smuggling held"
    - "the authz/validation check is enforced identically regardless of method/override header → tampering held"
    - "the operation is wrapped in a transaction/lock/idempotency key that holds under concurrent load → race held"

safe_signal:
  proxy: >
    a predeclared distinctive artifact only reachable via successful exploitation of the specific
    variant tested — a benchmark's build-time flag revealed by the desync/tamper/race, or (in a
    live app) an observable second-response artifact for smuggling, a successful protected action
    for method tampering, or a resource consumed MORE times than its stated limit for a race —
    each using only owned/synthetic accounts and resources.
  never: >
    do not run smuggling probes or race floods against shared/production infrastructure without
    explicit scope.md authorization; bound concurrency to what scope.md's concurrency setting
    allows; never target real users' resources.

impact_escalation:
  enabled_by: scope.md#impact_demo_authorized
  requires: human_confirm
  containment: "probes against owned/synthetic resources only; logged in cleanup.md with a revert (e.g. resetting an overused coupon)"

oracle: [signal-oracle, adjudication-oracle]
severity_rubric: { confirmed_smuggling_or_multi_use_of_single_use_resource: critical, method_tamper_bypasses_authz: high, timing_anomaly_suggestive_not_confirmed: needs_review }

procedure:
  - "PICK ONE VARIANT FIRST — smuggling, method tampering, or race — each has a distinct confirm and none substitutes for another."
  - "SMUGGLING: send a benign, non-destructive probe request with ambiguous framing (conflicting/duplicate Content-Length/Transfer-Encoding) and look for an observable desync artifact (a second, unexpected response; a subsequent unrelated request receiving your probe's leftover body). A theoretical framing mismatch with no observed artifact is not a finding."
  - "METHOD TAMPERING: identify the primary verb a protected action checks, then attempt the SAME action via an alternate verb or override header. Confirm requires the protected action to actually SUCCEED via the alternate path where the primary path is correctly blocked — not just 'the alternate verb returned 200 on an unrelated read'."
  - "RACE: identify a single-use or capacity-limited resource, then fire a bounded burst of concurrent requests against it (own account/resource only) and COUNT actual overuse (the resource consumed more times than its stated limit) — do not infer a race from response timing alone."
  - "NEGATIVE CONTROL per variant: a well-formed single request must behave correctly (smuggling: no desync; tampering: primary verb correctly blocked; race: sequential requests respect the limit) — proving the bug is in the concurrent/alternate path, not a broken check entirely."
  - "REPLAY: reproduce the confirmed variant once more (fresh session / fresh resource instance) before calling it confirmed."

emits: [attempt, finding]
---

## What "confirmed" looks like here
**Smuggling:** an observable desync artifact from a benign probe, reproduced once. **Method
tampering:** the same protected action succeeded via an alternate verb/header where the primary
verb correctly declined, reproduced once. **Race:** a counted overuse of a stated-limit resource
under concurrent requests you fired, reproduced once. A theoretical framing mismatch, an untested
alternate verb, or an unmeasured "it might race" is not a finding for any variant.

## Not this card
- An authz check bypassed by changing a URL parameter/id rather than the HTTP method →
  `bola.broken-object-level-authz`.
- A resource abused via legitimate repeated sequential use within its actual limit → not a race,
  by definition.

## Do not overclaim
- "The proxy and origin are different vendors" or "there's no visible mutex" is an activation, not
  a finding.
- State which variant, the exact observed artifact (response, session, or overuse count), and the
  negative control that isolates it, or it's `needs_review`, never `confirmed`.
