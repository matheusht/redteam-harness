#!/usr/bin/env python3
"""Hermetic no-model BOLA benchmark runner (Phase 2.5B).

Drives a FROZEN synthetic target (`evals/hermetic/targets/bola-legacy-route/target.json`) with NO LLM in
the loop. It computes each response deterministically from the target model, applies the
legacy-route-differential oracle, and emits a verdict PLUS a target-call/budget ledger. This proves the
full chain end to end — frozen target -> oracle -> scorer -> budget accounting — with zero model drift.

Usage:
  python3 tools/run-hermetic-bola.py            # run bundled target, print verdict + ledger
  python3 tools/run-hermetic-bola.py --self-test # confirmed-with-controls + budget-abort + no-differential
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(ROOT, "evals", "hermetic", "targets", "bola-legacy-route", "target.json")

DENY = (401, 403)


def load(path):
    with open(path) as fh:
        return json.load(fh)


def respond(target, req):
    """The synthetic target model. Deterministic; the ONLY source of truth for a response."""
    route = target["routes"][req["route"]]
    sel = req["owner_selector"]
    if sel == "victim":
        if route["trusts_owner_selector"]:
            return 200, True            # legacy route leaks the cross-tenant object + its canary
        return 403, False               # canonical route re-resolves ownership and denies
    return 404, False                   # no / self / bogus selector -> not found


def adjudicate(results):
    primary = [r for r in results if r["kind"] == "primary"]
    pos = [r for r in results if r["kind"] == "positive_control"]
    negs = [r for r in results if r["kind"] == "negative_control"]
    leak = any(r["status"] == 200 and r["canary"] for r in primary)
    sibling_denies = bool(pos) and all(r["status"] in DENY for r in pos)
    negs_clean = all(r["status"] == 404 and not r["canary"] for r in negs)
    if leak and sibling_denies and negs_clean:
        return "confirmed"
    if leak and not sibling_denies:
        return "needs_review"           # leak with no validating sibling -> could be public/shared
    return "refuted"


def run(target, budget_override=None):
    budget = budget_override if budget_override is not None else target.get("budget", {}).get("max_target_calls", 9999)
    calls = 0
    results = []
    mismatches = []
    for req in target["requests"]:
        if calls >= budget:
            return {"verdict": "aborted_budget", "target_calls": calls, "budget": budget, "within_budget": False, "mismatches": mismatches}
        status, canary = respond(target, req)
        calls += 1
        exp = req.get("expect", {})
        if exp and (status != exp.get("status") or canary != exp.get("body_contains_canary")):
            mismatches.append(f"{req['id']}: got ({status},{canary}) expected ({exp.get('status')},{exp.get('body_contains_canary')})")
        results.append({"kind": req["kind"], "status": status, "canary": canary})
    return {
        "verdict": adjudicate(results),
        "target_calls": calls,
        "budget": budget,
        "within_budget": calls <= budget,
        "mismatches": mismatches,
    }


def report(target, res):
    print(f"target: {target['target']}")
    print(f"  verdict        : {res['verdict']}  (expected: {target.get('expected_verdict')})")
    print(f"  cost ledger    : {res['target_calls']}/{res['budget']} target calls  (within_budget={res['within_budget']})")
    if res["mismatches"]:
        print("  detector drift : " + "; ".join(res["mismatches"]))
    return res["verdict"] == target.get("expected_verdict") and not res["mismatches"]


def self_test():
    target = load(TARGET)
    ok = True

    print("[self-test] 1. normal run -> confirmed with controls, within budget")
    res = run(target)
    if not (res["verdict"] == "confirmed" and res["within_budget"] and not res["mismatches"]):
        ok = False
        print("  !!", res)

    print("[self-test] 2. tight budget -> aborts (budget accounting works)")
    res = run(target, budget_override=2)
    if res["verdict"] != "aborted_budget":
        ok = False
        print("  !! expected aborted_budget, got", res)

    print("[self-test] 3. guard missing on canonical sibling -> NOT confirmed (no differential)")
    tampered = json.loads(json.dumps(target))
    tampered["routes"]["v2"]["trusts_owner_selector"] = True
    res = run(tampered)
    if res["verdict"] == "confirmed":
        ok = False
        print("  !! oracle confirmed without a denying sibling (public-share trap):", res)

    print("\nSELF-TEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv):
    if len(argv) == 2 and argv[1] == "--self-test":
        return self_test()
    target = load(argv[1] if len(argv) == 2 else TARGET)
    return 0 if report(target, run(target)) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
