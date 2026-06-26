# Orchestrator brief (blind) — routing qualification

You are the **routing orchestrator under test**. You will be given a list of raw recon observations
(`inputs/routing-case-*.json`). Derive the routing for each. You are scored mechanically against a
frozen gold you never see.

## Blindness controls (hard)
You may read ONLY the Plane-1 cards and engine docs:
`skills/patterns/`, `skills/vulns/`, `skills/oracles/`, `engine/routing.md`.
You are **forbidden** from reading: `casebooks/`, `fixtures/`, `evals/` (gold, crosswalk, examples, any
prior run). Those carry the answers. If you have already seen them, say so — the run is contaminated.

## What to produce (exact contract)
```json
{
  "case": "<the case id from the input>",
  "rows": [
    {
      "id": "<row id verbatim>",
      "cards": ["pattern.<id>", "..."],
      "strength": "strong | weak | negative",
      "held": true | false,
      "default_verdict": "refuted | needs_review | held | null",
      "coverage_gap": true | false
    }
  ],
  "loaded_routes": ["pattern.<id>", "vulns/<dir>", "..."]
}
```
Rules:
- `coverage_gap` — set `true` (and leave `cards` empty) when the observation is a vulnerability shape
  that NO pattern card models. Do NOT force-fit a card; flagging the gap honestly is the correct answer.
- `cards` — every pattern card the observation activates (use the exact `id:` from the card front-matter).
- `strength` — `negative` means a held defense tell, not a finding.
- `held` — `true` when the observation is a correctly-enforced defense (the held counterexample).
- `default_verdict` — ONLY for reflection/echo/render rows: the verdict you would assign **without**
  an execution/canary proof. For a markdown/diagram render row that is `refuted` (reflection ≠ execution).
  `null` for everything else.
- `loaded_routes` — the routes you would actually load. **Never** load a `stub:` route as a real card.

Return the JSON only. The runner (`tools/run-qualification.py`) translates row ids to the gold via the
crosswalk and scores activation recall, held discipline, FP refusal, and stub safety.
