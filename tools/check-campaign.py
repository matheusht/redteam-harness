#!/usr/bin/env python3
"""Campaign / candidate contract gate (GEPA Phase 1).

Stdlib-only. Enforces the manifest contracts (schemas/campaign-manifest.schema.json,
schemas/candidate-manifest.schema.json) BEFORE any optimizer output is trusted. This is the
tamper-detection and scope fence that lets a shadow campaign run without letting a candidate quietly
change what 'winning' means.

A candidate is BLOCKED if any of these hold:
  - it touches a file outside its single declared mutation_target (undeclared mutation);
  - it touches an immutable file (evaluator, oracle, routing gold, crosswalk, casebooks, corpora,
    hermetic targets, schemas, budgets) — the 'what winning means' set;
  - its declared budget differs from the campaign budget (no buying extra budget);
  - a frozen campaign input's sha256 has drifted (benchmark/evaluator tamper);
  - its diff hash does not match the diff file (candidate tamper);
  - its evidence bundle is missing;
  - it is a baseline but is not a no-op (a control must touch nothing).

A no-op baseline (is_baseline=true, touched_files empty) is ALLOWED — it is the retained control.

Usage:
  python3 tools/check-campaign.py --campaign <campaign.json> --candidate <candidate.json>
  python3 tools/check-campaign.py --self-test
"""

import hashlib
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Built-in immutable set: enforced regardless of what a campaign manifest declares. These are the
# files that define acceptance — a candidate that edits any of them is gaming the evaluator.
DEFAULT_IMMUTABLE = [
    "tools/score-routing.py",
    "tools/score-false-discovery.py",
    "tools/run-qualification.py",
    "tools/run-hermetic-bola.py",
    "tools/check-conformance.py",
    "tools/check-campaign.py",
    "evals/routing/gold/",
    "evals/qualification/crosswalk.json",
    "evals/hermetic/targets/",
    "fixtures/false-discovery/",
    "fixtures/adversarial-candidates/",
    "casebooks/",
    "schemas/",
]


def load(path):
    with open(path) as fh:
        return json.load(fh)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _under(path, prefix):
    """True if path is the prefix file, or sits under the prefix directory."""
    if prefix.endswith("/"):
        return path.startswith(prefix)
    return path == prefix or path.startswith(prefix + "/")


def gate(campaign, candidate, root):
    """Return (verdict, reasons). verdict is 'allow' or 'block'."""
    reasons = []

    if candidate.get("campaign_id") != campaign.get("campaign_id"):
        reasons.append(f"campaign_id mismatch: candidate {candidate.get('campaign_id')} != {campaign.get('campaign_id')}")

    targets = {t["mutation_target"] for t in campaign.get("tracks", [])}
    mt = candidate.get("mutation_target")
    if mt not in targets:
        reasons.append(f"mutation_target '{mt}' is not a declared track target {sorted(targets)}")

    touched = candidate.get("touched_files", [])
    is_baseline = bool(candidate.get("is_baseline"))

    if is_baseline and touched:
        reasons.append("baseline candidate must be a no-op (touched_files must be empty)")

    if mt:
        stray = [f for f in touched if not _under(f, mt)]
        if stray:
            reasons.append(f"touches files outside mutation_target '{mt}': {stray}")

    immutable = list(DEFAULT_IMMUTABLE) + list(campaign.get("immutable", []))
    leaked = [f for f in touched if any(_under(f, p) for p in immutable)]
    if leaked:
        reasons.append(f"touches immutable (evaluator/gold/casebook/budget/schema) files: {leaked}")

    cb = candidate.get("budget")
    if cb is not None and cb != campaign.get("budgets"):
        reasons.append("candidate budget differs from campaign budget")

    eb = candidate.get("evidence_bundle")
    if not eb or not os.path.isfile(os.path.join(root, eb)):
        reasons.append(f"evidence bundle missing: {eb}")

    diff = candidate.get("diff")
    diff_path = os.path.join(root, diff) if diff else None
    if not diff or not os.path.isfile(diff_path):
        if not is_baseline:
            reasons.append(f"diff missing: {diff}")
    else:
        actual = sha256_file(diff_path)
        if actual != candidate.get("candidate_hash"):
            reasons.append("candidate_hash does not match diff contents (tamper)")

    for name, spec in campaign.get("frozen_inputs", {}).items():
        p = os.path.join(root, spec.get("path", ""))
        if not os.path.isfile(p):
            reasons.append(f"frozen input '{name}' missing: {spec.get('path')}")
        elif sha256_file(p) != spec.get("sha256"):
            reasons.append(f"frozen input '{name}' drifted ({spec.get('path')})")

    return ("block" if reasons else "allow"), reasons


