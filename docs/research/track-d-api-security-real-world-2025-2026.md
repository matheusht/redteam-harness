# Track D — API Security, OWASP API & Real-World Archetypes (2025–2026): research → harness memo

**Status:** research memo, not a build authorization. Every archetype is a **hypothesis until
harness-validated** (Decision 0004: evidence-producing experiment inside an authorization envelope).
A report becomes a persistent pattern only if it maps to OWASP/paper taxonomy, recurs across unrelated
reports, **or** reproduces hermetically.
**Date:** 2026-06-29 · **Worktree:** `research/track-d-api-security`
**Method:** automated deep-research pass (5-angle fan-out → 26 sources fetched → 123 claims → 25
adversarially verified by 3-vote; 25/25 confirmed, 0 refuted). "Verified" = fetched + claims extracted;
"3-vote" = a specific claim survived adversarial verification.
**Related:** `AGENTS.md`, `docs/decisions/0001`, `docs/decisions/0004`, `docs/ROADMAP.md`, and the
patterns `client-supplied-selector-authz`, `legacy-route-differential`, `ssrf-server-side-fetch`,
`unsafe-default-authz-helper`, `ui-only-policy-enforcement`; vulns `broken-object-level-authz`,
`injection`.

> **Reading note.** Sanitized shapes only — no reusable exploit payloads or live endpoints. CVE/report
> IDs are cited as *provenance for an attack shape*, never as instructions. Nothing here weakens
> `safe_signal`, scope gates, broker authority, oracle separation, evaluator immutability, or cleanup;
> several findings reinforce the disbelief-default oracle. API research is a **knowledge lane, not a
> tool family** — executable scanners may become tool families later under separate review.

---

## 1. Executive synthesis — durable API lessons

The 2025–2026 evidence clusters on three well-corroborated pillars, all of which land squarely on
**existing** harness patterns: (a) **authorization keyed on client-supplied identifiers/properties**
(BOLA/API1 + BOPLA/API3); (b) **server-side-fetch SSRF** (API7) via webhook/callback URLs reaching
cloud metadata; (c) **broken authentication / JWT claim-validation** (API2). The academic tooling
(BOLAZ taint mapping, GraphQLer dependency-chaining, OpenAPI-spec IDOR triage) supplies *recon /
activation-signal logic*, **not** confirmation oracles — which fits our architecture exactly: a signal
generator feeds the disbelief-default two-layer oracle, never replaces it.

### Build-now (fits existing cards; small additions)
1. **Any endpoint that receives a client-supplied object ID is a BOLA candidate** — path, query,
   header, *or* body [OWASP API1]. Already `client-supplied-selector-authz` → `broken-object-level-authz`;
   the durable add is making "ID in *any* of the four positions" an explicit recon signal.
2. **Test write/delete/trigger BOLA, not just read.** State-changing ("action-level") BOLA is at least
   as large a real-world family as read-only IDOR [BOLA-in-the-wild taxonomy]. Our BOLA card is
   read-leaning; this is a coverage gap to close with a state-change safe_signal (inert, operator-gated).
3. **Sequential-integer object IDs are a high-value recon activation signal** (most prevalent single
   exploitation mechanism in disclosures) [taxonomy]. Cheap to detect, cheap to encode.
4. **ID opacity is not a control.** UUID/encoded/GraphQL-global IDs do not remove BOLA risk once IDs
   leak cross-endpoint [taxonomy]. This is a **do-not-overclaim rule**: "the ID is a UUID" must never be
   recorded as a held defense.
5. **Webhook/callback/URL-preview/PDF-image fetchers are the canonical SSRF activation signal** [OWASP
   API7; Plunk CVE-2026-32096; Omise]. Already `ssrf-server-side-fetch`; real disclosures confirm the
   shape and the **redirect-follow bypass** sub-shape (303 See Other defeated a no-redirect guard).

### Needs a new fixture / oracle before testing
6. **JWT claim-validation archetypes (audience + algorithm confusion) have no current card.** Missing
   `aud` validation enables cross-audience token replay [Argo CD CVE-2023-22482]; RS256→HS256 confusion
   forges tokens using the public key as HMAC secret [Jitsi CVE-2021-39215]. Needs a new
   `pattern.jwt-claim-validation` + a hermetic token-confusion oracle (token minted for audience X
   accepted at Y with a distinctive groups-derived privilege canary).
