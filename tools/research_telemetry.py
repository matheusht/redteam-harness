#!/usr/bin/env python3
"""Deterministic complete-funnel telemetry export and conservative offline scoring."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from engagement_records import RecordError, build_reference_index, canonical_json_bytes, load_json, validate_record
from engagement_state import atomic_write, read_ledger, reduce_engagement

COST_FIELDS = ("wall_seconds", "model_seconds", "tool_seconds", "target_calls", "model_calls", "input_tokens", "output_tokens", "cost_usd", "human_review_seconds")
ZERO_COST = {field: None for field in COST_FIELDS}
FUNNEL_ORDER = ("eligible", "selected", "skipped", "overridden", "held", "deferred", "contaminated", "reopened", "refuted", "confirmed")


def _history(state: str, recorded_at: str, source_ref: str, rationale: str, source_kind: str, source_sequence: int, source_revision: int | None = None) -> dict[str, Any]:
    return {"state": state, "recorded_at": recorded_at, "source_ref": source_ref, "rationale": rationale, "source_kind": source_kind, "source_sequence": source_sequence, "source_revision": source_revision}


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _sum_cost(records: list[dict[str, Any]]) -> dict[str, Any]:
    result = dict(ZERO_COST)
    for field in COST_FIELDS:
        values = [record.get("cost", {}).get(field) for record in records]
        result[field] = sum(values) if values and all(value is not None for value in values) else None
    return result


def _records_of_type(engagement: Path, kind: str) -> list[dict[str, Any]]:
    index = build_reference_index(engagement); records: list[dict[str, Any]] = []
    for entries in index.values():
        for entry in entries:
            if entry["type"] == kind and entry.get("engagement_id") == engagement.name:
                records.append(load_json(engagement / entry["path"]))
    identities = {"review": "review_id", "finding": "finding_id"}
    key = identities.get(kind)
    return sorted(records, key=lambda item: (item.get(key, ""), item.get("revision", 0)))


def export_telemetry(engagement: Path, output: Path | None = None) -> dict[str, Any]:
    engagement = engagement.resolve(); state = reduce_engagement(engagement); events = read_ledger(engagement, "event"); attempts = read_ledger(engagement, "attempt")
    proposals = [event for event in events if event["event_type"] == "candidate.proposed"]
    candidate_events: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        candidate_id = event.get("payload", {}).get("candidate_id")
        if candidate_id: candidate_events.setdefault(candidate_id, []).append(event)
    hypothesis_to_candidate: dict[str, str] = {}; hypothesis_events: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        payload = event.get("payload", {})
        if event["event_type"] == "hypothesis.created" and payload.get("origin_type") == "candidate": hypothesis_to_candidate[payload["hypothesis_id"]] = payload["origin_ref"]
        hypothesis_id = payload.get("hypothesis_id")
        if hypothesis_id: hypothesis_events.setdefault(hypothesis_id, []).append(event)
    reviews = _records_of_type(engagement, "review"); findings = _records_of_type(engagement, "finding")
    current_findings = {finding_id: finding for finding_id, current in state["findings"].items() for finding in findings if finding["finding_id"] == finding_id and finding["revision"] == current["revision"]}
    rows: list[dict[str, Any]] = []
    for proposal in proposals:
        candidate_id = proposal["payload"]["candidate_id"]; linked_hypotheses = sorted(key for key, value in hypothesis_to_candidate.items() if value == candidate_id)
        linked_attempts = sorted((attempt for attempt in attempts if attempt.get("hypothesis_ref") in linked_hypotheses), key=lambda item: item["attempt_id"])
        linked_finding_history = sorted((finding for finding in findings if candidate_id in finding.get("search_linkage", {}).get("candidate_refs", [])), key=lambda item: (item["finding_id"], item["revision"]))
        linked_findings = sorted((finding for finding in current_findings.values() if candidate_id in finding.get("search_linkage", {}).get("candidate_refs", [])), key=lambda item: item["finding_id"])
        linked_outcomes = [review for review in reviews if review.get("review_type") == "candidate_outcome" and review.get("entity_ref") == candidate_id]
        history = [_history("eligible", proposal["recorded_at"], proposal["event_id"], proposal["rationale"], "event", proposal["sequence"])]
        for event in candidate_events.get(candidate_id, []):
            state_name = {"candidate.selected": "selected", "candidate.skipped": "skipped", "candidate.deferred": "deferred"}.get(event["event_type"])
            if state_name: history.append(_history(state_name, event["recorded_at"], event["event_id"], event["rationale"], "event", event["sequence"]))
            if event.get("payload", {}).get("operator_override") is True: history.append(_history("overridden", event["recorded_at"], event["event_id"], event["payload"]["override_reason"], "event", event["sequence"]))
        for hypothesis_id in linked_hypotheses:
            for event in hypothesis_events.get(hypothesis_id, []):
                status = event["payload"].get("status")
                if status in {"held", "deferred"}: history.append(_history(status, event["recorded_at"], event["event_id"], event["rationale"], "event", event["sequence"]))
                if status == "queued" and any(change.get("previous") in {"held", "exhausted", "deferred", "blocked", "closed"} for change in event["state_changes"]): history.append(_history("reopened", event["recorded_at"], event["event_id"], event["rationale"], "event", event["sequence"]))
            for event in events:
                if event["event_type"] == "operator_prior.recorded" and event["payload"].get("reopen_hypothesis_id") == hypothesis_id: history.append(_history("reopened", event["recorded_at"], event["event_id"], event["rationale"], "event", event["sequence"]))
        for attempt in linked_attempts:
            if attempt["assessment"] == "held": history.append(_history("held", attempt["recorded_at"], attempt["attempt_id"], attempt["action_summary"], "attempt", attempt["sequence"]))
            if attempt["contamination"]["status"] == "confirmed": history.append(_history("contaminated", attempt["recorded_at"], attempt["attempt_id"], attempt["contamination"]["note"], "attempt", attempt["sequence"]))
        for finding in linked_finding_history:
            if finding["claim_state"] in {"contaminated", "refuted", "confirmed"}: history.append(_history(finding["claim_state"], finding["recorded_at"], finding["finding_id"], finding["change_reason"], "finding", finding["revision"], finding["revision"]))
        independent = len(linked_outcomes) == 1 and linked_outcomes[0]["independence"]["fresh_context"] is True and linked_outcomes[0]["independence"]["prior_verdict_visible"] is False and linked_outcomes[0]["independence"]["reviewer_run_id"] != linked_outcomes[0]["independence"].get("originating_run_id")
        outcome_review = linked_outcomes[0] if len(linked_outcomes) == 1 else None; outcome_label = outcome_review["verdict"] if outcome_review else "unresolved"; outcome_time = outcome_review["recorded_at"] if outcome_review else None
        if independent and outcome_label in {"positive", "negative"}: history.append(_history("confirmed" if outcome_label == "positive" else "refuted", outcome_review["recorded_at"], outcome_review["review_id"], outcome_review["rationale"], "review", 0))
        kind_order = {"event": 0, "attempt": 1, "finding": 2, "review": 3}
        history.sort(key=lambda item: (_time(item["recorded_at"]), kind_order[item["source_kind"]], item["source_sequence"], item["source_ref"], FUNNEL_ORDER.index(item["state"])))
        states = {item["state"] for item in history}; ex_ante = proposal.get("ex_ante", {}); before = ex_ante.get("recorded_before_outcome") is True and (outcome_time is None or _time(proposal["recorded_at"]) < _time(outcome_time))
        rows.append({"candidate_id": candidate_id, "eligible_at": proposal["recorded_at"], "funnel_states": [value for value in FUNNEL_ORDER if value in states], "funnel_history": history, "card_ids": proposal["payload"]["card_ids"], "ex_ante": {"recorded_at": proposal["recorded_at"], "recorded_before_outcome": before, "probability": ex_ante.get("probability"), "ordinal": ex_ante.get("ordinal")}, "outcome": {"label": outcome_label, "independent": independent, "recorded_at": outcome_time, "review_ref": outcome_review["review_id"] if outcome_review else None}, "attempt_refs": [item["attempt_id"] for item in linked_attempts], "review_refs": [item["review_id"] for item in linked_outcomes], "finding_refs": [item["finding_id"] for item in linked_findings], "cost": _sum_cost([*linked_attempts, *({"cost": review.get("review_cost", {})} for review in linked_outcomes)])})
    rows.sort(key=lambda item: item["candidate_id"]); denominator_complete = len(proposals) == len(rows) == len({row["candidate_id"] for row in rows})
    reasons: set[str] = set()
    if not rows or not denominator_complete: reasons.add("missing_denominator")
    if any(row["ex_ante"]["probability"] is None for row in rows): reasons.add("missing_ex_ante_probability")
    if any(not row["ex_ante"]["recorded_before_outcome"] for row in rows): reasons.add("post_outcome_confidence")
    if any(not row["outcome"]["independent"] for row in rows): reasons.add("missing_independent_outcome")
    if any(row["outcome"]["label"] == "unresolved" for row in rows): reasons.add("unresolved_outcome")
    if len(rows) < 30: reasons.add("small_sample")
    core_eligible = not reasons
    cost_records = [*attempts, *({"cost": review.get("review_cost", {})} for review in reviews)]
    cost_dimension_coverage = {field: {"records": len(cost_records), "measured": sum(record.get("cost", {}).get(field) is not None for record in cost_records)} for field in COST_FIELDS}
    export = {"schema_version": 1, "export_id": f"telemetry-{state['engagement_id']}", "engagement_id": state["engagement_id"], "classification": "calibration" if core_eligible else "telemetry", "source_hashes": state["source_hashes"], "denominator": {"eligible_count": len(proposals), "exported_count": len(rows), "complete": denominator_complete}, "candidates": rows, "cost_totals": _sum_cost(cost_records), "cost_coverage": {"attempt_count": len(attempts), "attempts_with_cost": sum("cost" in attempt for attempt in attempts), "review_count": len(reviews), "reviews_with_cost": sum("review_cost" in review for review in reviews)}, "cost_dimension_coverage": cost_dimension_coverage, "calibration_eligibility": {"eligible": core_eligible, "reasons": sorted(reasons)}, "policy": {"automatic_card_deletion": False, "automatic_prompt_change": False, "bandit_enabled": False}}
    errors = validate_record(export, "research-telemetry")
    if errors: raise RecordError("telemetry_export_invalid", "derived telemetry failed schema", errors)
    if output is not None: atomic_write(output, canonical_json_bytes(export))
    return export


def score_telemetry(export: dict[str, Any]) -> dict[str, Any]:
    errors = validate_record(export, "research-telemetry")
    if errors: raise RecordError("telemetry_input_invalid", "telemetry export failed schema", errors)
    rows = export["candidates"]; counts = {state: sum(state in row["funnel_states"] for row in rows) for state in FUNNEL_ORDER}
    result: dict[str, Any] = {"classification": export["classification"], "candidate_count": len(rows), "funnel_counts": counts, "cost_totals": export["cost_totals"], "cost_coverage": export["cost_coverage"], "cost_dimension_coverage": export["cost_dimension_coverage"], "brier_score": None, "reliability": [], "ordinal": {"weak_or_strong_with_outcome": 0, "strong_positive": 0, "weak_or_negative_positive": 0}, "small_sample": len(rows) < 30, "automatic_actions": [], "bandit_enabled": False}
    labeled = [row for row in rows if row["outcome"]["independent"] and row["outcome"]["label"] in {"positive", "negative"}]
    result["ordinal"] = {"weak_or_strong_with_outcome": sum(row["ex_ante"]["ordinal"] is not None for row in labeled), "strong_positive": sum(row["ex_ante"]["ordinal"] == "strong" and row["outcome"]["label"] == "positive" for row in labeled), "weak_or_negative_positive": sum(row["ex_ante"]["ordinal"] in {"weak", "negative"} and row["outcome"]["label"] == "positive" for row in labeled)}
    if export["classification"] == "calibration" and export["calibration_eligibility"]["eligible"]:
        result["brier_score"] = sum((row["ex_ante"]["probability"] - (1 if row["outcome"]["label"] == "positive" else 0)) ** 2 for row in rows) / len(rows)
        for lower in (0.0, 0.2, 0.4, 0.6, 0.8):
            bucket = [row for row in rows if lower <= row["ex_ante"]["probability"] <= 1.0] if lower == 0.8 else [row for row in rows if lower <= row["ex_ante"]["probability"] < lower + 0.2]
            if bucket: result["reliability"].append({"lower": lower, "upper": 1.0 if lower == 0.8 else lower + 0.2, "count": len(bucket), "mean_probability": sum(row["ex_ante"]["probability"] for row in bucket) / len(bucket), "positive_rate": sum(row["outcome"]["label"] == "positive" for row in bucket) / len(bucket)})
    return result
