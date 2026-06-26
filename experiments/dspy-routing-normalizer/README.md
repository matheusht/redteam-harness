# DSPy spike — routing-output normalizer (GEPA Phase 7)

**Status: built, evaluated, SHELVED (deterministic baseline wins for now).** Isolated experiment; not
wired into GEPA or the core harness. Revisit criteria below.

## The question
The plan's Phase 7: *test DSPy without turning it into the harness architecture.* The best first target
is **output normalization** — turning a blind router's messy free-form output into the strict
`score-routing` contract. The failure modes are real, observed in the rotation runs:

- a vuln id (`llm06.excessive-agency`, `vulns/...`) placed inside `cards`;
- JSON wrapped in explanation prose / a code fence;
- a `coverage_gap` row that still carries a force-fit card;
- non-vocab `strength` (`high`, `none`);
- stringy bools (`"true"`) and verdict casing (`"Refuted"`).

`cases.json` pins each failure mode to its normalized form.

## What was built
- **`baseline_normalize`** (stdlib, deterministic) — the control. Extracts the first balanced JSON
  object from prose, keeps only `pattern.*` ids in `cards` (moving vuln/other ids to `loaded_routes`),
  empties `cards` on `coverage_gap` rows and downgrades their strength (a gap is never "strong"),
  coerces bools/verdict vocab/strength synonyms. **Accuracy on the eval: 5/5.**
- **`DspyNormalizer`** (the spike) — a `dspy.Signature` + `dspy.Predict` that does the same job via an
  LM. Constructed **only** if `dspy` is importable AND an LM is configured; otherwise it skips cleanly.
  It is an optional dependency and is never required by GEPA or CI.

## How to run
```
python3 experiments/dspy-routing-normalizer/normalize.py --self-test   # deterministic baseline (CI runs this)
python3 experiments/dspy-routing-normalizer/normalize.py --dspy        # DSPy path if dspy + an LM are present
```

## Conclusion — shelve, keep isolated
On the failure modes we have actually seen, a **deterministic normalizer already scores 5/5**. DSPy
would add a heavy dependency and per-call LM latency/cost to a harness that is deliberately stdlib +
deterministic, for **no demonstrated gain** on these cases. Per the plan ("if it does not clearly help,
shelve it"), the spike stays an isolated experiment.

The acceptance bar DSPy must clear to earn a place — **revisit only when one of these is true**:
1. a failure mode appears that has **no recoverable JSON at all** (pure prose), where regex can't
   reconstruct the contract but an LM could;
2. we want to normalize the **evaluator's** natural-language adjudication (not just routing) into a
   structured verdict — a genuinely semantic task where typed LM modules may beat ad-hoc parsing;
3. the harness grows **several** stable LM programs (router, evaluator, planner) whose typed
   boundaries DSPy could unify — the point at which the dependency amortizes.

Until then: the deterministic normalizer is the recommended approach if/when we want to harden the
qualification runner against messy blind outputs. DSPy is parked, not adopted.
