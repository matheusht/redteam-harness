#!/usr/bin/env python3
"""Append-only ledgers and deterministic reducers for Decision 0005 engagements."""

from __future__ import annotations

import copy
import fcntl
import json
import os
import re
import secrets
import stat
import tempfile
from contextlib import contextmanager, nullcontext
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from engagement_records import (
    RecordError,
    build_reference_index,
    canonical_json_bytes,
    detect_secret_classes,
    load_json,
    resolve_schema_name,
    scan_file_secret_classes,
    sha256_bytes,
    sha256_file,
    validate_record,
    validate_record_references,
)
from finding_review import claim_rows, claim_tuple_hash, render_claim_proof, render_internal_report
from decision6_capabilities import artifact_variant, classify_event, require_actor

LEDGERS = {
    "event": ("events.jsonl", "engagement-event", "event_id"),
    "attempt": ("attempts.jsonl", "attempt-v2", "attempt_id"),
    "artifact": ("artifacts.jsonl", "artifact", "artifact_id"),
}
STATE_VALUES = {
    "claim": {"needs_review", "supported", "confirmed", "contaminated", "refuted"},
    "search": {"queued", "selected", "running", "held", "exhausted", "deferred", "blocked", "closed"},
    "coverage": {"active", "blocked", "coverage_dry"},
    "report": {"none", "draft", "accepted", "submitted"},
    "cleanup": {"open", "completed", "not_applicable", "blocked"},
    "memory": {"pending", "promote", "defer", "no_novel_lesson"},
    "engagement": {"active", "blocked", "closed"},
    "environment": {"ready", "blocked", "needs_review"},
}
EVENT_STATE_RULES = {
    "scope.attested": ({"engagement", "coverage", "memory"}, set()),
    "candidate.proposed": ({"search"}, {"search"}),
    "candidate.selected": ({"search"}, {"search"}),
    "candidate.skipped": ({"search"}, {"search"}),
    "candidate.deferred": ({"search"}, {"search"}),
    "operator_prior.recorded": ({"search", "coverage"}, set()),
    "hypothesis.created": ({"search"}, {"search"}),
    "hypothesis.status_changed": ({"search"}, {"search"}),
    "claim.adjudicated": ({"claim"}, {"claim"}),
    "finding.revised": (set(), set()),
    "review.regrade_completed": (set(), set()),
    "review.pocinator_completed": (set(), set()),
    "coverage.status_changed": ({"coverage"}, {"coverage"}),
    "report.generated": ({"report"}, {"report"}),
    "operator.review_recorded": ({"report"}, {"report"}),
    "submission.recorded": ({"report"}, {"report"}),
    "cleanup.updated": ({"cleanup"}, {"cleanup"}),
    "memory.disposition_recorded": ({"memory"}, {"memory"}),
    "engagement.blocked": ({"engagement", "coverage"}, {"engagement", "coverage"}),
    "engagement.reopened": ({"engagement", "coverage"}, {"engagement", "coverage"}),
    "engagement.closed": ({"engagement"}, {"engagement"}),
    "authority.requested": (set(), set()),
    "authority.resolved": (set(), set()),
    "scope.amendment_proposed": (set(), set()),
    "artifact.classified": (set(), set()),
    "environment.review_recorded": ({"environment"}, {"environment"}),
    "environment.preflight_recorded": ({"environment"}, set()),
}

COMMITTED_RECORD_LAYOUT = {
    "environment-preflight": "environment/preflight-*.json",
    "finding-v3": "findings/*/rev-*.json",
    "review": "reviews/*.json",
    "report-manifest": "reports/*.manifest.json",
    "memory-disposition": "memory/disposition-*.json",
    "migration-manifest": "legacy/migration-manifest.json",
}
COMMITTED_RECORD_SCHEMAS = {
    "environment-preflight": "environment-preflight", "finding-v3": "finding-v3", "review": "review",
    "report-manifest": "report-manifest", "memory-disposition": "memory-disposition", "migration-manifest": "migration-manifest",
}

TRANSITIONS = {
    "claim": {None: {"needs_review", "supported"}, "needs_review": {"supported", "contaminated", "refuted"}, "supported": {"confirmed", "needs_review", "contaminated", "refuted"}, "confirmed": {"needs_review", "contaminated", "refuted"}, "contaminated": {"needs_review", "refuted"}, "refuted": {"needs_review"}},
    "search": {None: {"queued"}, "queued": {"selected", "deferred", "blocked", "closed"}, "selected": {"running", "deferred", "blocked"}, "running": {"queued", "held", "exhausted", "deferred", "blocked", "closed"}, "held": {"queued", "closed"}, "exhausted": {"queued", "closed"}, "deferred": {"queued", "closed"}, "blocked": {"queued", "deferred", "closed"}, "closed": {"queued"}},
    "coverage": {None: {"active"}, "active": {"blocked", "coverage_dry"}, "blocked": {"active", "coverage_dry"}, "coverage_dry": {"active"}},
    "report": {None: {"none", "draft"}, "none": {"draft"}, "draft": {"accepted", "none"}, "accepted": {"submitted", "draft"}, "submitted": {"draft"}},
    "cleanup": {None: {"open", "completed", "not_applicable", "blocked"}, "open": {"completed", "not_applicable", "blocked"}, "blocked": {"completed", "not_applicable"}, "completed": set(), "not_applicable": set()},
    "memory": {None: {"pending", "promote", "defer", "no_novel_lesson"}, "pending": {"promote", "defer", "no_novel_lesson"}, "promote": {"defer"}, "defer": {"promote", "no_novel_lesson"}, "no_novel_lesson": {"defer", "promote"}},
    "engagement": {None: {"active"}, "active": {"blocked", "closed"}, "blocked": {"active", "closed"}, "closed": set()},
    "environment": {None: {"ready", "blocked", "needs_review"}, "needs_review": {"ready", "blocked"}, "ready": {"blocked"}, "blocked": set()},
}


def _reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RecordError("duplicate_json_key", f"duplicate JSON object key in ledger: {key}")
        result[key] = value
    return result


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def compute_record_hash(record: dict[str, Any]) -> str:
    body = copy.deepcopy(record)
    body.pop("record_hash", None)
    return sha256_bytes(canonical_json_bytes(body))


def _governed_root(path: Path) -> tuple[Path, tuple[str, ...]]:
    absolute = Path(os.path.abspath(path))
    for candidate in (absolute.parent, *absolute.parents[1:]):
        try:
            scope_stat = (candidate / "scope.md").lstat()
        except OSError:
            continue
        if stat.S_ISREG(scope_stat.st_mode) and not stat.S_ISLNK(scope_stat.st_mode):
            relative = absolute.relative_to(candidate)
            if relative.parts and all(part not in {"", ".", ".."} for part in relative.parts): return candidate, relative.parts
    return absolute.parent, (absolute.name,)


def _open_absolute_directory(path: Path) -> int:
    absolute = Path(os.path.abspath(path))
    if not absolute.is_absolute(): raise RecordError("unsafe_governed_path", str(path))
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0); fd = os.open("/", flags)
    try:
        for component in absolute.parts[1:]:
            child = os.open(component, flags, dir_fd=fd); os.close(fd); fd = child
        return fd
    except Exception: os.close(fd); raise


def _open_parent_fd(root: Path, parts: tuple[str, ...], *, create: bool) -> tuple[int, str]:
    if not parts: raise RecordError("unsafe_governed_path", str(root))
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = _open_absolute_directory(root)
    try:
        for component in parts[:-1]:
            if create:
                try: os.mkdir(component, 0o700, dir_fd=fd)
                except FileExistsError: pass
            child = os.open(component, flags, dir_fd=fd); os.close(fd); fd = child
        return fd, parts[-1]
    except Exception:
        os.close(fd); raise


def read_governed_file(path: Path) -> bytes:
    root, parts = _governed_root(path); parent_fd, name = _open_parent_fd(root, parts, create=False)
    try:
        fd = os.open(name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=parent_fd)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode): raise RecordError("unsafe_governed_path", str(path))
            chunks: list[bytes] = []
            while True:
                chunk = os.read(fd, 1024 * 1024)
                if not chunk: break
                chunks.append(chunk)
            after = os.fstat(fd)
            if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns): raise RecordError("governed_file_changed_during_read", str(path))
            return b"".join(chunks)
        finally: os.close(fd)
    finally: os.close(parent_fd)


def load_json(path: Path) -> Any:
    try: return json.loads(read_governed_file(path), object_pairs_hook=_reject_duplicates)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc: raise RecordError("governed_json_invalid", str(path), [str(exc)]) from exc


def atomic_write(path: Path, data: bytes) -> None:
    root, parts = _governed_root(path); parent_fd, name = _open_parent_fd(root, parts, create=True); temporary = f".{name}.{os.getpid()}.{secrets.token_hex(8)}"
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600, dir_fd=parent_fd)
        try:
            view = memoryview(data); total = 0
            while total < len(data): total += os.write(fd, view[total:])
            os.fsync(fd)
        finally: os.close(fd)
        os.replace(temporary, name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd); os.fsync(parent_fd)
    finally:
        try: os.unlink(temporary, dir_fd=parent_fd)
        except FileNotFoundError: pass
        os.close(parent_fd)


@contextmanager
def engagement_lock(engagement: Path) -> Iterator[None]:
    engagement = engagement.absolute(); root_fd = _open_absolute_directory(engagement)
    fd = os.open(".record-kernel.lock", os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600, dir_fd=root_fd)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode): raise RecordError("unsafe_governed_path", ".record-kernel.lock")
        fcntl.flock(fd, fcntl.LOCK_EX); yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN); os.close(fd); os.close(root_fd)


def _parse_ledger_data(data: bytes, relative: str, schema: str, identity: str) -> list[dict[str, Any]]:
    if data and not data.endswith(b"\n"):
        raise RecordError("ledger_unterminated_tail", f"{relative} does not end at a committed line boundary")
    physical_lines = data.split(b"\n")[:-1] if data else []
    records: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    previous: str | None = None
    previous_time: datetime | None = None
    for line_number, raw_line in enumerate(physical_lines, 1):
        if not raw_line:
            raise RecordError("ledger_blank_line", f"{relative}:{line_number}")
        try:
            record = json.loads(raw_line.decode("utf-8"), object_pairs_hook=_reject_duplicates)
        except UnicodeDecodeError as exc:
            raise RecordError("ledger_invalid_utf8", f"{relative}:{line_number}: {exc}") from exc
        except RecordError:
            raise
        except json.JSONDecodeError as exc:
            raise RecordError("ledger_interrupted_line", f"{relative}:{line_number}: {exc}") from exc
        if not isinstance(record, dict):
            raise RecordError("ledger_record_not_object", f"{relative}:{line_number}")
        if raw_line + b"\n" != canonical_json_bytes(record):
            raise RecordError("ledger_noncanonical_line", f"{relative}:{line_number}")
        errors = validate_record(record, schema)
        if errors:
            raise RecordError("ledger_schema_invalid", f"{relative}:{line_number}", errors)
        timestamp = datetime.fromisoformat(record["recorded_at"].replace("Z", "+00:00")) if "recorded_at" in record else datetime.fromisoformat(record["created_at"].replace("Z", "+00:00"))
        if previous_time is not None and timestamp < previous_time:
            raise RecordError("ledger_time_regression", f"{relative}:{line_number}")
        previous_time = timestamp
        expected_sequence = len(records) + 1
        if record["sequence"] != expected_sequence:
            raise RecordError("ledger_sequence_gap", f"{relative}:{line_number} expected {expected_sequence}")
        if record["previous_hash"] != previous:
            raise RecordError("ledger_previous_hash_mismatch", f"{relative}:{line_number}")
        if record["record_hash"] != compute_record_hash(record):
            raise RecordError("ledger_record_hash_mismatch", f"{relative}:{line_number}")
        record_id = record[identity]
        if record_id in seen_ids:
            raise RecordError("duplicate_ledger_id", f"{relative}:{record_id}")
        seen_ids.add(record_id)
        previous = record["record_hash"]
        records.append(record)
    return records


def read_ledger(engagement: Path, kind: str) -> list[dict[str, Any]]:
    if kind not in LEDGERS:
        raise RecordError("unknown_ledger", kind)
    relative, schema, identity = LEDGERS[kind]
    path = engagement / relative
    try: data = read_governed_file(path)
    except FileNotFoundError: return []
    except OSError as exc: raise RecordError("unsafe_ledger_path", relative, [str(exc)]) from exc
    return _parse_ledger_data(data, relative, schema, identity)


def materialize_ledger_record(kind: str, proposal: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    _, schema, identity = LEDGERS[kind]
    record = copy.deepcopy(proposal)
    for forbidden in ("sequence", "previous_hash", "record_hash"):
        if forbidden in record:
            raise RecordError("trusted_field_in_proposal", f"proposal must not set {forbidden}")
    if not isinstance(record.get(identity), str):
        raise RecordError("record_identity_missing", identity)
    if any(existing[identity] == record[identity] for existing in records):
        raise RecordError("duplicate_ledger_id", record[identity])
    record["sequence"] = len(records) + 1
    record["previous_hash"] = records[-1]["record_hash"] if records else None
    record["record_hash"] = compute_record_hash(record)
    errors = validate_record(record, schema)
    if errors:
        raise RecordError("record_schema_invalid", f"cannot append {kind}", errors)
    return record


def append_ledger_record(engagement: Path, kind: str, proposal: dict[str, Any], *, lock_held: bool = False) -> dict[str, Any]:
    relative, _, _ = LEDGERS[kind]
    with (nullcontext() if lock_held else engagement_lock(engagement)):
        records = read_ledger(engagement, kind)
        record = materialize_ledger_record(kind, proposal, records)
        line = canonical_json_bytes(record)
        path = engagement / relative; root, parts = _governed_root(path); parent_fd, name = _open_parent_fd(root, parts, create=False)
        try: fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0), 0o600, dir_fd=parent_fd)
        except Exception: os.close(parent_fd); raise
        original = os.fstat(fd)
        if not stat.S_ISREG(original.st_mode): os.close(fd); os.close(parent_fd); raise RecordError("unsafe_ledger_path", relative)
        original_size = original.st_size
        try:
            view = memoryview(line); total = 0
            while total < len(line):
                written = os.write(fd, view[total:])
                if written <= 0: raise OSError("append made no progress")
                total += written
            os.fsync(fd)
        except Exception as exc:
            os.ftruncate(fd, original_size); os.fsync(fd)
            raise RecordError("ledger_append_rolled_back", f"{relative}: append failed and tail was truncated to last verified boundary: {exc}") from exc
        finally:
            os.close(fd); os.close(parent_fd)
        return record


def repair_ledger_tail(engagement: Path, kind: str, operator_id: str, reason: str, recorded_at: str | None = None, authority_request_ref: str | None = None, executor_id: str | None = None, session_id: str | None = None) -> dict[str, Any]:
    if kind not in LEDGERS or not reason.strip():
        raise RecordError("tail_repair_input_invalid", "known ledger and non-empty reason required")
    engagement = engagement.absolute()
    relative, schema, identity = LEDGERS[kind]
    marker_path = engagement / "legacy" / "tail-repair.pending.json"
    with engagement_lock(engagement):
        event_bytes = read_governed_file(engagement / "events.jsonl"); event_boundary = event_bytes.rfind(b"\n") + 1 if event_bytes and not event_bytes.endswith(b"\n") else len(event_bytes); intact_events = _parse_ledger_data(event_bytes[:event_boundary], "events.jsonl", "engagement-event", "event_id")
        signed_operator = next(event["payload"]["operator_id"] for event in reversed(intact_events) if event["event_type"] == "scope.attested")
        if operator_id != signed_operator:
            raise RecordError("tail_repair_operator_mismatch", "repair operator must match the active attested scope")
        if marker_path.exists():
            marker = json.loads(read_governed_file(marker_path))
            if marker.get("operator_id") != operator_id or marker.get("ledger_kind") != kind:
                raise RecordError("tail_repair_pending_conflict", str(marker_path))
            path = engagement / relative
            try: data = read_governed_file(path)
            except FileNotFoundError: data = b""
            if data and not data.endswith(b"\n"):
                boundary = data.rfind(b"\n") + 1
                prefix, tail = data[:boundary], data[boundary:]
                if sha256_bytes(prefix) != marker.get("prefix_digest") or sha256_bytes(tail) != marker.get("quarantine_digest"):
                    raise RecordError("tail_repair_pending_bytes_mismatch", relative)
                _parse_ledger_data(prefix, relative, schema, identity)
                atomic_write(path, prefix)
            elif sha256_bytes(data) != marker.get("prefix_digest"):
                raise RecordError("tail_repair_pending_prefix_mismatch", relative)
        else:
            path = engagement / relative
            try: data = read_governed_file(path)
            except FileNotFoundError: data = b""
            if not data or data.endswith(b"\n"):
                raise RecordError("tail_repair_not_needed", relative)
            boundary = data.rfind(b"\n") + 1
            prefix, tail = data[:boundary], data[boundary:]
            _parse_ledger_data(prefix, relative, schema, identity)
            if kind == "event" and not _parse_ledger_data(prefix, relative, schema, identity):
                raise RecordError("tail_repair_no_scope_prefix", "event ledger has no committed scope event")
            tail_digest = sha256_bytes(tail)
            quarantine_rel = f"legacy/quarantine/{kind}-tail-{tail_digest[-12:]}.bin"
            atomic_write(engagement / quarantine_rel, tail)
            marker = {"schema_version": 1, "ledger_kind": kind, "ledger_path": relative, "prefix_digest": sha256_bytes(prefix), "quarantine_path": quarantine_rel, "quarantine_digest": tail_digest, "operator_id": operator_id, "reason": reason.strip(), "recorded_at": recorded_at or utc_now()}
            atomic_write(marker_path, canonical_json_bytes(marker))
            atomic_write(path, prefix)
        events = read_ledger(engagement, "event")
        event_id = f"event-tail-repair-{marker['quarantine_digest'][-12:]}"
        existing = next((event for event in events if event["event_id"] == event_id), None)
        if existing is None:
            proposal = base_event(event_id=event_id, engagement_id=events[0]["engagement_id"], recorded_at=marker["recorded_at"], actor_role="broker" if authority_request_ref else "operator", actor_id=executor_id if authority_request_ref else operator_id, event_type="observation.recorded", rationale=f"Operator quarantined an uncommitted {kind} ledger tail: {marker['reason']}", payload={"entity_id": f"{kind}-ledger", "entity_type": "ledger_tail_repair", "status": "repaired", "reason": marker["reason"], "record_path": marker["quarantine_path"], "record_digest": marker["quarantine_digest"], **({"authority_request_ref": authority_request_ref, "operator_id": operator_id} if authority_request_ref else {})}, session_id=session_id, operation_class="notebook" if authority_request_ref else None)
            preview = materialize_ledger_record("event", proposal, events)
            validate_event_semantics(preview)
            append_ledger_record(engagement, "event", proposal, lock_held=True)
        snapshot = reduce_engagement(engagement)
        write_snapshot(engagement, snapshot)
        from engagement_views import write_views
        write_views(engagement, snapshot)
        marker_path.unlink(missing_ok=True)
        return {"event_id": event_id, "quarantine_path": marker["quarantine_path"], "quarantine_digest": marker["quarantine_digest"]}


