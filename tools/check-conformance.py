#!/usr/bin/env python3
"""Conformance checker for the llm-redteam-harness (Phase 2.5A, baby version).

Stdlib-only — no YAML/JSON-schema dependency, so it runs in any CI. It validates the structural
contracts the orchestrator relies on, NOT semantics:

  - every card has a delimited front-matter block with id + type
  - pattern cards declare activation.strong / .weak / .negative
  - vuln cards declare safe_signal
  - routes_to: non-stub ids resolve (pattern.<id> or vulns/<dir>); stub: ids are quoted + skipped
  - casebooks reference only pattern ids that exist
  - no live-secret shapes leaked into any casebook / fixture / eval file
  - finding fixtures honor the evidence-contract migration gate (Phase 2.5A)
  - the false-discovery corpus has a zero invalid-accept rate
  - the adversarial-candidate corpus is well-formed (>=1 retain, all immutable-touching = block)

Structural only: a green run means the evidence CONTRACT is present and well-formed (necessary), NOT
that any finding is true (the model oracle still adjudicates that). Do not read green as "confirmed".

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


def check_cards(subdir, pattern_ids, cap_ids):
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
        check_optional_capabilities(name, subdir, fm, cap_ids)


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


def collect_capability_ids():
    ids = set()
    path = os.path.join(ROOT, "capabilities", "registry.yaml")
    if os.path.isfile(path):
        for m in re.finditer(r"^\s*-\s*id:\s*([A-Za-z0-9._-]+)", open(path).read(), re.MULTILINE):
            ids.add(m.group(1))
    return ids


def _capability_blocks(text):
    return [(m.group(1), m.group(2)) for m in re.finditer(
        r"^\s*-\s*id:\s*([A-Za-z0-9._-]+)\s*\n(.*?)(?=^\s*-\s*id:|\Z)", text, re.MULTILINE | re.DOTALL)]


# actions that may NEVER appear in a capability's allowed_actions (payload generators / agent modes /
# raw-offense). The keyhole must exclude these mechanically, not by convention.
DANGEROUS_ACTIONS = {
    "agent", "promptcraft", "anticlassifier", "injector", "tokenade", "fuzzer",
    "embed_arbitrary_payload", "conceal_agent", "jailbreak_templates", "raw_payload_promotion",
    "semantic_stego_raw", "token_exploit_raw", "harmful_probe_sets", "offense_modules",
}


def _cap_list(body, key):
    m = re.search(rf"^\s*{key}:\s*\[([^\]]*)\]", body, re.MULTILINE)
    return [x.strip().strip('"').strip("'") for x in m.group(1).split(",") if x.strip()] if m else []


def _get_field(body, key):
    m = re.search(rf"^\s*{key}:\s*(\S+)", body, re.MULTILINE)
    return m.group(1).strip() if m else None


def _payload_generator_problems(body):
    """A payload_generator entry: proposal-only, gated, never a judge or executor."""
    p = []
    auth = _get_field(body, "authority")
    if auth != "proposal_only":
        p.append("payload_generator authority must be proposal_only")
    if auth in ("oracle", "judge", "verdict", "confirmed", "allow", "success"):
        p.append(f"payload_generator claims forbidden authority: {auth}")
    if re.search(r"^\s*default:\s*disabled\s*$", body, re.MULTILINE) is None:
        p.append("payload_generator not default: disabled")
    if re.search(r"^\s*forbidden_actions:\s*\[", body, re.MULTILINE) is None:
        p.append("no forbidden_actions")
    for gate in ("scope_allows_payload_generation", "containment_plan", "oracle_separation"):
        if gate not in body:
            p.append(f"payload_generator missing required gate: {gate}")
    if _get_field(body, "payload_class") is None and "declared_payload_class" not in body:
        p.append("payload_generator missing declared payload_class")
    bad_emit = sorted(set(_cap_list(body, "emits")) & {"confirmed", "allow", "verdict", "success"})
    if bad_emit:
        p.append(f"payload_generator emits forbidden verdict tokens: {bad_emit}")
    return p


def capability_entry_problems(body):
    """Pure predicate — reasons a single registry entry violates its class contract (empty = clean).
    Class-aware: payload_generator -> proposal-only + gated; everything else -> the sensor_only keyhole.
    The single source of truth reused by check_capabilities and the _must_reject corpus."""
    if _get_field(body, "class") == "payload_generator":
        return _payload_generator_problems(body)
    p = []
    if re.search(r"^\s*authority:\s*sensor_only\s*$", body, re.MULTILINE) is None:
        p.append("authority not sensor_only")
    if re.search(r"^\s*authority:\s*(oracle|judge|authoritative|verdict)\b", body, re.MULTILINE):
        p.append("claims oracle/judge authority")
    if re.search(r"^\s*forbidden_actions:\s*\[", body, re.MULTILINE) is None:
        p.append("no forbidden_actions")
    if re.search(r"^\s*source:\s*\S+", body, re.MULTILINE) is None:
        p.append("no source")
    if re.search(r"^\s*license:\s*\S+", body, re.MULTILINE) is None:
        p.append("no license")
    allowed = set(_cap_list(body, "allowed_actions"))
    forbidden = set(_cap_list(body, "forbidden_actions"))
    if allowed & DANGEROUS_ACTIONS:
        p.append(f"dangerous in allowed_actions: {sorted(allowed & DANGEROUS_ACTIONS)}")
    if allowed & forbidden:
        p.append(f"allowed/forbidden overlap: {sorted(allowed & forbidden)}")
    return p


def check_capability_classes():
    """Validate capabilities/classes.yaml — the authority model. payload_generator must be proposal-only,
    default-disabled, gated, and forbidden from oracle/judge/verdict authority; only `oracle` may judge."""
    print("\n[capabilities] capability classes (authority model)")
    path = os.path.join(ROOT, "capabilities", "classes.yaml")
    if not os.path.isfile(path):
        return
    blocks = _capability_blocks(open(path).read())
    record(len(blocks) > 0, "classes: non-empty")
    by_id = {cid: body for cid, body in blocks}
    for cid, body in blocks:
        record(_get_field(body, "authority") is not None, f"classes/{cid}: declares authority")
        if cid != "oracle":
            record(_get_field(body, "authority") not in ("oracle", "judge", "verdict"),
                   f"classes/{cid}: non-oracle class doesn't claim oracle/judge authority")
    pg = by_id.get("payload_generator")
    if pg is not None:
        record(_get_field(pg, "authority") == "proposal_only",
               "classes/payload_generator: authority is proposal_only")
        record(re.search(r"^\s*default:\s*disabled\s*$", pg, re.MULTILINE) is not None,
               "classes/payload_generator: default disabled")
        for gate in ("signed_scope", "scope_allows_payload_generation", "declared_payload_class",
                     "containment_plan", "cleanup_plan", "oracle_separation"):
            record(gate in pg, f"classes/payload_generator: requires {gate}")
        for forb in ("oracle", "judge", "verdict", "confirmed", "allow"):
            record(forb in pg, f"classes/payload_generator: forbids {forb} authority")


def check_capabilities():
    """The narrow keyhole: every external capability must be sensor_only and declare its fences."""
    print("\n[capabilities] external capability registry")
    path = os.path.join(ROOT, "capabilities", "registry.yaml")
    if not os.path.isfile(path):
        return
    text = open(path).read()
    blocks = _capability_blocks(text)
    record(len(blocks) > 0, "capabilities: registry non-empty")
    for cid, body in blocks:
        problems = capability_entry_problems(body)
        record(not problems, f"capabilities/{cid}: sensor-only entry within the keyhole",
               "; ".join(problems) if problems else "")
    bad = re.findall(r"^\s*authority:\s*(oracle|judge|authoritative|verdict)\b", text, re.MULTILINE)
    record(not bad, "capabilities: no entry claims oracle/judge authority", f"found {bad}" if bad else "")


def scope_flag_problems(registry_text, template_text):
    """Pure predicate — scope_allows_* flags a registry requires that the scope template doesn't declare."""
    flags = sorted(set(re.findall(r"\bscope_allows_[a-z0-9_]+", registry_text)))
    return [f"undeclared scope flag: {f}" for f in flags if f not in template_text]


