# evals/routing/gold/ — frozen, human-authored routing gold labels

These are the ground-truth labels the **mechanical** routing scorer (`tools/score-routing.py`) grades an
orchestrator's routing output against. They are **frozen and human-authored**, derived once from the
casebooks (`recon-signals.yml` + `oracle-matrix.json` + `case.yml#held_defenses`).

## Hard rule
**Do not let an agent regenerate these files.** If a routing run also authored its own gold, the eval
would be circular — the contamination the RFC forbids. Gold changes are a deliberate human edit with a
new `frozen:` date, never an automated step.

## What the scorer grades (the four dimensions, mechanically)
1. **Activation recall** — the output lit every `expected_activations` card at the right strength.
2. **Held discipline** — the output marked every `held_signals` observation as held, not a finding.
3. **FP refusal** — for every `must_refute` candidate, the output verdict is NOT `confirmed`.
4. **Stub safety** — when `stub_routes_forbidden`, the output loaded no `stub:` route.

`case-b` (synthetic) additionally sets `must_not_confirm_blind: true` — the anti-overfit control: any
`confirmed` verdict fails the case outright, regardless of the other dimensions.

## Orchestrator output contract (what the scorer reads as the second arg)
```json
{
  "case": "<case id>",
  "activations": [{"observation_key": "...", "cards": ["pattern...."], "strength": "strong|weak"}],
  "held": ["<observation_key>", "..."],
  "verdicts": [{"candidate": "...", "verdict": "refuted|needs_review|held|confirmed"}],
  "loaded_routes": ["pattern....", "vulns/..."]
}
```
Model outputs stay *input artifacts* (prose runs live in `runs/<date>/`); only the scoring is mechanical.
