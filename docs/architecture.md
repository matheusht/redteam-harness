# Architecture (v1.1 summary)

Full brainstorm + decision history: `harness-merged-architecture-v1.html` (kept with the originating
engagement wiki). This is the standalone summary.

## Three planes (don't let them bleed)
- **Plane 1 — methodology** (`skills/`): vuln × technique × oracle cards. Read-only, target-agnostic,
  never edited mid-engagement. Travels.
- **Plane 2 — orchestration** (`engine/`): loop · roster · gates. Stateless re target, stateful re run.
- **Plane 3 — engagement** (`engagements/_TEMPLATE/` → copied into the target's own repo): scope,
  progress, findings, evidence, memory, cleanup. Append-only. Born per engagement.

**Rule:** Plane 1 read-only knowledge, Plane 3 write-only memory.

## Load-bearing decisions
1. **Composable two axes** — vuln (`what`) × technique (`how`), judged by oracles. Coverage is
   multiplicative. (Convergent with PyRIT converter / garak probe / promptfoo strategy.)
2. **Skills-as-modules, portable + deterministic** — plain `SKILL.md`, orchestrator loads the exact
   card by id. Engine-agnostic; native `.claude/skills/` mirror optional later. (See CLAUDE.md §3.)
3. **`safe_signal` is a load-gate** — a vuln card without a benign win-condition won't load. The
   scope fence made structural.
4. **Three record types** — `attempt` (many) → `finding` (few) → `pattern` (very few). Prevents one
   run becoming a "finding".
5. **Two-layer oracle, built before the loop** — signal (did it happen) → adjudication (does it prove
   a boundary failed); default-skeptical verdicts; mandatory neg+pos controls + replay + contamination
   ruleout.
6. **Ladder + winners loop, coverage-stop** (no UCB until cross-engagement stats exist). Refusal is
   an input to the next rung; terminal verdict is coverage/dry, never "model complied".
7. **Single agent first**; parallelism is a config knob gated on scope.
8. **Three-zone scope fence** — benign default · authorized human-confirmed impact-escalation · never.

## Prime directive
Rigor is the product. Default to disbelief; disprove before believing; be more conservative than the
operator's intuition.

## Deferred to Phase 2
Autoresearch keep-if-better ratchet + anti-cheat gate (immutable evaluator, holdouts,
replay-before-accept) riding a frozen eval slice; UCB; pack/multi-account concurrency.

## Provenance
Merged from: the engineer's plan (structural base), a research-convergence brainstorm, a
governance/evaluation deep-review (records, oracle layers, controls, contamination, anti-reward-
hacking), and an autoresearch curation (Claudini ratchet + anti-cheat gate; skip the rest).
