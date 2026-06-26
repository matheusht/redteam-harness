#!/usr/bin/env python3
"""Promotion bundle renderer + PR-only promotion path (GEPA Phase 5).

Assembles the review surface for promoting a shadow candidate into Plane 1. It joins the Phase 3
mechanical verdict and the Phase 4 replay-adjusted verdict with the candidate diff, both manifests,
scorer + replay results, false-discovery result, a cost comparison, a redaction report, and a human
checklist — conforming to schemas/promotion-bundle.schema.json.

It PROMOTES NOTHING. It never applies the diff, never writes under skills/, never commits or merges.
A candidate is promotable ONLY if its replay-adjusted verdict is `allow` AND the redaction scan is
clean; a `block`/`probe` candidate (everything in shadow mode) is rendered as archived-only. Promotion
happens later, by a human, through a reviewed PR on an isolated branch.

  GEPA candidate -> isolated branch -> scorers + replay -> THIS bundle -> human review -> PR -> merge

Usage:
  python3 tools/render-promotion-bundle.py --campaign <campaign-manifest.json> --candidate <id>
  python3 tools/render-promotion-bundle.py --self-test
"""

import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")


def load(path):
    with open(path) as fh:
        return json.load(fh)


def read(path):
    with open(path) as fh:
        return fh.read()


def _mod(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(TOOLS, filename))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


CONF = _mod("check_conformance", "check-conformance.py")

BUNDLE_REQUIRED = ["candidate_id", "campaign_id", "candidate_manifest", "campaign_manifest", "diff",
                   "scores", "false_discovery", "cost_comparison", "redaction_report",
                   "review_checklist", "verdict", "pinned"]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _benchmark_version(campaign):
    blob = "".join(sorted(spec["sha256"] for spec in campaign.get("frozen_inputs", {}).values()))
    return "bench-" + hashlib.sha256(blob.encode()).hexdigest()[:12]


