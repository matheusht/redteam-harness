#!/usr/bin/env python3
"""Model-in-the-loop evaluator qualification runner (Phase 2.5, slice 2).

Turns a real blind orchestrator/evaluator run into a mechanical QUALIFIED / BLOCKED verdict by feeding
its outputs through the frozen scorers. It is the adapter the scorers were built for:

  blind orchestrator output (natural, row-id keyed)
        |  translate via evals/qualification/crosswalk.json  (plumbing, not answers)
        v
  score-routing.py against evals/routing/gold/         -> activation/held/FP/stub dimensions
  score-false-discovery.py against the corpus          -> invalid_accept_rate (hard veto, must be 0)
        |
        v
  QUALIFIED only if every routing case PASSes AND the evaluator's invalid_accept_rate == 0.

The orchestrator never sees gold or the crosswalk (blindness). The crosswalk maps blind row ids to
frozen gold observation_keys; it is a structural id<->id anchor, never a verdict/strength/card.

Usage:
  python3 tools/run-qualification.py --evaluator <f> --orchestrator <f> [--orchestrator <f> ...]
  python3 tools/run-qualification.py --self-test   # examples/ perfect -> QUALIFIED, gaming -> BLOCKED
"""

import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
QUAL = os.path.join(ROOT, "evals", "qualification")
GOLD_DIR = os.path.join(ROOT, "evals", "routing", "gold")
CORPUS = os.path.join(ROOT, "fixtures", "false-discovery", "corpus.json")


def load(path):
    with open(path) as fh:
        return json.load(fh)


def _mod(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(TOOLS, filename))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


SR = _mod("score_routing", "score-routing.py")
SFD = _mod("score_false_discovery", "score-false-discovery.py")


def gold_by_case():
    out = {}
    for fn in sorted(os.listdir(GOLD_DIR)):
        if fn.endswith(".gold.json"):
            g = load(os.path.join(GOLD_DIR, fn))
            out[g["case"]] = g
    return out


def validate_orchestrator(o):
    problems = []
    if not isinstance(o.get("case"), str):
        problems.append("case missing")
    if not isinstance(o.get("rows"), list) or not o["rows"]:
        problems.append("rows missing/empty")
    else:
        for r in o["rows"]:
            if "id" not in r or not isinstance(r.get("cards"), list) or "strength" not in r:
                problems.append(f"row {r.get('id', '?')} malformed (need id, cards[], strength)")
    if not isinstance(o.get("loaded_routes"), list):
        problems.append("loaded_routes missing")
    return problems


def validate_evaluator(e):
    v = e.get("verdicts", e)
    vocab = {"refuted", "held", "needs_review", "deduped", "confirmed"}
    items = v if isinstance(v, list) else [{"id": k, "verdict": vv} for k, vv in v.items()]
    problems = []
    for it in items:
        if it.get("verdict") not in vocab:
            problems.append(f"verdict {it.get('id', '?')}={it.get('verdict')} out of vocab")
    return problems


def translate(orch, crosswalk):
    """Blind row-id-keyed output -> the score-routing 'out' contract, via the crosswalk."""
    cwc = crosswalk[orch["case"]]
    rowmap = cwc["rows"]
    activations, held = [], []
    rv = {}
    for r in orch["rows"]:
        key = rowmap.get(r["id"])
        if key is None:
            continue
        activations.append({"observation_key": key, "cards": r.get("cards", []), "strength": r.get("strength")})
        if r.get("held"):
            held.append(key)
        rv[r["id"]] = r.get("default_verdict")
    verdicts = [{"candidate": cand, "verdict": rv.get(rid)} for cand, rid in cwc.get("must_refute", {}).items()]
    gaps = [rowmap[r["id"]] for r in orch["rows"] if r.get("coverage_gap") and rowmap.get(r["id"])]
    return {"case": orch["case"], "activations": activations, "held": held, "verdicts": verdicts,
            "loaded_routes": orch.get("loaded_routes", []), "coverage_gaps": gaps}


def qualify(orchestrator_outputs, evaluator_output):
    golds = gold_by_case()
    crosswalk = load(os.path.join(QUAL, "crosswalk.json"))
    corpus = load(CORPUS)

    routing = []
    for orch in orchestrator_outputs:
        probs = validate_orchestrator(orch)
        gold = golds.get(orch.get("case"))
        if probs or gold is None:
            routing.append({"case": orch.get("case"), "passed": False, "dims": {"contract": (False, probs or "unknown case")}})
            continue
        passed, dims = SR.score(gold, translate(orch, crosswalk))
        routing.append({"case": orch["case"], "passed": passed, "dims": dims})

    eprobs = validate_evaluator(evaluator_output)
    fd = SFD.score(corpus, evaluator_output)
    fd_ok = fd["passed"] and not eprobs

    qualified = bool(routing) and all(r["passed"] for r in routing) and fd_ok
    return {"qualified": qualified, "routing": routing, "false_discovery": fd, "evaluator_contract": eprobs}


def report(res):
    print("== routing ==")
    for r in res["routing"]:
        print(f"  {'PASS' if r['passed'] else 'FAIL'}  {r['case']}")
        for dim, (ok, detail) in r["dims"].items():
            if not ok:
                print(f"        FAIL {dim} -> {detail}")
    fd = res["false_discovery"]
    print("== false-discovery ==")
    print(f"  {'PASS' if fd['passed'] else 'FAIL'}  invalid_accept_rate={fd['invalid_accept_rate']:.3f} "
          f"({len(fd['invalid_accepts'])}/{fd['total']})")
    if fd["invalid_accepts"]:
        print("        invalid accepts: " + ", ".join(fd["invalid_accepts"]))
    if res["evaluator_contract"]:
        print("        evaluator contract: " + "; ".join(res["evaluator_contract"]))
    print(f"\nQUALIFICATION: {'QUALIFIED' if res['qualified'] else 'BLOCKED'}")
    return res["qualified"]


def self_test():
    ex = os.path.join(QUAL, "examples")
    orchs = [load(os.path.join(ex, "orchestrator-case-a.json")), load(os.path.join(ex, "orchestrator-case-b.json"))]
    ok = True

    print("[self-test] perfect orchestrators + perfect evaluator -> QUALIFIED")
    if not report(qualify(orchs, load(os.path.join(ex, "evaluator.json")))):
        ok = False
        print("  !! perfect run did not qualify")

    print("\n[self-test] perfect orchestrators + GAMING evaluator -> BLOCKED")
    res = qualify(orchs, load(os.path.join(ex, "evaluator-gaming.json")))
    if res["qualified"]:
        ok = False
        print("  !! gaming evaluator was not blocked")

    print("\n[self-test] corrupted orchestrator (drop a row) -> BLOCKED")
    bad = json.loads(json.dumps(orchs))
    bad[0]["rows"] = bad[0]["rows"][1:]
    if qualify(bad, load(os.path.join(ex, "evaluator.json")))["qualified"]:
        ok = False
        print("  !! corrupted orchestrator was not blocked")

    print("\nSELF-TEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv):
    if len(argv) == 2 and argv[1] == "--self-test":
        return self_test()
    ev, orchs = None, []
    i = 1
    while i < len(argv):
        if argv[i] == "--evaluator":
            ev = load(argv[i + 1]); i += 2
        elif argv[i] == "--orchestrator":
            orchs.append(load(argv[i + 1])); i += 2
        else:
            i += 1
    if ev is None or not orchs:
        print(__doc__)
        return 2
    return 0 if report(qualify(orchs, ev)) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
