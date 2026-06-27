#!/usr/bin/env python3
"""Canonical experiment lifecycle entrypoint (Phase 14) — THE command to run for a campaign.

One public surface for the whole pipeline:

    preflight -> apply -> measure -> score -> replay -> record

It COMPOSES the existing, individually-tested functions — it reimplements none of them (no broker, no
materialization, no replay, no promotion logic is duplicated here):

    run-gepa-real.generate(...)              # generate candidates + shadow score + replay + promotion
      -> run-gepa-real.behavioral_bridge(...) # measure (materialize) + score (real-LM behavioral)
      -> render/score re-render               # bundles lead with the authoritative verdict
      -> assemble lifecycle-result.json       # one unified record per candidate (schema below)

and emits one `lifecycle-result.json` per candidate + a campaign `lifecycle-report.json`, conforming to
`schemas/lifecycle-result.schema.json`. The authoritative answer is `authoritative_stage` /
`authoritative_verdict` (Decision 0004 / Phase 10H0: measured materialization + broker-mediated
behavioral are authoritative; the deterministic shadow scoreboard is advisory). A missing real-LM
backend is `status=skipped` and is never a fake `allow`. It writes only under the campaign directory and
NEVER under `skills/` or Plane 1; it promotes nothing.

Usage:
  python3 tools/run-experiment-lifecycle.py --campaign <campaign-manifest.json> \
      --backend deterministic|gepa --behavioral-backend none|fake|model [--behavioral-model-cmd "..."] \
      [--candidate <id>]
  python3 tools/run-experiment-lifecycle.py --self-test

For --backend gepa, run under the GEPA venv (gepa + litellm) with GEPA_REFLECTION_LM set, exactly as
tools/run-gepa-real.py expects; --backend deterministic is CI-safe.
"""

import argparse
import importlib.util
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")


def _mod(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(TOOLS, filename))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


GR = _mod("run_gepa_real", "run-gepa-real.py")     # the internal orchestrator we compose


def load(path):
    with open(path) as fh:
        return json.load(fh)


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(obj, fh, indent=2)
        fh.write("\n")


def _rel(path):
    return os.path.relpath(path, ROOT) if path else None


def assemble_lifecycle_result(campaign_path, candidate_id):
    """Pure: read the per-candidate artifacts the chain already wrote and map them into the one
    lifecycle-result contract. Invents no verdicts — the authoritative answer comes straight from the
    bridge-result (materialization > scope > behavioral) and promotability from the promotion bundle."""
    camp_dir = os.path.dirname(campaign_path)
    campaign_id = load(campaign_path).get("campaign_id")
    cdir = os.path.join(camp_dir, "candidates", candidate_id)
    br = load(os.path.join(cdir, "bridge-result.json"))
    links = br.get("links", {}) or {}
    mat = links.get("materialization", {}) or {}

    pb_path = os.path.join(cdir, "promotion", "promotion-bundle.json")
    pb = load(pb_path) if os.path.isfile(pb_path) else {}
    rs_path = os.path.join(cdir, "replays", "replay-summary.json")
    rs = load(rs_path) if os.path.isfile(rs_path) else None
    shadow_path = os.path.join(camp_dir, "report.json")
    gate, gate_reasons = None, []
    if os.path.isfile(shadow_path):
        row = next((c for c in load(shadow_path).get("candidates", []) if c["candidate_id"] == candidate_id), {})
        gate, gate_reasons = row.get("gate"), row.get("gate_reasons", [])

    behavioral_present = br.get("behavioral_verdict") is not None
    beh_status = br.get("behavioral_status")
    if behavioral_present:
        status = "completed"
    elif beh_status in ("skipped", "failed"):
        status = beh_status                       # missing/failed real-LM backend — never a fake allow
    else:
        status = "completed"                      # blocked at materialization/scope, or behavioral not requested

    return {
        "campaign_id": campaign_id,
        "candidate_id": candidate_id,
        "status": status,
        "stages": {
            "preflight": {"verdict": gate, "reasons": gate_reasons} if gate is not None else None,
            "materialization": {k: mat.get(k) for k in ("verdict", "conformance_passed", "base_tree",
                                                        "candidate_tree", "actual_paths")},
            "scope": {"in_scope": br.get("in_scope"), "violations": br.get("scope_violations", [])},
            "behavioral": ({"verdict": br.get("behavioral_verdict"), "cost": br.get("cost"),
                            "fdr_invalids": br.get("fdr_invalids"), "coverage_delta": br.get("coverage_delta"),
                            "replay": br.get("replay")} if behavioral_present else None),
            "replay": {"stable": rs.get("stable")} if rs else None,
            "promotion": {"promotable": bool(pb.get("promotable", False))},
        },
        "authoritative_stage": br.get("authoritative_stage"),
        "authoritative_verdict": br.get("authoritative_verdict"),
        "promotable": bool(pb.get("promotable", False)),
        "artifacts": {
            "candidate_manifest": _rel(os.path.join(cdir, "candidate-manifest.json")),
            "diff": links.get("diff"),
            "materialization": mat or None,
            "bridge_result": _rel(os.path.join(cdir, "bridge-result.json")),
            "broker_events": links.get("broker_events"),
            "behavioral_run": links.get("behavioral_run"),
            "replay": _rel(rs_path) if rs else None,
            "promotion_bundle": _rel(pb_path) if pb else None,
        },
        "reasons": br.get("reasons", []) or ([f"behavioral {beh_status}"] if beh_status in ("skipped", "failed") else []),
    }


