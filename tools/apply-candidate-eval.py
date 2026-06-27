#!/usr/bin/env python3
"""Candidate-applied evaluation in isolation (GEPA Phase 9).

Phases 2-8 gated and scored candidate ARTIFACTS but never applied a candidate's diff, so coverage
delta vs the incumbent was 0 by construction and every clean candidate landed on `probe`. Phase 9
closes that: it actually APPLIES exactly one candidate diff in an ISOLATED git worktree (the live tree
is never touched), re-measures against the frozen evaluator, and feeds the MEASURED result through the
keep/discard policy. The verdict stops being provenance-only.

  candidate-manifest.json + candidate.diff
      |  check-campaign gate            (immutable / undeclared touch -> block, never applied)
      v
  git worktree add HEAD  ->  git apply candidate.diff   (isolated; live tree asserted byte-identical)
      |
      v
  re-run check-conformance.py IN THE WORKTREE           (a card-breaking variant blocks by MEASUREMENT)
      |  + frozen no-model benchmarks (card-independent -> equal the incumbent in deterministic mode)
      v
  score-candidate.decide(incumbent, applied)  ->  allow | probe | block

Backends:
  - deterministic (default, CI-safe): the frozen scorers do not read technique cards, so a card
    variant cannot move routing/coverage without a model; the applied scoreboard equals the incumbent
    for them, and the NEW measured signal is conformance against the patched tree. Clean variant ->
    probe; a variant that breaks the harness -> block; gold-touch -> block at the gate.
  - model (gated): re-run the blind orchestrator against the PATCHED workspace to get a real coverage
    delta. Requires an LM; skips honestly when unavailable (mirrors run-gepa-real).

Promotes nothing. Usage:
  python3 tools/apply-candidate-eval.py --campaign <campaign-manifest.json> [--candidate <id>]
  python3 tools/apply-candidate-eval.py --self-test
"""

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")


def _mod(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(TOOLS, filename))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


RG = _mod("run_gepa_shadow", "run-gepa-shadow.py")
CC = _mod("check_campaign", "check-campaign.py")
SC = _mod("score_candidate", "score-candidate.py")


def load(path):
    with open(path) as fh:
        return json.load(fh)


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(obj, fh, indent=2)
        fh.write("\n")


def sha256_file(path):
    if not os.path.isfile(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _git(args, cwd):
    return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)


def apply_in_isolation(root, diff_repo_path, target_repo_rel):
    """git-apply the candidate diff in a throwaway worktree at HEAD.

    Returns {diff_applies, isolation_ok, worktree, error}. The caller MUST call cleanup_worktree.
    The live tree's target file is asserted byte-identical before/after (the isolation invariant)."""
    live_target = os.path.join(root, target_repo_rel) if target_repo_rel else None
    before = sha256_file(live_target) if live_target else None

    wt = tempfile.mkdtemp(prefix="phase9-wt-")
    add = _git(["worktree", "add", "--detach", "--quiet", wt, "HEAD"], cwd=root)
    if add.returncode != 0:
        return {"diff_applies": False, "isolation_ok": True, "worktree": None,
                "error": f"worktree add failed: {add.stderr.strip()}"}

    diff_abs = diff_repo_path if os.path.isabs(diff_repo_path) else os.path.join(root, diff_repo_path)
    empty_diff = not (os.path.isfile(diff_abs) and os.path.getsize(diff_abs) > 0)
    if empty_diff:
        diff_applies, error = True, None            # a no-op baseline has an empty diff: nothing to apply
    else:
        chk = _git(["apply", "--check", "-p1", diff_abs], cwd=wt)
        if chk.returncode == 0:
            ap = _git(["apply", "-p1", diff_abs], cwd=wt)
            diff_applies = ap.returncode == 0
            error = None if diff_applies else f"git apply failed: {ap.stderr.strip()}"
        else:
            diff_applies, error = False, f"git apply --check failed: {chk.stderr.strip()}"

    after = sha256_file(live_target) if live_target else None
    isolation_ok = before == after
    return {"diff_applies": diff_applies, "isolation_ok": isolation_ok, "worktree": wt, "error": error}


