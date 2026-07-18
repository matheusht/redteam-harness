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
    - "smuggling: the front-end and origin parsers each tolerate a header shape the other would reject — an empty/zero-length header name, simultaneous conflicting Transfer-Encoding + Content-Length, a bare LF with no preceding CR, or control characters (0x1c-0x1f) left unvalidated in a header name — with no single shared canonical rejection between the two (diff-derived: the missing zero-length-name check in CVE-2023-25725, the accepted dual TE+CL in CVE-2024-23452, the missing control-char/OWS validation in CVE-2021-43797 — see the anchors section)"
    - "smuggling: a chunked-body or upgrade-response reader assumes a fixed shape (exactly one trailer line, CRLF-only chunk extensions, any non-101 status clearing an upgrade pause) instead of parsing to the true boundary, leaving room for attacker-controlled padding a peer parser reads differently (diff-derived: the fixed-line trailer assumption in CVE-2023-40175 / CVE-2025-58068, the unvalidated quoted chunk-extension in CVE-2026-2332, the accept-any-non-101 upgrade path in CVE-2024-23326)"
  weak:
    - "a proxy/origin pair of unknown vendor combination with no yet-observed parsing disagreement"
    - "a resource has a stated limit but concurrency has not yet been attempted"
  negative:
    - "proxy and origin agree on a single canonical parsing of length/framing headers → smuggling held"
    - "both sides fail closed on malformed/conflicting framing — reject an empty header name, reject dual Transfer-Encoding + Content-Length, reject a bare LF, and parse chunked trailers/extensions to their true boundary rather than assuming a fixed shape — using the same guard on both parsers → smuggling likely held (diff-derived: the zero-length-name reject replicated across HTTP/1/HPACK/QPACK in CVE-2023-25725, the dual TE+CL reject in CVE-2024-23452, the empty-Content-Length reject in CVE-2023-40175)"
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

oracle: [signal-oracle, adjudication-oracle, ghsa-fix-diff]
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

## Real disclosed anchor(s) for this class (fix-diff-derived)
Priors/taxonomy from real disclosed GHSA fix commits — the vulnerable pre-patch shape and the guard
the fix added. Verbatim hunks + primary sources in `skills/oracles/references/ghsa-fix-diff-corpus.md`
(HTTP request smuggling bucket); consult via the `ghsa-fix-diff` oracle. **These are all *fixed*
bugs, not live-bug claims:** a target matching a removed-line shape is a lead to run through the
funnel above, never a confirmation. **PARTIAL / SCOPED:** these anchors cover only the *smuggling*
variant of this card (CWE-444) — method tampering and races have no corpus bucket here. The class
splits by whether the fix is a fail-closed rejection at the parser boundary or a parser-completeness
fix for a chunked/upgrade edge case.

**Fail-closed rejection on malformed/conflicting header framing, `reject-on-malformed`:**
- **CVE-2023-25725** (HAProxy, fixed @ `a0e561a`): a zero-length header name passed through unchecked
  → identical empty-name rejection added at three independent parser sites — HTTP/1 (`h1.c`), HPACK
  (`hpack-dec.c`), and QPACK (`qpack-dec.c`). Pre-auth, all three protocol versions.
- **CVE-2024-23452 (GHSA-2862-59r4-c989)** (Apache bRPC, fixed @ `09b9600`): simultaneous
  Transfer-Encoding + Content-Length accepted → `on_headers_complete` now rejects the pair
  fail-closed, with an opt-in `allow_chunked_length` gflag escape hatch. Pre-auth RPC framing.
- **CVE-2023-40175 (GHSA-68xg-gqqm-vgj8)** (Puma, fixed @ `690155e`): an empty-string Content-Length
  slipped past the digit-only validator → `|| cl.empty?` added to the reject condition. Pre-auth
  application-server parsing.
- **CVE-2021-43797 (GHSA-wx5j-54mm-rqqq)** (Netty, fixed 4.1.71.Final @ `07aa6b5`): OWS validation
  skipped on the header-name side and control chars 0x1c-0x1f left unblocked → OWS made mandatory
  on both sides + the control-char range added to the name denylist. Pre-auth, any inbound HTTP/1.x
  parse (server or proxy role).
- **CVE-2023-27493 (GHSA-w5w5-487h-qv8q)** (Envoy, fixed @ `3a9df1f`): outbound header serialization
  had no character validation → an allowlist char-table gate (`headerNameIsValid`/`headerValueIsValid`)
  wired into the HTTP/1, HTTP/2, and QUIC upstream encode paths. Outbound proxy→upstream direction,
  reloadable-flag gated.

**Parser-completeness gaps for chunked encoding and upgrade responses, `state-machine-completeness`:**
- **CVE-2026-2332 (GHSA-355h-qmc2-wpwf)** (Jetty, fixed @ `ef62411`): an LF embedded inside a quoted
  chunk-extension string was accepted silently → `_chunkExtInQuote`/`_chunkExtQuotedPair` state added,
  now throws on embedded LF. Pre-auth chunked-body parsing.
- **CVE-2025-58068 (GHSA-hw6f-rjfj-j7j7)** (Eventlet, fixed @ `0bfebd1`): the trailer section after
  a terminal 0-length chunk was assumed to be exactly one line → replaced with a loop that discards
  to the blank line, handling an arbitrary trailer section. Same gap class as CVE-2023-40175's
  second hunk above. Pre-auth chunked-body reading.
- **CVE-2024-23326 (GHSA-vcf8-7238-v74c)** (Envoy, fixed @ `3f4475b`): any non-101 upstream response
  cleared the paused-for-upgrade state → fail-closed status-code allowlist (only `101` clears the
  pause, else rejected). Reloadable-flag gated, upgrade/websocket handshake path.
- **CVE-2024-53868** (Apache Traffic Server, fixed @ `ffbcfee`) — **CONTESTED** (illustrative): a bare
  LF with no preceding CR was accepted in the chunk-size line → reject-on-bare-LF added, gated by a
  new `strict_chunk_parsing` config (default-on). Genuine CWE-444 fix, but entangled in a 16-file
  config-plumbing commit — not cleanly isolable, kept illustrative only.

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
- If the class's added-guard shape is already present in the target's source for the reached sink —
  a fail-closed rejection of malformed/conflicting framing, or a parser that consumes chunked
  trailers/extensions to their true boundary rather than assuming a fixed shape (see the anchors
  above) — this path is patched; do not claim strong activation without a further specific reason.
  Presence of the guard is a strong held signal, not a soundness proof.