def run_lifecycle(campaign_path, backend="deterministic", behavioral_backend="none",
                  behavioral_model_cmd=None, only_candidate=None):
    camp_dir = os.path.dirname(campaign_path)
    assert "skills/" not in os.path.abspath(camp_dir) + os.sep, "lifecycle must not run under skills/"

    # 1. generate candidates + shadow score + replay + promotion (no behavioral yet)
    GR.generate(campaign_path, backend_name=backend, run_chain=True, behavioral_backend="none")
    # 2. measure (materialize) + score (behavioral if requested) — the bridge owns this
    bridge = GR.behavioral_bridge(campaign_path, backend=behavioral_backend, model_cmd=behavioral_model_cmd)
    # 3. re-render bundles/scores so they carry the bridge's authoritative verdict + behavioral evidence
    GR.render_all_promotions(campaign_path)
    GR.write_candidate_scores(campaign_path)

    # 4. record: assemble one lifecycle-result per candidate
    cids = GR.discover_campaign_candidates(campaign_path)
    if only_candidate:
        cids = [c for c in cids if c == only_candidate]
    rows = []
    for cid in cids:
        result = assemble_lifecycle_result(campaign_path, cid)
        write_json(os.path.join(camp_dir, "candidates", cid, "lifecycle-result.json"), result)
        rows.append({k: result[k] for k in ("candidate_id", "status", "authoritative_stage",
                                            "authoritative_verdict", "promotable")})
    report = {
        "campaign_id": load(campaign_path).get("campaign_id"),
        "backend": backend, "behavioral_backend": behavioral_backend,
        "behavioral_status": bridge.get("behavioral_status"),
        "candidates": rows, "promotable_any": any(r["promotable"] for r in rows),
        "note": "Canonical lifecycle record. authoritative_stage/authoritative_verdict are the single "
                "truth (materialization > scope > behavioral > shadow); a missing real-LM backend is "
                "skipped/failed, never a fake allow. Promotes nothing; PR-only.",
    }
    write_json(os.path.join(camp_dir, "lifecycle-report.json"), report)
    return report


# ---- self-test: CI-safe (deterministic generation + fake behavioral; no LM, no network) ----

def _tmp_campaign():
    d = os.path.join(ROOT, "evals", "_tmp_lifecycle_selftest")
    os.makedirs(d, exist_ok=True)
    write_json(os.path.join(d, "campaign-manifest.json"), {
        "campaign_id": "lifecycle-selftest", "created": "2026-06-27",
        "tracks": [{"name": "task-reframing", "mutation_target": "skills/techniques/task-reframing/",
                    "kind": "existing-card-variant"}],
        "mutable_allowlist": ["skills/techniques/task-reframing/"],
        "immutable": ["engine/", "skills/oracles/", "skills/patterns/", "skills/vulns/"],
        "frozen_inputs": {}, "budgets": {"model_calls": 40, "target_calls": 80, "tokens": None},
        "behavioral_budget": {"max_probes": 6}, "seed": "lifecycle-selftest-seed",
    })
    return os.path.join(d, "campaign-manifest.json"), d