def check_capability_scope_flags():
    tmpl = os.path.join(ROOT, "engagements", "_TEMPLATE", "scope.md")
    if not os.path.isfile(tmpl):
        return
    src = ""
    for fn in ("registry.yaml", "classes.yaml"):
        fp = os.path.join(ROOT, "capabilities", fn)
        if os.path.isfile(fp):
            src += open(fp).read() + "\n"
    problems = scope_flag_problems(src, open(tmpl).read())
    record(not problems, "capabilities: every required scope flag is declared in _TEMPLATE/scope.md",
           "; ".join(problems) if problems else "")


def _card_capability_refs(fm):
    line = re.search(r"^optional_capabilities:\s*(\[[^\]]*\])", fm, re.MULTILINE)
    if not line:
        return []
    return [e.strip().strip('"').strip("'") for e in line.group(1)[1:-1].split(",") if e.strip()]


def card_capability_problems(fm, cap_ids):
    """Pure predicate — optional_capabilities ids in a card that don't resolve to a registry id."""
    return [f"unresolved: {e}" for e in _card_capability_refs(fm) if e not in cap_ids]


def check_optional_capabilities(name, subdir, fm, cap_ids):
    for e in _card_capability_refs(fm):
        record(e in cap_ids, f"{subdir}/{name}: optional_capability resolves {e}",
               "no such capability id" if e not in cap_ids else "")