def report(campaign, candidate, root):
    verdict, reasons = gate(campaign, candidate, root)
    cid = candidate.get("candidate_id", "?")
    print(f"candidate {cid}: {verdict.upper()}")
    for r in reasons:
        print(f"  - {r}")
    return verdict == "allow"


# ---- self-test: build a tmp workspace and assert each criterion blocks/allows ----

def _write(root, rel, text):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as fh:
        fh.write(text)
    return p


def self_test():
    ok = True
    with tempfile.TemporaryDirectory() as root:
        frozen_rel = "evals/routing/gold/case-x.gold.json"
        _write(root, frozen_rel, '{"case":"x"}\n')
        frozen_hash = sha256_file(os.path.join(root, frozen_rel))

        diff_rel = "evals/gepa-shadow/c/candidate.diff"
        _write(root, diff_rel, "--- a/skills/techniques/task-reframing/SKILL.md\n+++ b\n+variant\n")
        diff_hash = sha256_file(os.path.join(root, diff_rel))
        _write(root, "evals/gepa-shadow/c/evidence-bundle.md", "# why\n")

        campaign = {
            "campaign_id": "camp-1",
            "created": "2026-06-26",
            "tracks": [{"name": "task-reframing", "mutation_target": "skills/techniques/task-reframing/", "kind": "existing-card-variant"}],
            "mutable_allowlist": ["skills/techniques/task-reframing/"],
            "immutable": [],
            "frozen_inputs": {"routing-gold-x": {"path": frozen_rel, "sha256": frozen_hash}},
            "budgets": {"model_calls": 10, "target_calls": 20, "tokens": None},
            "benchmark_set": ["routing:case-x"],
        }
        base = {
            "candidate_id": "cand-ok", "campaign_id": "camp-1", "parent": "baseline",
            "track": "task-reframing", "mutation_target": "skills/techniques/task-reframing/",
            "touched_files": ["skills/techniques/task-reframing/SKILL.md"],
            "diff": diff_rel, "candidate_hash": diff_hash,
            "evidence_bundle": "evals/gepa-shadow/c/evidence-bundle.md",
        }

        def expect(label, cand, want, camp=campaign):
            nonlocal ok
            verdict, reasons = gate(camp, cand, root)
            good = verdict == want
            print(f"[self-test] {label}: {verdict} (want {want}) {'ok' if good else 'MISMATCH ' + str(reasons)}")
            if not good:
                ok = False

        expect("clean candidate allows", base, "allow")

        undeclared = dict(base, candidate_id="cand-undeclared",
                          touched_files=["skills/techniques/task-reframing/SKILL.md", "engine/routing.md"])
        expect("undeclared file blocks", undeclared, "block")

        immutable = dict(base, candidate_id="cand-immutable",
                         touched_files=["skills/techniques/task-reframing/SKILL.md", "evals/routing/gold/case-x.gold.json"])
        expect("immutable touch blocks", immutable, "block")

        budget = dict(base, candidate_id="cand-budget", budget={"model_calls": 999, "target_calls": 20, "tokens": None})
        expect("budget change blocks", budget, "block")

        nobundle = dict(base, candidate_id="cand-nobundle", evidence_bundle="evals/gepa-shadow/c/missing.md")
        expect("missing evidence bundle blocks", nobundle, "block")

        tamper = dict(base, candidate_id="cand-tamper", candidate_hash="deadbeef")
        expect("diff hash tamper blocks", tamper, "block")

        baseline = {
            "candidate_id": "cand-baseline", "campaign_id": "camp-1", "parent": "baseline",
            "track": "task-reframing", "mutation_target": "skills/techniques/task-reframing/",
            "touched_files": [], "diff": diff_rel, "candidate_hash": diff_hash,
            "evidence_bundle": "evals/gepa-shadow/c/evidence-bundle.md", "is_baseline": True,
        }
        expect("no-op baseline allows", baseline, "allow")

        baseline_dirty = dict(baseline, candidate_id="cand-baseline-dirty",
                              touched_files=["skills/techniques/task-reframing/SKILL.md"])
        expect("baseline that mutates blocks", baseline_dirty, "block")

        drifted = dict(campaign, frozen_inputs={"routing-gold-x": {"path": frozen_rel, "sha256": "0" * 64}})
        expect("frozen-input drift blocks", base, "block", camp=drifted)

    print("\nSELF-TEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv):
    if len(argv) == 2 and argv[1] == "--self-test":
        return self_test()
    camp = cand = None
    i = 1
    while i < len(argv):
        if argv[i] == "--campaign":
            camp = load(argv[i + 1]); i += 2
        elif argv[i] == "--candidate":
            cand = load(argv[i + 1]); i += 2
        else:
            i += 1
    if camp is None or cand is None:
        print(__doc__)
        return 2
    return 0 if report(camp, cand, ROOT) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
