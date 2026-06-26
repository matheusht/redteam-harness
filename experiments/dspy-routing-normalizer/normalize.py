#!/usr/bin/env python3
"""DSPy spike — routing-output normalizer (GEPA Phase 7, ISOLATED experiment).

Hypothesis under test: does a DSPy typed module normalize a blind router's messy free-form output into
the strict score-routing contract MORE RELIABLY than the current prompt+JSON approach (or a plain
deterministic normalizer)? The failure modes are real — observed in the rotation runs: vuln ids inside
`cards`, prose-wrapped JSON, coverage_gap rows with a stray force-fit card, non-vocab strength,
stringy bools.

This file ships TWO normalizers over the same eval (`cases.json`):
  1. `baseline_normalize` — pure stdlib, deterministic. The CONTROL and the thing CI runs.
  2. `DspyNormalizer`     — a DSPy typed module, constructed ONLY if `dspy` + an LM are available.
                            The SPIKE. Skipped cleanly otherwise (it is an optional dependency and
                            must never be required by GEPA or the core harness).

Boundaries (per docs/gepa-autoresearch-implementation-plan.md Phase 7):
  - this does NOT replace any scorer; it only normalizes an INPUT before scoring;
  - it is NOT wired into GEPA or the conformance/CI required path beyond the deterministic self-test;
  - if DSPy does not clearly beat the deterministic baseline, the spike is shelved (see README).

Usage:
  python3 experiments/dspy-routing-normalizer/normalize.py --self-test   # deterministic baseline eval
  python3 experiments/dspy-routing-normalizer/normalize.py --dspy        # run the DSPy path if available
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CASES = os.path.join(HERE, "cases.json")

STRENGTHS = {"strong", "weak", "negative"}
STRENGTH_SYNONYMS = {"strong": "strong", "high": "strong", "weak": "weak", "low": "weak",
                     "negative": "negative", "neg": "negative", "held": "negative"}
VERDICTS = {"refuted", "needs_review", "held"}


def load_cases():
    return json.load(open(CASES))["cases"]


def extract_json(raw):
    """Pull the first balanced top-level JSON object out of possibly-prose-wrapped text."""
    if isinstance(raw, (dict, list)):
        return raw
    start = raw.find("{")
    if start < 0:
        raise ValueError("no JSON object found")
    depth, in_str, esc = 0, False, False
    for i in range(start, len(raw)):
        ch = raw[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(raw[start:i + 1])
    raise ValueError("unbalanced JSON object")


def _as_bool(v, default=False):
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes")
    return default


def _norm_strength(v, held, coverage_gap):
    if coverage_gap:
        return "weak"            # a gap row has no card to be 'strong' about; never let it read as a force-fit
    s = STRENGTH_SYNONYMS.get(str(v).strip().lower())
    if s in STRENGTHS:
        return s
    if held:
        return "negative"
    return "weak"


def _norm_verdict(v):
    if v is None:
        return None
    s = str(v).strip().lower()
    return s if s in VERDICTS else None


def normalize_row(row):
    coverage_gap = _as_bool(row.get("coverage_gap"))
    held = _as_bool(row.get("held"))
    raw_cards = row.get("cards") or []
    pattern_cards = sorted({c for c in raw_cards if isinstance(c, str) and c.startswith("pattern.")})
    non_pattern = [c for c in raw_cards if isinstance(c, str) and not c.startswith("pattern.")]
    cards = [] if coverage_gap else pattern_cards
    return {
        "id": row.get("id"),
        "cards": cards,
        "strength": _norm_strength(row.get("strength"), held, coverage_gap),
        "held": held,
        "default_verdict": _norm_verdict(row.get("default_verdict")),
        "coverage_gap": coverage_gap,
    }, non_pattern


def baseline_normalize(raw):
    """Deterministic stdlib normalizer: raw (str|dict) -> strict routing contract."""
    obj = extract_json(raw)
    moved = []
    rows = []
    for r in obj.get("rows", []):
        nr, non_pattern = normalize_row(r)
        rows.append(nr)
        moved += non_pattern
    loaded = list(obj.get("loaded_routes", []) or []) + moved
    return {
        "case": obj.get("case"),
        "rows": rows,
        "loaded_routes": sorted({c for c in loaded if isinstance(c, str)}),
    }


def score(normalizer):
    cases = load_cases()
    results = []
    for c in cases:
        try:
            got = normalizer(c["raw"])
            ok = got == c["expected"]
        except Exception as e:
            got, ok = {"error": str(e)}, False
        results.append((c["id"], ok, got, c["expected"]))
    passed = sum(1 for _, ok, _, _ in results if ok)
    return passed, len(results), results


# ---- the DSPy spike path (optional dependency; skipped if unavailable) ----

def dspy_normalizer_or_none():
    try:
        import dspy  # noqa: F401
    except Exception:
        return None, "dspy not installed"
    try:
        lm = getattr(__import__("dspy"), "settings").lm
    except Exception:
        lm = None
    if lm is None:
        return None, "dspy installed but no LM configured (dspy.settings.lm is unset)"

    import dspy

    class NormalizeRouting(dspy.Signature):
        """Normalize a blind router's messy output into the strict routing contract:
        rows of {id, cards (pattern.* only), strength in {strong,weak,negative}, held bool,
        default_verdict in {refuted,needs_review,held,null}, coverage_gap bool}; non-pattern ids
        and vuln ids move to loaded_routes; coverage_gap rows have empty cards."""
        raw_output = dspy.InputField()
        normalized_json = dspy.OutputField(desc="strict JSON: {case, rows[], loaded_routes[]}")

    predictor = dspy.Predict(NormalizeRouting)

    def run(raw):
        out = predictor(raw_output=raw if isinstance(raw, str) else json.dumps(raw))
        return extract_json(out.normalized_json)

    return run, "ready"


def self_test():
    passed, total, results = score(baseline_normalize)
    print("[self-test] deterministic baseline normalizer over cases.json")
    for cid, ok, got, exp in results:
        print(f"  {'ok  ' if ok else 'FAIL'} {cid}")
        if not ok:
            print(f"       got: {json.dumps(got)}")
            print(f"       exp: {json.dumps(exp)}")
    print(f"\nbaseline accuracy: {passed}/{total}")
    ok = passed == total
    print("SELF-TEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def run_dspy():
    norm, status = dspy_normalizer_or_none()
    if norm is None:
        print(f"[dspy] skipped — {status}")
        print("The spike requires `dspy` + a configured LM. The deterministic baseline is the control "
              "and is what CI runs (see --self-test).")
        return 0
    passed, total, results = score(norm)
    for cid, ok, _, _ in results:
        print(f"  {'ok  ' if ok else 'FAIL'} {cid}")
    print(f"\n[dspy] accuracy: {passed}/{total}  (status: {status})")
    return 0


def main(argv):
    if len(argv) == 2 and argv[1] == "--self-test":
        return self_test()
    if len(argv) == 2 and argv[1] == "--dspy":
        return run_dspy()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
