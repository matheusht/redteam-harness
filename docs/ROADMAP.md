# ROADMAP

Guiding rule: **cut thin vertical slices**; a slice is "done" only when the benign loop *closes*
(control captured · technique walked · contamination ruled out · replay · finding emitted). Rigor is
the product — see `docs/architecture.md` §Prime directive.

## Phase 0 — scaffold ✅ (2026-06-19)
Repo skeleton, 3 planes, schemas, two-layer oracle, ladder loop, LLM07 card + 3 technique cards,
engagement `_TEMPLATE`, sanitized calibration fixture.

## Phase 1 — first vertical slice: LLM07 (in progress)
- [ ] Review pass on the heart (`CLAUDE.md`, `llm07` card, both oracles).
- [ ] First live engagement: LLM07 vs a signed live target, end-to-end through the harness — negative control,
      ladder, two-layer adjudication, contamination ruleout, fresh-session replay, records emitted.
- [ ] Capture the engagement's `winners.md` (abstract) + observed defenses (`loses_to`).
- **Exit criterion:** the loop closes once, with a properly-adjudicated verdict (even "guard holds"
      is a valid, well-evidenced result).

## Phase 1.5 — routing layer + casebooks ✅ (2026-06-23)
- [x] First-class `skills/patterns/` cards with `activation` (strong/weak/negative) + `routes_to`:
      `client-supplied-selector-authz`, `legacy-route-differential`, `ui-only-policy-enforcement`,
      `transitive-sanitizer-reliance`.
- [x] `casebooks/` — scrubbed engagement memory; `_SCHEMA/` + two cases: `case-2026-06-b2b-agentic-chat`
      (real, sanitized) + `synthetic-negative-controls` (all held/refuted — the anti-overfit control).
- [x] `engine/routing.md` — recon emits activation signals before card selection; `recon-signals.md` +
      `pattern-candidates.md` in the engagement template; `fixtures/routing-activation.fixtures.md`.
- [x] First-class web/API authz vuln cards the patterns route to: `vulns/broken-object-level-authz` +
      `vulns/injection` (benign-canary objectives, scope-gated, controls + replay). `activation` block
      added to `vulns/llm07-system-prompt-leakage`.
- [x] `vulns/llm06-excessive-agency` — built to close the coverage gap the shadow eval surfaced
      (ui-only-policy activations were routing through BOLA for lack of a capability-bypass objective).
      `ui-only-policy-enforcement` + `client-supplied-selector-authz` now route to it un-stubbed.
- [x] **Phase 2.5A (baby):** `tools/check-conformance.py` (stdlib-only) + `engine/routing-eval.md` +
      a first **shadow eval run** (`evals/routing/runs/2026-06-23/`, both cases PASS) — static + first
      model-in-the-loop layer green (67 checks).
- [x] `vulns/llm05-improper-output-handling` — built; `transitive-sanitizer-reliance` un-stubbed.
      **No `stub:` routes remain** — every pattern card now routes only to cards that exist.
- [x] Mechanical activation matcher: `tools/score-routing.py` + frozen human-authored gold
      (`evals/routing/gold/`) — deterministic set-compare on the four dimensions, self-test reproduces
      the 2026-06-23 operator PASS. Model outputs stay input artifacts; only scoring is mechanical.

## Phase 2.5 — evaluator foundation (in progress, 2026-06-25)
"Build the evaluator before you optimize." Harden the inputs autoresearch will eventually be scored
against, using the traps THIS harness met live (replay run `b2b-2026-06-replay`: F2 re-confirmed,
LLM07 prompt-leak new, LLM05 render refuted). **No self-improvement loop until these land.**
- [x] **Evidence contract** — `schemas/finding.schema.json` carries a structured `evidence_contract`
      (negative/positive control, replay determinism, contamination ruleout, one-line justification,
      run-cost ledger, evidence refs). `tools/check-conformance.py` gates it: **new** findings
      (recorded ≥ 2026-06-25) require the contract; back-catalog is **advisory**. Green means
      "evidence contract *present*" — necessary, NOT sufficient; the model oracle still adjudicates truth.
