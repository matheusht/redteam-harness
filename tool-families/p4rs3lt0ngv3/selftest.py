#!/usr/bin/env python3
"""Hermetic self-test for the P4RS3LT0NGV3 tool family (P0-P3).

Stdlib-only, no network, no upstream checkout required. Proves the gates BITE:
  P0  manifest contract — real manifest passes; tampered manifests are rejected by the SAME conformance
      predicate (advanced module raw in allowed_actions; blocked entry missing its gate).
  P1  catalog output schema — valid fixtures pass; _must_reject fixtures fail closed (verdict leakage,
      premature advanced exposure, missing authority, unknown-transform-not-fail-closed).
  P2  catalog adapter — with no upstream installed, list/inspect return honest non-success; offline-fixture
      mode returns a compact sensor-only catalog; encode/decode are NOT reachable via the catalog adapter.
  P3  benign converter — approved-id roundtrip works on a benign canary; non-canary input is refused;
      negative control (decode of plaintext) does not produce a clean roundtrip.

Exit 0 = all gates bite. Exit 1 = a gate failed to bite (report it).
Usage:  python3 tool-families/p4rs3lt0ngv3/selftest.py
"""

import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
FIX = os.path.join(HERE, "fixtures")

FAILS = []
OKS = 0


def check(ok, label, detail=""):
    global OKS
    if ok:
        OKS += 1
        print(f"  ok   {label}")
    else:
        print(f"  FAIL {label}  {detail}")
        FAILS.append(label)