def _safe_engagement_file(engagement: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or not rel.parts or any(part in {"", ".", ".."} for part in rel.parts): raise RecordError("committed_path_escape", relative)
    candidate = engagement.absolute() / rel
    try: read_governed_file(candidate)
    except FileNotFoundError as exc: raise RecordError("committed_file_missing", relative) from exc
    except (OSError, RecordError) as exc: raise RecordError("committed_path_escape", relative, [str(exc)]) from exc
    return candidate


def validate_committed_payload(engagement: Path, payload: dict[str, Any]) -> None:
    relative = payload["record_path"]
    record_type = payload["record_type"]
    pattern = COMMITTED_RECORD_LAYOUT.get(record_type)
    if pattern is None or not Path(relative).match(pattern):
        raise RecordError("committed_record_layout_mismatch", f"{record_type}:{relative}")
    path = _safe_engagement_file(engagement, relative)
    if sha256_bytes(read_governed_file(path)) != payload["record_digest"]:
        raise RecordError("committed_file_digest_mismatch", relative)
    schema = COMMITTED_RECORD_SCHEMAS.get(record_type)
    if schema:
        value = load_json(path)
        if record_type == "environment-preflight":
            schema = resolve_schema_name(value)
            if schema not in {"environment-preflight", "environment-preflight-v2"}:
                raise RecordError("committed_file_schema_invalid", relative)
        errors = validate_record(value, schema)
        if errors:
            raise RecordError("committed_file_schema_invalid", relative, errors)
        identity_fields = {"environment-preflight": "preflight_id", "finding-v3": "finding_id", "review": "review_id", "report-manifest": "report_id", "memory-disposition": "disposition_id", "migration-manifest": "migration_id"}
        expected_id = value.get(identity_fields[record_type])
        expected_revision = value.get("revision") if record_type == "finding-v3" else None
        if expected_id != payload["record_id"] or expected_revision != payload["record_revision"]:
            raise RecordError("committed_file_identity_mismatch", relative)


def verify_file_authority(engagement: Path, events: list[dict[str, Any]], artifacts: list[dict[str, Any]], *, allowed_record_orphans: set[str] | None = None, allowed_artifact_orphans: set[str] | None = None) -> None:
    committed: dict[str, dict[str, Any]] = {}
    for event in events:
        if event["event_type"] != "record.committed":
            continue
        payload = event["payload"]
        relative = payload["record_path"]
        if relative in committed:
            raise RecordError("duplicate_file_commit", relative)
        validate_committed_payload(engagement, payload)
        committed[relative] = payload
    governed_files: set[str] = set()
    for pattern in COMMITTED_RECORD_LAYOUT.values():
        governed_files.update(path.relative_to(engagement).as_posix() for path in engagement.glob(pattern) if path.is_file())
    orphan_records = sorted(governed_files - set(committed) - (allowed_record_orphans or set()))
    if orphan_records:
        raise RecordError("orphan_immutable_record", ", ".join(orphan_records))
    bound_reports: set[str] = set()
    for relative, payload in committed.items():
        if payload["record_type"] == "report-manifest":
            bound_reports.add(load_json(engagement / relative)["report_path"])
    for relative in allowed_record_orphans or set():
        if relative.endswith(".manifest.json") and (engagement / relative).is_file():
            value = load_json(engagement / relative)
            if value.get("report_path"):
                bound_reports.add(value["report_path"])
    report_files = {path.relative_to(engagement).as_posix() for path in (engagement / "reports").glob("**/*.md") if path.is_file()}
    orphan_reports = sorted(report_files - bound_reports)
    if orphan_reports:
        raise RecordError("orphan_report_file", ", ".join(orphan_reports))

    artifact_paths: set[str] = set()
    for artifact in artifacts:
        relative = artifact["relative_path"]
        if relative in artifact_paths:
            raise RecordError("duplicate_artifact_path", relative)
        path = _safe_engagement_file(engagement, relative)
        if path.stat().st_size != artifact["size"] or sha256_file(path) != artifact["sha256"]:
            raise RecordError("artifact_file_digest_mismatch", relative)
        artifact_paths.add(relative)
    evidence_files = {
        path.relative_to(engagement).as_posix() for path in (engagement / "evidence").glob("**/*")
        if path.is_file() and path.name != ".gitkeep"
    }
    orphan_artifacts = sorted(evidence_files - artifact_paths - (allowed_artifact_orphans or set()))
    if orphan_artifacts:
        raise RecordError("orphan_artifact_file", ", ".join(orphan_artifacts))


def _scope_metadata(scope_path: Path) -> dict[str, str]:
    try: scope_bytes = read_governed_file(scope_path); text = scope_bytes.decode("utf-8")
    except FileNotFoundError: raise RecordError("scope_missing", str(scope_path))
    except (OSError, UnicodeDecodeError) as exc: raise RecordError("scope_missing", str(scope_path), [str(exc)]) from exc
    if re.search(r"\[fill|\[target|\[project|\[name|\[date|<[^>]+>|___", text, re.IGNORECASE):
        raise RecordError("scope_unsigned_or_incomplete", "scope contains placeholders")
    if not re.search(r"^- Signed:\s*\[[xX]\]\s*$", text, re.MULTILINE):
        raise RecordError("scope_unsigned_or_incomplete", "scope signature checkbox is not checked")
    required_sections = ("## Surfaces in scope", "## Benign safe-objective set", "## Escalation ceiling", "## Impact-demo authorization", "## Accounts / fixtures", "## Authorization")
    missing_sections = [heading for heading in required_sections if heading not in text]
    if missing_sections:
        raise RecordError("scope_sections_missing", ", ".join(missing_sections))
    kernels=[kernel for kernel in ("decision-0005-v1","decision-0006-v1") if f"- Record kernel: `{kernel}`" in text]
    if len(kernels)!=1: raise RecordError("record_kernel_not_selected", "scope must select exactly one supported record kernel")
    operator = re.search(r"^- Operator:\s*(.+?)\s*$", text, re.MULTILINE)
    signed = re.search(r"^- Date:\s*(\d{4}-\d{2}-\d{2})\s*$", text, re.MULTILINE)
    if not operator or not signed or operator.group(1).strip().startswith("["):
        raise RecordError("scope_signature_missing", "operator and ISO date are required")
    return {"operator": operator.group(1).strip(), "date": signed.group(1), "scope_hash": sha256_bytes(scope_bytes), "record_kernel": kernels[0]}


def require_scope_zone2_authorized(engagement: Path, scope_hash: str, category: str = "zone2_artifact_creation") -> None:
    snapshot = engagement / "scope-attestations" / f"{scope_hash.removeprefix('sha256:')}.md"
    try: snapshot_bytes = read_governed_file(snapshot)
    except (OSError, RecordError): raise RecordError("zone2_scope_snapshot_invalid", scope_hash)
    if sha256_bytes(snapshot_bytes) != scope_hash: raise RecordError("zone2_scope_snapshot_invalid", scope_hash)
    try: text = snapshot_bytes.decode("utf-8")
    except UnicodeDecodeError: raise RecordError("zone2_scope_snapshot_invalid", scope_hash)
    def value(name: str) -> str | None:
        occurrence = [name] * text.lower().count(name.lower()); pattern = rf"^\s*-\s*(?:\*\*{re.escape(name)}:\*\*|{re.escape(name)}:)\s*`([^`]*)`\s*(?:←[^\n]*)?$"; matches = re.findall(pattern, text, re.MULTILINE | re.IGNORECASE); return matches[0].strip().lower() if len(occurrence) == len(matches) == 1 else None
    authorized = value("impact_demo_authorized") == "yes"; categories = {item.strip() for item in (value("zone2_authorized_categories") or "").split(",") if item.strip()}; ceiling = value("zone2_escalation_ceiling"); containment = value("zone2_containment"); placeholders = {"none", "n/a", "no", "tbd", "unknown", "to be determined", "todo", "placeholder"}
    if not authorized or category.lower() not in categories or ceiling != "artifact_creation" or not containment or containment in placeholders or len(containment) < 8 or any(token in containment for token in ("<", ">", "[", "]", "{", "}", "___", "*")) or any(marker in containment for marker in ("tbd", "unknown", "placeholder", "todo", "none", "n/a", "to be determined")): raise RecordError("zone2_not_authorized_by_scope", category)


def persist_scope_snapshot(engagement: Path, scope_hash: str) -> str:
    source = engagement / "scope.md"
    data = read_governed_file(source)
    if sha256_bytes(data) != scope_hash:
        raise RecordError("scope_snapshot_source_mismatch", "scope.md does not match attested hash")
    relative = f"scope-attestations/{scope_hash.removeprefix('sha256:')}.md"
    destination = engagement / relative
    if destination.exists():
        if read_governed_file(destination) != data:
            raise RecordError("scope_snapshot_collision", relative)
    else:
        atomic_write(destination, data)
    return relative


def validate_scope_event_snapshot(engagement: Path, event: dict[str, Any]) -> None:
    payload = event["payload"]
    expected_relative = f"scope-attestations/{payload['scope_hash'].removeprefix('sha256:')}.md"
    if payload.get("scope_snapshot_path") != expected_relative:
        raise RecordError("scope_snapshot_path_mismatch", event["event_id"])
    snapshot_path = _safe_engagement_file(engagement, expected_relative)
    metadata = _scope_metadata(snapshot_path)
    signed_operator = re.sub(r"[^A-Za-z0-9._:-]+", "-", metadata["operator"]).strip("-") or "operator"
    if metadata["scope_hash"] != payload["scope_hash"] or metadata["date"] != payload.get("signed_date") or metadata["record_kernel"] != payload.get("record_kernel") or event["actor"] != {"role": "operator", "id": signed_operator} or payload.get("operator_id") != signed_operator:
        raise RecordError("historical_scope_attestation_mismatch", event["event_id"])


def base_event(*, event_id: str, engagement_id: str, recorded_at: str, actor_role: str, actor_id: str, event_type: str, rationale: str, payload: dict[str, Any], entity_refs: list[str] | None = None, evidence_refs: list[str] | None = None, review_refs: list[str] | None = None, finding_refs: list[str] | None = None, state_changes: list[dict[str, Any]] | None = None, session_id: str | None = None, operation_class: str | None = None, model: str | None = None, provider: str | None = None, tool_versions: list[str] | None = None) -> dict[str, Any]:
    actor = {"role": actor_role, "id": actor_id}
    result: dict[str, Any] = {
        "schema_version": 1,
        "event_id": event_id,
        "engagement_id": engagement_id,
        "recorded_at": recorded_at,
        "actor": actor,
        "event_type": event_type,
        "entity_refs": entity_refs or [],
        "rationale": rationale,
        "evidence_refs": evidence_refs or [],
        "review_refs": review_refs or [],
        "finding_refs": finding_refs or [],
        "provenance": {"actor": actor, "session_id": session_id, "model": model, "provider": provider, "prompt_version": None, "card_versions": [], "tool_versions": tool_versions or []},
        "ex_ante": None,
        "state_changes": state_changes or [],
        "payload": payload,
    }
    if operation_class is not None:
        result["operation_class"] = operation_class
    return result


def initialize_engagement(engagement: Path, recorded_at: str | None = None) -> dict[str, Any]:
    engagement = engagement.absolute()
    root_fd = _open_absolute_directory(engagement)
    try:
        metadata = _scope_metadata(engagement / "scope.md")
        engagement_id = engagement.name
        directories = ("reviews", "reports", "submissions", "environment", "evidence", "findings", "legacy", "memory", "scope-attestations")
        for name in directories:
            try: os.mkdir(name, 0o700, dir_fd=root_fd)
            except FileExistsError: pass
            child = os.open(name, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0), dir_fd=root_fd); os.close(child)
        for ledger in ("events.jsonl", "attempts.jsonl", "artifacts.jsonl"):
            fd = os.open(ledger, os.O_WRONLY | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600, dir_fd=root_fd)
            if not stat.S_ISREG(os.fstat(fd).st_mode): os.close(fd); raise RecordError("unsafe_ledger_path", ledger)
            os.close(fd)
    finally: os.close(root_fd)
    existing = read_ledger(engagement, "event")
    if existing:
        first = existing[0]
        active_scope = next(event["payload"]["scope_hash"] for event in reversed(existing) if event["event_type"] == "scope.attested")
        if first["event_type"] != "scope.attested" or active_scope != metadata["scope_hash"]:
            raise RecordError("engagement_already_initialized", "existing ledger is bound to different scope bytes")
    else:
        operator_id = re.sub(r"[^A-Za-z0-9._:-]+", "-", metadata["operator"]).strip("-") or "operator"
        scope_snapshot_path = persist_scope_snapshot(engagement, metadata["scope_hash"])
        proposal = base_event(
            event_id=f"event-scope-{metadata['scope_hash'][-12:]}", engagement_id=engagement_id,
            recorded_at=recorded_at or utc_now(), actor_role="operator", actor_id=operator_id,
            event_type="scope.attested", rationale="Operator-signed scope bytes attested for the Decision 0005 record kernel.",
            payload={"scope_hash": metadata["scope_hash"], "scope_snapshot_path": scope_snapshot_path, "operator_id": operator_id, "signed_date": metadata["date"], "record_kernel": metadata["record_kernel"], "supersedes_scope_hash": None},
            entity_refs=[engagement_id],
            state_changes=[
                {"dimension": "engagement", "entity_id": engagement_id, "previous": None, "current": "active"},
                {"dimension": "coverage", "entity_id": engagement_id, "previous": None, "current": "active"},
                {"dimension": "memory", "entity_id": engagement_id, "previous": None, "current": "pending"},
            ],
        )
        append_ledger_record(engagement, "event", proposal)
    snapshot = reduce_engagement(engagement)
    write_snapshot(engagement, snapshot)
    from engagement_views import write_views
    write_views(engagement, snapshot)
    return snapshot


