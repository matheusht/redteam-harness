#!/usr/bin/env python3
"""Offline environment identity collectors and safety preflight for Decision 0005."""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
from pathlib import Path
from typing import Any

from engagement_records import canonical_json_bytes, detect_secret_classes, sha256_bytes, sha256_file
from engagement_state import _scope_metadata, atomic_write, append_event, base_event, engagement_lock, read_ledger, reduce_engagement

COLLECTOR_VERSION = "decision5-preflight-v1"
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,159}$")
SAFE_LABEL = re.compile(r"^[A-Za-z0-9._:/-]{1,160}$")
SENSITIVE_ARG = re.compile(r"(?i)(?:^|[-_])(password|passwd|pwd|token|secret|authorization|cookie|api[-_]?key)(?:$|[=_-])")

LOCK_NAMES = ("package-lock.json", "pnpm-lock.yaml", "yarn.lock", "poetry.lock", "Pipfile.lock", "requirements.txt", "requirements-ci.txt", "Cargo.lock", "go.sum")


def _path_has_symlink(path: Path) -> bool:
    # Parent aliases do not cross a containment boundary here; the resolved target bytes are hashed.
    # The terminal object itself must not be a replaceable symlink.
    return path.is_symlink()


def _normalized_operator(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._:-]+", "-", value).strip("-") or "operator"


def _argv_is_reproducible(argv: list[str]) -> bool:
    if not argv or not all(isinstance(item, str) and item and "\x00" not in item and "\n" not in item for item in argv): return False
    executable = Path(argv[0])
    return executable.is_absolute() and not _path_has_symlink(executable) and executable.is_file() and os.access(executable, os.X_OK)


def _stable_file(path: Path) -> tuple[bytes | None, str | None, bool]:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError:
        return None, None, False
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode): return None, None, False
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk: break
            chunks.append(chunk)
        after = os.fstat(descriptor); named = os.stat(path, follow_symlinks=False)
        fingerprint = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, stat.S_IFMT(value.st_mode))
        data = b"".join(chunks); stable = fingerprint(before) == fingerprint(after) == fingerprint(named) and stat.S_ISREG(named.st_mode)
        return data, "sha256:" + hashlib.sha256(data).hexdigest(), stable
    except OSError:
        return None, None, False
    finally:
        os.close(descriptor)


def _stable_file_at(directory_fd: int, name: str) -> tuple[bytes | None, bool]:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try: descriptor = os.open(name, flags, dir_fd=directory_fd)
    except FileNotFoundError: return None, True
    except OSError: return None, False
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode): return None, False
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk: break
            chunks.append(chunk)
        after = os.fstat(descriptor); named = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        fingerprint = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, stat.S_IFMT(value.st_mode))
        return b"".join(chunks), fingerprint(before) == fingerprint(after) == fingerprint(named) and stat.S_ISREG(named.st_mode)
    except OSError:
        return None, False
    finally:
        os.close(descriptor)


def _combined_file_hash_at(directory_fd: int, names: tuple[str, ...]) -> tuple[str | None, bool]:
    payload = bytearray(); found = False; stable = True
    for name in sorted(names):
        data, file_stable = _stable_file_at(directory_fd, name); stable = stable and file_stable
        if data is None: continue
        found = True; payload.extend(name.encode("utf-8") + b"\0" + data + b"\0")
    return (sha256_bytes(bytes(payload)) if found else None), stable


def _combined_file_hash(paths: list[Path]) -> tuple[str | None, bool]:
    existing = sorted(paths, key=lambda path: path.name)
    if not existing: return None, True
    payload = bytearray(); found = False; stable = True
    for path in existing:
        if not path.exists(): continue
        data, _, file_stable = _stable_file(path); stable = stable and file_stable
        if data is None: continue
        found = True; payload.extend(path.name.encode("utf-8") + b"\0" + data + b"\0")
    return (sha256_bytes(bytes(payload)) if found else None), stable


def _safe_text_inputs(values: list[str]) -> None:
    classes = detect_secret_classes("\n".join(values).encode("utf-8", errors="replace"))
    if classes:
        raise ValueError("secret-shaped input rejected: " + ",".join(classes))


