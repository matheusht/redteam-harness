#!/usr/bin/env python3
"""Broker-derived feedback assembler for GEPA/autoresearch (Track B).

The feedback string/artifact handed to a reflective optimizer must be assembled from broker-owned
events and mechanical adjudication, never from researcher narration or an LLM judge. This helper takes
the behavioral evaluator's `events.jsonl` plus report summary and emits a compact JSON contract:

  - probes run, controls, responses, cost, coverage/FDR, replay stability;
  - no positive feedback unless an adjudication event says broker/oracle confirmation occurred;
  - final researcher claims are retained as non-authoritative observations only.

Usage:
  python3 tools/broker-feedback.py --events <events.jsonl> --report <report.json>
  python3 tools/broker-feedback.py --self-test
"""

import argparse
import json
import os
import sys


def load_json(path):
    with open(path) as fh:
        return json.load(fh)


def load_events(path):
    out = []
    with open(path) as fh:
        for line in fh:
            if line.strip():
                out.append(json.loads(line))
    return out


def _key(e):
    return (e.get("candidate_id"), e.get("session"), e.get("role"), e.get("episode_id"))


def build_feedback(report, events):
    groups = {}
    for e in events:
        groups.setdefault(_key(e), {"events": [], "final_claims": [], "adjudication": None})["events"].append(e)
        if e.get("type") == "final":
            groups[_key(e)]["final_claims"].append(e.get("verdict"))
        if e.get("type") == "adjudication":
            groups[_key(e)]["adjudication"] = e

    rows = []
    positive_feedback = []
    invalid_claims = []
    for (candidate_id, session, role, episode_id), g in sorted(groups.items(), key=lambda kv: tuple(str(x) for x in kv[0])):
        probes = [e for e in g["events"] if e.get("type") == "probe" and e.get("executed")]
        controls = sorted({e.get("kind") for e in probes if e.get("kind") in {"negative_control", "positive_control", "replay"}})
        adj = g["adjudication"] or {}
        broker_confirmed = bool(adj.get("broker_confirmed"))
        oracle_confirmed = bool(adj.get("oracle_confirmed"))
        fdr_invalid = bool(adj.get("fdr_invalid"))
        final_claimed_confirmed = "confirmed" in g["final_claims"]
        if oracle_confirmed:
            positive_feedback.append({"candidate_id": candidate_id, "session": session, "role": role, "episode_id": episode_id})
        if final_claimed_confirmed and not broker_confirmed:
            invalid_claims.append({"candidate_id": candidate_id, "session": session, "role": role, "episode_id": episode_id})
        rows.append({
            "candidate_id": candidate_id,
            "session": session,
            "role": role,
            "episode_id": episode_id,
            "probes_run": [e.get("kind") for e in probes],
            "controls": controls,
            "target_calls": sum(1 for e in probes if e.get("executed")),
            "final_claims": g["final_claims"],
            "broker_confirmed": broker_confirmed,
            "oracle_confirmed": oracle_confirmed,
            "fdr_invalid": fdr_invalid,
        })

    candidates = []
    for c in report.get("candidates", []):
        candidates.append({
            "candidate_id": c.get("candidate_id"),
            "behavioral_verdict": c.get("behavioral_verdict"),
            "coverage_delta": c.get("coverage_delta", []),
            "fdr_invalids": (c.get("candidate") or {}).get("fdr_invalids", []),
            "cost": (c.get("candidate") or {}).get("cost", {}),
            "replay": {
                "incumbent_stable": c.get("incumbent_stable"),
                "candidate_stable": c.get("candidate_stable"),
            },
        })

    return {
        "contract": "broker-derived-feedback/v1",
        "authority": "broker_events_and_mechanical_adjudication_only",
        "researcher_text_authority": "none",
        "positive_feedback": positive_feedback,
        "invalid_researcher_claims": invalid_claims,
        "episodes": rows,
        "candidates": candidates,
    }


def self_test():
    ok = True
    report = {"candidates": [{"candidate_id": "cand-a", "behavioral_verdict": "probe",
                              "coverage_delta": [], "candidate": {"fdr_invalids": [], "cost": {"model_calls": 1, "target_calls": 2}},
                              "incumbent_stable": True, "candidate_stable": True}]}
    events = [
        {"candidate_id": "cand-a", "session": 0, "role": "candidate", "episode_id": "ep1",
         "type": "probe", "kind": "core", "executed": True, "disclosed": True},
        {"candidate_id": "cand-a", "session": 0, "role": "candidate", "episode_id": "ep1",
         "type": "final", "verdict": "confirmed", "self_report": "negative control and replay passed"},
        {"candidate_id": "cand-a", "session": 0, "role": "candidate", "episode_id": "ep1",
         "type": "adjudication", "broker_confirmed": False, "oracle_confirmed": False, "fdr_invalid": False},
    ]
    fb = build_feedback(report, events)
    if fb["positive_feedback"]:
        ok = False
        print("[self-test] researcher claim without broker confirmation produced positive feedback")
    if not fb["invalid_researcher_claims"]:
        ok = False
        print("[self-test] invalid researcher claim was not recorded")

    events[-1] = {**events[-1], "broker_confirmed": True, "oracle_confirmed": True}
    fb = build_feedback(report, events)
    if len(fb["positive_feedback"]) != 1:
        ok = False
        print("[self-test] broker-confirmed episode did not produce positive feedback")
    print("[self-test] broker-derived feedback ignores self-report and uses adjudication:", "ok" if ok else "FAIL")
    print("\nSELF-TEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--events")
    ap.add_argument("--report")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv[1:])
    if args.self_test:
        return self_test()
    if not args.events or not args.report:
        ap.print_help()
        return 2
    print(json.dumps(build_feedback(load_json(args.report), load_events(args.events)), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
