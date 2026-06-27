#!/usr/bin/env python3
"""Replay & variance gate for a GEPA candidate (Phase 4).

Stops one lucky run from becoming a promoted technique. The policy: a primary run plus TWO
fresh-session replays, identical benchmark version and budget across all three, recorded session
identifiers, and cost variance captured. A claim only survives if it reproduces:

  - every protected case the primary passed must hold in every replay;
  - the candidate's claimed new coverage must reproduce in every replay;
  - fewer than two replays, a benchmark-version drift, or a budget change all fail the policy.

The replay gate can only DOWNGRADE, never upgrade:
    block  -> block   (replay cannot rescue a blocked candidate)
    allow  -> allow if stable, else probe   (non-deterministic success becomes probe)
    probe  -> probe

Caller classification (Decision 0004 / Phase 10H0): this gate is NON-AUTHORIZING. It only reduces an
already-recorded verdict for variance; it never applies a diff and never turns a non-allow into an allow.
Final candidate authorization comes from the measured materialization boundary
(`apply-candidate-eval.materialize_candidate`), and promotion eligibility additionally requires a pinned
`materialization.verdict == allow` (`render-promotion-bundle`). Replay stability is necessary but not
sufficient for promotion.

In shadow mode the benchmark is deterministic, so the three runs are identical reproductions and the
variance spread is 0 — honest, and the machinery is still exercised. The self-test injects real
instability to prove the downgrade fires.

Usage:
  python3 tools/replay-candidate.py --campaign <campaign-manifest.json>   # generate replays/ + report
  python3 tools/replay-candidate.py --self-test
"""

import hashlib
import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
MIN_REPLAYS = 2


def load(path):
    with open(path) as fh:
        return json.load(fh)


def _mod(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(TOOLS, filename))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _run_cost(run):
    c = run.get("cost", {})
    return float(c.get("model_calls", 0)) + float(c.get("target_calls", 0))


def assess(runs, phase3_verdict, claimed_new_coverage, expected_budget, expected_version):
    """runs[0] is the primary; runs[1:] are replays. Pure + deterministic."""
    reasons = []
    replays = runs[1:]
    policy_ok = True

    if len(replays) < MIN_REPLAYS:
        policy_ok = False
        reasons.append(f"insufficient replays: {len(replays)} < {MIN_REPLAYS}")
    if any(r.get("benchmark_version") != expected_version for r in runs):
        policy_ok = False
        reasons.append("benchmark version drift across runs")
    if any(r.get("budget") != expected_budget for r in runs):
        policy_ok = False
        reasons.append("budget changed across runs")

    primary_protected = {c for c, ok in runs[0].get("protected_cases", {}).items() if ok}
    protected_stable = all(
        all(r.get("protected_cases", {}).get(c) for c in primary_protected) for r in replays
    )
    if not protected_stable:
        reasons.append("a protected case did not hold across all replays")

    claimed = set(claimed_new_coverage)
    coverage_stable = all(claimed <= set(r.get("clean_confirmed_coverage", [])) for r in runs)
    if claimed and not coverage_stable:
        reasons.append("claimed new coverage did not reproduce in every run")

    costs = [_run_cost(r) for r in runs]
    cost_variance = {"runs": costs, "min": min(costs), "max": max(costs),
                     "spread": max(costs) - min(costs),
                     "mean": round(sum(costs) / len(costs), 2)}

    stable = policy_ok and protected_stable and coverage_stable

    if phase3_verdict == "block":
        verdict = "block"
    elif phase3_verdict == "allow":
        verdict = "allow" if stable else "probe"
        if not stable:
            reasons.append("allow downgraded to probe: result is not replay-stable")
    else:
        verdict = "probe"

    return {
        "verdict": verdict,
        "phase3_verdict": phase3_verdict,
        "stable": stable,
        "policy_ok": policy_ok,
        "protected_stable": protected_stable,
        "coverage_stable": coverage_stable,
        "cost_variance": cost_variance,
        "runs": len(runs),
        "reasons": reasons,
    }


# ---- campaign generation: build replays/ for each allowed candidate of a shadow campaign ----

def _benchmark_version(campaign):
    blob = "".join(sorted(spec["sha256"] for spec in campaign.get("frozen_inputs", {}).values()))
    return "bench-" + hashlib.sha256(blob.encode()).hexdigest()[:12]


def _run_record(sb, RG, candidate_id, idx, version, budget):
    inc = RG.incumbent_eval(sb)
    return {
        "run_id": "primary" if idx == 0 else f"replay-{idx}",
        "session_id": f"{candidate_id}-session-{idx}",
        "fresh_session": idx > 0,
        "benchmark_version": version,
        "budget": budget,
        "clean_confirmed_coverage": inc["clean_confirmed_coverage"],
        "protected_cases": inc["protected_cases"],
        "cost": inc["cost"],
    }