def validate_event_semantics(event: dict[str, Any]) -> None:
    changes = event.get("state_changes", [])
    dimensions = {change.get("dimension") for change in changes}
    event_type = event.get("event_type")
    allowed, required = EVENT_STATE_RULES.get(event_type, (set(), set()))
    if not dimensions.issubset(allowed):
        raise RecordError("event_state_dimension_mismatch", f"{event_type} cannot change {sorted(dimensions - allowed)}")
    if not required.issubset(dimensions):
        raise RecordError("event_required_transition_missing", f"{event_type} must change {sorted(required - dimensions)}")
    by_dimension = {change["dimension"]: change for change in changes}
    if len(by_dimension) != len(changes):
        raise RecordError("duplicate_event_state_dimension", event["event_id"])
    payload = event.get("payload", {})
    engagement_id = event.get("engagement_id")
    capability = classify_event(event_type, payload)
    if event.get("operation_class") is not None:
        require_actor(capability, event.get("actor", {}).get("role", ""))
    if event.get("operation_class") is not None and event["operation_class"] != capability["tier"]:
        raise RecordError("event_operation_class_mismatch", f"{event_type}:{event.get('operation_class')} != {capability['tier']}")
    if event.get("provenance", {}).get("actor") != event.get("actor"):
        raise RecordError("event_actor_provenance_mismatch", event.get("event_id", "unknown"))
    if event_type in {"report.generated", "operator.review_recorded", "submission.recorded"} and event.get("actor", {}).get("role") not in ({"operator", "broker"} if payload.get("authority_request_ref") else {"operator"}):
        raise RecordError("report_lifecycle_actor_invalid", event.get("event_id", "unknown"))
    if event_type in {"review.regrade_completed", "review.pocinator_completed"} and event.get("actor", {}).get("role") not in ({"reviewer", "broker"} if payload.get("reviewer_id") else {"reviewer"}):
        raise RecordError("typed_review_actor_invalid", event.get("event_id", "unknown"))
    if event_type == "claim.adjudicated" and event.get("actor", {}).get("role") not in ({"reviewer", "broker"} if payload.get("reviewer_id") else {"reviewer"}):
        raise RecordError("claim_adjudicator_role_invalid", event.get("event_id", "unknown"))
    if event_type == "finding.revised" and event.get("actor", {}).get("role") not in ({"operator", "broker"} if payload.get("authority_request_ref") else {"operator"}):
        raise RecordError("finding_filing_actor_invalid", event.get("event_id", "unknown"))
    if event_type == "record.committed" and event.get("actor", {}).get("role") not in {"operator", "broker", "migration"}:
        raise RecordError("file_commit_actor_unauthorized", event.get("event_id", "unknown"))
    if event_type in {"candidate.proposed", "candidate.selected", "candidate.skipped", "candidate.deferred"} and event.get("actor", {}).get("role") not in {"orchestrator", "operator", "broker"}:
        raise RecordError("candidate_actor_unauthorized", event.get("event_id", "unknown"))
    if event_type in {"candidate.selected", "candidate.skipped", "candidate.deferred"}:
        overridden = payload.get("operator_override", False)
        if overridden and (event.get("actor", {}).get("role") != "operator" or not payload.get("override_reason")):
            raise RecordError("candidate_override_authority_invalid", event.get("event_id", "unknown"))
        if not overridden and payload.get("override_reason") is not None:
            raise RecordError("candidate_override_reason_without_override", event.get("event_id", "unknown"))
    if event_type == "candidate.proposed":
        if payload.get("activation_strength") == "negative":
            raise RecordError("negative_signal_not_candidate", "negative routing signals are controls, not candidates")
        if event.get("ex_ante") is None or event["ex_ante"].get("recorded_before_outcome") is not True:
            raise RecordError("candidate_ex_ante_missing", event.get("event_id", "unknown"))
        required_refs = {payload.get("source_observation_ref"), payload.get("routing_review_ref")}
        if None in required_refs or not required_refs.issubset(set(event.get("entity_refs", []))):
            raise RecordError("candidate_provenance_refs_missing", event.get("event_id", "unknown"))
    if event_type == "operator_prior.recorded" and event.get("actor", {}).get("role") not in {"operator", "broker"}:
        raise RecordError("operator_prior_actor_unauthorized", event.get("event_id", "unknown"))
    if event_type == "operator_prior.recorded" and payload.get("reopen_hypothesis_id"):
        expected_changes = {("search", payload["reopen_hypothesis_id"], "queued"), ("coverage", event["engagement_id"], "active")}
        actual_changes = {(change["dimension"], change["entity_id"], change["current"]) for change in event["state_changes"]}
        if actual_changes != expected_changes or not payload.get("reopening_condition"):
            raise RecordError("operator_prior_reopen_binding_invalid", event.get("event_id", "unknown"))
    elif event_type == "operator_prior.recorded" and event["state_changes"]:
        raise RecordError("operator_prior_unbound_state_change", event.get("event_id", "unknown"))
    if event_type == "review.coverage_completed":
        if event.get("actor", {}).get("role") not in ({"reviewer", "broker"} if payload.get("reviewer_id") else {"reviewer"}) or not event.get("review_refs") or payload.get("review_type") != "coverage" or payload.get("verdict") not in {"continue", "coverage_dry", "blocked"}:
            raise RecordError("coverage_review_event_invalid", event.get("event_id", "unknown"))

    if event_type == "scope.attested":
        if event.get("actor", {}).get("role") != "operator" or event.get("actor", {}).get("id") != payload.get("operator_id"):
            raise RecordError("scope_attestation_not_operator_bound", event.get("event_id", "unknown"))
        if event.get("sequence") == 1:
            expected = {"engagement": "active", "coverage": "active", "memory": "pending"}
            if set(by_dimension) != set(expected) or any(by_dimension[dimension]["entity_id"] != engagement_id or by_dimension[dimension]["previous"] is not None or by_dimension[dimension]["current"] != target for dimension, target in expected.items()):
                raise RecordError("initial_state_incomplete", "first scope attestation must initialize exact engagement, coverage, and memory state")
        elif changes:
            raise RecordError("scope_reattestation_changes_state", event["event_id"])
        return

    binding: tuple[str, str | None, str | None] | None = None
    if event_type.startswith("candidate."):
        targets = {"candidate.proposed": "queued", "candidate.selected": "selected", "candidate.skipped": "closed", "candidate.deferred": "deferred"}
        binding = ("search", payload.get("candidate_id"), targets[event_type])
    elif event_type == "hypothesis.created":
        binding = ("search", payload.get("hypothesis_id"), "queued")
    elif event_type == "hypothesis.status_changed":
        binding = ("search", payload.get("hypothesis_id"), payload.get("status"))
    elif event_type == "claim.adjudicated":
        binding = ("claim", payload.get("entity_id"), payload.get("status"))
    elif event_type == "finding.revised":
        binding = None
    elif event_type == "coverage.status_changed":
        binding = ("coverage", engagement_id, payload.get("status"))
    elif event_type == "report.generated":
        binding = ("report", payload.get("report_ref"), "draft")
    elif event_type == "operator.review_recorded":
        binding = ("report", payload.get("report_ref"), "accepted")
    elif event_type == "submission.recorded":
        binding = ("report", payload.get("report_ref"), "submitted")
    elif event_type == "cleanup.updated":
        matching_obligations = [item for item in payload.get("cleanup_obligations", []) if item.get("obligation_id") == payload.get("entity_id")]
        if len(matching_obligations) != 1 or matching_obligations[0].get("status") != payload.get("status"):
            raise RecordError("cleanup_transition_obligation_mismatch", event["event_id"])
        binding = ("cleanup", payload.get("entity_id"), payload.get("status"))
    elif event_type == "memory.disposition_recorded":
        binding = ("memory", engagement_id, payload.get("memory_disposition"))
    elif event_type == "engagement.blocked":
        if payload.get("entity_id") != engagement_id or payload.get("status") != "blocked":
            raise RecordError("event_payload_state_mismatch", event["event_id"])
        for dimension in ("engagement", "coverage"):
            change = by_dimension[dimension]
            if change["entity_id"] != engagement_id or change["current"] != "blocked":
                raise RecordError("event_state_entity_mismatch", event["event_id"])
    elif event_type == "engagement.reopened":
        if payload.get("entity_id") != engagement_id or payload.get("status") != "active":
            raise RecordError("event_payload_state_mismatch", event["event_id"])
        for dimension in ("engagement", "coverage"):
            change = by_dimension[dimension]
            if change["entity_id"] != engagement_id or change["current"] != "active":
                raise RecordError("event_state_entity_mismatch", event["event_id"])
    elif event_type == "engagement.closed":
        if payload.get("entity_id") != engagement_id or payload.get("status") != "closed":
            raise RecordError("event_payload_state_mismatch", event["event_id"])
        binding = ("engagement", engagement_id, "closed")

    if binding:
        dimension, entity_id, target = binding
        change = by_dimension.get(dimension)
        if change is None or not isinstance(entity_id, str) or change["entity_id"] != entity_id or change["current"] != target:
            raise RecordError("event_state_entity_mismatch", f"{event_type} payload and state change disagree")
        if payload.get("status") is not None and payload["status"] != target:
            raise RecordError("event_payload_state_mismatch", f"{event_type}:{payload['status']} != {target}")


def validate_transition(states: dict[str, dict[str, str]], change: dict[str, Any]) -> None:
    dimension = change["dimension"]
    entity_id = change["entity_id"]
    current = states.setdefault(dimension, {}).get(entity_id)
    if change["previous"] != current:
        raise RecordError("stale_transition_precondition", f"{dimension}:{entity_id} is {current!r}, not {change['previous']!r}")
    target = change["current"]
    if target not in STATE_VALUES[dimension]:
        raise RecordError("unknown_transition_state", f"{dimension}:{target}")
    if target not in TRANSITIONS[dimension].get(current, set()) and not (dimension == "claim" and target == current):
        raise RecordError("invalid_state_transition", f"{dimension}:{current!r}->{target!r}")
    states[dimension][entity_id] = target


def _index_entry(index: dict[str, list[dict[str, Any]]], entity_id: str, kind: str, engagement_id: str, revision: int | None = None) -> dict[str, Any] | None:
    return next((entry for entry in index.get(entity_id, []) if entry["type"] == kind and entry.get("engagement_id") == engagement_id and (revision is None or entry.get("revision") == revision)), None)


def validate_temporal_search_reference(event: dict[str, Any], seen_events: dict[str, dict[str, Any]], index: dict[str, list[dict[str, Any]]], engagement: Path) -> None:
    payload = event["payload"]
    event_type = event["event_type"]
    if event_type == "routing.assessed":
        source = seen_events.get(payload["source_observation_ref"])
        if source is None or source["event_type"] != "observation.recorded":
            raise RecordError("routing_source_not_prior_observation", event["event_id"])
    elif event_type == "candidate.proposed":
        source = seen_events.get(payload["source_observation_ref"])
        if source is None or source["event_type"] != "observation.recorded":
            raise RecordError("candidate_source_not_prior_observation", event["event_id"])
        routing_ref = payload["routing_review_ref"]
        routing_event = seen_events.get(routing_ref)
        if routing_event is not None:
            if routing_event["event_type"] != "routing.assessed":
                raise RecordError("candidate_routing_not_prior_assessment", event["event_id"])
        else:
            entry = _index_entry(index, routing_ref, "review", event["engagement_id"])
            if entry is None:
                raise RecordError("candidate_routing_not_prior_assessment", event["event_id"])
            review = load_json(engagement / entry["path"])
            if review.get("review_type") != "signal" or datetime.fromisoformat(review["recorded_at"].replace("Z", "+00:00")) > datetime.fromisoformat(event["recorded_at"].replace("Z", "+00:00")):
                raise RecordError("candidate_routing_review_not_prior_signal", event["event_id"])


def validate_reference_precedence(event: dict[str, Any], index: dict[str, list[dict[str, Any]]], committed_entity_ids: set[str]) -> None:
    payload = event["payload"]
    refs = set(event.get("evidence_refs", [])) | set(event.get("review_refs", [])) | set(event.get("finding_refs", [])) | set(event.get("artifact_refs", []))
    for key in ("environment_ref", "routing_review_ref", "origin_ref", "review_ref", "adjudication_review_ref", "disposition_ref", "authority_request_ref"):
        if payload.get(key):
            refs.add(payload[key])
    for key in ("experiment_refs", "control_refs", "supporting_evidence_refs", "conflicting_evidence_refs"):
        refs.update(payload.get(key, []))
    event_time = datetime.fromisoformat(event["recorded_at"].replace("Z", "+00:00"))
    for reference in refs:
        entries = [entry for entry in index.get(reference, []) if entry.get("engagement_id") == event["engagement_id"]]
        if any(entry["type"] in {"review", "finding", "environment", "memory-disposition"} for entry in entries) and reference not in committed_entity_ids:
            raise RecordError("record_reference_precedes_commit", f"{event['event_id']}:{reference}")
        temporal_entries = [entry for entry in entries if entry["type"] in {"attempt", "artifact", "review", "finding", "memory-disposition"} and entry.get("recorded_at")]
        if temporal_entries and all(datetime.fromisoformat(entry["recorded_at"].replace("Z", "+00:00")) > event_time for entry in temporal_entries):
            raise RecordError("record_reference_from_future", f"{event['event_id']}:{reference}")


def validate_cross_ledger_causality(events: list[dict[str, Any]], attempts: list[dict[str, Any]], artifacts: list[dict[str, Any]]) -> None:
    event_times = {event["event_id"]: datetime.fromisoformat(event["recorded_at"].replace("Z", "+00:00")) for event in events}
    hypothesis_times = {event["payload"]["hypothesis_id"]: event_times[event["event_id"]] for event in events if event["event_type"] == "hypothesis.created"}
    artifact_times = {artifact["artifact_id"]: datetime.fromisoformat(artifact["created_at"].replace("Z", "+00:00")) for artifact in artifacts}
    environment_commit_times = {event["payload"]["record_id"]: event_times[event["event_id"]] for event in events if event["event_type"] == "record.committed" and event["payload"]["record_type"] == "environment-preflight"}
    scope_timeline = [(event_times[event["event_id"]], event["payload"]["scope_hash"]) for event in events if event["event_type"] == "scope.attested"]
    environment_timeline: list[tuple[datetime, str | None]] = []
    for event in events:
        if event["event_type"] == "scope.attested":
            environment_timeline.append((event_times[event["event_id"]], None))
        elif event["event_type"] in {"environment.preflight_recorded", "environment.review_recorded"}:
            environment_timeline.append((event_times[event["event_id"]], event["payload"]["environment_ref"] if event["payload"].get("status") == "ready" else None))
    event_by_id = {event["event_id"]: event for event in events}
    for artifact in artifacts:
        artifact_time = datetime.fromisoformat(artifact["created_at"].replace("Z", "+00:00"))
        active_environment = next((environment_ref for timestamp, environment_ref in reversed(environment_timeline) if timestamp <= artifact_time), None)
        if artifact["environment_ref"] != active_environment:
            raise RecordError("artifact_environment_not_active", artifact["artifact_id"])
        classification_ref = artifact.get("precreation_classification_event_ref")
        if classification_ref is not None:
            classified = event_by_id.get(classification_ref)
            if classified is None or classified["event_type"] != "artifact.classified" or classified["payload"].get("artifact_id") != artifact["artifact_id"] or classified["payload"].get("classification_digest") != artifact.get("precreation_classification_digest") or classified["payload"].get("source_digest") != artifact.get("classified_source_digest") or classified["payload"].get("source_size") != artifact.get("classified_source_size") or classified["payload"].get("advisory_zone") != artifact["advisory_zone"] or event_times[classification_ref] > artifact_time:
                raise RecordError("artifact_classification_event_invalid", artifact["artifact_id"])
        if artifact["advisory_zone"] == "unknown":
            raise RecordError("artifact_zone_unknown", artifact["artifact_id"])
        if artifact["advisory_zone"] == "review_required":
            confirmation = event_by_id.get(artifact.get("escalation_confirmation_event_ref")); cleanup_event = event_by_id.get(artifact.get("cleanup_obligation_ref"))
            if confirmation is None or confirmation["event_type"] != "escalation.confirmed" or cleanup_event is None or cleanup_event["event_type"] != "cleanup.updated":
                raise RecordError("zone2_confirmation_invalid", artifact["artifact_id"])
            expires_at = datetime.fromisoformat(confirmation["payload"]["expires_at"].replace("Z", "+00:00")); confirmation_time = event_times[confirmation["event_id"]]
            confirmation_payload = confirmation["payload"]; obligation_id = confirmation_payload.get("cleanup_obligation_id")
            cleanup_status = None
            for candidate in events:
                if event_times[candidate["event_id"]] > artifact_time or candidate["event_type"] != "cleanup.updated": continue
                for item in candidate["payload"]["cleanup_obligations"]:
                    if item["obligation_id"] == obligation_id: cleanup_status = item["status"]
            bounded = confirmation_payload.get("confirmation", {})
            if confirmation_payload.get("confirmation_scope") != "zone2_artifact_creation" or confirmation_payload.get("entity_id") != artifact["artifact_id"] or bounded.get("bounded_action") != artifact["artifact_id"] or confirmation_payload.get("environment_ref") != artifact["environment_ref"] or confirmation_payload.get("cleanup_obligation_ref") != cleanup_event["event_id"] or obligation_id != artifact.get("cleanup_obligation_id") or cleanup_status != "open" or not (confirmation_time <= artifact_time <= expires_at):
                raise RecordError("zone2_confirmation_invalid", artifact["artifact_id"])
    seen_attempts: set[str] = set()
    for attempt in attempts:
        attempt_time = datetime.fromisoformat(attempt["recorded_at"].replace("Z", "+00:00"))
        active_scope = next((scope_hash for timestamp, scope_hash in reversed(scope_timeline) if timestamp <= attempt_time), None)
        if active_scope is None or attempt["scope_hash"] != active_scope:
            raise RecordError("attempt_scope_not_active", attempt["attempt_id"])
        hypothesis_time = hypothesis_times.get(attempt["hypothesis_ref"])
        if hypothesis_time is None or hypothesis_time > attempt_time:
            raise RecordError("attempt_precedes_hypothesis", attempt["attempt_id"])
        experiment_time = event_times.get(attempt["experiment_ref"])
        if experiment_time is not None and experiment_time > attempt_time:
            raise RecordError("attempt_precedes_experiment", attempt["attempt_id"])
        for artifact_ref in attempt["evidence_refs"]:
            if artifact_ref not in artifact_times or artifact_times[artifact_ref] > attempt_time:
                raise RecordError("attempt_precedes_evidence", f"{attempt['attempt_id']}:{artifact_ref}")
        environment_time = environment_commit_times.get(attempt["environment_ref"])
        if environment_time is None or environment_time > attempt_time:
            raise RecordError("attempt_precedes_environment_commit", attempt["attempt_id"])
        active_environment = next((environment_ref for timestamp, environment_ref in reversed(environment_timeline) if timestamp <= attempt_time), None)
        if attempt["environment_ref"] != active_environment:
            raise RecordError("attempt_environment_not_active", attempt["attempt_id"])
        controls = set(attempt.get("control_of", []))
        if not controls.issubset(seen_attempts):
            raise RecordError("attempt_control_precedes_primary", attempt["attempt_id"])
        if attempt["kind"] in {"negative_control", "positive_control", "replay"} and not controls:
            raise RecordError("attempt_control_link_missing", attempt["attempt_id"])
        if attempt["kind"] in {"primary", "source_trace", "environment_check"} and controls:
            raise RecordError("primary_attempt_has_control_link", attempt["attempt_id"])
        seen_attempts.add(attempt["attempt_id"])


