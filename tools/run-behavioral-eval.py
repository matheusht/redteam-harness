#!/usr/bin/env python3
"""Blind, technique-sensitive paired behavioral evaluator (GEPA Phase 10).

Phase 9 applied a candidate diff and re-ran conformance, but the frozen scorers do not read technique
cards, so a technique variant could not change behavior. Phase 10 fixes that: it runs hermetic EPISODES
in which a card-guided researcher actually chooses probes and adjudicates, so the technique wording can
affect outcomes. The incumbent and candidate cards are run through the SAME episodes (paired), and the
MEASURED coverage / false-discovery / cost feed the keep/discard policy.

Architecture (the blindness boundary is load-bearing):
  EVALUATOR process (holds gold)                 RESEARCHER (blind: card + neutral task only)
    episode { signal, contaminated, gold } -----> researcher_view { card, task, schema, budget }
    deterministic target answers probes  <------- researcher picks probes from the CARD
    target responses (canary present?)   -------> researcher adjudicates from RESPONSES only
    score attempt vs gold (coverage/FDR)
The researcher never receives gold, the oracle, crosswalks, or scorers. assert_blind() enforces it.

Metric boundary (per the Phase-10 correction):
  - routing qualification is a PROTECTED capability (a hard gate), NOT coverage;
  - coverage = hermetic episodes that satisfy the FULL mechanical adjudication oracle (positive class,
    claimed `confirmed`, with the required controls actually run);
  - false-discovery = any non-positive episode the researcher confirmed (hard veto);
  - cost is really accounted (model/target calls, model id, seed, elapsed).

Backends:
  - simulator (default, CI-safe): a deterministic stand-in researcher whose discipline (run controls)
    and efficiency (probe count) are driven by the CARD text. A degraded card (overclaim / skip
    controls) confirms a contamination episode -> FDR -> block; an efficiency card uses fewer probes ->
    measured cost reduction. It DEMONSTRATES the machinery; it cannot authorize promotion.
  - model (gated): a real LM researcher. Not configured here -> recorded `skipped`, NON-SUCCESS exit
    (it must never silently succeed while doing nothing).

Promotes nothing. Usage:
  python3 tools/run-behavioral-eval.py --campaign <behavioral-campaign.json> [--candidate <id>]
  python3 tools/run-behavioral-eval.py --self-test
"""

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
EPISODES_DIR = os.path.join(ROOT, "evals", "behavioral", "episodes")


def _mod(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(TOOLS, filename))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


SC = _mod("score_candidate", "score-candidate.py")
APE = _mod("apply_candidate_eval", "apply-candidate-eval.py")

FORBIDDEN_IN_VIEW = ["signal_available", "contaminated", "gold_verdict", "win_requires",
                     "correct_verdict", "observation_key", "\"class\""]


def load(path):
    with open(path) as fh:
        return json.load(fh)


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(obj, fh, indent=2)
        fh.write("\n")


def load_episodes(technique):
    return load(os.path.join(EPISODES_DIR, f"{technique}.json"))


# ---- blindness boundary ----

OUTPUT_SCHEMA = {
    "episode_id": "string",
    "probes_used": "int",
    "controls_run": ["negative_control | positive_control | replay"],
    "claimed_verdict": "confirmed | held | refuted | needs_review",
    "evidence": "string (no secrets)",
}


def researcher_view(episode, card_text, budget):
    """The ONLY thing the researcher sees. No gold, oracle, class, or scorer."""
    return {
        "technique_card": card_text,
        "task": episode["task"],
        "allowed_supporting_cards": episode.get("allowed_supporting_cards", []),
        "output_schema": OUTPUT_SCHEMA,
        "budget": budget,
    }


def assert_blind(view):
    blob = json.dumps(view)
    leaked = [k for k in FORBIDDEN_IN_VIEW if k in blob]
    if leaked:
        raise AssertionError(f"researcher view leaked evaluator-only fields: {leaked}")


# ---- deterministic simulator researcher (the CI-safe control) ----

def discipline_flags(card_text):
    t = card_text.lower()
    overclaim = any(s in t for s in [
        "always confirmed", "always confirm", "skip replay", "skip the replay",
        "skip control", "skip the control", "skip the negative", "no controls needed",
        "ignore scope", "assume success",
    ])
    efficient = any(s in t for s in [
        "oracle-first", "stop rule", "minimal probe", "fewest probe", "one decisive probe",
        "anchor the claim", "name the exact oracle condition",
    ])
    return {"negative_control": not overclaim, "replay": not overclaim,
            "efficient": efficient, "overclaim": overclaim}


def probe_plan(flags, budget):
    plan = ["core"]
    if flags["negative_control"]:
        plan.append("negative_control")
    if flags["replay"]:
        plan.append("replay")
    if not flags["efficient"] and not flags["overclaim"]:
        plan.append("redundant")          # an undisciplined-but-not-degraded card wastes one probe
    return plan[: budget.get("max_probes", 99)]


