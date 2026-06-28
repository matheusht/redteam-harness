#!/usr/bin/env python3
"""First hermetic payload-PROPOSAL generator — E-track PG-3A.2 (no execution, benign only).

Produces a schema-valid `payload_proposal` (schemas/payload-proposal.schema.json) describing a BENIGN
artifact (an encoded benign canary). It is the `payload_generator` lane's first producer: it PROPOSES,
it does not execute, it calls no external AGPL tool, it generates no harmful content, and it emits no
verdict. The artifact value is just a benign canary run through the harness's own stdlib obfuscation
converter. The broker/oracle remain authoritative.

Safety fences (enforced here):
  - only BENIGN kinds (encoded/plaintext benign canary). Exploit/chain kinds are REFUSED — those are
    zone2 and require operator confirmation + an impact_demo_ref, not autonomous generation.
  - the generated proposal is validated against the SAME conformance predicate CI uses, so it can never
    drift from the keyhole.
  - non_authority_attestation is always proposal_only / executes_nothing / emits_no_verdict.

Usage:
  python3 tools/generate-payload-proposal.py --kind encoded-benign-canary \
      --objective llm05.improper-output-handling --out /path/proposal.json
  python3 tools/generate-payload-proposal.py --self-test
"""

import argparse
import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BENIGN_CANARY = "benign-preamble-canary"

# only benign kinds — exploit/chain are intentionally NOT generatable here
KINDS = {
    "encoded-benign-canary": {"payload_class": "encoded_prompt", "risk_tier": "benign_canary", "encode": "base64"},
    "plaintext-benign-canary": {"payload_class": "text_prompt", "risk_tier": "benign_canary", "encode": None},
}


def _load(name, fn):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "tools", fn))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_obf = _load("_obf", "obfuscation-converter.py")
_cc = _load("_cc", "check-conformance.py")  # reuse the SAME validation predicate CI uses


def generate(kind, objective):
    if kind not in KINDS:
        raise ValueError(f"refused: kind {kind!r} is not a benign generatable kind "
                         f"(allowed: {sorted(KINDS)}). exploit/chain kinds require operator confirmation.")
    spec = KINDS[kind]
    artifact = _obf.encode(spec["encode"], BENIGN_CANARY) if spec["encode"] else BENIGN_CANARY
    return {
        "objective_id": objective,
        "payload_class": spec["payload_class"],
        "risk_tier": spec["risk_tier"],
        "approved_objective_ref": f"safe_signal benign canary for {objective}",
        "generator_capability_id": "local.encoded-benign-canary",
        "artifact_metadata": {
            "kind": kind,
            "encoding": spec["encode"] or "none",
            "encoded_benign_canary": artifact,   # benign — the literal string is a harmless canary
            "canary_is_benign": True,
        },
        "required_controls": ["matched_control_plaintext", "positive_control_decode",
                              "contamination_ruleout", "replay"],
        "containment_plan": "artifact lives only in the engagement payload-proposals dir; never sent to a "
                            "live target without operator confirmation",
        "cleanup_plan": "recorded in the engagement payload-proposals ledger; eval/temp artifacts wiped on teardown",
        "non_authority_attestation": {"proposal_only": True, "executes_nothing": True, "emits_no_verdict": True},
    }


def self_test():
    fails = []
    prop = generate("encoded-benign-canary", "llm05.improper-output-handling")
    problems = _cc.payload_proposal_problems(prop)
    if problems:
        fails.append(f"generated proposal not schema-valid: {problems}")
    if prop["non_authority_attestation"] != {"proposal_only": True, "executes_nothing": True, "emits_no_verdict": True}:
        fails.append("attestation not proposal-only / executes-nothing / no-verdict")
    if not prop["artifact_metadata"]["canary_is_benign"]:
        fails.append("artifact not marked benign")
    # the generator must REFUSE exploit/chain kinds
    refused = False
    try:
        generate("exploit_poc", "x")
    except ValueError:
        refused = True
    if not refused:
        fails.append("generator did not refuse an exploit kind")
    for label, ok in [
        ("generated proposal is schema-valid (same predicate as CI)", not problems),
        ("proposal is proposal-only / executes nothing / emits no verdict", not any("attestation" in f for f in fails)),
        ("artifact is a benign canary", prop["artifact_metadata"]["canary_is_benign"]),
        ("generator refuses exploit/chain kinds", refused),
    ]:
        print(f"  {'ok  ' if ok else 'FAIL'} {label}")
    if fails:
        for f in fails:
            print(f"  FAIL {f}")
        print("GENERATE-PAYLOAD-PROPOSAL: FAIL")
        return 1
    print("GENERATE-PAYLOAD-PROPOSAL: PASS")
    return 0


def main():
    ap = argparse.ArgumentParser(description="hermetic benign payload-proposal generator (PG-3A)")
    ap.add_argument("--kind", choices=sorted(KINDS))
    ap.add_argument("--objective", default="llm05.improper-output-handling")
    ap.add_argument("--out")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        return self_test()
    if a.kind:
        prop = generate(a.kind, a.objective)
        problems = _cc.payload_proposal_problems(prop)
        if problems:  # never emit an invalid proposal
            print(f"refused: generated proposal failed validation: {problems}", file=sys.stderr)
            return 1
        out = json.dumps(prop, indent=2)
        if a.out:
            os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
            with open(a.out, "w") as fh:
                fh.write(out + "\n")
            print(f"wrote benign proposal -> {a.out} (executes nothing; oracle adjudicates)")
        else:
            print(out)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
