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

## Phase 2 — breadth (second slice + harvest)
- [ ] LLM01 prompt-injection card live (indirect, inert canary in an ingested surface).
- [ ] LLM02 sensitive-info, LLM05 improper-output-handling, LLM06 excessive-agency cards.
- [ ] Harvest prior engagement learnings into technique "winning variants" (abstract, scrubbed).
- [ ] MITRE ATLAS cross-walk on each card.

## Phase 3 — autoresearch (only once a frozen eval slice exists)
- [ ] **Claudini keep-if-better ratchet**: propose technique variant → run on frozen slice → keep
      only if it beats the incumbent's confirmed-finding rate.
- [ ] **Anti-cheat gate** (rated more important): immutable evaluator per campaign · isolated
      experiments · hidden/rotating holdouts · replay-before-accept · revert-on-regression · no
      shared memory that turns evaluator quirks into strategy folklore.

## Phase 4 — scale (only when a concrete wall appears)
- [ ] Pack mode / multi-account concurrency (config knob 1→N), gated on `scope.md`.
- [ ] UCB selection — once cross-engagement stats are worth optimizing over.
- [ ] Optional native `.claude/skills/` mirror; optional report skill (decoupled finding-schema consumer).

## Stubs to grow (need gray-box / infra)
LLM03 supply-chain · LLM04 poisoning · LLM08 embeddings · LLM09 misinformation · LLM10 unbounded.

## Explicitly NOT on the roadmap (scope fence ✗)
Real-harm uplift as product · a working-jailbreak library · HarmBench-style harm metrics ·
wholesale ingestion of harm corpora.