def _iter_internal_refs(value: Any, key: str = "") -> Iterator[str]:
    if isinstance(value, dict):
        for child_key, child in value.items():
            if child_key.endswith("_ref") and isinstance(child, str):
                yield child
            elif child_key.endswith("_refs") and isinstance(child, list):
                yield from (item for item in child if isinstance(item, str))
            else:
                yield from _iter_internal_refs(child, child_key)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_internal_refs(child, key)


def _indexed_record(engagement: Path, entry: dict[str, Any], entity_id: str) -> dict[str, Any]:
    path = engagement / entry["path"]
    if path.suffix != ".jsonl":
        return load_json(path)
    for line in path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        identity_values = {record.get(key) for key in ("event_id", "attempt_id", "artifact_id")}
        payload = record.get("payload", {})
        identity_values.update({payload.get("candidate_id"), payload.get("hypothesis_id")})
        if entity_id in identity_values:
            return record
    raise RecordError("indexed_record_missing", entity_id)


def compute_review_input_hash(engagement: Path, review: dict[str, Any], index: dict[str, list[dict[str, Any]]]) -> str:
    review_time = datetime.fromisoformat(review["recorded_at"].replace("Z", "+00:00"))
    committed_inputs: list[dict[str, str]] = []
    for reference in sorted(review["input_refs"]):
        candidates = [entry for entry in index.get(reference, []) if entry.get("engagement_id") == review["engagement_id"] and (not entry.get("recorded_at") or datetime.fromisoformat(entry["recorded_at"].replace("Z", "+00:00")) <= review_time)]
        if review.get("finding_revision") is not None and reference == review.get("entity_ref") and any(entry["type"] == "finding" for entry in candidates):
            candidates = [entry for entry in candidates if entry["type"] != "finding" or entry.get("revision") == review["finding_revision"]]
        if not candidates:
            raise RecordError("review_input_unresolved", f"{review['review_id']}:{reference}:{index.get(reference, [])}")
        entry = max(candidates, key=lambda item: (item.get("revision") or 0, item.get("recorded_at") or ""))
        record = _indexed_record(engagement, entry, reference)
        digest = record.get("record_hash") or sha256_file(engagement / entry["path"])
        committed_inputs.append({"ref": reference, "digest": digest})
    return sha256_bytes(canonical_json_bytes(committed_inputs))


def validate_committed_record_precedence(engagement: Path, event: dict[str, Any], index: dict[str, list[dict[str, Any]]], committed_entity_ids: set[str]) -> None:
    payload = event["payload"]
    record = load_json(engagement / payload["record_path"])
    schema_name = resolve_schema_name(record)
    reference_errors = validate_record_references(record, schema_name, index)
    if reference_errors:
        raise RecordError("committed_record_reference_invalid", payload["record_id"], reference_errors)
    if schema_name == "review":
        if record["input_hash"] != compute_review_input_hash(engagement, record, index):
            raise RecordError("review_input_hash_mismatch", payload["record_id"])
        required_inputs = {item["attempt_ref"] for item in record.get("control_applicability", [])} | {item["attempt_ref"] for item in record.get("replay_freshness", [])}
        if record.get("proof_profile_ref"):
            required_inputs.add(record["proof_profile_ref"])
        if not required_inputs.issubset(set(record["input_refs"])):
            raise RecordError("review_material_not_in_input_set", payload["record_id"])
    event_time = datetime.fromisoformat(event["recorded_at"].replace("Z", "+00:00"))
    record_time_text = record.get("recorded_at") or record.get("generated_at") or record.get("created_at")
    record_time = datetime.fromisoformat(record_time_text.replace("Z", "+00:00")) if record_time_text else event_time
    if record_time > event_time:
        raise RecordError("record_commit_precedes_record_time", payload["record_id"])
    internal_refs = set(_iter_internal_refs(record))
    if schema_name == "review" and record.get("review_type") == "claim_adjudication" and record.get("finding_revision") is None and record.get("entity_ref") == record.get("proposed_finding_id"):
        internal_refs.discard(record["entity_ref"])
    if schema_name == "report-manifest":
        internal_refs.add(record["finding_id"])
    elif schema_name == "migration-manifest":
        internal_refs.update(entry["imported_finding_id"] for entry in record["entries"])
    for reference in internal_refs:
        entries = [entry for entry in index.get(reference, []) if entry.get("engagement_id") == event["engagement_id"]]
        if any(entry["type"] in {"review", "finding", "environment", "memory-disposition"} for entry in entries) and reference not in committed_entity_ids:
            raise RecordError("committed_record_reference_precedes_commit", f"{payload['record_id']}:{reference}")
        temporal_entries = [entry for entry in entries if entry.get("recorded_at")]
        if temporal_entries and all(datetime.fromisoformat(entry["recorded_at"].replace("Z", "+00:00")) > record_time for entry in temporal_entries):
            raise RecordError("committed_record_reference_from_future", f"{payload['record_id']}:{reference}")


def _initial_snapshot(engagement_id: str, scope_hash: str) -> dict[str, Any]:
    return {
        "schema_version": 1, "engagement_id": engagement_id, "scope_hash": scope_hash,
        "active_environment_ref": None, "environment_preflights": {}, "last_event_id": None, "event_count": 0,
        "ledger_hash": "sha256:" + "0" * 64, "attempt_count": 0, "artifact_count": 0,
        "active_blockers": [], "authority_requests": {}, "scope_drafts": [], "candidates": {}, "control_candidates": [], "operator_priors": [], "hypotheses": {}, "findings": {},
        "outstanding_reviews": [], "proof_reviews": {}, "coverage": "active", "reports": {}, "report_refs": [], "submission_refs": [],
        "cleanup": {"open_count": 0, "obligations": [], "recorded": False}, "memory_disposition": None, "source_hashes": {}, "integrity_errors": [],
    }


