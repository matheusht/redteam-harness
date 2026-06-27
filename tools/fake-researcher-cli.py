#!/usr/bin/env python3
"""Deterministic fake researcher CLI — the provider-neutral wire contract, no model (Phase 10G).

Reads one JSON object {"view": ..., "responses": [...]} on stdin and prints exactly one action object
on stdout. This is what a real LM wrapper would replace; here it is deterministic so CI can test the
subprocess protocol (and, with --malformed, the bounded-retry path) without any credentials.

It is BLIND by construction: it only ever receives the serialized researcher view and the broker's
mediated responses. It has no repository, gold, scorer, or candidate-identity access.
"""

import json
import sys


def discipline_flags(card_text):
    t = (card_text or "").lower()
    overclaim = any(s in t for s in [
        "always confirmed", "always confirm", "skip replay", "skip control",
        "skip the negative", "no controls needed", "ignore scope", "assume success",
    ])
    efficient = any(s in t for s in [
        "oracle-first", "stop rule", "minimal probe", "one decisive probe", "name the exact oracle condition",
    ])
    return {"overclaim": overclaim, "efficient": efficient}


def plan_for(card_text, budget):
    f = discipline_flags(card_text)
    if f["overclaim"]:
        plan = ["core"]
    elif f["efficient"]:
        plan = ["core", "negative_control", "replay"]
    else:
        plan = ["core", "negative_control", "replay", "core"]
    return plan[: budget.get("max_probes", len(plan))], f


def main(argv):
    malformed = "--malformed" in argv[1:]
    data = json.loads(sys.stdin.read() or "{}")
    if malformed:
        sys.stdout.write("not-an-action {{{")
        return 0
    view = data.get("view", {})
    responses = data.get("responses", [])
    plan, f = plan_for(view.get("technique_card", ""), view.get("budget", {}))
    probes_done = [r["action"]["kind"] for r in responses if r.get("action", {}).get("type") == "probe"]

    if len(probes_done) < len(plan):
        action = {"type": "probe", "kind": plan[len(probes_done)]}
    else:
        def disclosed(kind):
            return any(r["action"].get("kind") == kind and r["response"].get("disclosed") for r in responses)
        ran_controls = any(k in ("negative_control", "replay") for k in probes_done)
        if not disclosed("core"):
            verdict = "refuted"
        elif f["overclaim"] or not ran_controls:
            verdict = "confirmed"
        elif disclosed("negative_control") or ("replay" in probes_done and not disclosed("replay")):
            verdict = "needs_review"
        else:
            verdict = "confirmed"
        action = {"type": "final", "verdict": verdict, "controls_claimed": sorted(set(probes_done) & {"negative_control", "replay"})}
    action["_usage"] = {"tokens": 0}
    sys.stdout.write(json.dumps(action))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
