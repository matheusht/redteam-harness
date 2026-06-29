#!/usr/bin/env python3
"""Hermetic API-security benchmark runner (Track D).

Drives FROZEN synthetic API targets with no live network and no LLM. Each target declares an oracle
and a list of canned request outcomes. The runner derives deterministic (signal, effect,
control_ok) tuples and adjudicates them with the same skeptical contract used elsewhere:

  confirmed   : a primary signals AND has the distinctive canary/effect,
                every positive_control proves the guard can deny/strip,
                every negative_control is clean, within budget
  needs_review: a primary signals but the distinctive canary/effect or controls are incomplete
  refuted      : otherwise

Usage:
  python3 tools/run-hermetic-api.py             # run every bundled API target
  python3 tools/run-hermetic-api.py <target.json>
  python3 tools/run-hermetic-api.py --self-test
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGETS_DIR = os.path.join(ROOT, "evals", "hermetic", "targets")
API_ORACLES = (
    "api_bola_state_change",
    "jwt_claim_validation",
    "bopla_property_authz",
    "ssrf_redirect_follow",
    "graphql_global_id",
)
DENY = (401, 403)


def load(path):
    with open(path) as fh:
        return json.load(fh)


def _ok_status(req):
    return req.get("status") in (200, 201, 202, 204)


def derive(oracle, req):
    """Map a canned request row to (signal, effect, control_ok)."""
    if oracle == "api_bola_state_change":
        signal = _ok_status(req) and req.get("selector") == "victim"
        effect = signal and bool(req.get("foreign_canary_effect"))
        control_ok = req.get("status") in DENY and not req.get("foreign_canary_effect", False)
        return signal, effect, control_ok

    if oracle == "jwt_claim_validation":
        wrong_audience = req.get("aud") != req.get("expected_aud")
        wrong_alg = req.get("alg") != req.get("expected_alg")
        signal = bool(req.get("accepted")) and (wrong_audience or wrong_alg)
        effect = signal and bool(req.get("privilege_canary_granted"))
        control_ok = (not req.get("accepted")) and (wrong_audience or wrong_alg) and not req.get("privilege_canary_granted", False)
        return signal, effect, control_ok

    if oracle == "bopla_property_authz":
        read_signal = req.get("operation") == "read" and bool(req.get("guarded_property_present"))
        write_signal = req.get("operation") == "write" and (
            bool(req.get("echoed_guarded_property"))
            or bool(req.get("persisted_guarded_property"))
            or bool(req.get("effective_property_impact"))
        )
        signal = read_signal or write_signal
        effect = bool(req.get("exposed_property_canary") or req.get("persisted_guarded_property") or req.get("effective_property_impact"))
        control_ok = req.get("guard_result") in ("denied", "stripped", "coerced") and not effect
        return signal, effect, control_ok

    if oracle == "ssrf_redirect_follow":
        signal = bool(req.get("server_fetch_attempted") or req.get("followed_redirect") or req.get("url_reflected"))
        effect = bool(req.get("fetch_reached_stand_in_canary"))
        control_ok = req.get("guard_result") in ("redirect_blocked", "allowlist_denied", "no_fetch") and not effect
        return signal, effect, control_ok

    if oracle == "graphql_global_id":
        signal = bool(req.get("introspection_enabled") or req.get("global_id_decoded") or req.get("resolver_called"))
        effect = bool(req.get("foreign_canary_returned"))
        control_ok = req.get("guard_result") in ("resolver_denied", "field_filtered") and not effect
        return signal, effect, control_ok

    raise ValueError(f"unknown oracle: {oracle}")


def adjudicate(results):
    primary = [r for r in results if r["kind"] == "primary"]
    pos = [r for r in results if r["kind"] == "positive_control"]
    negs = [r for r in results if r["kind"] == "negative_control"]
    primary_signal = any(r["signal"] for r in primary)
    primary_effect = any(r["signal"] and r["effect"] for r in primary)
    controls_ok = bool(pos) and all(r["control_ok"] for r in pos)
    negs_clean = all((not r["signal"]) and (not r["effect"]) for r in negs)
    if primary_effect and controls_ok and negs_clean:
        return "confirmed"
    if primary_signal or primary_effect:
        return "needs_review"
    return "refuted"


def run(target, budget_override=None):
    oracle = target["oracle"]
    budget = budget_override if budget_override is not None else target.get("budget", {}).get("max_target_calls", 9999)
    calls = 0
    results, mismatches = [], []
    for req in target["requests"]:
        if calls >= budget:
            return {"verdict": "aborted_budget", "target_calls": calls, "budget": budget,
                    "within_budget": False, "mismatches": mismatches}
        signal, effect, control_ok = derive(oracle, req)
        calls += 1
        exp = req.get("expect")
        if exp and (
            signal != exp.get("signal")
            or effect != exp.get("effect", exp.get("signal"))
            or control_ok != exp.get("control_ok", False)
        ):
            mismatches.append(
                f"{req['id']}: got ({signal},{effect},{control_ok}) "
                f"expected ({exp.get('signal')},{exp.get('effect')},{exp.get('control_ok', False)})"
            )
        results.append({"kind": req["kind"], "signal": signal, "effect": effect, "control_ok": control_ok})
    return {"verdict": adjudicate(results), "target_calls": calls, "budget": budget,
            "within_budget": calls <= budget, "mismatches": mismatches}


def report(target, res):
    print(f"target: {target['target']}  [{target['oracle']}]")
    print(f"  verdict     : {res['verdict']}  (expected: {target.get('expected_verdict')})")
    print(f"  cost ledger : {res['target_calls']}/{res['budget']} target calls  (within_budget={res['within_budget']})")
    if res["mismatches"]:
        print("  detector drift: " + "; ".join(res["mismatches"]))
    return res["verdict"] == target.get("expected_verdict") and not res["mismatches"]


def bundled_targets():
    out = []
    for name in sorted(os.listdir(TARGETS_DIR)):
        tp = os.path.join(TARGETS_DIR, name, "target.json")
        if os.path.isfile(tp):
            t = load(tp)
            if t.get("oracle") in API_ORACLES:
                out.append(t)
    return out


def _break_positive_control(t):
    tampered = json.loads(json.dumps(t))
    for r in tampered["requests"]:
        if r["kind"] != "positive_control":
            continue
        oracle = tampered["oracle"]
        if oracle == "api_bola_state_change":
            r["status"], r["foreign_canary_effect"] = 200, True
        elif oracle == "jwt_claim_validation":
            r["accepted"], r["privilege_canary_granted"] = True, True
        elif oracle == "bopla_property_authz":
            r["guard_result"], r["persisted_guarded_property"] = "accepted", True
        elif oracle == "ssrf_redirect_follow":
            r["guard_result"], r["fetch_reached_stand_in_canary"] = "allowed", True
        elif oracle == "graphql_global_id":
            r["guard_result"], r["foreign_canary_returned"] = "allowed", True
        r.pop("expect", None)
    return tampered


def _effectless_primary(t):
    tampered = json.loads(json.dumps(t))
    for r in tampered["requests"]:
        if r["kind"] != "primary":
            continue
        oracle = tampered["oracle"]
        if oracle == "api_bola_state_change":
            r["status"], r["foreign_canary_effect"] = 200, False
        elif oracle == "jwt_claim_validation":
            r["accepted"], r["privilege_canary_granted"] = True, False
        elif oracle == "bopla_property_authz":
            r["operation"] = "write"
            r["guarded_property_present"] = False
            r["echoed_guarded_property"] = True
            r["exposed_property_canary"] = False
            r["persisted_guarded_property"] = False
            r["effective_property_impact"] = False
        elif oracle == "ssrf_redirect_follow":
            r["url_reflected"] = True
            r["server_fetch_attempted"] = False
            r["followed_redirect"] = False
            r["fetch_reached_stand_in_canary"] = False
        elif oracle == "graphql_global_id":
            r["introspection_enabled"] = True
            r["global_id_decoded"] = True
            r["resolver_called"] = False
            r["foreign_canary_returned"] = False
        r.pop("expect", None)
    return tampered


def self_test():
    ok = True
    targets = bundled_targets()
    if len(targets) < 5:
        ok = False
        print(f"[self-test] expected >=5 API targets, found {len(targets)}")

    for t in targets:
        print(f"\n[self-test] {t['oracle']}: confirmed-with-controls, within budget, no drift")
        res = run(t)
        if not (res["verdict"] == t["expected_verdict"] and res["within_budget"] and not res["mismatches"]):
            ok = False
            print("  !!", res)

        res = run(t, budget_override=1)
        if res["verdict"] != "aborted_budget":
            ok = False
            print("  !! tight budget did not abort:", res)

        if run(_break_positive_control(t))["verdict"] == "confirmed":
            ok = False
            print("  !! confirmed without a denying/stripping positive control")

        effectless = run(_effectless_primary(t))["verdict"]
        if effectless == "confirmed":
            ok = False
            print("  !! confirmed on signal-only primary without distinctive canary/effect")
        if effectless not in ("needs_review", "refuted"):
            ok = False
            print("  !! unexpected signal-only verdict:", effectless)

    print("\nSELF-TEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv):
    if len(argv) == 2 and argv[1] == "--self-test":
        return self_test()
    if len(argv) == 2:
        t = load(argv[1])
        return 0 if report(t, run(t)) else 1
    ok = True
    for t in bundled_targets():
        if not report(t, run(t)):
            ok = False
        print()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