- [x] **False-discovery corpus** — `fixtures/false-discovery/` encodes the live traps (echoed canary,
      public-share-as-IDOR, inert-reflection-as-XSS, title-rename-as-execution, phantom CSP, missing
      replay, duplicate-surface-as-coverage, one-backend-refusal-as-hold). Acceptance: **invalid-accept
      rate = 0** (no trap's correct verdict is `confirmed`); the checker asserts it.
- [x] **Mechanical routing scorer** — see Phase 1.5 (frozen gold + `tools/score-routing.py`).
- [x] **Model-in-the-loop qualification (slice 2)** — `evals/qualification/` + `tools/run-qualification.py`:
      a blind orchestrator/evaluator driver that feeds real subagent outputs through the frozen scorers
      and emits a single QUALIFIED/BLOCKED verdict (QUALIFIED ⇒ all routing dims PASS AND invalid-accept
      rate 0). Adapter + contract + briefs + crosswalk + self-test landed; CI runs the self-test.
      **Live blind runs captured** (`runs/2026-06-25{,b,c}/`): run 1 BLOCKED → three **card** clarifications
      (render presence = weak; legacy↔selector co-activation; selector activation-vs-adjudication) →
      run c **QUALIFIED** (both routing cases PASS, evaluator 0/8 invalid accepts). **Gold never edited** —
      every fix was a generalizable Plane-1 card clarification surfaced by a blind run.
- [x] **Rotation case** (`casebooks/rotation-case-01-web-api/`, `runs/2026-06-25-rotation01/`): a fresh
      web/API surface (billing/profile; seeded from sanitized web archetypes, csivitu/ctf-challenges MIT,
      nothing vendored), routed blind by a **Sonnet** router → **QUALIFIED**. Generalized the same two
      cards to a new surface, recognized held siblings, refused an escaped render, and honestly flagged an
      **SSRF coverage gap** (new `coverage_honesty` scorer dimension) instead of force-fitting a card.
      Routing now qualified on TWO surfaces. **Open coverage gap:** no SSRF pattern card (candidate next).
- [x] **Cost/budget accounting** — `run_cost` on findings; `tools/run-hermetic-bola.py` emits a per-run
      target-call/budget ledger so "equal coverage at ≥10% lower cost" becomes measurable.
- [x] **Adversarial candidate corpus (prepared, not launched)** — `fixtures/adversarial-candidates/`:
      candidates that mutate budget / mutate the scorer / duplicate coverage / omit controls / overfit
      visible cases, plus one valid additive candidate that must be retained. This is the Phase-3 gate
      fixture, staged now.
- [x] **Phase 2.5B — hermetic benchmark.** Started with the **no-model BOLA legacy-route** target
      (`evals/hermetic/targets/bola-legacy-route/`, pure HTTP/status/body differential, deterministic,
      no LLM), then added the canned/fake-model harness for LLM05 / LLM07 / model-router / LLM06
      (`tools/run-hermetic-fakemodel.py`). Recorded deterministic outputs anchor the frozen benchmark.

## Phase 2 — breadth (second slice + harvest)
- [ ] LLM01 prompt-injection card live (indirect, inert canary in an ingested surface).
- [x] LLM05 improper-output-handling + LLM06 excessive-agency cards (first-class vuln cards).
- [ ] LLM02 sensitive-info card.
- [ ] Harvest prior engagement learnings into technique "winning variants" (abstract, scrubbed).
- [ ] MITRE ATLAS cross-walk on each card.

## Phase 3A — GEPA shadow autoresearch (active in shadow; no automatic promotion)
- [x] **Campaign/candidate contracts**: add campaign manifest, candidate manifest, promotion bundle,
      and hash checks for mutable allowlist, evaluator/scorer/gold/casebook hashes, model settings,
      budgets, lineage, and protected cases. Candidate artifacts are JSON manifest + Markdown evidence
      bundle + diff.
- [x] **Standalone GEPA adapter first (Phase 8)**: `tools/run-gepa-real.py` now provides a narrow
      standalone adapter surface: `--backend gepa` uses GEPA `optimize_anything` when installed/configured,
      `--backend deterministic` is the CI-safe control, and `--backend auto` falls back honestly.
      DSPy remains shelved unless a bounded spike later proves value.
- [x] **Multi-track, single-mutation campaign**: first shadow campaign may cover `task-reframing`,
      `decomposition`, and one new technique-card candidate, but each candidate mutates exactly one
      declared component.
- [x] **Keep-if-better ratchet, shadow only**: propose technique variant → run on frozen slice → keep
      only if it beats the incumbent on **gated `clean_confirmed_coverage`** or equal coverage with at
      least 10% lower cost. Output is an evidence bundle, not a Plane-1 edit.
- [x] **Replay and promotion bundle**: primary run + two fresh-session replays, protected-case
      regression check, false-discovery scorer, cost comparison, redaction report, and PR-only human
      review before any promotion.
- [x] **Benchmark expansion before real ratchet (Phase 6)**: fake-model hermetic targets for LLM05 /
      LLM07 / LLM06 / model-router landed (`evals/hermetic/targets/`, `tools/run-hermetic-fakemodel.py`),
      wired into the shadow runner's frozen evaluator. SSRF decided: `pattern.ssrf-server-side-fetch`
      added (scoped pattern, review/held posture). Second rotation `rotation-case-02-agentic-tooluse`
      QUALIFIED — routing now qualified on three surfaces.
- [x] **Indirect prompt injection gap closed:** scoped `pattern.indirect-prompt-injection` card added;
      `transitive-sanitizer-reliance` explicitly points prompt-channel injection out of scope. rotation-02
      remains frozen as the historical pre-card gap record.
- [x] **Phase 8 adapter campaign:** `gepa-phase8-2026-06-26` freezes the broad evaluator, generates
      three scoped candidate deltas + a no-op baseline + an invalid gold-touch control, runs gate →
      scorer → replay → promotion bundle, and promotes nothing. Local run used deterministic backend
      because GEPA is not installed/configured in this environment; `--backend gepa` is wired for the
      standalone `optimize_anything` API.
- [x] **Phase 9 — candidate-applied evaluation (`tools/apply-candidate-eval.py`).** Each gate-passing
      candidate's diff is now **applied in an isolated `git worktree` at HEAD** (the live tree is asserted
      byte-identical), conformance is re-run against the patched workspace, and the measured result feeds
      the keep/discard policy. A variant that breaks the harness blocks by measurement; a clean variant is
      `probe` (frozen scorers don't read technique cards, so no behavioral delta without a model). On the
      Phase-8 campaign: 4 applied clean (probe), 1 gold-touch blocked, 0 promoted.
- [x] **Phase 10 — blind technique-sensitive behavioral evaluation (`tools/run-behavioral-eval.py`).**
      A card-guided researcher chooses probes and adjudicates on hermetic episodes (positive / held /
      refuted / contamination / control), blind to gold (`assert_blind`); incumbent vs candidate are paired
      on identical episodes/budget/seed. Routing is a protected capability (not coverage); coverage =
      oracle-confirmed episodes; FDR is a hard veto; cost is really accounted. First campaign
      `behavioral-canonical-v2-2026-06-27`: baseline probe, efficiency candidate allow-by-cost (non-promotable for the
      simulator), decomposition probe, degraded control block. A degraded card blocks via contamination FDR.
- [x] **Phase 10F — behavioral provenance/gating/replay hardening.** Evaluator-side **broker**
      authoritative for probes/controls/replay/responses/evidence/cost (model claims can't prove actions);
      canonical campaign/candidate gate + isolated apply + **measured** patched-workspace conformance (no
      hardcoded eligibility); paired incumbent/candidate over primary + two fresh sessions with anonymized
      A/B + strict 3/3; **immutable** hash-pinned `runs/<run-id>/` artifacts (no overwrite); capability
      blindness for the model adapter (jailed subprocess). Canonical campaign `behavioral-canonical-v2-2026-06-27`:
      no-op probe, efficiency allow-by-cost (non-promotable), decomposition probe, degraded block, immutable-touch
      blocked at the gate.
- [x] **Phase 10G — provider-neutral researcher adapter + fake adapter.** Strict action/final schemas,
      bounded malformed-output retries, jailed subprocess, usage accounting, honest `ModelUnavailable`
      non-success; deterministic fake CLI tests the wire protocol in CI. **Real-model qualification run is
      BLOCKED** (no isolated LM backend); simulator success is never substituted. Autonomy envelope recorded
      in Decision 0003.
- [ ] **Next — consolidation proof: authoritative apply-then-measure boundary.** Keep
      `check-campaign` as a fast manifest/hash preflight, but make isolated worktree application plus the
      actual changed tree the authority for `declared == actual`, mutable-allowlist membership, and
      byte-empty baselines. No final candidate `allow` before materialization. This is the first concrete
      application of Decision 0004's “measure effects, do not parse claims” rule; delete patch-format
      special cases only after parity/adversarial tests prove the measured contract is faithful.
- [ ] **Real-LM behavioral qualification.** Configure a sufficiently isolated LM backend
      (`--backend model --model-cmd ...`) and capture one blind, paired, 3/3 qualification (incumbent →
      no-op → degraded → task-reframing → decomposition). Only after it passes may real GEPA generate
      novel candidates; simulator results remain plumbing evidence, not autonomous learning.
- [ ] **Lifecycle consolidation checkpoint — before the autonomous controller.** Establish one
      canonical public experiment flow (`preflight → apply → measure → score → replay → record`), one
      run-status/artifact contract, and mark existing lifecycle entrypoints internal or historical.
      Compose tested functions incrementally; do not introduce a new framework or role-class hierarchy.
- [ ] **Then: sealed evaluator → first real GEPA campaign → autonomous campaign controller.** The
      controller may schedule, replay, reject, archive, and create evidence PRs inside the autonomy
      envelope (Decision 0004, absorbing 0003). Live bounded operation and automatic promotion remain
      separate review decisions.
- **Learning north-star (Decision 0004):** `autonomous_gap_closure_count = 0`. Increment only
  when the system discovers and closes a previously uncovered behavior without a human authoring the
  case or candidate, while preserving FDR=0, protected cases, replay, and evaluator immutability.
- **FDR is a hard veto, not a tradeoff term:** a candidate that raises coverage AND raises
  false-discovery rate is rejected — coverage and FDR are not fungible.
- **Scope fence:** autoresearch mutates **technique-card variants only** — never the evaluator, oracle,
  casebook ground truth, budget, or sealed holdout data.
- **Promotion path:** GEPA candidate → isolated branch → scorers/replay → promotion bundle → human
  review → PR merge. No direct-to-main and no manual copy into `skills/techniques/`.

### Launch preconditions (all must hold before the first ratchet run)
1. False-discovery corpus: **zero invalid accepts** (`fixtures/false-discovery/`).
2. Adversarial candidate corpus: **100% valid-candidate retention + 100% bad-candidate block**
   (`fixtures/adversarial-candidates/`).
3. Cost/budget accounting exists and is recorded per run (`run_cost` + hermetic ledger).
4. Routing scorer is mechanical and frozen-gold-backed (`tools/score-routing.py`).
5. A hermetic benchmark exists (`evals/hermetic/`), no-model BOLA target landed, fake-model harness for
   the model-dependent cards in place.

## Phase 3B+ — review-required capability expansion
- [ ] **Live GEPA advisory mode**: GEPA reads scrubbed live traces and suggests next probes; human
      approval required before execution. Bounded/autonomous live modes require a separate review.
- [ ] **Evaluator co-evolution**: GEPA may eventually propose oracle/scorer/gold/casebook changes only
      behind a sealed meta-evaluator, protected historical cases, zero invalid accepts, and explicit PR
      review.
- [ ] **Autonomous PoC ladder**: Level 0 evidence explanation → Level 1 benign canary proof → Level 2
      local hermetic PoC → Level 3 scoped live PoC with human confirmation → Level 4 autonomous exploit
      chaining (separate review).
- [x] **DSPy spike (Phase 7) — done, SHELVED.** Built an isolated routing-output normalizer
      (`experiments/dspy-routing-normalizer/`): a deterministic stdlib baseline (5/5 on the observed
      messy-output failure modes, CI-tested) + an optional guarded DSPy module. DSPy showed no gain over
      the deterministic baseline on these cases, so it stays parked, not adopted; revisit only on
      pure-prose outputs, evaluator-adjudication normalization, or once several stable LM programs exist.
      No full DSPy rewrite.

## Phase 4 — scale (only when a concrete wall appears)
- [ ] Pack mode / multi-account concurrency (config knob 1→N), gated on `scope.md`.
- [ ] UCB selection — once cross-engagement stats are worth optimizing over.
- [ ] Optional native `.claude/skills/` mirror; optional report skill (decoupled finding-schema consumer).

## Stubs to grow (need gray-box / infra)
LLM03 supply-chain · LLM04 poisoning · LLM08 embeddings · LLM09 misinformation · LLM10 unbounded.

## Explicitly NOT on the roadmap (scope fence ✗)
Real-harm uplift as product · a working-jailbreak library · HarmBench-style harm metrics ·
wholesale ingestion of harm corpora.
