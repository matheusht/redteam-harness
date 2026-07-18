---
id: oracles.ghsa-fix-diff
name: GHSA fix-diff oracle
description: Priors/taxonomy pass — for a bug class, what does the real disclosed fix commit look like? The vulnerable pre-patch shape (removed lines) vs the guard the fix adds (added lines), mined from re-fetchable GHSA/OSV fix commits.
type: oracle
---

# GHSA fix-diff oracle — "what does the real fix for this class look like?"

The code-delta sibling of `severity-precedent-oracle.md`. That card mines the CVSS *vector* a bug
class earned; this one mines the *code delta* that fixed it — the vulnerable pre-patch shape (the
lines a fix removed, or the check it lacked) and the guard the fix adds (the lines it added: a bound,
a canonicalization, a per-object/per-function authz check, a deserialization type-filter, a
prototype-key block, an entity-expansion-off feature swap). The fix diff is a built-in,
mechanically-diffable ground truth: does the target's code carry the pre-patch shape
(candidate-vulnerable) or the post-patch guard (candidate-patched)? This card is the terse,
invocable-by-id index; the verbatim hunks, sources, and per-anchor verdicts live in
`skills/oracles/references/ghsa-fix-diff-corpus.md`.

## What this is / is NOT

- **IS:** a priors-and-taxonomy tool. For a class, it names the dominant guard shape and points at
  real re-fetchable fix commits whose removed/added hunks are the strong (vulnerable) and negative
  (patched) ground-truth patterns.
- **IS NOT a live-bug claim.** Every anchor is a *fixed* bug. A target matching a removed-line shape
  is a lead to run through the normal funnel, **never** a confirmation; a target matching an
  added-guard shape is a strong (not absolute — see incomplete fixes) held signal.
- **IS NOT a severity pass.** It scores nothing — that is `oracles.severity-precedent`. The two join
  by shared CVE/GHSA id (a GHSA carries both the fix commit and the CVSS vector).
- **IS NOT a PoC.** The mined artifact is the maintainers' own patch (defensive), never an exploit
  payload.

## How to use it

1. Take the finding/candidate's **CWE + mechanism** and find its bucket below.
2. Read the **dominant guard shape** and open the bucket in the corpus for the verbatim removed/added
   hunks of the closest anchors.
3. **As a Stage-0 / Stage-1 prior** (`engine/whitebox-analysis.md`): the removed-line shape is a
   candidate-sink signature; the changed function/route/param is the sink Stage 3 must prove is
   reachable.
4. **As a novelty / release-eligibility check** (`engine/whitebox-analysis.md` Stage 5.25 and the
   IBC-card "check release eligibility" steps): compare the target's *actual source shape* against
   the pre/post-patch snapshot — this catches both "this is the already-patched historical bug, don't
   file it" **and** "this is a regression of a patched shape under a newer version," which a
   version-string check alone misses.
5. **As a pocinator differential** (`engine/pocinator.md` §5 lens 11): run the PoC against the pinned
   pre-fix commit (positive) and post-fix commit (negative), with the maintainers' own diff as the
   traced mechanism.
6. **Falsify overclaims:** if the exact added-guard line from the fix commit is present in the
   target's code, the class is (at least locally) patched — do not claim strong activation without a
   further, specific reason (an incomplete-fix sibling path, a regression).

## The gate: IN / CONTESTED / OUT (how each anchor earned its place)

- **IN (machine-checkable signature):** fix commit re-fetchable at a primary source **and** the
  removed→added delta is a clear, isolable security guard **and** CWE + mechanism class-match the
  bucket. Promotable to a Stage-0/Stage-1 signature.
