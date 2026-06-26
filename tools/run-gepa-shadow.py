#!/usr/bin/env python3
"""GEPA shadow campaign runner (Phase 2+).

The deterministic spine of a shadow campaign: it gates every candidate through the contract fence
(tools/check-campaign.py), runs the gate-passing ones through the FROZEN scorers
(tools/run-qualification.py + tools/run-hermetic-bola.py), and emits a campaign report. It promotes
NOTHING — it never writes under skills/ and never applies a candidate's diff.

  campaign-manifest.json
      |  discover candidates/*/candidate-manifest.json
      v
  check-campaign gate  --(block)-->  recorded, not scored, not promoted
      |  (allow)
      v
  run-qualification (routing + false-discovery) + run-hermetic-bola
      |
      v
  report.json + report.md   (promoted_any is always false)

Shadow honesty: this runner gates candidate artifacts but does not apply a candidate diff to a live
orchestrator. Candidates are scored against campaign-selected frozen benchmark outputs. Coverage
delta vs the incumbent is therefore 0 by construction here; the value proven is the contract gate,
frozen evaluator, keep/discard, replay, and promotion-bundle chain. Candidate-applied evaluation is
the next layer.

Usage:
  python3 tools/run-gepa-shadow.py --campaign <campaign-manifest.json>
  python3 tools/run-gepa-shadow.py --self-test
"""

import importlib.util
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
EXAMPLES = os.path.join(ROOT, "evals", "qualification", "examples")


def load(path):
    with open(path) as fh:
        return json.load(fh)


def _mod(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(TOOLS, filename))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


CC = _mod("check_campaign", "check-campaign.py")
RQ = _mod("run_qualification", "run-qualification.py")
HB = _mod("run_hermetic_bola", "run-hermetic-bola.py")
HF = _mod("run_hermetic_fakemodel", "run-hermetic-fakemodel.py")
SC = _mod("score_candidate", "score-candidate.py")


def qualification_orchestrators(campaign=None):
    """Campaign-selected frozen orchestrator outputs for routing qualification."""
    mapping = {
        "routing:case-a": os.path.join(EXAMPLES, "orchestrator-case-a.json"),
        "routing:case-b": os.path.join(EXAMPLES, "orchestrator-case-b.json"),
        "routing:rotation-case-01-web-api": os.path.join(
            ROOT, "evals", "qualification", "runs", "2026-06-25-rotation01", "orchestrator-rotation-01.json"
        ),
        "routing:rotation-case-02-agentic-tooluse": os.path.join(
            ROOT, "evals", "qualification", "runs", "2026-06-26-rotation02", "orchestrator.json"
        ),
    }
    if campaign:
        wanted = set(campaign.get("benchmark_set", []))
        paths = [p for key, p in mapping.items() if key in wanted]
    else:
        paths = [mapping["routing:case-a"], mapping["routing:case-b"]]
    return [load(p) for p in paths if os.path.isfile(p)]


def baseline_scoreboard(campaign=None):
    """The frozen, candidate-independent benchmark result the campaign measures against."""
    orchs = qualification_orchestrators(campaign)
    evaluator = load(os.path.join(EXAMPLES, "evaluator.json"))
    qual = RQ.qualify(orchs, evaluator)

    target = HB.load(HB.TARGET)
    herm = HB.run(target)
    herm_ok = herm["verdict"] == target.get("expected_verdict") and not herm["mismatches"]

    fakemodel = []
    for ft in HF.bundled_targets():
        fr = HF.run(ft)
        fakemodel.append({
            "oracle": ft["oracle"],
            "verdict": fr["verdict"],
            "passed": fr["verdict"] == ft.get("expected_verdict") and not fr["mismatches"],
            "model_calls": fr["model_calls"],
        })

    return {
        "routing_qualified": qual["qualified"],
        "routing": [{"case": r["case"], "passed": r["passed"]} for r in qual["routing"]],
        "false_discovery": {
            "invalid_accept_rate": qual["false_discovery"]["invalid_accept_rate"],
            "passed": qual["false_discovery"]["passed"],
        },
        "hermetic_bola": {"verdict": herm["verdict"], "passed": herm_ok,
                          "target_calls": herm["target_calls"], "budget": herm["budget"]},
        "hermetic_fakemodel": fakemodel,
    }


def _coverage_keys(sb):
    keys = [f"routing:{c['case']}" for c in sb["routing"] if c["passed"]]
    if sb["hermetic_bola"]["passed"]:
        keys.append("hermetic:bola-legacy-route")
    keys += [f"hermetic:{t['oracle']}" for t in sb.get("hermetic_fakemodel", []) if t["passed"]]
    return sorted(keys)


def _protected(sb):
    p = {f"routing:{c['case']}": c["passed"] for c in sb["routing"]}
    p["hermetic:bola-legacy-route"] = sb["hermetic_bola"]["passed"]
    for t in sb.get("hermetic_fakemodel", []):
        p[f"hermetic:{t['oracle']}"] = t["passed"]
    p["false-discovery"] = sb["false_discovery"]["passed"]
    return p