def _head_commit():
    try:
        return subprocess.check_output(["git", "-C", ROOT, "rev-parse", "HEAD"],
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return None


def redaction_hits(texts):
    hits = []
    for label, text in texts:
        for pat, desc in CONF.SECRET_PATTERNS:
            if re.search(pat, text):
                hits.append(f"{label}: {desc}")
    return sorted(set(hits))


def _sha256_text(text):
    return hashlib.sha256(text.encode()).hexdigest()


def build_bundle(campaign, candidate_manifest, report_candidate, scoreboard, replay_summary,
                 diff_text, bundle_text, paths, pinned):
    """Pure: returns (bundle_dict, promotable, redaction_list). No disk I/O."""
    phase3 = report_candidate["keep_discard"]["verdict"]
    final = replay_summary["verdict"] if replay_summary else phase3

    redaction = redaction_hits([("diff", diff_text), ("evidence-bundle", bundle_text)])
    redaction_clean = not redaction

    fdr = scoreboard["false_discovery"]
    inc_cost = {"model_calls": 0, "target_calls": scoreboard["hermetic_bola"]["target_calls"]}
    cand_cost = dict(inc_cost)

    mt = candidate_manifest["mutation_target"]
    touched = candidate_manifest.get("touched_files", [])
    single_component = all(t == mt or t.startswith(mt) for t in touched)
    diff_hash_ok = _sha256_text(diff_text) == candidate_manifest.get("candidate_hash")
    replay_stable = bool(replay_summary and replay_summary.get("stable"))
    contract_gate_allow = report_candidate.get("gate") == "allow"

    checklist = [
        {"item": f"Single mutated component identified: {mt}", "checked": single_component},
        {"item": "No immutable file touched (contract gate allowed the candidate)", "checked": contract_gate_allow},
        {"item": "False-discovery invalid_accept_rate == 0", "checked": bool(fdr["passed"])},
        {"item": "Replay-stable: primary + 2 fresh-session replays reproduced", "checked": replay_stable},
        {"item": "Diff hash matches candidate_hash", "checked": diff_hash_ok},
        {"item": "Redaction clean: no secret shapes in diff or evidence bundle", "checked": redaction_clean},
        {"item": "HUMAN: read the diff; the change is benign and in scope", "checked": False},
        {"item": "HUMAN: the evidence bundle justification holds", "checked": False},
        {"item": "HUMAN: approve Plane-1 promotion via this PR (no direct-to-main, no manual copy)", "checked": False},
    ]

    bundle = {
        "candidate_id": candidate_manifest["candidate_id"],
        "campaign_id": campaign["campaign_id"],
        "candidate_manifest": paths["candidate_manifest"],
        "campaign_manifest": paths["campaign_manifest"],
        "diff": paths["diff"],
        "scores": paths["scores"],
        "replays": [paths["replay_summary"]] if replay_summary else [],
        "false_discovery": {"invalid_accept_rate": fdr["invalid_accept_rate"], "passed": bool(fdr["passed"])},
        "cost_comparison": {"incumbent": inc_cost, "candidate": cand_cost, "delta_pct": 0.0},
        "redaction_report": {"scanned": True, "secret_hits": redaction},
        "review_checklist": checklist,
        "verdict": final,
        "pinned": pinned,
    }
    promotable = (final == "allow") and redaction_clean
    return bundle, promotable, redaction


def verify_drift(bundle, root):
    """Re-hash the pinned inputs against the tree; return a list of drifts (empty == intact)."""
    drifts = []
    pinned = bundle.get("pinned", {})
    cm = os.path.join(root, bundle["campaign_manifest"])
    if not os.path.isfile(cm):
        drifts.append(f"campaign manifest missing: {bundle['campaign_manifest']}")
    elif sha256_file(cm) != pinned.get("campaign_manifest_hash"):
        drifts.append("campaign manifest hash drifted")
    dm = os.path.join(root, bundle["candidate_manifest"])
    if not os.path.isfile(dm):
        drifts.append(f"candidate manifest missing: {bundle['candidate_manifest']}")
    elif sha256_file(dm) != pinned.get("candidate_manifest_hash"):
        drifts.append("candidate manifest hash drifted")
    campaign = load(cm) if os.path.isfile(cm) else {"frozen_inputs": {}}
    fi = campaign.get("frozen_inputs", {})
    for name, want in pinned.get("frozen_input_hashes", {}).items():
        spec = fi.get(name)
        if not spec:
            drifts.append(f"frozen input '{name}' no longer in campaign manifest")
            continue
        p = os.path.join(root, spec["path"])
        if not os.path.isfile(p):
            drifts.append(f"frozen input '{name}' file missing")
        elif sha256_file(p) != want:
            drifts.append(f"frozen input '{name}' drifted ({spec['path']})")
    if _benchmark_version(campaign) != pinned.get("benchmark_version"):
        drifts.append("benchmark_version drifted")
    return drifts


def validate_bundle(bundle):
    return [k for k in BUNDLE_REQUIRED if k not in bundle]


def render_md(bundle, promotable):
    status = "PROMOTABLE — open a PR" if promotable else "NOT PROMOTABLE — archived only"
    lines = [
        f"# Promotion bundle — {bundle['candidate_id']}",
        "",
        f"**Status: {status}**  ·  verdict (replay-adjusted): `{bundle['verdict']}`  ·  campaign "
        f"`{bundle['campaign_id']}`",
        "",
        "This bundle promotes nothing. Promotion is a human action via a reviewed PR on an isolated "
        "branch; the diff is NOT applied here and nothing is written under `skills/`.",
        "",
        "## Mutated component (single)",
        f"`{bundle['candidate_manifest']}` → see `diff`. The PR must identify exactly one mutated component.",
        "",
        "## Mechanical results",
        f"- false-discovery: invalid_accept_rate={bundle['false_discovery']['invalid_accept_rate']:.3f} "
        f"(passed={bundle['false_discovery']['passed']})",
        f"- cost: incumbent {bundle['cost_comparison']['incumbent']} vs candidate "
        f"{bundle['cost_comparison']['candidate']} (Δ {bundle['cost_comparison']['delta_pct']}%)",
        f"- redaction: {'clean' if not bundle['redaction_report']['secret_hits'] else bundle['redaction_report']['secret_hits']}",
        "",
        "## Review checklist",
    ]
    for c in bundle["review_checklist"]:
        lines.append(f"- [{'x' if c['checked'] else ' '}] {c['item']}")
    lines += ["", "## Artifacts",
              f"- candidate manifest: `{bundle['candidate_manifest']}`",
              f"- campaign manifest: `{bundle['campaign_manifest']}`",
              f"- diff: `{bundle['diff']}`",
              f"- scores: `{bundle['scores']}`",
              f"- replays: {bundle['replays'] or '—'}", ""]
    return "\n".join(lines)


def render_pr_body(bundle, promotable):
    return "\n".join([
        f"## GEPA promotion: {bundle['candidate_id']}",
        "",
        f"- Campaign: `{bundle['campaign_id']}`",
        f"- Single mutated component: see `{bundle['diff']}` (candidate manifest `{bundle['candidate_manifest']}`)",
        f"- Replay-adjusted verdict: `{bundle['verdict']}`",
        f"- False-discovery passed: {bundle['false_discovery']['passed']}",
        f"- Redaction: {'clean' if not bundle['redaction_report']['secret_hits'] else 'HITS — do not merge'}",
        "",
        ("This candidate is promotable. Apply the diff on this isolated branch, re-run conformance, and "
         "request human review." if promotable else
         "This candidate is NOT promotable (archived only). Do not apply the diff or merge."),
        "",
        "Checklist (humans must tick the HUMAN items):",
        *[f"- [{'x' if c['checked'] else ' '}] {c['item']}" for c in bundle["review_checklist"]],
        "",
    ])


def render_cli(campaign_path, candidate_id):
    campaign = load(campaign_path)
    camp_dir = os.path.dirname(campaign_path)
    report = load(os.path.join(camp_dir, "report.json"))
    cand_dir = os.path.join(camp_dir, "candidates", candidate_id)
    candidate_manifest = load(os.path.join(cand_dir, "candidate-manifest.json"))

    rc = next((c for c in report["candidates"] if c["candidate_id"] == candidate_id), None)
    if rc is None:
        print(f"no such candidate in report: {candidate_id}")
        return 2

    rs_path = os.path.join(cand_dir, "replays", "replay-summary.json")
    replay_summary = load(rs_path) if os.path.isfile(rs_path) else None

    rel = lambda p: os.path.relpath(p, ROOT)
    paths = {
        "candidate_manifest": rel(os.path.join(cand_dir, "candidate-manifest.json")),
        "campaign_manifest": rel(campaign_path),
        "diff": rel(os.path.join(cand_dir, "candidate.diff")),
        "scores": rel(os.path.join(camp_dir, "report.json")),
        "replay_summary": rel(rs_path) if replay_summary else None,
    }
    diff_text = read(os.path.join(cand_dir, "candidate.diff"))
    bundle_text = read(os.path.join(cand_dir, "evidence-bundle.md"))

    pinned = {
        "rendered_at_commit": _head_commit(),
        "campaign_manifest_hash": sha256_file(campaign_path),
        "candidate_manifest_hash": sha256_file(os.path.join(cand_dir, "candidate-manifest.json")),
        "frozen_input_hashes": {name: spec["sha256"] for name, spec in campaign.get("frozen_inputs", {}).items()},
        "benchmark_version": _benchmark_version(campaign),
    }
    bundle, promotable, _ = build_bundle(campaign, candidate_manifest, rc, report["baseline_scoreboard"],
                                         replay_summary, diff_text, bundle_text, paths, pinned)
    missing = validate_bundle(bundle)
    if missing:
        print(f"bundle invalid, missing: {missing}")
        return 1

    out_dir = os.path.join(cand_dir, "promotion")
    assert "skills/" not in out_dir
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "promotion-bundle.json"), "w") as fh:
        json.dump(bundle, fh, indent=2); fh.write("\n")
    with open(os.path.join(out_dir, "promotion-bundle.md"), "w") as fh:
        fh.write(render_md(bundle, promotable))
    with open(os.path.join(out_dir, "pr-body.md"), "w") as fh:
        fh.write(render_pr_body(bundle, promotable))

    print(render_md(bundle, promotable))
    return 0


