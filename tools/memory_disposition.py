#!/usr/bin/env python3
"""Operator-owned terminal memory disposition and engagement closure gates."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
from typing import Any

from engagement_records import (
    RecordError, build_reference_index, canonical_json_bytes, detect_secret_classes,
    load_json, sha256_file, validate_record, validate_record_references,
)
from engagement_state import (
    _scope_metadata, _append_kernel_event as append_event, atomic_write, base_event, engagement_lock,
    read_ledger, reduce_engagement,
)


def _operator(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._:-]+", "-", value).strip("-") or "operator"


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _validate_promotable_abstraction(proposal: dict[str, Any], discovered_terms: set[str] | None = None) -> None:
    if proposal["disposition"] != "promote": return
    retained_text = [proposal["lesson_summary"], proposal["rationale"], proposal["sanitization"]["notes"], proposal["human_review"]["rationale"], proposal.get("reopening_condition") or ""]
    source_ids = set(proposal["candidate_refs"])
    for values in proposal["source_refs"].values(): source_ids.update(values)
    forbidden_recipe = re.compile(r"(?i)(https?://|```|\bcurl\b|\bwget\b|authorization\s*:|bearer\s+|\bpython\s+-c\b|\b(?:select|insert|update|delete)\s+.+\bfrom\b|(?:^|\s)/(?:api|admin|etc)/|(?:^|\s)--[a-z]|\n)")
    target_terms = {proposal["engagement_id"], *proposal["sanitization"]["target_terms_checked"], *(discovered_terms or set())}
    unsafe = any(forbidden_recipe.search(text) for text in retained_text) or any(reference.lower() in text.lower() for reference in source_ids for text in retained_text) or any(term.lower() in text.lower() for term in target_terms if len(term) >= 2 for text in retained_text)
    if len(proposal["lesson_summary"]) > 500 or unsafe:
        raise RecordError("memory_abstraction_not_sanitized", "all retained promotable text must be target-neutral prose without commands, endpoints, source IDs, target terms, or recipes")


def record_memory_disposition(engagement: Path, proposal_path: Path, operator_id: str, authority_request_ref: str | None = None, executor_id: str | None = None, session_id: str | None = None) -> dict[str, Any]:
    engagement = engagement.absolute(); proposal = load_json(proposal_path); operator_id = _operator(operator_id)
    errors = validate_record(proposal, "memory-disposition")
    if errors: raise RecordError("memory_disposition_invalid", "memory disposition failed schema validation", errors)
    _validate_promotable_abstraction(proposal)
    secret_classes = detect_secret_classes(canonical_json_bytes(proposal))
    if secret_classes: raise RecordError("secret_shaped_memory_content", "memory disposition contains forbidden secret-shaped content", [{"class": item} for item in secret_classes])
    relative = f"memory/disposition-{proposal['disposition_id']}.json"
    with engagement_lock(engagement):
        state = reduce_engagement(engagement, allowed_record_orphans={relative})
        scope = _scope_metadata(engagement / "scope.md")
        if state["memory_disposition"] is not None:
            existing_path = engagement / relative
            if state["memory_disposition"]["disposition_ref"] == proposal["disposition_id"] and existing_path.is_file() and existing_path.read_bytes() == canonical_json_bytes(proposal): return proposal
            raise RecordError("memory_disposition_already_terminal", state["memory_disposition"]["disposition_ref"])
        if proposal["engagement_id"] != state["engagement_id"] or proposal["scope_hash"] != state["scope_hash"]:
            raise RecordError("memory_disposition_scope_mismatch", proposal["disposition_id"])
        if proposal["human_review"]["reviewer"] != {"role": "operator", "id": operator_id} or _operator(scope["operator"]) != operator_id:
            raise RecordError("memory_disposition_authority_invalid", operator_id)
        if proposal["human_review"]["decision"] != proposal["disposition"] or _time(proposal["human_review"]["reviewed_at"]) > _time(proposal["recorded_at"]):
            raise RecordError("memory_disposition_review_invalid", proposal["disposition_id"])
        index = build_reference_index(engagement)
        reference_errors = validate_record_references(proposal, "memory-disposition", index)
        if reference_errors: raise RecordError("memory_disposition_reference_invalid", proposal["disposition_id"], reference_errors)
        discovered_terms: set[str] = set()
        for reference in proposal["source_refs"]["environment_refs"]:
            for entry in index.get(reference, []):
                if entry.get("type") == "environment" and entry.get("engagement_id") == proposal["engagement_id"]:
                    environment = load_json(engagement / entry["path"]); identity = environment.get("identity", {})
                    discovered_terms.update(str(value) for value in (identity.get("endpoint_identity"), identity.get("account_role")) if value and value != "local")
                    discovered_terms.update(str(value) for value in identity.get("feature_flags", []))
        _validate_promotable_abstraction(proposal, discovered_terms)
        proposal_time = _time(proposal["recorded_at"])
        source_ids = set(proposal["candidate_refs"])
        for values in proposal["source_refs"].values(): source_ids.update(values)
        for reference in source_ids:
            entries = [entry for entry in index.get(reference, []) if entry.get("engagement_id") == proposal["engagement_id"] and entry.get("recorded_at")]
            if entries and all(_time(entry["recorded_at"]) > proposal_time for entry in entries):
                raise RecordError("memory_disposition_source_from_future", reference)
        path = engagement / relative; record_bytes = canonical_json_bytes(proposal)
        if path.exists() and path.read_bytes() != record_bytes: raise RecordError("memory_disposition_id_collision", proposal["disposition_id"])
        if not path.exists(): atomic_write(path, record_bytes)
        digest = sha256_file(path); event_ids = {event["event_id"] for event in read_ledger(engagement, "event")}; actor_role = "broker" if authority_request_ref else "operator"; actor_id = executor_id if authority_request_ref else operator_id
        commit_id = f"event-{proposal['disposition_id']}-commit"; disposition_event_id = f"event-{proposal['disposition_id']}-recorded"
        if commit_id not in event_ids:
            append_event(engagement, base_event(event_id=commit_id, engagement_id=state["engagement_id"], recorded_at=proposal["recorded_at"], actor_role=actor_role, actor_id=actor_id, event_type="record.committed", rationale="Commit the immutable operator-reviewed memory disposition.", payload={"record_path": relative, "record_digest": digest, "record_type": "memory-disposition", "record_id": proposal["disposition_id"], "record_revision": None, **({"authority_request_ref": authority_request_ref} if authority_request_ref else {})}, session_id=session_id, operation_class="authority" if authority_request_ref else None), lock_held=True)
        if disposition_event_id not in event_ids:
            memory_prior = "pending"
            for prior_event in read_ledger(engagement, "event"):
                for change in prior_event["state_changes"]:
                    if change["dimension"] == "memory" and change["entity_id"] == state["engagement_id"]: memory_prior = change["current"]
            append_event(engagement, base_event(event_id=disposition_event_id, engagement_id=state["engagement_id"], recorded_at=proposal["recorded_at"], actor_role=actor_role, actor_id=actor_id, event_type="memory.disposition_recorded", rationale=proposal["rationale"], payload={"entity_id": state["engagement_id"], "memory_disposition": proposal["disposition"], "disposition_ref": proposal["disposition_id"], "disposition_digest": digest, "operator_id": operator_id, **({"authority_request_ref": authority_request_ref} if authority_request_ref else {})}, entity_refs=[proposal["disposition_id"]], state_changes=[{"dimension": "memory", "entity_id": state["engagement_id"], "previous": memory_prior, "current": proposal["disposition"]}], session_id=session_id, operation_class="authority" if authority_request_ref else None), lock_held=True)
        return proposal


def close_engagement(engagement: Path, operator_id: str, reason: str, recorded_at: str, authority_request_ref: str | None = None, executor_id: str | None = None, session_id: str | None = None) -> dict[str, Any]:
    engagement = engagement.absolute(); operator_id = _operator(operator_id)
    with engagement_lock(engagement):
        state = reduce_engagement(engagement); scope = _scope_metadata(engagement / "scope.md")
        if _operator(scope["operator"]) != operator_id: raise RecordError("engagement_closure_authority_invalid", operator_id)
        memory = state["memory_disposition"]
        if memory is None: raise RecordError("engagement_closure_memory_missing", state["engagement_id"])
        prior = "active"
        for event in read_ledger(engagement, "event"):
            for change in event["state_changes"]:
                if change["dimension"] == "engagement" and change["entity_id"] == state["engagement_id"]: prior = change["current"]
        if prior == "closed": raise RecordError("engagement_already_closed", state["engagement_id"])
        event = base_event(event_id=f"event-{state['engagement_id']}-closed", engagement_id=state["engagement_id"], recorded_at=recorded_at, actor_role="broker" if authority_request_ref else "operator", actor_id=executor_id if authority_request_ref else operator_id, event_type="engagement.closed", rationale=reason, payload={"entity_id": state["engagement_id"], "status": "closed", "scope_hash": state["scope_hash"], "operator_id": operator_id, "disposition_ref": memory["disposition_ref"], "disposition_digest": memory["disposition_digest"], **({"authority_request_ref": authority_request_ref} if authority_request_ref else {})}, entity_refs=[memory["disposition_ref"]], state_changes=[{"dimension": "engagement", "entity_id": state["engagement_id"], "previous": prior, "current": "closed"}], session_id=session_id, operation_class="authority" if authority_request_ref else None)
        append_event(engagement, event, lock_held=True)
        return reduce_engagement(engagement)