def _cost_of(sb):
    fake_calls = sum(t["model_calls"] for t in sb.get("hermetic_fakemodel", []))
    return {"model_calls": fake_calls, "target_calls": sb["hermetic_bola"]["target_calls"]}


def incumbent_eval(sb):
    return {"clean_confirmed_coverage": _coverage_keys(sb), "protected_cases": _protected(sb), "cost": _cost_of(sb)}


def candidate_eval(cand, sb):
    """Shadow candidate eval: candidate diff is not applied, so it reproduces the incumbent scoreboard.
    Gate-passing means single-mutation/budget/contract are already satisfied."""
    return {
        "candidate_id": cand.get("candidate_id"), "campaign_id": cand.get("campaign_id"),
        "conformance_passed": True,
        "false_discovery_rate": sb["false_discovery"]["invalid_accept_rate"],
        "evidence_contract_complete": True, "budget_unchanged": True, "single_mutation": True,
        "clean_confirmed_coverage": _coverage_keys(sb),
        "protected_cases": _protected(sb), "cost": _cost_of(sb),
    }


def evaluate_campaign(campaign, candidates, root, scoreboard):
    results = []
    for cand in candidates:
        verdict, reasons = CC.gate(campaign, cand, root)
        entry = {
            "candidate_id": cand.get("candidate_id"),
            "track": cand.get("track"),
            "is_baseline": bool(cand.get("is_baseline")),
            "gate": verdict,
            "gate_reasons": reasons,
            "scored": None,
            "coverage_delta_vs_baseline": None,
            "keep_discard": {"verdict": "block", "reasons": ["blocked at contract gate"]},
            "promoted": False,
        }
        if verdict == "allow":
            entry["scored"] = scoreboard
            entry["coverage_delta_vs_baseline"] = 0
            kd = SC.decide(incumbent_eval(scoreboard), candidate_eval(cand, scoreboard))
            entry["keep_discard"] = {"verdict": kd["verdict"], "reasons": kd["reasons"]}
        results.append(entry)
    return {
        "campaign_id": campaign.get("campaign_id"),
        "baseline_scoreboard": scoreboard,
        "candidates": results,
        "allowed": [r["candidate_id"] for r in results if r["gate"] == "allow"],
        "blocked": [r["candidate_id"] for r in results if r["gate"] == "block"],
        "promoted_any": False,
    }


def discover_candidates(campaign_manifest_path):
    cdir = os.path.join(os.path.dirname(campaign_manifest_path), "candidates")
    out = []
    if not os.path.isdir(cdir):
        return out
    for name in sorted(os.listdir(cdir)):
        mf = os.path.join(cdir, name, "candidate-manifest.json")
        if os.path.isfile(mf):
            out.append(load(mf))
    return out