def cleanup_worktree(root, wt):
    if wt and os.path.isdir(wt):
        _git(["worktree", "remove", "--force", wt], cwd=root)
        if os.path.isdir(wt):
            subprocess.run(["rm", "-rf", wt])
    _git(["worktree", "prune"], cwd=root)


def measure_conformance(worktree):
    """Run a TRUSTED conformance checker against the patched workspace. Defense-in-depth: the candidate
    diff is gated so it cannot touch the checker, but we still overwrite the worktree's copy with the
    evaluator's own HEAD checker before running, so a checker the candidate somehow altered can never
    grade itself. The checker derives its scan root from its own location, so the trusted-content file
    placed at <worktree>/tools/check-conformance.py scans the patched workspace."""
    import shutil
    dst = os.path.join(worktree, "tools", "check-conformance.py")
    if not os.path.isdir(os.path.dirname(dst)):
        return False
    trusted = os.path.join(ROOT, "tools", "check-conformance.py")
    try:
        shutil.copyfile(trusted, dst)
    except OSError:
        return False
    r = subprocess.run([sys.executable, dst], cwd=worktree, capture_output=True, text=True)
    return r.returncode == 0


def applied_candidate_eval(candidate, incumbent_scoreboard, applied_scoreboard,
                           conformance_passed, single_mutation):
    """Build the score-candidate input from the MEASURED applied scoreboard + measured conformance.

    budget_unchanged is True for any candidate that reached here: the contract gate already blocks a
    candidate whose budget differs from the campaign budget, so a gate-passing candidate's budget is
    unchanged by construction."""
    return {
        "candidate_id": candidate.get("candidate_id"),
        "campaign_id": candidate.get("campaign_id"),
        "conformance_passed": bool(conformance_passed),
        "false_discovery_rate": applied_scoreboard["false_discovery"]["invalid_accept_rate"],
        "evidence_contract_complete": True,
        "budget_unchanged": True,
        "single_mutation": single_mutation,
        "clean_confirmed_coverage": RG._coverage_keys(applied_scoreboard),
        "protected_cases": RG._protected(applied_scoreboard),
        "cost": RG._cost_of(applied_scoreboard),
    }


def evaluate_candidate(campaign, candidate, scoreboard, backend, root=ROOT):
    cid = candidate.get("candidate_id")
    gate_verdict, gate_reasons = CC.gate(campaign, candidate, root)
    entry = {
        "candidate_id": cid,
        "track": candidate.get("track"),
        "backend": backend,
        "gate": gate_verdict,
        "gate_reasons": gate_reasons,
        "diff_applies": None,
        "isolation_ok": None,
        "conformance_passed": None,
        "coverage_delta_vs_incumbent": None,
        "applied_verdict": "block",
        "verdict_reasons": ["blocked at contract gate; not applied"],
        "promoted": False,
    }
    if gate_verdict != "allow":
        return entry

    mt = candidate.get("mutation_target", "")
    target_rel = (mt + "SKILL.md") if mt.endswith("/") else mt
    iso = apply_in_isolation(root, candidate["diff"], target_rel)
    entry["diff_applies"] = iso["diff_applies"]
    entry["isolation_ok"] = iso["isolation_ok"]
    if iso.get("error"):
        entry["apply_error"] = iso["error"]

    conformance_passed = False
    if iso["worktree"] and iso["diff_applies"]:
        conformance_passed = measure_conformance(iso["worktree"])
    cleanup_worktree(root, iso["worktree"])
    entry["conformance_passed"] = conformance_passed

    if not iso["isolation_ok"]:
        entry["applied_verdict"] = "block"
        entry["verdict_reasons"] = ["isolation invariant violated: the live tree changed during apply"]
        return entry
    if not iso["diff_applies"]:
        entry["applied_verdict"] = "block"
        entry["verdict_reasons"] = ["candidate diff does not apply cleanly at HEAD: " + (iso.get("error") or "")]
        return entry

    applied_scoreboard = scoreboard            # deterministic: frozen scorers don't read technique cards
    inc = RG.incumbent_eval(scoreboard)
    cand_eval = applied_candidate_eval(candidate, scoreboard, applied_scoreboard,
                                       conformance_passed, single_mutation=True)
    decision = SC.decide(inc, cand_eval)
    entry["coverage_delta_vs_incumbent"] = sorted(set(decision["coverage"]["new_distinct"]))
    entry["applied_verdict"] = decision["verdict"]
    entry["verdict_reasons"] = decision["reasons"]
    return entry


