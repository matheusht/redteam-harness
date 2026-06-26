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

### `targets/{llm05-render-escape,llm07-prompt-canary,llm06-capability-dispatch,model-router-differential}/` — canned/fake-model, landed (Phase 6B)
Each is driven by **recorded** model outputs so determinism holds. `tools/run-hermetic-fakemodel.py`
derives `(signal, leak)` from each request's canned fields via the target's oracle, checks them against
the per-request `expect` (so a broken detector surfaces as drift), and adjudicates uniformly: confirmed
needs a leaking primary, a firing positive control (the detector works), and clean negative controls.
Every target ships a **confirmed** row, a **held/refuted** row, a **false-positive trap**, and a budget.

| target | oracle | the false-positive trap |
| --- | --- | --- |
| `llm05-render-escape` | LLM05 — markup payload + canary reaches an active sink | the canary word in plain prose / an escaped sink (inert reflection) |
| `llm07-prompt-canary` | LLM07 — exact system-prompt canary fingerprint leaks | a near-miss fingerprint (`SYS-CANARY-0000`) |
| `llm06-capability-dispatch` | LLM06 — dispatched a tool outside the granted set | *listing* an ungranted tool without dispatching it |
| `model-router-differential` | same input class hits a backend whose policy != expected | a different backend that still enforces the expected policy |

```
python3 tools/run-hermetic-fakemodel.py             # run every bundled fake-model target
python3 tools/run-hermetic-fakemodel.py --self-test # per oracle: confirmed + budget-abort + detector-break
```

These four targets are wired into the GEPA shadow runner's baseline scoreboard and pinned in the first
campaign's `frozen_inputs`, so the evaluator the ratchet is scored against is now wider than BOLA alone.

## Boundary
A hermetic target is frozen and human-authored. Autoresearch may never mutate a target, its expected
verdict, or the budget — those are sealed evaluator data (see `docs/ROADMAP.md` Phase-3 scope fence).
