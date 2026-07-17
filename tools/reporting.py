#!/usr/bin/env python3
"""Revision-bound deterministic internal report generation."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from engagement_records import canonical_json_bytes, load_json, sha256_bytes, sha256_file
from engagement_state import atomic_write, base_event, _append_kernel_event_idempotent as append_event, compute_review_input_hash, engagement_lock, read_governed_file, reduce_engagement
from finding_review import RENDERER_VERSION, claim_rows, render_claim_proof, render_internal_report

TEMPLATE_VERSION = "decision-0005-report-v1"


def _generate_report_locked(engagement: Path, finding_id: str, revision: int, included_claim_ids: list[str], omitted_claims: list[dict[str, str]], operator_id: str, recorded_at: str, authority_request_ref: str | None = None, executor_id: str | None = None, session_id: str | None = None) -> dict[str, Any]:
    engagement = engagement.absolute(); report_id = f"report-{finding_id}-r{revision}"; report_rel = f"reports/{finding_id}-r{revision}.md"; manifest_rel = f"reports/{finding_id}-r{revision}.manifest.json"; report_path = engagement / report_rel; manifest_path = engagement / manifest_rel
    state = reduce_engagement(engagement, allowed_record_orphans={report_rel, manifest_rel})
    from engagement_records import build_reference_index
    entry = next((item for item in build_reference_index(engagement).get(finding_id, []) if item["type"] == "finding" and item.get("revision") == revision), None)
    if entry is None:
        raise ValueError(f"missing finding revision {finding_id}:{revision}")
    finding_path = engagement / entry["path"]; finding = load_json(finding_path)
    claim_ids = {row["claim_id"] for row in claim_rows(finding)}
    included = set(included_claim_ids); omitted = {item["claim_id"] for item in omitted_claims}
    if not included or included & omitted or included | omitted != claim_ids:
        raise ValueError("included and omitted claims must partition the exact finding claim IDs")
    report_bytes = render_internal_report(finding, included_claim_ids, omitted_claims).encode("utf-8")
    try: prior_report=read_governed_file(report_path)
    except FileNotFoundError: prior_report=None
    if prior_report is not None and prior_report!=report_bytes: raise ValueError("report byte collision during resume")
    if prior_report is None: atomic_write(report_path, report_bytes)
    proof_bytes = render_claim_proof(finding).encode("utf-8")
    review_ref = finding["adjudication"]["review_ref"]
    review_entry = next(item for item in build_reference_index(engagement)[review_ref] if item["type"] == "review")
    manifest = {
        "schema_version": 1, "report_id": report_id, "engagement_id": finding["engagement_id"], "generated_at": recorded_at,
        "finding_id": finding_id, "finding_revision": revision, "finding_digest": sha256_file(finding_path),
        "adjudication_review_ref": review_ref, "adjudication_review_digest": sha256_file(engagement / review_entry["path"]),
        "template_version": TEMPLATE_VERSION, "renderer_version": RENDERER_VERSION, "report_path": report_rel,
        "report_digest": sha256_bytes(report_bytes), "operator_status": "draft", "included_claim_ids": included_claim_ids,
        "omitted_claims": omitted_claims, "claim_proof_matrix_hash": sha256_bytes(proof_bytes),
        "generator_provenance": {"actor": {"role": "broker" if authority_request_ref else "operator", "id": executor_id if authority_request_ref else operator_id}, "session_id": session_id, "provider": None, "model": None, "prompt_version": TEMPLATE_VERSION, "tool_versions": [RENDERER_VERSION], "card_versions": []},
        "historical_reason": None,
    }
    manifest_bytes=canonical_json_bytes(manifest)
    try: prior_manifest=read_governed_file(manifest_path)
    except FileNotFoundError: prior_manifest=None
    if prior_manifest is not None and prior_manifest!=manifest_bytes: raise ValueError("report manifest collision during resume")
    if prior_manifest is None: atomic_write(manifest_path, manifest_bytes)
    commit = base_event(event_id=f"event-{report_id}-commit", engagement_id=finding["engagement_id"], recorded_at=recorded_at, actor_role="broker" if authority_request_ref else "operator", actor_id=executor_id if authority_request_ref else operator_id, event_type="record.committed", rationale="Commit revision-bound report manifest.", payload={"record_path": manifest_rel, "record_digest": sha256_file(manifest_path), "record_type": "report-manifest", "record_id": report_id, "record_revision": None, **({"authority_request_ref": authority_request_ref} if authority_request_ref else {})}, session_id=session_id, operation_class="authority" if authority_request_ref else None)
    append_event(engagement, commit, lock_held=True)
    generated = base_event(event_id=f"event-{report_id}-generated", engagement_id=finding["engagement_id"], recorded_at=recorded_at, actor_role="broker" if authority_request_ref else "operator", actor_id=executor_id if authority_request_ref else operator_id, event_type="report.generated", rationale="Generate internal report from exact structured claims and proof.", payload={"report_ref": report_id, "finding_id": finding_id, "finding_revision": revision, "report_manifest_digest": sha256_file(manifest_path), "operator_id": operator_id, **({"authority_request_ref": authority_request_ref} if authority_request_ref else {})}, entity_refs=[report_id, finding_id], finding_refs=[finding_id], state_changes=[{"dimension": "report", "entity_id": report_id, "previous": None, "current": "draft"}], session_id=session_id, operation_class="authority" if authority_request_ref else None)
    append_event(engagement, generated, lock_held=True)
    return manifest


def generate_report(engagement: Path, finding_id: str, revision: int, included_claim_ids: list[str], omitted_claims: list[dict[str, str]], operator_id: str, recorded_at: str, authority_request_ref: str | None = None, executor_id: str | None = None, session_id: str | None = None) -> dict[str, Any]:
    engagement = engagement.absolute()
    with engagement_lock(engagement):
        return _generate_report_locked(engagement, finding_id, revision, included_claim_ids, omitted_claims, operator_id, recorded_at, authority_request_ref, executor_id, session_id)


def accept_report(engagement: Path, report_id: str, operator_id: str, reason: str, recorded_at: str, authority_request_ref: str | None = None, executor_id: str | None = None, session_id: str | None = None) -> dict[str, Any]:
    engagement = engagement.absolute(); review_id = f"review-{report_id}-operator"; path_rel = f"reviews/{review_id}.json"; path = engagement / path_rel; state = reduce_engagement(engagement, allowed_record_orphans={path_rel})
    if state["reports"].get(report_id, {}).get("status") != "draft":
        raise ValueError("report must be a current draft")
    from engagement_records import build_reference_index
    review = {"schema_version": 1, "review_id": review_id, "engagement_id": state["engagement_id"], "review_type": "operator", "proposed_finding_id": None, "recorded_at": recorded_at, "entity_ref": report_id, "finding_revision": state["reports"][report_id]["finding_revision"], "input_refs": [report_id], "input_hash": "sha256:" + "0" * 64, "evidence_refs": [], "rationale": reason, "conflicting_evidence": [], "verdict": "accepted", "corrections": [], "required_next_actions": [], "independence": {"reviewer_id": operator_id, "reviewer_run_id": f"run-{review_id}", "reviewer_model": None, "fresh_context": True, "prior_verdict_visible": False, "disconfirming_objective": "Reject unsupported or stale report language.", "originating_run_id": f"event-{report_id}-generated"}}
    review["input_hash"] = compute_review_input_hash(engagement, review, build_reference_index(engagement)); review_bytes=canonical_json_bytes(review)
    try: prior_review=read_governed_file(path)
    except FileNotFoundError: prior_review=None
    if prior_review is not None and prior_review!=review_bytes: raise ValueError("operator report review ID collision")
    if prior_review is None: atomic_write(path,review_bytes)
    actor_role = "broker" if authority_request_ref else "operator"; actor_id = executor_id if authority_request_ref else operator_id
    commit = base_event(event_id=f"event-{review_id}-commit", engagement_id=state["engagement_id"], recorded_at=recorded_at, actor_role=actor_role, actor_id=actor_id, event_type="record.committed", rationale="Commit operator report review.", payload={"record_path": path_rel, "record_digest": sha256_bytes(review_bytes), "record_type": "review", "record_id": review_id, "record_revision": None, **({"authority_request_ref": authority_request_ref} if authority_request_ref else {})}, session_id=session_id, operation_class="authority" if authority_request_ref else None); append_event(engagement, commit)
    accepted = base_event(event_id=f"event-{report_id}-accepted", engagement_id=state["engagement_id"], recorded_at=recorded_at, actor_role=actor_role, actor_id=actor_id, event_type="operator.review_recorded", rationale=reason, payload={"report_ref": report_id, "review_ref": review_id, "status": "accepted", "reason": reason, "operator_id": operator_id, **({"authority_request_ref": authority_request_ref} if authority_request_ref else {})}, entity_refs=[report_id], review_refs=[review_id], state_changes=[{"dimension": "report", "entity_id": report_id, "previous": "draft", "current": "accepted"}], session_id=session_id, operation_class="authority" if authority_request_ref else None); append_event(engagement, accepted)
    return review


def record_submission(engagement: Path, report_id: str, submission_file: Path, program: str, operator_id: str, recorded_at: str, authority_request_ref: str | None = None, executor_id: str | None = None, session_id: str | None = None) -> str:
    engagement = engagement.absolute(); state = reduce_engagement(engagement); file_path = submission_file.absolute()
    try: relative_path = file_path.relative_to(engagement); file_bytes = read_governed_file(file_path)
    except (ValueError, OSError): raise ValueError("submission must be a regular file under submissions/ for an accepted report")
    if state["reports"].get(report_id, {}).get("status") != "accepted" or not relative_path.parts or relative_path.parts[0] != "submissions": raise ValueError("submission must be a regular file under submissions/ for an accepted report")
    submission_id = f"submission-{report_id}"; rel = relative_path.as_posix()
    event = base_event(event_id=f"event-{submission_id}", engagement_id=state["engagement_id"], recorded_at=recorded_at, actor_role="broker" if authority_request_ref else "operator", actor_id=executor_id if authority_request_ref else operator_id, event_type="submission.recorded", rationale="Record operator-authored external submission separately from internal report.", payload={"submission_ref": submission_id, "report_ref": report_id, "submission_path": rel, "submission_digest": sha256_bytes(file_bytes), "program": program, "operator_id": operator_id, "authorship_note": f"Authored and approved by operator {operator_id}; recorded by {executor_id or operator_id}.", **({"authority_request_ref": authority_request_ref} if authority_request_ref else {})}, entity_refs=[submission_id, report_id], state_changes=[{"dimension": "report", "entity_id": report_id, "previous": "accepted", "current": "submitted"}], session_id=session_id, operation_class="authority" if authority_request_ref else None); append_event(engagement, event)
    return submission_id
