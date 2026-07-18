---
id: pattern.ssrf-server-side-fetch
name: Server-Side Fetch Of A Client-Supplied URL
description: >
  The server (or an agent tool) fetches a URL that the client supplies — avatar import, link preview,
  webhook, "fetch this document", a tool that takes a url argument. If the destination is not
  constrained to an allowlist, the request can be pointed at internal services or cloud metadata. The
  SSRF shape. Scoped pattern: recognize and ROUTE TO REVIEW; it does not authorize internal probing.
type: pattern
owasp: "A10:2021 Server-Side Request Forgery / API7-style"
also: "LLM06 Excessive Agency when the fetch is an agent tool taking a url argument"
atlas: "—"
routes_to: ["stub:vulns/server-side-request-forgery"]

activation:
  strong:
    - "the server or an agent tool fetches a URL TAKEN FROM CLIENT INPUT (request body/query field, or a tool `url`/`endpoint`/`callback` argument) — presence of a client-controlled fetch destination is strong, on sight; you do NOT need to have already reached an internal host"
    - "a webhook, callback URL, avatar importer, link previewer, import-from-url, or document fetcher accepts a client-named destination and performs the fetch asynchronously"
    - "the server follows a redirect from an allowed/client-supplied URL to a second destination; redirect-follow bypass is a distinct sub-shape"
    - "a sibling/newer route or tool constrains the destination to an allowlist while this one does not (the differential says the team knows it needs constraining — co-activate pattern.legacy-route-differential)"
    - "the outbound call is made straight from the client-supplied value with no pre-fetch destination check in front of the sink — e.g. a bare `http.Get(originUrl)` / `file_get_contents($_REQUEST['url'])` guarded (if at all) only by a scheme-prefix check, not a host/IP allowlist (diff-derived: the removed unguarded `return http.Get(originUrl)` in CVE-2025-59146, the `preg_match('/^http[s]{0,1}:\\/\\//' )`-only check in CVE-2024-36414 — see the anchors section)"
    - "an absolute-URL / same-origin check treats a scheme-optional or protocol-relative form as already-safe, or a redirect/rebuild step trusts a request-supplied value (e.g. the `Host` header) to reconstruct the fetch target (diff-derived: axios's optional-scheme `isAbsoluteURL` regex in CVE-2024-39338, the `Host`-header-sourced `originalHost.value` in Next.js CVE-2024-34351)"
  weak:
    - "the fetch destination is client-influenced but partly templated (a path or id appended to a fixed host) — reachability depends on how much of the host the client controls"
    - "a redirect is followed server-side, so an allowlisted host can bounce to an arbitrary one"
  negative:
    - "the destination is validated against a strict allowlist of external hosts before the fetch, with redirects disabled and internal/loopback/link-local ranges denied → defense holds, record as held"
    - "the 'url' is actually an opaque server-side id the client cannot steer to a network destination"
    - "the supplied URL is only reflected, stored, or queued, and no server-side fetch reaches a controlled canary endpoint"
    - "a destination allowlist/filter function (host+IP allowlist, private-IP denial) or a strict input-format constraint is invoked immediately before the outbound sink, and the scheme-capture in any absolute-URL check is mandatory (not optional) → likely held (diff-derived: `is_allowed_hostname()` gating the outbound call in CVE-2024-31461, `ValidateURLWithFetchSetting(...)` inserted right before `http.Get(originUrl)` in CVE-2025-59146, the mandatory-scheme `isAbsoluteURL` regex in CVE-2024-39338)"
---

# Server-side fetch of a client-supplied URL

> **Activation vs adjudication (load-bearing).** Activation keys on the server fetching a
> *client-controlled destination* — that is **strong**, on sight. Whether it actually reaches an
> internal service, cloud metadata, or only allowlisted hosts is the **adjudication** question
> (held vs exploited), decided later under scope — NOT a precondition for a strong activation.

> **Scope posture (load-bearing).** This card recognizes the shape and routes to **review / held**.
> It does **not** authorize probing internal ranges. Loopback (`127.0.0.0/8`), link-local cloud
> metadata (`169.254.169.254`), and other internal/private ranges are **review-gated** — operator
> confirmation in `scope.md` is required before any internal-destination probe. Default safe signal is
> a **controlled external canary** the operator owns, or a **hermetic target**. Live external
> callbacks to attacker infrastructure require explicit scope.

**Idea.** Whenever the server will go fetch something *the client named*, ask who constrains the
destination. The dangerous tell is not the feature; it is the absence of an allowlist + redirect
disablement around it.

## Suggested probes (benign, scope-gated)
- **Differential against a sibling** that does enforce an allowlist (your positive control that the
  constraint *can* live here) — the finding is often the route/tool differential, not the fetch alone.
- **Controlled external canary first:** point the fetch at a benign URL the operator owns and confirm
  the server actually makes the request (a hit on your canary endpoint proves the fetch is reachable)
  — no internal destinations involved.
- **Redirect-follow shape:** point the first hop at a controlled external URL that redirects to a
  hermetic or operator-owned stand-in canary. Confirmation requires the server-side fetch to reach the
  stand-in canary; merely observing the redirect response body is not enough.
- **Allowlist / redirect checks (design-level, no internal traffic):** does it follow redirects? does
  it parse the host before or after normalization? These are reasoning probes, not internal requests.
- **Internal-destination probes are operator-only:** loopback / metadata / private ranges require an
  explicit `scope.md` grant and Zone-2 confirmation. Absent that, record the shape as **held / needs
  review**, do not fire.

