---
id: pattern.legacy-route-differential
name: Legacy / Sibling Route Enforces Differently
description: >
  Two versions or variants of the same logical endpoint enforce DIFFERENT authorization or policy.
  A guard added to the canonical route was never back-ported to the older/alternate one, which stays
  mounted and reachable.
type: pattern
owasp: "A01 Broken Access Control / API1:2023"
also: "the delivery mechanism for many client-supplied-selector and ui-only-policy bypasses"
atlas: "—"
routes_to: [pattern.client-supplied-selector-authz, pattern.ui-only-policy-enforcement]

activation:
  strong:
    - "versioned route pairs for the same resource (/v1 vs /v2, /api vs /internal, legacy vs new)"
    - "a guard / validation call present in one handler and absent in its sibling for the same action"
    - "the frontend calls the new route, but the old one is still mounted and responds"
    - "a legacy/older endpoint honors a client-supplied owner/tenant selector while the canonical sibling DENIES the same actor for the same object (the guard was added to the canonical version and never back-ported) — CO-ACTIVATE pattern.client-supplied-selector-authz"
    - "a security-policy / middleware path matcher normalizes or decodes the request path differently than the router/handler that ultimately serves it, so an encoded, duplicate-slash, or matrix-param variant of a guarded path slips past the policy on one route while its sibling stays covered (diff-derived: the `%3B`-encoded matrix-param bypass of the path policy in CVE-2026-50559 (Quarkus), the duplicate-slash/semicolon Fastify-vs-Express canonicalization mismatch in CVE-2026-33808 (fastify-express) — see the anchors section)"
    - "an internal-only marker (header, path segment) meant to route around the guarded handler is trusted with no secret/identity binding, so a forged marker reaches the same unguarded path a legacy back-channel would (diff-derived: the unbound `x-middleware-subrequest` header skipping `middleware.ts` entirely in CVE-2025-29927 (Next.js))"
  weak:
    - "method variants on the same path that branch into different handlers (GET vs POST, query vs body)"
    - "a route named with a deprecation hint (legacy, old, compat, v0) that still answers"
  negative:
    - "all variants funnel through the SAME authorization layer → no differential, record as held"
    - "the legacy route is actually removed / 410s / 404s for everyone"
    - "the path is canonicalized (percent-decode loop, matrix-param strip, duplicate-slash collapse, dot-removal) BEFORE it reaches the authorization/security-policy matcher, and every consumer (proxy, static-resource handler, CSRF filter) calls the SAME canonicalization function → likely held (diff-derived: the shared `normalizePath()` call inserted ahead of `pathMatcher.match()` in CVE-2026-50559 (Quarkus); the `normalizeUrl()`/`removeDuplicateSlashes()` fix applied to `req.raw.url` before dispatch in CVE-2026-33808 (fastify-express))"
---

# Legacy / sibling route enforces differently

> **Co-activation rule.** When the differential is *driven by* a client-controlled owner / tenant /
> resource selector (the legacy route trusts the selector, the canonical one re-resolves it), this card
> and `pattern.client-supplied-selector-authz` fire **together** — co-activate both, don't pick one.
> The route is the delivery mechanism; the selector is the trust bug.

**Idea.** Authorization that lives at the *route perimeter* gets duplicated per version, and one copy
drifts. The new route gets the guard; the old route keeps serving the unguarded path the team thinks
is dead. The bug is the *delta between siblings*, demonstrated with one fixed actor.

## Suggested probes
- **Enumerate the variants**: version suffixes, method pairs, internal/admin twins of a public route.
- **Run one fixed, authorized-looking request against every variant** and diff the authorization
  *outcome* (not the response shape).
- **Carry a selector or policy value across siblings** (compose with `pattern.client-supplied-selector-authz`
  / `pattern.ui-only-policy-enforcement`): the value the secure sibling rejects, try on the legacy one.

## Required oracle controls
- **The canonical sibling is your positive control**: it must DENY the same action — that proves the
  guard exists and the legacy route is the one missing it.