7. **BOPLA (property-level authz) is distinct from object-level BOLA.** Read-overfetch (unexpected
   property echoed) and write-mass-assignment (privileged property accepted) [OWASP API3]. Needs its own
   activation signal and a property-canary oracle, distinct from the object-ID oracle.
8. **Chained ID-disclosure is a real precondition shape** (producer endpoint emits an ID a consumer
   endpoint later trusts) [BOLAZ; taxonomy cross-endpoint leakage]. Needs a two-step casebook/oracle:
   ID-source → ID-consumer, not a single-request confirm.
9. **GraphQL needs *stateful* (dependency-chained) probing**, not isolated operations: introspection →
   global-ID leakage → chained resolver authz [GraphQLer; OWASP GraphQL testing]. Needs a GraphQL
   surface fixture; isolated-operation testing under-reports.
10. **SSRF impact-proof needs a safe stand-in canary for cloud metadata.** The real impact is a fetch
    crossing into a server-internal/metadata boundary [Omise→169.254.169.254]. A hermetic fake must use
    an operator-owned internal canary host, never live metadata — and live-internal probing stays
    scope-gated (our `ssrf-server-side-fetch` already enforces this).

### Future review (separate decision / capability)
11. **API9 Improper Inventory (shadow/zombie/legacy/mobile-only APIs)** maps onto
    `legacy-route-differential`, but the *discovery* of undocumented surfaces is a recon-capability
    question (spec diffing, version enumeration) that may later want a tool-family adapter — review
    first.
12. **Static spec-driven candidate detection (OpenAPI → potential IDOR/BOLA)** [Barabanov 2022] is a
    promising recon signal generator but emits *candidates*, not findings — future adapter, kept
    strictly upstream of the oracle.

### Reject / defer (not ingestable now)
13. **Any precise quantitative ranking from a single preprint** (e.g. "41.7% is *the* largest family")
    — ingest the *methodological* lesson (cover state-changing BOLA), defer the statistic [taxonomy is a
    single non-peer-reviewed preprint, n=84, LLM-assisted classification, fragile margin].
14. **"OWASP API Top 10 2025" re-rankings** — no final/RC 2025 *API* edition was verified in this pass
    (the verified `owasp.org/Top10/2025` source is the *web* Top 10, a different project). Treat API
    Top 10 2023 as current; defer any 2025-API claims until confirmed.
