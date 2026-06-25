# ROADMAP

Guiding rule: **cut thin vertical slices**; a slice is "done" only when the benign loop *closes*
(control captured · technique walked · contamination ruled out · replay · finding emitted). Rigor is
the product — see `docs/architecture.md` §Prime directive.

## Phase 0 — scaffold ✅ (2026-06-19)
Repo skeleton, 3 planes, schemas, two-layer oracle, ladder loop, LLM07 card + 3 technique cards,
engagement `_TEMPLATE`, sanitized calibration fixture.

## Phase 1 — first vertical slice: LLM07 (in progress)
- [ ] Review pass on the heart (`CLAUDE.md`, `llm07` card, both oracles).
- [ ] First live engagement: LLM07 vs Adapta, end-to-end through the harness — negative control,
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
- [x] **Cost/budget accounting** — `run_cost` on findings; `tools/run-hermetic-bola.py` emits a per-run
      target-call/budget ledger so "equal coverage at ≥10% lower cost" becomes measurable.
- [x] **Adversarial candidate corpus (prepared, not launched)** — `fixtures/adversarial-candidates/`:
      candidates that mutate budget / mutate the scorer / duplicate coverage / omit controls / overfit
      visible cases, plus one valid additive candidate that must be retained. This is the Phase-3 gate
      fixture, staged now.
- [ ] **Phase 2.5B — hermetic benchmark.** Started with the **no-model BOLA legacy-route** target
      (`evals/hermetic/targets/bola-legacy-route/`, pure HTTP/status/body differential, deterministic,
      no LLM). Next: a **canned/fake-model** harness for LLM05 / LLM07 / model-router / LLM06
      (recorded deterministic outputs only — a real LLM drifts and cannot anchor a frozen benchmark).

## Phase 2 — breadth (second slice + harvest)
- [ ] LLM01 prompt-injection card live (indirect, inert canary in an ingested surface).
- [ ] LLM02 sensitive-info, LLM05 improper-output-handling, LLM06 excessive-agency cards.
- [ ] Harvest prior engagement learnings into technique "winning variants" (abstract, scrubbed).
- [ ] MITRE ATLAS cross-walk on each card.

## Phase 3 — autoresearch (BLOCKED until the Phase-2.5 gates pass)
- [ ] **Claudini keep-if-better ratchet**: propose technique variant → run on frozen slice → keep
      only if it beats the incumbent on **gated `clean_confirmed_coverage`** (distinct benchmark cases
      passing the full adjudication oracle within a fixed budget — NOT raw confirmed-finding rate, which
      rewards evaluator-gaming; see `autoresearch-evaluation-rfc.html` §03).
- [ ] **Anti-cheat gate** (rated more important): immutable evaluator per campaign · isolated
      experiments · hidden/rotating holdouts · replay-before-accept · revert-on-regression · no
      shared memory that turns evaluator quirks into strategy folklore.
- **FDR is a hard veto, not a tradeoff term:** a candidate that raises coverage AND raises
  false-discovery rate is rejected — coverage and FDR are not fungible.
- **Scope fence:** autoresearch mutates **technique-card variants only** — never the evaluator, oracle,
  casebook ground truth, budget, or sealed holdout data.

### Launch preconditions (all must hold before the first ratchet run)
1. False-discovery corpus: **zero invalid accepts** (`fixtures/false-discovery/`).
2. Adversarial candidate corpus: **100% valid-candidate retention + 100% bad-candidate block**
   (`fixtures/adversarial-candidates/`).
3. Cost/budget accounting exists and is recorded per run (`run_cost` + hermetic ledger).
4. Routing scorer is mechanical and frozen-gold-backed (`tools/score-routing.py`).
5. A hermetic benchmark exists (`evals/hermetic/`), no-model BOLA target landed, fake-model harness for
   the model-dependent cards in place.

## Phase 4 — scale (only when a concrete wall appears)
- [ ] Pack mode / multi-account concurrency (config knob 1→N), gated on `scope.md`.
- [ ] UCB selection — once cross-engagement stats are worth optimizing over.
- [ ] Optional native `.claude/skills/` mirror; optional report skill (decoupled finding-schema consumer).

## Stubs to grow (need gray-box / infra)
LLM03 supply-chain · LLM04 poisoning · LLM08 embeddings · LLM09 misinformation · LLM10 unbounded.

## Explicitly NOT on the roadmap (scope fence ✗)
Real-harm uplift as product · a working-jailbreak library · HarmBench-style harm metrics ·
wholesale ingestion of harm corpora.
