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

12 buckets mined this pass; **64 IN + 9 CONTESTED = 73 anchored fix diffs, 81 candidates dropped**
(mostly closed-source vendors with no public fix commit, or version-bump-only SVN-mirror "fixed"
SHAs). 5 buckets cleared the ≥6-clean-anchor bar (**BFLA, SSTI, XXE, prototype pollution, JWT**); the
other 7 are **THIN** (illustrative, several one anchor short). **Not yet mined** (deferred, not
dropped): XSS, CSRF, open redirect, request smuggling, memory-corruption RCE, cache poisoning, and
the OAuth-flow pattern cards — fix-diff-clean GHSAs there are sparser and want a top-up pass.

## Reference (keyed by bug class → CWE). Full hunks + sources in the corpus.

### SSRF (CWE-918) — THIN (5 IN / 2 CONTESTED / 9 dropped)
- **Dominant guard shape:** a pre-fetch destination check inserted right before the outbound sink —
  a destination allowlist/filter (`bound`) or input canonicalization/format-constraint. Minority:
  param-binding (trusted-host) and outright sink removal.
- **Closest anchors:** CVE-2020-13379 (grafana, MD5-regex canonicalization), CVE-2024-31461 (plane,
  hostname allowlist), CVE-2025-59146 (new-api, `ValidateURLWithFetchSetting` before `http.Get`),
  axios (scheme-mandatory regex), next.js (trusted-host binding). CONTESTED: SuiteCRM, parse-server.
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

### Insecure deserialization → RCE (CWE-502) — THIN (3 IN / 0 CONTESTED / 10 dropped)
- **Dominant guard shape:** `deser-type-filter` — an assignability/allowlist check
  (`Throwable.class.isAssignableFrom` / `SERIALIZABLE_PACKAGES` package-allowlist) inserted right
  before the reflective `Class.forName()` + String-constructor instantiation.
- **Weakest bucket, and the reason is itself a datapoint:** the CWE-502 seed is heavy with Apache
  SVN-mirrored projects whose OSV "fixed" SHAs are version-bump-only commits; the adjudicator also
  dropped Jenkins (CWE mismatch — per-function-authz mechanism) and PyYAML (SHA pointed at an
  *unmerged proposal*, not the shipped 5.1 fix). Prime candidate for a targeted top-up.
- **Grounds:** `skills/vulns/insecure-deserialization`.

### OS command injection → RCE (CWE-78) — THIN (5 IN / 1 CONTESTED / 4 dropped)
- **Dominant guard shape:** `param-binding` — stop interpolating attacker input into a shell-parsed
  string; bind it as a positional argument / disable the shell (`shell:false`, `"$@"`). Secondary:
  `canonicalization` (php Best-Fit byte remap, shell-quote line-terminator escape).
- **Closest anchors:** CVE-2026-9277 (shell-quote), CVE-2026-31975 (claudecodeui), CVE-2024-4577
  (php-cgi), CVE-2025-64756 (node-glob), GHSA-hxwm-x553-x359 (@npmcli/git). CONTESTED: CVE-2025-49141
  (haxcms — endpoint deletion, no added guard to promote).
- **Grounds:** `skills/vulns/os-command-injection`, `skills/vulns/injection`.

### SQL injection (CWE-89) — THIN (4 IN / 1 CONTESTED / 10 dropped)
- **Dominant guard shape (bimodal by injection position):** `param-binding` (?-placeholder +
  bindings) for value-position SQLi; allowlist / exact-match validation for identifier/keyword-position
  SQLi that can't be bound as a parameter (`ORDER BY` column, boolean connector, cast type).
- **Closest anchors:** gin-vue-admin (ORDER BY allowlist), librenms (LIKE param-binding), Ghost (slug
  binding), Django (boolean-connector allowlist). CONTESTED: Sequelize (non-contiguous fix).
- **Grounds:** `skills/vulns/sql-injection`.

### Path traversal / LFI (CWE-22 / CWE-98) — THIN (5 IN / 1 CONTESTED / 8 dropped)
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

## Non-overclaim caveats (non-negotiable)

- A fix diff proves a bug **existed and was fixed** — never that the disclosing project, or an
  in-scope target pinned at/past the fix tag, is currently exploitable.
- A structural match to a removed-line shape can be a false positive (same shape, guarded elsewhere,
  or unreachable) — it is a lead, not a finding.
- **Incomplete fixes:** presence of the added guard is a strong held signal, **not** a soundness
  proof. A disclosed fix does not always fully close the class (e.g. a guard added to one
  schema-mutating method leaving its siblings unguarded). Guard-present does not exempt Stage-3
  reachability or Stage-4 confirmation.