def check_capability_must_reject():
    """Permanent negative tests: every fixture MUST be rejected by the SAME validation predicates.
    Converts the manual gate-bites into CI-enforced regressions (mirrors fixtures/findings/_must_reject)."""
    base = os.path.join(ROOT, "fixtures", "capabilities", "_must_reject")
    if not os.path.isdir(base):
        return
    print("\n[capabilities] _must_reject corpus (the keyhole must fail closed)")
    cap_ids = collect_capability_ids()
    tmpl = os.path.join(ROOT, "engagements", "_TEMPLATE", "scope.md")
    tmpl_text = open(tmpl).read() if os.path.isfile(tmpl) else ""
    for fn in sorted(os.listdir(base)):
        fp = os.path.join(base, fn)
        if not os.path.isfile(fp):
            continue
        content = open(fp).read()
        if fn.endswith(".md"):
            problems = card_capability_problems(front_matter(content) or "", cap_ids)
        elif "scope-flag" in fn:
            problems = scope_flag_problems(content, tmpl_text)
        else:  # registry-entry yaml
            problems = [p for _, body in _capability_blocks(content) for p in capability_entry_problems(body)]
        record(bool(problems), f"_must_reject/{fn}: rejected by the keyhole [{'; '.join(problems) or 'NONE'}]",
               "fixture should be rejected but passed all checks" if not problems else "")


# --- tool-family manifests (docs/tool-family-adapter-architecture.md) ---------------------------
# A family manifest owns the authority contract for an external toolkit. Detection is exposed; every
# advanced surface (embed/extract/injector/conceal/network/multi-layer/executor) stays in scope but is
# listed under blocked_until with its gate. The manifest fails closed: an action not explicitly allowed,
# or a staged entry missing its gates, must be rejected.

TF_FORBIDDEN_AUTHORITY = {"oracle", "judge", "authoritative", "verdict", "confirmed", "allow", "success"}


def _yaml_section(text, key):
    """Indented block under a top-level `key:` (until the next col-0 line or EOF)."""
    m = re.search(rf"^{key}:\s*\n(.*?)(?=^\S|\Z)", text, re.MULTILINE | re.DOTALL)
    return m.group(1) if m else ""


def tool_family_blocked_entry_problems(body):
    """Pure predicate — reasons a single blocked_until entry is unsafe (empty = clean). Each staged
    surface (incl. injector/template/conceal) must declare its gate, risk, scope gates, redaction, and
    non-authority language, or it does not get to sit in the manifest."""
    p = []
    if _get_field(body, "blocked_until") is None:
        p.append("missing blocked_until gate")
    if _get_field(body, "risk_tier") is None:
        p.append("missing risk_tier")
    if not _cap_list(body, "requires"):
        p.append("missing scope-gate requires[]")
    if re.search(r"^\s*redaction:\s*\S+", body, re.MULTILINE) is None:
        p.append("missing redaction rule")
    auth = _get_field(body, "authority")
    if auth is None:
        p.append("missing non-authority language (authority)")
    elif auth in TF_FORBIDDEN_AUTHORITY:
        p.append(f"claims forbidden authority: {auth}")
    if re.search(r"^\s*evidence_role:\s*\S+", body, re.MULTILINE) is None:
        p.append("missing evidence_role")
    return p