- **CONTESTED (illustrative — quote, don't promote):** the fix is real but entangled with an
  unrelated refactor, spread across multiple commits / a backport with no single whole-fix SHA, or
  the advisory and diff disagree on which check moved. Cited to illustrate the class, not turned into
  a literal match signature.
- **OUT (dropped, reason logged in the corpus):** no fetchable fix commit (version-string-only,
  dead/force-pushed SHA, aggregator-only "patch" link), mislabeled CWE/mechanism, or
  refactor-not-fix (version bump / dependency update / cosmetic).

## Coverage honesty

19 buckets mined across two passes; **108 IN + 19 CONTESTED = 127 anchored fix diffs, 136 candidates
dropped** (mostly closed-source vendors with no public fix commit, or version-bump / release-tag
"fixed" SHAs that resolve to a changelog bump rather than the real code diff). Buckets that clear the
≥6-clean-anchor bar and assert a convention: **BFLA, SSTI, XXE, prototype pollution, JWT** (pass 1)
plus **SSRF (7), OS command injection (7), insecure deserialization (6), HTTP request smuggling (8)**
and **XSS (6, borderline)** after the top-up. Still **THIN** (illustrative, several one anchor short):
IDOR/BOLA (4), auth bypass (4), SQL injection (4), path traversal (5 — 0 net-new this pass, both
candidates dropped), CSRF (5), open redirect (5), file upload (3), crypto (5), OAuth-flow (5). **Not
yet mined** (deferred, not dropped): memory-corruption RCE and cache poisoning.

## Reference (keyed by bug class → CWE). Full hunks + sources in the corpus.

### SSRF (CWE-918) — IN (7 IN / 2 CONTESTED / 12 dropped)
- **Dominant guard shape:** a pre-fetch destination check inserted right before the outbound sink —
  a destination allowlist/filter (`bound`) or input canonicalization/format-constraint. Minority:
  param-binding (trusted-host) and outright sink removal.
- **Closest anchors:** CVE-2020-13379 (grafana, MD5-regex canonicalization), CVE-2024-31461 (plane,
  hostname allowlist), CVE-2025-59146 (new-api, `ValidateURLWithFetchSetting` before `http.Get`),
  axios (scheme-mandatory regex), next.js (trusted-host binding), CVE-2026-53727 (css_parser,
  `SsrfFilter` + scheme-allowlist — also closes a `file://`-redirect→LFI escalation), CVE-2026-4874
  (keycloak, `isHostAllowedForClient` on the backchannel-logout host). CONTESTED: SuiteCRM, parse-server.
- **Grounds:** `skills/patterns/ssrf-server-side-fetch`, `skills/vulns/information-disclosure`.

### IDOR / BOLA (CWE-639 / CWE-284) — THIN (4 IN / 2 CONTESTED / 13 dropped)
- **Dominant guard shape:** swap a client-controlled object key for the authenticated session
  identity, or scope the object lookup by owner (`userid`/`OrgID`) — `exact-match-swap` /
  owner-scoped `per-object-authz`.
- **Closest anchors:** CVE-2024-1313 (grafana), CVE-2025-69207 (khoj), CVE-2026-33702 (chamilo),
  CVE-2025-3636 (moodle). CONTESTED: open-webui CVE-2026-29071 (buried in a multi-file release
  commit), LinkAce GHSA-cj8f-h888-m57m (spread across 9 files).
- **Grounds:** `skills/vulns/broken-object-level-authz`, `skills/patterns/client-supplied-selector-authz`,
  `skills/patterns/bopla-property-authz`.

### BFLA (CWE-862 / CWE-285) — IN (7 IN / 0 CONTESTED / 2 dropped)
- **Dominant guard shape:** a `per-function-authz` check inserted immediately before a
  previously-unguarded sink (route middleware / controller `Forbidden` gate / method-level
  `checkPermission`). Minority: exact-match role-check swap; field-level write-protection binding.
- **Closest anchors:** gitea, craftcms, pimcore, arcadedb (per-function check), easyappointments
  (role-check swap), shopware + plainpad (field-level write-protection). 6/7 promotable signatures;
  arcadedb IN-but-not-promoted (narrated multi-method insertion, not a single verbatim delta).
- **Grounds:** `skills/vulns/broken-function-level-authz`, `skills/patterns/unsafe-default-authz-helper`,
  `skills/patterns/ui-only-policy-enforcement`.

### Auth bypass (generic / middleware / gateway) (CWE-287 / CWE-863) — THIN (4 IN / 1 CONTESTED / 8 dropped)
- **Dominant guard shapes:** (1) canonicalize-path-before-authz so the security matcher can't diverge
  from the routed path (Quarkus IN, fastify-express CONTESTED); (2) bind a trusted internal signal to
  an unforgeable identity — per-process secret on a trusted header (Next.js `param-binding`) or
  immutable id instead of a spoofable display name (openclaw `exact-match-swap`); (3) enforce a
  body-size bound so an AuthZ gateway isn't starved of the payload (Moby).
- **Closest anchors:** Next.js (CVE-2025-29927 family), openclaw, Moby (CVE-2026-34040), Quarkus
  (CVE-2026-50559). CONTESTED: fastify-express. Thinness driven by closed-source vendor firmware/SaaS
  (F5, Palo Alto, Fortinet, Cisco, Atlassian) with no fetchable public fix commit.
- **Grounds:** `skills/vulns/jwt-authentication-bypass`, `skills/patterns/legacy-route-differential`,
  `skills/patterns/transitive-sanitizer-reliance`.

### Insecure deserialization → RCE (CWE-502) — IN (6 IN / 0 CONTESTED / 10 dropped)
- **Dominant guard shape:** `deser-type-filter` — an assignability/allowlist check
  (`Throwable.class.isAssignableFrom` / `SERIALIZABLE_PACKAGES` package-allowlist) inserted right
  before the reflective `Class.forName()` + String-constructor instantiation. The top-up adds three
  non-Java variants: an unpredictable-token + escape-boundary check (serialize-javascript), a
  recursive type-denylist over array/generic type args (MessagePack-CSharp), and an
  unsafe-fallback-path denial that stops silently using the full unpickler (pytorch `weights_only`).
- **Top-up recovered the bucket:** pass 1 was thin (Apache SVN-mirror "fixed" SHAs that are
  version-bump-only, plus a Jenkins CWE mismatch and a PyYAML unmerged-proposal SHA); targeting
  GitHub-native npm/NuGet/PyPI projects added 3 clean anchors to clear the bar.
- **Closest anchors:** CVE-2017-7525 (jackson-databind, package-allowlist), CVE-2023-46604 (ActiveMQ),
  CVE-2020-7660 (serialize-javascript, CSPRNG placeholder), CVE-2026-48517 (MessagePack-CSharp,
  recursive type-denylist), CVE-2025-32434 (pytorch, restricted-unpickler enforcement).
- **Grounds:** `skills/vulns/insecure-deserialization`.

### OS command injection → RCE (CWE-78) — IN (7 IN / 1 CONTESTED / 8 dropped)
- **Dominant guard shape:** `param-binding` — stop interpolating attacker input into a shell-parsed
  string; bind it as a positional argument / disable the shell (`shell:false`, `"$@"`). Secondary:
  `canonicalization` (php Best-Fit byte remap, shell-quote line-terminator escape); the top-up adds
  an executable-basename allowlist (PraisonAI) and a shell-metacharacter denylist+escape (greenshot).
- **Closest anchors:** CVE-2026-9277 (shell-quote), CVE-2026-31975 (claudecodeui), CVE-2024-4577
  (php-cgi), CVE-2025-64756 (node-glob), GHSA-hxwm-x553-x359 (@npmcli/git), GHSA-9qhq-v63v-fv3j
  (PraisonAI, basename allowlist), CVE-2026-22035 (greenshot, metachar denylist). CONTESTED:
  CVE-2025-49141 (haxcms — endpoint deletion, no added guard to promote).
- **Grounds:** `skills/vulns/os-command-injection`, `skills/vulns/injection`.

### SQL injection (CWE-89) — THIN (4 IN / 1 CONTESTED / 10 dropped)
- **Dominant guard shape (bimodal by injection position):** `param-binding` (?-placeholder +
  bindings) for value-position SQLi; allowlist / exact-match validation for identifier/keyword-position
  SQLi that can't be bound as a parameter (`ORDER BY` column, boolean connector, cast type).
- **Closest anchors:** gin-vue-admin (ORDER BY allowlist), librenms (LIKE param-binding), Ghost (slug
  binding), Django (boolean-connector allowlist). CONTESTED: Sequelize (non-contiguous fix).
- **Grounds:** `skills/vulns/sql-injection`.

### Path traversal / LFI (CWE-22 / CWE-98) — THIN (5 IN / 1 CONTESTED / 11 dropped; 0 net-new in the top-up — both candidates dropped as version-bump SHAs)
- **Dominant guard shape:** `canonicalization` — absolutize / URL-decode / normalize the attacker
  path **before** a containment prefix-check (`filepath.Abs`, decode+normalize, `check_file_dir_name`).
  Variants: bound-containment (`inCwd` startsWith), denylist→safe-API (model lookup).
- **Closest anchors:** nuclei (`filepath.Abs`), Ghost (decode+normalize), openemr
  (`check_file_dir_name`), tar-fs (`inCwd` startsWith), hexo (Page-model lookup). CONTESTED: jsPDF
  (gate entangled with a this-binding/use-strict refactor).
- **Grounds:** `skills/vulns/path-traversal-lfi`.

### Server-side template injection → RCE (CWE-1336 / CWE-94) — IN (8 IN / 1 CONTESTED / 6 dropped)
- **Dominant guard shape (two-way split):** (1) escape / JSON-stringify / identifier-allowlist the
  untrusted value before it's concatenated into compiled template source (handlebars `depthedLookup`
  JSON.stringify, ejs & smarty identifier regex, pug, prestashop); (2) wrap the whole render in a
  Twig/Jinja sandbox with an allowlist (cachet `Twig SecurityPolicy`, dynaconf `SandboxedEnvironment`);
  grav a regex denylist variant.
