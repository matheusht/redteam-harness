# Deep-research + oracle plan — the "CVSS-in-the-wild, per bug class" severity-precedent oracle

*Same shape and rigor as the HackerOne humanization pass: mine a corpus of real public artifacts that carry a built-in, third-party ground truth, keep only what survives an oracle gate, and ship the distilled convention as a card the harness loads by id. Here the artifact is the published CVSS vector string, and its ground truth is that the vector was assigned by NVD / a CNA / a GHSA reviewer, is immutable, timestamped, and re-fetchable — not something the harness reasons into existence.*

---

## 1. ROLE and the gap it closes

**What it is.** A severity oracle that, for a confirmed finding of a given bug class, answers one narrow question: *how did real disclosed CVEs/GHSAs of this same class actually get scored* — especially on the metrics that CVSS metric-definitions alone do not settle (Scope, Confidentiality, Integrity, Attack Complexity, Privileges Required / Attack Requirements). It emits a per-class convention plus the closest real CVEs to cite, so a report's severity argument is anchored to scorer precedent rather than defended from first-principles metric-definition reasoning.

**The gap, grounded in the harness map.** Two places in the harness already name this exact need and leave it unbuilt:

- `skills/reporting/hackerone-reports.md` (§"Ground severity in real disclosed comparable CVEs when metric definitions alone don't converge") records the pain point in the harness's own words: for a generic-mechanism bypass (framework-level authz gap, gateway bypass, middleware defect) the metric definitions "alone often don't settle" whether C/I should be scored for the worst case the mechanism *could* reach or only what was *directly demonstrated*. Its worked evidence is that real disclosed precedent for the *same bug shape* is genuinely split even among well-known projects: a prior CVE on the very same project scored Integrity **Low**, a structurally similar middleware auth bypass scored Integrity **High**, and a path-normalization bypass scored Integrity **None**. It calls out Scope specifically as the metric "real scorers apply inconsistently" relative to the "different security authority" reasoning a researcher constructs from first principles, and prescribes: search for and cite the closest real disclosed CVEs and *match their convention*. Today that prescription is prose advice with no corpus behind it — every reviewer re-does the search ad hoc.
- `engine/regrade.md` §5 and `skills/oracles/regrade-oracle.md` ("What this oracle is NOT for") both explicitly fence off a **"CVSS-precedent-reviewer pattern"** — "a narrower, later, severity-methodology-only pass" that is *distinct from* a regrade of the finding's validity — and point at `skills/reporting/hackerone-reports.md` as where it lives. So the harness has already decided this pass exists, is separate from regrade and pocinator, and needs disclosed-CVE precedent as its input — but it has **no oracle card, no corpus, and no gate**. It is the one Post-stage judgment pass named in the docs that was never given a backing artifact.

**Why this is the same template as the HackerOne pass.** The map's `autoresearch-evals-roadmap` and `skills` audits both independently flag the finding-severity field as un-anchored: `schemas/finding.schema.json` stores only a bare `severity` enum (`info/low/medium/high/critical`) with no CVSS reasoning, and `engine/regrade.md`'s own worked examples (the JVM filter-chain critical→high downgrade, the Vercel-flags prototype-pollution critical→high revision) are the reviewing model re-deriving CVSS from scratch — "the same textbook CVSS methodology that `skills/reporting/hackerone-reports.md`'s separate CVSS-precedent-reviewer pattern was built to patch elsewhere." This pass replaces that from-scratch re-derivation with a mined distribution of how the class is really scored, and — critically — the ground truth is built into the artifact (a published, authority-assigned vector), so the oracle is not subjective.

**What it is NOT.** Not a revalidation of whether the finding is real (that is regrade). Not a check of whether the PoC proves the claim (that is pocinator). Not a general CVSS tutorial. It only supplies scoring precedent for a class, keyed to the contested metrics, once validity is already settled.

---

## 2. HARD RULES (refuse to include an entry otherwise)