## Required oracle controls (adjudication is default-skeptical)
- **Negative control MUST hold:** the allowlisted-host request (or the validating sibling) must behave
  safely. Without a constrained control there is no differential to point at.
- **Reachability, not vibes:** a confirmed finding shows the server *actually fetched the
  client-named destination* (canary hit / response differential), not merely that a `url` field exists.
- **Stand-in internal canary for safe tests:** in hermetic or scoped lab runs, use a synthetic
  internal stand-in service rather than live cloud metadata. No live metadata probing.
- **Internal reach is operator-confirmed:** any claim that an internal/metadata host was reached is a
  Zone-2 artifact requiring human confirmation; never auto-confirm it.
- **Replay** in a fresh session.

## Counterexamples (look like it, aren't)
- The `url` field is validated against a strict external allowlist with redirects disabled → held; the
  feature is safe.
- The "url" is an opaque internal id the client cannot steer to a network location → not SSRF.
- The server fetches a *fixed* URL and the client only supplies a query string consumed as data → no
  client-controlled destination.
- The response echoes or stores the supplied URL but no controlled canary receives a server-side
  request → activation may remain, confirmation is refuted or `needs_review`.

## Real disclosed anchor(s) for this class (fix-diff-derived)
Priors/taxonomy from real disclosed GHSA fix commits — the vulnerable pre-patch shape and the guard
the fix added. Verbatim hunks + primary sources in `skills/oracles/references/ghsa-fix-diff-corpus.md`
(SSRF bucket). **These are all *fixed* bugs, not live-bug claims:** a target matching a removed-line
shape is a lead to run through the review-gated funnel above, never a confirmation. The class splits
by which guard the fix inserted in front of the outbound sink.

**Destination allowlist / filter (bound), `dest-allowlist`:**
- **CVE-2024-31461** (plane, GHSA-j77v-w36v-63v6, fixed 0.17-dev @ `4b0ccea`): the Jira-importer took
  an attacker-supplied `hostname` and fetched it with no destination check → `is_allowed_hostname()`
  restricting the base domain to a fixed Atlassian-host set, invoked before the request. Authenticated
  workspace-admin.
- **CVE-2025-59146** (new-api, GHSA-xxv6-m6fx-vfhh, fixed 0.9.0.5 @ `ef63416`): any authenticated user
  could hand the LLM-gateway a URL to fetch with no validation → `ValidateURLWithFetchSetting(...)`
  (private-IP + domain/IP filter) inserted immediately before `http.Get(originUrl)`. Reached cloud
  metadata (`169.254.169.254`) for credential theft.

**Input canonicalization / format-constraint, `canonicalization`:**
- **CVE-2020-13379** (grafana, GHSA-wc9w-wvq2-ffm9, fixed 6.7.4/7.0.2 @ `ba953be`): the unauthenticated
  avatar handler took the trailing path segment verbatim as the fetch hash → a 32-hex-char MD5 regex
  (`validMD5`) applied before the outbound gravatar fetch. Pre-auth.
- **CVE-2024-39338** (axios, GHSA-8hc4-vh64-cxmj, fixed 1.7.4 @ `07a661a`): `isAbsoluteURL()`'s scheme
  group was optional, so a protocol-relative `//attacker-host` was misclassified as already-absolute
  and skipped `baseURL` merging → the scheme capture made mandatory (one-token regex fix). Library-level.

**Trusted-source param-binding, `param-binding`:**
- **CVE-2024-34351** (next.js, GHSA-fr5h-rqp8-mj6g, fixed 14.1.1 @ `8f7a6ca`): a Server Action redirect
  rebuilt the internal fetch URL from the attacker-controllable `Host` header (`originalHost.value`) →
  sourced from a trusted server env var (`__NEXT_PRIVATE_HOST`) first, falling back to the header.
  Self-hosted deployments only.

**Sink removal (no promotable guard signature), illustrative:**
- **CVE-2024-36414** (SuiteCRM, GHSA-wg74-772c-8gr7, fixed 7.14.4/8.6.1 @ `504d6f0`) — **CONTESTED**
  (illustrative): the Connectors `action_CallRest` AJAX action took a raw `url` param, checked only an
  `http(s)://` prefix, then `file_get_contents()`'d and echoed it back → the entire fetch-and-echo body
  was deleted outright, no replacement guard. Authenticated fetch-and-echo proxy.
- **CVE-2025-64430** (parse-server, GHSA-x4qj-2f4q-r4rx, fixed 7.5.4/8.4.0-alpha.1 @ `8bbe3ef`) —
  **CONTESTED** (illustrative): a Parse.File `_source` of `{format:'uri', uri:<attacker-controlled>}`
  was fetched via raw `http.get(uri, ...)` with no destination check → the URI-fetch code path and its
  call site were deleted outright, disabling URI-backed file uploads.

## Do not overclaim
- "There is a url parameter" is an activation, not a finding. Name the destination class the fetch can
  be steered to, or it is only a coverage hit.
- Do not assert internal reachability you have not been scoped to test — held/needs-review is the
  correct, honest verdict when scope does not permit the probe.
- GraphQL or REST introspection alone is not SSRF. Route GraphQL global-id resolver issues separately
  and require a chained resolver canary before confirmation.
- If the class's added-guard shape is already present for the reached sink — a destination
  allowlist/filter invoked immediately before the outbound call, a mandatory-scheme (not optional)
  absolute-URL check, or a trusted-source-bound rebuild of the fetch host (see the anchors above) —
  this path is patched; do not claim strong activation without a further, specific reason (an
  unguarded sibling route/tool, a redirect-follow bypass of the same allowlist). Presence of the guard
  is a strong held signal, not a soundness proof.