- **Closest anchors:** handlebars, ejs, smarty, pug, prestashop, cachet, dynaconf, grav. CONTESTED:
  CVE-2026-33938 (handlebars AST type-confusion — genuine guard inside a multi-CVE omnibus SHA with a
  spliced hunk).
- **Grounds:** `skills/vulns/server-side-template-injection`.

### XXE (CWE-611) — IN (6 IN / 0 CONTESTED / 7 dropped)
- **Dominant guard shape:** `entity-expansion-off` — `setFeature`/`setProperty` disabling DTD-decl +
  load-external-dtd + external general/parameter entities (dom4j, jackson-databind,
  jackson-dataformat-xml, tika, jenkins flaky-test-handler), or binding a restrictive `EntityResolver`
  in place of null (geoserver). Two variants: direct feature disabling; swap to a safe-default factory
  (`SAXReader.createDefault()`).
- **Closest anchors:** dom4j, jackson-databind, jackson-dataformat-xml, tika, geoserver, jenkins.
- **Grounds:** `skills/vulns/xxe-injection`.

### Prototype pollution (CWE-1321) — IN (7 IN / 0 CONTESTED / 2 dropped)
- **Dominant guard shape:** `prototype-key-block` — a denylist blocking `__proto__` / `constructor` /
  `prototype` path segments (or resetting stepped-onto builtin prototype objects) inside a recursive
  merge / dotted-path setKey / unflatten / config traversal (lodash, minimist ×2, requirejs, ini,
  flat). One canonicalization variant (dset).
