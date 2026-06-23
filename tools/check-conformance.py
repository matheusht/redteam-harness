#!/usr/bin/env python3
"""Conformance checker for the llm-redteam-harness (Phase 2.5A, baby version).

Stdlib-only — no YAML/JSON-schema dependency, so it runs in any CI. It validates the structural
contracts the orchestrator relies on, NOT semantics:

  - every card has a delimited front-matter block with id + type
  - pattern cards declare activation.strong / .weak / .negative
  - vuln cards declare safe_signal
  - routes_to: non-stub ids resolve (pattern.<id> or vulns/<dir>); stub: ids are quoted + skipped
  - casebooks reference only pattern ids that exist
  - no live-secret shapes leaked into any casebook file

Usage:  python3 tools/check-conformance.py        (exit 0 = clean, 1 = failures)
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FAILS = []
CHECKS = 0


def record(ok, label, detail=""):
    global CHECKS
    CHECKS += 1
    if ok:
        print(f"  ok   {label}")
    else:
        print(f"  FAIL {label}  {detail}")
        FAILS.append(f"{label}  {detail}")


def front_matter(text):
    if not text.startswith("---"):
        return None
    parts = text.split("\n---", 2)
    if len(parts) < 2:
        return None
    return parts[0].lstrip("-\n")


def get_key(fm, key):
    m = re.search(rf"^{re.escape(key)}:\s*(.*)$", fm, re.MULTILINE)
    return m.group(1).strip() if m else None


def list_cards(subdir):
    base = os.path.join(ROOT, "skills", subdir)
    if not os.path.isdir(base):
        return []
    out = []
    for name in sorted(os.listdir(base)):
        path = os.path.join(base, name, "SKILL.md")
        if os.path.isfile(path):
            out.append((name, path))
    return out


def collect_pattern_ids():
    ids = {}
    for name, path in list_cards("patterns"):
        fm = front_matter(open(path).read()) or ""
        cid = get_key(fm, "id")
        if cid:
            ids[cid] = name
    return ids


def check_cards(subdir, pattern_ids):
    print(f"\n[cards] skills/{subdir}/")
    for name, path in list_cards(subdir):
        text = open(path).read()
        fm = front_matter(text)
        record(fm is not None, f"{subdir}/{name}: front-matter present")
        if fm is None:
            continue
        record(get_key(fm, "id") is not None, f"{subdir}/{name}: has id")
        record(get_key(fm, "type") is not None, f"{subdir}/{name}: has type")

        if subdir == "vulns":
            record("safe_signal:" in fm, f"{subdir}/{name}: vuln has safe_signal")

        if subdir == "patterns":
            has_act = re.search(r"^activation:", fm, re.MULTILINE)
            record(bool(has_act), f"{subdir}/{name}: has activation block")
            for tier in ("strong", "weak", "negative"):
                record(bool(re.search(rf"^\s+{tier}:", fm, re.MULTILINE)),
                       f"{subdir}/{name}: activation.{tier}")

        check_routes_to(name, subdir, fm, pattern_ids)


def check_routes_to(name, subdir, fm, pattern_ids):
    line = re.search(r"^routes_to:\s*(\[[^\]]*\])", fm, re.MULTILINE)
    if not line:
        return
    raw = line.group(1)

    unquoted_stub = re.search(r'(?<!")stub:', raw)
    record(unquoted_stub is None, f"{subdir}/{name}: stub ids are quoted",
           "found unquoted stub: in routes_to" if unquoted_stub else "")

    entries = [e.strip().strip('"').strip("'") for e in raw[1:-1].split(",") if e.strip()]
    for e in entries:
        if e.startswith("stub:"):
            continue
        if e.startswith("pattern."):
            record(e in pattern_ids, f"{subdir}/{name}: route resolves {e}",
                   "no such pattern id" if e not in pattern_ids else "")
        elif e.startswith("vulns/"):
            p = os.path.join(ROOT, "skills", e, "SKILL.md")
            record(os.path.isfile(p), f"{subdir}/{name}: route resolves {e}",
                   "no such vuln card" if not os.path.isfile(p) else "")
        else:
            record(False, f"{subdir}/{name}: route form {e}", "unknown route form (use stub: / pattern. / vulns/)")


def check_oracles():
    print("\n[oracles] skills/oracles/")
    base = os.path.join(ROOT, "skills", "oracles")
    if not os.path.isdir(base):
        return
    for fn in sorted(os.listdir(base)):
        if not fn.endswith(".md"):
            continue
        fm = front_matter(open(os.path.join(base, fn)).read())
        record(fm is not None, f"oracles/{fn}: front-matter present")
        if fm is not None:
            record(get_key(fm, "id") is not None, f"oracles/{fn}: has id")
            record(get_key(fm, "type") is not None, f"oracles/{fn}: has type")


def check_casebooks(pattern_ids):
    print("\n[casebooks] pattern-id references")
    base = os.path.join(ROOT, "casebooks")
    if not os.path.isdir(base):
        return
    for name in sorted(os.listdir(base)):
        cdir = os.path.join(base, name)
        if name.startswith("_") or not os.path.isdir(cdir):
            continue
        refs = set()
        for fn in os.listdir(cdir):
            fp = os.path.join(cdir, fn)
            if os.path.isfile(fp):
                refs |= set(re.findall(r"pattern\.[a-z0-9-]+", open(fp).read()))
        unknown = sorted(r for r in refs if r not in pattern_ids)
        record(not unknown, f"casebooks/{name}: pattern refs resolve",
               f"unknown: {unknown}" if unknown else "")


SECRET_PATTERNS = [
    (r"user_[A-Za-z0-9]{20,}", "clerk-style user id"),
    (r"\b019[0-9a-f]{2}-[0-9a-f]{4}-[0-9a-f]{4}", "uuidv7-style id"),
    (r"eyJ[A-Za-z0-9_-]{10,}", "jwt"),
    (r"[Bb]earer\s+[A-Za-z0-9._-]{12,}", "bearer token value"),
    (r"XTENANT|EVIDENCE-[0-9A-F]{6,}", "engagement canary token"),
]


def check_secrets():
    print("\n[secrets] casebook scan")
    base = os.path.join(ROOT, "casebooks")
    hits = []
    for dirpath, _, files in os.walk(base):
        for fn in files:
            fp = os.path.join(dirpath, fn)
            text = open(fp, errors="ignore").read()
            for pat, desc in SECRET_PATTERNS:
                for m in re.finditer(pat, text):
                    hits.append(f"{os.path.relpath(fp, ROOT)}: {desc} :: {m.group(0)[:24]}")
    record(not hits, "casebooks contain no live-secret shapes",
           "; ".join(hits) if hits else "")


def main():
    pattern_ids = collect_pattern_ids()
    print(f"known pattern ids: {sorted(pattern_ids)}")
    for subdir in ("patterns", "vulns", "techniques"):
        check_cards(subdir, pattern_ids)
    check_oracles()
    check_casebooks(pattern_ids)
    check_secrets()

    print(f"\n{CHECKS} checks, {len(FAILS)} failing")
    if FAILS:
        print("CONFORMANCE: FAIL")
        return 1
    print("CONFORMANCE: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