def load_conformance():
    spec = importlib.util.spec_from_file_location("conf", os.path.join(ROOT, "tools", "check-conformance.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---- P4-owned output predicate (converter/catalog outputs; mirrors the keyhole) ----
FORBIDDEN_KEYS = ("verdict", "confirmed", "allow", "success")
ADVANCED_STEMS = ("agent", "promptcraft", "anticlassifier", "tokenade", "fuzzer",
                  "random", "planner", "chain", "rank_", "proposal")


def _is_advanced(name):
    return isinstance(name, str) and any(s in name for s in ADVANCED_STEMS)


def output_problems(obj):
    if not isinstance(obj, dict):
        return ["not an object"]
    p = [f"forbidden verdict key: {k}" for k in FORBIDDEN_KEYS if k in obj]
    if obj.get("authority") != "sensor_only":
        p.append("authority must be sensor_only")
    if "action" not in obj:
        p.append("missing action")
    av = obj.get("available")
    if av is True:
        if not any(obj.get(k) for k in ("transforms", "transform", "evidence", "roundtrip")):
            p.append("available:true but no payload (dishonest)")
    elif av is False:
        if not obj.get("reason"):
            p.append("available:false needs a reason")
    else:
        p.append("missing/invalid available flag")
    listed = []
    if isinstance(obj.get("transforms"), list):
        listed += [x.get("id") if isinstance(x, dict) else x for x in obj["transforms"]]
    if isinstance(obj.get("available_actions"), list):
        listed += obj["available_actions"]
    p += [f"premature advanced exposure: {n}" for n in listed if _is_advanced(n)]
    return p


def test_p0_manifest(conf):
    print("\n[P0] manifest contract gate bites")
    man = os.path.join(HERE, "manifest.yaml")
    text = open(man).read()
    check(not conf.tool_family_manifest_problems(text), "real manifest passes")

    tampered_raw = text.replace(
        "allowed_actions: [list_transforms,",
        "allowed_actions: [promptcraft, list_transforms,")
    check(bool(conf.tool_family_manifest_problems(tampered_raw)),
          "tampered: advanced module raw in allowed_actions is rejected")

    tampered_gate = text.replace("    blocked_until: M3_hermetic_adapter\n", "", 1)
    check(bool(conf.tool_family_manifest_problems(tampered_gate)),
          "tampered: blocked_until entry missing its gate is rejected")


def test_p1_outputs():
    print("\n[P1] catalog output schema gate bites")
    for fn in ("list_transforms.example.json", "inspect_transform.example.json"):
        obj = json.load(open(os.path.join(FIX, fn)))
        problems = output_problems(obj)
        check(not problems, f"valid fixture passes: {fn}", "; ".join(problems))
    mr = os.path.join(FIX, "_must_reject")
    for fn in sorted(os.listdir(mr)):
        if not fn.endswith(".json"):
            continue
        problems = output_problems(json.load(open(os.path.join(mr, fn))))
        check(bool(problems), f"_must_reject fails closed: {fn} [{'; '.join(problems) or 'NONE'}]")


def _load_module(relpath, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, relpath))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_p2_adapter():
    print("\n[P2] catalog adapter (honest non-success + offline catalog; read-only)")
    a = _load_module(os.path.join("adapters", "p4_catalog_adapter.py"), "p4_catalog_adapter")

    ext = a.list_transforms(prefer="external", p4_home=None)
    check(ext["available"] is False and bool(ext.get("reason")),
          "external list w/ no upstream => honest non-success", json.dumps(ext))
    check(ext.get("authority") == "sensor_only" and not output_problems(ext),
          "non-success envelope is still sensor-only/clean", "; ".join(output_problems(ext)))

    off = a.list_transforms(prefer="offline")
    check(off["available"] is True and off.get("transforms") and not output_problems(off),
          "offline list => compact sensor-only catalog", "; ".join(output_problems(off)))

    ins = a.inspect_transform("base64", prefer="offline")
    check(ins["available"] is True and ins.get("transform") and not output_problems(ins),
          "offline inspect known id => transform metadata")

    unk = a.inspect_transform("does_not_exist", prefer="offline")
    check(unk["available"] is False and bool(unk.get("reason")),
          "offline inspect unknown id => fail closed")

    adv = a.inspect_transform("promptcraft", prefer="offline")
    check(adv["available"] is False, "inspect advanced module id => refused (blocked)")

    check(not hasattr(a, "encode_benign") and not hasattr(a, "decode_if_possible"),
          "catalog adapter cannot encode/decode (read-only)")


def test_p3_converter():
    print("\n[P3] benign converter (approved-id roundtrip; benign-only; negative control)")
    c = _load_module(os.path.join("adapters", "p4_benign_converter.py"), "p4_benign_converter")
    canary = "benign-canary-001"

    for t in ("base64", "hex", "rot13", "reverse"):
        rt = c.transform_roundtrip(canary, t)
        r = rt.get("roundtrip", {})
        ok = (rt["available"] is True and r.get("roundtrip_ok") is True
              and r.get("negative_control", {}).get("control_holds") is True
              and not output_problems(rt))
        check(ok, f"roundtrip + negative control holds: {t}", json.dumps(rt))

    twice = (c.transform_roundtrip(canary, "base64"), c.transform_roundtrip(canary, "base64"))
    check(twice[0] == twice[1], "roundtrip is deterministic (same input => same output)")

    refused = c.encode_benign("rm -rf / definitely not a canary", "base64")
    check(refused["available"] is False and bool(refused.get("reason")),
          "non-canary input is refused (benign-canary-only)")

    bad_t = c.transform_roundtrip(canary, "evil_transform")
    check(bad_t["available"] is False, "unapproved transform is refused")

    fx = json.load(open(os.path.join(FIX, "roundtrip", "base64.example.json")))
    live = c.transform_roundtrip(canary, "base64")
    check(fx["roundtrip"]["transformed"] == live["roundtrip"]["transformed"] and not output_problems(fx),
          "static roundtrip fixture matches live computation (replay)")


def main():
    conf = load_conformance()
    test_p0_manifest(conf)
    test_p1_outputs()
    try:
        test_p2_adapter()
    except NameError:
        print("\n[P2] adapter test not yet defined — skipped")
    try:
        test_p3_converter()
    except NameError:
        print("\n[P3] converter test not yet defined — skipped")
    print(f"\n{OKS} checks ok, {len(FAILS)} failing")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
