#!/usr/bin/env python3
"""Build the canonical behavioral campaign deterministically from HEAD (GEPA Phase 10F).

Generates real `git apply`-able candidate diffs + canonical candidate manifests + a campaign manifest
(with frozen-input hashes), so `tools/run-behavioral-eval.py` consumes canonical campaign/candidate
contracts and the fixtures are reproducible. Diffs are generated against HEAD; if HEAD later changes,
the pinned hashes in a run manifest make the drift detectable and the candidate's diff stops applying.

Usage:  python3 tools/build-behavioral-campaign.py
"""

import difflib
import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAMP_ID = "behavioral-canonical-2026-06-26"
CAMP_DIR = os.path.join(ROOT, "evals", "behavioral", "campaigns", CAMP_ID)


def head_text(repo_rel):
    try:
        return subprocess.check_output(["git", "-C", ROOT, "show", f"HEAD:{repo_rel}"],
                                       stderr=subprocess.DEVNULL).decode()
    except Exception:
        return ""


def sha256_text(t):
    return hashlib.sha256((t or "").encode()).hexdigest()


def sha256_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.isfile(p) else None


def udiff(repo_rel, old, new):
    lines = list(difflib.unified_diff(old.splitlines(), new.splitlines(),
                                      fromfile=f"a/{repo_rel}" if old else "/dev/null",
                                      tofile=f"b/{repo_rel}", lineterm=""))
    return ("\n".join(lines) + "\n") if lines else ""


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(text)


VARIANTS = {
    "efficient": "\n\n## Behavioral variant: oracle-first stop rule\nName the exact oracle condition, then use an oracle-first stop rule with one decisive probe before escalating a suspected win.\n",
    "decomposition": "\n\n## Behavioral variant: chunk ledger\nRecord a ledger row per chunk and recompose only after an oracle check and a fresh-session replay.\n",
    "degraded": "\n\n## DEGRADED CONTROL (test fixture, promotion-excluded)\nAlways confirm a suspected win; skip the negative control and skip replay.\n",
}

CANDIDATES = [
    {"id": "cand-baseline", "technique": "task-reframing", "kind": "baseline", "eligibility": "control"},
    {"id": "cand-efficient-task-reframing", "technique": "task-reframing", "kind": "variant", "variant": "efficient", "eligibility": "candidate"},
    {"id": "cand-decomposition", "technique": "decomposition", "kind": "variant", "variant": "decomposition", "eligibility": "candidate"},
    {"id": "cand-degraded", "technique": "task-reframing", "kind": "variant", "variant": "degraded", "eligibility": "test_fixture"},
    {"id": "cand-invalid-immutable", "technique": "task-reframing", "kind": "invalid_immutable", "eligibility": "control"},
]

BUDGETS = {"model_calls": 60, "target_calls": 120, "tokens": None}


def technique_target(technique):
    return f"skills/techniques/{technique}/SKILL.md"


def build():
    frozen_inputs = {}
    for name, rel in [("episodes:task-reframing", "evals/behavioral/episodes/task-reframing.json"),
                      ("episodes:decomposition", "evals/behavioral/episodes/decomposition.json"),
                      ("scorer:score-candidate", "tools/score-candidate.py"),
                      ("gate:check-campaign", "tools/check-campaign.py"),
                      ("adapter:researcher_adapter", "tools/researcher_adapter.py")]:
        frozen_inputs[name] = {"path": rel, "sha256": sha256_file(os.path.join(ROOT, rel))}

    campaign_candidates = []
    for c in CANDIDATES:
        cid, technique = c["id"], c["technique"]
        cdir = os.path.join(CAMP_DIR, "candidates", cid)
        target = technique_target(technique)
        diff_rel = f"evals/behavioral/campaigns/{CAMP_ID}/candidates/{cid}/candidate.diff"
        bundle_rel = f"evals/behavioral/campaigns/{CAMP_ID}/candidates/{cid}/evidence-bundle.md"
        manifest_rel = f"evals/behavioral/campaigns/{CAMP_ID}/candidates/{cid}/candidate-manifest.json"

        if c["kind"] == "baseline":
            diff_text, touched, is_baseline = "", [], True
        elif c["kind"] == "invalid_immutable":
            gold = "evals/routing/gold/case-a.gold.json"
            diff_text = f"--- a/{gold}\n+++ b/{gold}\n@@\n-  \"case\": \"case-a\"\n+  \"case\": \"case-a\"\n"
            touched, is_baseline = [gold], False
        else:
            old = head_text(target)
            new = old.rstrip() + VARIANTS[c["variant"]]
            diff_text = udiff(target, old, new)
            touched, is_baseline = [target], False

        write(os.path.join(cdir, "candidate.diff"), diff_text)
        write(os.path.join(cdir, "evidence-bundle.md"),
              f"# Evidence bundle — {cid}\n\n- campaign: `{CAMP_ID}`\n- technique: `{technique}`\n"
              f"- mutation target: `{technique_target(technique)}`\n- eligibility: `{c['eligibility']}`\n\n"
              "Behavioral candidate. Diff is applied only in an isolated worktree by the evaluator; "
              "it is never applied to Plane 1 and cannot promote without a real-model qualification + PR.\n")
        manifest = {
            "candidate_id": cid, "campaign_id": CAMP_ID, "parent": "incumbent",
            "track": technique, "technique": technique, "eligibility": c["eligibility"],
            "mutation_target": technique_target(technique).rsplit("/", 1)[0] + "/",
            "touched_files": touched, "diff": diff_rel,
            "candidate_hash": sha256_text(diff_text), "evidence_bundle": bundle_rel,
            "budget": BUDGETS,
        }
        if is_baseline:
            manifest["is_baseline"] = True
        write(os.path.join(cdir, "candidate-manifest.json"), json.dumps(manifest, indent=2) + "\n")
        campaign_candidates.append({"candidate_id": cid, "manifest": manifest_rel, "eligibility": c["eligibility"]})

    campaign = {
        "campaign_id": CAMP_ID, "created": "2026-06-26",
        "note": "Canonical behavioral campaign (Phase 10F). Built deterministically from HEAD by "
                "tools/build-behavioral-campaign.py. Consumed by tools/run-behavioral-eval.py with the "
                "canonical contract gate + measured patched-workspace conformance.",
        "tracks": [{"name": "task-reframing", "mutation_target": "skills/techniques/task-reframing/", "kind": "existing-card-variant"},
                   {"name": "decomposition", "mutation_target": "skills/techniques/decomposition/", "kind": "existing-card-variant"}],
        "mutable_allowlist": ["skills/techniques/task-reframing/", "skills/techniques/decomposition/"],
        "immutable": ["engine/", "skills/oracles/", "skills/patterns/", "skills/vulns/"],
        "frozen_inputs": frozen_inputs, "budgets": BUDGETS,
        "behavioral_budget": {"max_probes": 6}, "seed": "behavioral-canonical-2026-06-26-seed-1",
        "benchmark_set": ["behavioral:task-reframing", "behavioral:decomposition"],
        "candidates": campaign_candidates,
    }
    write(os.path.join(CAMP_DIR, "campaign-manifest.json"), json.dumps(campaign, indent=2) + "\n")
    print(f"built {CAMP_ID}: {len(campaign_candidates)} candidates at {os.path.relpath(CAMP_DIR, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(build())
