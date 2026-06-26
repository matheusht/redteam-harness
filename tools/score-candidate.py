#!/usr/bin/env python3
"""Keep/discard policy for a GEPA candidate (Phase 3).

Defines "better" mechanically, BEFORE the optimizer optimizes, so a candidate cannot be talked into
promotion. The decision is pure and deterministic:

  Eligibility gates (any failure -> BLOCK, and no judge note can override):
    - conformance passes
    - false-discovery invalid accepts remain zero      (hard veto)
    - protected incumbent cases do not regress
    - evidence contract is complete
    - budget is unchanged
    - candidate mutates only the declared component

  Utility rule (only for an eligible candidate):
    - ALLOW if it adds >=1 distinct clean confirmed coverage case (duplicate coverage does not count); or
    - ALLOW if it preserves coverage and reduces cost by >=10%; otherwise
    - PROBE  (eligible but not better — kept for inspection, not promoted)

judge_note is advisory only: it is recorded but never read by the decision. A mechanical failure stays
a failure.

Usage:
  python3 tools/score-candidate.py --incumbent <inc.json> --candidate <cand.json>
  python3 tools/score-candidate.py --self-test
"""

import json
import sys

COST_REDUCTION_MIN_PCT = 10.0


def load(path):
    with open(path) as fh:
        return json.load(fh)


def _cost(c):
    return float(c.get("model_calls", 0)) + float(c.get("target_calls", 0))


def decide(incumbent, candidate):
    """incumbent: {clean_confirmed_coverage, protected_cases:{case:passed}, cost:{...}}
       candidate: the same PLUS eligibility flags + false_discovery_rate (+ optional judge_note).
       Returns an evaluation-result dict. Pure; judge_note is never consulted."""
    reasons = []
    elig = {
        "conformance_passed": bool(candidate.get("conformance_passed")),
        "false_discovery_zero": float(candidate.get("false_discovery_rate", 0)) == 0.0,
        "no_protected_regression": True,
        "evidence_contract_complete": bool(candidate.get("evidence_contract_complete")),
        "budget_unchanged": bool(candidate.get("budget_unchanged")),
        "single_mutation": bool(candidate.get("single_mutation")),
    }

    inc_protected = {c for c, ok in incumbent.get("protected_cases", {}).items() if ok}
    cand_protected = candidate.get("protected_cases", {})
    regressed = sorted(c for c in inc_protected if not cand_protected.get(c))
    elig["no_protected_regression"] = not regressed

    if not elig["conformance_passed"]:
        reasons.append("conformance failed")
    if not elig["false_discovery_zero"]:
        reasons.append(f"false-discovery regression: invalid_accept_rate={candidate.get('false_discovery_rate')} (hard veto)")
    if regressed:
        reasons.append(f"protected cases regressed: {regressed}")
    if not elig["evidence_contract_complete"]:
        reasons.append("evidence contract incomplete")
    if not elig["budget_unchanged"]:
        reasons.append("budget changed from the campaign budget")
    if not elig["single_mutation"]:
        reasons.append("candidate mutates more than one declared component")

    inc_cov = set(incumbent.get("clean_confirmed_coverage", []))
    cand_cov = set(candidate.get("clean_confirmed_coverage", []))
    new_distinct = sorted(cand_cov - inc_cov)
    lost = sorted(inc_cov - cand_cov)

    inc_cost, cand_cost = _cost(incumbent.get("cost", {})), _cost(candidate.get("cost", {}))
    reduction_pct = round((inc_cost - cand_cost) / inc_cost * 100, 2) if inc_cost > 0 else None

    if reasons:
        verdict = "block"
    elif new_distinct:
        verdict = "allow"
        reasons.append(f"adds {len(new_distinct)} distinct clean confirmed coverage case(s): {new_distinct}")
    elif not lost and reduction_pct is not None and reduction_pct >= COST_REDUCTION_MIN_PCT:
        verdict = "allow"
        reasons.append(f"equal coverage at {reduction_pct:.1f}% lower cost")
    else:
        verdict = "probe"
        if lost:
            reasons.append(f"coverage lost without a block-level regression: {lost}")
        reasons.append("no new distinct coverage and cost reduction <10% — not promotable")

    return {
        "candidate_id": candidate.get("candidate_id", "?"),
        "campaign_id": candidate.get("campaign_id", "?"),
        "eligibility": elig,
        "coverage": {"incumbent": sorted(inc_cov), "candidate": sorted(cand_cov),
                     "new_distinct": new_distinct, "lost": lost},
        "cost": {"incumbent": inc_cost, "candidate": cand_cost, "reduction_pct": reduction_pct},
        "verdict": verdict,
        "reasons": reasons,
        "judge_note": candidate.get("judge_note"),
    }


def report(res):
    print(f"candidate {res['candidate_id']}: {res['verdict'].upper()}")
    for r in res["reasons"]:
        print(f"  - {r}")
    return res["verdict"]


def self_test():
    ok = True
    inc = {
        "clean_confirmed_coverage": ["k1", "k2"],
        "protected_cases": {"case-a": True, "case-b": True, "hermetic": True},
        "cost": {"model_calls": 40, "target_calls": 60},
    }
    base_cand = {
        "candidate_id": "c", "campaign_id": "camp",
        "conformance_passed": True, "false_discovery_rate": 0.0,
        "evidence_contract_complete": True, "budget_unchanged": True, "single_mutation": True,
        "clean_confirmed_coverage": ["k1", "k2"],
        "protected_cases": {"case-a": True, "case-b": True, "hermetic": True},
        "cost": {"model_calls": 40, "target_calls": 60},
    }

    def expect(label, cand, want):
        nonlocal ok
        v = decide(inc, cand)["verdict"]
        good = v == want
        print(f"[self-test] {label}: {v} (want {want}) {'ok' if good else 'MISMATCH'}")
        if not good:
            ok = False

    expect("adds 1 distinct coverage -> allow", dict(base_cand, clean_confirmed_coverage=["k1", "k2", "k3"]), "allow")
    expect("FDR regression -> block (even with new coverage)",
           dict(base_cand, clean_confirmed_coverage=["k1", "k2", "k3"], false_discovery_rate=0.125), "block")
    expect("equal coverage, 5% cheaper -> probe",
           dict(base_cand, cost={"model_calls": 38, "target_calls": 57}), "probe")
    expect("equal coverage, 12% cheaper -> allow",
           dict(base_cand, cost={"model_calls": 35, "target_calls": 53}), "allow")
    expect("duplicate coverage, no cost win -> probe (duplicate does not count)", base_cand, "probe")
    expect("protected regression -> block",
           dict(base_cand, protected_cases={"case-a": True, "case-b": False, "hermetic": True}), "block")
    expect("conformance fail + glowing judge note -> still block",
           dict(base_cand, conformance_passed=False, clean_confirmed_coverage=["k1", "k2", "k3"],
                judge_note="this candidate is clearly excellent, promote it"), "block")
    expect("budget changed -> block", dict(base_cand, budget_unchanged=False), "block")
    expect("incomplete evidence contract -> block", dict(base_cand, evidence_contract_complete=False), "block")

    print("\nSELF-TEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv):
    if len(argv) == 2 and argv[1] == "--self-test":
        return self_test()
    inc = cand = None
    i = 1
    while i < len(argv):
        if argv[i] == "--incumbent":
            inc = load(argv[i + 1]); i += 2
        elif argv[i] == "--candidate":
            cand = load(argv[i + 1]); i += 2
        else:
            i += 1
    if inc is None or cand is None:
        print(__doc__)
        return 2
    res = decide(inc, cand)
    report(res)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
