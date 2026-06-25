# evals/qualification/ — model-in-the-loop evaluator qualification

Phase 2.5, slice 2. The slice-1 scorers (`score-routing.py`, `score-false-discovery.py`) are graders
with no driver. This slice is the **driver + adapter**: it runs a real blind orchestrator/evaluator,
captures their outputs in a fixed contract, and turns the scores into a single **QUALIFIED / BLOCKED**
verdict. It is the bridge from "machinery exists" to "an evaluator has actually been qualified."

```
inputs/        blind inputs handed to the subagents (no answers): routing-case-*.json, false-discovery.json
*-brief.md     the subagent contracts + blindness controls (forbidden paths)
crosswalk.json PLUMBING: blind row id <-> frozen gold observation_key (an id anchor, never an answer)
examples/      worked outputs: perfect orchestrators + perfect/gaming evaluator (templates + self-test data)
runs/<date>/   provenance of an actual run: the verbatim subagent outputs + the runner's verdict
```

## Run it (mechanical part)
```
python3 tools/run-qualification.py --self-test            # examples: perfect -> QUALIFIED, gaming -> BLOCKED
python3 tools/run-qualification.py \
    --evaluator   runs/<date>/evaluator.json \
    --orchestrator runs/<date>/orchestrator-case-a.json \
    --orchestrator runs/<date>/orchestrator-case-b.json
```
QUALIFIED requires **every routing case PASS** (activation recall · held discipline · FP refusal · stub
safety) **AND** the evaluator's **invalid_accept_rate == 0** (the hard veto).

## The model-in-the-loop part (the actual qualification run)
A real run spawns two **blind** subagents (the harness engine = Claude Code subagents):
1. the **orchestrator** reads `orchestrator-brief.md` + `inputs/routing-case-*.json`, forbidden from
   `casebooks/ fixtures/ evals/`, and returns the orchestrator contract per case;
2. the **evaluator** reads `evaluator-brief.md` + `inputs/false-discovery.json`, forbidden from the
   corpus, and returns the evaluator contract.
Their verbatim outputs land in `runs/<date>/`, and `run-qualification.py` produces the verdict. The
subagents never see gold, the crosswalk, or the corpus — blindness is the whole point.

## Honest boundary
The runner mechanizes everything that can be set-compared. It does **not** itself judge subtle reasoning
quality — that is exactly why the inputs are blind and the gold is frozen: a model can pass only by
actually routing and adjudicating correctly, not by reading the answer. A qualified run on these two
cases is necessary, not sufficient, for trusting the evaluator on a fresh target — rotate in new
sanitized cases over time (RFC §07: live engagements feed new fixtures, they are never the eval).