def run_cli(campaign_path, only_candidate=None, backend="deterministic"):
    campaign = load(campaign_path)
    scoreboard = RG.baseline_scoreboard(campaign)
    candidates = RG.discover_candidates(campaign_path)
    if only_candidate:
        candidates = [c for c in candidates if c.get("candidate_id") == only_candidate]
        if not candidates:
            print(f"no such candidate: {only_candidate}")
            return 2

    results = []
    for cand in candidates:
        entry = evaluate_candidate(campaign, cand, scoreboard, backend)
        cdir = os.path.join(os.path.dirname(campaign_path), "candidates", cand["candidate_id"])
        write_json(os.path.join(cdir, "applied-eval.json"), entry)
        results.append(entry)

    report = {
        "campaign_id": campaign["campaign_id"],
        "backend": backend,
        "candidates": results,
        "applied": [r["candidate_id"] for r in results if r["gate"] == "allow" and r["diff_applies"]],
        "blocked": [r["candidate_id"] for r in results if r["applied_verdict"] == "block"],
        "promoted_any": False,
        "limitation": "deterministic backend: frozen scorers do not read technique cards, so behavioral "
                      "coverage delta is 0 here; conformance against the patched tree is the measured "
                      "model-free signal. A real coverage delta needs --backend model (an LM in the loop).",
    }
    out_dir = os.path.dirname(campaign_path)
    write_json(os.path.join(out_dir, "applied-eval-report.json"), report)
    md = render_md(report)
    with open(os.path.join(out_dir, "applied-eval-report.md"), "w") as fh:
        fh.write(md)
    print(md)
    return 0


