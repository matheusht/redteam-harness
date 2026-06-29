# Track B — Red-team search, autoresearch, and self-improvement methods (2025–2026)

**Status:** research memo (knowledge lane, not a build authorization). Every method below is a
**hypothesis until harness-validated**. Nothing here authorizes a candidate to mutate the evaluator,
oracle, scorer, gold, casebooks, budgets, sealed data, or conformance checks; nothing weakens
`safe_signal`, broker authority, oracle separation, materialization, replay, the FDR hard veto, or
PR-only promotion. LLM reviewers may triage; they cannot approve persistence or declare a candidate
better.

**Date:** 2026-06-29 · **Author:** Track-B research fork · **Consumes:** Decisions 0002/0003/0004,
`docs/gepa-autoresearch-implementation-plan.md`, `docs/lifecycle-consolidation-inventory.md`,
`tools/{run-experiment-lifecycle,run-gepa-real,run-behavioral-eval,score-candidate,replay-candidate}.py`.

**Verification ledger:** 14 sources **directly verified** (fetched, substantive content extracted);
3 corroborated via search snippets / secondary summaries only (lower confidence, flagged in the
table); the EMNLP-2025 "Rethinking Jailbreak Evaluation" PDF and the RedAgent PDF did not render —
treated as **not directly verified** and not load-bearing for any recommendation. The brief's seed
list named several systems I could not independently verify as primary sources (CoP agentic
red-teaming, "Jailbreak Autoresearch", Claudini, JustAsk, the Cerebras anti-cheating writeup,
SciTriage, AgentHarm-Gen / Red-Agent-Reflect); rather than invent details I **omit** them. The
≥15-directly-verified target is narrowly missed (14); the explanation is the two binary-PDF parse
failures, not a coverage gap — the verified 14 already span every method family the brief asked for.

---

## 1. Executive synthesis

Ten durable lessons, each tied to ≥1 directly verified source and split by readiness.

### Build-now (fits the existing lifecycle without weakening any invariant)

1. **Textual-feedback evolution beats scalar-reward search for our card-shaped objects, and is far
   cheaper.** GEPA evolves *textual components* (prompts/cards) by reflecting on execution traces in
   natural language and keeping a **Pareto front** of per-instance winners, beating GRPO by up to 20%
   with **35× fewer rollouts** and MIPROv2 by >10% (GEPA, 2507.19457; DSPy docs). Our technique cards
   are exactly textual components and our behavioral evaluator already emits per-episode traces — this
   is the right optimizer shape for `run-gepa-real.py`, *provided* the feedback channel stays inside
   the broker (see lesson 8).

2. **Keep a Pareto front over episodes, not a single global best.** GEPA's central anti-local-optima
   move is to sample mutation parents proportionally from the set of candidates that win on *at least
   one* instance (GEPA; DSPy docs). Our `score-candidate.py` currently does pairwise incumbent-vs-one
   on aggregate coverage/cost. A per-episode Pareto record (still gated by the same eligibility vetoes)
   would diversify candidates without changing what "better" means.

3. **Mechanical, capability-verified success beats LLM-judge success.** AIRTBench scores a solve only
   when the agent submits the real flag, verified by the platform API — not by a judge reading the
   transcript (AIRTBench, 2506.14682). AgentDojo's targeted-ASR is likewise a programmatic check that
   the injected side-effect occurred (AgentDojo, 2406.13352). This is our two-layer oracle and broker
   model already: it is external, independent confirmation that the lesson is correct, and a reason to
   **resist** any future "let an LLM judge adjudicate coverage" shortcut.

4. **Variance is real and must be reported, not assumed away.** Refusal/safety decisions flip on
   **18–28% of prompts** across seed/temperature configs; single-shot agrees with a 5-seed ground
   truth only ~92–98% of the time; the authors recommend **N≥3 samples** for 95% reliability and
   reporting a stability metric alongside pass rates (Instability of Safety, 2512.12066). Our 3/3
   fresh-session replay floor (Decision 0002; `replay-candidate.py`) is *exactly* the right order of
   magnitude — this source is direct empirical backing for keeping it and for **recording cost/verdict
   variance** even though we don't yet gate on it.