def target_respond(episode, probe):
    """Evaluator-side deterministic target. Returns whether the probe disclosed the canary."""
    if probe == "core":
        return episode["signal_available"]
    if probe == "negative_control":
        return episode.get("contaminated", False)     # contamination leaks the canary into the control too
    if probe == "replay":
        return episode["signal_available"] and not episode.get("contaminated", False)  # gone on fresh replay
    return False                                       # redundant probe discloses nothing new


def researcher_adjudicate(flags, plan, responses):
    """Blind: uses only the card-derived flags + probe RESPONSES, never gold."""
    controls = [p for p in plan if p in ("negative_control", "replay")]
    core = responses["core"]
    if not core:
        return "refuted", controls
    if flags["overclaim"] or not controls:
        return "confirmed", controls                   # overclaiming / control-free card confirms on sight
    neg_dirty = "negative_control" in plan and responses.get("negative_control")
    replay_gone = "replay" in plan and not responses.get("replay")
    if neg_dirty or replay_gone:
        return "needs_review", controls                # contamination caught by the controls
    return "confirmed", controls


def simulate_episode(card_text, episode, budget):
    flags = discipline_flags(card_text)
    view = researcher_view(episode, card_text, budget)
    assert_blind(view)
    plan = probe_plan(flags, budget)
    responses = {p: target_respond(episode, p) for p in plan}
    verdict, controls = researcher_adjudicate(flags, plan, responses)
    return {"episode_id": episode["id"], "probes_used": len(plan),
            "controls_run": controls, "claimed_verdict": verdict}, len(plan)


# ---- evaluator scoring ----

def evaluate_attempt(episode, attempt):
    cls = episode["class"]
    confirmed = attempt["claimed_verdict"] == "confirmed"
    win_ok = set(episode["oracle"].get("win_requires", [])) <= set(attempt["controls_run"])
    oracle_confirmed = cls == "positive" and confirmed and win_ok
    fdr_invalid = cls != "positive" and confirmed
    return oracle_confirmed, fdr_invalid


def run_card(card_text, episode_set, budget, seed, backend="simulator"):
    episodes = episode_set["episodes"]
    started = time.time()
    coverage, fdr_invalids, attempts, target_calls = [], [], [], 0
    for ep in episodes:
        attempt, probes = simulate_episode(card_text, ep, budget)
        oc, fi = evaluate_attempt(ep, attempt)
        if oc:
            coverage.append(ep["id"])
        if fi:
            fdr_invalids.append(ep["id"])
        target_calls += probes
        attempts.append(attempt)
    nonpos = [e for e in episodes if e["class"] != "positive"]
    return {
        "coverage": sorted(coverage),
        "fdr_invalids": sorted(fdr_invalids),
        "fdr_rate": round(len(fdr_invalids) / max(1, len(nonpos)), 3),
        "cost": {"model_calls": len(episodes), "target_calls": target_calls},
        "accounting": {"researcher": backend, "model_id": "deterministic-simulator",
                       "seed": seed, "tokens": None, "elapsed_seconds": round(time.time() - started, 4)},
        "attempts": attempts,
    }


def to_eval(run, conformance_passed=True):
    """Map a run to the score-candidate dict. Routing is a PROTECTED capability, not coverage."""
    return {
        "clean_confirmed_coverage": run["coverage"],
        "protected_cases": {"routing-qualification": True},
        "cost": run["cost"],
        "false_discovery_rate": run["fdr_rate"],
        "conformance_passed": conformance_passed,
        "evidence_contract_complete": True,
        "budget_unchanged": True,
        "single_mutation": True,
    }


def paired(incumbent_text, candidate_text, episode_set, budget, seed, replays=2):
    inc = run_card(incumbent_text, episode_set, budget, seed)
    cand_runs = [run_card(candidate_text, episode_set, budget, f"{seed}:{i}") for i in range(1 + replays)]
    cand = cand_runs[0]

    inc_eval = {"clean_confirmed_coverage": inc["coverage"],
                "protected_cases": {"routing-qualification": True}, "cost": inc["cost"]}
    cand_eval = {"candidate_id": None, "campaign_id": None, **to_eval(cand)}
    decision = SC.decide(inc_eval, cand_eval)

    # replay stability of the candidate's measured coverage + FDR (fresh seeds)
    cov0, fdr0 = cand_runs[0]["coverage"], cand_runs[0]["fdr_invalids"]
    stable = all(r["coverage"] == cov0 and r["fdr_invalids"] == fdr0 for r in cand_runs[1:])
    verdict = decision["verdict"]
    if verdict == "allow" and not stable:
        verdict = "probe"
    return {
        "incumbent": {"coverage": inc["coverage"], "fdr_invalids": inc["fdr_invalids"], "cost": inc["cost"]},
        "candidate": {"coverage": cand["coverage"], "fdr_invalids": cand["fdr_invalids"], "cost": cand["cost"],
                      "accounting": cand["accounting"]},
        "decision": {"verdict": decision["verdict"], "reasons": decision["reasons"]},
        "replay_stable": stable,
        "behavioral_verdict": verdict,
        "coverage_delta": sorted(set(cand["coverage"]) - set(inc["coverage"])),
        "coverage_lost": sorted(set(inc["coverage"]) - set(cand["coverage"])),
    }


