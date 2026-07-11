#!/usr/bin/env python3
"""Deterministic claim/proof helpers for Decision-0005 review and reports."""
from __future__ import annotations

from typing import Any

from engagement_records import canonical_json_bytes, sha256_bytes

RENDERER_VERSION = "decision-0005-proof-v1"


def claim_tuple_hash(finding: dict[str, Any]) -> str:
    """Hash only the revision's structured claim tuple, never narrative report text."""
    value = {
        "finding_id": finding["finding_id"],
        "revision": finding["revision"],
        "claim_state": finding["claim_state"],
        "classification": finding["classification"],
        "claims": finding["claims"],
        "scope_provenance": {
            "scope_hash": finding["scope_provenance"]["scope_hash"],
            "environment_ref": finding["scope_provenance"]["environment_ref"],
            "target_refs": finding["scope_provenance"]["target_refs"],
        },
    }
    return sha256_bytes(canonical_json_bytes(value))


def claim_rows(finding: dict[str, Any]) -> list[dict[str, Any]]:
    claims = finding["claims"]
    ordered = [claims["mechanism"], claims["reachability"], *claims["impact_claims"]]
    proof_by_claim = {item["claim_id"]: item for item in finding["proof"]["claim_proofs"]}
    rows: list[dict[str, Any]] = []
    for claim in ordered:
        proof = proof_by_claim[claim["claim_id"]]
        rows.append({
            "claim_id": claim["claim_id"],
            "statement": claim["statement"],
            "claim_status": claim.get("status", "mechanism_or_reachability"),
            "attempt_refs": proof["attempt_refs"],
            "artifact_refs": proof["artifact_refs"],
            "control_refs": proof["control_refs"],
            "replay_refs": proof["replay_refs"],
            "applicability_rationale": proof["applicability_rationale"],
        })
    return rows


def _cell(value: Any) -> str:
    if isinstance(value, list):
        value = ", ".join(value) if value else "—"
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_claim_proof(finding: dict[str, Any]) -> str:
    lines = [
        f"# Claim-to-proof matrix — {finding['finding_id']} revision {finding['revision']}",
        "",
        f"- Claim state: `{finding['claim_state']}`",
        f"- Claim tuple: `{claim_tuple_hash(finding)}`",
        f"- Renderer: `{RENDERER_VERSION}`",
        "",
        "| Claim | Status | Statement | Primary attempts | Artifacts | Controls | Replays |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in claim_rows(finding):
        lines.append("| " + " | ".join(_cell(row[key]) for key in ("claim_id", "claim_status", "statement", "attempt_refs", "artifact_refs", "control_refs", "replay_refs")) + " |")
    uncertainty = [f"- {item}" for item in finding["claims"]["uncertainty"]] or ["- None recorded."]
    lines.extend(["", "## Uncertainty", "", *uncertainty, ""])
    return "\n".join(lines)