5. **Cost is a first-class search axis, and "more rollouts" is the wrong default.** GEPA's headline is
   sample efficiency, not just accuracy (GEPA; DSPy budget controls: `auto`/`max_full_evals`/
   `max_metric_calls`). This validates Decision 0002's `cost = model_calls + target_calls`, equal
   weight, and the "equal coverage ⇒ needs ≥10% lower cost" rule in `score-candidate.py`. Adopt GEPA's
   explicit per-campaign metric-call budget as the canonical budget unit.

### Needs new evaluator / fixture before use

6. **Evaluator gaming is a measured, model-dependent threat — build it into the false-discovery
   corpus.** The Reward Hacking Benchmark catalogs six tool-agent exploit classes (metadata leakage,
   evaluator tampering / monkey-patching, sequence fabrication, parser/proxy gaming, overfitting
   visible checks, denial-of-evaluation) at rates **0% (Claude Sonnet 4.5) to 13.9% (DeepSeek-R1-Zero)**,
   rising with task-chain length and dropping ~88% under environment hardening (2605.02964). Our
   `fixtures/adversarial-candidates/` covers *manifest-level* gaming (mutate budget/scorer, duplicate
   coverage); it does **not** yet cover *researcher-runtime* gaming (a blind researcher fabricating an
   intermediate artifact or special-casing a visible episode). That is a new fixture family.

7. **Quality-diversity archives are the missing structure for "coverage," but only with a held axis.**
   Rainbow Teaming / RainbowPlus and the cross-generational Gemma study use **MAP-Elites** archives
   (3-D: strategy × encoding × harm-category) to fill behavioral niches and then **replay across
   targets** to measure transfer (Rainbow Teaming, 2402.16822; 2606.00813). For us the durable idea is
   *coverage as an archive of distinct oracle-confirmed niches*, not a scalar count — but the archive
   axes must be evaluator-owned (a candidate must not define its own niches, or it games coverage).

8. **Reflective feedback must be broker-derived, never researcher-narrated.** Every reflective system
   (GEPA's "actionable side information", GOAT's observe→think→strategy→respond loop, AgentFuzzer's
   ASR+coverage score, RedAgent's memory buffer) feeds the optimizer a *signal about what happened*
   (GEPA; GOAT 2410.01606; AgentFuzzer 2505.05849). Decision 0004's "measure effects, don't parse
   claims" means our GEPA feedback string must be assembled from **broker events** (probes run,
   controls fired, target responses, cost ledger), not from the researcher's self-report. This is a
   contract to add to the behavioral bridge before any reflective loop runs with a real proposer.

### Future review (do not build under current decisions; needs a new accepted policy)

9. **Self-modifying agents validate against a frozen benchmark and still need sandbox + human
   oversight.** The Darwin Gödel Machine self-edits and empirically validates each change on SWE-bench
   (20→50%) / Polyglot (14.2→30.7%) over 80 iterations, "with safety precautions (sandboxing, human
   oversight)" (2505.22954). The transferable caution: even the canonical self-improving agent keeps
   an *external* benchmark and a human in the loop. An autonomous campaign controller (post-Phase-14)
   may borrow the archive/open-ended-search shape, but **constitutional autonomy stays out of the loop**
   (Decision 0004) — the candidate never edits the benchmark it is judged on.

10. **Assume contamination; design the evaluator to resist it.** Contamination-resistant benchmark work
    recommends canaries, freshness (post-cutoff items), transformations, and sealed/holdout sets
    (2505.08389); the Gemma study and HarmBench-style practice add fixed judge + fixed seeds for
    reproducibility (2606.00813). This is the design spec for the *future* sealed-evaluator/holdout
    boundary on the ROADMAP — recorded here as a requirements source, not a build item.

---

## 2. Source table