- **Closest anchors:** lodash (CVE-2019-10744), minimist (both sequential CVEs, distinct guards),
  requirejs, ini, flat, dset.
- **Grounds:** `skills/vulns/prototype-pollution` (already cited; this deepens it).

### JWT / token validation flaws (CWE-347) — IN (6 IN / 0 CONTESTED / 2 dropped)
- **Dominant guard shapes (two-way split):** (a) reject asymmetric/PEM/SSH keys as HMAC secrets —
  `denylist→safe-API` via `is_pem_format()`/`is_ssh_key()` (python-jose, pyjwt) and PEM-header regex
  canonicalization (fast-jwt) — to kill algorithm confusion; (b) fail-closed algorithm/signature
  binding — require an explicit alg bound to the header (hono), refuse `alg=none` (node-jsonwebtoken),
  require a SignedJWT when signature configs exist (pac4j).
- **Closest anchors:** python-jose, pyjwt, fast-jwt (alg-confusion), node-jsonwebtoken (alg=none),
  hono (alg binding), pac4j (SignedJWT requirement).
- **Grounds:** `skills/vulns/jwt-authentication-bypass`, `skills/patterns/jwt-claim-validation`.

### CSRF (CWE-352) — THIN (5 IN / 1 CONTESTED / 5 dropped)
- **Dominant guard shape:** an authenticity / same-origin check inserted before the state-changing
  sink — an HTTP-method restriction (move the change off a bare `GET`/query-string onto a body-bound
  `POST`), a server-side synchronizer / double-submit token check, or a `Content-Type: application/json`
  gate that forces a CORS preflight a cross-origin form can't pass.
