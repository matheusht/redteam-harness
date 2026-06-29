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
  - an autoresearch train/held split is malformed or held/train frozen inputs drift.

A no-op baseline (is_baseline=true, touched_files empty) is ALLOWED — it is the retained control.

Usage:
  python3 tools/check-campaign.py --campaign <campaign.json> --candidate <candidate.json>
  python3 tools/check-campaign.py --self-test
"""

import hashlib
import json
import os
import re
import subprocess
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


def _rename_paths(p):
    """A numstat path may encode a rename as 'old => new' or 'pre/{old => new}/post'."""
    if "=>" not in p:
        return {p}
    p = p.replace("{", "").replace("}", "")
    if "{" not in p and " => " in p and "/" not in p.split(" => ")[0].split("/")[-1]:
        pass
    out = set()
    # generic: split on ' => ', recombine brace context if present
    if "{" in p or "/" in p:
        # best-effort: take both sides verbatim
        left, right = p.split(" => ", 1)
        out.add(left.strip())
        out.add(right.strip())
    else:
        left, right = p.split(" => ", 1)
        out.add(left.strip())
        out.add(right.strip())
    return {x for x in out if x}


def git_patch_analysis(diff_path, root):
    """Derive touched paths and detect UNSUPPORTED patch forms using git's own parser. The header-only
    parser missed mode-only, binary, rename, copy, and symlink patches — a candidate could change a
    file's mode (e.g. make the conformance checker executable) with a patch that has no ---/+++ headers
    and so derived no paths. Returns (paths, unsupported_reasons). Fail closed: callers must block on
    any unsupported reason and on a non-empty patch that yields no paths."""
    paths, unsupported = set(), []
    num = subprocess.run(["git", "-C", root, "apply", "--numstat", diff_path], capture_output=True, text=True)
    if num.returncode == 0:
        for ln in num.stdout.splitlines():
            parts = ln.split("\t")
            if len(parts) == 3:
                added, removed, p = parts
                if added == "-" and removed == "-":
                    unsupported.append(f"binary patch: {p}")
                paths |= _rename_paths(p)
    else:
        unsupported.append(f"git could not parse the patch: {num.stderr.strip()[:120]}")
    summ = subprocess.run(["git", "-C", root, "apply", "--summary", diff_path], capture_output=True, text=True)
    for ln in summ.stdout.splitlines():
        t = ln.strip()
        if t.startswith("rename ") or t.startswith("copy ") or t.startswith("mode change"):
            unsupported.append(t)
        if "120000" in t:
            unsupported.append(f"symlink: {t}")
    text = open(diff_path).read()
    for ln in text.splitlines():
        m = re.match(r"diff --git a/(.+?) b/(.+)$", ln)
        if m:
            paths.add(m.group(1)); paths.add(m.group(2))
        if ln.startswith("--- ") or ln.startswith("+++ "):
            p = ln[4:].split("\t")[0].strip()
            if p not in ("/dev/null", ""):
                paths.add(p[2:] if p[:2] in ("a/", "b/") else p)
        if ln.startswith("old mode") or ln.startswith("new mode"):
            unsupported.append("mode change")
        if ln.startswith("rename from") or ln.startswith("rename to"):
            unsupported.append("rename")
        if ln.startswith("copy from") or ln.startswith("copy to"):
            unsupported.append("copy")
        if ln.startswith("GIT binary patch") or ln.startswith("Binary files"):
            unsupported.append("binary patch")
        if "120000" in ln:
            unsupported.append("symlink mode")
    return {p for p in paths if p and p != "/dev/null"}, sorted(set(unsupported))


def gate(campaign, candidate, root):
    """Return (verdict, reasons). verdict is 'allow' or 'block'."""
    reasons = []
    reasons.extend(split_contract_problems(campaign))

    if candidate.get("campaign_id") != campaign.get("campaign_id"):
        reasons.append(f"campaign_id mismatch: candidate {candidate.get('campaign_id')} != {campaign.get('campaign_id')}")

    targets = {t["mutation_target"] for t in campaign.get("tracks", [])}
    mt = candidate.get("mutation_target")
    if mt not in targets:
        reasons.append(f"mutation_target '{mt}' is not a declared track target {sorted(targets)}")

    declared = set(candidate.get("touched_files", []))
    is_baseline = bool(candidate.get("is_baseline"))

    if is_baseline and declared:
        reasons.append("baseline candidate must be a no-op (touched_files must be empty)")

    # Derive the diff's ACTUAL paths and require the declaration matches exactly. Then run the
    # mutation-target / immutable checks against the UNION, so a file hidden from touched_files but
    # present in the diff still blocks.
    diff = candidate.get("diff")
    diff_path = os.path.join(root, diff) if diff else None
    derived = set()
    if not diff or not os.path.isfile(diff_path):
        if not is_baseline:
            reasons.append(f"diff missing: {diff}")
    else:
        if sha256_file(diff_path) != candidate.get("candidate_hash"):
            reasons.append("candidate_hash does not match diff contents (tamper)")
        size = os.path.getsize(diff_path)
        if is_baseline:
            if size != 0:
                reasons.append("baseline candidate diff must be byte-empty")
        else:
            if size == 0:
                reasons.append("non-baseline candidate diff is empty (fail closed)")
            derived, unsupported = git_patch_analysis(diff_path, root)
            if unsupported:
                reasons.append(f"unsupported patch form(s) — mode/binary/rename/copy/symlink rejected: {unsupported}")
            if not derived:
                reasons.append("diff derives no touched paths (fail closed)")
            if derived != declared:
                reasons.append(f"declared touched_files {sorted(declared)} do not match diff-derived paths "
                               f"{sorted(derived)} (a candidate cannot hide edits from the manifest)")

    effective = declared | derived
    if mt:
        stray = sorted(f for f in effective if not _under(f, mt))
        if stray:
            reasons.append(f"touches files outside mutation_target '{mt}': {stray}")

    frozen_paths = [spec.get("path") for spec in campaign.get("frozen_inputs", {}).values() if spec.get("path")]
    immutable = list(DEFAULT_IMMUTABLE) + list(campaign.get("immutable", [])) + frozen_paths
    leaked = sorted(f for f in effective if any(_under(f, p) for p in immutable))
    if leaked:
        reasons.append(f"touches immutable (evaluator/gold/casebook/budget/schema) files: {leaked}")

    cb = candidate.get("budget")
    if cb is not None and cb != campaign.get("budgets"):
        reasons.append("candidate budget differs from campaign budget")

    eb = candidate.get("evidence_bundle")
    if not eb or not os.path.isfile(os.path.join(root, eb)):
        reasons.append(f"evidence bundle missing: {eb}")

    for name, spec in campaign.get("frozen_inputs", {}).items():
        p = os.path.join(root, spec.get("path", ""))
        if not os.path.isfile(p):
            reasons.append(f"frozen input '{name}' missing: {spec.get('path')}")
        elif sha256_file(p) != spec.get("sha256"):
            reasons.append(f"frozen input '{name}' drifted ({spec.get('path')})")

    return ("block" if reasons else "allow"), reasons


def split_contract_problems(campaign):
    """Validate optional Track-B autoresearch split metadata.

    Shape:
      "autoresearch_splits": {
        "reflection_train": ["episodes:task-reframing"],
        "held_eval": ["episodes:decomposition"]
      }

    Split ids reference `frozen_inputs` keys, not file paths, so hash pinning remains single-sourced.
    """
    split = campaign.get("autoresearch_splits")
    if split is None:
        return []
    problems = []
    train = split.get("reflection_train")
    held = split.get("held_eval")
    frozen = set(campaign.get("frozen_inputs", {}).keys())
    if not isinstance(train, list) or not train:
        problems.append("autoresearch_splits.reflection_train must be a non-empty list of frozen_input keys")
        train = []
    if not isinstance(held, list) or not held:
        problems.append("autoresearch_splits.held_eval must be a non-empty list of frozen_input keys")
        held = []
    missing = sorted((set(train) | set(held)) - frozen)
    if missing:
        problems.append(f"autoresearch_splits reference unknown frozen_inputs: {missing}")
    overlap = sorted(set(train) & set(held))
    if overlap:
        problems.append(f"autoresearch_splits train/held overlap: {overlap}")
    return problems


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


def _diff_for(paths):
    """A well-formed multi-file unified diff touching exactly `paths`."""
    out = []
    for p in paths:
        out += [f"--- a/{p}", f"+++ b/{p}", "@@ -1 +1,2 @@", " base", "+variant"]
    return ("\n".join(out) + "\n") if out else ""


CARD = "skills/techniques/task-reframing/SKILL.md"


def self_test():
    ok = True
    with tempfile.TemporaryDirectory() as root:
        subprocess.run(["git", "-C", root, "init", "-q"], check=False)   # git's patch parser needs a repo
        frozen_rel = "evals/routing/gold/case-x.gold.json"
        _write(root, frozen_rel, '{"case":"x"}\n')
        frozen_hash = sha256_file(os.path.join(root, frozen_rel))
        bundle = "evals/c/evidence-bundle.md"
        _write(root, bundle, "# why\n")

        def mkdiff(name, paths):
            rel = f"evals/c/{name}.diff"
            _write(root, rel, _diff_for(paths))
            return rel, sha256_file(os.path.join(root, rel))

        card_diff, card_h = mkdiff("card", [CARD])

        campaign = {
            "campaign_id": "camp-1", "created": "2026-06-26",
            "tracks": [{"name": "task-reframing", "mutation_target": "skills/techniques/task-reframing/", "kind": "existing-card-variant"}],
            "mutable_allowlist": ["skills/techniques/task-reframing/"], "immutable": [],
            "frozen_inputs": {"routing-gold-x": {"path": frozen_rel, "sha256": frozen_hash}},
            "autoresearch_splits": {"reflection_train": ["routing-gold-x"], "held_eval": []},
            "budgets": {"model_calls": 10, "target_calls": 20, "tokens": None},
            "benchmark_set": ["routing:case-x"],
        }
        campaign["autoresearch_splits"] = {
            "reflection_train": ["routing-gold-x"],
            "held_eval": ["held-x"],
        }
        held_rel = "evals/behavioral/episodes/held-x.json"
        _write(root, held_rel, '{"episode":"held"}\n')
        campaign["frozen_inputs"]["held-x"] = {"path": held_rel, "sha256": sha256_file(os.path.join(root, held_rel))}
        base = {
            "candidate_id": "cand-ok", "campaign_id": "camp-1", "parent": "baseline",
            "track": "task-reframing", "mutation_target": "skills/techniques/task-reframing/",
            "touched_files": [CARD], "diff": card_diff, "candidate_hash": card_h, "evidence_bundle": bundle,
        }

        def expect(label, cand, want, camp=campaign):
            nonlocal ok
            verdict, reasons = gate(camp, cand, root)
            good = verdict == want
            print(f"[self-test] {label}: {verdict} (want {want}) {'ok' if good else 'MISMATCH ' + str(reasons)}")
            if not good:
                ok = False

        expect("clean candidate allows", base, "allow")

        stray_diff, stray_h = mkdiff("stray", [CARD, "engine/routing.md"])
        expect("undeclared (out-of-target) file blocks",
               dict(base, candidate_id="cand-stray", touched_files=[CARD, "engine/routing.md"],
                    diff=stray_diff, candidate_hash=stray_h), "block")

        imm_diff, imm_h = mkdiff("imm", [CARD, frozen_rel])
        expect("declared immutable touch blocks",
               dict(base, candidate_id="cand-immutable", touched_files=[CARD, frozen_rel],
                    diff=imm_diff, candidate_hash=imm_h), "block")

        # P0: a candidate whose diff edits the conformance checker while declaring ONLY the card.
        p0_diff, p0_h = mkdiff("p0", [CARD, "tools/check-conformance.py"])
        expect("P0: diff edits an immutable checker but declares only the card -> block",
               dict(base, candidate_id="cand-p0-hidden", touched_files=[CARD],
                    diff=p0_diff, candidate_hash=p0_h), "block")

        # touched_files claims a file the diff does not actually touch.
        expect("declared != diff-derived paths blocks",
               dict(base, candidate_id="cand-overdeclare", touched_files=[CARD, "engine/routing.md"]), "block")

        expect("budget change blocks", dict(base, candidate_id="cand-budget",
               budget={"model_calls": 999, "target_calls": 20, "tokens": None}), "block")
        expect("missing evidence bundle blocks", dict(base, candidate_id="cand-nobundle",
               evidence_bundle="evals/c/missing.md"), "block")
        expect("diff hash tamper blocks", dict(base, candidate_id="cand-tamper", candidate_hash="deadbeef"), "block")

        empty_diff, empty_h = mkdiff("empty", [])
        baseline = {
            "candidate_id": "cand-baseline", "campaign_id": "camp-1", "parent": "baseline",
            "track": "task-reframing", "mutation_target": "skills/techniques/task-reframing/",
            "touched_files": [], "diff": empty_diff, "candidate_hash": empty_h,
            "evidence_bundle": bundle, "is_baseline": True,
        }
        expect("no-op baseline allows", baseline, "allow")
        expect("baseline that mutates blocks", dict(baseline, candidate_id="cand-baseline-dirty",
               touched_files=[CARD], diff=card_diff, candidate_hash=card_h), "block")

        drifted = dict(campaign, frozen_inputs={"routing-gold-x": {"path": frozen_rel, "sha256": "0" * 64}})
        expect("frozen-input drift blocks", base, "block", camp=drifted)

        bad_split = dict(campaign, autoresearch_splits={"reflection_train": ["routing-gold-x"], "held_eval": ["routing-gold-x"]})
        expect("train/held overlap blocks", base, "block", camp=bad_split)

        held_touch_diff, held_touch_h = mkdiff("held-touch", [CARD, held_rel])
        expect("candidate touching held frozen input blocks",
               dict(base, candidate_id="cand-held-touch", touched_files=[CARD, held_rel],
                    diff=held_touch_diff, candidate_hash=held_touch_h), "block")

        # P0 (round 2): Git patch forms that a header-only parser misses.
        def mkraw(name, text):
            _write(root, f"evals/c/{name}.diff", text)
            return f"evals/c/{name}.diff", sha256_file(os.path.join(root, f"evals/c/{name}.diff"))

        mode_rel, mode_h = mkraw("mode", "diff --git a/tools/check-conformance.py b/tools/check-conformance.py\n"
                                 "old mode 100644\nnew mode 100755\n")
        expect("P0: mode-only patch declared as empty baseline -> block",
               dict(base, candidate_id="cand-mode-baseline", is_baseline=True, touched_files=[],
                    diff=mode_rel, candidate_hash=mode_h), "block")
        expect("P0: mode-only patch on the checker (non-baseline) -> block",
               dict(base, candidate_id="cand-mode", touched_files=["tools/check-conformance.py"],
                    diff=mode_rel, candidate_hash=mode_h), "block")

        bin_rel, bin_h = mkraw("bin", "diff --git a/skills/techniques/task-reframing/SKILL.md "
                               "b/skills/techniques/task-reframing/SKILL.md\nGIT binary patch\nliteral 3\nabc\n")
        expect("P0: binary patch -> block",
               dict(base, candidate_id="cand-bin", touched_files=[CARD], diff=bin_rel, candidate_hash=bin_h), "block")

        ren_rel, ren_h = mkraw("ren", "diff --git a/skills/techniques/task-reframing/SKILL.md b/skills/techniques/x.md\n"
                               "rename from skills/techniques/task-reframing/SKILL.md\nrename to skills/techniques/x.md\n")
        expect("P0: rename patch -> block",
               dict(base, candidate_id="cand-ren", touched_files=[CARD], diff=ren_rel, candidate_hash=ren_h), "block")

        expect("non-empty baseline diff blocks",
               dict(baseline, candidate_id="cand-baseline-nonempty", touched_files=[],
                    diff=card_diff, candidate_hash=card_h), "block")

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