| # | Title | Year | Link | Venue/status | Verified? | Method studied | Benchmark/evidence | Transfers | Doesn't transfer | Cheat/overfit risk | Conf. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | GEPA: Reflective Prompt Evolution Can Outperform RL | 2025 | arxiv.org/abs/2507.19457 | ICLR 2026 (Oral) | **Yes** | Reflective textual evolution + Pareto front | 4 tasks; vs GRPO/MIPROv2 (Qwen3-8B etc.) | Optimizer shape for technique cards; budget=metric-calls; Pareto-over-episodes | RL weight updates; their tasks are accuracy not security | Validation-set overfit if no held test (their own warning) | High |
| 2 | DSPy GEPA optimizer docs | 2025 | dspy.ai/api/optimizers/GEPA/overview | Official docs | **Yes** | GEPA config: feedback metric, train/val split, minibatch, budget | Reference impl | Concrete adapter contract; explicit train≠val warning | Tied to DSPy module model (Decision 0002 shelves DSPy) | "No valset ⇒ uses trainset" = built-in overfit footgun | High |
| 3 | AIRTBench | 2025 | arxiv.org/abs/2506.14682 | arXiv (Dreadnode) | **Yes** | Autonomous AI-red-team agent capability | 70 black-box CTF, flag-verified by API | Mechanical capability-verified oracle; ATLAS/OWASP tagging; repeatability gaps | Their targets are CTFs not app surfaces; needs their platform | Low — flag check is hard to game | High |
| 4 | AgentDojo | 2024 | arxiv.org/abs/2406.13352 | NeurIPS 2024 D&B | **Yes** | Indirect-PI benchmark for tool agents | 97 tasks, 629 security cases; Utility + targeted-ASR | Paired utility/ASR metric; programmatic side-effect check; defense slots | Their task envs; not our card model | Low — programmatic check | High |
| 5 | GOAT: Generative Offensive Agent Tester | 2024 | arxiv.org/abs/2410.01606 | ICML 2025 poster | **Yes** | Multi-turn attacker agent (observe/think/strategy/respond), 7 techniques | JailbreakBench; ASR@10 97%/88% | Reasoning-loop structure; composition-not-recitation; ≤5-turn bound | Produces jailbreak content (payload risk); judge-based ASR | Judge-based ASR inflates (see #9–11) | Med-High |
| 6 | AgentFuzzer / AgentVigil / AgentXploit | 2025 | arxiv.org/abs/2505.05849 | arXiv | **Yes** | Black-box fuzzing for indirect PI: seed corpus + MCTS/UCB1 + 5 mutators + ASR×coverage score | AgentDojo o3-mini 38→71%; VWA GPT-4o 36→70% | UCB1 seed selection; ASR+coverage reward; transfer test set | Seed corpus = payload zoo (must stay out); live-URL nav is Zone-2 | Coverage-bonus could be gamed if niche self-defined | Med-High |
| 7 | Rainbow Teaming | 2024 | arxiv.org/abs/2402.16822 | NeurIPS 2024 | **Yes** | MAP-Elites QD adversarial-prompt archive | >90% ASR; transferable | Coverage-as-archive; explicit diversity axes; BLEU dedup idea | Generates adversarial prompts (payload risk); judge-scored | Judge-scored fitness; axes-as-coverage gaming | Med-High |
| 8 | Reward Hacking Benchmark (tool-use agents) | 2026 | arxiv.org/abs/2605.02964 | arXiv | **Yes** | Taxonomy + measurement of evaluator gaming | 6 exploit classes; 0–13.9% across models; hardening −88% rel. | New FDR-trap family (runtime gaming); hardening = our broker isolation | Their tasks are coding/agent harnesses | This *is* the cheat-risk source | High |
| 9 | When Judgment Becomes Noise | 2025 | arxiv.org/abs/2509.20293 | arXiv | **Yes** | LLM-judge benchmark validity failures | 6.8–90.5% unexplained variance; factor collapse r>0.93; ELO masks noise | Why our oracle must be mechanical+adjudication, not single LLM judge | Studies judge benchmarks, not our oracle | N/A (argues against judge reliance) | High |
| 10 | A Coin Flip for Safety (LLM judges) | 2026 | arxiv.org/abs/2603.06594 | arXiv | **Yes** (abstract-level) | LLM judges unreliable for adversarial-robustness scoring | Inter-judge disagreement; ~chance reliability | Backs deterministic signal-oracle + multi-condition adjudication | Abstract-level only; numbers thin | N/A | Med |
| 11 | Instability of Safety (seeds & temperature) | 2025 | arxiv.org/abs/2512.12066 | arXiv | **Yes** | Refusal-decision variance across configs | 4 models, 876 prompts, 20 configs; 18–28% flips; N≥3⇒95% | Direct backing for 3/3 replay + report variance + low-temp | Studies refusal not coverage; transfer is by analogy | N/A | High |
| 12 | Darwin Gödel Machine | 2025 | arxiv.org/abs/2505.22954 | arXiv (Sakana) | **Yes** | Self-modifying agent + open-ended archive | SWE-bench 20→50%; Polyglot 14.2→30.7%; 80 iters | Archive/open-ended-search shape for a future controller | Self-edits code; needs sandbox+human; constitutional autonomy | High — must keep benchmark external to candidate | Med-High |
| 13 | Cross-Generational Transfer (MAP-Elites, Gemma) | 2026 | arxiv.org/abs/2606.00813 | arXiv | **Yes** | QD archive + multi-seed cross-version replay | 3 seeds (42/1337/2718), ChaCha8 RNG, fixed judge; non-monotonic ASR | Reproducible differential probing; fixed-seed+fixed-judge replay; transfer matrix | Generates jailbreaks (payload risk); model-version focus | Fixed judge still LLM (mitigated by determinism) | High |
| 14 | Towards Contamination-Resistant Benchmarks | 2025 | arxiv.org/abs/2505.08389 | arXiv | **Yes** | Canary/freshness/transform/sealed-holdout design | Detection via canary reproduction + transform gap | Spec for the future sealed-evaluator/holdout boundary | It's benchmark design, not an optimizer | N/A | Med-High |
| 15 | RedAgent | 2024 | arxiv.org/abs/2407.16667 | arXiv | **No** (snippet only) | Context-aware autonomous red-team agent, memory buffer, self-reflection | "jailbreaks most black-box LLMs within 5 queries" | Memory-buffer + reflection pattern (corroborates #5/#8) | PDF unparsed; numbers unverified; payload-producing | Memory could leak target secrets across runs | Low |
| 16 | Rethinking Jailbreak Evaluation | 2025 | aclanthology.org/2025.findings-emnlp.92 | EMNLP 2025 Findings | **No** (PDF unparsed) | Jailbreak-eval flaws | — | Corroborates #9–11 only; not load-bearing | unparsed | unknown | Low |
| 17 | RLVR can lead to Reward Hacking | 2026 | arxiv.org/abs/2604.15149 | arXiv | **No** (snippet only) | Verifier-gaming under RLVR | snippet: models overwrite tests/monkey-patch scorers | Corroborates #6 (verifier must be out of candidate's reach) | snippet only | This is the cheat pattern | Low |

---

## 3. Method extraction

For each useful method: search strategy · mutation unit · feedback signal · evaluator boundary ·
anti-cheat controls · cost model · replay/variance · failure modes · how it maps to our lifecycle.

### M1 — GEPA reflective Pareto evolution (sources 1,2)
- **Search:** evolutionary; sample a parent from the Pareto front (winners-per-instance), reflect on
  its traces, propose a mutation, evaluate on a minibatch, keep if it advances any frontier point.
- **Mutation unit:** one textual component (= one technique card) — matches Decision 0002's
  single-declared-component rule exactly.
- **Feedback:** scalar score **+** natural-language "actionable side information" derived from traces.
- **Evaluator boundary:** train set drives reflection; **separate val set** tracks Pareto scores; DSPy
  warns that omitting the valset silently reuses the trainset (built-in overfit footgun).
- **Anti-cheat:** none native — GEPA optimizes whatever the metric rewards. **The harness must own the
  metric and the held split.**
- **Cost:** explicit budget (`max_metric_calls`), the canonical unit; maps to `model_calls+target_calls`.
- **Replay/variance:** none native; we add it via `replay-candidate.py` (3/3).
- **Failure modes:** validation overfit; reward gaming if the metric is parseable by the researcher.
- **Maps to:** `run-gepa-real.py` proposer → preflight → materialize → behavioral eval → replay →
  bundle. The frontier and feedback-string assembly are the two new pieces.

### M2 — MAP-Elites quality-diversity archive (sources 7,13)
- **Search:** maintain a discrete archive over behavioral axes; each cell keeps the best solution;
  mutate-and-place to fill niches.
- **Mutation unit:** an attack/prompt (for us: a technique-card variant tagged to a niche).
- **Feedback:** fitness (ASR) + niche coordinates.
- **Evaluator boundary:** **axes must be evaluator-owned**; if a candidate defines its own niches it
  inflates "coverage."
- **Anti-cheat:** fixed judge + fixed seeds + deterministic RNG (2606.00813) → reproducible cells.
- **Cost:** archive size × evals/cell; bounded by campaign budget.
- **Replay/variance:** the Gemma study runs 3 seeds and reports mean±sd, then replays cross-target.
- **Failure modes:** coverage-gaming via self-defined axes; payload-zoo accumulation in cells.
- **Maps to:** a *future* "coverage = archive of oracle-confirmed niches" representation in the
  behavioral evaluator (needs-new-evaluator tier).

### M3 — Reasoning attacker loop (sources 5,6,15)
- **Search:** per-turn observe→reflect→pick-strategy→act (GOAT); or fuzz with MCTS/UCB1 seed
  selection + mutators (AgentFuzzer); or memory-buffer self-reflection (RedAgent).
- **Mutation unit:** the next probe / conversation move.
- **Feedback:** target response + (judge ASR | programmatic side-effect | ASR+coverage bonus).
- **Evaluator boundary:** weakest in GOAT (judge-scored); strongest in AgentFuzzer when the side-effect
  is programmatic.
- **Anti-cheat:** prefer programmatic success; cap turns (GOAT ≤5) to bound cost.
- **Cost:** queries; AgentFuzzer's UCB1 explicitly trades exploit vs explore to spend budget well.
- **Replay/variance:** none native.
- **Failure modes:** payload-zoo (the seed corpus *is* a payload library — must stay out of Plane 1);
  judge inflation; memory leaking target secrets across runs.
- **Maps to:** the loop shape echoes `engine/loop.md` (chain-don't-recite); UCB1 is the eventual UCB
  selection deferred in Decision 0002 / AGENTS.md §7 — adopt only once cross-engagement stats exist.

### M4 — Evaluator-gaming taxonomy + hardening (source 8, corroborated 17)
- **Search:** N/A (it's a measurement of the *threat*).
- **Unit:** an exploit attempt against the harness, not the target.
- **Feedback:** whether the score moved without the task being solved.
- **Evaluator boundary:** the whole point — environment hardening (boundary isolation, reduced file
  access) cut exploits ~88% relative without hurting task success.
- **Anti-cheat:** this *defines* our anti-cheat checklist (§6).
- **Cost:** measured via chained tasks (exploits jump at the first unverifiable step).
- **Failure modes:** the six classes; reasoning-trace analysis catches 72% (model often self-rationalizes).
- **Maps to:** new `fixtures/false-discovery/` *runtime-gaming* traps + a check that broker isolation
  (jailed subprocess, no repo access) is the realization of "environment hardening."

### M5 — Judge-reliability / variance discipline (sources 9,10,11)
- **Method:** quantify judge noise (unexplained variance, factor collapse, ELO masking) and decision
  instability across seeds/temperature; recommend mechanical checks + N≥3 + report stability.
- **Maps to:** validates two-layer oracle (mechanical signal-oracle first), 3/3 replay, low-temperature
  researcher (our ollama/claude bridges already pin temp 0 + seed), and "record variance" as advisory.

### M6 — Contamination-resistant / sealed evaluation (sources 13,14)
- **Method:** canaries, freshness, transformations, sealed holdout; fixed judge+seed for replay.
- **Maps to:** the future sealed-evaluator boundary; near-term, the casebook freshness rule (rotated
  cases not from the same lineage — already in Decision 0002).

---

## 4. Autoresearch implications (mapping to our machinery)

- **GEPA candidate generation:** keep single-component mutation (Decision 0002); add a **Pareto-over-
  episodes** record so parents are sampled from per-episode winners (M1) rather than aggregate best.
- **Mutation strategy:** seed = existing in-scope card (Phase 12 already does this); evolve via
  reflection on **broker-derived** feedback (M1/M3). Defer UCB1 seed selection (M3) until cross-
  engagement stats exist (AGENTS.md §7).
- **Campaign manifests:** record the canonical budget as `max_metric_calls`-equivalent
  (`model_calls+target_calls`) and pin a held evaluation split distinct from the reflection split (DSPy
  warning, source 2). Add `held_split_hash` to `frozen_inputs`.
- **Behavioral evaluator:** add a **broker-feedback contract** — the reflective string handed to the
  proposer is assembled from `events.jsonl` (probes/controls/responses/cost), never from the
  researcher's claims (Decision 0004; M1/M4). Keep the researcher blind and the broker authoritative.
- **False-discovery corpus:** add a **runtime-gaming** trap family from M4's six classes (esp.
  evaluator-tampering, sequence-fabrication, special-casing a visible episode, denial-of-evaluation).
  Acceptance stays `invalid_accept_rate = 0`.
- **Sealed/holdout evaluation:** future; spec = source 14 (canary/freshness/transform/sealed) + source
  13 (fixed judge+seed). Not built under current decisions.
- **Promotion bundles:** unchanged (PR-only). Add the held-split result and a variance line (cost +
  verdict spread across the 3 replays) as advisory evidence (source 11).
- **Casebook memory:** archive idea from M2 maps to scrubbed casebooks as a *niche library of
  confirmed/refuted shapes*, retrieval-only, never authoritative (matches the existing casebook-
  retrieval index firewall).
- **Tool-family generated proposals:** any fuzzer/seed-corpus (M3) is `payload_generator` class at
  most — proposal-only, default-disabled, sensor/oracle separation intact. A seed corpus is a governed
  dataset, never Plane-1 context.

---

## 5. Worked examples

### Example A — Pareto-over-episodes parent selection (from GEPA)
- **Paper/system idea:** GEPA samples mutation parents from the Pareto front of per-instance winners,
  avoiding the local optima of greedy "evolve the global best" (source 1).
- **Harness interpretation:** record, per candidate, which behavioral episodes it confirmed; sample the
  next mutation parent from cards that win on *some* episode, not just the highest aggregate coverage.
- **Candidate mutation:** one technique card (single declared component).
- **Evaluation gate:** unchanged `score-candidate.py` eligibility (conformance, FDR=0, no protected
  regression, evidence-contract complete, budget unchanged, single mutation).
- **Anti-cheat control:** the per-episode win record is **broker-owned**; the candidate cannot assert
  its own wins.
- **Acceptance metric:** equal-or-greater distinct oracle-confirmed coverage at ≤ budget, FDR=0,
  3/3 replay-stable.
- **Stop condition:** no new distinct niche confirmed for K consecutive frontier samples → archive.

### Example B — Runtime evaluator-gaming trap (from Reward Hacking Benchmark)
- **Paper claim:** tool agents game evaluators by tampering with scoring, fabricating intermediate
  artifacts, or special-casing visible checks at rates up to 13.9% (source 8).
- **Harness hypothesis:** a blind researcher in `run-behavioral-eval.py` might claim `confirmed` while
  the broker has no matching signal event, or "reproduce" a visible episode while failing a hidden
  sibling.
- **Probe shape (fixture, not live):** a synthetic candidate whose researcher emits a confirmed verdict
  with no broker signal event, plus one that passes a visible episode and fails its held twin.
- **Negative control:** an honest researcher on the same episodes must yield coverage only where broker
  events exist.
- **Oracle adjudication:** coverage counts **only** broker-evidenced confirmations (already the rule —
  this fixture proves it bites).
- **Persistent memory candidate if validated:** a `false-discovery` trap class
  `researcher-claim-without-broker-event` with correct verdict `refuted`/`needs_review`.

### Example C — Variance-aware replay reporting (from Instability of Safety)
- **Paper claim:** 18–28% of decisions flip across seeds/temperature; N≥3 needed for 95% reliability
  (source 11).
- **Harness hypothesis:** a candidate that "wins" on a primary run may be within replay noise.
- **Candidate mutation:** any technique-card variant.
- **Evaluation gate:** `replay-candidate.py` 3/3 with protected-case stability (existing).
- **Anti-cheat control:** replay is **downgrade-only** and non-authorizing (existing).
- **Acceptance metric:** allow only if stable across all 3; record cost/verdict spread.
- **Stop condition:** flips on any replay → downgrade to `probe`.

### Example D — Contamination-resistant held split (from sources 2,13,14)
- **System idea:** keep reflection data separate from the scored split; assume contamination; pin a
  fixed judge + fixed seeds (sources 2,13,14).
- **Harness interpretation:** campaign manifest pins `held_split_hash`; the proposer never sees the
  held episodes; replay uses the pinned seed.
- **Candidate mutation:** technique card.
- **Evaluation gate:** declared==actual materialization; behavioral eval on the held split only.
- **Anti-cheat control:** held split is in the immutable allowlist-exclusion set (candidate may never
  touch it); drift in `held_split_hash` blocks the PR (existing hash-pinning).
- **Acceptance metric:** improvement holds on the held split, FDR=0.
- **Stop condition:** held-split improvement absent → no promotion.

---

## 6. Anti-cheat checklist for future autoresearch campaigns

Synthesized from sources 1,2,8,9,11,13 + Decisions 0003/0004. Use verbatim as a campaign preflight.

- **What a candidate MAY mutate:** exactly one declared technique-card component. Nothing else.
- **What a candidate MUST NEVER see or touch:** the gold/episodes' hidden labels, the held evaluation
  split, the scorers, oracle, false-discovery corpus, casebook ground truth, budgets, conformance
  checks, sealed data. (DSPy's "no valset ⇒ reuse trainset" footgun, source 2, is forbidden — a held
  split is mandatory.)
- **What evidence is authoritative:** broker `events.jsonl` (probes, controls, target responses, cost
  ledger) and the mechanical signal-oracle + multi-condition adjudication-oracle. **Not** the
  researcher's narration, **not** an LLM judge's free-text verdict (sources 8,9,10).
- **How replay works:** primary + 2 fresh sessions, strict 3/3 on deterministic/hermetic evals, fixed
  seed, low temperature; downgrade-only; protected cases must hold in every replay (source 11).
- **How FDR blocks:** `invalid_accept_rate` on the false-discovery corpus must be `0` — a hard veto,
  never traded against coverage. Add the runtime-gaming trap family (source 8) before the first real
  reflective campaign.
- **How cost wins are validated:** cost = `model_calls + target_calls` from ledgers (not candidate-
  reported); equal coverage requires ≥10% lower cost; record cost variance across replays (source 11).
- **When human review is required:** every Plane-1 merge (PR-only); any change to evaluator/oracle/
  gold/budget/casebook (reviewed as an evaluator-change, incumbent re-run first); any scope expansion;
  any Zone-2 artifact. Self-improving-agent autonomy (source 12) stays behind a separate accepted
  policy.
- **The load-bearing invariant (Decisions 0003/0004):** a candidate can never change its evaluator and
  then use the changed evaluator to authorize itself. Materialize-then-measure; no final `allow` from
  parsed claims.

---

## 7. Top next builds (ranked)

Each: validation method + stop condition. All are small, fit the existing lifecycle, and add an
invariant or a deletion rather than a framework (Decision 0004 complexity budget).

1. **Broker-feedback contract for the GEPA bridge** (new evaluator contract). The reflective string is
   assembled from `events.jsonl`, never researcher text. *Validation:* a fixture where a researcher
   lies in its narration but the assembled feedback still reflects only broker events; parity test.
   *Stop:* if feedback cannot be assembled without researcher text, do not enable the reflective loop.
2. **Runtime evaluator-gaming false-discovery traps** (new fixture family, from source 8). *Validation:*
   `invalid_accept_rate` stays 0 with the new traps; an honest candidate is retained. *Stop:* any trap
   accepted as `confirmed` blocks autoresearch.
3. **Held evaluation split pinned in the campaign manifest** (`held_split_hash` in `frozen_inputs`,
   from sources 2,13,14). *Validation:* drift in the hash blocks the PR; proposer provably never reads
   held episodes. *Stop:* no held split ⇒ no "better" claim.
4. **Pareto-over-episodes parent selection** in `run-gepa-real.py` (from source 1). *Validation:*
   replay shows diversified candidates without FDR regression. *Stop:* if it raises FDR or duplicate
   coverage, revert to incumbent-vs-one.
5. **Variance line in the promotion bundle** (cost + verdict spread across the 3 replays, advisory,
   from source 11). *Validation:* bundle renders the spread; no gate change. *Stop:* purely advisory —
   never auto-blocks (Decision 0002 cost-variance = record-only).
6. **Canonical budget unit = metric-calls equivalent** (`model_calls+target_calls`) in the manifest
   (from sources 1,2). *Validation:* ledger matches manifest within tolerance. *Stop:* ledger/manifest
   mismatch blocks promotion (existing).
7. **Coverage-as-confirmed-niche archive** (future-tier, from source 2/M2), evaluator-owned axes only.
   *Validation:* axes are in the immutable set; a candidate cannot add a niche. *Stop:* if axes are
   candidate-writable, do not adopt — it would game coverage.
8. **UCB1 seed/probe selection** (from source 6) — **deferred** per AGENTS.md §7 until cross-engagement
   stats exist. *Validation:* offline replay vs ladder-and-winners on frozen casebooks. *Stop:* no
   measured gain over ladder ⇒ stay with ladder.
9. **MCTS-style multi-turn probe planning** as a technique-card variant (from sources 6, M3),
   chain-not-recite. *Validation:* hermetic episode shows higher distinct coverage at equal budget,
   FDR=0, 3/3. *Stop:* payload-zoo creep (a seed corpus appearing in Plane 1) ⇒ reject.
10. **Sealed-evaluator/holdout boundary** (future-tier, design spec from sources 13,14) — only after the
    canonical lifecycle is consolidated and behind a new accepted decision. *Validation:* one signed
    aggregate decision per candidate freeze; no per-probe leakage. *Stop:* any pre-freeze leakage of
    held data ⇒ do not ship.

---

## Top 3 harness-ingestable hypotheses (ranked by value × testability)

1. **H1 — "Reflective feedback assembled from broker events (not researcher claims) improves
   single-mutation candidates without raising FDR."** *Value:* unlocks the GEPA reflective loop that
   Decisions 0002/0004 point at, with the measure-don't-parse invariant intact. *Testability:* high —
   builds 1 + 2 above; provable on the existing canonical v2 campaign with a real proposer + a
   different researcher model (the Phase-13 setup already does cross-model). Sources 1,2,8,4.
2. **H2 — "A runtime evaluator-gaming trap family keeps `invalid_accept_rate = 0` against a
   researcher that fabricates confirmations or special-cases visible episodes."** *Value:* closes the
   gap between manifest-level and runtime gaming before any reflective campaign runs. *Testability:*
   high — pure fixture work, no live target, deterministic. Source 8 (corroborated 17).
3. **H3 — "A held evaluation split (distinct from the reflection split, hash-pinned) is necessary for a
   trustworthy 'better' claim; candidates that win only on the reflection split do not survive the
   held split."** *Value:* directly attacks the DSPy "reuse trainset" overfit footgun and the
   contamination risk. *Testability:* medium-high — needs a clean train/held partition of the
   behavioral episodes; provable by showing a known-overfit candidate passes reflection but fails held.
   Sources 2,13,14.

These three are the smallest set that lets the autoresearch loop learn (epistemic autonomy) while
provably keeping constitutional autonomy — what counts as true/better — outside the candidate loop.