def tool_family_manifest_problems(text):
    """Pure predicate — reasons a family manifest violates the contract (empty = clean). Single source
    of truth reused by check_tool_family_manifests and the _must_reject corpus."""
    p = []
    if re.search(r"^family_id:\s*\S+", text, re.MULTILINE) is None:
        p.append("missing family_id")
    if re.search(r"^\s*reviewed_commit:\s*\S+", text, re.MULTILINE) is None:
        p.append("missing upstream.reviewed_commit")
    if re.search(r"^\s*license:\s*\S+", text, re.MULTILINE) is None:
        p.append("missing upstream.license")
    if re.search(r"^integration:\s*\S+", text, re.MULTILINE) is None:
        p.append("missing integration")
    top_auth = re.search(r"^authority:\s*(\S+)", text, re.MULTILINE)
    if top_auth and top_auth.group(1).strip() in TF_FORBIDDEN_AUTHORITY:
        p.append(f"top-level authority claims forbidden role: {top_auth.group(1).strip()}")
    allowed = set(_cap_list(text, "allowed_actions"))
    if not allowed:
        p.append("missing allowed_actions")
    if allowed & DANGEROUS_ACTIONS:
        p.append(f"dangerous in allowed_actions: {sorted(allowed & DANGEROUS_ACTIONS)}")
    for cid, body in _capability_blocks(_yaml_section(text, "blocked_until")):
        for prob in tool_family_blocked_entry_problems(body):
            p.append(f"blocked_until/{cid}: {prob}")
    return p


# Families whose manifest follows THIS contract shape (flat allowed_actions[] + a blocked_until: section
# of `- id:` blocks). p4rs3lt0ngv3 adopts this shared contract (its converter/catalog outputs get
# additional schema validation in its own selftest.py).
#
# glossopetrae is intentionally EXCLUDED (documented temporary exclusion). It lives in the `-gloss`
# worktree on a different, more-evolved contract: a single `actions:` list (per-action class + status)
# with top-level evidence_role / forbidden_authority / output_schema, validated by its OWN checker
# variant that REQUIRES `authority: sensor_only` and additionally scans adapter-evidence JSON for verdict
# keys. The two manifest shapes are not interchangeable, so converging them is a deliberate design merge
# (pick ONE contract shape), NOT done in this reconciliation slice. When merged, the unified checker MUST
# preserve BOTH guards: this branch's full TF_FORBIDDEN_AUTHORITY top-level reject AND GLOSS's
# require-sensor_only + evidence_role + forbidden_authority + adapter-evidence-JSON scan.
TOOL_FAMILY_CONTRACT_OWNED = {"st3gg", "p4rs3lt0ngv3"}


def check_tool_family_manifests():
    """Family manifests: detection-first, machine-checkable, staged authority. Fail closed."""
    base = os.path.join(ROOT, "tool-families")
    if not os.path.isdir(base):
        return
    print("\n[tool-families] family manifests (manifest holds authority; advanced surfaces gated)")
    for fam in sorted(os.listdir(base)):
        if fam not in TOOL_FAMILY_CONTRACT_OWNED:
            continue
        mpath = os.path.join(base, fam, "manifest.yaml")
        if os.path.isfile(mpath):
            problems = tool_family_manifest_problems(open(mpath).read())
            record(not problems, f"tool-families/{fam}/manifest.yaml: detection-first + staged authority",
                   "; ".join(problems) if problems else "")
        apath = os.path.join(base, fam, "AGENT.md")
        if os.path.isfile(apath):
            atext = open(apath).read().lower()
            record("plane 1/2" in atext and "raw" in atext,
                   f"tool-families/{fam}/AGENT.md: states raw payloads not stored in Plane 1/2")