def reduce_engagement(engagement: Path, *, allowed_record_orphans: set[str] | None = None, allowed_artifact_orphans: set[str] | None = None, allow_scope_drift: bool = False) -> dict[str, Any]:
    engagement = engagement.absolute()
    events = read_ledger(engagement, "event")
    if not events or events[0]["event_type"] != "scope.attested":
        raise RecordError("scope_attestation_missing", "first event must be scope.attested")
    scope_hash = events[0]["payload"]["scope_hash"]
    attempts = read_ledger(engagement, "attempt")
    artifacts = read_ledger(engagement, "artifact")
    engagement_id = events[0]["engagement_id"]
    index = build_reference_index(engagement)
    ledgers = (("attempt", "attempt-v2", attempts), ("artifact", "artifact", artifacts), ("event", "engagement-event", events))
    for kind, _schema, records in ledgers:
        for record in records:
            if record.get("engagement_id") != engagement_id:
                raise RecordError("cross_engagement_ledger_record", f"{kind}:{record.get(kind + '_id')}")
    for kind, schema, records in ledgers:
        for record in records:
            reference_errors = validate_record_references(record, schema, index)
            if reference_errors:
                raise RecordError("record_reference_invalid", f"stored {kind} references do not resolve", reference_errors)
    validate_cross_ledger_causality(events, attempts, artifacts)
    verify_file_authority(engagement, events, artifacts, allowed_record_orphans=allowed_record_orphans, allowed_artifact_orphans=allowed_artifact_orphans)
    state = _initial_snapshot(engagement_id, scope_hash)
    states: dict[str, dict[str, str]] = {dimension: {} for dimension in STATE_VALUES}
    seen_events: dict[str, dict[str, Any]] = {}
    committed_entity_ids: set[str] = set()
    committed_records: dict[str, dict[str, Any]] = {}
    reviewer_run_ids: set[str] = set()
    review_run_subjects: dict[str, tuple[str | None, int | None, str, str]] = {}
    latest_regrades: dict[tuple[str, int], dict[str, Any]] = {}
    active_scope_operator: str | None = None
    latest_preflight_ref: str | None = None
    consumed_authority_actions: set[str] = set()
    def consume_exact_authority(event: dict[str, Any], request: dict[str, Any] | None, action: dict[str, Any]) -> bool:
        reference = event["payload"].get("authority_request_ref")
        if request is None or reference in consumed_authority_actions or request["action_digest"] != sha256_bytes(canonical_json_bytes(action)): return False
        consumed_authority_actions.add(reference); return True
    for event in events:
        if event["engagement_id"] != state["engagement_id"]:
            raise RecordError("cross_engagement_event", event["event_id"])
        if event["event_type"] == "scope.attested":
            validate_scope_event_snapshot(engagement, event)
            active_scope_operator = event["payload"]["operator_id"]
        validate_event_semantics(event)
        validate_temporal_search_reference(event, seen_events, index, engagement)
        payload = event["payload"]
        request = state["authority_requests"].get(payload.get("authority_request_ref")) if payload.get("authority_request_ref") else None
        expected_authority_action = {"environment.review_recorded": "review-preflight", "report.generated": "generate-report", "operator.review_recorded": "accept-report", "submission.recorded": "record-submission", "memory.disposition_recorded": "record-memory", "engagement.closed": "close", "finding.revised": "revise-finding", "scope.attested": "reattest-scope", "cleanup.updated": "record-cleanup", "operator_prior.recorded": "record-operator-prior", "engagement.reopened": "reopen", "migration.apply_authorized": "apply-migration"}.get(event["event_type"])
        if event["event_type"] == "observation.recorded" and payload.get("entity_type") == "ledger_tail_repair" and payload.get("authority_request_ref"): expected_authority_action = "repair-ledger-tail"
        event_time = datetime.fromisoformat(event["recorded_at"].replace("Z", "+00:00"))
        broker_authorized = bool(expected_authority_action and request and request["action_kind"] == expected_authority_action and request["status"] == "approved" and request["scope_hash"] == state["scope_hash"] and request["environment_ref"] == state["active_environment_ref"] and request["resolved_at"] is not None and event_time >= datetime.fromisoformat(request["resolved_at"].replace("Z", "+00:00")) and (request["expires_at"] is None or event_time <= datetime.fromisoformat(request["expires_at"].replace("Z", "+00:00"))) and event["actor"]["role"] == "broker" and event.get("provenance", {}).get("session_id") and payload.get("operator_id") == active_scope_operator)
        validate_reference_precedence(event, index, committed_entity_ids)
        if event["event_type"] == "record.committed":
            validate_committed_record_precedence(engagement, event, index, committed_entity_ids)
            if payload["record_type"] == "migration-manifest":
                migration_manifest=load_json(engagement/payload["record_path"]); authority_fields=("authority_request_ref","authority_action_digest","authority_control_engagement_id","source_scope_hash","destination_scope_hash")
                present=[field in migration_manifest for field in authority_fields]
                if any(present) and (not all(present) or migration_manifest.get("destination_scope_hash")!=state["scope_hash"] or migration_manifest.get("scope_operator_id")!=active_scope_operator or migration_manifest.get("producer")!=event.get("actor") or migration_manifest.get("producer_session_id")!=event.get("provenance",{}).get("session_id") or payload.get("authority_request_ref")!=migration_manifest.get("authority_request_ref")): raise RecordError("migration_manifest_authority_binding_invalid", migration_manifest.get("migration_id","unknown"))
            if payload["record_type"] == "review":
                review = load_json(engagement / payload["record_path"])
                run_id = review["independence"]["reviewer_run_id"]
                origin_id = review["independence"]["originating_run_id"]
                origin_entries = [entry for entry in index.get(origin_id, []) if entry.get("engagement_id") == engagement_id and entry["type"] in {"event", "attempt"}]; origin_record = seen_events.get(origin_id) or next((item for item in attempts if item["attempt_id"] == origin_id), None); origin_actor = origin_record.get("actor", {}) if origin_record else {}; origin_provenance = origin_record.get("provenance", {}) if origin_record else {}; independence = review["independence"]
                prior_run_ids = set(review.get("prior_review_run_ids", []))
                relevant_revisions = {review.get("finding_revision")}
                if isinstance(review.get("finding_revision"), int) and review["finding_revision"] > 1:
                    relevant_revisions.add(review["finding_revision"] - 1)
                permitted_prior_types = {"claim_adjudication", "regrade"} if review["review_type"] == "regrade" else ({"regrade", "pocinator"} if review["review_type"] == "pocinator" else set())
                prior_subjects_match = all(review_run_subjects.get(prior, (None, None, "", ""))[0] == review.get("proposed_finding_id") and review_run_subjects.get(prior, (None, None, "", ""))[1] in relevant_revisions and review_run_subjects.get(prior, (None, None, "", ""))[2] in permitted_prior_types and review_run_subjects.get(prior, (None, None, "", ""))[3] == review.get("entity_ref") for prior in prior_run_ids) if prior_run_ids else True
                independence_required = review["review_type"] in {"claim_adjudication", "regrade", "pocinator", "coverage"}; strict_independence = independence_required and event["actor"]["role"] == "broker"; reviewer_session = independence.get("reviewer_session_id"); reviewer_model = independence.get("reviewer_model"); origin_session = origin_provenance.get("session_id"); origin_model = origin_provenance.get("model"); origin_time = datetime.fromisoformat(origin_record["recorded_at"].replace("Z", "+00:00")) if origin_record else None; review_time = datetime.fromisoformat(review["recorded_at"].replace("Z", "+00:00")); origin_precedes = bool(origin_time and (origin_time < review_time <= event_time if strict_independence else origin_time <= event_time)); same_principal = strict_independence and (independence.get("reviewer_id") == origin_actor.get("id") or reviewer_session == origin_session); same_model = strict_independence and reviewer_model == origin_model
                if run_id in reviewer_run_ids or run_id in prior_run_ids or not prior_run_ids.issubset(reviewer_run_ids) or not prior_subjects_match or (review["review_type"] in {"regrade", "pocinator"} and not prior_run_ids) or not origin_entries or origin_record is None or not origin_precedes or (strict_independence and (not reviewer_session or not origin_session or not reviewer_model or not origin_model)) or same_principal or same_model or independence.get("prior_verdict_visible") is not False:
                    raise RecordError("review_freshness_not_bound", review["review_id"])
                reviewer_run_ids.add(run_id)
                review_run_subjects[run_id] = (review.get("proposed_finding_id"), review.get("finding_revision"), review["review_type"], review["entity_ref"])
        if event["event_type"] == "scope.attested" and event["sequence"] > 1 and payload.get("authority_request_ref"):
            scope_action = {"action_kind": "reattest-scope", "lane_id": request.get("lane_id") if request else None, "executor_id": payload.get("executor_id"), "session_id": event.get("provenance", {}).get("session_id"), "draft_digest": payload.get("scope_hash"), "operator_id": payload.get("operator_id"), "recorded_at": event["recorded_at"]}
            if request is None or request["status"] != "approved" or request["scope_hash"] != state["scope_hash"] or request["environment_ref"] != state["active_environment_ref"] or not consume_exact_authority(event, request, scope_action): raise RecordError("scope_reattestation_authority_invalid", event["event_id"])
        if event["event_type"] == "observation.recorded" and payload.get("entity_type") == "ledger_tail_repair" and payload.get("authority_request_ref"):
            repair_action = {"action_kind": "repair-ledger-tail", "lane_id": request.get("lane_id") if request else None, "executor_id": event["actor"]["id"], "session_id": event.get("provenance", {}).get("session_id"), "ledger": str(payload.get("entity_id", "")).removesuffix("-ledger"), "operator_id": payload.get("operator_id"), "reason": payload.get("reason"), "recorded_at": event["recorded_at"]}
            if not broker_authorized or not consume_exact_authority(event, request, repair_action): raise RecordError("ledger_repair_authority_invalid", event["event_id"])
        if event["event_type"] == "migration.apply_authorized":
            action_path = engagement / str(request.get("action_path", "")) if request else engagement/"missing"; stored_action = load_json(action_path) if action_path.is_file() and not action_path.is_symlink() else {}
            migration_exact = bool(request and payload.get("action_digest") == request["action_digest"] and stored_action.get("proposal_digest") == payload.get("proposal_digest") and sha256_bytes(str(stored_action.get("destination", "")).encode()) == payload.get("destination_digest") and consume_exact_authority(event, request, stored_action))
            if not broker_authorized or not migration_exact or payload.get("status") != "authorized": raise RecordError("migration_apply_authority_invalid", event["event_id"])
        if event["event_type"] == "cleanup.updated":
            cleanup_action = {"action_kind": "record-cleanup", "lane_id": request.get("lane_id") if request else None, "executor_id": event["actor"]["id"], "session_id": event.get("provenance", {}).get("session_id"), "operator_id": payload.get("operator_id"), "recorded_at": event["recorded_at"], "reason": event["rationale"], "entity_id": payload.get("entity_id"), "status": payload.get("status"), "cleanup_obligations": payload.get("cleanup_obligations")}
            cleanup_exact = event["actor"]["role"] == "operator" or consume_exact_authority(event, request, cleanup_action)
            if not cleanup_exact or (event["actor"] != {"role": "operator", "id": active_scope_operator} and not broker_authorized) or payload.get("operator_id") != active_scope_operator or payload.get("scope_hash") != state["scope_hash"] or payload.get("updated_at") != event["recorded_at"]:
                raise RecordError("cleanup_authority_invalid", event["event_id"])
        if event["event_type"] == "memory.disposition_recorded":
            entry = _index_entry(index, payload.get("disposition_ref"), "memory-disposition", engagement_id)
            if entry is None: raise RecordError("memory_disposition_record_missing", event["event_id"])
            disposition = load_json(engagement / entry["path"])
            memory_action = {"action_kind": "record-memory", "lane_id": request.get("lane_id") if request else None, "executor_id": event["actor"]["id"], "session_id": event.get("provenance", {}).get("session_id"), "file_digest": payload.get("disposition_digest"), "operator_id": payload.get("operator_id")}
            memory_authority_exact = event["actor"]["role"] == "operator" or consume_exact_authority(event, request, memory_action)
            if not memory_authority_exact or state["memory_disposition"] is not None or (event["actor"] != {"role": "operator", "id": active_scope_operator} and not broker_authorized) or disposition["disposition"] != payload.get("memory_disposition") or disposition["scope_hash"] != state["scope_hash"] or disposition["human_review"]["reviewer"] != {"role": "operator", "id": active_scope_operator} or sha256_file(engagement / entry["path"]) != payload.get("disposition_digest"):
                raise RecordError("memory_disposition_binding_invalid", event["event_id"])
        if event["event_type"] == "engagement.closed":
            memory = state["memory_disposition"]
            reports_current = all(any(report["finding_id"] == finding_id and report["finding_revision"] == finding["revision"] and report["status"] in {"accepted", "submitted"} for report in state["reports"].values()) for finding_id, finding in state["findings"].items())
            pending_reviews = bool(state["outstanding_reviews"])
            cleanup_terminal = state["cleanup"]["recorded"] and all(item["status"] in {"completed", "not_applicable", "blocked"} for item in state["cleanup"]["obligations"])
            memory_bound = memory is not None and payload.get("disposition_ref") == memory["disposition_ref"] and payload.get("disposition_digest") == memory["disposition_digest"]
            close_action = {"action_kind": "close", "lane_id": request.get("lane_id") if request else None, "executor_id": event["actor"]["id"], "session_id": event.get("provenance", {}).get("session_id"), "operator_id": payload.get("operator_id"), "reason": event["rationale"], "recorded_at": event["recorded_at"]}
            close_authority_exact = event["actor"]["role"] == "operator" or consume_exact_authority(event, request, close_action)
            if not close_authority_exact or (event["actor"] != {"role": "operator", "id": active_scope_operator} and not broker_authorized) or payload.get("operator_id") != active_scope_operator or payload.get("scope_hash") != state["scope_hash"] or not memory_bound or not cleanup_terminal or states["coverage"].get(engagement_id, "active") not in {"coverage_dry", "blocked"} or pending_reviews or not reports_current:
                raise RecordError("engagement_closure_gate_failed", event["event_id"])
        if event["event_type"] == "escalation.confirmed":
            require_scope_zone2_authorized(engagement, state["scope_hash"]); confirmation_time = datetime.fromisoformat(event["recorded_at"].replace("Z", "+00:00")); expires_at = datetime.fromisoformat(payload["expires_at"].replace("Z", "+00:00")); cleanup_event = seen_events.get(payload["cleanup_obligation_ref"]); bounded = payload.get("confirmation", {})
            cleanup_open = cleanup_event is not None and cleanup_event["event_type"] == "cleanup.updated" and any(item["obligation_id"] == payload.get("cleanup_obligation_id") and item["status"] == "open" for item in cleanup_event["payload"]["cleanup_obligations"]) and any(item["obligation_id"] == payload.get("cleanup_obligation_id") and item["status"] == "open" for item in state["cleanup"]["obligations"])
            bounded_valid = bounded.get("category") == "zone2_artifact_creation" and bounded.get("bounded_action") == payload.get("entity_id") and bounded.get("scope_hash") == state["scope_hash"] and bounded.get("operator_id") == active_scope_operator and bounded.get("confirmed_at") == event["recorded_at"] and bounded.get("expires_at") == payload.get("expires_at")
            if event["actor"] != {"role": "operator", "id": active_scope_operator} or payload.get("status") != "confirmed" or payload.get("confirmation_scope") != "zone2_artifact_creation" or payload.get("environment_ref") != state["active_environment_ref"] or not cleanup_open or not bounded_valid or expires_at <= confirmation_time or (expires_at - confirmation_time).total_seconds() > 1800:
                raise RecordError("zone2_confirmation_invalid", event["event_id"])
        if event["event_type"] == "operator_prior.recorded":
            prior_action = {"action_kind": "record-operator-prior", "lane_id": request.get("lane_id") if request else None, "executor_id": event["actor"]["id"], "session_id": event.get("provenance", {}).get("session_id"), "operator_id": payload.get("operator_id"), "recorded_at": event["recorded_at"], "prior_id": payload.get("prior_id"), "prior_statement": payload.get("prior_statement"), "strength": payload.get("strength"), "reason": payload.get("reason")}
            prior_exact = event["actor"]["role"] == "operator" or consume_exact_authority(event, request, prior_action)
            if not prior_exact or (event["actor"] != {"role": "operator", "id": active_scope_operator} and not broker_authorized) or payload.get("operator_id", active_scope_operator) != active_scope_operator: raise RecordError("operator_prior_not_scope_authorized", event["event_id"])
        if event["event_type"] == "engagement.reopened":
            reopen_action = {"action_kind": "reopen", "lane_id": request.get("lane_id") if request else None, "executor_id": event["actor"]["id"], "session_id": event.get("provenance", {}).get("session_id"), "operator_id": payload.get("operator_id"), "recorded_at": event["recorded_at"], "reason": event["rationale"]}
            reopen_exact = event["actor"]["role"] == "operator" or consume_exact_authority(event, request, reopen_action)
            if not reopen_exact or (event["actor"] != {"role": "operator", "id": active_scope_operator} and not broker_authorized) or payload.get("operator_id", active_scope_operator) != active_scope_operator: raise RecordError("engagement_reopen_authority_invalid", event["event_id"])
        if event["event_type"] in {"authority.requested", "authority.resolved", "scope.amendment_proposed", "artifact.classified"} and not event.get("provenance", {}).get("session_id"):
            raise RecordError("session_provenance_required", event["event_id"])
        if event["event_type"] == "scope.amendment_proposed":
            expected_draft = f"scope-drafts/{payload['draft_digest'].removeprefix('sha256:')}.md"; draft_path = engagement / str(payload.get("draft_path", ""))
            if payload.get("draft_path") != expected_draft or payload.get("supersedes_scope_hash") != state["scope_hash"] or not draft_path.is_file() or draft_path.is_symlink() or sha256_bytes(read_governed_file(draft_path)) != payload["draft_digest"]: raise RecordError("scope_draft_binding_invalid", event["event_id"])
        if event["event_type"] == "authority.resolved" and event["actor"] != {"role": "operator", "id": active_scope_operator}:
            raise RecordError("authority_resolution_operator_invalid", event["event_id"])
        if event["event_type"] == "authority.requested":
            request_id = payload["request_id"]
            if request_id in state["authority_requests"] or payload.get("request_status") != "pending_authority" or payload.get("scope_hash") != state["scope_hash"] or payload.get("environment_ref") not in {None, state["active_environment_ref"]}:
                raise RecordError("authority_request_invalid", event["event_id"])
            if event["actor"]["role"] == "broker":
                expected_action_path = f"authority/requests/{request_id}.action.json"; action_path = engagement / str(payload.get("action_path", ""))
                if payload.get("action_path") != expected_action_path or not action_path.is_file() or action_path.is_symlink() or sha256_bytes(read_governed_file(action_path)) != payload["action_digest"] or detect_secret_classes(read_governed_file(action_path)): raise RecordError("authority_action_record_invalid", event["event_id"])
            if payload.get("expires_at") is not None and datetime.fromisoformat(payload["expires_at"].replace("Z", "+00:00")) <= datetime.fromisoformat(event["recorded_at"].replace("Z", "+00:00")):
                raise RecordError("authority_request_expiry_invalid", event["event_id"])
        if event["event_type"] == "authority.resolved":
            request = state["authority_requests"].get(payload["request_id"])
            if request is None or request["status"] != "pending_authority" or request["request_event_ref"] != payload.get("request_event_ref") or request["action_digest"] != payload.get("action_digest"):
                raise RecordError("authority_resolution_binding_invalid", event["event_id"])
            expired_at_resolution = request["expires_at"] is not None and datetime.fromisoformat(event["recorded_at"].replace("Z", "+00:00")) > datetime.fromisoformat(request["expires_at"].replace("Z", "+00:00"))
            if payload["resolution"] == "approved" and expired_at_resolution:
                raise RecordError("authority_approval_expired", event["event_id"])
        if event["event_type"] == "environment.review_recorded":
            current_environment = state["environment_preflights"].get(payload["environment_ref"]); review_entry = _index_entry(index, payload.get("review_ref"), "review", engagement_id)
            review = load_json(engagement / review_entry["path"]) if review_entry else {}; environment_entry = _index_entry(index, payload["environment_ref"], "environment", engagement_id); environment = load_json(engagement / environment_entry["path"]) if environment_entry else {}
            safety = environment.get("safety", {}); accepted_safe = environment.get("fidelity_complete") is True and safety.get("credentials_present") is False and safety.get("secret_scan_status") == "clean" and safety.get("automated_redaction_status") == "clean" and safety.get("cleanup_open_count") == 0
            expected_status = "ready" if review.get("verdict") == "accepted" else "blocked"
            exact_action = {"action_kind": "review-preflight", "lane_id": request.get("lane_id") if request else None, "executor_id": event["actor"]["id"], "session_id": event.get("provenance", {}).get("session_id"), "preflight_id": payload["environment_ref"], "verdict": review.get("verdict"), "reason": event["rationale"], "operator_id": payload.get("operator_id"), "recorded_at": event["recorded_at"]}
            authority_exact = consume_exact_authority(event, request, exact_action)
            if not broker_authorized or not authority_exact or latest_preflight_ref != payload["environment_ref"] or current_environment is None or current_environment["status"] != "needs_review" or review_entry is None or payload.get("review_ref") not in committed_entity_ids or review.get("review_type") != "operator" or review.get("entity_ref") != payload["environment_ref"] or review.get("independence", {}).get("reviewer_id") != active_scope_operator or payload.get("operator_id") != active_scope_operator or payload.get("status") != expected_status or (expected_status == "ready" and not accepted_safe):
                raise RecordError("environment_operator_review_invalid", event["event_id"])
        if event["event_type"] == "environment.preflight_recorded":
            environment_ref = payload["environment_ref"]
            environment_entry = _index_entry(index, environment_ref, "environment", engagement_id)
            if environment_ref not in committed_entity_ids or environment_entry is None:
                raise RecordError("environment_preflight_not_committed", event["event_id"])
            environment = load_json(engagement / environment_entry["path"])
            common_invalid = environment.get("scope_hash") != state["scope_hash"] or environment.get("status") != payload.get("status") or environment.get("identity_hash") != payload.get("identity_hash") or environment.get("identity_hash") != sha256_bytes(canonical_json_bytes(environment.get("identity")))
            if environment.get("schema_version") == 1:
                actor_invalid = event["actor"]["role"] != "operator" or event["actor"]["id"] != active_scope_operator
            else:
                provenance = environment.get("provenance", {})
                actor_invalid = event["actor"] != provenance.get("actor") or event.get("provenance", {}).get("session_id") != provenance.get("session_id") or event["actor"].get("role") not in {"orchestrator", "hunter", "broker"} or not provenance.get("session_id")
            if common_invalid or actor_invalid:
                raise RecordError("environment_preflight_not_usable", event["event_id"])
            safety = environment.get("safety", {})
            v2_ready_invalid = environment.get("schema_version") == 2 and (safety.get("automated_redaction_status") != "clean" or safety.get("credentials_present") is not False or safety.get("operator_review_ref") is not None)
            if payload["status"] == "ready" and (environment.get("fidelity_complete") is not True or environment.get("collector", {}).get("reproducible") is not True or environment.get("identity", {}).get("runtime_digest") is None or safety.get("advisory_zone") != "clear_local" or safety.get("zone2_authorization_granted") is not False or safety.get("secret_scan_status") != "clean" or safety.get("cleanup_open_count") != 0 or v2_ready_invalid):
                raise RecordError("environment_preflight_not_usable", event["event_id"])
            latest_preflight_ref = environment_ref
        if event["event_type"] in {"candidate.proposed", "candidate.selected", "hypothesis.created"} and (states["coverage"].get(engagement_id) == "coverage_dry" or states["engagement"].get(engagement_id) == "closed"):
            raise RecordError("search_material_after_closed_coverage", event["event_id"])
        if event["event_type"] == "report.generated":
            report_ref = payload["report_ref"]; commitment = committed_records.get(report_ref)
            finding_commitment = committed_records.get(payload["finding_id"]); current_finding = state["findings"].get(payload["finding_id"])
            if (event["actor"] != {"role": "operator", "id": active_scope_operator} and not broker_authorized) or commitment is None or finding_commitment is None or current_finding is None or current_finding["revision"] != payload["finding_revision"] or report_ref not in event["entity_refs"]:
                raise RecordError("report_generation_authority_invalid", event["event_id"])
            manifest = load_json(engagement / commitment["record_path"]); finding = load_json(engagement / finding_commitment["record_path"])
            report_action = {"action_kind": "generate-report", "lane_id": request.get("lane_id") if request else None, "executor_id": event["actor"]["id"], "session_id": event.get("provenance", {}).get("session_id"), "finding_id": payload["finding_id"], "revision": payload["finding_revision"], "included_claim_ids": manifest.get("included_claim_ids"), "omitted_claims": manifest.get("omitted_claims"), "operator_id": payload.get("operator_id"), "recorded_at": event["recorded_at"]}
            if event["actor"]["role"] != "operator" and not consume_exact_authority(event, request, report_action): raise RecordError("report_generation_authority_invalid", event["event_id"])
            report_path = engagement / manifest["report_path"]
            claim_ids = {row["claim_id"] for row in claim_rows(finding)}; included = set(manifest["included_claim_ids"]); omitted = {item["claim_id"] for item in manifest["omitted_claims"]}
            review_entry = _index_entry(index, manifest["adjudication_review_ref"], "review", engagement_id)
            adjudication_review = load_json(engagement / review_entry["path"]) if review_entry else {}
            expected_prior_revision = None if payload["finding_revision"] == 1 else payload["finding_revision"] - 1
            if manifest.get("finding_id") != payload["finding_id"] or manifest.get("finding_revision") != payload["finding_revision"] or manifest.get("finding_digest") != finding_commitment["record_digest"] or manifest.get("report_id") != report_ref or sha256_file(engagement / commitment["record_path"]) != payload["report_manifest_digest"] or not report_path.is_file() or sha256_file(report_path) != manifest["report_digest"] or report_path.read_bytes() != render_internal_report(finding, manifest["included_claim_ids"], manifest["omitted_claims"]).encode("utf-8") or sha256_bytes(render_claim_proof(finding).encode("utf-8")) != manifest["claim_proof_matrix_hash"] or review_entry is None or manifest["adjudication_review_ref"] != finding.get("adjudication", {}).get("review_ref") or adjudication_review.get("review_type") != "claim_adjudication" or adjudication_review.get("proposed_finding_id") != payload["finding_id"] or adjudication_review.get("finding_revision") != expected_prior_revision or sha256_file(engagement / review_entry["path"]) != manifest["adjudication_review_digest"] or included & omitted or included | omitted != claim_ids or not included:
                raise RecordError("report_manifest_binding_mismatch", event["event_id"])
        if event["event_type"] == "operator.review_recorded":
            report = state["reports"].get(payload["report_ref"]); review_entry = _index_entry(index, payload["review_ref"], "review", engagement_id)
            review = load_json(engagement / review_entry["path"]) if review_entry else {}
            accept_action = {"action_kind": "accept-report", "lane_id": request.get("lane_id") if request else None, "executor_id": event["actor"]["id"], "session_id": event.get("provenance", {}).get("session_id"), "report_id": payload["report_ref"], "operator_id": payload.get("operator_id"), "reason": event["rationale"], "recorded_at": event["recorded_at"]}
            accept_exact = event["actor"]["role"] == "operator" or consume_exact_authority(event, request, accept_action)
            if not accept_exact or (event["actor"] != {"role": "operator", "id": active_scope_operator} and not broker_authorized) or report is None or state["findings"].get(report.get("finding_id"), {}).get("revision") != report.get("finding_revision") or report["status"] != "draft" or review_entry is None or payload["review_ref"] not in committed_entity_ids or review.get("review_type") != "operator" or review.get("verdict") != "accepted" or review.get("entity_ref") != payload["report_ref"] or review.get("independence", {}).get("reviewer_id") != active_scope_operator or payload["review_ref"] not in event["review_refs"]:
                raise RecordError("operator_report_review_invalid", event["event_id"])
        if event["event_type"] == "submission.recorded":
            report = state["reports"].get(payload["report_ref"]); submission_path = (engagement / payload["submission_path"]).resolve(); submission_root = (engagement / "submissions").resolve()
            submission_action = {"action_kind": "record-submission", "lane_id": request.get("lane_id") if request else None, "executor_id": event["actor"]["id"], "session_id": event.get("provenance", {}).get("session_id"), "report_id": payload["report_ref"], "file_digest": payload["submission_digest"], "program": payload["program"], "operator_id": payload.get("operator_id"), "recorded_at": event["recorded_at"]}
            submission_exact = event["actor"]["role"] == "operator" or consume_exact_authority(event, request, submission_action)
            if not submission_exact or (event["actor"] != {"role": "operator", "id": active_scope_operator} and not broker_authorized) or report is None or state["findings"].get(report.get("finding_id"), {}).get("revision") != report.get("finding_revision") or report["status"] != "accepted" or not submission_path.is_relative_to(submission_root) or not submission_path.is_file() or submission_path.is_symlink() or sha256_file(submission_path) != payload["submission_digest"] or active_scope_operator not in payload["authorship_note"]:
                raise RecordError("submission_authority_invalid", event["event_id"])
        if event["event_type"] in {"review.regrade_completed", "review.pocinator_completed"}:
            review_ref = payload["review_ref"]
            review_entry = _index_entry(index, review_ref, "review", engagement_id)
            current_finding = state["findings"].get(payload["finding_id"])
            finding_commitment = committed_records.get(payload["finding_id"])
            if review_ref not in committed_entity_ids or review_entry is None or review_ref not in event["review_refs"] or current_finding is None or current_finding["revision"] != payload["finding_revision"] or finding_commitment is None:
                raise RecordError("typed_review_subject_not_current", event["event_id"])
            review = load_json(engagement / review_entry["path"]); finding = load_json(engagement / finding_commitment["record_path"])
            expected_type = "regrade" if event["event_type"] == "review.regrade_completed" else "pocinator"
            if review.get("review_type") != expected_type or review.get("entity_ref") != payload["finding_id"] or review.get("finding_revision") != payload["finding_revision"] or review.get("verdict") != payload["verdict"] or review.get("independence", {}).get("reviewer_id") != payload.get("reviewer_id", event["actor"]["id"]) or review.get("claim_tuple_hash") != payload["claim_tuple_hash"] or payload["claim_tuple_hash"] != claim_tuple_hash(finding):
                raise RecordError("typed_review_binding_mismatch", event["event_id"])
            if expected_type == "regrade":
                latest_regrades[(payload["finding_id"], payload["finding_revision"])] = {"event_id": event["event_id"], "verdict": payload["verdict"]}
            if expected_type == "pocinator":
                prior_regrade = latest_regrades.get((payload["finding_id"], payload["finding_revision"]))
                escalation_ready = prior_regrade and prior_regrade["verdict"] == "escalation_found" and any(item["review_ref"] == prior_regrade["event_id"] and item["status"] == "evidence_collected" for item in state["outstanding_reviews"])
                if prior_regrade is None or (prior_regrade["verdict"] not in {"confirmed", "confirmed_with_correction"} and not escalation_ready):
                    raise RecordError("pocinator_without_acceptable_regrade", event["event_id"])
                if review.get("high_value") != payload["high_value"]:
                    raise RecordError("pocinator_value_mismatch", event["event_id"])
                if review["verdict"] == "verified" and (review["module_level_only"] or not review["end_to_end_composition_reviewed"]):
                    raise RecordError("module_proof_not_end_to_end", event["event_id"])
        if event["event_type"] == "claim.adjudicated":
            review_ref = payload["review_ref"]
            review_entry = _index_entry(index, review_ref, "review", engagement_id)
            if review_ref not in committed_entity_ids or review_entry is None or review_ref not in event["review_refs"]:
                raise RecordError("claim_adjudication_review_not_committed", event["event_id"])
            review = load_json(engagement / review_entry["path"])
            expected_prior_revision = state["findings"].get(payload["entity_id"], {}).get("revision")
            if sha256_file(engagement / review_entry["path"]) != payload["review_digest"] or review.get("review_type") != "claim_adjudication" or review.get("verdict") != payload["status"] or review.get("proposed_finding_id") != payload["entity_id"] or review.get("entity_ref") != payload["entity_id"] or review.get("finding_revision") != expected_prior_revision or review.get("independence", {}).get("reviewer_id") != payload.get("reviewer_id", event["actor"]["id"]):
                raise RecordError("claim_adjudication_review_mismatch", event["event_id"])
        if event["event_type"] == "legacy.record_imported" and payload.get("imported_finding_id") is not None:
            finding_id, revision = payload["imported_finding_id"], payload["imported_revision"]
            commitment=committed_records.get(finding_id);finding_entry=_index_entry(index,finding_id,"finding",engagement_id,revision)
            if event["actor"]["role"]!="migration" or revision!=1 or finding_id in state["findings"] or commitment is None or finding_entry is None or commitment["record_revision"]!=revision:
                raise RecordError("legacy_finding_import_invalid",event["event_id"])
            finding=load_json(engagement/finding_entry["path"])
            legacy=finding.get("legacy_import",{})
            if finding.get("claim_state")!="needs_review" or finding.get("revision")!=1 or finding.get("engagement_id")!=engagement_id or legacy.get("source_artifact_ref")!=payload.get("source_artifact_ref") or legacy.get("source_hash")!=payload.get("source_hash") or sha256_file(engagement/finding_entry["path"])!=commitment["record_digest"]:
                raise RecordError("legacy_finding_record_mismatch",event["event_id"])
        if event["event_type"] == "finding.revised":
            finding_id, revision = payload["finding_id"], payload["finding_revision"]
            commitment = committed_records.get(finding_id)
            finding_entry = _index_entry(index, finding_id, "finding", engagement_id, revision)
            adjudication_event = seen_events.get(payload["adjudication_event_ref"])
            prior = state["findings"].get(finding_id)
            expected_revision = 1 if prior is None else prior["revision"] + 1
            expected_supersedes = None if prior is None else prior["revision"]
            finding_action = {"action_kind": "revise-finding", "lane_id": request.get("lane_id") if request else None, "executor_id": event["actor"]["id"], "session_id": event.get("provenance", {}).get("session_id"), "file_digest": payload["finding_digest"], "operator_id": payload.get("operator_id"), "recorded_at": event["recorded_at"]}
            finding_authority_exact = event["actor"]["role"] == "operator" or consume_exact_authority(event, request, finding_action)
            if not finding_authority_exact or (event["actor"] != {"role": "operator", "id": active_scope_operator} and not broker_authorized) or payload.get("operator_id", active_scope_operator) != active_scope_operator:
                raise RecordError("finding_filing_not_scope_operator", event["event_id"])
            regrade_obligations = [item for item in state["outstanding_reviews"] if item["review_type"] in {"regrade_escalation", "regrade"} and item["entity_ref"] == finding_id and item["status"] in {"pending", "routed", "evidence_collected", "correction_required"}]
            resolutions = set(payload.get("resolves_review_refs", []))
            if any(item["review_type"] == "regrade_escalation" and item["status"] != "evidence_collected" for item in regrade_obligations):
                raise RecordError("escalation_evidence_not_collected", event["event_id"])
            if any(item["review_ref"] not in resolutions for item in regrade_obligations):
                raise RecordError("regrade_correction_not_resolved", event["event_id"])
            if revision != expected_revision or payload["supersedes_revision"] != expected_supersedes:
                raise RecordError("finding_revision_not_contiguous", event["event_id"])
            if commitment is None or finding_entry is None or commitment["record_revision"] != revision or commitment["record_digest"] != payload["finding_digest"]:
                raise RecordError("finding_revision_not_committed", event["event_id"])
            finding = load_json(engagement / finding_entry["path"])
            if finding.get("revision") != revision or finding.get("supersedes_revision") != expected_supersedes or finding.get("claim_state") != payload["status"] or finding.get("change_reason") != payload["change_reason"] or finding.get("adjudication", {}).get("review_ref") != payload["adjudication_review_ref"] or finding.get("scope_provenance", {}).get("scope_hash") != state["scope_hash"] or finding.get("scope_provenance", {}).get("environment_ref") != state["active_environment_ref"] or sha256_file(engagement / finding_entry["path"]) != payload["finding_digest"]:
                raise RecordError("finding_revision_record_mismatch", event["event_id"], [{"finding_revision": finding.get("revision"), "event_revision": revision, "finding_supersedes": finding.get("supersedes_revision"), "expected_supersedes": expected_supersedes, "finding_state": finding.get("claim_state"), "event_state": payload.get("status"), "finding_change_reason": finding.get("change_reason"), "event_change_reason": payload.get("change_reason"), "finding_review_ref": finding.get("adjudication", {}).get("review_ref"), "event_review_ref": payload.get("adjudication_review_ref"), "finding_scope_hash": finding.get("scope_provenance", {}).get("scope_hash"), "active_scope_hash": state.get("scope_hash"), "finding_environment_ref": finding.get("scope_provenance", {}).get("environment_ref"), "active_environment_ref": state.get("active_environment_ref"), "file_digest_matches": sha256_file(engagement / finding_entry["path"]) == payload.get("finding_digest")}])
            attempt_by_id = {attempt["attempt_id"]: attempt for attempt in attempts}
            artifact_by_id = {artifact["artifact_id"]: artifact for artifact in artifacts}
            proof = finding["proof"]
            primary_ids = set(proof["primary_attempt_refs"]); negative_ids = set(proof["negative_control_refs"]); positive_ids = set(proof["positive_control_refs"]); replay_ids = set(proof["replay_refs"])
            primary_attempts = [attempt_by_id[reference] for reference in primary_ids]
            claim_evidence_refs = set(finding["claims"]["mechanism"]["evidence_refs"]) | set(finding["claims"]["reachability"]["evidence_refs"]) | {reference for impact in finding["claims"]["impact_claims"] for reference in impact["evidence_refs"]}
            proof_attempt_ids = primary_ids | negative_ids | positive_ids | replay_ids | {reference for reference in set(proof["evidence_refs"]) | claim_evidence_refs if reference in attempt_by_id} | {reference for mapping in proof["claim_proofs"] for reference in mapping["attempt_refs"] + mapping["control_refs"] + mapping["replay_refs"]}
            if not primary_attempts or any(item["kind"] != "primary" or item["assessment"] != "suspected_signal" for item in primary_attempts) or all(item["observation"]["source"] == "model_report" for item in primary_attempts):
                raise RecordError("primary_proof_invalid", event["event_id"])
            if any(attempt_by_id[reference]["scope_hash"] != state["scope_hash"] or attempt_by_id[reference]["environment_ref"] != state["active_environment_ref"] or attempt_by_id[reference]["contamination"]["status"] != "none_observed" for reference in proof_attempt_ids):
                raise RecordError("proof_provenance_or_contamination_invalid", event["event_id"])
            proof_artifact_ids = {reference for reference in set(proof["evidence_refs"]) | claim_evidence_refs if reference in artifact_by_id} | {reference for mapping in proof["claim_proofs"] for reference in mapping["artifact_refs"]}
            if any(artifact_by_id[reference].get("environment_ref") != state["active_environment_ref"] for reference in proof_artifact_ids):
                raise RecordError("proof_artifact_environment_mismatch", event["event_id"])
            applicability = proof["control_applicability"]
            control_expectations = (("negative", negative_ids, "negative_control", {"no_signal", "held"}), ("positive", positive_ids, "positive_control", {"suspected_signal"}), ("replay", replay_ids, "replay", {"suspected_signal"}))
            for policy, references, expected_kind, assessments in control_expectations:
                if applicability[policy] == "required" and not references:
                    raise RecordError("required_proof_stage_missing", f"{event['event_id']}:{policy}")
                for reference in references:
                    item = attempt_by_id[reference]
                    if item["kind"] != expected_kind or item["assessment"] not in assessments or not primary_ids.intersection(item["control_of"]):
                        raise RecordError("proof_stage_linkage_invalid", f"{event['event_id']}:{reference}")
            required_controls = (negative_ids if applicability["negative"] == "required" else set()) | (positive_ids if applicability["positive"] == "required" else set())
            required_replays = replay_ids if applicability["replay"] == "required" else set()
            for mapping in proof["claim_proofs"]:
                mapping_attempts = set(mapping["attempt_refs"]); mapping_controls = set(mapping["control_refs"]); mapping_replays = set(mapping["replay_refs"])
                if not mapping_attempts or not mapping_attempts.issubset(primary_ids) or any(attempt_by_id[reference]["kind"] != "primary" for reference in mapping_attempts) or all(attempt_by_id[reference]["observation"]["source"] == "model_report" for reference in mapping_attempts):
                    raise RecordError("atomic_claim_model_report_only", f"{event['event_id']}:{mapping['claim_id']}")
                if mapping_controls != required_controls or mapping_replays != required_replays:
                    raise RecordError("atomic_claim_proof_stage_missing", f"{event['event_id']}:{mapping['claim_id']}")
                if any(not mapping_attempts.intersection(attempt_by_id[reference]["control_of"]) for reference in mapping_controls | mapping_replays):
                    raise RecordError("atomic_claim_control_linkage_invalid", f"{event['event_id']}:{mapping['claim_id']}")
            if adjudication_event is None or adjudication_event["event_type"] != "claim.adjudicated" or adjudication_event["payload"].get("entity_id") != finding_id or adjudication_event["payload"].get("status") != payload["status"] or adjudication_event["payload"].get("review_ref") != payload["adjudication_review_ref"]:
                raise RecordError("finding_adjudication_event_mismatch", event["event_id"])
            review_entry = _index_entry(index, payload["adjudication_review_ref"], "review", engagement_id)
            review = load_json(engagement / review_entry["path"]) if review_entry is not None else {}
            if review_entry is None or payload["adjudication_review_ref"] not in committed_entity_ids or sha256_file(engagement / review_entry["path"]) != payload["adjudication_review_digest"] or review.get("proposed_finding_id") != finding_id or review.get("finding_revision") != expected_supersedes or finding.get("scope_provenance", {}).get("provenance", {}).get("actor", {}).get("id") != review.get("independence", {}).get("reviewer_id"):
                raise RecordError("finding_adjudication_review_mismatch", event["event_id"])
            if states["claim"].get(finding_id) != payload["status"] or finding_id not in event["finding_refs"] or payload["adjudication_review_ref"] not in event["review_refs"]:
                raise RecordError("finding_claim_state_mismatch", event["event_id"])
        if event["event_type"] == "hypothesis.created":
            origin_type, origin_ref = payload["origin_type"], payload["origin_ref"]
            if origin_type == "candidate":
                candidate = state["candidates"].get(origin_ref)
                if not candidate or candidate.get("status") != "selected":
                    raise RecordError("hypothesis_origin_candidate_not_selected", event["event_id"])
                if not set(payload["card_ids"]).intersection(candidate["card_ids"]):
                    raise RecordError("hypothesis_candidate_card_mismatch", event["event_id"])
                if payload.get("candidate_ref") not in (None, origin_ref):
                    raise RecordError("hypothesis_candidate_ref_mismatch", event["event_id"])
            elif origin_type == "operator_prior":
                if origin_ref not in seen_events or seen_events[origin_ref]["event_type"] != "operator_prior.recorded":
                    raise RecordError("hypothesis_origin_not_prior_operator_event", event["event_id"])
            elif origin_type == "reviewer_challenge":
                if not ((origin_ref in seen_events and seen_events[origin_ref]["event_type"] in {"review.challenge_recorded", "review.regrade_completed"}) or _index_entry(index, origin_ref, "review", engagement_id)):
                    raise RecordError("hypothesis_origin_not_prior_challenge", event["event_id"])
            elif origin_type == "confirmed_primitive":
                origin_event = seen_events.get(origin_ref)
                event_confirmed = origin_event is not None and origin_event["event_type"] in {"claim.adjudicated", "finding.revised"} and origin_event["payload"].get("status") == "confirmed"
                finding_commitment = committed_records.get(origin_ref)
                file_confirmed = finding_commitment is not None and load_json(engagement / finding_commitment["record_path"]).get("claim_state") == "confirmed"
                if not (event_confirmed or file_confirmed):
                    raise RecordError("hypothesis_origin_not_confirmed_primitive", event["event_id"])
            elif origin_type == "target_model":
                if origin_ref not in seen_events or seen_events[origin_ref]["event_type"] != "observation.recorded":
                    raise RecordError("hypothesis_origin_not_prior_target_model", event["event_id"])
        if event["event_type"] == "review.coverage_completed":
            if payload.get("review_type") != "coverage" or not event["review_refs"]:
                raise RecordError("coverage_review_event_invalid", event["event_id"])
            dispositions: dict[str, str] = {}
            for review_ref in event["review_refs"]:
                entry = _index_entry(index, review_ref, "review", engagement_id)
                if entry is None:
                    raise RecordError("coverage_review_record_missing", review_ref)
                review = load_json(engagement / entry["path"])
                if review.get("review_type") != "coverage" or review.get("verdict") != payload.get("verdict") or review.get("independence", {}).get("fresh_context") is not True or review.get("independence", {}).get("reviewer_id") != payload.get("reviewer_id", event["actor"]["id"]):
                    raise RecordError("coverage_review_not_cold", review_ref)
                for item in review.get("hypothesis_dispositions", []):
                    if item["hypothesis_ref"] in dispositions:
                        raise RecordError("coverage_review_duplicate_hypothesis", item["hypothesis_ref"])
                    dispositions[item["hypothesis_ref"]] = item["status"]
            current_dispositions = {key: value["status"] for key, value in state["hypotheses"].items()}
            if dispositions != current_dispositions:
                raise RecordError("coverage_review_hypothesis_state_mismatch", f"review={dispositions}; state={current_dispositions}")
        if event["event_type"] == "coverage.status_changed" and payload.get("status") == "coverage_dry":
            review_event = seen_events.get(payload["coverage_review_ref"])
            if review_event is None or review_event["event_type"] != "review.coverage_completed" or review_event["payload"].get("verdict") != "coverage_dry":
                raise RecordError("coverage_dry_without_cold_review", event["event_id"])
            unresolved = {key: value["status"] for key, value in state["hypotheses"].items() if value["status"] not in {"exhausted", "closed"}}
            if unresolved:
                raise RecordError("coverage_dry_with_active_hypotheses", str(unresolved))
        for change in event["state_changes"]:
            validate_transition(states, change)
        event_type = event["event_type"]
        if event_type == "scope.attested":
            prior = state["scope_hash"]
            if event["sequence"] > 1 and payload.get("supersedes_scope_hash") != prior:
                raise RecordError("scope_reattestation_mismatch", event["event_id"])
            state["scope_hash"] = payload["scope_hash"]
            if event["sequence"] > 1:
                state["active_environment_ref"] = None
                for request in state["authority_requests"].values():
                    if request["status"] in {"pending_authority", "approved"}: request["status"] = "superseded"
        elif event_type == "authority.requested":
            state["authority_requests"][payload["request_id"]] = {"request_id": payload["request_id"], "request_event_ref": event["event_id"], "action_kind": payload["action_kind"], "action_digest": payload["action_digest"], "action_path": payload.get("action_path"), "lane_id": payload["lane_id"], "status": "pending_authority", "requested_at": event["recorded_at"], "scope_hash": payload["scope_hash"], "environment_ref": payload["environment_ref"], "expires_at": payload["expires_at"], "resolved_at": None, "resolution_event_ref": None}
        elif event_type == "authority.resolved":
            request = state["authority_requests"][payload["request_id"]]; request["status"] = payload["resolution"]; request["resolved_at"] = payload["resolved_at"]; request["resolution_event_ref"] = event["event_id"]
        elif event_type == "scope.amendment_proposed":
            state["scope_drafts"].append({"event_id": event["event_id"], "draft_path": payload["draft_path"], "draft_digest": payload["draft_digest"], "supersedes_scope_hash": payload["supersedes_scope_hash"]})
        elif event_type == "environment.review_recorded":
            current = state["environment_preflights"][payload["environment_ref"]]; current["status"] = payload["status"]; current["operator_review_ref"] = payload["review_ref"]
            state["active_environment_ref"] = payload["environment_ref"] if payload["status"] == "ready" else None
            for authority_request in state["authority_requests"].values():
                if authority_request["status"] in {"pending_authority", "approved"} and authority_request["environment_ref"] != state["active_environment_ref"]: authority_request["status"] = "superseded"
        elif event_type == "environment.preflight_recorded":
            environment_entry = _index_entry(index, payload["environment_ref"], "environment", engagement_id)
            environment = load_json(engagement / environment_entry["path"])
            state["environment_preflights"][payload["environment_ref"]] = {"status": payload["status"], "identity_hash": payload["identity_hash"], "scope_hash": environment["scope_hash"], "operator_review_ref": None}
            state["active_environment_ref"] = payload["environment_ref"] if payload["status"] == "ready" else None
            for authority_request in state["authority_requests"].values():
                if authority_request["status"] in {"pending_authority", "approved"} and authority_request["environment_ref"] != state["active_environment_ref"]: authority_request["status"] = "superseded"
        elif event_type == "cleanup.updated":
            obligations = {item["obligation_id"]: item for item in state["cleanup"]["obligations"]}
            for item in payload["cleanup_obligations"]:
                obligations[item["obligation_id"]] = {"obligation_id": item["obligation_id"], "status": item["status"]}
            state["cleanup"]["obligations"] = [obligations[key] for key in sorted(obligations)]
            state["cleanup"]["open_count"] = sum(item["status"] in {"open", "blocked"} for item in obligations.values())
            state["cleanup"]["recorded"] = True
        elif event_type == "routing.assessed" and payload["activation_strength"] == "negative":
            state["control_candidates"].append({"routing_event_id": event["event_id"], "source_observation_ref": payload["source_observation_ref"], "card_ids": payload["card_ids"], "status": "likely_held", "rationale": event["rationale"]})
        elif event_type == "candidate.proposed":
            state["candidates"][payload["candidate_id"]] = {"status": payload["status"], "rationale": event["rationale"], "source_observation_ref": payload["source_observation_ref"], "routing_review_ref": payload["routing_review_ref"], "activation_strength": payload["activation_strength"], "card_ids": payload["card_ids"], "ex_ante": event["ex_ante"]}
        elif event_type in {"candidate.selected", "candidate.skipped", "candidate.deferred"}:
            candidate = state["candidates"].setdefault(payload["candidate_id"], {})
            candidate["status"] = payload["status"]
            candidate["rationale"] = event["rationale"]
        elif event_type == "operator_prior.recorded":
            state["operator_priors"].append({"event_id": event["event_id"], "prior_id": payload["prior_id"], "prior_statement": payload["prior_statement"], "entity_refs": event["entity_refs"], "strength": payload.get("strength"), "rationale": event["rationale"]})
            if payload.get("reopen_hypothesis_id"):
                hypothesis = state["hypotheses"].get(payload["reopen_hypothesis_id"])
                if hypothesis is None:
                    raise RecordError("operator_prior_reopen_hypothesis_missing", event["event_id"])
                hypothesis["status"] = "queued"
                hypothesis["rationale"] = payload["reopening_condition"]
        elif event_type == "hypothesis.created":
            state["hypotheses"][payload["hypothesis_id"]] = {"status": payload["status"], "rationale": event["rationale"], "origin_type": payload["origin_type"], "origin_ref": payload["origin_ref"], "statement": payload["hypothesis_statement"], "suspected_invariant": payload["suspected_invariant"], "trust_boundary": payload["trust_boundary"], "attacker_path": payload["attacker_path"], "impact_ceiling": payload["impact_ceiling"], "bounded_space": payload["bounded_space"], "lens_ids": payload["lens_ids"], "card_ids": payload["card_ids"], "expected_confirming_evidence": payload["expected_confirming_evidence"], "decisive_falsifiers": payload["decisive_falsifiers"], "cost_estimate": payload["cost_estimate"], "constraints": payload["constraints"], "next_experiment": payload["next_experiment"], "completion_criteria": payload["completion_criteria"], "experiment_refs": [], "control_refs": [], "supporting_evidence_refs": [], "conflicting_evidence_refs": [], "unresolved_questions": [], "next_route": None}
            if payload["origin_type"] == "reviewer_challenge":
                for item in state["outstanding_reviews"]:
                    if item["review_ref"] == payload["origin_ref"] and item["status"] == "pending":
                        item["status"] = "routed"; item["hypothesis_ref"] = payload["hypothesis_id"]
        elif event_type == "hypothesis.status_changed":
            hypothesis = state["hypotheses"].setdefault(payload["hypothesis_id"], {})
            hypothesis.update({"status": payload["status"], "rationale": payload["disposition_rationale"], "experiment_refs": payload["experiment_refs"], "control_refs": payload["control_refs"], "supporting_evidence_refs": payload["supporting_evidence_refs"], "conflicting_evidence_refs": payload["conflicting_evidence_refs"], "unresolved_questions": payload["unresolved_questions"], "next_route": payload["next_route"]})
            if payload["supporting_evidence_refs"]:
                for item in state["outstanding_reviews"]:
                    if item["hypothesis_ref"] == payload["hypothesis_id"] and item["status"] == "routed":
                        opened_at = datetime.fromisoformat(item["opened_at"].replace("Z", "+00:00"))
                        evidence_is_new = all(any(entry.get("recorded_at") and datetime.fromisoformat(entry["recorded_at"].replace("Z", "+00:00")) > opened_at for entry in index.get(reference, []) if entry.get("engagement_id") == engagement_id) for reference in payload["supporting_evidence_refs"])
                        if evidence_is_new:
                            item["status"] = "evidence_collected"
        elif event_type == "review.regrade_completed":
            if payload["verdict"] == "escalation_found":
                state["outstanding_reviews"].append({"review_type": "regrade_escalation", "entity_ref": payload["finding_id"], "review_ref": event["event_id"], "reason": event["rationale"], "status": "pending", "hypothesis_ref": None, "opened_at": event["recorded_at"]})
            elif payload["verdict"] in {"confirmed_with_correction", "needs_more_evidence", "blocked"}:
                status = "correction_required" if payload["verdict"] == "confirmed_with_correction" else ("blocked" if payload["verdict"] == "blocked" else "pending")
                state["outstanding_reviews"].append({"review_type": "regrade", "entity_ref": payload["finding_id"], "review_ref": event["event_id"], "reason": event["rationale"], "status": status, "hypothesis_ref": None, "opened_at": event["recorded_at"]})
        elif event_type == "review.pocinator_completed":
            key = f"{payload['finding_id']}:r{payload['finding_revision']}"
            prior_proof = state["proof_reviews"].get(key)
            accumulate = prior_proof is not None and prior_proof["verdict"] == payload["verdict"] == "reward_hacked"
            refs = ([*prior_proof["review_refs"], payload["review_ref"]] if accumulate and payload["review_ref"] not in prior_proof["review_refs"] else ([payload["review_ref"]] if not accumulate else prior_proof["review_refs"]))
            reviewer_id = review["independence"]["reviewer_id"]
            reviewer_ids = ([*prior_proof["reviewer_ids"], reviewer_id] if accumulate and reviewer_id not in prior_proof["reviewer_ids"] else ([reviewer_id] if not accumulate else prior_proof["reviewer_ids"]))
            if payload["verdict"] == "verified": terminal = "verified"
            elif payload["verdict"] == "blocked": terminal = "blocked"
            elif payload["verdict"] == "reward_hacked" and payload["high_value"]: terminal = "second_review_confirmed" if len(refs) >= 2 and len(reviewer_ids) >= 2 else "pending_second_review"
            else: terminal = "route_back"
            state["proof_reviews"][key] = {"finding_revision": payload["finding_revision"], "claim_tuple_hash": payload["claim_tuple_hash"], "verdict": payload["verdict"], "review_refs": refs, "reviewer_ids": reviewer_ids, "terminal_status": terminal}
            if terminal in {"route_back", "pending_second_review", "blocked"}:
                state["outstanding_reviews"].append({"review_type": "pocinator", "entity_ref": payload["finding_id"], "review_ref": event["event_id"], "reason": event["rationale"], "status": "blocked" if terminal == "blocked" else "correction_required", "hypothesis_ref": None, "opened_at": event["recorded_at"]})
        elif event_type == "legacy.record_imported" and payload.get("imported_finding_id") is not None:
            commitment=committed_records[payload["imported_finding_id"]]
            state["findings"][payload["imported_finding_id"]]={"revision":payload["imported_revision"],"status":"needs_review","digest":commitment["record_digest"],"adjudication_review_ref":None,"change_reason":"initial legacy reconstruction"}
            state["outstanding_reviews"].append({"review_type":"legacy_adjudication","entity_ref":payload["imported_finding_id"],"review_ref":event["event_id"],"reason":"Legacy finding requires independent adjudication before any authority or report acceptance.","status":"pending","hypothesis_ref":None,"opened_at":event["recorded_at"]})
        elif event_type == "finding.revised":
            state["findings"][payload["finding_id"]] = {"revision": payload["finding_revision"], "status": payload["status"], "digest": payload["finding_digest"], "adjudication_review_ref": payload["adjudication_review_ref"], "change_reason": payload["change_reason"]}
            resolved = set(payload.get("resolves_review_refs", []))
            state["outstanding_reviews"] = [item for item in state["outstanding_reviews"] if item["review_ref"] not in resolved]
        elif event_type == "report.generated":
            state["report_refs"].append(payload["report_ref"])
            state["reports"][payload["report_ref"]] = {"finding_id": payload["finding_id"], "finding_revision": payload["finding_revision"], "status": "draft", "manifest_digest": payload["report_manifest_digest"], "historical_reason": None}
        elif event_type == "operator.review_recorded":
            state["reports"][payload["report_ref"]]["status"] = "accepted"
        elif event_type == "submission.recorded":
            state["submission_refs"].append(payload["submission_ref"])
            state["reports"][payload["report_ref"]]["status"] = "submitted"
        elif event_type == "memory.disposition_recorded":
            state["memory_disposition"] = {"disposition": payload["memory_disposition"], "disposition_ref": payload["disposition_ref"], "disposition_digest": payload["disposition_digest"]}
        elif event_type == "engagement.blocked":
            state["active_blockers"].append(event["rationale"])
        elif event_type == "engagement.reopened":
            state["active_blockers"] = []
        if event_type == "record.committed":
            committed_entity_ids.add(payload["record_id"])
            committed_records[payload["record_id"]] = payload
        state["last_event_id"] = event["event_id"]
        seen_events[event["event_id"]] = event
    if not allow_scope_drift:
        metadata = _scope_metadata(engagement / "scope.md")
        # Drifted bytes are an unattested proposal, not active authority. Continue reducing
        # against the immutable latest attestation; exact scope-bound operations therefore
        # remain confined to the old scope while propose-scope can preserve the new bytes.
        if metadata["scope_hash"] == state["scope_hash"]:
            latest_scope_event = next(event for event in reversed(events) if event["event_type"] == "scope.attested")
            signed_operator_id = re.sub(r"[^A-Za-z0-9._:-]+", "-", metadata["operator"]).strip("-") or "operator"
            if latest_scope_event["actor"] != {"role": "operator", "id": signed_operator_id} or latest_scope_event["payload"].get("operator_id") != signed_operator_id or latest_scope_event["payload"].get("signed_date") != metadata["date"]:
                raise RecordError("active_scope_attestation_mismatch", "latest scope event does not match the current signed scope operator/date")
    for report in state["reports"].values():
        current_revision = state["findings"].get(report["finding_id"], {}).get("revision")
        if current_revision is not None and current_revision != report["finding_revision"]:
            report["status"] = "historical"
            report["historical_reason"] = f"superseded by finding revision {current_revision}"
    state["event_count"] = len(events)
    state["attempt_count"] = len(attempts)
    state["artifact_count"] = len(artifacts)
    state["coverage"] = states["coverage"].get(state["engagement_id"], "active")
    state["ledger_hash"] = events[-1]["record_hash"]
    state["source_hashes"] = {
        name: sha256_file(engagement / name) for name in ("events.jsonl", "attempts.jsonl", "artifacts.jsonl")
    }
    errors = validate_record(state, "state-snapshot")
    if errors:
        raise RecordError("snapshot_schema_invalid", "reducer emitted invalid state", errors)
    return state


