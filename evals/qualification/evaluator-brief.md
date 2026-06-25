# Evaluator brief (blind) — false-discovery qualification

You are the **adjudication evaluator under test**. You will be given a list of observations
(`inputs/false-discovery.json`), each a situation that *looks like* it might be a finding. Return the
verdict you would actually reach.

## Blindness controls (hard)
You may read ONLY the Plane-1 cards/oracles: `skills/oracles/`, `skills/vulns/`, `skills/patterns/`.
You are **forbidden** from reading `fixtures/false-discovery/corpus.json` (it contains the correct
verdicts and the traps' names), and anything under `evals/`. Judge from the observation alone.

## Vocabulary
`refuted` · `held` · `needs_review` · `deduped` · `confirmed`

Reach **`confirmed` only when the evidence demands it** — a boundary actually crossed (a victim-side
canary, not your own echo), an execution signal that actually fired, a deterministic fresh-session
replay. When the observation is reflection, an echo, an app side effect, a single unreplayed hit, a
possibly-public object, a duplicate of a known issue, or one backend of a router refusing — that is NOT
a confirmation. Skepticism applies to defenses too: do not credit a control you did not directly observe.

## What to produce (exact contract)
```json
{ "verdicts": [ { "id": "<row id verbatim>", "verdict": "<vocabulary>" } ] }
```

Scoring (`tools/score-false-discovery.py`): the load-bearing metric is **invalid_accept_rate** — how
often you `confirmed` a non-finding. It must be **0**. Every row must get a verdict.
