#!/usr/bin/env python3
"""False-discovery scorer (Phase 2.5A).

Distinct from the conformance check. `tools/check-conformance.py` only proves the corpus FIXTURE is
well-formed (no trap's own `correct_verdict` is 'confirmed'). THIS tool scores an actual EVALUATOR's
verdicts over the corpus and computes the real **invalid-accept rate** — how often the evaluator
`confirmed` a trap that is a non-finding. That is the gate the Phase-3 launch precondition refers to.

Evaluator-output format (the second arg):
  {"verdicts": [{"id": "trap-...", "verdict": "refuted|held|needs_review|deduped|confirmed"}]}
  (a {"id": "verdict"} object under "verdicts" is also accepted)

Acceptance: invalid_accept_rate == 0 AND every trap evaluated.

Usage:
  python3 tools/score-false-discovery.py <evaluator-output.json>
  python3 tools/score-false-discovery.py --self-test   # perfect->PASS, naive->caught
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, "fixtures", "false-discovery", "corpus.json")


def load(path):
    with open(path) as fh:
        return json.load(fh)


def normalize(out):
    v = out.get("verdicts", out)
    if isinstance(v, dict):
        return dict(v)
    return {e["id"]: e["verdict"] for e in v}


def score(corpus, out):
    entries = corpus.get("entries", [])
    verdicts = normalize(out)
    invalid_accepts = []   # evaluator confirmed a non-finding trap
    unscored = []
    for e in entries:
        tid = e["id"]
        if tid not in verdicts:
            unscored.append(tid)
            continue
        if verdicts[tid] == "confirmed":   # every trap's correct verdict is non-confirmed
            invalid_accepts.append(tid)
    total = len(entries)
    rate = len(invalid_accepts) / total if total else 0.0
    return {
        "total": total,
        "invalid_accepts": invalid_accepts,
        "invalid_accept_rate": rate,
        "unscored": unscored,
        "passed": not invalid_accepts and not unscored,
    }


def report(corpus, out):
    r = score(corpus, out)
    print(f"false-discovery: {'PASS' if r['passed'] else 'FAIL'}  "
          f"(invalid_accept_rate={r['invalid_accept_rate']:.3f}, {len(r['invalid_accepts'])}/{r['total']})")
    if r["invalid_accepts"]:
        print("  invalid accepts (confirmed a non-finding): " + ", ".join(r["invalid_accepts"]))
    if r["unscored"]:
        print("  unscored traps (no verdict supplied): " + ", ".join(r["unscored"]))
    return r["passed"]


def self_test():
    corpus = load(CORPUS)
    ok = True

    print("[self-test] perfect evaluator (each trap -> its correct verdict) should PASS")
    perfect = {"verdicts": {e["id"]: e["correct_verdict"] for e in corpus["entries"]}}
    if not report(corpus, perfect):
        ok = False
        print("  !! perfect evaluator did not PASS")

    print("[self-test] naive evaluator (each trap -> its naive wrong verdict) should be CAUGHT")
    naive = {"verdicts": {e["id"]: e["naive_wrong_verdict"] for e in corpus["entries"]}}
    res = report(corpus, naive)
    expected_accepts = [e["id"] for e in corpus["entries"] if e["naive_wrong_verdict"] == "confirmed"]
    if res or score(corpus, naive)["invalid_accepts"] != expected_accepts:
        ok = False
        print("  !! naive evaluator's invalid accepts were not caught exactly")

    print("\nSELF-TEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv):
    if len(argv) == 2 and argv[1] == "--self-test":
        return self_test()
    if len(argv) == 2:
        return 0 if report(load(CORPUS), load(argv[1])) else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