15. **Request smuggling/desync, unrestricted resource consumption, gateway-vs-backend gaps, unsafe
    third-party consumption, agentic tool-calling backends** — requested but produced **no verified
    claim** this pass. Record as open coverage gaps (don't force-fit), candidate for a follow-up track.

---

## 2. Source table

Type: OWASP / paper / disclosure(CVE/H1/GHSA) / practitioner. Years/venues as reported. arXiv IDs
encode month (25xx=2025, 26xx=2026; 2201=2022).

| # | Source (short) | Year | Link | Type | Verified? | API risk | Evidence kind | Transfers | Doesn't transfer | Conf. |
|---|---|---|---|---|---|---|---|---|---|---|
| D1 | OWASP API1:2023 BOLA | 2023 | owasp.org/API-Security/.../0xa1-broken-object-level-authorization | OWASP | yes (3-vote) | API1 | authoritative spec | ID-in-any-position recon signal; per-object authz control | — | high |
| D2 | OWASP API Top 10 2023 index | 2023 | owasp.org/API-Security/.../0x11-t10 | OWASP | yes (3-vote) | API1–10 | authoritative taxonomy | full API1–10 mapping | exact 2025 re-rank | high |
| D3 | OWASP API7:2023 SSRF | 2023 | owasp.org/API-Security/.../0xa7-server-side-request-forgery | OWASP | yes (3-vote) | API7 | authoritative spec | server-side-fetch activation signal | — | high |
| D4 | OWASP API2:2023 Broken Auth | 2023 | owasp.org/API-Security/.../0xa2-broken-authentication | OWASP | yes | API2 | authoritative spec | auth/JWT archetype framing | — | high |
| D5 | BOLA in the Wild (taxonomy, 100+ disclosures) | 2026 | arxiv.org/html/2605.25865 | paper (preprint) | yes (3-vote) | API1 | empirical (n=84) | test state-change BOLA; int-enum signal; ID-leak chaining; opacity≠control | precise % (fragile margin) | medium |
| D6 | Rethinking BOLA under Zero Trust (BOLAZ) | 2025 | arxiv.org/abs/2507.02309 | paper | yes (3-vote) | API1 | method/taint | producer/consumer ID-flow as recon signal | efficacy unreplicated | high (method) |
| D7 | GraphQLer | 2025 | arxiv.org/abs/2504.13358 | paper | yes (3-vote) | API1/API5 | method/tool | dependency-chained GraphQL probing | tool efficacy unreplicated | high (method) |
| D8 | OpenAPI-spec IDOR/BOLA detection | 2022 | arxiv.org/abs/2201.10833 | paper | yes (3-vote) | API1 | static method | spec-driven candidate recon signal | candidates ≠ confirms; dated | medium |
| D9 | Omise webhook SSRF → AWS keys | — | hackerone.com/reports/508459 | disclosure (H1) | yes (3-vote) | API7 | real-world | redirect-follow bypass; metadata-boundary impact proof | live metadata dependency | high |
| D10 | Plunk SSRF (CVE-2026-32096) | 2026 | github.com/useplunk/plunk/security/advisories/GHSA-xpqg-p8mp-7g44 | disclosure (CVE/GHSA) | yes (3-vote) | API7 | real-world | unauth server-side-fetch via webhook confirm URL | vendor-specific endpoint | high |
| D11 | Argo CD JWT audience not verified (CVE-2023-22482) | 2023 | hackerone.com/reports/1889161 · GHSA-q9hr-j4rf-8fjc | disclosure | yes (3-vote) | API2 | real-world | cross-audience token-confusion oracle shape | deployment status | high |
| D12 | Jitsi JWT alg confusion (CVE-2021-39215) | 2021 | hackerone.com/reports/1210502 · GHSA-45ff-37jm-xjfx | disclosure | yes (3-vote, 2-1 on detail) | API2 | real-world | RS256→HS256 confusion shape + precondition set | deployment status | high (shape) |
| D13 | H1 #3382343 (real-world disclosure) | — | hackerone.com/reports/3382343 | disclosure | yes | API1/7 | real-world | corroborating archetype | single report | medium |
| D14 | OWASP GraphQL Testing Guide (WSTG) | — | owasp.org/www-project-web-security-testing-guide/.../Testing_GraphQL | OWASP | yes | API1/8 | authoritative method | introspection→authz probe order | — | high |
| D15 | OWASP API SSRF + GraphQL Cheat Sheet | — | cheatsheetseries.owasp.org/.../GraphQL_Cheat_Sheet | OWASP | yes | API7/8 | authoritative control | defense/positive-control framing | — | high |
| D16 | PortSwigger JWT / alg-confusion academy | — | portswigger.net/web-security/jwt(/algorithm-confusion) | practitioner | yes (secondary) | API2 | technique ref | precondition checklist for JWT oracle | lower-confidence (blog) | medium |
| D17 | PortSwigger GraphQL academy | — | portswigger.net/web-security/graphql | practitioner | yes (secondary) | API1 | technique ref | GraphQL recon order | secondary | medium |
| D18 | Cerberauth JWT cross-service relay | — | vulnapi.cerberauth.com/.../jwt-cross-service-relay-attack | practitioner | yes (secondary) | API2 | technique ref | audience-relay corroboration | secondary | medium |
| D19 | CMC survey: RESTful API vuln detection | 2025 | techscience.com/cmc/v84n3/63208/html | paper (survey) | yes (secondary) | API1–10 | survey | landscape framing | survey, not primary | medium |
| D20 | OWASP (web) Top 10 2025 A01 BAC | 2025 | owasp.org/Top10/2025/A01_2025-Broken_Access_Control | OWASP | yes | (web, not API) | authoritative | BAC framing; **not** API Top 10 | do not conflate w/ API Top 10 | high |

Secondary/blog sources fetched but demoted (Danaepp, Akamai, Wiz, ApyGuard, WorkOS) corroborate the
OWASP-2025 "upcoming changes" rumor but are **not** primary; their re-ranking claims are **deferred**
(§1.14). **Real-world disclosure coverage:** D9–D13 (Omise, Plunk, Argo CD, Jitsi, +1) are concrete
named CVEs/advisories/reports — the requested "meaningful real-world coverage." Directly-verified
primary+OWASP+disclosure set ≈ 15; with verified secondary practitioner refs ≈ 20.

---

## 3. Real-world archetype extraction (sanitized shapes)

Per archetype: asset · vuln class · recon signal · safe probe shape · negative control · positive
control · impact-proof shape · do-not-overclaim · likely card.

### A1 — Object-ID BOLA (read) [D1, D5, D6]
- **Asset:** REST per-object endpoint. **Class:** API1 BOLA (read).
- **Recon signal:** object ID in path/query/header/body; integer-shaped IDs especially.
- **Safe probe:** principal-A requests principal-B's *own planted benign canary object*.
- **Negative control:** no-selector / self-selector request must **not** return the cross-principal object.
- **Positive control:** a guarded sibling endpoint (or path-param variant) that **denies** the same cross-principal ID — proves the guard belongs there.
- **Impact proof:** B's distinctive app-owned canary appears in A's response (boundary crossed).
- **Do-not-overclaim:** 200/echo/ID-shaped public value ≠ confirm; UUID opacity ≠ held.
- **Card:** `client-supplied-selector-authz` → `broken-object-level-authz`.

### A2 — State-changing BOLA (write/delete/trigger) [D5]
- **Asset:** REST mutation endpoint. **Class:** API1 BOLA (action-level).
- **Recon signal:** mutating verb (PUT/PATCH/DELETE/POST-action) accepting an object ID.
- **Safe probe:** A triggers an **inert, reversible** state change on B's planted canary object (operator-gated; Zone-2 confirm before any non-inert mutation).
- **Negative control:** same mutation with self/no selector must not touch B's object.
- **Positive control:** guarded sibling rejects the cross-principal mutation.
- **Impact proof:** B's canary object shows the inert change attributable to A.
- **Do-not-overclaim:** a 200 on a mutation ≠ the mutation took effect on B's object; require an observed effect on the canary; never a destructive proof.
- **Card:** `client-supplied-selector-authz` → `broken-object-level-authz` (**needs state-change safe_signal**).

### A3 — Chained ID-disclosure (producer → consumer) [D6, D5]
- **Asset:** two REST/GraphQL endpoints. **Class:** API1 via ID leakage.
- **Recon signal:** endpoint P returns an ID that endpoint C later trusts for access.
- **Safe probe:** obtain a foreign ID from P (legitimately or via leakage), feed to C for B's canary.
- **Negative control:** C with a bogus/own ID must not return B's object.
- **Positive control:** C denies a fabricated cross-principal ID not sourced from P.
- **Impact proof:** canary crosses only when the *real* leaked ID is used.
- **Do-not-overclaim:** ID opacity is not a control; the finding is the *consumer's* missing authz, not the leak alone.
- **Card:** `unsafe-default-authz-helper` / `client-supplied-selector-authz`.

### A4 — BOPLA: read overfetch [D2 (API3)]
- **Asset:** REST resource serializer. **Class:** API3 (excessive data exposure).
- **Recon signal:** response includes properties the UI never shows.
- **Safe probe:** request the object; inspect for a privileged/foreign **property canary**.
- **Negative control:** a properly-scoped sibling returns only authorized properties.
- **Positive control:** an admin-only view that *correctly* gates the property.
- **Impact proof:** a distinctive sensitive-property canary appears for an unentitled principal.
- **Do-not-overclaim:** presence of a field ≠ sensitive; require an app-owned property canary that should be gated.
- **Card:** **new** `pattern.bopla-property-authz` (gap) → BOLA/BFLA family.

### A5 — BOPLA: write mass-assignment [D2 (API3)]
- **Asset:** REST create/update accepting an object body. **Class:** API3 (mass assignment).
- **Recon signal:** write endpoint binds whole objects; privileged property names guessable.
- **Safe probe:** include an inert privileged property (e.g. a benign role/flag canary) in the body.
- **Negative control:** omit the property → baseline; a guarded sibling rejects/strips it.
- **Positive control:** the server **coerces/strips** the property on a sibling (defense holding).
- **Impact proof:** the privileged property is **accepted and reflected as effective** (not just echoed).
- **Do-not-overclaim:** echo of the submitted property ≠ it took effect; require effective-state evidence.
- **Card:** **new** `pattern.bopla-property-authz`.

### A6 — Webhook/callback SSRF → internal boundary [D3, D9, D10]
- **Asset:** webhook/callback/URL-preview/import fetcher. **Class:** API7 SSRF.
- **Recon signal:** server fetches a **client-supplied URL**; confirm/subscribe flows (e.g. SNS) that fetch a `SubscribeURL`.
- **Safe probe:** point the fetch at an **operator-owned external canary** first (prove reachability).
- **Negative control:** allowlisted/own-host destination; a sibling that constrains destinations.
- **Positive control:** a destination-allowlist sibling that denies the off-list host.
- **Impact proof:** fetch crosses into a **server-internal/metadata canary** the client could not otherwise reach (loopback/metadata only under explicit scope; hermetic uses a stand-in internal host, never live 169.254.169.254).
- **Do-not-overclaim:** an outbound 200 to *your* canary proves reachability, not internal impact; internal-boundary crossing requires the internal canary + scope.
- **Card:** `ssrf-server-side-fetch` (+ **redirect-follow bypass** sub-shape: 303/See-Other defeating a no-redirect guard, per D9).

### A7 — JWT audience-not-verified (cross-audience confusion) [D11]
- **Asset:** OIDC/JWT-protected API. **Class:** API2 broken auth.
- **Recon signal:** service validates signature but multiple audiences share an IdP; no `aud` allowlist.
- **Safe probe:** present a token minted for audience **X** to service **Y** (both operator-controlled in a hermetic fixture).
- **Negative control:** a token with the correct `aud` for Y (baseline accept); a service that enforces `allowedAudiences` rejects X.
- **Positive control:** the same service with audience-checking enabled denies the X-token.
- **Impact proof:** Y accepts the X-token and grants a distinctive **groups-derived privilege canary**.
- **Do-not-overclaim:** signature-valid ≠ intended-for-this-service; the finding is the missing `aud` check.
- **Card:** **new** `pattern.jwt-claim-validation`.

### A8 — JWT algorithm confusion (RS256→HS256) [D12, D16]
- **Asset:** JWT verifier configured for asymmetric keys. **Class:** API2 broken auth.
- **Recon signal:** verifier accepts attacker-chosen `alg`; public key obtainable; same key reused across alg families.
- **Safe probe:** forge a token in a hermetic fixture by signing with the public key as HMAC secret under a symmetric `alg`.
- **Negative control:** a verifier that rejects any non-`RS*` alg before key fetch (defense holds).
- **Positive control:** the patched verifier (rejects symmetric alg) denies the forged token.
- **Impact proof:** forged token accepted with a distinctive privilege canary.
- **Do-not-overclaim:** full precondition set required (server honors attacker alg **+** key reused across families **+** public key in exact format); absent any, record **held**.
- **Card:** `pattern.jwt-claim-validation`.

### A9 — GraphQL chained authz / global-ID IDOR [D7, D14, D17]
- **Asset:** GraphQL endpoint. **Class:** API1 via resolver authz.
- **Recon signal:** introspection enabled; opaque global IDs (decode/increment/re-encode); related mutation+query chains.
- **Safe probe:** introspect → obtain a foreign global ID → chain a resolver to fetch B's canary.
- **Negative control:** the chain with a bogus/own global ID returns nothing cross-principal.
- **Positive control:** a resolver that *does* enforce per-node authz denies the foreign ID.
- **Impact proof:** B's canary node returned to A through the chain.
- **Do-not-overclaim:** introspection availability ≠ vuln; global-ID decodability ≠ confirm.
- **Card:** `client-supplied-selector-authz` (**needs GraphQL surface fixture**).

### A10 — Shadow/zombie/legacy API differential [D2 (API9), D5]
- **Asset:** versioned/legacy/mobile-only route. **Class:** API9 inventory / API1.
- **Recon signal:** `/v1` vs `/v2`, deprecated-but-mounted routes; guard present on canonical, absent on sibling.
- **Safe probe:** identical request to both; compare authz decision for B's canary.
- **Negative control:** canonical sibling denies the cross-principal request (positive control too).
- **Impact proof:** legacy route honors a client-supplied selector the canonical denies.
- **Do-not-overclaim:** different format ≠ different authz; a 404 legacy route is gone, not bypassed.
- **Card:** `legacy-route-differential` (+ co-activate `client-supplied-selector-authz`).

---

## 4. OWASP API1–API10 mapping (+ non-OWASP recurring)

| OWASP API risk | Coverage | Harness card | Status |
|---|---|---|---|
| **API1 BOLA** | strong | `client-supplied-selector-authz` → `broken-object-level-authz` | covered; add state-change + GraphQL |
| **API2 Broken Authentication** | new | — | **gap** → `pattern.jwt-claim-validation` (aud + alg) |
| **API3 BOPLA** | new | — | **gap** → `pattern.bopla-property-authz` (overfetch + mass-assign) |
| **API4 Unrestricted Resource Consumption** | none | — | open gap (no verified claim) |
| **API5 BFLA** | partial | `unsafe-default-authz-helper` (role-vs-resource) | partial; function-level needs explicit signal |
| **API6 Unrestricted Sensitive Business Flows** | none | — | open gap |
| **API7 SSRF** | strong | `ssrf-server-side-fetch` | covered; add redirect-follow sub-shape |
| **API8 Security Misconfiguration** | partial | (introspection via GraphQL) | partial |
| **API9 Improper Inventory (shadow/zombie)** | partial | `legacy-route-differential` | covered for differential; *discovery* is future recon-capability |
| **API10 Unsafe Consumption of APIs** | none | — | open gap |

**Non-OWASP recurring patterns (call out separately):**
- **Chained ID-disclosure** (producer→consumer ID trust) — orthogonal to single-endpoint BOLA [D5, D6].
- **ID-opacity-as-non-control** — a *do-not-overclaim rule*, not a vuln class [D5].
- **Cross-audience token confusion** — a JWT-specific multi-tenant shape under API2 [D11].
- **Redirect-follow SSRF bypass** (303/See-Other) — a sub-shape under API7 [D9].
- **Spec-driven candidate triage** (OpenAPI → potential IDOR) — a recon-signal generator, not a finding [D8].

---

## 5. Casebook / eval ideas (≥15 sanitized rows)

Format: surface · activation signal · expected shape · oracle · hermetic feasibility · support.

1. **`bola-int-enum-read`** — REST per-object; integer ID; **confirmed** if B-canary crosses, **held** if guarded sibling denies; object-ID canary oracle; hermetic easy. [D1,D5]
2. **`bola-uuid-not-immune`** — REST; UUID ID leaked via second endpoint; **confirmed** only via chain, **refuted** if "UUID = safe" assumed; chained two-step oracle; hermetic easy. [D5,D6]
3. **`bola-state-change-trigger`** — REST mutation; **confirmed** on inert effect to B-canary, **needs_review** on bare 200; effect-on-canary oracle; hermetic medium (state model). [D5]
4. **`bola-producer-consumer-chain`** — two endpoints; producer leaks ID; **confirmed** at consumer; ID-flow oracle; hermetic medium. [D6]
5. **`bopla-overfetch-property`** — REST serializer; **confirmed** if gated property-canary returned to unentitled user, **refuted** if field is public; property-canary oracle; hermetic easy. [D2]
6. **`bopla-mass-assign-write`** — REST write; **confirmed** if privileged property effective, **held** if coerced/stripped, **needs_review** if only echoed; effective-state oracle; hermetic medium. [D2]
7. **`ssrf-webhook-external-canary`** — webhook fetch; **confirmed** reachability to operator canary, **needs_review** for internal (scope); egress-canary oracle; hermetic easy. [D3,D10]
8. **`ssrf-redirect-303-bypass`** — fetcher with no-redirect guard; **confirmed** if 303 reaches stand-in internal host, **held** if redirect dropped; redirect-follow oracle; hermetic easy (stand-in host). [D9]
9. **`ssrf-metadata-boundary`** — fetcher; **confirmed** only if internal/metadata **stand-in** canary crossed (never live metadata); boundary-canary oracle; hermetic medium. [D9]
10. **`jwt-audience-confusion`** — OIDC API; token aud=X at service Y; **confirmed** if accepted with privilege canary, **held** if `allowedAudiences` enforced; token-confusion oracle; hermetic easy. [D11]
11. **`jwt-alg-confusion-rs-hs`** — JWT verifier; **confirmed** if forged HS-token accepted, **held** if non-`RS*` rejected; alg-confusion oracle; hermetic easy. [D12]
12. **`graphql-global-id-idor`** — GraphQL; introspection + global-ID; **confirmed** via chained resolver to B-canary; chained-authz oracle; hermetic medium. [D7,D14]
13. **`graphql-introspection-only`** — GraphQL; **refuted/held** — introspection enabled is *not* a finding alone; coverage/FP-discipline oracle; hermetic easy (FDR trap). [D14]
14. **`shadow-legacy-route-differential`** — `/v1` vs `/v2`; **confirmed** if legacy honors selector canonical denies; differential oracle; hermetic easy. [D2,D5]
15. **`bfla-role-not-resource`** — role-gated route accepting cross-principal selector; **confirmed** if role-only guard misses resource binding, **held** if binding mandatory; helper-binding oracle; hermetic easy. [D6]
16. **(FDR trap) `idor-public-value-not-cross`** — endpoint returns an ID-shaped value that is actually public; **refuted** (must not confirm); FP-discipline oracle; hermetic easy. [D5]
17. **(FDR trap) `ssrf-echo-not-fetch`** — server reflects the URL but never fetches; **refuted**; FP-discipline oracle; hermetic easy. [D3]

---

## 6. Reviewer pass (5.5 subagent as **critic / triage only — not authority**)

> Per the brief and `AGENTS.md`: an LLM reviewer may triage and grade clarity/risk; it **cannot**
> approve persistence. Persistence requires a fixture, a hermetic target, or human review. Recorded
> separately from the findings, as required.

Grades: clarity / generality / oracle-completeness / FP-risk / safety-fit (1–5, 5 best).

| Candidate | Clar | Gen | Oracle | FP-risk(↓good) | Safety | Critic note |
|---|---|---|---|---|---|---|
| state-change BOLA (A2) | 5 | 5 | 4 | low | needs Zone-2 confirm for non-inert | **strongest add**; oracle needs a crisp inert-effect definition before build |
| JWT aud confusion (A7) | 5 | 4 | 5 | low | hermetic-only | clean, fully hermetic; generality limited to OIDC-multi-audience deployments |
| JWT alg confusion (A8) | 4 | 4 | 5 | low | hermetic-only | tight precondition set is its own FP guard; document all three preconditions or it over-claims |
| BOPLA mass-assign (A5) | 4 | 5 | 3 | **medium** | inert | "effective vs echoed" is the whole game; oracle must prove *effective* state or it false-positives |
| chained ID-disclosure (A3) | 4 | 5 | 4 | low | inert | high generality; two-step oracle adds complexity — justify against complexity budget |
| GraphQL global-ID IDOR (A9) | 4 | 4 | 4 | medium | inert | needs a GraphQL surface fixture first; introspection-only must be a held control |
| redirect-follow SSRF (A6 sub) | 5 | 4 | 4 | low | scope-gated | concrete, well-evidenced; reuses `ssrf-server-side-fetch` |
| int-enum recon signal | 5 | 5 | n/a | low | safe | trivially ingestable as an activation signal |
| ID-opacity≠control rule | 5 | 5 | n/a | low | safe | a do-not-overclaim rule, not a card — cheapest, safest ingestion |

**Critic's overall:** the three JWT/BOPLA *cards* are net-new capability and each needs a hermetic
fixture before persistence; the two *rules* (int-enum signal, ID-opacity≠control) and the state-change
BOLA extension are the lowest-risk, highest-leverage. The critic **does not approve** any of these —
they enter the normal gate (fixture/hermetic target → conformance → human PR).

---

## 7. Top next builds (ranked, with validation + stop condition)

| # | Build | Type | Validation | Stop condition |
|---|---|---|---|---|
| 1 | `int-enum` + `id-in-any-position` recon **activation signals** on `client-supplied-selector-authz` | signal | routing gold lights the right card on an int-ID fixture | signal added, gold passes, no over-activation |
| 2 | **`id-opacity-is-not-a-control`** do-not-overclaim rule + FDR trap `idor-public-value-not-cross` | oracle rule + FDR trap | `score-false-discovery` keeps invalid-accept 0 | trap encoded, correct verdict = refuted |
| 3 | State-change BOLA **safe_signal** on `broken-object-level-authz` (inert effect, Zone-2 for non-inert) | vuln-card extension | one hermetic mutation fixture: confirmed on inert effect, needs_review on bare 200 | safe_signal defined; conformance green |
| 4 | FDR trap **`ssrf-echo-not-fetch`** (reflection ≠ fetch) | FDR trap | invalid-accept stays 0 | trap encoded |
| 5 | **`pattern.jwt-claim-validation`** (aud + alg confusion) | new pattern card | hermetic JWT fixture: confirmed vs held on both sub-shapes | card + fixture; routes resolve; no payloads |
| 6 | Hermetic **JWT token-confusion target** (`evals/hermetic/targets/jwt-*`) | hermetic target | deterministic accept/deny ledger; positive control (patched verifier denies) | target deterministic, budget ledger present |
| 7 | **`pattern.bopla-property-authz`** (overfetch + mass-assign) | new pattern card | property-canary oracle distinguishes effective vs echoed | card + fixture; effective-state proven |
| 8 | SSRF **redirect-follow (303) sub-shape** + stand-in internal canary host | card extension + fixture | hermetic: 303 reaches stand-in, no-redirect drops it | sub-shape encoded; never live metadata |
| 9 | **GraphQL surface fixture** + global-ID chained-authz oracle; introspection-only as held control | fixture + oracle | confirmed on chained foreign-ID; introspection-only = held | fixture deterministic; held control bites |
| 10 | Record open coverage gaps (API4/API6/API10, request-smuggling, gateway-vs-backend) via `coverage_honesty` | coverage honesty | scorer flags gap, no force-fit | gaps recorded; candidate follow-up track noted |

---

## Top 3 harness-ingestable API hypotheses (value × testability)

1. **ID opacity is not a control + the int-enum/any-position recon signal.** *(highest — pure rule +
   signal, fully hermetic, reinforces disbelief-default.)* Validate with builds #1–#2; stop when the
   FDR trap holds invalid-accept at 0 and routing gold lights the right card. [D1, D5]
2. **Test state-changing BOLA, not just read.** *(high value, medium cost — closes a real-world
   coverage gap; needs an inert-effect safe_signal + Zone-2 gate for non-inert.)* Validate with build
   #3; stop when a hermetic mutation fixture confirms on an inert effect and `needs_review`s a bare 200.
   [D5]
3. **JWT claim-validation (audience + algorithm confusion) as a hermetic-only new card.** *(high value,
   cleanly hermetic; generality bounded to OIDC/JWT deployments.)* Validate with builds #5–#6; stop when
   the hermetic fixture confirms both sub-shapes and a patched-verifier positive control denies them.
   [D11, D12]

All three either *strengthen disbelief-default rules* or are *fully hermetic new cards* — the lowest-risk
first ingestions, each one small, reversible, and testable.

---

### Verification ledger
26 sources fetched; 25/25 verified claims confirmed (0 refuted); ~15 directly-verified primary/OWASP/
disclosure sources with concrete real-world coverage (Omise H1 #508459, Plunk CVE-2026-32096, Argo CD
CVE-2023-22482, Jitsi CVE-2021-39215, +H1 #3382343). Soft spots stated openly: single-preprint
quantitative figures (D5) ingested as methodology not statistics; two H1 pages JS-gated, confirmed via
advisories/CVEs; academic tools (D6–D8) are recon-signal generators, not oracles. No 2025 *API* Top 10
edition verified (deferred). No reusable payloads; every recommendation cites ≥1 verified source;
nothing weakens `safe_signal`, scope gates, broker authority, oracle separation, evaluator immutability,
or cleanup. API research kept as a knowledge lane, not a tool family.