def require_repair_authority_from_intact_prefix(engagement: Path, request_id: str, action_kind: str, action_digest: str, lane_id: str, applied_at: str) -> dict[str, Any]:
    engagement = engagement.absolute(); data = read_governed_file(engagement / "events.jsonl"); boundary = data.rfind(b"\n") + 1 if data and not data.endswith(b"\n") else len(data); prefix = data[:boundary]
    events = _parse_ledger_data(prefix, "events.jsonl", "engagement-event", "event_id"); request_event = next((event for event in events if event["event_type"] == "authority.requested" and event["payload"].get("request_id") == request_id), None); resolution = next((event for event in events if event["event_type"] == "authority.resolved" and event["payload"].get("request_id") == request_id), None)
    if request_event is None or resolution is None or resolution["payload"].get("resolution") != "approved" or resolution["payload"].get("request_event_ref") != request_event["event_id"] or resolution["payload"].get("action_digest") != action_digest: raise RecordError("approved_authority_request_required", request_id)
    request = request_event["payload"]; latest_scope_event = next(event for event in reversed(events) if event["event_type"] == "scope.attested"); signed_operator = latest_scope_event["payload"]["operator_id"]; active_scope = latest_scope_event["payload"]["scope_hash"]
    active_environment = None
    for event in events:
        if event["event_type"] in {"environment.preflight_recorded", "environment.review_recorded"}: active_environment = event["payload"]["environment_ref"] if event["payload"].get("status") == "ready" else None
        elif event["event_type"] == "scope.attested": active_environment = None
    applied = datetime.fromisoformat(applied_at.replace("Z", "+00:00")); expires = datetime.fromisoformat(request["expires_at"].replace("Z", "+00:00")) if request.get("expires_at") else None; resolved = datetime.fromisoformat(resolution["recorded_at"].replace("Z", "+00:00")); action_path = engagement / str(request.get("action_path", ""))
    consumed = any(event["event_type"] != "record.committed" and event["payload"].get("authority_request_ref") == request_id for event in events)
    if request.get("action_kind") != action_kind or request.get("action_digest") != action_digest or request.get("lane_id") != lane_id or request.get("scope_hash") != active_scope or request.get("environment_ref") != active_environment or resolution["actor"] != {"role": "operator", "id": signed_operator} or applied < resolved or expires is None or applied > expires or datetime.now(timezone.utc) > expires or consumed or not action_path.is_file() or action_path.is_symlink() or sha256_file(action_path) != action_digest: raise RecordError("repair_authority_invalid", request_id)
    return {"request_id": request_id, "status": "approved", "request_event_ref": request_event["event_id"], "resolution_event_ref": resolution["event_id"]}