def _git_collect(target: Path) -> tuple[dict[str, Any], bytes, bytes, int, bool]:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_DIRECTORY", 0)
    try: descriptor = os.open(target, flags)
    except OSError:
        return {"source_identity": None, "git_commit": None, "dirty_tree_hash": None, "build_identity": None, "dependency_lock_hash": None}, b"", b"target is not a stable directory", 1, False
    try:
        before_target = os.fstat(descriptor)
        commands = (["git", "rev-parse", "HEAD"], ["git", "status", "--porcelain=v1", "--untracked-files=all"])
        def enter_open_directory() -> None: os.fchdir(descriptor)
        results = [subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, pass_fds=(descriptor,), preexec_fn=enter_open_directory) for command in (*commands, *commands)]
        stdout = b"".join(result.stdout for result in results); stderr = b"".join(result.stderr for result in results); exit_code = max(result.returncode for result in results)
        commit = results[0].stdout.decode("ascii", errors="replace").strip() if results[0].returncode == 0 else None; status_bytes = results[1].stdout if results[1].returncode == 0 else b""
        stable = results[2].returncode == 0 and results[3].returncode == 0 and results[2].stdout.strip() == results[0].stdout.strip() and results[3].stdout == results[1].stdout
        first_lock_hash, first_locks_stable = _combined_file_hash_at(descriptor, LOCK_NAMES); second_lock_hash, second_locks_stable = _combined_file_hash_at(descriptor, LOCK_NAMES)
        after_target = os.fstat(descriptor)
        try: named_target = os.stat(target, follow_symlinks=False)
        except OSError: named_target = None
        fingerprint = lambda value: (value.st_dev, value.st_ino, value.st_mtime_ns, stat.S_IFMT(value.st_mode))
        directory_stable = named_target is not None and stat.S_ISDIR(named_target.st_mode) and fingerprint(before_target) == fingerprint(after_target) == fingerprint(named_target)
        stable = stable and directory_stable and first_locks_stable and second_locks_stable and first_lock_hash == second_lock_hash
        identity = {"source_identity": f"git:{commit}" if commit else None, "git_commit": commit, "dirty_tree_hash": sha256_bytes(status_bytes), "build_identity": None, "dependency_lock_hash": first_lock_hash}
        return identity, stdout, stderr, exit_code, stable and results[1].returncode == 0
    finally:
        os.close(descriptor)


def _file_collect(mode: str, target: Path) -> tuple[dict[str, Any], bytes, bytes, int, bool]:
    if target.is_symlink() or not target.is_file():
        return {"source_identity": None, "git_commit": None, "dirty_tree_hash": None, "build_identity": None, "dependency_lock_hash": None}, b"", b"target is not a regular file", 1, False
    _, digest, stable = _stable_file(target)
    if digest is None:
        return {"source_identity": None, "git_commit": None, "dirty_tree_hash": None, "build_identity": None, "dependency_lock_hash": None}, b"", b"target changed during collection", 1, False
    return {"source_identity": f"{mode}:{digest}", "git_commit": None, "dirty_tree_hash": None, "build_identity": digest if mode == "package" else None, "dependency_lock_hash": None}, digest.encode("ascii"), b"", 0, stable