def check_tool_family_must_reject():
    """Permanent negatives: a malformed family manifest MUST be rejected by the same predicate."""
    base = os.path.join(ROOT, "fixtures", "tool-families", "_must_reject")
    if not os.path.isdir(base):
        return
    print("\n[tool-families] _must_reject corpus (the manifest must fail closed)")
    for fn in sorted(os.listdir(base)):
        fp = os.path.join(base, fn)
        if not os.path.isfile(fp):
            continue
        problems = tool_family_manifest_problems(open(fp).read())
        record(bool(problems), f"_must_reject/{fn}: rejected [{'; '.join(problems) or 'NONE'}]",
               "fixture should be rejected but passed all checks" if not problems else "")


PAYLOAD_PROPOSAL_REQUIRED = ["objective_id", "payload_class", "risk_tier", "approved_objective_ref",
                             "generator_capability_id", "artifact_metadata", "required_controls",
                             "containment_plan", "cleanup_plan", "non_authority_attestation"]
PAYLOAD_CLASSES = {"text_prompt", "encoded_prompt", "multimodal_artifact", "stego_carrier",
                   "exploit_poc", "chain_candidate"}
RISK_TIERS = {"benign_canary", "local_poc", "zone2_review_required"}
ZONE2_PAYLOAD_CLASSES = {"exploit_poc", "chain_candidate"}
FORBIDDEN_PROPOSAL_KEYS = ("verdict", "confirmed", "allow", "success")


def payload_proposal_problems(obj):
    """Pure predicate — reasons a payload proposal is malformed (an INERT proposal, never a verdict)."""
    if not isinstance(obj, dict):
        return ["not an object"]
    p = [f"missing {k}" for k in PAYLOAD_PROPOSAL_REQUIRED if k not in obj]
    p += [f"carries forbidden verdict key {k}" for k in FORBIDDEN_PROPOSAL_KEYS if k in obj]
    pc = obj.get("payload_class")
    if pc is not None and pc not in PAYLOAD_CLASSES:
        p.append(f"payload_class not in enum: {pc}")
    if "required_controls" in obj and not (isinstance(obj["required_controls"], list) and obj["required_controls"]):
        p.append("required_controls must be a non-empty list")
    if "non_authority_attestation" in obj:
        att = obj["non_authority_attestation"]
        if not isinstance(att, dict):
            p.append("non_authority_attestation must be an object")
        else:
            for k in ("proposal_only", "executes_nothing", "emits_no_verdict"):
                if att.get(k) is not True:
                    p.append(f"non_authority_attestation.{k} must be true")
    rt = obj.get("risk_tier")
    if rt is not None and rt not in RISK_TIERS:
        p.append(f"risk_tier not in enum: {rt}")
    # zone-2 tiers / exploit classes require operator confirmation + an impact-demo reference, never auto-run
    if pc in ZONE2_PAYLOAD_CLASSES or rt == "zone2_review_required":
        if obj.get("operator_confirmation_required") is not True:
            p.append("zone2 payload_class/risk_tier requires operator_confirmation_required: true")
        if not (isinstance(obj.get("impact_demo_ref"), str) and obj["impact_demo_ref"].strip()):
            p.append("zone2 payload_class/risk_tier requires an impact_demo_ref")
    return p


def check_payload_proposals():
    """PG-2: the inert payload-proposal schema gate. Valid example passes; malformed ones must reject."""
    base = os.path.join(ROOT, "fixtures", "payload-proposals")
    if not os.path.isdir(base):
        return
    print("\n[payload-proposals] inert proposal schema gate (PG-2)")
    for fn in sorted(os.listdir(base)):
        fp = os.path.join(base, fn)
        if not (fn.endswith(".json") and os.path.isfile(fp)):
            continue
        problems = payload_proposal_problems(load_json(fp))
        record(not problems, f"payload-proposals/{fn}: valid proposal",
               "; ".join(problems) if problems else "")
    mr = os.path.join(base, "_must_reject")
    if os.path.isdir(mr):
        for fn in sorted(os.listdir(mr)):
            if not fn.endswith(".json"):
                continue
            problems = payload_proposal_problems(load_json(os.path.join(mr, fn)))
            record(bool(problems), f"payload-proposals/_must_reject/{fn}: rejected [{'; '.join(problems) or 'NONE'}]",
                   "malformed proposal should be rejected but passed" if not problems else "")


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
    print("\n[secrets] casebook + fixture + eval scan")
    hits = []
    for sub in ("casebooks", "fixtures", "evals"):
        base = os.path.join(ROOT, sub)
        if not os.path.isdir(base):
            continue
        for dirpath, _, files in os.walk(base):
            for fn in files:
                fp = os.path.join(dirpath, fn)
                text = open(fp, errors="ignore").read()
                for pat, desc in SECRET_PATTERNS:
                    for m in re.finditer(pat, text):
                        hits.append(f"{os.path.relpath(fp, ROOT)}: {desc} :: {m.group(0)[:24]}")
    record(not hits, "casebooks/fixtures/evals contain no live-secret shapes",
           "; ".join(hits) if hits else "")