def require_approved_authority(engagement: Path, request_id: str, action_kind: str, action_digest: str, lane_id: str, applied_at: str) -> dict[str, Any]:
    state = reduce_engagement(engagement)
    request = state["authority_requests"].get(request_id)
    if request is None or request["status"] != "approved" or request["action_kind"] != action_kind or request["action_digest"] != action_digest or request["lane_id"] != lane_id or request["scope_hash"] != state["scope_hash"] or request["environment_ref"] not in {None, state["active_environment_ref"]}:
        raise RecordError("approved_authority_request_required", request_id)
    applied = datetime.fromisoformat(applied_at.replace("Z", "+00:00"))
    if request["expires_at"] is not None and datetime.now(timezone.utc) > datetime.fromisoformat(request["expires_at"].replace("Z", "+00:00")):
        raise RecordError("authority_request_not_current", request_id)
    if request["resolved_at"] is None or applied < datetime.fromisoformat(request["resolved_at"].replace("Z", "+00:00")) or (request["expires_at"] is not None and applied > datetime.fromisoformat(request["expires_at"].replace("Z", "+00:00"))):
        raise RecordError("authority_request_not_current", request_id)
    for event in read_ledger(engagement, "event"):
        if event.get("event_type") != "record.committed" and event.get("payload", {}).get("authority_request_ref") == request_id:
            raise RecordError("authority_request_already_consumed", request_id)
    return request


