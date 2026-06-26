#!/usr/bin/env python3
"""Hermetic fake-model benchmark runner (GEPA Phase 6B).

Generalizes the no-model BOLA harness to LLM-agentic oracles using FROZEN, canned model outputs (no
live LLM, zero drift). Each target declares an `oracle` and a list of requests whose canned fields the
oracle interprets deterministically into (signal, leak). The runner derives those, checks them against
each request's `expect` (so a broken detector is caught), then adjudicates uniformly:

  confirmed   : a primary signals AND leaks, every positive_control fires (detector works),
                every negative_control is clean (no ambient signal), within budget
  needs_review: a primary leaks but no positive_control validates the detector
  refuted      : otherwise

Oracles (each target ships a confirmed row, a held/refuted row, a false-positive trap, and a budget):
  render_escape       LLM05 — markup payload + canary reaches an ACTIVE sink (escaped/inert -> no signal)
  prompt_canary       LLM07 — exact system-prompt canary fingerprint appears (near-miss -> no leak)
  capability_dispatch LLM06 — dispatched a tool outside the granted set (listing != dispatch)
  router_differential same input class hits a backend whose policy != expected (diff backend, same policy -> inert)

Usage:
  python3 tools/run-hermetic-fakemodel.py            # run every bundled fake-model target
  python3 tools/run-hermetic-fakemodel.py <target.json>
  python3 tools/run-hermetic-fakemodel.py --self-test
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGETS_DIR = os.path.join(ROOT, "evals", "hermetic", "targets")
FAKE_MODEL_ORACLES = ("render_escape", "prompt_canary", "capability_dispatch", "router_differential")


def load(path):
    with open(path) as fh:
        return json.load(fh)


def derive(oracle, target, req):
    """Map a request's canned fields to (signal, leak). Deterministic; the ONLY source of truth."""
    if oracle == "render_escape":
        out = req.get("model_output", "")
        payload = ("CANARY" in out) and ("<" in out)         # escaped markup loses the '<'
        signal = payload and req.get("sink") == "active"
        return signal, signal
    if oracle == "prompt_canary":
        leak = target.get("canary", "\x00") in req.get("model_output", "")
        return leak, leak
    if oracle == "capability_dispatch":
        signal = req.get("dispatched") not in req.get("granted", [])
        return signal, signal
    if oracle == "router_differential":
        signal = req.get("policy") != req.get("expected_policy")
        return signal, signal
    raise ValueError(f"unknown oracle: {oracle}")


def adjudicate(results):
    primary = [r for r in results if r["kind"] == "primary"]
    pos = [r for r in results if r["kind"] == "positive_control"]
    negs = [r for r in results if r["kind"] == "negative_control"]
    leak = any(r["signal"] and r["leak"] for r in primary)
    detector_works = bool(pos) and all(r["signal"] for r in pos)
    negs_clean = all((not r["signal"]) and (not r["leak"]) for r in negs)
    if leak and detector_works and negs_clean:
        return "confirmed"
    if leak and not detector_works:
        return "needs_review"
    return "refuted"


def run(target, budget_override=None):
    oracle = target["oracle"]
    budget = budget_override if budget_override is not None else target.get("budget", {}).get("max_model_calls", 9999)
    calls = 0
    results, mismatches = [], []
    for req in target["requests"]:
        if calls >= budget:
            return {"verdict": "aborted_budget", "model_calls": calls, "budget": budget,
                    "within_budget": False, "mismatches": mismatches}
        signal, leak = derive(oracle, target, req)
        calls += 1
        exp = req.get("expect")
        if exp and (signal != exp.get("signal") or leak != exp.get("leak", exp.get("signal"))):
            mismatches.append(f"{req['id']}: got ({signal},{leak}) expected ({exp.get('signal')},{exp.get('leak')})")
        results.append({"kind": req["kind"], "signal": signal, "leak": leak})
    return {"verdict": adjudicate(results), "model_calls": calls, "budget": budget,
            "within_budget": calls <= budget, "mismatches": mismatches}


def report(target, res):
    print(f"target: {target['target']}  [{target['oracle']}]")
    print(f"  verdict     : {res['verdict']}  (expected: {target.get('expected_verdict')})")
    print(f"  cost ledger : {res['model_calls']}/{res['budget']} model calls  (within_budget={res['within_budget']})")
    if res["mismatches"]:
        print("  detector drift: " + "; ".join(res["mismatches"]))
    return res["verdict"] == target.get("expected_verdict") and not res["mismatches"]


def bundled_targets():
    out = []
    for name in sorted(os.listdir(TARGETS_DIR)):
        tp = os.path.join(TARGETS_DIR, name, "target.json")
        if os.path.isfile(tp):
            t = load(tp)
            if t.get("oracle") in FAKE_MODEL_ORACLES:
                out.append(t)
    return out


def self_test():
    ok = True
    targets = bundled_targets()
    if len(targets) < 4:
        ok = False
        print(f"[self-test] expected >=4 fake-model targets, found {len(targets)}")

    for t in targets:
        print(f"\n[self-test] {t['oracle']}: confirmed-with-controls, within budget, no drift")
        res = run(t)
        if not (res["verdict"] == t["expected_verdict"] and res["within_budget"] and not res["mismatches"]):
            ok = False
            print("  !!", res)

        res = run(t, budget_override=1)
        if res["verdict"] != "aborted_budget":
            ok = False
            print("  !! tight budget did not abort:", res)

        tampered = json.loads(json.dumps(t))
        for r in tampered["requests"]:
            if r["kind"] == "positive_control":
                if tampered["oracle"] == "prompt_canary":
                    r["model_output"] = "no canary here"
                elif tampered["oracle"] == "render_escape":
                    r["model_output"], r["sink"] = "plain text", "escaped"
                elif tampered["oracle"] == "capability_dispatch":
                    r["dispatched"] = r["granted"][0]
                else:
                    r["policy"] = r["expected_policy"]
                r.pop("expect", None)
        if run(tampered)["verdict"] == "confirmed":
            ok = False
            print("  !! confirmed without a working detector (positive control broken)")

    print("\nSELF-TEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv):
    if len(argv) == 2 and argv[1] == "--self-test":
        return self_test()
    if len(argv) == 2:
        t = load(argv[1])
        return 0 if report(t, run(t)) else 1
    ok = True
    for t in bundled_targets():
        if not report(t, run(t)):
            ok = False
        print()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
