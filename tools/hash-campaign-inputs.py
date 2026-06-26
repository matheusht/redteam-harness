#!/usr/bin/env python3
"""Hash the frozen inputs of a GEPA campaign (Phase 2 helper).

Every input that affects acceptance — routing gold, crosswalk, false-discovery / adversarial corpora,
hermetic targets, the scorers themselves — is hashed into the campaign manifest's `frozen_inputs`
block. tools/check-campaign.py recomputes those hashes and BLOCKS on drift, so this helper is how you
freeze a campaign and how CI proves the benchmark wasn't tampered with mid-run.

Usage:
  python3 tools/hash-campaign-inputs.py <path> [<path> ...]   # emit a frozen_inputs JSON block
  python3 tools/hash-campaign-inputs.py --check <campaign.json> # re-hash, report drift (exit 1 on drift)
  python3 tools/hash-campaign-inputs.py --self-test
"""

import hashlib
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def name_for(path):
    rel = os.path.relpath(path, ROOT)
    return rel.replace("/", ":").replace(".json", "").replace(".py", "")


def emit(paths):
    block = {}
    for p in paths:
        ap = p if os.path.isabs(p) else os.path.join(ROOT, p)
        rel = os.path.relpath(ap, ROOT)
        block[name_for(ap)] = {"path": rel, "sha256": sha256_file(ap)}
    return block


def check(campaign_path):
    camp = json.load(open(campaign_path))
    drift = []
    for name, spec in camp.get("frozen_inputs", {}).items():
        ap = os.path.join(ROOT, spec["path"])
        if not os.path.isfile(ap):
            drift.append(f"{name}: missing {spec['path']}")
        elif sha256_file(ap) != spec["sha256"]:
            drift.append(f"{name}: drifted {spec['path']}")
    for d in drift:
        print(f"  DRIFT {d}")
    print("frozen inputs:", "DRIFT" if drift else "intact")
    return 1 if drift else 0


def self_test():
    ok = True
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, "x.json")
        open(f, "w").write('{"a":1}\n')
        h1 = sha256_file(f)
        h2 = sha256_file(f)
        if h1 != h2:
            ok = False
            print("[self-test] hash not stable")
        open(f, "w").write('{"a":2}\n')
        if sha256_file(f) == h1:
            ok = False
            print("[self-test] hash did not change on edit")
    print("[self-test] hash stable + change-sensitive:", "ok" if ok else "FAIL")
    print("\nSELF-TEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv):
    if len(argv) == 2 and argv[1] == "--self-test":
        return self_test()
    if len(argv) == 3 and argv[1] == "--check":
        return check(argv[2])
    if len(argv) >= 2:
        print(json.dumps(emit(argv[1:]), indent=2))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