def write_snapshot(engagement: Path, snapshot: dict[str, Any]) -> None:
    atomic_write(engagement / "state.snapshot.json", canonical_json_bytes(snapshot))


def assert_resume_current(engagement: Path) -> dict[str, Any]:
    expected = reduce_engagement(engagement)
    snapshot_path = engagement / "state.snapshot.json"
    if not snapshot_path.is_file() or snapshot_path.is_symlink() or read_governed_file(snapshot_path) != canonical_json_bytes(expected):
        raise RecordError("stale_state_snapshot", "run `reduce` to rebuild state.snapshot.json")
    from engagement_views import assert_views_current
    assert_views_current(engagement, expected)
    return expected


def append_event(engagement: Path, proposal: dict[str, Any], *, lock_held: bool = False) -> dict[str, Any]:
    """Public notebook append boundary; authority and typed reviews use dedicated commands."""
    capability = classify_event(proposal.get("event_type", ""), proposal.get("payload", {}))
    if proposal.get("event_type") == "record.committed":
        raise RecordError("canonical_record_command_required", proposal.get("payload", {}).get("record_type", "unknown"))
    if capability["tier"] in {"authority", "real_world"}:
        raise RecordError("canonical_authority_command_required", proposal.get("event_type", "unknown"))
    if proposal.get("actor", {}).get("role") == "reviewer" or proposal.get("event_type", "").startswith("review.") or proposal.get("event_type") == "claim.adjudicated":
        raise RecordError("canonical_review_command_required", proposal.get("event_type", "unknown"))
    require_actor(capability, proposal.get("actor", {}).get("role", ""))
    if proposal.get("operation_class") != capability["tier"]:
        raise RecordError("event_operation_class_mismatch", proposal.get("event_type", "unknown"))
    if not proposal.get("provenance", {}).get("session_id"):
        raise RecordError("session_provenance_required", proposal.get("event_type", "unknown"))
    return _append_kernel_event(engagement, proposal, lock_held=lock_held)


def _append_kernel_event_idempotent(engagement: Path, proposal: dict[str, Any], *, lock_held: bool = False) -> dict[str, Any]:
    existing = next((event for event in read_ledger(engagement, "event") if event["event_id"] == proposal["event_id"]), None)
    if existing is not None:
        strip_chain = lambda value: {key: item for key, item in value.items() if key not in {"sequence", "previous_hash", "record_hash"}}
        if canonical_json_bytes(strip_chain(existing)) != canonical_json_bytes(strip_chain(proposal)): raise RecordError("event_id_collision", proposal["event_id"])
        return existing
    return _append_kernel_event(engagement, proposal, lock_held=lock_held)


def _append_kernel_event(engagement: Path, proposal: dict[str, Any], *, lock_held: bool = False) -> dict[str, Any]:
    """Trusted kernel producer path; never expose this as a public command."""
    # The append, reduction, snapshot, and views share one lock so concurrent writers cannot publish
    # a projection older than the authoritative ledger tail.
    with (nullcontext() if lock_held else engagement_lock(engagement)):
        current_events = read_ledger(engagement, "event")
        if not current_events:
            raise RecordError("scope_attestation_missing", "initialize engagement first")
        proposal = copy.deepcopy(proposal)
        if proposal.get("engagement_id") != current_events[0]["engagement_id"]:
            raise RecordError("cross_engagement_event", str(proposal.get("event_id")))
        latest_scope_hash = next(event["payload"]["scope_hash"] for event in reversed(current_events) if event["event_type"] == "scope.attested")
        if proposal.get("event_type") not in {"scope.attested", "scope.amendment_proposed"}:
            draft_bytes = read_governed_file(engagement/"scope.md"); draft_digest = sha256_bytes(draft_bytes)
            if draft_digest != latest_scope_hash and not any(event["event_type"] == "scope.amendment_proposed" and event["payload"].get("draft_digest") == draft_digest for event in current_events):
                if not draft_bytes or detect_secret_classes(draft_bytes): raise RecordError("scope_draft_invalid", "drifted scope bytes are empty or secret-shaped")
                relative = f"scope-drafts/{draft_digest.removeprefix('sha256:')}.md"; destination = engagement/relative
                if destination.exists() and read_governed_file(destination) != draft_bytes: raise RecordError("scope_draft_collision", relative)
                if not destination.exists(): atomic_write(destination, draft_bytes)
                uid, sid = os.getuid(), os.getsid(0); draft_event = base_event(event_id=f"event-scope-draft-{draft_digest[-12:]}", engagement_id=current_events[0]["engagement_id"], recorded_at=proposal["recorded_at"], actor_role="broker", actor_id=f"local-uid-{uid}:broker", event_type="scope.amendment_proposed", rationale="Preserve drifted scope bytes without activating them.", payload={"draft_path": relative, "draft_digest": draft_digest, "supersedes_scope_hash": latest_scope_hash}, session_id=f"session-posix-{uid}-{sid}", operation_class="notebook")
                _append_kernel_event(engagement, draft_event, lock_held=True); current_events = read_ledger(engagement, "event")
        if proposal.get("event_type") == "scope.attested":
            payload = proposal.get("payload", {})
            metadata = _scope_metadata(engagement / "scope.md")
            signed_operator_id = re.sub(r"[^A-Za-z0-9._:-]+", "-", metadata["operator"]).strip("-") or "operator"
            if payload.get("scope_hash") != metadata["scope_hash"] or payload.get("supersedes_scope_hash") != latest_scope_hash:
                raise RecordError("scope_reattestation_mismatch", "fresh scope attestation must bind current bytes and supersede the active hash")
            if proposal.get("actor", {}).get("role") != "operator" or proposal.get("actor", {}).get("id") != signed_operator_id or payload.get("operator_id") != signed_operator_id or payload.get("signed_date") != metadata["date"]:
                raise RecordError("scope_reattestation_not_operator_bound", "attestation actor must match the signed scope operator and date")
            reduce_engagement(engagement, allow_scope_drift=True)  # validates every historical attestation before extending authority
            expected_snapshot = f"scope-attestations/{metadata['scope_hash'].removeprefix('sha256:')}.md"
            if payload.get("scope_snapshot_path") not in (None, expected_snapshot):
                raise RecordError("scope_snapshot_path_mismatch", proposal["event_id"])
            payload["scope_snapshot_path"] = persist_scope_snapshot(engagement, metadata["scope_hash"])
        preview = materialize_ledger_record("event", proposal, current_events)
        validate_event_semantics(preview)
        reference_errors = validate_record_references(preview, "engagement-event", build_reference_index(engagement))
        if reference_errors:
            raise RecordError("record_reference_invalid", "event references do not resolve", reference_errors)
        if proposal.get("event_type") == "record.committed":
            validate_committed_payload(engagement, proposal["payload"])
            reduce_engagement(engagement, allowed_record_orphans={proposal["payload"]["record_path"]})
        elif proposal.get("event_type") != "scope.attested":
            reduce_engagement(engagement)  # blocks every ordinary write after scope drift
        states: dict[str, dict[str, str]] = {dimension: {} for dimension in STATE_VALUES}
        for event in current_events:
            for change in event["state_changes"]:
                validate_transition(states, change)
        for change in proposal.get("state_changes", []):
            validate_transition(states, change)
        ledger_path = engagement / LEDGERS["event"][0]
        verified_boundary = ledger_path.stat().st_size
        record = append_ledger_record(engagement, "event", proposal, lock_held=True)
        try:
            snapshot = reduce_engagement(engagement)
        except Exception:
            with open(ledger_path, "r+b") as handle:
                handle.truncate(verified_boundary)
                handle.flush()
                os.fsync(handle.fileno())
            raise
        write_snapshot(engagement, snapshot)
        from engagement_views import write_views
        write_views(engagement, snapshot)
        return record


def register_artifact(engagement: Path, file_path: Path, metadata: dict[str, Any], *, classification: dict[str, Any]) -> dict[str, Any]:
    variant = artifact_variant(metadata)
    expected_class = "notebook" if variant == "clear_local" else "real_world"
    if metadata.get("operation_class") != expected_class or not metadata.get("producer_session_id"):
        raise RecordError("artifact_provenance_invalid", metadata.get("artifact_id", "unknown"))
    if metadata.get("advisory_zone") not in ({"clear_local"} if variant == "clear_local" else {"review_required", "unknown"}):
        raise RecordError("artifact_zone_underclassified", metadata.get("artifact_id", "unknown"))
    if expected_class == "real_world" and (not metadata.get("escalation_confirmation_event_ref") or not metadata.get("cleanup_obligation_ref")):
        raise RecordError("artifact_creation_requires_fresh_confirmation", metadata.get("artifact_id", "unknown"))
    unhashed_metadata = copy.deepcopy(metadata)
    for field in ("precreation_classification_digest", "precreation_classification_event_ref", "classified_source_digest", "classified_source_size", "classified_at"):
        unhashed_metadata.pop(field, None)
    classification_body = {key: value for key, value in classification.items() if key != "classification_event_ref"}
    classification_digest = sha256_bytes(canonical_json_bytes(classification_body))
    expected_decision = "allow_local_creation" if expected_class == "notebook" else "allow_confirmed_creation"
    if classification.get("decision") != expected_decision or classification.get("file_absent_at_classification") is not True or classification.get("artifact_id") != metadata.get("artifact_id") or classification.get("metadata_digest") != sha256_bytes(canonical_json_bytes(unhashed_metadata)) or metadata.get("precreation_classification_digest") != classification_digest or metadata.get("precreation_classification_event_ref") != classification.get("classification_event_ref") or metadata.get("classified_source_digest") != classification.get("source_digest") or metadata.get("classified_source_size") != classification.get("source_size") or metadata.get("classified_at") != classification.get("classified_at"):
        raise RecordError("artifact_classification_mismatch", metadata.get("artifact_id", "unknown"))
    state = reduce_engagement(engagement, allowed_artifact_orphans={classification.get("relative_path", "")})
    event = next((item for item in read_ledger(engagement, "event") if item["event_id"] == classification.get("classification_event_ref")), None)
    expired = classification.get("expires_at") is not None and datetime.now(timezone.utc) > datetime.fromisoformat(classification["expires_at"].replace("Z", "+00:00"))
    if event is None or event["event_type"] != "artifact.classified" or event["payload"].get("classification_digest") != classification_digest or classification.get("scope_hash") != state["scope_hash"] or classification.get("environment_ref") != state["active_environment_ref"] or expired:
        raise RecordError("artifact_classification_event_invalid", metadata.get("artifact_id", "unknown"))
    return _register_artifact_core(engagement, file_path, metadata)


def _register_legacy_artifact(engagement: Path, file_path: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    """Trusted Decision-0005/migration compatibility path; never exposed by the public CLI."""
    if metadata.get("schema_version") != 1 or metadata.get("operation_class") is not None or metadata.get("producer", {}).get("role") not in {"operator", "migration", "broker"} or (metadata.get("producer", {}).get("role") == "broker" and not metadata.get("producer_session_id")):
        raise RecordError("legacy_artifact_compatibility_invalid", metadata.get("artifact_id", "unknown"))
    return _register_artifact_core(engagement, file_path, metadata)


def _register_artifact_core(engagement: Path, file_path: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    engagement = engagement.absolute()
    governed_file = file_path.absolute()
    try: relative_path = governed_file.relative_to(engagement)
    except ValueError: raise RecordError("artifact_path_not_contained", "artifact must be a regular non-symlink file under engagement/evidence")
    if not relative_path.parts or relative_path.parts[0] != "evidence" or any(part in {"", ".", ".."} for part in relative_path.parts): raise RecordError("artifact_path_not_contained", "artifact must be a regular non-symlink file under engagement/evidence")
    try: artifact_bytes = read_governed_file(governed_file)
    except (OSError, RecordError): raise RecordError("artifact_path_not_contained", "artifact must be a regular non-symlink file under engagement/evidence")
    relative = relative_path.as_posix(); artifact_digest = sha256_bytes(artifact_bytes)
    if metadata.get("classified_source_digest") is not None and (artifact_digest != metadata.get("classified_source_digest") or len(artifact_bytes) != metadata.get("classified_source_size")):
        raise RecordError("artifact_classified_source_mismatch", metadata.get("artifact_id", "unknown"))
    secret_classes = detect_secret_classes(artifact_bytes)
    if secret_classes:
        raise RecordError("secret_shaped_artifact_content", "artifact registration blocked by secret-pattern classes", [{"class": value} for value in secret_classes])
    metadata_secret_classes = detect_secret_classes(canonical_json_bytes(metadata))
    if metadata_secret_classes:
        raise RecordError("secret_shaped_artifact_metadata", "artifact metadata blocked by secret-pattern classes", [{"class": value} for value in metadata_secret_classes])
    proposal = copy.deepcopy(metadata)
    for trusted in ("relative_path", "sha256", "size", "immutable", "sequence", "previous_hash", "record_hash"):
        if trusted in proposal:
            raise RecordError("trusted_field_in_proposal", f"artifact metadata must not set {trusted}")
    proposal.update({"relative_path": relative, "sha256": artifact_digest, "size": len(artifact_bytes), "immutable": True})
    with engagement_lock(engagement):
        reduce_engagement(engagement, allowed_artifact_orphans={relative})
        records = read_ledger(engagement, "artifact")
        preview = materialize_ledger_record("artifact", proposal, records)
        reference_errors = validate_record_references(preview, "artifact", build_reference_index(engagement))
        if reference_errors:
            raise RecordError("record_reference_invalid", "artifact references do not resolve", reference_errors)
        ledger_path = engagement / LEDGERS["artifact"][0]
        verified_boundary = ledger_path.stat().st_size
        record = append_ledger_record(engagement, "artifact", proposal, lock_held=True)
        try:
            snapshot = reduce_engagement(engagement)
        except Exception:
            with open(ledger_path, "r+b") as handle:
                handle.truncate(verified_boundary)
                handle.flush()
                os.fsync(handle.fileno())
            raise
        write_snapshot(engagement, snapshot)
        from engagement_views import write_views
        write_views(engagement, snapshot)
        return record


def append_attempt(engagement: Path, proposal: dict[str, Any]) -> dict[str, Any]:
    with engagement_lock(engagement):
        reduce_engagement(engagement)  # scope and existing ledgers must be authoritative before write
        records = read_ledger(engagement, "attempt")
        preview = materialize_ledger_record("attempt", proposal, records)
        reference_errors = validate_record_references(preview, "attempt-v2", build_reference_index(engagement))
        if reference_errors:
            raise RecordError("record_reference_invalid", "attempt references do not resolve", reference_errors)
        ledger_path = engagement / LEDGERS["attempt"][0]
        verified_boundary = ledger_path.stat().st_size
        record = append_ledger_record(engagement, "attempt", proposal, lock_held=True)
        try:
            snapshot = reduce_engagement(engagement)
        except Exception:
            with open(ledger_path, "r+b") as handle:
                handle.truncate(verified_boundary)
                handle.flush()
                os.fsync(handle.fileno())
            raise
        write_snapshot(engagement, snapshot)
        from engagement_views import write_views
        write_views(engagement, snapshot)
        return record
