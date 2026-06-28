# Post-Phase-14 Capability Fit Review

**Status:** review-only research note — **NOT build permission**\
**Date:** 2026-06-27\
**Governs nothing.** This document evaluates post-Phase-14 *candidate* capabilities (AIWG-inspired
workflow/index, Tollbooth observer, Carbonyl browser adapter, Fortémi memory) against
[Decision 0004](decisions/0004-epistemic-autonomy-complexity-budget.md), the Phase 14 roadmap boundary,
licensing, the complexity budget, and the "sensors not judges" rule. Any item below becomes buildable
**only** after a fresh accepted decision/roadmap update that names the invariant it enforces, the
complexity it deletes, and how it stays outside evaluator truth. Reading this file authorizes no code.

> **Sourcing discipline.** Every external claim is tagged *verified* (read from the source repo's raw
> README/LICENSE/API) or *inferred*/*not directly verified*. Four read-only source-research passes
> produced the facts; no tool was installed or run. No raw secrets, client names, or live engagement
> details appear here.

---

## Executive Recommendation

### Recommended adoption order

1. **AIWG-inspired one-file workflow manifest (harness-native, no dependency).** Smallest, cheapest,
   MIT-derived *pattern* (not the framework), pure Plane-2 markdown. Gate strictly on a **measured
   context reduction**. → *Good first spike.*
2. **Thin local casebook retrieval index (Fortémi-*inspired*, not Fortémi).** A single-file embedding
   index over already-scrubbed `casebooks/` markdown. No external service, no license entanglement, no
   self-rewriting store. Delivers ~90% of the retrieval value Fortémi sells. → *Good first/early spike.*
3. **Tollbooth read-only egress observer — design review first.** Genuine "measure, don't parse" value
   (a second witness to the broker's call ledger), but AGPL-3.0 + a TLS-decrypting MITM that *persists
   API keys* makes it a heavy, secret-laden, copyleft dependency. → *Needs design review; later spike,
   redaction-first, unmodified external container only.*
4. **Fortémi as a substrate — defer.** Heavy multi-service stack (Postgres/pgvector/PostGIS/Redis/LLM/
   Node MCP), BSL-1.1 license, and a **native LLM revision pipeline that self-rewrites stored memory** —
   a direct conflict with the append-only-evidence invariant. Revisit only if the thin index (item 2)
   is outgrown. → *Defer.*
5. **Carbonyl / carbonyl-agent — reject/defer.** Playwright MCP already covers JS-heavy public-page
   recon with a lighter, integrated, permissive path. The carbonyl-agent SDK is AGPLv3 and its headline
   features are **cookie persistence and bot-detection evasion** — both fight our redaction and
   authorized-engagement gates. → *Reject for now.*

### What to avoid

- **Vendoring any AGPL/BSL dependency into the portable harness (Plane 1/2 code).** Tollbooth (AGPL-3.0),
  carbonyl-agent (AGPLv3), and Fortémi (BSL-1.1) all carry copyleft/commercial obligations that would
  contaminate a harness meant to travel. If ever used, only as arms-length, unmodified, out-of-process
  external services with legal sign-off.
- **Adopting any *framework* wholesale.** AIWG's CLI + 200+ agents + `.aiwg/` memory, Fortémi's full
  stack, Carbonyl's Chromium engine. Take patterns/contracts, not frameworks.
- **Any tool emitting a verdict.** Tollbooth's ML refusal classifier, any retrieval "confidence," any
  adapter "success" signal — these are **sensor outputs**, never adjudications. Broker/oracle/evaluator
  stay authoritative.
- **Mutable or self-rewriting memory.** Fortémi's revision jobs; AIWG's `.aiwg/` store. Memory is
  append-only evidence, never self-edited belief.
- **A MITM that persists secrets.** Any observer must redact at the capture boundary before anything
  touches a plane.

### Why this aligns with Decision 0004

- **Epistemic autonomy maximized, constitutional autonomy untouched.** Items 1–2 help the system reason
  and recall without authoring belief; none of the five can change what counts as true/better/safe.
- **Complexity is a finite budget.** The order front-loads the two capabilities that *delete an existing
  path* with *zero new dependency* and back-loads everything that *adds* a heavy external service. Every
  item is gated on "deletes more than it adds," per §4 of 0004.
- **"Measure, don't parse" served, not subverted.** Tollbooth is interesting precisely because it is an
  independent measurement of egress — but only if it never becomes a judge or a secret store.
- **The load-bearing invariant is preserved.** None of these may let a candidate change its evaluator
  and authorize itself; memory and observers are explicitly firewalled from adjudication.

---

## Current Harness Boundary

### What Phase 14 made canonical

- **One public experiment entrypoint:** `tools/run-experiment-lifecycle.py`, composing existing tested
  functions over `preflight → apply → measure → score → replay → record`. It writes only under the
  campaign directory; never to `skills/` or Plane 1.
- **One lifecycle-result contract:** `schemas/lifecycle-result.schema.json` —
  `authoritative_stage` + `authoritative_verdict` are the single truth a reader/automation consults.
- **Authority precedence:** `materialization-block > off-scope > behavioral > shadow`. The deterministic
  shadow scoreboard is advisory; the measured materialization is the boundary; the broker-mediated
  behavioral verdict is the authoritative learning signal.
- **Every old entrypoint classified** (public / internal building block / historical / test-only) in
  `docs/lifecycle-consolidation-inventory.md`.
- **Earned honesty preserved:** `autonomous_gap_closure_count = 0`; a simulator/fake behavioral `allow`
  is correctly non-promotable.

### What post-14 work may and may not do

| May (with a fresh decision) | May **not** (without a separate accepted policy) |
| --- | --- |
| Add a **sensor** that produces evidence into the broker/Plane-3 ledger | Add a **judge**: anything that emits `confirmed`/`allow`/a verdict |
| Add a **read-only retrieval/index** over already-scrubbed memory | Add **mutable or self-rewriting** memory/belief |
| Add a **thin Plane-2 manifest** that points at cards/judges and shrinks context | Add a **framework, runtime, agent zoo, controller daemon, or DB** |
| Reduce loaded context or delete an authority path | Increase loaded context or duplicate an authority path |
| Reconcile an out-of-band measurement against the broker ledger (flag-only) | Let a tool's output **authorize a candidate** or mutate Plane 1 |

Phase 14 is the **last active implementation phase**. The items below are a **review backlog**.

---

## Source Review

### AIWG — `github.com/jmagly/aiwg`

- **Verified facts.** A **deployment/orchestration tool for AI-coding context — not an LLM runtime**
  ("AIWG never calls a model… configures what it sees"). `aiwg use <framework>` **copies markdown+YAML
  source files into each platform's native lookup path** (`.claude/agents/`, `~/.codex/skills/`,
  `.cursor/rules/`, …). Five primitive artifact types (Agents, Skills, Commands, Rules, Behaviors), each
  "a single `.md` file with YAML frontmatter; nothing executes until an AI platform reads it." Explicit
  non-goals: not a prompt library, not an LLM runtime, not an importable framework. **License: MIT**
  (verified via README badge; *verbatim LICENSE file not re-read*). **Actively maintained** (~1,926
  commits, 155 stars, active CI). "200+ agents / 400+ artifacts" are *marketing claims, inferred*.
- **Fit.** The reusable kernel is a **pattern**: per-objective markdown that tells an agent *what to
  read, which tool is authoritative, which artifacts are required, which claims are forbidden*. Maps to a
  thin `engine/workflows/<objective>.md` in Plane 2, beside `engine/loop.md` and `engine/routing.md`.
- **Non-transferable parts.** The CLI, the 200+ agents/behaviors/lifecycle-hooks, the `.aiwg/`
  persistent memory + cost telemetry, and the multi-platform deploy step. All violate the no-zoo /
  no-mutable-memory / complexity-budget rules.
- **Licensing/deployment.** MIT — permissive. We copy *no code*; we reuse a one-file idea, so obligation
  is near-zero. Re-read the LICENSE file before copying any literal text.

### Tollbooth — `github.com/FlechetteLabs/Tollbooth`

- **Verified facts.** A **transparent MITM HTTP/HTTPS proxy built on mitmproxy** ("inspecting, debugging,
  and **modifying** traffic from agent containers"). Application layer — *not* eBPF, *not* an LLM-gateway.
  **Requires TLS interception** via a generated CA (`setup-certs.sh`). Captures *all* container egress;
  parses LLM API calls into conversations; branching/retry tree view; request edit + **response mocking**;
  rules engine; export to JSON/MD/HTML; **ML-powered refusal detection**. Modify/mock are **opt-in, not
  default-on**, but interception is inherent to the proxy path. README states **traffic is persisted to
  disk and API keys are stored**. **License: AGPL-3.0** (verified). Young (created 2026-01-22, ~74
  commits, 18 stars). *Root requirement not directly verified* (CA + Docker typically need elevation).
- **Fit.** A Plane-2/3 **evidence sensor**: a redacted `traffic_digest.json` as a **second witness** to
  the broker's `events.jsonl` — cross-checking observed model/host calls and flagging unexpected egress.
  This directly serves "measure, don't parse."
- **Non-transferable parts.** Modify/mock/drop/rules-engine (must be inert), the ML refusal classifier
  (a judge — forbidden), and the raw decrypted-traffic + API-key store (collides with redaction).
- **Licensing/deployment.** AGPL-3.0 network-copyleft → **never vendor or link**; only as a standalone,
  unmodified, arms-length container with legal sign-off. "Read-only" holds at the *config* level (empty
  rules, no intercept), **never at the wire** — it is a TLS-decrypting MITM by design. State this honestly.

### Carbonyl — `github.com/jmagly/carbonyl` + `github.com/jmagly/carbonyl-agent`

- **Verified facts.** `fathyb/carbonyl` (upstream, **BSD-3-Clause**) = "Chromium running inside your
  terminal," rendering web content to terminal text; **stale** (last release Feb 2023). `jmagly/carbonyl`
  = an **actively-maintained fork** tracking Chromium stable M147, **BSD-3-Clause**, ~100 GB to build
  from source. `jmagly/carbonyl-agent` = a **Python SDK that drives the headless browser** and returns
  rendered terminal text for LLM agents/scraping; adds **session persistence (cookies/localStorage/
  IndexedDB), daemon mode, host-browser cookie import, a uinput "trusted input" backend, and
  bot-detection evasion** (UA spoof, `webdriver` suppression, TLS-fingerprint spoofing). **Relicensed to
  AGPLv3 on 2026-05-31** (verified), last release May 2026, ~10 stars, single-maintainer.
- **Fit.** At most an optional Plane-2 recon **adapter** feeding raw text into Plane-3, for hermetic,
  scope-gated public-source ingestion of JS-heavy pages.
- **Non-transferable parts.** Cookie/secret persistence, host-cookie import, bot-evasion, trusted-input,
  daemon mode — all fight the redaction gate and the *authorized*-engagement ethos.
- **Licensing/deployment.** **License split is the headline:** the renderer is BSD-3 (fine), but the SDK
  we'd actually call is **AGPLv3** (network-copyleft, incompatible with a portable/permissive harness).
  Full Chromium = large attack/CVE/supply-chain surface. **Playwright MCP is already available** and
  covers the only real benefit with less weight and a permissive posture.

### Fortémi — `github.com/Fortemi/fortemi`

- **Verified facts.** A self-hosted "intelligent knowledge base": **hybrid RAG (BM25 + dense vectors,
  fused via RRF) + an automatic knowledge graph** (>70%-similarity links, Louvain communities, W3C
  SKOS). Storage: **PostgreSQL 18 + pgvector + PostGIS + Redis**, multi-memory schema isolation, default
  embedding `nomic-embed-text`. Interfaces: Axum REST + a **Node.js MCP server (43–205 tools)**. **License:
  BSL-1.1**, README states conversion to AGPL-3.0 in **2030** (*verbatim LICENSE file returned 404 —
  not directly verified*). Latest release 2026-06-15, **~19 stars** (early/niche). **Critically: it
  self-rewrites memory** — `matric-jobs` is an async pipeline for "embedding, **revision**, linking,
  extraction"; notes are mutable with revision/reprocessing endpoints. An LLM rewrites stored note
  content.
- **Fit.** A Plane-3/4 **sanitized retrieval substrate** indexing the *output* of the existing Decision
  0001 staging pipeline (raw → redaction/scope → extract → human promotion). It would supply only the
  **retrieval layer** the harness currently lacks (casebooks are flat markdown with no index).
- **Non-transferable parts.** The **revision/reprocessing pipeline** (violates append-only-evidence —
  must be disabled and *proven* off), the multi-service stack (disproportionate at current corpus size),
  and any path where retrieval feeds adjudication (the backdoor-to-belief Decision 0004 forbids).
- **Licensing/deployment.** BSL-1.1: the free grant is a single-user local workstation tool; **server/
  networked/multi-user/hosted use likely requires a commercial license** until 2030. Legal review before
  any non-local use.

---

## Capability Placement Table

| Capability | Candidate source | Fits in | Purpose | Adopt now? | Notes |
| --- | --- | --- | --- | --- | --- |
| **Workflow / context index** | AIWG (MIT) — *pattern only* | Plane 2 (`engine/workflows/<objective>.md`) | Tell the agent what to Read, which tool is the authoritative judge, which artifacts are required, which claims are forbidden — shrink per-loop context | **No** — *good first spike, post-14* | Take the one-file manifest idea; reject the framework, `.aiwg/` memory, agent zoo. Gate on **measured** context reduction + path deletion. |
| **Read-only egress observer** | Tollbooth (AGPL-3.0) | Plane 2/3 evidence sensor → broker ledger | Independent second-witness to the broker call ledger; unexpected-egress flag; traffic digest in evidence bundles | **No** — *needs design review, later spike* | Unmodified external container, rules inert, redact-at-capture, never a judge. AGPL + persisted API keys are the blockers. |
| **Browser / recon adapter** | Carbonyl BSD + carbonyl-agent AGPLv3 | Plane 2 recon adapter → Plane-3 signals | Hermetic public-source ingestion of JS-heavy pages | **No** — *reject/defer* | Playwright MCP already covers this. AGPL SDK + cookie persistence + bot-evasion fight our gates. |
| **Sanitized memory / retrieval** | Fortémi (BSL-1.1) | Plane 3/4 retrieval substrate over casebooks | Semantic recall of prior scrubbed cases + public-source context at recon time | **No** — *defer; build a thin index instead* | Prefer a single-file embedding index over scrubbed `casebooks/`. Fortémi self-rewrites memory (append-only violation) and is a heavy stack. |
| **Sealed evaluator relationship** | *harness-internal (no external tool)* | Plane 2 evaluator boundary | Query a sealed evaluator once after candidate freeze; receive only signed aggregate decisions/failure categories | **No** — *design review after lifecycle is canonical* | Already on the roadmap (Phase 3B+). It is the boundary the *autonomous controller* depends on; none of the four tools may be it. Governs the load-bearing invariant. |
| **Autonomous controller relationship** | *harness-internal (no external tool)* | Plane 2 orchestration | Schedule, replay, reject, archive, open evidence PRs inside the Decision-0004 envelope | **No** — *after Phase 14 + sealed-evaluator design review* | Operational autonomy, bounded. Comes only over the now-canonical lifecycle. Tools above are sensors it *may consume*, never authorities it obeys. |

---

## Worked Examples

### 1. AIWG-style workflow index reducing context load

1. Today, to run the LLM07 rung the orchestrator holds routing heuristics in-context, scans card
   descriptions, and decides which of N `skills/` cards to open.
2. Instead, it Reads one ~30-line `engine/workflows/llm07-system-prompt-leakage.md`:
   ```yaml
   objective: llm07-system-prompt-leakage
   reads: [skills/vulns/llm07-system-prompt-leakage/SKILL.md, skills/oracles/adjudication-oracle.md]
   authoritative_judge: oracle:adjudication-oracle   # the ONLY thing that may emit `confirmed`
   required_artifacts: [attempt, finding]            # Plane-3 outputs this loop must produce
   forbidden_claims: ["candidate self-confirms", "tool output treated as verdict"]
   ```
3. The orchestrator Reads exactly the listed card ids — no fuzzy match, no auto-invoke, no deploy step.
4. **Win condition (the gate):** measured loaded tokens for the loop drop versus the routing-prose path,
   the routing reasoning for that objective is *removed* (not added alongside), and a card that claims
   self-confirmation is mechanically contradicted by `authoritative_judge`. If context does not drop,
   the spike failed its only justification → reject.

### 2. Tollbooth verifying the broker / model-call ledger

1. Run Tollbooth as an **unmodified upstream container**, observe-only: rules engine empty, no intercept/
   edit/mock/drop — pure capture of the agent container's egress.
2. A harness-owned export adapter reads Tollbooth's JSON export and **redacts at the boundary**: strips
   `Authorization`/`Cookie`/`Set-Cookie`/api-key headers, bearer tokens, and signed-URL query params;
   reduces each call to `{method, host, path, status, model, token_counts, timestamp}`.
3. It writes `traffic_digest.json` into the **immutable engagement run dir** (Plane 3), referenced from
   the evidence bundle.
4. A reconciliation check diffs the digest's observed model/host calls against the broker's
   `events.jsonl`: a count mismatch or an unexpected host becomes a **flag-only sensor signal** — it
   never changes a verdict, and the broker ledger stays authoritative.
5. **Golden test:** a digest produced from traffic seeded with known fake keys/JWTs/cookies must contain
   **zero** secrets.

### 3. Carbonyl producing hermetic web recon signals (the bar it must clear, and why it likely doesn't)

1. Input: one public URL that first passes a scope allowlist check (no in-scope live target, ever).
2. Run **ephemeral**: no named profile, persistence off, no host-cookie import, evasion flags off, no
   uinput; render to plain terminal text + final URL only.
3. The adapter forbids any `Set-Cookie`/`Authorization` material from reaching a plane; output is raw
   recon signal into Plane 3, never Plane 1, never a verdict.
4. **Acceptance bar:** it must render a JS-heavy public page our HTTP/DOM path *cannot*, and do so
   *materially better than Playwright MCP on the same page*. Since Playwright MCP already exists and is
   permissively licensed, this bar is rarely met → the example mostly demonstrates why we **defer**.

### 4. Fortémi retrieving sanitized prior cases without becoming oracle truth

1. Define a **read-only retrieval contract** with no write/confirm/authorize verbs:
   `retrieve(query, top_k) -> [{casebook_id, scrubbed_excerpt, score, source_ref}]`.
2. At recon/routing, the orchestrator calls `retrieve("client-supplied selector chooses tenant", 5)` and
   receives scrubbed excerpts from prior casebooks, each **labeled "retrieved prior, not evidence."**
3. Those priors *inform which cards to consider*; they never enter the adjudication path.
4. **Firewall test (the invariant):** disabling the retrieval store must change **no** verdict. If a
   verdict moves, retrieval has become a backdoor to belief → fail. (In the thin-index version this is
   the same contract minus the Postgres/graph/revision machinery — which is why the thin index is
   preferred.)

---

## Proposed Post-14 Review Backlog

> **Review-only.** Nothing here is a build authorization. Each item needs a fresh accepted decision.

### Good first spike

**A. AIWG-inspired one-file workflow manifest (`engine/workflows/`).**
- *Description.* One markdown type per objective listing card ids to Read, the single authoritative
  judge, required Plane-3 artifacts, and forbidden claims. No CLI, no executable, no new memory.
- *Why it matters.* Makes "tools are sensors, not judges" **declarable and checkable per workflow**, and
  shrinks per-loop loaded context by replacing routing re-derivation with a static pointer.
- *Implementation surface.* A few markdown files + a conformance check that each manifest names exactly
  one oracle/broker judge and only resolvable card ids. No dependency.
- *Risk.* Net-new build during a freeze; context-bloat irony if loaded *in addition to* routing prose;
  laundering self-authorization if a candidate-controllable tool were ever named judge.
- *Acceptance.* Measured token drop on one objective; the replaced routing path is deleted; judge
  invariant holds under a self-confirm test; zero new mutable state/secrets; removing `engine/workflows/`
  restores prior behavior with no dangling refs.
- *Kill criteria.* Loaded context does not strictly drop, or it cannot be loaded *instead of* routing
  prose → delete the directory.

**B. Thin local casebook retrieval index (Fortémi-*inspired*, no Fortémi).**
- *Description.* A single-file embedding/BM25 index built over already-scrubbed `casebooks/` markdown,
  with the read-only `retrieve(query, top_k)` contract from Worked Example 4.
- *Why it matters.* Casebooks currently have no retrieval — recall is manual/grep. This delivers ~90% of
  Fortémi's value with no external service, no license entanglement, no self-rewriting store.
- *Implementation surface.* One indexer script + one retrieval function + a frozen recall holdout. Local,
  single-process; embeddings via an already-available local model.
- *Risk.* Secret leakage if redaction upstream is imperfect; context bloat without a top-k cap;
  retrieval drifting into adjudication.
- *Acceptance.* Read-only (no write to any plane); zero secrets on a redaction-probe corpus; retrieved
  context labeled non-authoritative; **firewall test passes** (disabling it changes no verdict);
  bounded, measured per-query context cost.
- *Kill criteria.* Any verdict depends on retrieval, or a secret survives the probe corpus → revert to
  grep.

### Good later spike

**C. Tollbooth read-only egress observer (after design review).**
- *Description.* Unmodified external Tollbooth container, observe-only, feeding a redacted
  `traffic_digest.json` as a broker second-witness (Worked Example 2).
- *Why it matters.* An *independent* network-layer record of what actually left the box — the purest
  "measure, don't parse" sensor for the call ledger.
- *Implementation surface.* External container (no vendoring) + a harness-owned redacting export adapter
  + a flag-only reconciliation report.
- *Risk.* AGPL-3.0 copyleft; TLS-decrypting MITM; **persists API keys**; modify/mock present; the ML
  refusal classifier is a latent judge; live-scope visibility beyond the target.
- *Acceptance.* AGPL containment (standalone unmodified container, nothing linked, legal sign-off);
  modify/mock/drop provably inert; redaction golden test = zero secrets; digest append-only/immutable;
  reconciliation is flag-only; broker stays authoritative; honest "not read-only at the wire" note.
- *Kill criteria.* AGPL boundary can't be cleared, secrets reach a plane, or any digest field feeds an
  accept/reject → reject.

### Needs design review

**D. Sealed evaluator boundary.** Harness-internal; query once after candidate freeze, receive only
signed aggregate decisions/failure categories. The dependency for any autonomous controller. Must be
designed *after* the canonical lifecycle exists (it now does) and *before* a controller. None of the four
external tools may be this. Governs the load-bearing invariant (a candidate can't change its evaluator
and authorize itself).

**E. Autonomous campaign controller.** Harness-internal; schedule/replay/reject/archive/open-PR inside
the Decision-0004 envelope, over the now-canonical lifecycle. Comes only after **D**. May *consume* the
sensors above; may never *obey* them as authorities.

### Reject / defer

**F. Fortémi as a substrate — defer.** Heavy stack, BSL-1.1, and a self-rewriting revision pipeline that
violates append-only evidence. Revisit only if spike **B** is outgrown and multimodal/graph retrieval
becomes load-bearing.

**G. Carbonyl / carbonyl-agent — reject for now.** Playwright MCP already covers JS-heavy public-page
recon with less weight and a permissive license. AGPLv3 SDK + cookie persistence + bot-evasion are net
negatives against our gates. Revisit only if a concrete recon case defeats both HTTP/DOM scraping *and*
Playwright MCP, and the BSD renderer can be used without the AGPL SDK.

---

## Complexity Budget

Per Decision 0004 §4: record the capability added, the old path deleted/internalized, the new concepts/
failure modes, and why a smaller alternative is insufficient.

| Capability | New concepts it adds | Old complexity it deletes / internalizes | Why a smaller alternative is insufficient |
| --- | --- | --- | --- |
| **A. Workflow manifest** | One markdown type + one conformance rule | Per-loop re-derivation of card selection; the unwritten "which tool judges" norm becomes an explicit, checkable artifact | The smaller alternative *is* this — a single static file. Anything smaller (status quo prose) is what it replaces and is measurably larger in loaded context. If it can't beat the prose, it ships nothing. |
| **B. Thin retrieval index** | One indexer + one read-only retrieve contract | The "build our own embedding index" future work; manual grep recall over casebooks | Grep is the smaller alternative and is the kill-criteria fallback; it fails on semantic recall (synonymous selector names, paraphrased lessons). A one-file index is the minimum that adds semantic recall without a service. |
| **C. Tollbooth observer** | An external MITM service + a redacting export adapter + a reconciliation report | Hand-rolled per-provider egress instrumentation | Smaller alternative: trust the broker's own ledger. Insufficient *only* if we need an **independent** witness (broker compromise/bug). That need is not yet demonstrated → later spike, not now. |
| **D. Sealed evaluator** | A sealed boundary + signed aggregate decision format | Folds today's "evaluator immutable during a campaign" rule into a mechanically sealed surface | A convention (current immutability gate) is the smaller alternative and holds today. A sealed boundary is required only when an *autonomous* controller could otherwise reach the evaluator — i.e. only alongside **E**. |
| **E. Autonomous controller** | Scheduling/replay/archival/PR automation over the lifecycle | Manual per-candidate driving of the canonical lifecycle | Manual operation is the smaller alternative and is correct until a concrete throughput wall appears. Not justified by potential future reuse alone (0004 §4). |
| **F. Fortémi** | Postgres/pgvector/PostGIS/Redis/LLM/Node MCP + graph + SKOS + revision jobs | (Claims to internalize retrieval) — but adds far more than it deletes | **B** is the smaller alternative and delivers ~90% of the value with none of the stack, license, or append-only-violation cost. Fortémi is insufficient*ly justified*, not insufficient in capability. |
| **G. Carbonyl** | A full Chromium engine + AGPL SDK as a recon path | (Claims to replace brittle scraping) | Playwright MCP is the smaller alternative, already integrated and permissive. Carbonyl adds attack surface and license cost for a benefit Playwright already provides. |

---

## Final Recommendation

### Exact next decision to write, if any

**None is required to *stay paused*.** If the project wants to unfreeze the cheapest item, the next
decision to author is a **narrow Decision 0005 — "Harness-native workflow manifest + thin casebook
retrieval index (sensors, not judges)"** that:
- authorizes **only** spikes **A** and **B** above;
- restates that both are read-only, produce no verdicts, hold no mutable/self-rewriting state, add no
  external dependency, and are deletable;
- makes each spike's acceptance gate (measured context drop for A; firewall test for B) a hard
  precondition for keeping the code;
- explicitly does **not** authorize Tollbooth, Carbonyl, Fortémi, the sealed evaluator, or the
  controller.

Tollbooth (C) and the sealed evaluator (D) each warrant their **own** later design-review decision; do
not bundle them.

### Exact next spike goal, if any

> *Spike A:* Add one `engine/workflows/llm07-system-prompt-leakage.md` manifest and a conformance check;
> prove loaded-context for that loop strictly drops versus the routing-prose path and that the routing
> reasoning for that objective is deleted, not duplicated. If context does not drop, delete the spike.

This is the smallest possible step, requires no dependency, no license review, and either deletes a path
or deletes itself.

### What remains intentionally unbuilt

- **No sealed evaluator, no autonomous controller, no live GEPA, no evaluator co-evolution, no
  tool-adapter implementation** — none is authorized by this review.
- **No AGPL/BSL dependency vendored** into the portable harness.
- **No tool that emits a verdict**; broker/oracle/evaluator truth stays authoritative.
- **No mutable or self-rewriting memory**; memory stays append-only evidence.
- **`autonomous_gap_closure_count` stays `0`** — nothing here closes a gap; these are sensors and aids,
  not learning.

---

### Validation

- All external claims are tagged *verified* or *inferred/not directly verified*; the Fortémi LICENSE file
  and AIWG LICENSE file bodies were not re-read (license *names* came from README/badge — re-read before
  any literal copy), and Tollbooth's root requirement is *not directly verified*.
- No implementation changes were made except this report. No Plane-1 edit, no code, no vendored
  dependency, no tool installed or run.
- No raw secrets, client/target names, or sensitive engagement details appear here.
- **This backlog is review-only. It is not build permission.** Each item requires a fresh accepted
  decision naming the invariant it enforces and the complexity it deletes.