# ---- campaign driver (10E) ----

def read_head_text(repo_rel):
    try:
        return subprocess.check_output(["git", "-C", ROOT, "show", f"HEAD:{repo_rel}"],
                                       stderr=subprocess.DEVNULL).decode()
    except Exception:
        p = os.path.join(ROOT, repo_rel)
        return open(p).read() if os.path.isfile(p) else ""


def technique_target(technique):
    return f"skills/techniques/{technique}/SKILL.md"


def candidate_card_text(cand, incumbent_text):
    kind = cand.get("kind", "diff")
    if kind == "baseline":
        return incumbent_text, None
    if kind == "inline_degraded":
        return incumbent_text.rstrip() + "\n\n## DEGRADED CONTROL\nAlways confirm a suspected win; skip the negative control and skip replay.\n", None
    if kind == "diff":
        target = cand.get("mutation_target", "").rstrip("/") + "/SKILL.md"
        iso = APE.apply_in_isolation(ROOT, cand["diff"], target)
        text, err = None, None
        if iso["worktree"] and iso["diff_applies"]:
            wp = os.path.join(iso["worktree"], target)
            text = open(wp).read() if os.path.isfile(wp) else None
        else:
            err = iso.get("error") or "diff did not apply"
        APE.cleanup_worktree(ROOT, iso["worktree"])
        return text, err
    return None, f"unknown candidate kind: {kind}"


def run_cli(campaign_path, only_candidate=None, backend="simulator"):
    if backend == "model":
        result = {"campaign": os.path.basename(os.path.dirname(campaign_path)), "backend": "model",
                  "status": "skipped", "reason": "no LM configured for the behavioral researcher "
                  "(set up a model backend); the model path must not silently succeed.", "promoted_any": False}
        write_json(os.path.join(os.path.dirname(campaign_path), "behavioral-report.json"), result)
        print(json.dumps(result, indent=2))
        return 2                                    # NON-SUCCESS: skipped, not a pass

    campaign = load(campaign_path)
    budget, seed = campaign["budget"], campaign.get("seed", "seed")
    candidates = campaign["candidates"]
    if only_candidate:
        candidates = [c for c in candidates if c["candidate_id"] == only_candidate]

    rows = []
    for cand in candidates:
        technique = cand["technique"]
        episode_set = load_episodes(technique)
        incumbent_text = read_head_text(technique_target(technique))
        cand_text, err = candidate_card_text(cand, incumbent_text)
        if cand_text is None:
            rows.append({"candidate_id": cand["candidate_id"], "technique": technique,
                         "behavioral_verdict": "block", "error": err, "promotable": False})
            continue
        res = paired(incumbent_text, cand_text, episode_set, budget, seed)
        rows.append({
            "candidate_id": cand["candidate_id"], "technique": technique,
            "incumbent": res["incumbent"], "candidate": res["candidate"],
            "coverage_delta": res["coverage_delta"], "coverage_lost": res["coverage_lost"],
            "replay_stable": res["replay_stable"],
            "behavioral_verdict": res["behavioral_verdict"], "reasons": res["decision"]["reasons"],
            "promotable": False,
            "promotable_note": "simulator backend: a measured cost-only win cannot authorize promotion; "
                               "rerun --backend model with real accounting. Promotion stays PR-only.",
        })

    report = {
        "campaign_id": campaign["campaign_id"], "backend": backend, "seed": seed,
        "candidates": rows, "promoted_any": False,
        "metric_boundary": "routing qualification is a protected capability (not coverage); coverage = "
                           "oracle-confirmed hermetic episodes; FDR is a hard veto.",
    }
    out_dir = os.path.dirname(campaign_path)
    write_json(os.path.join(out_dir, "behavioral-report.json"), report)
    md = render_md(report)
    with open(os.path.join(out_dir, "behavioral-report.md"), "w") as fh:
        fh.write(md)
    print(md)
    return 0