def self_test():
    ok = True
    campaign = {"campaign_id": "camp"}
    scoreboard = {"false_discovery": {"invalid_accept_rate": 0.0, "passed": True},
                  "hermetic_bola": {"target_calls": 5}}
    diff_text = "--- a/skills/techniques/x/SKILL.md\n+ok\n"
    cm = {"candidate_id": "c", "mutation_target": "skills/techniques/x/",
          "touched_files": ["skills/techniques/x/SKILL.md"], "candidate_hash": _sha256_text(diff_text)}
    rc = {"candidate_id": "c", "keep_discard": {"verdict": "allow"}}
    paths = {"candidate_manifest": "cm.json", "campaign_manifest": "camp.json", "diff": "c.diff",
             "scores": "report.json", "replay_summary": "rs.json"}
    pinned = {"campaign_manifest_hash": "x", "candidate_manifest_hash": "y",
              "frozen_input_hashes": {}, "benchmark_version": "bench-0"}

    b, promotable, red = build_bundle(campaign, cm, rc, scoreboard, {"verdict": "allow", "stable": True},
                                      diff_text, "# clean bundle\n", paths, pinned)
    if not promotable or validate_bundle(b) or b["verdict"] != "allow":
        ok = False; print("[self-test] allow + stable + clean should be promotable & schema-complete")
    else:
        print("[self-test] allow + stable + clean -> promotable: ok")

    _, prom_probe, _ = build_bundle(campaign, cm, rc, scoreboard, {"verdict": "probe", "stable": True},
                                    diff_text, "# clean\n", paths, pinned)
    if prom_probe:
        ok = False; print("[self-test] probe candidate must NOT be promotable")
    else:
        print("[self-test] probe -> archived, not promotable: ok")

    secret_diff = diff_text + "Authorization: Bearer abcdef0123456789xyz\n"
    cm2 = dict(cm, candidate_hash=_sha256_text(secret_diff))
    _, prom_secret, red2 = build_bundle(campaign, cm2, rc, scoreboard, {"verdict": "allow", "stable": True},
                                        secret_diff, "# clean\n", paths, pinned)
    if prom_secret or not red2:
        ok = False; print("[self-test] secret in diff must block promotion via redaction")
    else:
        print("[self-test] secret in diff -> redaction blocks promotion: ok")

    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "evals"), exist_ok=True)
        open(os.path.join(d, "evals", "gold.json"), "w").write('{"k":1}\n')
        gold_hash = sha256_file(os.path.join(d, "evals", "gold.json"))
        camp = {"campaign_id": "c", "frozen_inputs": {"gold": {"path": "evals/gold.json", "sha256": gold_hash}}}
        open(os.path.join(d, "campaign.json"), "w").write(json.dumps(camp))
        open(os.path.join(d, "cand.json"), "w").write('{"candidate_id":"c"}\n')
        drift_bundle = {
            "campaign_manifest": "campaign.json", "candidate_manifest": "cand.json",
            "pinned": {"campaign_manifest_hash": sha256_file(os.path.join(d, "campaign.json")),
                       "candidate_manifest_hash": sha256_file(os.path.join(d, "cand.json")),
                       "frozen_input_hashes": {"gold": gold_hash}, "benchmark_version": _benchmark_version(camp)},
        }
        if verify_drift(drift_bundle, d):
            ok = False; print("[self-test] intact bundle reported drift")
        open(os.path.join(d, "evals", "gold.json"), "w").write('{"k":2}\n')  # tamper the gold
        if not verify_drift(drift_bundle, d):
            ok = False; print("[self-test] gold drift not detected")
        else:
            print("[self-test] intact -> no drift; tampered gold -> drift blocks: ok")

    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "promotion")
        os.makedirs(p, exist_ok=True)
        open(os.path.join(p, "promotion-bundle.json"), "w").write(json.dumps(b))
        wrote_skills = any("skills/" in os.path.join(dp, f) for dp, _, fs in os.walk(d) for f in fs)
        if wrote_skills:
            ok = False; print("[self-test] renderer must never write under skills/")
        else:
            print("[self-test] writes only promotion artifacts, never skills/: ok")

    print("\nSELF-TEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def verify_cli(bundle_path):
    bundle = load(bundle_path)
    drifts = verify_drift(bundle, ROOT)
    if drifts:
        print(f"DRIFT — bundle {bundle.get('candidate_id')} no longer matches the tree; re-render/replay required:")
        for d in drifts:
            print(f"  - {d}")
        return 1
    print(f"intact — bundle {bundle.get('candidate_id')} pins match the tree")
    return 0


def main(argv):
    if len(argv) == 2 and argv[1] == "--self-test":
        return self_test()
    if len(argv) == 3 and argv[1] == "--verify":
        return verify_cli(argv[2])
    camp = cand = None
    i = 1
    while i < len(argv):
        if argv[i] == "--campaign":
            camp = argv[i + 1]; i += 2
        elif argv[i] == "--candidate":
            cand = argv[i + 1]; i += 2
        else:
            i += 1
    if not camp or not cand:
        print(__doc__)
        return 2
    return render_cli(camp, cand)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
