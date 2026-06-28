#!/usr/bin/env python3
"""Casebook retrieval index — E-track memory slice (thin, local, read-only).

A SENSOR over already-scrubbed casebooks: given a query, return the most relevant prior cases as
`memory_item`-shaped records (schemas/memory-item.schema.json), each labeled a non-authoritative
"retrieved_prior". It is the thin local alternative to adopting a heavy memory stack (Fortemi) — it
delivers semantic-ish recall over a small markdown corpus with zero external dependency.

Hard invariants (the firewall):
  - **Read-only.** It never writes any plane; it only reads casebooks/*/lessons.md (already scrubbed).
  - **No verdict.** A returned record carries NO confirmed/allow/verdict field. Retrieval informs which
    cards to consider; it can never confirm a finding or authorize a candidate. Disabling this index must
    change no verdict (firewall property) — the oracle/broker stay authoritative.
  - **Sanitized-only.** It indexes the output of the Decision-0001 staging pipeline, never raw sources.

Scoring is stdlib term-overlap (no embeddings dependency); good enough for a small corpus and trivially
swappable for a richer backend later behind the same retrieve() contract.

Usage:
  python3 tools/casebook-retrieval-index.py --query "client supplied tenant selector" --top-k 3
  python3 tools/casebook-retrieval-index.py --self-test       # exit 0 = clean (incl. firewall check)
"""

import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASEBOOKS = os.path.join(ROOT, "casebooks")
FORBIDDEN_KEYS = ("verdict", "confirmed", "allow", "authorizes")  # the firewall: retrieval is no judge


def _tokens(text):
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def load_index():
    """Build memory_item-shaped records from scrubbed casebook lessons. Read-only."""
    items = []
    if not os.path.isdir(CASEBOOKS):
        return items
    for name in sorted(os.listdir(CASEBOOKS)):
        cdir = os.path.join(CASEBOOKS, name)
        if name.startswith("_") or not os.path.isdir(cdir):
            continue
        for fn in ("lessons.md", "promotion-notes.md"):
            fp = os.path.join(cdir, fn)
            if not os.path.isfile(fp):
                continue
            text = open(fp, errors="ignore").read()
            items.append({
                "id": f"{name}:{fn}",
                "source_type": "casebook",
                "sanitized_text": text,
                "allowed_planes": ["plane-3", "plane-4"],
                "redaction_attestation": {"redacted": True, "by": "casebook-anonymization"},
                "_tokens": _tokens(text),
                "_source_ref": os.path.relpath(fp, ROOT),
                "_casebook_id": name,
            })
    return items


def retrieve(query, top_k=3, index=None):
    """Return up to top_k priors as non-authoritative retrieved_prior records (no verdict, ever)."""
    index = index if index is not None else load_index()
    q = _tokens(query)
    scored = []
    for it in index:
        overlap = len(q & it["_tokens"])
        if overlap == 0:
            continue
        score = overlap / (len(q) or 1)
        excerpt = it["sanitized_text"].strip().replace("\n", " ")[:240]
        scored.append({
            "kind": "retrieved_prior",          # explicit: NON-authoritative sensor output
            "authoritative": False,
            "casebook_id": it["_casebook_id"],
            "scrubbed_excerpt": excerpt,
            "score": round(score, 3),
            "source_ref": it["_source_ref"],
        })
    scored.sort(key=lambda r: r["score"], reverse=True)
    return scored[:top_k]


def self_test():
    index = load_index()
    fails = []
    # firewall 1: index records conform to the memory_item shape and carry no judge keys
    for it in index:
        for k in FORBIDDEN_KEYS:
            if k in it:
                fails.append(f"index record {it['id']} carries forbidden judge key {k!r}")
        for req in ("id", "source_type", "sanitized_text", "allowed_planes", "redaction_attestation"):
            if req not in it:
                fails.append(f"index record {it['id']} missing required memory_item field {req!r}")
        if "plane-1" in it.get("allowed_planes", []):
            fails.append(f"index record {it['id']} claims plane-1 write access")
    # firewall 2: retrieval results are non-authoritative and verdict-free
    results = retrieve("client supplied selector tenant authorization", top_k=3, index=index)
    for r in results:
        if r.get("authoritative") is not False or r.get("kind") != "retrieved_prior":
            fails.append("a result is not labeled non-authoritative retrieved_prior")
        for k in FORBIDDEN_KEYS:
            if k in r:
                fails.append(f"a result carries forbidden judge key {k!r}")
    print(f"  ok   index built read-only over {len(index)} scrubbed casebook record(s)")
    print(f"  {'ok  ' if all('forbidden judge key' not in f for f in fails) else 'FAIL'} "
          f"firewall: no verdict/confirm/allow key in index or results")
    print(f"  ok   retrieve() returned {len(results)} non-authoritative prior(s)")
    if fails:
        for f in fails:
            print(f"  FAIL {f}")
        print("CASEBOOK-RETRIEVAL-INDEX: FAIL")
        return 1
    print("CASEBOOK-RETRIEVAL-INDEX: PASS")
    return 0


def main():
    ap = argparse.ArgumentParser(description="thin read-only casebook retrieval index (E-track memory)")
    ap.add_argument("--query")
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        return self_test()
    if a.query:
        import json
        print(json.dumps(retrieve(a.query, a.top_k), indent=2))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
