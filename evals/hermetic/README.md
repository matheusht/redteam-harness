# evals/hermetic/ — hermetic benchmark (frozen targets, deterministic)

Phase 2.5B. A hermetic benchmark qualifies the **oracle + routing** against a target whose answer is
fixed, with a budget ledger — the frozen slice the Phase-3 ratchet will eventually be scored on.

## Hard rule — no real LLM in a hermetic target
A real model drifts run-to-run and cannot anchor a frozen benchmark. Hermetic targets are either:
- **no-model** (pure HTTP status/body differential — the BOLA target below), or
- **canned/fake-model** (recorded deterministic outputs — for the model-dependent cards, next).

So a hermetic run tests whether the harness **correctly adjudicates a known-answer transcript**, NOT
live model behavior. Live model behavior is tested in live slices, never here.

## Built
### `targets/bola-legacy-route/` — no-model, landed
Two-version chat-read endpoint: legacy `v1` trusts the client owner selector, canonical `v2`
re-resolves from the principal. The harness (`tools/run-hermetic-bola.py`) computes each response
deterministically from the target model, applies the `legacy-route-differential` oracle, and emits a
verdict **plus a target-call/budget ledger**. This proves the full chain: **frozen target → oracle →
scorer → budget accounting**, with zero model dependency.

```
python3 tools/run-hermetic-bola.py            # runs the bundled target, prints verdict + cost ledger
python3 tools/run-hermetic-bola.py --self-test # asserts confirmed-with-controls + budget-abort behavior
```

## Next (canned/fake-model harness)
`targets/render-escape/`, `targets/prompt-canary/`, `targets/capability-dispatch/`,
`targets/router-differential/` — each driven by **recorded** model outputs so determinism holds. These
exercise the LLM05 / LLM07 / LLM06 / model-router oracles. Not yet built; the BOLA target proves the
plumbing first (the cheapest, model-free slice), per the plan's sequencing.

## Boundary
A hermetic target is frozen and human-authored. Autoresearch may never mutate a target, its expected
verdict, or the budget — those are sealed evaluator data (see `docs/ROADMAP.md` Phase-3 scope fence).