# ---- Phase 2.5A: evidence-contract gate + evaluator corpora ----

POLICY_CUTOFF = "2026-06-25"
FINDING_BASE_REQUIRED = [
    "id", "engagement", "owasp", "surface", "objective", "scope_class", "severity",
    "confidence", "attempt_id", "control_attempt_id", "oracle_verdict", "dedup_key", "status",
]
CONTRACT_REQUIRED = ["negative_control", "replay", "contamination", "justification", "run_cost"]


def load_json(path):
    with open(path) as fh:
        return json.load(fh)


def finding_is_new(f):
    d = f.get("recorded_date")
    return bool(d) and d >= POLICY_CUTOFF


def _int_ge(v, lo):
    return isinstance(v, int) and not isinstance(v, bool) and v >= lo


def contract_problems(f):
    """Deep validation of evidence_contract: nested required fields + types, not just top-level keys."""
    ec = f.get("evidence_contract")
    if not isinstance(ec, dict):
        return ["evidence_contract missing or not an object"]
    p = []

    nc = ec.get("negative_control")
    if not isinstance(nc, dict):
        p.append("negative_control missing/not-object")
    else:
        if not isinstance(nc.get("ran"), bool):
            p.append("negative_control.ran must be bool")
        if nc.get("result") not in ("refused", "no_signal", "different_outcome", "n/a"):
            p.append("negative_control.result invalid")

    rp = ec.get("replay")
    if not isinstance(rp, dict):
        p.append("replay missing/not-object")
    else:
        if not _int_ge(rp.get("sessions"), 1):
            p.append("replay.sessions must be int >= 1")
        if not isinstance(rp.get("fresh_session"), bool):
            p.append("replay.fresh_session must be bool")
        if not isinstance(rp.get("deterministic"), bool):
            p.append("replay.deterministic must be bool")

    ct = ec.get("contamination")
    if not isinstance(ct, dict):
        p.append("contamination missing/not-object")
    elif not isinstance(ct.get("ruled_out"), bool):
        p.append("contamination.ruled_out must be bool")

    j = ec.get("justification")
    if not (isinstance(j, str) and j.strip()):
        p.append("justification must be a non-empty string")

    rc = ec.get("run_cost")
    if not isinstance(rc, dict):
        p.append("run_cost missing/not-object")
    else:
        for k in ("model_calls", "target_calls"):
            if not _int_ge(rc.get(k), 0):
                p.append(f"run_cost.{k} must be int >= 0")

    pc = ec.get("positive_control")
    if pc is not None and not isinstance(pc, dict):
        p.append("positive_control must be an object when present")
    return p


def contract_complete(f):
    return not contract_problems(f)