def self_test():
    import shutil
    ok = True
    camp_path, d = _tmp_campaign()
    try:
        # deterministic generation + fake behavioral: CI-safe, exercises the whole canonical flow.
        run_lifecycle(camp_path, backend="deterministic", behavioral_backend="fake")
        results = {cid: load(os.path.join(d, "candidates", cid, "lifecycle-result.json"))
                   for cid in GR.discover_campaign_candidates(camp_path)}
        verdicts = {cid: (r["authoritative_verdict"], r["authoritative_stage"], r["status"]) for cid, r in results.items()}

        def v(cid):
            return verdicts.get(cid, (None, None, None))
        report = load(os.path.join(d, "lifecycle-report.json"))
        # parity with Phase 12-13 semantics (a fake-backend efficiency variant may legitimately `allow`
        # on a broker-measured cost cut — that is correct; the safety is that it must NOT be promotable).
        checks = {
            "no-op baseline -> probe (behavioral)": v("cand-baseline")[0] == "probe" and v("cand-baseline")[1] == "behavioral",
            "in-scope variant -> behavioral verdict": v("cand-gepa-task-reframing-001")[0] in ("probe", "allow") and v("cand-gepa-task-reframing-001")[1] == "behavioral",
            "gold-touch -> block at materialization": v("cand-gepa-invalid-gold-touch")[0] == "block" and v("cand-gepa-invalid-gold-touch")[1] == "materialization",
            "fake/simulator backend authorizes NO promotion": report["promotable_any"] is False,
            "lifecycle never wrote skills/": not any("skills/" in p for dp, _, fs in os.walk(d) for p in [os.path.join(dp, f) for f in fs]),
        }
        for label, good in checks.items():
            if not good:
                ok = False
                print(f"[self-test] {label}: FAIL ({verdicts}, promotable_any={report['promotable_any']})")
        print("[self-test] deterministic+fake lifecycle parity (baseline probe, gold-touch block, no fake promotion):",
              "ok" if all(checks.values()) else "FAIL")

        # missing real-LM backend -> skipped, NEVER a fake allow
        run_lifecycle(camp_path, backend="deterministic", behavioral_backend="model", behavioral_model_cmd=None)
        elig = load(os.path.join(d, "candidates", "cand-baseline", "lifecycle-result.json"))
        if elig["status"] != "skipped" or elig["authoritative_verdict"] == "allow":
            ok = False
            print(f"[self-test] missing model backend must be skipped + never allow; got {elig['status']}/{elig['authoritative_verdict']}")
        else:
            print("[self-test] missing real-LM backend -> status=skipped, authoritative != allow (no fake win): ok")

        # contract completeness: required fields present
        req = ["campaign_id", "candidate_id", "status", "stages", "authoritative_stage",
               "authoritative_verdict", "promotable", "artifacts", "reasons"]
        if not all(k in elig for k in req):
            ok = False
            print(f"[self-test] lifecycle-result missing required fields: {[k for k in req if k not in elig]}")
        else:
            print("[self-test] lifecycle-result carries the full contract (stages/authoritative/artifacts): ok")
    finally:
        shutil.rmtree(d, ignore_errors=True)

    print("\nSELF-TEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv):
    ap = argparse.ArgumentParser(description="Canonical experiment lifecycle entrypoint (Phase 14).")
    ap.add_argument("--campaign")
    ap.add_argument("--backend", choices=["deterministic", "gepa"], default="deterministic")
    ap.add_argument("--behavioral-backend", choices=["none", "fake", "model"], default="none")
    ap.add_argument("--behavioral-model-cmd")
    ap.add_argument("--candidate")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv[1:])
    if args.self_test:
        return self_test()
    if not args.campaign:
        ap.print_help()
        return 2
    report = run_lifecycle(args.campaign, backend=args.backend, behavioral_backend=args.behavioral_backend,
                           behavioral_model_cmd=args.behavioral_model_cmd, only_candidate=args.candidate)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