- **A different resource that enforces the same selector class corroborates** (e.g. a path-param
  endpoint that 403s a cross-tenant id, or a list endpoint that ignores the owner override): it shows
  the platform CAN enforce, so the gap is route-specific drift, not a systemic absence. This also kills
  the public-share / "anyone-can-read" false positive — if the object were legitimately readable, the
  guarded sibling would return it too.
- **Same actor, same intent**: the only variable is the route. If you changed the account or the
  payload too, you haven't isolated the differential.
- **Canary + replay** as for the underlying pattern (selector / policy). Cross-tenant → operator-confirm.

## Counterexamples
- Both routes deny → no differential.
- The legacy route returns a *different format* but the *same authorization decision* → not a finding.
- A 404 on the legacy route is the route being gone, not a bypass.

## Real disclosed anchor(s) for this class (fix-diff-derived)
Priors/taxonomy from real disclosed GHSA fix commits — the vulnerable pre-patch shape and the guard
the fix added. Verbatim hunks + primary sources in `skills/oracles/references/ghsa-fix-diff-corpus.md`
(Auth bypass / generic mechanism bucket). **These are all *fixed* bugs, not live-bug claims:** a target
matching a removed-line shape is a lead to run through the funnel above, never a confirmation. The
bucket splits by which layer the guard closes.

**Path-matcher / sink canonicalization mismatch (the classic sibling-differential shape), `canonicalization`:**
- **CVE-2026-50559** (Quarkus, GHSA-qcxp-gm7m-4j5v, fixed 3.37.0 + back-ports @ `fc5c83a`): an encoded
  matrix param (`%3B`) was never stripped by the security-policy's path normalizer, so an encoded path
  like `/api/admin%3Bbypass=true/data` failed to match the `/api/admin/*` policy while the static-resource
  handler decoded further downstream → a shared `normalizePath()` (decode-loop + matrix-param strip +
  dot-removal) is now called before every consumer's match, so policy and sink can no longer diverge.
  Path-policy-protected endpoints and protected static resources.
- **CVE-2026-33808** (fastify-express, GHSA-6hw5-45gm-fj88, fixed 4.0.5 @ `674020f`) — **CONTESTED**
  (illustrative; primary CWE is off-bucket CWE-436, kept for mechanism fit): Fastify's router normalized
  duplicate slashes/semicolons for its own route match, but forwarded the raw, only-`decodeURI`'d path to
  Express, so `//admin` or `/admin;x` reached the route while skipping the path-scoped Express auth
  middleware registered at `/admin` → `normalizeUrl()` applied to `req.raw.url` before Express dispatch.
  This is the textbook "canonical route enforces, legacy-parsed sibling path doesn't" shape.

**Trusted internal-marker bypass (the "legacy back-channel" variant), `param-binding`:**
- **CVE-2025-29927** (Next.js, GHSA-f82v-jwr5-mffw, fixed 12.3.5 / 13.5.9 / 14.2.25 / 15.2.3 @ `52a078d`):
  a client-forged `x-middleware-subrequest` header — meant only for the internal recursion guard — was
  trusted with no secret binding, letting any request skip `middleware.ts` (where auth/authz live)
  entirely → a per-process random secret is now stamped onto genuine internal subrequests and checked
  before the header is honored. Pre-auth, full middleware/auth skip on any route.

(CVE-2026-34040 (Moby, AuthZ-plugin body truncation) and CVE-2026-28474 (openclaw, display-name-vs-id
allowlist) sit in the same corpus bucket but fit `transitive-sanitizer-reliance` / identity-binding
mechanisms better and are not repeated here.)

## Do not overclaim
- A version difference is not a vulnerability; an **authorization-outcome** difference for the same
  actor is. State the delta in one sentence: "route X allows action A for actor P; sibling Y denies it."
- If the canonical route's path-matching layer already canonicalizes (decodes, strips matrix params,
  collapses duplicate slashes) BEFORE authorization, using the SAME normalization the sink/handler uses —
  i.e. the added-guard shape from the anchors above is already present for the "legacy" route too — this
  differential is closed; do not claim strong activation without a further, specific reason (a
  still-divergent internal-only path, a header-trust bypass at a different layer). Presence of the guard
  is a strong held signal, not a soundness proof.
