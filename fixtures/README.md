# fixtures/ — frozen evaluator inputs

Frozen, human-authored inputs the evaluator grades against. None of these is a live optimization
environment; live engagements feed *new* sanitized fixtures here, they are never themselves the eval.

| Path | What it is | Checked by |
| --- | --- | --- |
| `routing-activation.fixtures.md` | recon → pattern-card activation map (prose) | `engine/routing.md` calibration |
| `llm07-calibration.md` | sanitized LLM07 ladder calibration | by eye |
| `findings/` | example finding instances exercising the evidence-contract gate | `tools/check-conformance.py` |
| `false-discovery/corpus.json` | live traps; a correct evaluator never `confirmed`s any | `tools/check-conformance.py` (invalid-accept == 0) |
| `adversarial-candidates/corpus.json` | Phase-3 gate: retain the valid additive, block the gamers | `tools/check-conformance.py` (well-formedness) |

## The evidence-contract gate (`findings/`)
`schemas/finding.schema.json` carries a structured `evidence_contract` (negative/positive control,
replay determinism, contamination ruleout, one-line justification, run-cost ledger, evidence refs).

Migration policy — **new findings hard-gated, back-catalog advisory**:
- `recorded_date >= 2026-06-25` ⇒ the contract is **required** (a missing/incomplete one FAILS).
- earlier findings ⇒ **advisory** warning only, until migrated.

`findings/_must_reject/` holds new-dated findings with absent/incomplete contracts; the checker asserts
the gate **catches** them (the invalid-accept guard). A green checker means the evidence contract is
**present and well-formed — necessary, not sufficient**. The model oracle still decides if it is TRUE.

## Corpora acceptance rules (asserted in CI)
- `false-discovery`: two gates. **Structural pre-gate** (`check-conformance.py`) — the fixture is
  well-formed, no trap's `correct_verdict` is `confirmed`. **Evaluator gate**
  (`tools/score-false-discovery.py`) — scores an actual evaluator's verdicts over the corpus and
  requires `invalid_accept_rate == 0` (every trap evaluated, none `confirmed`). The self-test proves a
  perfect evaluator passes and a naive one is caught.
- `adversarial-candidates`: ≥1 `retain`, ≥1 `block`, and every `touches_immutable` candidate is `block`.
  (The full retention/block check is a model-in-the-loop Phase-3 gate; this is the structural pre-gate.)