- **Closest anchors:** GHSA-26v7-h57m-gh9m (new-api, GET→POST + query→JSON body), GHSA-jrq5-hg6x-j6g3
  (goshs, double-submit token header), GHSA-ww7h-g2qf-7xv6 (TYPO3 form, `assertAllowedHttpMethod` POST),
  GHSA-5j53-63w8-8625 (fastapi-users, double-submit OAuth-state cookie), GHSA-39hj-fxvw-758m (Sunshine,
  JSON content-type gate). CONTESTED: GHSA-vvmr-8829-6whx (symfony, DI service-ordering fix — not a
  single isolable guard).
- **Grounds:** `skills/patterns/legacy-route-differential`, `skills/vulns/business-logic-abuse` (no
  dedicated CSRF card).

### Reflected / Stored / DOM XSS (CWE-79) — THIN (6 IN / 1 CONTESTED / 6 dropped)
- **Dominant guard shape (bimodal by injection position):** `escape` — HTML-entity-encode the
  attacker value immediately before HTML/template interpolation (better-auth, Statamic, json-markup);
  `param-binding` + tiny exact-match allowlist for value-position input (Talishar `intval` + `1`/`2`
  check); `denylist→safe-API` — run the untrusted string through a dedicated sanitizer before persisting
  it (NocoDB `DOMPurify.sanitize()`); `canonicalization-before-denylist-match` — normalize (`trim()`)
  before comparing against a hard-coded denylisted attribute name, closing a whitespace bypass
  (Roundcube SVG `<animate>` sanitizer).
- **Closest anchors:** better-auth (reflected, escape), Talishar (stored, param-binding+allowlist),
  NocoDB (stored, DOMPurify), Statamic CMS (stored→privilege-escalation, escape), json-markup /
  Jaeger UI (stored, escape — fix lives in the dependency, not jaeger-ui itself), Roundcube Webmail
  (sanitizer-bypass, canonicalization). CONTESTED: Grav admin (GHSA-65mj-f7p4-wggq entangled inside a
  squashed commit fixing four distinct GHSAs plus an unrelated rate-limit change).
- **Thinness driver:** several otherwise-good candidates' OSV "fixed" SHA resolves to a version-bump
  / release-tag commit, not the real code diff (GLPI, Open eClass) — the same failure mode flagged in
  the CWE-502 bucket above. NukeViet and PrestaShop advisories name the fix location in prose but
  supply no resolvable commit SHA at all.
- **Grounds:** `skills/vulns/cross-site-scripting`.

### HTTP request smuggling (CWE-444) — IN (8 IN / 1 CONTESTED / 2 dropped)
- **Dominant guard shapes:** strict header/parser validation that fails closed — reject control chars
  / bare-LF / empty header names / conflicting TE+CL, correct trailer-section boundary detection, or
  an allow-list char table before header serialization.
- **Closest anchors:** CVE-2021-43797 (netty, control-char block + OWS canon), CVE-2023-40175 (puma,
  reject-empty-CL + trailer boundary), CVE-2023-27493 / CVE-2024-23326 (envoy, char-table allowlist /
  status-code allowlist), CVE-2026-2332 (jetty, quoted-chunk-ext parser state), CVE-2025-58068
  (eventlet, discard full trailer), CVE-2024-23452 (brpc, reject TE+CL), CVE-2023-25725 (haproxy,
  reject empty header name across H1/H2/H3). CONTESTED: trafficserver (bare-LF, config-plumbing-entangled).
- **Grounds:** `skills/vulns/http-protocol-abuse`.

### Open redirect (CWE-601) — THIN (5 IN / 1 CONTESTED / 8 dropped)
- **Dominant guard shape:** allow-list / relative-URL validation of the redirect target before
  trusting it — reject absolute netloc + protocol-relative `//host`, or match against a configured
  site/portal/registered-URI set. Minority: scheme/host stripping (rebuild from path+query only).
