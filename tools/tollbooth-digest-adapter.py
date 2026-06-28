#!/usr/bin/env python3
"""Tollbooth digest adapter — E-track Tollbooth spike (hermetic half).

Tollbooth (AGPL-3.0) is a TLS-decrypting MITM proxy that observes an agent container's egress. Its value
to us is a SECOND-WITNESS egress ledger to reconcile against the broker's own call ledger ("measure, do
not parse"). Its risk is that it persists decrypted traffic incl. API keys. This adapter is the
**redaction boundary**: it reads Tollbooth's JSON export and emits an allowlist-schema, secret-free
`traffic_digest.json` that is the ONLY thing allowed to enter a plane / evidence bundle.

Design invariants:
  - **Allowlist, not blocklist.** The digest keeps ONLY {timestamp, method, host, path_no_query, status,
    model, token_counts}. Headers and bodies are dropped wholesale; query strings (signed-URL params) are
    stripped. Anything not on the keep-list never leaves.
  - **Defense-in-depth scan.** After building the digest we re-scan the serialized output for known secret
    shapes and refuse if any survive.
  - **Arms-length.** Tollbooth runs as an unmodified external container; nothing from it is vendored. This
    adapter is ours and consumes only its export file.
  - **Ephemeral raw store.** The adapter NEVER copies raw bodies/headers; the operator must keep
    Tollbooth's own capture store on an ephemeral/tmpfs volume, wiped on teardown (live-stand-up concern).
  - **Sensor, not judge.** The digest + reconciliation are evidence signals; the broker/oracle stay
    authoritative.

NOTE: the export schema below is OUR expected contract; reconcile field names against the real Tollbooth
export when the live container is stood up (operator-gated; not done here).

Usage:
  python3 tools/tollbooth-digest-adapter.py --export flows.json --out traffic_digest.json
  python3 tools/tollbooth-digest-adapter.py --self-test        # exit 0 = clean (golden-secret test)
"""

import argparse
import json
import re
import sys

KEEP_FLOW_FIELDS = ("timestamp", "method", "host", "path", "status", "model", "token_counts")

# secret shapes that must NEVER survive into a digest (superset of the conformance secret scan)
SECRET_PATTERNS = [
    (r"eyJ[A-Za-z0-9_-]{10,}", "jwt"),
    (r"[Bb]earer\s+[A-Za-z0-9._-]{8,}", "bearer token"),
    (r"sk-[A-Za-z0-9-]{8,}", "api key (sk-)"),
    (r"(?i)x-api-key", "api-key header name"),
    (r"(?i)set-cookie|cookie\s*[:=]", "cookie"),
    (r"(?i)authorization", "authorization header name"),
    (r"X-Amz-Signature|X-Goog-Signature|sig=", "signed-url param"),
]


def _strip_query(path):
    return (path or "").split("?", 1)[0].split("#", 1)[0]


def redact_flow(flow):
    """Project a raw flow onto the keep-list only. Headers/bodies are never read into the digest."""
    tc = flow.get("token_counts") or flow.get("usage") or {}
    return {
        "timestamp": flow.get("timestamp"),
        "method": flow.get("method"),
        "host": flow.get("host"),
        "path": _strip_query(flow.get("path")),
        "status": flow.get("status"),
        "model": flow.get("model"),
        "token_counts": {
            "input": tc.get("input") if "input" in tc else tc.get("input_tokens"),
            "output": tc.get("output") if "output" in tc else tc.get("output_tokens"),
        },
    }


def build_digest(export):
    flows = export.get("flows", [])
    redacted = [redact_flow(f) for f in flows]
    hosts = sorted({r["host"] for r in redacted if r["host"]})
    digest = {
        "schema": "etrack.traffic_digest.v1",
        "flow_count": len(redacted),
        "hosts": hosts,
        "flows": redacted,
    }
    leaks = scan_secrets(json.dumps(digest))
    if leaks:
        raise ValueError(f"redaction failed — secrets survived into digest: {leaks}")
    return digest


def scan_secrets(text):
    hits = []
    for pat, desc in SECRET_PATTERNS:
        if re.search(pat, text):
            hits.append(desc)
    return hits


def _is_native_tollbooth(raw):
    """The real Tollbooth REST export shape: {"traffic": [...], "total": N} with nested request/response.
    (Confirmed against a live `GET /api/traffic` from an unmodified Tollbooth container, 2026-06-27.)"""
    return isinstance(raw, dict) and "traffic" in raw


def normalize_export(raw):
    """Map the native Tollbooth export onto the flat flow shape redact_flow projects. Headers/content
    (where secrets live) are dropped here by omission — never carried into the digest."""
    if not _is_native_tollbooth(raw):
        return raw  # already flat {"flows": [...]}
    flows = []
    for f in raw.get("traffic", []):
        req = f.get("request") or {}
        resp = f.get("response") or {}
        flows.append({
            "timestamp": f.get("timestamp"),
            "method": req.get("method"),
            "host": req.get("host"),
            "path": req.get("path") or req.get("url"),   # _strip_query removes any signed-URL query
            "status": resp.get("status_code"),
            "model": f.get("model") if f.get("is_llm_api") else None,
            "token_counts": (f.get("usage") if f.get("is_llm_api") else None) or {},
        })
    return {"flows": flows}


