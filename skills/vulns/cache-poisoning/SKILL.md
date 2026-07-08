---
id: cachep.cache-poisoning
name: Cache Poisoning / Cache-Key Confusion
description: >
  Prove a shared cache (CDN, ISR/full-route cache, fetch cache, edge cache) stores a response keyed
  on less than what actually shaped that response — an "unkeyed input" (a header, query param, or
  request property the origin reads but the cache key ignores) let the caller steer the cached
  ORIGIN OUTPUT while the cache still serves it to unrelated later requests under the canonical key.
  Confirmed only when a second, distinct probe (same cache key, none of the candidate unkeyed input)
  receives the first probe's altered response — proving the poison outlived the request that caused
  it, not just per-request behavior.
type: vuln
owasp: "A04:2021 Insecure Design (Cache Poisoning) / API8-style"
atlas: "—"
patterns: []

activation:
  strong:
    - "responses carry cache-control: s-maxage / stale-while-revalidate, an x-vercel-cache or CDN cache-status header, or an ISR/ SSG page is served behind any shared/CDN cache"
    - "the same URL can return materially different content-types or payload shapes (JSON vs HTML, RSC payload vs rendered page) depending on a request header"
    - "a Vary header is present but narrow (e.g. only framework-internal headers) while other request properties still visibly change the response"
    - "an 'internal' control-flow header (middleware-subrequest markers, route-match markers, invoke-status markers) is trusted from the request without verifying it originated server-side"
  weak:
    - "app uses ISR/SSG/ any ‘revalidate’ caching strategy at all — worth a cheap unkeyed-input sweep even with no other signal yet"
  negative:
    - "Vary broadly covers Cookie/Accept-Language/Authorization/RSC-plumbing headers AND the CDN is confirmed to actually honor Vary (not all CDNs do — check separately) → likely held"
    - "cache key is derived from a full hash of the request (headers included) rather than a narrow allowlist → overkeyed, not unkeyed; different bug class (possible key-collision via weak hash, not confusion)"

safe_signal:
  proxy: >
    attach a unique, attacker-owned cache-buster to EVERY probe (e.g. a random query param) so only
    your own, freshly-created cache entries are ever touched — never a real user's cached response.
    Probe 1: cache-buster + candidate unkeyed input set to a harmless, distinctive marker value.
    Probe 2 (the actual signal): SAME cache-buster, candidate input REMOVED entirely (plain
    request). If probe 2 still returns probe 1's altered output, the entry was poisoned by your own
    probe alone.
  never: >
    never poison a URL a real user could hit (no cache-buster == out of bounds); never chain into
    stored XSS, credential/cookie leakage via a poisoned SSR payload, or DoS beyond your own
    cache-buster-scoped entries without scope.md authorization AND an operator confirm.

impact_escalation:
  enabled_by: scope.md#impact_demo_authorized
  requires: human_confirm
  containment: >
    all probes scoped to a unique, attacker-owned cache-buster; no shared/production cache entry
    touched; logged in engagement cleanup.md with the exact buster value for cleanup/expiry tracking.

oracle: [signal-oracle, adjudication-oracle]
severity_rubric:
  { cross_user_stored_xss_or_credential_leak_via_poison: critical, response_body_or_status_poisoned_for_unrelated_requests: high, format_confusion_no_sensitive_data: medium, refused_or_correctly_varied: info }

procedure:
  - "MAP THE CACHE: identify every cached surface (ISR/SSG pages, `use cache` functions, fetch-cache calls, CDN edge cache) and read what its Vary/cache-key logic actually includes — this is a cheap, read-only source/response-header pass before any live probing."
  - "ENUMERATE CANDIDATE UNKEYED INPUTS: headers/params the origin visibly reads (via response diffing) that are NOT in the observed Vary set — start from known classes (RSC/router-prefetch headers, X-Forwarded-Host/Proto, Accept-Language, internal-looking `x-*` control headers, `_rsc`/similar cache-busting query params, fat-GET bodies)."
  - "BASELINE: request the target URL with a fresh, unique cache-buster and NO candidate input. Record the clean response (status, content-type, body hash) as the control."
  - "PROBE 1 (poison attempt): same cache-buster, add the candidate unkeyed input with a distinctive, harmless marker. Confirm the response visibly changes vs. baseline — this proves the input reaches the origin and shapes output, nothing about caching yet."
  - "PROBE 2 (the actual confirmation): SAME cache-buster as probe 1, but drop the candidate input entirely — a plain request. If this returns PROBE 1's altered output (not the clean baseline), the entry was cached under the canonical key while shaped by the unkeyed input: CONFIRMED cache-key confusion, self-contained to your own cache-buster."
  - "NEGATIVE CONTROL: repeat the baseline with a THIRD fresh cache-buster and no candidate input, confirm it reproduces the clean baseline — rules out flakiness/generic instability being mistaken for poisoning."
  - "RULE OUT contamination: confirm the poisoned response wasn't just a coincidental match, and that the two cache-buster values are independent entries (different cache keys), not the same request re-hitting your own connection/session."
  - "STOP at the scope.md ceiling — do not extend a confirmed cache-key-confusion primitive into an actual cross-user chain (real stored XSS delivery, real credential exposure) without explicit scope and a fresh operator confirm; note the chain as a routed escalation, not an assumed finding."