- **Closest anchors:** CVE-2024-28113 (peering-manager, reject netloc + `//` bypass), CVE-2024-24818
  (espocrm, site+portal allow-list), CVE-2024-28239 (directus, per-driver allow-list + `//host`
  reject), CVE-2026-28415 (gradio, scheme/host stripping), CVE-2026-25649 (traccar, registered
  redirect_uri equality). CONTESTED: CVE-2026-34442 (freescout, Host-header allow-list, entangled).
- **Grounds:** boundary cross-ref for `skills/patterns/ssrf-server-side-fetch` (no dedicated open-redirect card).

### Unrestricted file upload → RCE (CWE-434) — THIN (3 IN / 3 CONTESTED / 10 dropped)
- **Dominant guard shape:** swap a client-controlled / denylist extension check for a server-side
  allow-list or safe-API, or move uploads to a non-executable path.
- **Closest anchors:** CVE-2024-24809 (traccar, denylist→safe-API), CVE-2025-0520 (showdoc,
  exact-match-swap), GHSA-rf6j-xgqp-wjxg (openeclass, allowlist). CONTESTED: CVE-2023-23607 (Dasherr),
  CVE-2026-24897 (Erugo, canonicalization), CVE-2025-32028 (haxcms-php) — each partial or entangled.
- **Grounds:** `skills/vulns/arbitrary-file-upload`.

### Cryptographic weakness (CWE-327 / CWE-916 / CWE-330) — THIN (5 IN / 1 CONTESTED / 7 dropped)
- **Dominant guard shape:** replace a weak primitive with a strong one at the exact call site —
  `Math.random`→CSPRNG (`crypto.randomBytes`/`randomInt`) for token generation (CWE-330); weak
  hash/KDF→strong (MD5/SHA1→BCrypt/SHA256, iterations 1→250k) for password storage (CWE-327/916); or
  delete the insecure API outright.
- **Closest anchors:** CVE-2025-7783 (form-data, Math.random→randomBytes), CVE-2025-22150 (undici,
  randomInt), CVE-2020-5229 (opencast, MD5→BCrypt), CVE-2023-46233 (crypto-js, SHA1→SHA256 + 250k
  iters), CVE-2021-39182 (EnroCrypt, MD5 removed). CONTESTED: CVE-2024-29886 (serverpod,
  SHA-256→Argon2id, migration-entangled).
- **Grounds:** `skills/vulns/cryptographic-weakness`.

### OAuth / OIDC flow flaws (CWE-287 / CWE-863) — THIN (5 IN / 2 CONTESTED / 7 dropped)
- **Dominant guard shape:** bind/verify a flow parameter that was previously unchecked — PKCE
  downgrade-prevention (reject a `code_verifier` when no `code_challenge` was issued), `client_id`
  equality at code exchange, a client-confidentiality predicate on auto-approval, or a boolean-operator
  fix in a rejection predicate. A distinct sub-shape (CONTESTED, mechanism-matched but off the
  CWE-287/863 headline) is auth-code single-use made atomic (claim-and-delete / distributed lock).
- **Closest anchors:** GHSA-mrx3-gxjx-hjqj (authentik, PKCE downgrade), GHSA-qgp8-v765-qxx9 (cloudflare
  workers-oauth-provider, downgrade guard), GHSA-qh6q-598w-w6m2 (pocket-id, AND→OR fix),
  GHSA-xqxv-4jc2-x56x (zitadel, `client_id` equality), GHSA-7w2c-w47h-789w (doorkeeper,
  client-confidentiality predicate). CONTESTED: better-auth (atomic consume), sentry (distributed-lock
  single-use).
- **Grounds:** `skills/patterns/oauth-authorization-code-single-use`, `skills/patterns/oauth-client-binding`,
  `skills/patterns/delegated-capability-attenuation`.

## Non-overclaim caveats (non-negotiable)

- A fix diff proves a bug **existed and was fixed** — never that the disclosing project, or an
  in-scope target pinned at/past the fix tag, is currently exploitable.
- A structural match to a removed-line shape can be a false positive (same shape, guarded elsewhere,
  or unreachable) — it is a lead, not a finding.
- **Incomplete fixes:** presence of the added guard is a strong held signal, **not** a soundness
  proof. A disclosed fix does not always fully close the class (e.g. a guard added to one
  schema-mutating method leaving its siblings unguarded). Guard-present does not exempt Stage-3
  reachability or Stage-4 confirmation.