def check_finding_fixtures():
    print("\n[findings] evidence-contract gate (necessary, not sufficient)")
    base = os.path.join(ROOT, "fixtures", "findings")
    if not os.path.isdir(base):
        return
    for fn in sorted(os.listdir(base)):
        fp = os.path.join(base, fn)
        if not fn.endswith(".json") or not os.path.isfile(fp):
            continue
        f = load_json(fp)
        missing = [k for k in FINDING_BASE_REQUIRED if k not in f]
        record(not missing, f"findings/{fn}: base required fields", f"missing {missing}" if missing else "")
        record("recorded_date" in f, f"findings/{fn}: recorded_date present (drives the migration gate)",
               "every finding must carry recorded_date so the cutoff is explicit, never defaulted" if "recorded_date" not in f else "")
        problems = contract_problems(f)
        if finding_is_new(f):
            record(not problems, f"findings/{fn}: new finding carries complete, well-formed evidence contract",
                   f"recorded >= {POLICY_CUTOFF} but: {problems}" if problems else "")
        else:
            if problems:
                print(f"  warn findings/{fn}: legacy finding (pre-{POLICY_CUTOFF}) contract gaps {problems} — advisory, not gated")
            record(True, f"findings/{fn}: legacy finding advisory-only")

    mr = os.path.join(base, "_must_reject")
    if os.path.isdir(mr):
        for fn in sorted(os.listdir(mr)):
            fp = os.path.join(mr, fn)
            if not fn.endswith(".json"):
                continue
            f = load_json(fp)
            caught = finding_is_new(f) and bool(contract_problems(f))
            record(caught, f"findings/_must_reject/{fn}: caught by the contract gate (invalid-accept guard)",
                   "a new finding without a complete, well-formed contract slipped through" if not caught else "")


def check_false_discovery_corpus():
    print("\n[false-discovery] invalid-accept guard")
    fp = os.path.join(ROOT, "fixtures", "false-discovery", "corpus.json")
    if not os.path.isfile(fp):
        return
    entries = load_json(fp).get("entries", [])
    record(len(entries) > 0, "false-discovery: corpus non-empty")
    confirmable = [e.get("id", "?") for e in entries if e.get("correct_verdict") == "confirmed"]
    record(not confirmable, "false-discovery: invalid_accept_rate == 0 (no trap's correct verdict is 'confirmed')",
           f"wrongly confirmable: {confirmable}" if confirmable else "")
    req = ["id", "trap_class", "observation", "correct_verdict", "missing_control", "why"]
    for e in entries:
        miss = [k for k in req if k not in e]
        record(not miss, f"false-discovery/{e.get('id', '?')}: well-formed", f"missing {miss}" if miss else "")


def check_adversarial_candidates():
    print("\n[adversarial-candidates] Phase-3 gate fixture (staged, not launched)")
    fp = os.path.join(ROOT, "fixtures", "adversarial-candidates", "corpus.json")
    if not os.path.isfile(fp):
        return
    entries = load_json(fp).get("entries", [])
    retain = [e.get("id", "?") for e in entries if e.get("expected_disposition") == "retain"]
    block = [e.get("id", "?") for e in entries if e.get("expected_disposition") == "block"]
    record(len(retain) >= 1, "adversarial: at least one valid additive candidate to retain",
           "no retain candidate" if not retain else "")
    record(len(block) >= 1, "adversarial: at least one gaming candidate to block",
           "no block candidate" if not block else "")
    for e in entries:
        d = e.get("expected_disposition")
        record(d in ("retain", "block"), f"adversarial/{e.get('id', '?')}: disposition in vocab", f"got {d}")
    leaks = [e.get("id", "?") for e in entries if e.get("touches_immutable") and e.get("expected_disposition") != "block"]
    record(not leaks, "adversarial: every immutable-touching candidate is blocked", f"leaky: {leaks}" if leaks else "")


def main():
    pattern_ids = collect_pattern_ids()
    cap_ids = collect_capability_ids()
    print(f"known pattern ids: {sorted(pattern_ids)}")
    print(f"known capability ids: {sorted(cap_ids)}")
    for subdir in ("patterns", "vulns", "techniques"):
        check_cards(subdir, pattern_ids, cap_ids)
    check_capabilities()
    check_capability_classes()
    check_capability_scope_flags()
    check_capability_must_reject()
    check_tool_family_manifests()
    check_tool_family_must_reject()
    check_payload_proposals()
    check_oracles()
    check_casebooks(pattern_ids)
    check_secrets()
    check_finding_fixtures()
    check_false_discovery_corpus()
    check_adversarial_candidates()

    print(f"\n{CHECKS} checks, {len(FAILS)} failing")
    if FAILS:
        print("CONFORMANCE: FAIL")
        return 1
    print("CONFORMANCE: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