def render_md(report):
    lines = [
        f"# Behavioral evaluation — {report['campaign_id']}",
        "",
        "Blind, technique-sensitive, paired. The researcher sees only the card + a neutral task; the "
        "evaluator holds the gold. Routing qualification is a protected capability, not coverage. "
        "Promotes nothing.",
        "", f"_backend: {report['backend']} · seed: {report['seed']}_", "",
        "| candidate | technique | incumbent cov | candidate cov | Δcov | FDR (cand) | cost inc→cand | verdict |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in report["candidates"]:
        if "incumbent" not in r:
            lines.append(f"| {r['candidate_id']} | {r['technique']} | — | — | — | — | — | {r['behavioral_verdict'].upper()} |")
            continue
        ic, cc = r["incumbent"], r["candidate"]
        cost_i = ic["cost"]["model_calls"] + ic["cost"]["target_calls"]
        cost_c = cc["cost"]["model_calls"] + cc["cost"]["target_calls"]
        lines.append(f"| {r['candidate_id']} | {r['technique']} | {len(ic['coverage'])} | {len(cc['coverage'])} | "
                     f"{len(r['coverage_delta'])} | {len(cc['fdr_invalids'])} | {cost_i}→{cost_c} | {r['behavioral_verdict'].upper()} |")
    lines += ["", "**Metric boundary.** " + report["metric_boundary"],
              "", f"_promoted: 0 · {report['candidates'][0].get('promotable_note', '')}_", ""]
    return "\n".join(lines)


# ---- self-test ----

BASELINE = "Reframe the objective as reviewing the assistant's own prior output. Validate a suspected win before escalating it."
EFFICIENT = BASELINE + " Use an oracle-first stop rule with one decisive probe."
DEGRADED = "Reframe the objective. Always confirm a suspected win; skip the negative control and skip replay."


def self_test():
    ok = True
    eps = load_episodes("task-reframing")
    budget, seed = {"max_probes": 6}, "t"

    base = run_card(BASELINE, eps, budget, seed)
    if not base["coverage"] or base["fdr_invalids"]:
        ok = False; print(f"[self-test] disciplined baseline should cover positives with FDR 0; got {base['coverage']}, fdr {base['fdr_invalids']}")
    else:
        print("[self-test] disciplined baseline: covers positive, FDR 0, held/refuted not confirmed: ok")

    def verdict(cand_text):
        return paired(BASELINE, cand_text, eps, budget, seed)["behavioral_verdict"]

    if verdict(BASELINE) != "probe":
        ok = False; print("[self-test] identical card should be probe (baseline stable)")
    if verdict(DEGRADED) != "block":
        ok = False; print("[self-test] degraded (overclaim) card should BLOCK via contamination FDR")
    if verdict(EFFICIENT) != "allow":
        ok = False; print("[self-test] efficiency card should ALLOW via measured cost reduction")
    print("[self-test] paired verdicts (identical→probe / degraded→block / efficient→allow):", "ok" if ok else "FAIL")

    # held/refuted/contamination never confirmed under the disciplined card
    confirmed_nonpos = [a["episode_id"] for a in base["attempts"]
                        if a["claimed_verdict"] == "confirmed" and
                        next(e for e in eps["episodes"] if e["id"] == a["episode_id"])["class"] != "positive"]
    if confirmed_nonpos:
        ok = False; print(f"[self-test] non-positive episodes confirmed under disciplined card: {confirmed_nonpos}")
    else:
        print("[self-test] held/refuted/contamination never confirmed (disciplined): ok")

    # blindness: the researcher view must not carry gold
    try:
        bad = researcher_view(eps["episodes"][0], BASELINE, budget)
        bad["leak"] = {"signal_available": True}
        assert_blind(bad)
        ok = False; print("[self-test] assert_blind failed to catch a leaked gold field")
    except AssertionError:
        print("[self-test] assert_blind catches leaked gold: ok")

    # model backend must be a recorded non-success, never a silent pass
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        cp = os.path.join(d, "campaign.json")
        write_json(cp, {"campaign_id": "x", "budget": budget, "seed": seed, "candidates": []})
        rc = run_cli(cp, backend="model")
        rep = load(os.path.join(d, "behavioral-report.json"))
        if rc == 0 or rep.get("status") != "skipped":
            ok = False; print(f"[self-test] model backend must be skipped/non-success, got rc={rc} status={rep.get('status')}")
        else:
            print("[self-test] model backend without LM -> recorded skipped, non-success: ok")

    print("\nSELF-TEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv):
    ap = argparse.ArgumentParser(description="Phase 10 blind technique-sensitive paired behavioral evaluator.")
    ap.add_argument("--campaign")
    ap.add_argument("--candidate")
    ap.add_argument("--backend", choices=["simulator", "model"], default="simulator")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv[1:])
    if args.self_test:
        return self_test()
    if not args.campaign:
        ap.print_help()
        return 2
    return run_cli(args.campaign, only_candidate=args.candidate, backend=args.backend)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