def render_md(report):
    sb = report["baseline_scoreboard"]
    lines = [
        f"# GEPA shadow campaign — {report['campaign_id']}",
        "",
        "Shadow run: candidates are gated and scored against the campaign-selected frozen benchmark "
        "outputs. Nothing is applied or promoted (`promoted_any: false`). Coverage delta is 0 by "
        "construction in this runner because candidate diffs are not applied to an orchestrator.",
        "",
        "## Baseline scoreboard (incumbent control)",
        f"- routing qualified: **{sb['routing_qualified']}** "
        f"({', '.join(c['case'] + ('✓' if c['passed'] else '✗') for c in sb['routing'])})",
        f"- false-discovery: invalid_accept_rate={sb['false_discovery']['invalid_accept_rate']:.3f} "
        f"(passed={sb['false_discovery']['passed']})",
        f"- hermetic BOLA: {sb['hermetic_bola']['verdict']} (passed={sb['hermetic_bola']['passed']}, "
        f"{sb['hermetic_bola']['target_calls']}/{sb['hermetic_bola']['budget']} target calls)",
        "- hermetic fake-model: " + (", ".join(
            f"{t['oracle']}={t['verdict']}{'✓' if t['passed'] else '✗'}" for t in sb.get("hermetic_fakemodel", []))
            or "—"),
        "",
        "## Candidates",
        "",
        "| candidate | track | gate | scored | Δcoverage | keep/discard | promoted |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in report["candidates"]:
        scored = "QUALIFIED" if r["scored"] and r["scored"]["routing_qualified"] else ("—" if not r["scored"] else "scored")
        delta = "—" if r["coverage_delta_vs_baseline"] is None else str(r["coverage_delta_vs_baseline"])
        kd = r["keep_discard"]["verdict"].upper()
        lines.append(f"| {r['candidate_id']} | {r['track']} | {r['gate'].upper()} | {scored} | {delta} | {kd} | {r['promoted']} |")
    blocked = [r for r in report["candidates"] if r["gate"] == "block"]
    if blocked:
        lines += ["", "## Blocked at the contract gate (retained, never promoted)"]
        for r in blocked:
            lines.append(f"- **{r['candidate_id']}**: " + "; ".join(r["gate_reasons"]))
    kd_counts = {}
    for r in report["candidates"]:
        v = r["keep_discard"]["verdict"]
        kd_counts[v] = kd_counts.get(v, 0) + 1
    kd_str = " · ".join(f"{k}: {kd_counts[k]}" for k in sorted(kd_counts))
    lines += ["", "## Keep/discard policy (Phase 3)",
              "Mechanical: eligibility gates are hard vetoes; an eligible candidate is `allow` only if it "
              "adds a distinct clean confirmed coverage case or preserves coverage at >=10% lower cost. In "
              "shadow mode every gate-passing candidate reproduces the incumbent scoreboard, so it is "
              "`probe` (eligible, not better) — exactly right until candidate-applied evaluation measures "
              "a real behavioral delta.",
              "", f"_keep/discard: {kd_str}_",
              "", f"_allowed: {len(report['allowed'])} · blocked: {len(report['blocked'])} · promoted: 0_", ""]
    return "\n".join(lines)


def run_cli(campaign_path):
    campaign = load(campaign_path)
    candidates = discover_candidates(campaign_path)
    report = evaluate_campaign(campaign, candidates, ROOT, baseline_scoreboard(campaign))

    out_dir = os.path.dirname(campaign_path)
    with open(os.path.join(out_dir, "report.json"), "w") as fh:
        json.dump(report, fh, indent=2)
        fh.write("\n")
    with open(os.path.join(out_dir, "report.md"), "w") as fh:
        fh.write(render_md(report))

    print(render_md(report))
    return 0 if not report["promoted_any"] else 1


# ---- self-test: tmp campaign with a no-op baseline (allow) + a gold-editing candidate (block) ----

def _write(root, rel, text):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as fh:
        fh.write(text)
    return p


def self_test():
    ok = True
    with tempfile.TemporaryDirectory() as root:
        _write(root, "c/baseline/candidate.diff", "")
        bh = CC.sha256_file(os.path.join(root, "c/baseline/candidate.diff"))
        _write(root, "c/baseline/evidence-bundle.md", "# baseline\n")
        _write(root, "c/bad/candidate.diff", "--- a/evals/routing/gold/x\n+tamper\n")
        bad_h = CC.sha256_file(os.path.join(root, "c/bad/candidate.diff"))
        _write(root, "c/bad/evidence-bundle.md", "# bad\n")

        campaign = {
            "campaign_id": "camp-st", "created": "2026-06-26",
            "tracks": [{"name": "task-reframing", "mutation_target": "skills/techniques/task-reframing/", "kind": "existing-card-variant"}],
            "mutable_allowlist": ["skills/techniques/task-reframing/"], "immutable": [],
            "frozen_inputs": {}, "budgets": {"model_calls": 1, "target_calls": 1, "tokens": None},
            "benchmark_set": ["routing:case-a"],
        }
        candidates = [
            {"candidate_id": "cand-baseline", "campaign_id": "camp-st", "parent": "baseline",
             "track": "task-reframing", "mutation_target": "skills/techniques/task-reframing/",
             "touched_files": [], "diff": "c/baseline/candidate.diff", "candidate_hash": bh,
             "evidence_bundle": "c/baseline/evidence-bundle.md", "is_baseline": True},
            {"candidate_id": "cand-bad", "campaign_id": "camp-st", "parent": "baseline",
             "track": "task-reframing", "mutation_target": "skills/techniques/task-reframing/",
             "touched_files": ["skills/techniques/task-reframing/SKILL.md", "evals/routing/gold/x"],
             "diff": "c/bad/candidate.diff", "candidate_hash": bad_h,
             "evidence_bundle": "c/bad/evidence-bundle.md", "is_baseline": False},
        ]

        report = evaluate_campaign(campaign, candidates, root, baseline_scoreboard())
        by = {c["candidate_id"]: c for c in report["candidates"]}

        if by["cand-baseline"]["gate"] != "allow" or by["cand-baseline"]["scored"] is None:
            ok = False; print("[self-test] baseline should allow + be scored")
        if by["cand-bad"]["gate"] != "block" or by["cand-bad"]["scored"] is not None:
            ok = False; print("[self-test] gold-editing candidate should block + not be scored")
        if report["promoted_any"]:
            ok = False; print("[self-test] nothing may be promoted")
        if not report["baseline_scoreboard"]["routing_qualified"]:
            ok = False; print("[self-test] baseline scoreboard should be QUALIFIED against frozen examples")

        print("[self-test] baseline allow+scored, invalid blocked, nothing promoted:", "ok" if ok else "FAIL")

    print("\nSELF-TEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv):
    if len(argv) == 2 and argv[1] == "--self-test":
        return self_test()
    if len(argv) == 3 and argv[1] == "--campaign":
        return run_cli(argv[2])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
