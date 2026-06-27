#!/usr/bin/env python3
"""Candidate-applied evaluation in isolation (GEPA Phase 9; authoritative boundary in Phase 10H0).

Phases 2-8 gated and scored candidate ARTIFACTS but never applied a candidate's diff. Phase 9 applied
exactly one candidate diff in an ISOLATED git worktree and re-measured conformance. Phase 10H0 makes the
APPLIED REPOSITORY STATE — not the patch text — the final authority (`materialize_candidate`): the
contract gate becomes a fast PREFLIGHT that can reject but never authorize, and `allow` requires the diff
to apply with `git apply --index`, the STAGED tree to be measured, declared==actual paths, mutable-
allowlist membership, regular-file type, the baseline/non-baseline tree rule, and trusted conformance.

  candidate-manifest.json + candidate.diff
      |  check-campaign.gate                    PREFLIGHT (fast; may reject, cannot authorize)
      v
  git worktree add --detach HEAD -> git apply --index     (isolated; live tree asserted byte-identical)
      |  measure the STAGED index: changed paths, file modes, binary, base/candidate tree ids
      v
  measured_policy(...)  +  trusted conformance (committed HEAD checker) in the worktree
      |  authoritative allow | block  (measured tree, never the patch syntax)
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

# The only legitimate post-apply file mode: a regular, non-executable file. Measuring the staged mode
# (not the patch header) catches an executable-bit flip, a symlink (120000), a gitlink (160000), and a
# deletion (000000) uniformly — the cases a header parser had to special-case one by one.
REGULAR_FILE_MODE = "100644"


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
    """Run a TRUSTED conformance checker against the patched workspace. The trusted bytes come from
    COMMITTED HEAD (`git show HEAD:tools/check-conformance.py`), not the possibly-dirty working tree, so
    neither an uncommitted local edit nor a candidate diff can make the checker grade itself. The checker
    derives its scan root from its own location, so writing the trusted bytes to
    <worktree>/tools/check-conformance.py scans the patched workspace."""
    dst = os.path.join(worktree, "tools", "check-conformance.py")
    if not os.path.isdir(os.path.dirname(dst)):
        return False
    head = subprocess.run(["git", "-C", ROOT, "show", "HEAD:tools/check-conformance.py"],
                          capture_output=True, text=True)
    if head.returncode != 0:
        return False
    with open(dst, "w") as fh:
        fh.write(head.stdout)
    r = subprocess.run([sys.executable, dst], cwd=worktree, capture_output=True, text=True)
    return r.returncode == 0


def _git_z(args, cwd):
    r = _git(args, cwd)
    return [t for t in r.stdout.split("\0") if t] if r.returncode == 0 else []


def _staged_changes(wt):
    """Measure the candidate's effect from the STAGED Git index (never the patch text).

    Returns (paths, modes, binary): the changed path set, {path: new_mode}, and the subset that Git
    reports as binary. `git apply --index` stages exactly what the patch did, so this is ground truth
    for declared==actual, file type, and binary detection regardless of how the patch was written."""
    paths = _git_z(["diff", "--cached", "--name-only", "-z", "--no-renames", "HEAD"], wt)
    modes = {}
    raw = _git(["diff", "--cached", "--raw", "-z", "--no-renames", "HEAD"], cwd=wt)
    toks = raw.stdout.split("\0")
    i = 0
    while i < len(toks):                              # raw -z: ":m1 m2 s1 s2 STATUS" NUL path NUL ...
        meta = toks[i]
        if meta.startswith(":"):
            fields = meta[1:].split(" ")
            new_mode = fields[1] if len(fields) >= 2 else "000000"
            path = toks[i + 1] if i + 1 < len(toks) else ""
            if path:
                modes[path] = new_mode
            i += 2
        else:
            i += 1
    binary = []
    num = _git(["diff", "--cached", "--numstat", "-z", "--no-renames", "HEAD"], cwd=wt)
    for rec in num.stdout.split("\0"):               # numstat -z: "added\tremoved\tpath", "-" == binary
        if not rec:
            continue
        parts = rec.split("\t")
        if len(parts) >= 3 and parts[0] == "-" and parts[1] == "-":
            binary.append(parts[2])
    return sorted(paths), modes, sorted(binary)


def measured_policy(facts):
    """Pure: given MEASURED facts about the applied tree, return (reasons, flags). This is the parity
    surface — every rejection a patch parser made by reading the diff must also fall out of measured tree
    state here, which is what lets the patch parser become preflight-only. No git, no I/O.

    facts: declared(set/list), is_baseline(bool), mt(str), allowlist(list), immutable(list),
    actual(list), modes(dict path->new_mode), binary(list), base_tree, candidate_tree,
    target_rel(str), target_regular(bool)."""
    reasons = []
    declared, actual = set(facts["declared"]), set(facts["actual"])
    mt = facts["mt"]
    allowlist = facts["allowlist"]
    immutable = facts["immutable"]
    modes = facts["modes"]

    paths_match = actual == declared
    if not paths_match:
        reasons.append(f"declared touched_files {sorted(declared)} != measured changed paths {sorted(actual)}")

    bad_modes = sorted(f"{p}:{modes.get(p)}" for p in actual if modes.get(p) != REGULAR_FILE_MODE)
    regular_files_ok = not bad_modes
    if bad_modes:
        reasons.append(f"non-regular file state after apply (symlink/gitlink/exec/delete): {bad_modes}")
    if facts["binary"]:
        reasons.append(f"binary content in changed files: {sorted(facts['binary'])}")

    stray = sorted(p for p in actual if mt and not CC._under(p, mt))
    out_allow = sorted(p for p in actual if allowlist and not any(CC._under(p, a) for a in allowlist))
    leaked = sorted(p for p in actual if any(CC._under(p, im) for im in immutable))
    allowlist_passed = not (stray or out_allow or leaked)
    if stray:
        reasons.append(f"measured paths outside mutation_target '{mt}': {stray}")
    if out_allow:
        reasons.append(f"measured paths outside the mutable allowlist {allowlist}: {out_allow}")
    if leaked:
        reasons.append(f"measured paths touch immutable (evaluator/gold/budget) files: {leaked}")

    if facts["is_baseline"]:
        baseline_unchanged = bool(facts["candidate_tree"]) and facts["candidate_tree"] == facts["base_tree"] and not actual
        if not baseline_unchanged:
            reasons.append("baseline candidate changed the tree (a control must touch nothing)")
    else:
        baseline_unchanged = None
        if not actual or facts["candidate_tree"] == facts["base_tree"]:
            reasons.append("non-baseline candidate produced no measured change to the tree")

    if not facts["is_baseline"] and facts["target_rel"]:
        if not facts["target_regular"] or modes.get(facts["target_rel"], REGULAR_FILE_MODE) != REGULAR_FILE_MODE:
            reasons.append(f"declared technique component '{facts['target_rel']}' is not a regular file after apply")

    return reasons, {"paths_match": paths_match, "regular_files_ok": regular_files_ok,
                     "allowlist_passed": allowlist_passed, "baseline_unchanged": baseline_unchanged}


def _blank_materialization(declared, is_baseline, target_rel):
    return {
        "preflight": "block", "preflight_reasons": [],
        "apply": "block",
        "base_tree": None, "candidate_tree": None,
        "declared_paths": sorted(set(declared)), "actual_paths": [],
        "paths_match": False, "allowlist_passed": False,
        "baseline_unchanged": (True if is_baseline else None),
        "regular_files_ok": False, "isolation_ok": True, "conformance_passed": False,
        "is_baseline": is_baseline, "target_rel": target_rel,
        "measured_reasons": [], "reasons": [], "verdict": "block",
        "patched_card_text": None,
    }


def materialize_candidate(campaign, candidate, root=ROOT):
    """Authoritative candidate boundary (Phase 10H0): applied repository state, not patch syntax, decides.

    The contract gate runs first as a fast PREFLIGHT (defense in depth) but cannot authorize. The diff is
    then applied with `git apply --index` in a clean detached worktree at committed HEAD, and the
    resulting STAGED tree is measured: declared==actual paths, mutable-allowlist membership, no immutable
    touch, regular-file type, the baseline/non-baseline tree rule, and trusted conformance from committed
    HEAD. A final `allow` requires preflight pass AND every measured check; otherwise `block` with the
    measured reasons. Fail-closed and the worktree is always cleaned up."""
    declared = sorted(set(candidate.get("touched_files", [])))
    is_baseline = bool(candidate.get("is_baseline"))
    mt = candidate.get("mutation_target", "") or ""
    target_rel = (mt + "SKILL.md") if mt.endswith("/") else mt
    allowlist = list(campaign.get("mutable_allowlist", [])) or ([mt] if mt else [])
    immutable = list(CC.DEFAULT_IMMUTABLE) + list(campaign.get("immutable", []))
    res = _blank_materialization(declared, is_baseline, target_rel)

    pf_verdict, pf_reasons = CC.gate(campaign, candidate, root)     # PREFLIGHT — cannot authorize
    res["preflight"] = "pass" if pf_verdict == "allow" else "block"
    res["preflight_reasons"] = pf_reasons

    measured = []
    diff = candidate.get("diff")
    diff_abs = (diff if os.path.isabs(diff) else os.path.join(root, diff)) if diff else None
    live_target = os.path.join(root, target_rel) if target_rel else None
    before = sha256_file(live_target) if live_target else None

    wt = tempfile.mkdtemp(prefix="phase10h0-wt-")
    try:
        add = _git(["worktree", "add", "--detach", "--quiet", wt, "HEAD"], cwd=root)
        if add.returncode != 0:
            measured.append(f"worktree add failed: {add.stderr.strip()}")
        else:
            res["base_tree"] = (_git(["rev-parse", "HEAD^{tree}"], cwd=wt).stdout.strip() or None)
            empty = not (diff_abs and os.path.isfile(diff_abs) and os.path.getsize(diff_abs) > 0)
            if empty:
                res["apply"] = "pass"                              # no-op baseline: nothing to apply
            else:
                chk = _git(["apply", "--index", "--check", diff_abs], cwd=wt)
                if chk.returncode != 0:
                    measured.append(f"candidate diff does not apply at HEAD: {chk.stderr.strip()}")
                else:
                    ap = _git(["apply", "--index", diff_abs], cwd=wt)
                    if ap.returncode == 0:
                        res["apply"] = "pass"
                    else:
                        measured.append(f"git apply --index failed: {ap.stderr.strip()}")

            if res["apply"] == "pass":
                paths, modes, binary = _staged_changes(wt)
                res["actual_paths"] = paths
                res["candidate_tree"] = (_git(["write-tree"], cwd=wt).stdout.strip() or None)

                target_regular = False
                if target_rel:
                    wp = os.path.join(wt, target_rel)
                    target_regular = os.path.isfile(wp) and not os.path.islink(wp)
                    res["patched_card_text"] = open(wp).read() if target_regular else None

                facts = {"declared": declared, "is_baseline": is_baseline, "mt": mt,
                         "allowlist": allowlist, "immutable": immutable, "actual": paths,
                         "modes": modes, "binary": binary, "base_tree": res["base_tree"],
                         "candidate_tree": res["candidate_tree"], "target_rel": target_rel,
                         "target_regular": target_regular}
                policy_reasons, flags = measured_policy(facts)
                res.update(flags)
                measured += policy_reasons

                res["conformance_passed"] = measure_conformance(wt)
                if not res["conformance_passed"]:
                    measured.append("trusted conformance (committed HEAD checker) failed against the patched workspace")
    finally:
        cleanup_worktree(root, wt)

    after = sha256_file(live_target) if live_target else None
    res["isolation_ok"] = before == after
    if not res["isolation_ok"]:
        measured.append("isolation invariant violated: the live tree changed during apply")

    res["measured_reasons"] = measured
    if res["preflight"] != "pass":
        res["reasons"] = [f"preflight: {r}" for r in pf_reasons] + measured
        res["verdict"] = "block"
    elif measured:
        res["reasons"] = measured
        res["verdict"] = "block"
    else:
        res["verdict"] = "allow"
    return res


def materialization_summary(mat):
    """The pinnable subset a downstream artifact references (no patched bytes)."""
    return {k: mat[k] for k in ("verdict", "preflight", "apply", "base_tree", "candidate_tree",
                                "declared_paths", "actual_paths", "paths_match", "allowlist_passed",
                                "baseline_unchanged", "regular_files_ok", "isolation_ok",
                                "conformance_passed", "reasons")}


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
    mat = materialize_candidate(campaign, candidate, root)
    entry = {
        "candidate_id": cid,
        "track": candidate.get("track"),
        "backend": backend,
        "gate": "allow" if mat["preflight"] == "pass" else "block",   # preflight only; cannot authorize
        "gate_reasons": mat["preflight_reasons"],
        "diff_applies": mat["apply"] == "pass",
        "isolation_ok": mat["isolation_ok"],
        "conformance_passed": mat["conformance_passed"],
        "materialization": materialization_summary(mat),
        "coverage_delta_vs_incumbent": None,
        "applied_verdict": mat["verdict"],
        "verdict_reasons": mat["reasons"],
        "promoted": False,
    }
    if mat["verdict"] != "allow":          # measured boundary is authoritative — not the patch gate
        return entry

    applied_scoreboard = scoreboard            # deterministic: frozen scorers don't read technique cards
    inc = RG.incumbent_eval(scoreboard)
    cand_eval = applied_candidate_eval(candidate, scoreboard, applied_scoreboard,
                                       mat["conformance_passed"], single_mutation=True)
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

    # ---- measured-boundary parity: every rejection a patch parser made must fall out of measured tree
    #      state. Pure (no git/conformance), so it directly proves the measured contract is faithful. ----
    mt = "skills/techniques/task-reframing/"
    card = mt + "SKILL.md"
    clean = {"declared": [card], "is_baseline": False, "mt": mt, "allowlist": [mt],
             "immutable": list(CC.DEFAULT_IMMUTABLE), "actual": [card], "modes": {card: "100644"},
             "binary": [], "base_tree": "AAA", "candidate_tree": "BBB", "target_rel": card,
             "target_regular": True}
    if measured_policy(clean)[0]:
        ok = False; print(f"[self-test] clean card variant must pass measured policy; got {measured_policy(clean)[0]}")

    adversarial = {
        "exec-bit mode change": dict(clean, modes={card: "100755"}),
        "symlink post-state": dict(clean, modes={card: "120000"}, target_regular=False),
        "gitlink/submodule post-state": dict(clean, modes={card: "160000"}, target_regular=False),
        "deletion of the card": dict(clean, modes={card: "000000"}, target_regular=False),
        "binary content": dict(clean, binary=[card]),
        "declared != actual paths": dict(clean, actual=[card, mt + "extra.md"], modes={card: "100644", mt + "extra.md": "100644"}),
        "out of mutation target": dict(clean, declared=["engine/routing.md"], actual=["engine/routing.md"],
                                       modes={"engine/routing.md": "100644"}, target_rel="engine/routing.md"),
        "immutable checker touch": dict(clean, declared=[card, "tools/check-conformance.py"],
                                        actual=[card, "tools/check-conformance.py"],
                                        modes={card: "100644", "tools/check-conformance.py": "100644"}),
        "mode-only on the checker": dict(clean, declared=["tools/check-conformance.py"],
                                         actual=["tools/check-conformance.py"], target_rel="tools/check-conformance.py",
                                         modes={"tools/check-conformance.py": "100755"}),
        "baseline that changed the tree": dict(clean, is_baseline=True),
        "non-baseline with no change": dict(clean, actual=[], modes={}, candidate_tree="AAA"),
    }
    parity_ok = True
    for label, facts in adversarial.items():
        if not measured_policy(facts)[0]:
            parity_ok = ok = False
            print(f"[self-test] measured policy MISSED: {label}")
    print("[self-test] measured-policy parity (mode/symlink/gitlink/delete/binary/mismatch/allowlist/"
          "immutable/baseline):", "ok" if parity_ok else "FAIL")

    # ---- measurement mechanism: _staged_changes reads paths/modes/binary from the STAGED index ----
    with tempfile.TemporaryDirectory() as repo:
        _git(["init", "--quiet"], cwd=repo)
        _git(["config", "user.email", "t@t"], cwd=repo)
        _git(["config", "user.name", "t"], cwd=repo)
        os.makedirs(os.path.join(repo, os.path.dirname(card)), exist_ok=True)
        with open(os.path.join(repo, card), "w") as fh:
            fh.write("line one\nline two\n")
        _git(["add", "-A"], cwd=repo)
        _git(["commit", "-m", "init", "--quiet"], cwd=repo)

        wt = tempfile.mkdtemp(prefix="phase10h0-selftest-wt-")
        try:
            _git(["worktree", "add", "--detach", "--quiet", wt, "HEAD"], cwd=repo)
            mod = f"--- a/{card}\n+++ b/{card}\n@@ -1,2 +1,3 @@\n line one\n line two\n+variant\n"
            dpath = os.path.join(repo, "mod.diff"); open(dpath, "w").write(mod)
            _git(["apply", "--index", dpath], cwd=wt)
            paths, modes, binary = _staged_changes(wt)
            mech_ok = paths == [card] and modes.get(card) == "100644" and binary == []
            if not mech_ok:
                ok = False; print(f"[self-test] _staged_changes mechanism wrong: {paths} {modes} {binary}")
            else:
                print("[self-test] _staged_changes reads modify (path + 100644, no binary) from the index: ok")
        finally:
            cleanup_worktree(repo, wt)

        wt2 = tempfile.mkdtemp(prefix="phase10h0-selftest-wt2-")
        try:
            _git(["worktree", "add", "--detach", "--quiet", wt2, "HEAD"], cwd=repo)
            modechg = f"diff --git a/{card} b/{card}\nold mode 100644\nnew mode 100755\n"
            mpath = os.path.join(repo, "mode.diff"); open(mpath, "w").write(modechg)
            _git(["apply", "--index", mpath], cwd=wt2)
            _, modes2, _ = _staged_changes(wt2)
            if modes2.get(card) != "100755":
                ok = False; print(f"[self-test] _staged_changes missed a mode-only change: {modes2}")
            else:
                print("[self-test] _staged_changes detects a mode-only change as 100755 from the index: ok")
        finally:
            cleanup_worktree(repo, wt2)

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
        print("[model backend] BLOCKED: re-routing against the patched workspace needs an LM in the loop, "
              "not configured here. The real-model path is the blind behavioral evaluator "
              "(run-behavioral-eval.py --backend model); use --backend deterministic for the model-free "
              "conformance signal. Recorded as non-success; no result is fabricated.")
        return 2     # NON-SUCCESS — never report a model run that did not happen as ok
    if not args.campaign:
        ap.print_help()
        return 2
    return run_cli(args.campaign, only_candidate=args.candidate, backend=args.backend)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
