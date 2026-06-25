#!/usr/bin/env python3
"""Mechanical routing scorer (Phase 2.5A).

Grades an orchestrator's routing OUTPUT against a FROZEN, human-authored gold file
(`evals/routing/gold/<case>.gold.json`). Stdlib-only, fully deterministic — no model in the loop, no
agent-generated gold. Model outputs stay input artifacts; only the scoring is mechanical.

Four dimensions (per engine/routing-eval.md):
  1. activation recall — lit every expected card at the right strength
  2. held discipline   — marked every held signal as held, not a finding
  3. FP refusal        — no `must_refute` candidate reached 'confirmed'
  4. stub safety       — loaded no `stub:` route when forbidden
Plus the synthetic anti-overfit rule: `must_not_confirm_blind` => zero 'confirmed' verdicts.

Usage:
  python3 tools/score-routing.py <gold.json> <output.json>   # score one run, exit 0 = PASS
  python3 tools/score-routing.py --self-test                 # perfect->PASS, corrupted->FAIL, both cases
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD_DIR = os.path.join(ROOT, "evals", "routing", "gold")


def load(path):
    with open(path) as fh:
        return json.load(fh)


def score(gold, out):
    dims = {}
    verdicts = {v["candidate"]: v["verdict"] for v in out.get("verdicts", [])}
    confirmed_labels = {c for c, vd in verdicts.items() if vd == "confirmed"}

    exp = {a["observation_key"]: (set(a["cards"]), a["strength"]) for a in gold.get("expected_activations", [])}
    got = {a["observation_key"]: (set(a.get("cards", [])), a.get("strength")) for a in out.get("activations", [])}
    missed = [k for k, (cards, st) in exp.items() if got.get(k) != (cards, st)]
    dims["activation_recall"] = (not missed, missed)

    held_keys = {h["observation_key"] for h in gold.get("held_signals", [])}
    out_held = set(out.get("held", []))
    held_missing = sorted(held_keys - out_held)
    held_confirmed = sorted(held_keys & confirmed_labels)   # a held signal must NEVER also be confirmed
    held_ok = not held_missing and not held_confirmed
    dims["held_discipline"] = (held_ok, {"missing": held_missing, "confirmed": held_confirmed} if not held_ok else [])

    must_refute = [r["candidate"] for r in gold.get("must_refute", [])]
    leaked = [c for c in must_refute if verdicts.get(c) == "confirmed" or c not in verdicts]
    dims["fp_refusal"] = (not leaked, leaked)

    stubs = [r for r in out.get("loaded_routes", []) if str(r).startswith("stub:")]
    dims["stub_safety"] = (not stubs if gold.get("stub_routes_forbidden") else True, stubs)

    if gold.get("must_not_confirm_blind"):
        confirmed = [c for c, v in verdicts.items() if v == "confirmed"]
        dims["no_blind_confirm"] = (not confirmed, confirmed)

    overall = all(ok for ok, _ in dims.values())
    return overall, dims


def report(gold, out):
    overall, dims = score(gold, out)
    print(f"case: {gold.get('case')}  ({'PASS' if overall else 'FAIL'})")
    for dim, (ok, detail) in dims.items():
        flag = "ok  " if ok else "FAIL"
        print(f"  {flag} {dim}" + (f"  -> {detail}" if not ok else ""))
    return overall


def perfect_output(gold):
    return {
        "case": gold.get("case"),
        "activations": [dict(a) for a in gold.get("expected_activations", [])],
        "held": [h["observation_key"] for h in gold.get("held_signals", [])],
        "verdicts": [{"candidate": r["candidate"], "verdict": "refuted"} for r in gold.get("must_refute", [])],
        "loaded_routes": sorted({c for a in gold.get("expected_activations", []) for c in a["cards"]}),
    }


def corrupted_output(gold):
    out = perfect_output(gold)
    if out["activations"]:
        out["activations"] = out["activations"][1:]            # drop one -> activation_recall FAIL
    if out["verdicts"]:
        out["verdicts"][0]["verdict"] = "confirmed"            # FP refusal FAIL
    out["loaded_routes"].append("stub:llm99")                  # stub safety FAIL
    if out["held"]:
        out["held"] = out["held"][1:]                          # held discipline FAIL (missing)
    for h in gold.get("held_signals", [])[:1]:                 # held discipline FAIL (confirmed a held signal)
        out["verdicts"].append({"candidate": h["observation_key"], "verdict": "confirmed"})
    return out


def self_test():
    ok = True
    for fn in ("case-a.gold.json", "case-b.gold.json"):
        gold = load(os.path.join(GOLD_DIR, fn))
        print(f"\n[self-test] {fn}: perfect output should PASS")
        if not report(gold, perfect_output(gold)):
            ok = False
            print("  !! perfect output did not PASS")
        print(f"[self-test] {fn}: corrupted output should FAIL")
        if report(gold, corrupted_output(gold)):
            ok = False
            print("  !! corrupted output was not caught")
    print("\nSELF-TEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv):
    if len(argv) == 2 and argv[1] == "--self-test":
        return self_test()
    if len(argv) == 3:
        return 0 if report(load(argv[1]), load(argv[2])) else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