def generate_for_campaign(campaign_path):
    campaign = load(campaign_path)
    camp_dir = os.path.dirname(campaign_path)
    report = load(os.path.join(camp_dir, "report.json"))
    RG = _mod("run_gepa_shadow", "run-gepa-shadow.py")

    sb = report["baseline_scoreboard"]
    version = _benchmark_version(campaign)
    budget = campaign["budgets"]
    summary_rows = []

    for cand in report["candidates"]:
        cid = cand["candidate_id"]
        if cand["gate"] != "allow":
            summary_rows.append({"candidate_id": cid, "final_verdict": "block",
                                 "note": "blocked at contract gate; no replay"})
            continue

        runs = [_run_record(sb, RG, cid, i, version, budget) for i in range(1 + MIN_REPLAYS)]
        claimed_new = cand["scored"] and []  # shadow: candidate reproduces incumbent, no claimed new coverage
        result = assess(runs, cand["keep_discard"]["verdict"], [], budget, version)

        rdir = os.path.join(camp_dir, "candidates", cid, "replays")
        os.makedirs(rdir, exist_ok=True)
        for r in runs:
            with open(os.path.join(rdir, r["run_id"] + ".json"), "w") as fh:
                json.dump(r, fh, indent=2); fh.write("\n")
        out = {"candidate_id": cid, "phase3_verdict": cand["keep_discard"]["verdict"], **result}
        with open(os.path.join(rdir, "replay-summary.json"), "w") as fh:
            json.dump(out, fh, indent=2); fh.write("\n")
        summary_rows.append({"candidate_id": cid, "final_verdict": result["verdict"],
                             "stable": result["stable"], "cost_spread": result["cost_variance"]["spread"]})

    md = ["# Replay report — " + campaign["campaign_id"], "",
          "Primary + two fresh-session replays per allowed candidate, identical benchmark version and "
          "budget. The replay gate downgrades non-reproducible `allow`s to `probe`; it never upgrades.",
          f"\nBenchmark version: `{version}`  ·  budget: `{json.dumps(budget)}`", "",
          "| candidate | final verdict | replay-stable | cost spread |", "| --- | --- | --- | --- |"]
    for r in summary_rows:
        md.append(f"| {r['candidate_id']} | {r['final_verdict'].upper()} | "
                  f"{r.get('stable', '—')} | {r.get('cost_spread', '—')} |")
    md += ["", "_Shadow mode: deterministic benchmark, so replays are identical reproductions and cost "
           "spread is 0. Non-determinism would downgrade an `allow` to `probe` (see replay-candidate --self-test)._", ""]
    with open(os.path.join(camp_dir, "replay-report.md"), "w") as fh:
        fh.write("\n".join(md))
    with open(os.path.join(camp_dir, "replay-report.json"), "w") as fh:
        json.dump({"campaign_id": campaign["campaign_id"], "benchmark_version": version,
                   "budget": budget, "candidates": summary_rows}, fh, indent=2); fh.write("\n")
    print("\n".join(md))
    return 0


def self_test():
    ok = True
    version, budget = "bench-abc", {"model_calls": 40, "target_calls": 80, "tokens": None}

    def run(idx, coverage=("k1", "k2"), protected=None, cost=(40, 60), ver=version, bud=budget):
        return {"run_id": "primary" if idx == 0 else f"replay-{idx}", "benchmark_version": ver,
                "budget": bud, "clean_confirmed_coverage": list(coverage),
                "protected_cases": protected or {"case-a": True, "case-b": True},
                "cost": {"model_calls": cost[0], "target_calls": cost[1]}}

    stable = [run(0), run(1), run(2)]

    def expect(label, runs, p3, claimed, want, bud=budget, ver=version):
        nonlocal ok
        v = assess(runs, p3, claimed, bud, ver)["verdict"]
        good = v == want
        print(f"[self-test] {label}: {v} (want {want}) {'ok' if good else 'MISMATCH'}")
        if not good:
            ok = False

    expect("allow + 2 stable replays -> allow", stable, "allow", ["k1"], "allow")
    expect("allow + replay drops a protected case -> probe",
           [run(0), run(1, protected={"case-a": True, "case-b": False}), run(2)], "allow", ["k1"], "probe")
    expect("allow + replay loses claimed coverage -> probe",
           [run(0), run(1, coverage=("k1",)), run(2)], "allow", ["k2"], "probe")
    expect("block + stable replays -> block (cannot rescue)", stable, "block", ["k1"], "block")
    expect("allow + only 1 replay -> probe (policy)", [run(0), run(1)], "allow", ["k1"], "probe")
    expect("allow + replay budget drift -> probe",
           [run(0), run(1, bud={"model_calls": 1}), run(2)], "allow", ["k1"], "probe")
    expect("probe + stable -> probe", stable, "probe", [], "probe")

    var = assess([run(0, cost=(40, 60)), run(1, cost=(42, 61)), run(2, cost=(39, 60))], "allow", [], budget, version)
    if var["cost_variance"]["spread"] != max(var["cost_variance"]["runs"]) - min(var["cost_variance"]["runs"]):
        ok = False
        print("[self-test] cost variance spread miscomputed")
    else:
        print("[self-test] cost variance recorded: ok")

    print("\nSELF-TEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv):
    if len(argv) == 2 and argv[1] == "--self-test":
        return self_test()
    if len(argv) == 3 and argv[1] == "--campaign":
        return generate_for_campaign(argv[2])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
