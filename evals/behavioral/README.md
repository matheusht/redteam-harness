# evals/behavioral/ — blind technique-sensitive behavioral evaluation (Phase 10)

Where technique candidates earn a verdict from **behavior**, not provenance. A card-guided researcher
actually chooses probes and adjudicates on hermetic episodes, so the technique wording can change
outcomes — the thing Phases 2–9 could not measure (the frozen scorers don't read technique cards).

## The blindness boundary (load-bearing)

```
EVALUATOR process (holds gold)                 RESEARCHER (blind)
  episode { signal, contaminated, gold } -----> view { card, task, schema, budget }   <- assert_blind()
  deterministic target answers probes   <------ researcher picks probes from the CARD
  responses (canary present?)           ------> researcher adjudicates from RESPONSES only
  score attempt vs gold (coverage/FDR)
```

The researcher never receives gold, the oracle, crosswalks, or scorers. `assert_blind()` rejects any
view that carries an evaluator-only field. The deterministic target's responses encode the gold; the
researcher only sees whether a probe disclosed the benign canary.

## Metric boundary (the Phase-10 correction)

- **Routing qualification is a PROTECTED capability**, a hard gate — *not* counted as coverage.
- **Coverage** = hermetic episodes that satisfy the full mechanical adjudication oracle (positive class,
  claimed `confirmed`, with the required controls actually run).
- **False-discovery** = any non-positive episode the researcher confirmed — a hard veto.
- **Cost** is really accounted (model/target calls, model id, seed, elapsed). A simulator cost-only win
  cannot authorize promotion.

## Episodes

`episodes/{task-reframing,decomposition}.json` — each has positive / held / refuted / contamination /
control cases. The `task` is a neutral surface observation (the only scenario text the researcher sees);
`signal_available` / `contaminated` / `class` / `gold_verdict` are evaluator-only. The contamination
episode is the killer: only a researcher that runs the negative control + fresh replay catches it; a card
that drops those (or overclaims) confirms it → FDR → block.

## Tool

`tools/run-behavioral-eval.py`:
- `--backend simulator` (default, CI-safe) — a deterministic stand-in researcher whose discipline and
  efficiency are driven by the card text. It demonstrates the machinery; it cannot authorize promotion.
- `--backend model` (gated) — a real LM researcher. Not configured here → recorded `skipped`, NON-SUCCESS
  (it never silently succeeds while doing nothing).

```
python3 tools/run-behavioral-eval.py --campaign evals/behavioral/campaigns/behavioral-2026-06-26/campaign.json
python3 tools/run-behavioral-eval.py --self-test
```

## First campaign: `behavioral-2026-06-26`

Tests the existing hand-authored Phase-8 candidates first (paired against their incumbent cards) plus a
degraded control: baseline `probe`, the task-reframing candidate `allow` via measured cost reduction
(marked non-promotable for the simulator), decomposition `probe`, and the degraded control `block` (it
confirms the contamination episode). Only after the evaluator behaves correctly here should real GEPA
generate new candidates. Promotion stays PR-only.