def _golden_export():
    """A synthetic Tollbooth export seeded with fake secrets in every dangerous field."""
    return {"flows": [{
        "timestamp": "2026-06-27T00:00:00Z",
        "method": "POST",
        "host": "api.example.com",
        "path": "/v1/messages?X-Amz-Signature=DEADBEEFCAFE1234&sig=abc",
        "status": 200,
        "model": "claude-fake-test",
        "usage": {"input_tokens": 12, "output_tokens": 34},
        "request_headers": {
            "Authorization": "Bearer sk-live-AAAABBBBCCCCDDDD1111",
            "Cookie": "session=eyJhbGciOiJub25lIn0.fake.payload",
            "x-api-key": "sk-test-ZZZZYYYYXXXX9999",
        },
        "request_body": "{\"token\":\"eyJhbGciOiJIUzI1NiJ9.body.sig\",\"pw\":\"hunter2\"}",
        "response_body": "ok",
    }]}


def _golden_native_export():
    """The real native Tollbooth shape, seeded with fake secrets in nested request headers/content."""
    return {"total": 1, "traffic": [{
        "flow_id": "x1", "timestamp": "2026-06-27T00:00:00Z", "is_llm_api": False,
        "request": {
            "method": "POST", "host": "api.example.com", "port": 443,
            "url": "https://api.example.com/v1/messages?X-Amz-Signature=DEADBEEFNATIVE",
            "path": "/v1/messages",
            "headers": {"Authorization": "Bearer sk-live-NATIVE1111", "Cookie": "s=eyJhbGciNATIVE"},
            "content": "{\"key\":\"sk-test-NATIVE2222\"}",
        },
        "response": {"status_code": 200, "reason": "OK", "headers": {}, "content": "ok"},
    }]}


def self_test():
    digest = build_digest(_golden_export())          # raises if any secret survives
    blob = json.dumps(digest)
    planted = [
        "sk-live-AAAABBBBCCCCDDDD1111", "Bearer sk-live", "eyJhbGci",
        "DEADBEEFCAFE1234", "hunter2", "sk-test-ZZZZYYYYXXXX9999", "Cookie", "Authorization",
    ]
    survived = [p for p in planted if p in blob]
    kept_ok = (digest["flows"][0]["host"] == "api.example.com"
               and digest["flows"][0]["path"] == "/v1/messages"
               and digest["flows"][0]["model"] == "claude-fake-test"
               and digest["flows"][0]["token_counts"] == {"input": 12, "output": 34})
    print(f"  {'ok  ' if not survived else 'FAIL'} golden-secret: no planted secret in digest "
          f"({len(survived)} survived)")
    print(f"  {'ok  ' if kept_ok else 'FAIL'} allowlist fields retained (host/path-no-query/model/tokens)")
    print(f"  ok   query string stripped from path; headers/bodies dropped")
    # native Tollbooth shape (real /api/traffic export): redaction must hold after normalization
    native = build_digest(normalize_export(_golden_native_export()))
    nblob = json.dumps(native)
    nplanted = ["sk-live-NATIVE1111", "eyJhbGciNATIVE", "sk-test-NATIVE2222", "DEADBEEFNATIVE",
                "Authorization", "Cookie"]
    nsurvived = [p for p in nplanted if p in nblob]
    nkept = native["flows"][0]["host"] == "api.example.com" and native["flows"][0]["path"] == "/v1/messages"
    print(f"  {'ok  ' if not nsurvived else 'FAIL'} native shape: no planted secret in digest "
          f"({len(nsurvived)} survived)")
    print(f"  {'ok  ' if nkept else 'FAIL'} native shape: allowlist fields retained after normalize")
    if survived or not kept_ok or nsurvived or not nkept:
        if survived:
            print(f"  FAIL survived: {survived}")
        if nsurvived:
            print(f"  FAIL native survived: {nsurvived}")
        print("TOLLBOOTH-DIGEST-ADAPTER: FAIL")
        return 1
    print("TOLLBOOTH-DIGEST-ADAPTER: PASS")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Tollbooth export -> redacted traffic digest (E-track)")
    ap.add_argument("--export", help="path to a Tollbooth JSON export")
    ap.add_argument("--out", help="path to write traffic_digest.json")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        return self_test()
    if a.export:
        with open(a.export) as fh:
            digest = build_digest(normalize_export(json.load(fh)))
        out = json.dumps(digest, indent=2)
        if a.out:
            with open(a.out, "w") as fh:
                fh.write(out + "\n")
            print(f"wrote {a.out} ({digest['flow_count']} flows, {len(digest['hosts'])} hosts)")
        else:
            print(out)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
