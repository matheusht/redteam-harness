#!/usr/bin/env python3
"""Trusted record primitives for the Decision 0005 engagement kernel.

This module owns JSON loading, Draft 2020-12 schema validation, canonical bytes,
and read-only legacy inventory. It does not drive targets or adjudicate claims.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
from typing import Any, Iterable

class RecordError(ValueError):
    """A stable, operator-facing record validation failure."""

    def __init__(self, code: str, message: str, details: list[dict[str, Any]] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or []

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": self.details}


_JSONSCHEMA_IMPORT_ERROR: ImportError | None = None
try:
    from jsonschema import Draft202012Validator, FormatChecker
    from referencing import Registry, Resource
except ImportError as exc:  # imported lazily enough for the CLI to emit a structured failure
    _JSONSCHEMA_IMPORT_ERROR = exc
    Draft202012Validator = FormatChecker = Registry = Resource = None  # type: ignore[assignment]

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"
REQUIRED_JSONSCHEMA_VERSION = "4.26.0"
NEW_SCHEMA_FILES = (
    "research-common.schema.json",
    "finding-v3.schema.json",
    "attempt-v2.schema.json",
    "artifact.schema.json",
    "review.schema.json",
    "engagement-event.schema.json",
    "state-snapshot.schema.json",
    "environment-preflight.schema.json",
    "report-manifest.schema.json",
    "memory-disposition.schema.json",
    "migration-manifest.schema.json",
)
RECORD_SCHEMA_FILES = {
    "finding-v3": "finding-v3.schema.json",
    "attempt-v2": "attempt-v2.schema.json",
    "artifact": "artifact.schema.json",
    "review": "review.schema.json",
    "engagement-event": "engagement-event.schema.json",
    "state-snapshot": "state-snapshot.schema.json",
    "environment-preflight": "environment-preflight.schema.json",
    "report-manifest": "report-manifest.schema.json",
    "memory-disposition": "memory-disposition.schema.json",
    "migration-manifest": "migration-manifest.schema.json",
    "finding-v2-legacy": "finding.schema.json",
}


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RecordError("duplicate_json_key", f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def load_json(path: os.PathLike[str] | str) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle, object_pairs_hook=_reject_duplicate_pairs)
    except RecordError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RecordError("invalid_json", f"cannot load JSON {path}: {exc}") from exc


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha256_file(path: os.PathLike[str] | str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def check_dependency_version() -> None:
    if _JSONSCHEMA_IMPORT_ERROR is not None:
        raise RecordError("validator_unavailable", "jsonschema==4.26.0 and its referencing dependency are not importable") from _JSONSCHEMA_IMPORT_ERROR
    try:
        actual = importlib.metadata.version("jsonschema")
    except importlib.metadata.PackageNotFoundError as exc:
        raise RecordError("validator_unavailable", "jsonschema distribution is not installed") from exc
    if actual != REQUIRED_JSONSCHEMA_VERSION:
        raise RecordError(
            "validator_version_mismatch",
            f"jsonschema {REQUIRED_JSONSCHEMA_VERSION} required, found {actual}",
        )


def _load_schema_documents(schema_dir: Path = SCHEMA_DIR) -> dict[str, dict[str, Any]]:
    documents: dict[str, dict[str, Any]] = {}
    for path in sorted(schema_dir.glob("*.schema.json")):
        document = load_json(path)
        if not isinstance(document, dict):
            raise RecordError("invalid_schema_document", f"schema is not an object: {path}")
        documents[path.name] = document
    return documents


def build_registry(documents: dict[str, dict[str, Any]] | None = None) -> Registry:
    check_dependency_version()
    documents = documents or _load_schema_documents()
    registry = Registry()
    seen: dict[str, str] = {}
    for name, document in sorted(documents.items()):
        schema_id = document.get("$id")
        if schema_id:
            if schema_id in seen:
                raise RecordError("duplicate_schema_id", f"{name} and {seen[schema_id]} declare {schema_id}")
            seen[schema_id] = name
            try:
                registry = registry.with_resource(schema_id, Resource.from_contents(document))
            except Exception as exc:
                raise RecordError("invalid_schema_resource", f"cannot register {name}: {exc}") from exc
    return registry


def _reference_problems(name: str, document: dict[str, Any], documents: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {value.get("$id"): value for value in documents.values() if value.get("$id")}
    problems: list[dict[str, Any]] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            ref = value.get("$ref")
            if isinstance(ref, str):
                if ref.startswith("#"):
                    target = document
                    fragment = ref[1:]
                else:
                    base, marker, fragment = ref.partition("#")
                    target = by_id.get(base)
                    if target is None:
                        problems.append({"schema": name, "code": "unresolved_ref", "ref": ref})
                        target = None
                    fragment = fragment if marker else ""
                if target is not None and fragment.startswith("/"):
                    current: Any = target
                    try:
                        for token in fragment[1:].split("/"):
                            token = token.replace("~1", "/").replace("~0", "~")
                            current = current[token]
                    except (KeyError, TypeError):
                        problems.append({"schema": name, "code": "unresolved_ref_fragment", "ref": ref})
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(document)
    return problems


def validate_schema_documents() -> list[dict[str, Any]]:
    check_dependency_version()
    documents = _load_schema_documents()
    registry = build_registry(documents)
    problems: list[dict[str, Any]] = []
    for name in NEW_SCHEMA_FILES:
        document = documents.get(name)
        if document is None:
            problems.append({"schema": name, "code": "missing_schema"})
            continue
        if document.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            problems.append({"schema": name, "code": "wrong_metaschema"})
            continue
        problems.extend(_reference_problems(name, document, documents))
        try:
            Draft202012Validator.check_schema(document)
            Draft202012Validator(document, registry=registry, format_checker=FormatChecker())
        except Exception as exc:
            problems.append({"schema": name, "code": "invalid_schema", "message": str(exc)})
    return problems


def _error_detail(error: Any) -> dict[str, Any]:
    instance_path = "/" + "/".join(str(part) for part in error.absolute_path)
    schema_path = "/" + "/".join(str(part) for part in error.absolute_schema_path)
    validator = str(error.validator or "schema")
    return {
        "code": f"schema_{validator}",
        "instance_path": instance_path,
        "schema_path": schema_path,
        "message": error.message,
    }


def _semantic_record_errors(record: Any, schema_name: str) -> list[dict[str, Any]]:
    if schema_name != "finding-v3" or not isinstance(record, dict):
        return []
    claims = record.get("claims", {})
    proof = record.get("proof", {})
    claim_ids: list[str] = []
    mechanism = claims.get("mechanism", {})
    reachability = claims.get("reachability", {})
    for value in (mechanism.get("claim_id"), reachability.get("claim_id")):
        if isinstance(value, str):
            claim_ids.append(value)
    for impact in claims.get("impact_claims", []):
        if isinstance(impact, dict) and isinstance(impact.get("claim_id"), str):
            claim_ids.append(impact["claim_id"])
    mapped = [item.get("claim_id") for item in proof.get("claim_proofs", []) if isinstance(item, dict)]
    errors: list[dict[str, Any]] = []
    if len(claim_ids) != len(set(claim_ids)):
        errors.append({"code": "duplicate_claim_id", "instance_path": "/claims", "schema_path": "/semantic", "message": "atomic claim IDs must be unique"})
    if sorted(claim_ids) != sorted(mapped) or len(mapped) != len(set(mapped)):
        errors.append({"code": "claim_proof_mapping_mismatch", "instance_path": "/proof/claim_proofs", "schema_path": "/semantic", "message": "claim_proofs must map every atomic claim exactly once"})
    applicability = proof.get("control_applicability", {})
    requirements = (("negative", "negative_control_refs"), ("positive", "positive_control_refs"), ("replay", "replay_refs"))
    for policy, refs in requirements:
        if applicability.get(policy) == "required" and not proof.get(refs):
            errors.append({"code": "required_control_missing", "instance_path": f"/proof/{refs}", "schema_path": "/semantic", "message": f"{policy} control is required but has no reference"})
    for index_number, mapping in enumerate(proof.get("claim_proofs", [])):
        if not isinstance(mapping, dict):
            continue
        if not mapping.get("attempt_refs") and not mapping.get("artifact_refs"):
            errors.append({"code": "claim_proof_evidence_missing", "instance_path": f"/proof/claim_proofs/{index_number}", "schema_path": "/semantic", "message": "each atomic claim needs an attempt or artifact reference"})
        if (applicability.get("negative") == "required" or applicability.get("positive") == "required") and not mapping.get("control_refs"):
            errors.append({"code": "claim_proof_control_missing", "instance_path": f"/proof/claim_proofs/{index_number}/control_refs", "schema_path": "/semantic", "message": "each atomic claim needs its applicable control binding"})
        if applicability.get("replay") == "required" and not mapping.get("replay_refs"):
            errors.append({"code": "claim_proof_replay_missing", "instance_path": f"/proof/claim_proofs/{index_number}/replay_refs", "schema_path": "/semantic", "message": "each atomic claim needs its applicable replay binding"})
    return errors


def validate_record(record: Any, schema_name: str) -> list[dict[str, Any]]:
    check_dependency_version()
    filename = RECORD_SCHEMA_FILES.get(schema_name)
    if filename is None:
        return [{"code": "unknown_schema", "instance_path": "/", "schema_path": "/", "message": schema_name}]
    documents = _load_schema_documents()
    schema = documents.get(filename)
    if schema is None:
        return [{"code": "missing_schema", "instance_path": "/", "schema_path": "/", "message": filename}]
    try:
        validator = Draft202012Validator(schema, registry=build_registry(documents), format_checker=FormatChecker())
        errors = sorted(validator.iter_errors(record), key=lambda item: (list(item.absolute_path), item.message))
    except Exception as exc:
        return [{"code": "schema_resolution_failed", "instance_path": "/", "schema_path": "/", "message": str(exc)}]
    return [_error_detail(error) for error in errors] + _semantic_record_errors(record, schema_name)


def infer_schema_name(record: Any) -> str | None:
    if not isinstance(record, dict):
        return None
    version = record.get("schema_version")
    if "finding_id" in record and version == 3:
        return "finding-v3"
    if "attempt_id" in record and version == 2:
        return "attempt-v2"
    if "artifact_id" in record and version == 1:
        return "artifact"
    if "review_id" in record and version == 1:
        return "review"
    if "event_id" in record and version == 1:
        return "engagement-event"
    if "last_event_id" in record and "ledger_hash" in record and version == 1:
        return "state-snapshot"
    if "preflight_id" in record and version == 1:
        return "environment-preflight"
    if "report_id" in record and "finding_revision" in record and version == 1:
        return "report-manifest"
    if "disposition_id" in record and version == 1:
        return "memory-disposition"
    if "migration_id" in record and version == 1:
        return "migration-manifest"
    if "id" in record and version in (None, 2):
        return "finding-v2-legacy"
    return None


def resolve_schema_name(record: Any, explicit: str | None = None) -> str:
    inferred = infer_schema_name(record)
    if inferred is None:
        raise RecordError("unknown_record_version", "record identity/schema_version is unknown or ambiguous")
    if explicit and explicit != inferred:
        raise RecordError("schema_dispatch_mismatch", f"record dispatches to {inferred}, not {explicit}")
    return inferred


def _record_identity(record: dict[str, Any]) -> tuple[str, str, int | None] | None:
    identities = (
        ("attempt_id", "attempt"), ("artifact_id", "artifact"), ("review_id", "review"),
        ("preflight_id", "environment"), ("environment_id", "environment"),
        ("finding_id", "finding"), ("event_id", "event"), ("target_id", "target"),
    )
    for key, kind in identities:
        value = record.get(key)
        if isinstance(value, str):
            return value, kind, record.get("revision") if isinstance(record.get("revision"), int) else None
    return None


def build_reference_index(engagement_dir: os.PathLike[str] | str) -> dict[str, list[dict[str, Any]]]:
    root = Path(engagement_dir).resolve()
    index: dict[str, list[dict[str, Any]]] = {}
    paths = sorted(set(root.glob("**/*.json")) | set(root.glob("*.jsonl")))
    for path in paths:
        if path.name in {"state.snapshot.json", "records.index.json"}:
            continue
        records: list[Any]
        if path.suffix == ".jsonl":
            records = []
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    records.append(json.loads(line, object_pairs_hook=_reject_duplicate_pairs))
                except (json.JSONDecodeError, RecordError) as exc:
                    raise RecordError("invalid_jsonl", f"{path}:{line_number}: {exc}") from exc
        else:
            records = [load_json(path)]
        for record in records:
            if not isinstance(record, dict):
                continue
            identity = _record_identity(record)
            if identity:
                entity_id, kind, revision = identity
                entry = {"type": kind, "engagement_id": record.get("engagement_id") or record.get("engagement"), "revision": revision, "path": path.relative_to(root).as_posix()}
                index.setdefault(entity_id, []).append(entry)
            if record.get("event_type") in {"candidate.proposed", "hypothesis.created"}:
                payload = record.get("payload", {})
                key = "candidate_id" if record["event_type"] == "candidate.proposed" else "hypothesis_id"
                entity_id = payload.get(key) if isinstance(payload, dict) else None
                if isinstance(entity_id, str):
                    kind = "candidate" if record["event_type"] == "candidate.proposed" else "hypothesis"
                    index.setdefault(entity_id, []).append({"type": kind, "engagement_id": record.get("engagement_id"), "revision": None, "path": path.relative_to(root).as_posix()})
    for entity_id, entries in index.items():
        seen: set[tuple[str, int | None]] = set()
        for entry in entries:
            key = (entry["type"], entry["revision"])
            if key in seen:
                raise RecordError("duplicate_record_id", f"duplicate {entry['type']} ID/revision: {entity_id}")
            seen.add(key)
    return index


def _at(record: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = record
    for part in path:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def validate_record_references(record: Any, schema_name: str, index: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    if not isinstance(record, dict):
        return []
    engagement_id = record.get("engagement_id") or record.get("engagement")
    specs: dict[str, list[tuple[tuple[str, ...], set[str]]]] = {
        "finding-v3": [
            (("scope_provenance", "environment_ref"), {"environment"}), (("scope_provenance", "target_refs"), {"target"}),
            (("proof", "primary_attempt_refs"), {"attempt"}), (("proof", "negative_control_refs"), {"attempt"}),
            (("proof", "positive_control_refs"), {"attempt"}), (("proof", "replay_refs"), {"attempt"}),
            (("proof", "evidence_refs"), {"attempt", "artifact"}), (("claims", "conflicting_evidence"), {"attempt", "artifact"}),
            (("adjudication", "review_ref"), {"review"}), (("search_linkage", "candidate_refs"), {"candidate"}),
            (("search_linkage", "hypothesis_refs"), {"hypothesis"}),
        ],
        "attempt-v2": [
            (("environment_ref",), {"environment"}), (("escalation_confirmation_event_ref",), {"event"}),
            (("hypothesis_ref",), {"hypothesis"}), (("experiment_ref",), {"event", "experiment"}),
            (("evidence_refs",), {"artifact"}), (("control_of",), {"attempt"}),
        ],
        "artifact": [
            (("target_refs",), {"target"}), (("environment_ref",), {"environment"}),
            (("escalation_confirmation_event_ref",), {"event"}), (("cleanup_obligation_ref",), {"event", "cleanup"}),
            (("supersedes_artifact_id",), {"artifact"}),
        ],
        "review": [
            (("entity_ref",), {"attempt", "finding", "artifact", "hypothesis", "candidate", "engagement"}),
            (("input_refs",), {"attempt", "finding", "artifact", "review", "environment"}),
            (("evidence_refs",), {"attempt", "artifact"}), (("conflicting_evidence",), {"attempt", "artifact"}),
        ],
        "engagement-event": [
            (("evidence_refs",), {"attempt", "artifact"}), (("review_refs",), {"review"}),
        ],
    }
    dynamic_specs: list[tuple[tuple[str, ...], Any, set[str]]] = []
    if schema_name == "finding-v3":
        claims = record.get("claims", {})
        for name in ("mechanism", "reachability"):
            dynamic_specs.append((("claims", name, "evidence_refs"), claims.get(name, {}).get("evidence_refs", []), {"attempt", "artifact"}))
        for index_number, impact in enumerate(claims.get("impact_claims", [])):
            dynamic_specs.append((("claims", "impact_claims", str(index_number), "evidence_refs"), impact.get("evidence_refs", []), {"attempt", "artifact"}))
        for index_number, mapping in enumerate(record.get("proof", {}).get("claim_proofs", [])):
            for field, allowed in (("attempt_refs", {"attempt"}), ("artifact_refs", {"artifact"}), ("control_refs", {"attempt"}), ("replay_refs", {"attempt"})):
                dynamic_specs.append((("proof", "claim_proofs", str(index_number), field), mapping.get(field, []), allowed))
        legacy = record.get("legacy_import")
        if isinstance(legacy, dict):
            dynamic_specs.append((("legacy_import", "source_artifact_ref"), legacy.get("source_artifact_ref"), {"artifact"}))
    elif schema_name == "review":
        for index_number, control in enumerate(record.get("control_applicability", [])):
            dynamic_specs.append((("control_applicability", str(index_number), "attempt_ref"), control.get("attempt_ref"), {"attempt"}))
        for index_number, disposition in enumerate(record.get("hypothesis_dispositions", [])):
            dynamic_specs.append((("hypothesis_dispositions", str(index_number), "hypothesis_ref"), disposition.get("hypothesis_ref"), {"hypothesis"}))

    errors: list[dict[str, Any]] = []
    combined = [(path, _at(record, path), allowed) for path, allowed in specs.get(schema_name, [])] + dynamic_specs
    for path, value, allowed in combined:
        refs = value if isinstance(value, list) else ([] if value is None else [value])
        for ref in refs:
            if not isinstance(ref, str):
                continue
            if ref == engagement_id and "engagement" in allowed:
                continue
            candidates = index.get(ref, [])
            same = [item for item in candidates if item.get("engagement_id") == engagement_id]
            if not candidates:
                code, message = "unresolved_record_ref", f"reference does not exist: {ref}"
            elif not same:
                code, message = "cross_engagement_ref", f"reference belongs to another engagement: {ref}"
            elif not any(item["type"] in allowed for item in same):
                code, message = "wrong_record_ref_type", f"reference {ref} is not one of {sorted(allowed)}"
            elif schema_name == "review" and path == ("entity_ref",) and record.get("finding_revision") is not None and any(item["type"] == "finding" for item in same) and not any(item["type"] == "finding" and item.get("revision") == record["finding_revision"] for item in same):
                code, message = "stale_finding_revision_ref", f"finding revision does not exist: {ref}@{record['finding_revision']}"
            else:
                continue
            errors.append({"code": code, "instance_path": "/" + "/".join(path), "schema_path": "/references", "message": message})
    return errors


def validate_record_with_references(record: Any, schema_name: str, engagement_dir: os.PathLike[str] | str) -> list[dict[str, Any]]:
    errors = validate_record(record, schema_name)
    if errors:
        return errors
    return validate_record_references(record, schema_name, build_reference_index(engagement_dir))


def validate_fixture_suite(path: Path | None = None) -> dict[str, Any]:
    path = path or ROOT / "fixtures" / "engagement-records" / "suite.json"
    suite = load_json(path)
    if not isinstance(suite, dict) or not isinstance(suite.get("cases"), list):
        raise RecordError("invalid_fixture_suite", f"fixture suite malformed: {path}")
    results = []
    failures = []
    for case in suite["cases"]:
        case_id = case.get("id", "unknown")
        errors = validate_record(case.get("record"), case.get("schema", ""))
        expected_valid = case.get("valid") is True
        passed = (not errors) == expected_valid
        result = {"id": case_id, "passed": passed, "error_codes": sorted({e["code"] for e in errors})}
        results.append(result)
        if not passed:
            failures.append(result)
    return {"case_count": len(results), "failures": failures, "results": results}


def validate_reference_fixture_suite(path: Path | None = None) -> dict[str, Any]:
    path = path or ROOT / "fixtures" / "engagement-records" / "reference-cases.json"
    suite = load_json(path)
    results = []
    failures = []
    for case in suite.get("cases", []):
        errors = validate_record_references(case.get("record"), case.get("schema", ""), case.get("index", {}))
        passed = (not errors) == (case.get("valid") is True)
        result = {"id": case.get("id", "unknown"), "passed": passed, "error_codes": sorted({error["code"] for error in errors})}
        results.append(result)
        if not passed:
            failures.append(result)
    return {"case_count": len(results), "failures": failures, "results": results}


def _legacy_violation_codes(record: Any, schema_errors: list[dict[str, Any]]) -> list[str]:
    codes: set[str] = set()
    if not isinstance(record, dict):
        return ["not_object"]
    if "base_model" in record:
        codes.add("forbidden_base_model")
    if record.get("scope_class") not in ("proxy_safe", "operator_only", "forbidden"):
        codes.add("unsupported_scope_class")
    if record.get("schema_version") != 2:
        codes.add("unexpected_schema_version")
    if schema_errors:
        codes.add("legacy_schema_invalid")
    return sorted(codes)


def legacy_finding_inventory(root: os.PathLike[str] | str) -> dict[str, Any]:
    """Read and hash local Plane-3 findings without modifying or importing them."""
    root_path = Path(root).resolve()
    engagement_root = root_path / "engagements"
    paths = sorted(
        path for path in engagement_root.glob("**/findings/**/*.json")
        if "_TEMPLATE" not in path.parts and path.is_file()
    )
    files: list[dict[str, Any]] = []
    counts = {
        "total": 0,
        "schema_version_2": 0,
        "forbidden_base_model": 0,
        "unsupported_scope_class": 0,
        "legacy_schema_invalid": 0,
        "parse_error": 0,
    }
    for path in paths:
        rel = path.relative_to(root_path).as_posix()
        item: dict[str, Any] = {"path": rel, "sha256": sha256_file(path), "size": path.stat().st_size}
        counts["total"] += 1
        try:
            record = load_json(path)
            errors = validate_record(record, "finding-v2-legacy")
            violations = _legacy_violation_codes(record, errors)
            if isinstance(record, dict) and record.get("schema_version") == 2:
                counts["schema_version_2"] += 1
            for key in ("forbidden_base_model", "unsupported_scope_class", "legacy_schema_invalid"):
                if key in violations:
                    counts[key] += 1
            item["schema_version"] = record.get("schema_version") if isinstance(record, dict) else None
            item["violations"] = violations
        except RecordError as exc:
            counts["parse_error"] += 1
            item["violations"] = ["parse_error"]
            item["error"] = exc.message
        files.append(item)
    corpus_material = b"".join(
        f"{item['path']}\0{item['sha256']}\0{item['size']}\n".encode("utf-8") for item in files
    )
    return {
        "schema_version": 1,
        "inventory_kind": "legacy_finding_read_only",
        "source_root_hash": sha256_bytes(corpus_material),
        "counts": counts,
        "files": files,
    }


def write_canonical_json(path: os.PathLike[str] | str, value: Any) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(canonical_json_bytes(value))


def summarize_errors(errors: Iterable[dict[str, Any]]) -> str:
    return "; ".join(f"{error['code']} {error.get('instance_path', '/')}: {error['message']}" for error in errors)
