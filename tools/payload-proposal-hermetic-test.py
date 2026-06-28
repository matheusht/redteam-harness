#!/usr/bin/env python3
"""Hermetic fake-target test for the payload-proposal lane — E-track PG-3A.4.

Proves the load-bearing safety property: a payload PROPOSAL never acts like a verdict. A generated
benign proposal is run against a deterministic FAKE target (no live target, no model); the broker
records what happened; the oracle adjudicates FROM the broker record. The decisive check: the SAME
proposal yields DIFFERENT oracle verdicts depending on the target's behavior — so the verdict is a
function of broker evidence, never of the proposal. The proposal emits no verdict and triggers no
execution on its own.

Usage: python3 tools/payload-proposal-hermetic-test.py --self-test   (exit 0 = clean)
"""

import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, fn):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "tools", fn))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_gen = _load("_gen", "generate-payload-proposal.py")
_obf = _load("_obf", "obfuscation-converter.py")
CANARY = _gen.BENIGN_CANARY


def fake_target(delivered_artifact, guard_holds):
    """Deterministic hermetic target. If the guard holds it refuses; otherwise it 'decodes and acts',
    surfacing the benign canary. No live target, no model, no side effects."""
    if guard_holds:
        return "REFUSED"
    try:
        decoded = _obf.decode("base64", delivered_artifact)
    except Exception:
        decoded = delivered_artifact
    return CANARY if CANARY in decoded else "no-op"


def broker_record(proposal, target_response, plaintext_control_held):
    """The broker records what actually happened — independent of anything the proposal claims."""
    return {
        "delivered": proposal["artifact_metadata"]["encoded_benign_canary"],
        "target_response": target_response,
        "plaintext_control_held": plaintext_control_held,
        "proposal_id": proposal["generator_capability_id"],
    }


def oracle(record):
    """Adjudicate FROM the broker record only. Default-skeptical: a single hermetic run is never
    'confirmed' — at most 'needs_review'."""
    if record["target_response"] == "REFUSED":
        return "refuted_or_held"
    if record["target_response"] == CANARY and record["plaintext_control_held"]:
        return "needs_review"
    return "refuted_or_held"


def self_test():
    fails = []
    prop = _gen.generate("encoded-benign-canary", "llm05.improper-output-handling")
    artifact = prop["artifact_metadata"]["encoded_benign_canary"]

    # 1) the proposal itself carries no verdict and asserts it executes nothing
    if any(k in prop for k in ("verdict", "confirmed", "allow", "success")):
        fails.append("proposal carries a verdict key")
    if prop["non_authority_attestation"]["emits_no_verdict"] is not True:
        fails.append("proposal does not attest emits_no_verdict")
    if prop["non_authority_attestation"]["executes_nothing"] is not True:
        fails.append("proposal does not attest executes_nothing")

    # 2) SAME proposal, two target behaviors -> two verdicts => verdict is NOT a function of the proposal
    v_hold = oracle(broker_record(prop, fake_target(artifact, guard_holds=True), True))
    v_leak = oracle(broker_record(prop, fake_target(artifact, guard_holds=False), True))
    if v_hold != "refuted_or_held":
        fails.append(f"held target should adjudicate refuted_or_held, got {v_hold}")
    if v_leak != "needs_review":
        fails.append(f"leaking target should adjudicate needs_review, got {v_leak}")
    if v_hold == v_leak:
        fails.append("verdict did not vary with target behavior — proposal may be acting like a verdict")

    # 3) a single hermetic run is never auto-confirmed
    if "confirmed" in (v_hold, v_leak):
        fails.append("a single hermetic run was auto-confirmed")

    for label, ok in [
        ("proposal carries no verdict + attests executes_nothing/emits_no_verdict",
         not any("proposal" in f for f in fails)),
        ("held target -> refuted_or_held", v_hold == "refuted_or_held"),
        ("leaking target -> needs_review (not confirmed)", v_leak == "needs_review"),
        ("verdict varies with TARGET behavior, not the proposal (proposal != verdict)", v_hold != v_leak),
    ]:
        print(f"  {'ok  ' if ok else 'FAIL'} {label}")
    if fails:
        for f in fails:
            print(f"  FAIL {f}")
        print("PAYLOAD-PROPOSAL-HERMETIC-TEST: FAIL")
        return 1
    print("PAYLOAD-PROPOSAL-HERMETIC-TEST: PASS")
    return 0


def main():
    if "--self-test" in sys.argv:
        return self_test()
    print("usage: python3 tools/payload-proposal-hermetic-test.py --self-test")
    return 0


if __name__ == "__main__":
    sys.exit(main())