emits: [attempt, finding]
---

## What "confirmed" looks like here
Two requests share the same cache key (proven by a shared, unique cache-buster) — the first carries
a candidate unkeyed input and gets an altered response; the second carries NO candidate input and
still gets that altered response. That is the whole signature: poisoning is proven by the SECOND,
clean-looking request receiving the first request's effect, never by the first request's response
alone (a header changing the response on its own request proves reflection, not caching).

## Not this card
- An unkeyed input that changes the response but the cache correctly excludes that route from
  caching entirely (e.g. `Cache-Control: private, no-store`) → no poisoning surface, held.
- A response that differs per-request but is demonstrably never cached (verified via a cache-status
  header showing MISS on every repeated identical request) → not this bug class.
- Overkeyed / weak-hash cache-key collisions (two DIFFERENT legitimate requests colliding onto the
  same stored entry due to a weak hash, rather than an input being ignored) — same family, different
  mechanism; still valid to report but land the mechanism honestly (`hash-collision`, not
  `unkeyed-input`) since the fix and severity framing differ.
- A URL-shaped field the server fetches server-side → that's `pattern.ssrf-server-side-fetch`, not this.

## Do not overclaim
- Probe 1 alone (the response changed when you sent the candidate input) is reflection, not cache
  poisoning — it proves nothing about what gets served to a DIFFERENT, unrelated request. Confirmation
  requires probe 2.
- "Vary is missing" is a `weak` signal, not a finding — many CDNs additionally normalize or drop
  headers before the origin ever sees them, and some correctly bypass caching entirely for dynamic
  routes regardless of Vary. Verify with the actual probe/counter-probe pair, don't infer from headers
  alone.
- Name the exact unkeyed input and the exact cached artifact (status/content-type/body) in one
  sentence, or it isn't confirmed.

## References (from 2026-07-06 deep-research pass, `engagements/vercel-open-source-2026-07/`)
- GHSA-gp8f-8m3g-qvj9 / CVE-2024-46982, GHSA-67rr-84xm-4c7r / CVE-2025-49826,
  GHSA-r2fc-ccr8-96c4 / CVE-2025-49005, GHSA-wfc6-r584-vfw7 / CVE-2026-44576,
  GHSA-vfv6-92ff-j949 / CVE-2026-44582, GHSA-3g8h-86w9-wvmq / CVE-2026-44572 (all `vercel/next.js`),
  and the sibling-pattern GHSA-f82v-jwr5-mffw / CVE-2025-29927 (trusted internal header, not cache
  poisoning itself, but the same "internal control header trusted from the client" root cause).
- Cross-framework confirmation of the same pattern: Nuxt GHSA-jvhm-gjrh-3h93/CVE-2025-27415, SvelteKit
  GHSA-j62c-4x62-9r35, React Router/Remix GHSA-f46r-rw29-r322.
- Researcher write-ups: Allam Rachid ("zhero"), *"Next.js and cache poisoning: a quest for the black
  hole"* and *"Next.js, cache, and chains: the stale elixir"* (zhero-web-sec.github.io) — concrete
  unkeyed-input vectors: `x-middleware-prefetch`, `Rsc`/`_rsc`, `x-invoke-status`, `__nextDataReq`,
  `x-now-route-matches`.
- General pattern: PortSwigger "Practical Web Cache Poisoning," "Web Cache Entanglement," and Web
  Security Academy's cache-poisoning/cache-deception material.
- Next.js source-level notes (unverified against a live exploit, useful as a starting map):
  `packages/next/src/server/base-server.ts` (ISR/full-route cache key + `setVaryHeader`),
  `packages/next/src/server/lib/incremental-cache/index.ts` (`generateCacheKey` for the fetch cache).