1. **Real published vectors only.** Every cited vector must exist verbatim as a string in a primary-authority record (NVD, a CNA's CVE record, or a GHSA advisory). No hand-constructed vectors, no "what it should have scored," no reconstructed-from-the-prose vectors. If the authority published a base score but not a full vector, the entry is metadata-only and cannot back a per-metric convention.
2. **No fabrication; everything re-fetchable.** Store, per entry: CVE/GHSA id, the full vector string, the CVSS version, the numeric base score, the assigning authority, and the source URL. A reader must be able to reproduce the lookup and land on the identical vector. An id or vector that cannot be re-fetched at a primary authority is dropped, never paraphrased in.
3. **Re-verify at the primary source, never an aggregator.** Snyk, Tenable, VulDB, vendor blogs, and enrichment feeds (e.g. CVSS-BT / EPSS-joined dashboards) frequently show a base score or vector that diverges from NVD/GHSA — sometimes a temporal/enriched score, sometimes the aggregator's own re-scoring. Confirm the vector against NVD's CVE API (or the GHSA record / CVE-List v5 JSON) before it counts. If only an aggregator carries a vector, the entry is **unverifiable → OUT**.
4. **Class match by CWE + mechanism, not title keyword.** A CVE titled "SSRF" that is really an open redirect (CWE-601), or a "deserialization" that is actually an auth bypass, is cross-class contamination. Verify the CWE id *and* read the advisory's mechanism description; keyword-in-title is not sufficient to place a CVE in a bucket.
5. **Record the assigning authority and any intra-CVE disagreement.** Many CVEs carry more than one CVSS assessment (NVD's analysis, the CNA-of-record's, sometimes an ADP/CISA vector). When they disagree, record **all** of them — the disagreement is itself a datapoint about a contested metric, and silently picking one authority is a scoring choice the oracle must not make on the corpus's behalf.
6. **Never translate across CVSS versions.** `skills/reporting/hackerone-reports.md` already proved metric-for-metric translation between 3.1 and 4.0 is non-proportional (a 4.0 "high" landing at 10.0 Critical under a mechanical 3.1 S:C/C:H/I:H translation; a hedged I:L still computing 9.3). Keep 3.1 and 4.0 in **separate columns per class**; a convention is only ever stated within one version.
7. **Distribution over anecdote.** A convention is emitted only from the distribution across the whole bucket, never from the single most severe, most cited, or most recent example. The modal value and the spread are the product; a lone outlier is reported as an outlier.
8. **Benign by construction.** The corpus is scoring metadata (ids, vectors, scores, CWE, links) — no exploit payloads, no PoCs. This pass emits no attack content, so it raises no `safe_signal` gate; it is a reporting/severity artifact.

---

## 3. SOURCES (which are structured and clean; which need care)

**Clean, structured, primary — use as the backbone:**

- **NVD CVE API 2.0 (`services.nvd.nist.gov`).** Authoritative CVSS vectors (v3.1 and, increasingly, v4.0), CWE, and reference links, queryable by CVE id, CWE, and keyword; each record exposes NVD's own analysis vector *and* any CNA-supplied vector separately. This is the primary cross-check for every entry. **Caveat to design around:** NVD's post-2024 analysis backlog means many recent CVEs carry no NVD-analyzed vector yet — only the CNA's. So NVD is authoritative *when present* but incomplete for the newest CVEs; do not treat "no NVD vector" as "no ground truth."
- **GitHub Security Advisories (GHSA), via the GraphQL Security Advisory API / mirrored on OSV.dev.** For open-source and GitHub-hosted packages this is often the CNA-of-record and the most mechanism-informed vector (assigned by a maintainer/GHSA reviewer who read the fix). Carries CVSS vector, CWE, affected-version range, and a linked fix commit. For the pattern/vuln classes this harness cares about most (BOLA, SSRF, prototype pollution, deserialization, XXE, path traversal, OAuth/JWT), GHSA is frequently the cleanest source and the best primary. This is the same corpus family already proven fetchable and already used ad hoc in `engine/pocinator.md` (the Zuul `zuul-core` resolved-jar case).
- **CVE List v5 JSON (`cve.org` / the CVEProject GitHub feed).** Carries the CNA-assigned vector even when NVD has not analyzed the record — the gap-filler for rule 2's re-fetchability requirement when NVD is silent.

**Usable with care:**

- **Vendor / project security advisories (Apache, Django, Kubernetes, HashiCorp, etc.).** Often the CNA and the origin of the authoritative vector, but formats vary; treat as primary only when the advisory *is* the CNA record for that CVE, and still cross-check the vector against NVD/CVE-List.
- **Bugcrowd VRT + program-published severities.** Useful as an *independent* severity-precedent cross-check (a structured taxonomy), but VRT is a rating band, not a CVSS vector — use to sanity-check a class's typical band, never as a vector source.

**Aggregator-trap — explicitly excluded as a vector source:**

- **Snyk DB, Tenable, VulDB, and CVSS-enrichment dashboards.** High coverage, but they routinely surface a re-scored, temporal, or enriched vector that differs from the authority's base vector. Fine for *discovery* (finding candidate CVE ids for a class), never for the *vector of record*. Any entry whose vector exists only on an aggregator is OUT (rule 3).
- **Narrative writeups / blog indexes (PortSwigger Academy writeups, pentester.land).** No built-in structured ground truth; do not substitute for NVD/GHSA when the goal is an oracle-gated vector.

---

## 4. METHOD

**Step 0 — fix the class taxonomy and its CWE anchors (Opus, once).** Define the bucket list and pin each bucket to the CWE id(s) that gate membership, so rule 4 (class-match) is mechanical, not vibes. Proposed buckets (≈15–20), each with primary CWE anchor:

- SSRF (CWE-918)
- IDOR / BOLA — broken object-level authz (CWE-639 / CWE-284 / API1)
- BFLA — broken function-level authz (CWE-862 / CWE-285)
- Auth bypass — generic mechanism/middleware/gateway bypass (CWE-287 / CWE-863) *(the exact "shape" the reporting skill flags as least-convergent)*
- RCE by subtype, split into separate buckets because they score differently:
  - Insecure deserialization (CWE-502)
  - OS command injection (CWE-78)
  - Server-side template injection → RCE (CWE-1336 / CWE-94)
  - Unrestricted upload → RCE (CWE-434)
  - Memory-corruption RCE (CWE-787 / CWE-120)
- SQL injection (CWE-89) and NoSQL injection (CWE-943), separate buckets
- Cross-site scripting — split reflected / stored / DOM (CWE-79) because UI/Scope conventions differ across the three
- HTTP request smuggling (CWE-444)
- Prototype pollution (CWE-1321) — note the frequent CWE-1321-vs-CWE-863 mislabel the reporting skill already warns about
- XXE (CWE-611)
- Path traversal / LFI (CWE-22 / CWE-98)
- CSRF (CWE-352)
- Open redirect (CWE-601)
- Cache poisoning (CWE-524 / web-cache-deception)
- JWT / token validation flaws (CWE-347)
- GraphQL authz abuse (routes to BOLA/BFLA CWEs; kept as a discovery lens)
- Information disclosure (CWE-200) — deliberately kept as a low-severity anchor bucket

**Step 1 — collect a set of real comparable CVEs per bucket (Sonnet researchers, fan-out).** For each bucket, use NVD keyword+CWE queries and GHSA CWE queries to assemble a candidate set, then filter to true class members by reading each advisory's mechanism (rule 4). Target ≈8–15 re-verified CVEs per bucket; record every candidate that was *dropped for contamination* and why (this dropped-list is itself a fixture for the routing/false-discovery corpora later).

**Step 2 — re-verify and normalize each vector (Sonnet).** For every kept CVE: pull the full vector from NVD *and* the CNA/GHSA record; record all assessments and any disagreement (rule 5); tag the CVSS version; store id, vector, score, authority, CWE, source URL, one-line mechanism, and the linked fix commit where present.

**Step 3 — compute the per-metric distribution per bucket, per CVSS version (Sonnet tabulates, Opus reviews).** Within each bucket, and separately for 3.1 and 4.0, tabulate the value distribution of every metric, with special attention to the contested ones:

- **CVSS 3.1:** Scope (S:U vs S:C), Confidentiality / Integrity / Availability magnitude (H/L/N), Attack Complexity (L vs H), Privileges Required (N/L/H), User Interaction (N vs R).
- **CVSS 4.0:** the Vulnerable-System group (VC/VI/VA) vs the Subsequent-System group (SC/SI/SA) — 4.0's replacement for Scope, where SSRF-pivots-to-metadata and sandbox-escape reasoning now live; Attack Requirements (AT:N vs AT:P); Attack Complexity; Privileges Required; User Interaction (N/P/A).

For each contested metric, record the modal value, the fraction agreeing, and the full spread. Expected, testable-against-the-corpus hypotheses to confirm or refute (not to assume): SSRF Scope splits on whether a pivot/metadata read was demonstrated vs a bare server-side fetch; read-only IDOR clusters at C:H / I:N; auth-bypass Integrity is the genuinely-split metric the reporting skill already observed; request smuggling and race/TOCTOU cluster at AC:H (3.1) / AT:P (4.0); deserialization and command injection cluster at AC:L with full C:H/I:H/A:H; stored vs reflected XSS diverge on UI and Scope.

**Step 4 — note the 3.1↔4.0 split explicitly per bucket.** Record how many of each bucket's CVEs carry a 4.0 vector vs only 3.1, and never merge the two. Where a class is scored under both, present both conventions side by side and flag that they are not translations of each other.

---

## 5. ORACLE GATE (what is IN, OUT, or CONTESTED)

A per-class severity convention is emitted only if it passes the gate; otherwise it is surfaced honestly rather than forced into a number.

**IN — a convention is asserted for a (class, CVSS-version, metric) when all hold:**
- **≥ N=6 re-verified comparable CVEs** in the bucket for that CVSS version (≥8 preferred); below 6 the class is "thin — illustrative only," may cite examples but asserts no convention.
- **Class match verified by CWE + mechanism**, not title keyword (rule 4).
- **Every backing vector re-verified at a primary authority** (NVD / GHSA / CVE-List), aggregator-only vectors excluded (rule 3).
- **A clear modal value** for the metric — the mode covers **≥ ~2/3** of the bucket. Emit as: "typical `<value>` (k/n CVEs), cite `<closest CVEs>`."

**CONTESTED — surface the real distribution, do not force a number, when:**
- No value reaches the ~2/3 mode (genuine split), **or**
- The split is *structured* (e.g. bimodal: read-only demonstrations score one way, pivot/chain demonstrations another) — in which case name the discriminator, not just the percentages. Example output shape: *"SSRF Scope is CONTESTED: S:U when only server-side fetch is demonstrated (k CVEs), S:C when metadata/internal-service pivot is reached (m CVEs) — score to what was demonstrated, cite the matching sub-cluster."* This directly operationalizes the reporting skill's Zuul-style problem: the reviewer is handed the real split and its discriminator instead of arguing Scope from the "different security authority" definition.
- Intra-CVE authority disagreement (NVD vs CNA) is itself recorded as a contested signal for that metric.

**OUT — excluded entirely:**
- Single example (one CVE cannot establish a convention; may still be cited as a lone comparable, never as "the convention").
- Cross-class contamination (CWE/mechanism mismatch).
- Unverifiable vector (aggregator-only, or not re-fetchable at a primary authority).
- Reporter/researcher self-assigned severity with no CNA/third-party record behind it.

The gate's design principle mirrors the humanization ruleset's "IN rules only, survived per-quote verification": nothing enters the reference that a reader cannot re-fetch and re-confirm, and a genuine split is shipped *as a split* rather than laundered into a false consensus.

---

## 6. OUTPUT

**Primary artifact — a new oracle card:** `skills/oracles/severity-precedent-oracle.md` (terse, invocable-by-id, same form as the existing `skills/oracles/*-oracle.md` cards). It defines the pass, the IN/OUT/CONTESTED gate above, and a keyed reference table.

**Backing corpus:** `skills/oracles/references/severity-precedent-corpus.md` (or `skills/reporting/research/severity-precedent-corpus.md` to sit beside the HackerOne corpus) — the full per-CVE evidence table (id, vector, version, score, authority, CWE, mechanism, fix-commit link, source URL) plus the dropped-for-contamination list, so every convention in the card is auditable to its backing rows. This is the analogue of `hackerone-genuine-human-corpus.md` backing `hackerone-humanization-ruleset.md`.

**Card reference shape, keyed by bug class:**

```
<bug class>  (CWE anchor)
  CVSS 3.1:  typical vector  ->  base score
  CVSS 4.0:  typical vector  ->  base score
  Contested metrics:
    Scope (3.1) / Subsequent-System (4.0):  IN <value> (k/n)  OR  CONTESTED <split + discriminator>
    Integrity:                              IN <value> (k/n)  OR  CONTESTED ...
    Attack Complexity / Attack Requirements: ...
    Privileges Required:                    ...
  Closest real CVEs to cite:  <3–5 CVE/GHSA ids + links, one line of why each is the closest comparable>
  n = <bucket size>,  version coverage = <#3.1 / #4.0>
```

**Consumption edits (small, into existing skills):**
- `skills/reporting/hackerone-reports.md` §"Ground severity in real disclosed comparable CVEs": replace the ad-hoc "search for and cite the closest real CVEs" instruction with "load `skills/oracles/severity-precedent-oracle.md`, match the class convention, cite its closest CVEs; only fall back to a fresh search if the class is thin/absent."
- `skills/reporting/vulnerability-report-writing.md` §Severity: point the per-metric reasoning at the oracle for the contested metrics.
- `engine/regrade.md` §5 and `skills/oracles/regrade-oracle.md` "What this oracle is NOT for": update the cross-reference so the carved-out CVSS-precedent pass now names its concrete backing card instead of only pointing at reporting prose.

---

## 7. HOW IT PLUGS IN

**Pipeline stage.** This is the **"CVSS-precedent reviewer" narrow pass** that `engine/regrade.md` §5 and `regrade-oracle.md` already define as a *distinct, later, severity-methodology-only* Post-stage — separate from regrade (is-it-real) and pocinator (does-the-PoC-prove-it). It runs in the `Post: triage -> regrade -> pocinator -> filing` band, after regrade has settled validity and the claim tuple, at severity-authoring / report-writing time. It consumes the finding's confirmed mechanism + CWE, returns the class convention + contested-metric guidance + cite-list, and feeds:

- the report's **Severity section** (`skills/reporting/vulnerability-report-writing.md`), where per-metric reasoning is authored, and
- the finding's bare `severity` enum (`schemas/finding.schema.json`), giving the enum a precedent-anchored justification the schema itself doesn't store.

**Skills it strengthens.**
- `skills/reporting/hackerone-reports.md` and `vulnerability-report-writing.md` — turns "match disclosed precedent" from advice into a loadable, corpus-backed lookup.
- `engine/regrade.md` — its own §5 carve-out finally has a backing artifact; its worked severity-correction examples (JVM filter-chain, prototype-pollution) gain an external anchor instead of from-scratch CVSS re-derivation.
- `engine/pocinator.md` lens 6 (claim strength) — a severity claim can now be checked against class precedent, not just internal consistency.
- `skills/vulns/*` and `skills/patterns/*` severity_rubric fields — the map notes these are asserted from OWASP/textbook knowledge with zero citations; each card's rubric can cite the matching class convention as its external anchor (the same "cite a real disclosed anchor" move already proven on the IBC/workflow cards).

**Boundary preserved.** It does not re-open validity (regrade's job) or PoC fidelity (pocinator's job); it is severity-only, exactly as the docs already require.

---

## 8. MODEL ROUTING and scale

Per the harness roster (`engine/roster.md`, and the memory routing roster: Sonnet for hunter/investigation fan-out, Opus for orchestration/triage):

- **Opus (orchestration, once + adjudication):** fix the class taxonomy and CWE anchors (Step 0); set the gate thresholds (N, the ~2/3 mode); adjudicate IN vs CONTESTED and name the discriminator for each split; police cross-class contamination; assemble the final card + corpus. This is judgment work — deciding a genuine split from a thin bucket, and refusing to force a number — which is the same reason regrade/pocinator put the verdict call on the planning tier.
- **Sonnet (researchers, fan-out, one per 1–2 buckets):** run the NVD/GHSA queries, filter candidates to true class members by CWE+mechanism, re-verify each vector at a primary authority, record intra-CVE authority disagreements, and tabulate the per-metric distribution. Structured, high-volume, cheap-per-item verification — well-suited to the mid tier.
- **Helper/offline (optional):** mechanical de-dup of CVE ids across buckets and link-liveness checks.

**Rough scale.** ≈15–20 buckets × ≈8–15 re-verified CVEs each ≈ **150–300 CVE vectors** re-verified at a primary authority, plus the dropped-for-contamination set. Comparable in magnitude to the 74-report HackerOne pass, but the artifacts are far cheaper to verify — a CVSS vector is a single structured field with a canonical authority, versus a full report whose voice had to be read and quote-verified — so the per-item cost is lower even at higher item count. A first pass can ship the ≈8–10 highest-leverage buckets for this harness (SSRF, BOLA, auth bypass, prototype pollution, deserialization, XXE, path traversal, SQLi, stored XSS, request smuggling) and grow the rest incrementally, exactly as the vuln/pattern-card grounding is being back-filled.

---

## 9. Honest limitations (stated up front, not discovered later)

- **NVD backlog skews version coverage.** Newer CVEs increasingly carry only a CNA/GHSA 4.0 vector with no NVD 3.1 analysis; older ones only 3.1. Some buckets will have a strong 3.1 convention and a thin 4.0 one (or vice versa). The card must show version coverage per bucket and refuse to translate to fill the gap (rule 6).
- **Scorer inconsistency is the subject, not a defect to smooth over.** The whole reason this pass exists is that real scorers disagree on Scope/Integrity for the same class. The oracle's job on those is to surface the split *with its discriminator*, not to manufacture a consensus — a CONTESTED verdict is a success, not a failure, of the gate.
- **CWE labels are themselves imperfect.** Some CVEs are mis-CWE'd at the source (the prototype-pollution-vs-incorrect-authorization confusion the reporting skill already flags). Class membership is decided by CWE **and** a read of the mechanism, and a mislabeled-at-source CVE that is really another class is dropped to the contamination list with a note.
- **Precedent is convention, not correctness.** Matching how a class was scored is more defensible to a triager and closer to what reviewers expect (and it protects the HackerOne Signal score the reporting skill notes) — but it is scorer *convention*, which can itself be wrong. The card frames its output as "what real scorers did," never as "the objectively correct score," and leaves the operator free to argue a departure explicitly, backed by the shown distribution.
