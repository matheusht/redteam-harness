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
  weak:
    - "the fetch destination is client-influenced but partly templated (a path or id appended to a fixed host) — reachability depends on how much of the host the client controls"
    - "a redirect is followed server-side, so an allowlisted host can bounce to an arbitrary one"
  negative:
    - "the destination is validated against a strict allowlist of external hosts before the fetch, with redirects disabled and internal/loopback/link-local ranges denied → defense holds, record as held"
    - "the 'url' is actually an opaque server-side id the client cannot steer to a network destination"
    - "the supplied URL is only reflected, stored, or queued, and no server-side fetch reaches a controlled canary endpoint"
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

## Do not overclaim
- "There is a url parameter" is an activation, not a finding. Name the destination class the fetch can
  be steered to, or it is only a coverage hit.
- Do not assert internal reachability you have not been scoped to test — held/needs-review is the
  correct, honest verdict when scope does not permit the probe.
- GraphQL or REST introspection alone is not SSRF. Route GraphQL global-id resolver issues separately
  and require a chained resolver canary before confirmation.