def collect_preflight(
    engagement: Path,
    *,
    preflight_id: str,
    mode: str,
    target: Path,
    expected_identity: str,
    runtime: Path,
    reproduction_argv: list[str],
    operator_id: str,
    recorded_at: str,
    operator_redaction_attested: bool = False,
    advisory_zone: str = "clear_local",
    credentials_present: bool = False,
    account_labels: list[str] | None = None,
    configuration_files: list[Path] | None = None,
    endpoint_identity: str | None = None,
    account_role: str | None = None,
    feature_flags: list[str] | None = None,
) -> dict[str, Any]:
    operator_id = _normalized_operator(operator_id)
    if not ID_PATTERN.fullmatch(preflight_id): raise ValueError("preflight ID is not a safe record ID")
    if _path_has_symlink(target) or _path_has_symlink(runtime) or any(_path_has_symlink(path) for path in configuration_files or []): raise ValueError("preflight paths must not contain symlink components")
    engagement = engagement.resolve(); target = target.absolute(); runtime = runtime.absolute()
    account_labels = sorted(set(account_labels or [])); feature_flags = sorted(set(feature_flags or [])); configuration_files = [path.absolute() for path in (configuration_files or [])]
    _safe_text_inputs([preflight_id, expected_identity, *reproduction_argv, *account_labels, endpoint_identity or "", account_role or "", *feature_flags])
    if any(SENSITIVE_ARG.search(item) for item in reproduction_argv) or any(not SAFE_LABEL.fullmatch(item) for item in [*account_labels, *feature_flags, *([endpoint_identity] if endpoint_identity else []), *([account_role] if account_role else [])]): raise ValueError("secret-bearing command options or unsafe account metadata are forbidden")
    if mode not in {"git", "package", "local_runtime"} or advisory_zone not in {"clear_local", "review_required", "unknown"}:
        raise ValueError("unsupported preflight mode or advisory zone")
    if mode == "git": observed, stdout, stderr, exit_code, stable = _git_collect(target); operation = "git_identity"; actual_identity = observed["git_commit"]
    else:
        observed, stdout, stderr, exit_code, stable = _file_collect(mode, target); operation = "package_identity" if mode == "package" else "local_runtime_identity"; actual_identity = observed["source_identity"].split(":", 1)[1] if observed["source_identity"] else None
    runtime_digest = None
    if runtime.is_file() and not runtime.is_symlink():
        _, runtime_digest, runtime_stable = _stable_file(runtime)
        if not runtime_stable: runtime_digest = None
    reproduction_verified = _argv_is_reproducible(reproduction_argv)
    first_configuration_hash, first_configuration_stable = _combined_file_hash(configuration_files); second_configuration_hash, second_configuration_stable = _combined_file_hash(configuration_files)
    if first_configuration_hash != second_configuration_hash or not first_configuration_stable or not second_configuration_stable: stable = False
    identity = {
        **observed,
        "expected_identity": expected_identity,
        "runtime_identity": f"file:{runtime_digest}" if runtime_digest else None,
        "runtime_digest": runtime_digest,
        "configuration_hash": first_configuration_hash,
        "endpoint_identity": endpoint_identity,
        "account_role": account_role,
        "feature_flags": feature_flags,
    }
    missing: list[dict[str, str]] = []
    if exit_code != 0 or actual_identity is None: missing.append({"field": "target_identity", "reason": "collector could not establish target identity"})
    elif actual_identity.removeprefix("sha256:") != expected_identity.removeprefix("sha256:"): missing.append({"field": "expected_identity", "reason": "observed target identity differs from expected identity"})
    if not stable: missing.append({"field": "target_stability", "reason": "target identity changed or could not be read stably during collection"})
    if runtime_digest is None: missing.append({"field": "runtime_identity", "reason": "runtime must be a regular non-symlink file"})
    if any(not path.is_file() or path.is_symlink() for path in configuration_files): missing.append({"field": "configuration_hash", "reason": "every requested configuration file must be a regular non-symlink file"})
    if not reproduction_verified: missing.append({"field": "reproduction_argv", "reason": "argv[0] must be an absolute, executable, non-symlink regular file and argv must be exact"})
    fidelity_complete = not missing; relative = f"environment/preflight-{preflight_id}.json"
    with engagement_lock(engagement):
        state = reduce_engagement(engagement, allowed_record_orphans={relative})
        scope_metadata = _scope_metadata(engagement / "scope.md")
        if _normalized_operator(scope_metadata["operator"]) != operator_id or scope_metadata["scope_hash"] != state["scope_hash"]:
            raise ValueError("operator or scope hash does not match active signed scope")
        cleanup_open = state["cleanup"]["open_count"]
        needs_review = advisory_zone != "clear_local" or (mode == "git" and observed["dirty_tree_hash"] != sha256_bytes(b""))
        status = "blocked" if not fidelity_complete or cleanup_open or not operator_redaction_attested else ("needs_review" if needs_review else "ready")
        record = {
            "schema_version": 1, "preflight_id": preflight_id, "engagement_id": state["engagement_id"], "recorded_at": recorded_at, "scope_hash": state["scope_hash"], "target_refs": [], "mode": mode, "status": status,
            "identity": identity, "identity_hash": sha256_bytes(canonical_json_bytes(identity)), "fidelity_complete": fidelity_complete, "missing_fidelity": missing,
            "collector": {"collector_version": COLLECTOR_VERSION, "operation": operation, "reproduction_argv": reproduction_argv, "reproducible": reproduction_verified, "exit_code": exit_code, "stdout_digest": sha256_bytes(stdout), "stderr_digest": sha256_bytes(stderr)},
            "safety": {"scope_attested": True, "operator_redaction_attested": operator_redaction_attested, "credentials_present": credentials_present, "account_labels": account_labels, "cleanup_open_count": cleanup_open, "advisory_zone": advisory_zone, "zone2_authorization_granted": False, "secret_scan_status": "clean", "secret_pattern_classes": []},
            "provenance": {"actor": {"role": "operator", "id": operator_id}, "provider": None, "model": None, "prompt_version": None, "tool_versions": [COLLECTOR_VERSION], "card_versions": []},
        }
        path = engagement / relative; record_bytes = canonical_json_bytes(record)
        if path.exists() and path.read_bytes() != record_bytes: raise ValueError("preflight ID already exists with different immutable bytes")
        if not path.exists(): atomic_write(path, record_bytes)
        events = read_ledger(engagement, "event"); event_ids = {item["event_id"] for item in events}
        commit_id = f"event-{preflight_id}-commit"; recorded_id = f"event-{preflight_id}-recorded"
        if commit_id not in event_ids:
            commit = base_event(event_id=commit_id, engagement_id=state["engagement_id"], recorded_at=recorded_at, actor_role="operator", actor_id=operator_id, event_type="record.committed", rationale="Commit immutable environment and safety preflight.", payload={"record_path": relative, "record_digest": sha256_file(path), "record_type": "environment-preflight", "record_id": preflight_id, "record_revision": None})
            append_event(engagement, commit, lock_held=True)
        if recorded_id not in event_ids:
            event = base_event(event_id=recorded_id, engagement_id=state["engagement_id"], recorded_at=recorded_at, actor_role="operator", actor_id=operator_id, event_type="environment.preflight_recorded", rationale="Record preflight result; advisory Zone classification does not authorize Zone-2.", payload={"environment_ref": preflight_id, "status": status, "identity_hash": record["identity_hash"]}, entity_refs=[preflight_id])
            append_event(engagement, event, lock_held=True)
        return record