def render_md(report):
    lines = [
        f"# Candidate-applied evaluation — {report['campaign_id']}",
        "",
        "Each gate-passing candidate's diff is **applied in an isolated git worktree** (the live tree is "
        "asserted byte-identical), then conformance is re-run against the patched workspace. Promotes "
        "nothing.",
        "",
        f"_backend: {report['backend']}_",
        "",
        "| candidate | gate | diff applies | isolation ok | conformance (patched) | applied verdict |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for r in report["candidates"]:
        def cell(v):
            return "—" if v is None else str(v)
        lines.append(f"| {r['candidate_id']} | {r['gate'].upper()} | {cell(r['diff_applies'])} | "
                     f"{cell(r['isolation_ok'])} | {cell(r['conformance_passed'])} | {r['applied_verdict'].upper()} |")
    lines += ["", f"_applied: {len(report['applied'])} · blocked: {len(report['blocked'])} · promoted: 0_",
              "", "**Limitation.** " + report["limitation"], ""]
    return "\n".join(lines)


# ---- self-test: the decide-path (synthetic measured scoreboards) + the isolation mechanism ----

def _fake_scoreboard(coverage_cases, fdr_rate=0.0, protected_extra=None):
    routing = [{"case": c, "passed": True} for c in coverage_cases]
    sb = {
        "routing_qualified": True,
        "routing": routing,
        "false_discovery": {"invalid_accept_rate": fdr_rate, "passed": fdr_rate == 0.0},
        "hermetic_bola": {"verdict": "confirmed", "passed": True, "target_calls": 5, "budget": 8},
        "hermetic_fakemodel": [{"oracle": "render_escape", "verdict": "confirmed", "passed": True, "model_calls": 4}],
    }
    if protected_extra is not None:
        sb["routing"] = [{"case": c, "passed": p} for c, p in protected_extra]
    return sb


def self_test():
    ok = True
    incumbent_sb = _fake_scoreboard(["case-a", "case-b"])
    inc = RG.incumbent_eval(incumbent_sb)
    cand = {"candidate_id": "c", "campaign_id": "x"}

    def verdict(applied_sb, conformance=True, single=True):
        ce = applied_candidate_eval(cand, incumbent_sb, applied_sb, conformance, single)
        return SC.decide(inc, ce)["verdict"]

    # neutral applied scoreboard (no behavioral change) -> probe
    if verdict(incumbent_sb) != "probe":
        ok = False; print("[self-test] neutral applied scoreboard should be probe")
    # better applied scoreboard (a new routing case passes) -> allow
    if verdict(_fake_scoreboard(["case-a", "case-b", "case-c"])) != "allow":
        ok = False; print("[self-test] added coverage should be allow")
    # conformance broken in the patched tree -> block
    if verdict(incumbent_sb, conformance=False) != "block":
        ok = False; print("[self-test] broken conformance should block")
    # protected regression -> block
    if verdict(_fake_scoreboard([], protected_extra=[("case-a", True), ("case-b", False)])) != "block":
        ok = False; print("[self-test] protected regression should block")
    print("[self-test] decide-path (neutral/better/conformance-break/regression):", "ok" if ok else "FAIL")

    # isolation mechanism on a real throwaway git repo
    with tempfile.TemporaryDirectory() as repo:
        _git(["init", "--quiet"], cwd=repo)
        _git(["config", "user.email", "t@t"], cwd=repo)
        _git(["config", "user.name", "t"], cwd=repo)
        tgt = "skills/techniques/demo/SKILL.md"
        os.makedirs(os.path.join(repo, os.path.dirname(tgt)), exist_ok=True)
        with open(os.path.join(repo, tgt), "w") as fh:
            fh.write("line one\nline two\n")
        _git(["add", "-A"], cwd=repo)
        _git(["commit", "-m", "init", "--quiet"], cwd=repo)
        before = sha256_file(os.path.join(repo, tgt))

        diff = (f"--- a/{tgt}\n+++ b/{tgt}\n@@ -1,2 +1,3 @@\n line one\n line two\n+line three (variant)\n")
        dpath = os.path.join(repo, "cand.diff")
        with open(dpath, "w") as fh:
            fh.write(diff)
        iso = apply_in_isolation(repo, "cand.diff", tgt)
        cleanup_worktree(repo, iso["worktree"])
        after = sha256_file(os.path.join(repo, tgt))
        iso_ok = iso["diff_applies"] and iso["isolation_ok"] and before == after
        if not iso_ok:
            ok = False; print(f"[self-test] isolation apply failed: {iso}, live changed={before != after}")
        else:
            print("[self-test] isolated apply: clean diff applies, live tree byte-identical: ok")

        # a non-applying diff is reported as such, and the live tree still does not change
        bad = os.path.join(repo, "bad.diff")
        with open(bad, "w") as fh:
            fh.write(f"--- a/{tgt}\n+++ b/{tgt}\n@@ -50,2 +50,3 @@\n nope\n nope\n+nope\n")
        iso2 = apply_in_isolation(repo, "bad.diff", tgt)
        cleanup_worktree(repo, iso2["worktree"])
        if iso2["diff_applies"] or not iso2["isolation_ok"]:
            ok = False; print(f"[self-test] non-applying diff mishandled: {iso2}")
        else:
            print("[self-test] non-applying diff reported, live tree untouched: ok")

    print("\nSELF-TEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv):
    ap = argparse.ArgumentParser(description="Phase 9 candidate-applied evaluation in isolation.")
    ap.add_argument("--campaign")
    ap.add_argument("--candidate")
    ap.add_argument("--backend", choices=["deterministic", "model"], default="deterministic")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv[1:])

    if args.self_test:
        return self_test()
    if args.backend == "model":
        print("[model backend] requires an LM in the loop to re-route against the patched workspace; "
              "not configured in this environment. Use --backend deterministic for the model-free path.")
        return 0
    if not args.campaign:
        ap.print_help()
        return 2
    return run_cli(args.campaign, only_candidate=args.candidate, backend=args.backend)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
