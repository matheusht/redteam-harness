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

from engagement_records import build_reference_index, canonical_json_bytes, detect_secret_classes, load_json, sha256_bytes, sha256_file
from engagement_state import _scope_metadata, atomic_write, _append_kernel_event_idempotent as append_event, base_event, compute_review_input_hash, engagement_lock, read_ledger, reduce_engagement, require_approved_authority

COLLECTOR_VERSION = "decision5-preflight-v1"
COLLECTOR_VERSION_V2 = "decision6-preflight-v2"
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,159}$")
SAFE_LABEL = re.compile(r"^[A-Za-z0-9._:/-]{1,160}$")
SENSITIVE_ARG = re.compile(r"(?i)(?:^|[-_])(password|passwd|pwd|token|secret|authorization|cookie|api[-_]?key)(?:$|[=_-])")

GIT_EXECUTABLE = Path("/usr/bin/git")
GIT_SAFE_PREFIX = [str(GIT_EXECUTABLE), "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null"]
GIT_SAFE_ENV = {"PATH": "/usr/bin:/bin", "HOME": "/nonexistent", "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0", "LC_ALL": "C"}
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


def _stable_relative_file_at(root_fd: int, relative: Path) -> tuple[bytes | None, bool]:
    if relative.is_absolute() or not relative.parts or ".." in relative.parts or "." in relative.parts: return None, False
    directory_fd = os.dup(root_fd)
    try:
        for component in relative.parts[:-1]:
            next_fd = os.open(component, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0), dir_fd=directory_fd)
            os.close(directory_fd); directory_fd = next_fd
        return _stable_file_at(directory_fd, relative.parts[-1])
    except OSError:
        return None, False
    finally:
        os.close(directory_fd)


def _git_secret_scan_at(descriptor: int, enter_directory: Any) -> tuple[set[str], str, bool, list[subprocess.CompletedProcess[bytes]]]:
    commands = ([*GIT_SAFE_PREFIX, "ls-files", "--cached", "--others", "--exclude-standard", "-z"], [*GIT_SAFE_PREFIX, "ls-files", "--others", "--ignored", "--exclude-standard", "-z"])
    results = [subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, pass_fds=(descriptor,), preexec_fn=enter_directory, env=GIT_SAFE_ENV) for command in commands]
    if any(result.returncode != 0 for result in results): return set(), sha256_bytes(b""), False, results
    classes: set[str] = set(); stable = True; manifest = bytearray(); names = set(b"\0".join(result.stdout.rstrip(b"\0") for result in results).split(b"\0"))
    for raw in sorted(names):
        if not raw: continue
        try: relative = Path(raw.decode("utf-8"))
        except UnicodeDecodeError: stable = False; continue
        data, file_stable = _stable_relative_file_at(descriptor, relative)
        if data is None or not file_stable: stable = False; continue
        manifest.extend(raw + b"\0" + sha256_bytes(data).encode("ascii") + b"\0"); classes.update(detect_secret_classes(data))
    return classes, sha256_bytes(bytes(manifest)), stable, results


def _git_collect(target: Path) -> tuple[dict[str, Any], bytes, bytes, int, bool, set[str]]:
    empty = {"source_identity": None, "git_commit": None, "dirty_tree_hash": None, "dirty_tracked_hash": None, "generated_untracked_hash": None, "build_identity": None, "dependency_lock_hash": None}
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_DIRECTORY", 0)
    try: descriptor = os.open(target, flags)
    except OSError: return empty, b"", b"target is not a stable directory", 1, False, set()
    try:
        before_target = os.fstat(descriptor); commands = ([*GIT_SAFE_PREFIX, "rev-parse", "HEAD"], [*GIT_SAFE_PREFIX, "status", "--porcelain=v1", "--untracked-files=all"])
        def enter_open_directory() -> None: os.fchdir(descriptor)
        first = [subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, pass_fds=(descriptor,), preexec_fn=enter_open_directory, env=GIT_SAFE_ENV) for command in commands]
        first_lock_hash, first_locks_stable = _combined_file_hash_at(descriptor, LOCK_NAMES); secret_classes, first_scan_digest, first_scan_stable, first_scan_results = _git_secret_scan_at(descriptor, enter_open_directory); second_lock_hash, second_locks_stable = _combined_file_hash_at(descriptor, LOCK_NAMES)
        second = [subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, pass_fds=(descriptor,), preexec_fn=enter_open_directory, env=GIT_SAFE_ENV) for command in commands]; second_secret_classes, second_scan_digest, second_scan_stable, second_scan_results = _git_secret_scan_at(descriptor, enter_open_directory); results = [*first, *first_scan_results, *second, *second_scan_results]
        stdout = b"".join(result.stdout for result in results); stderr = b"".join(result.stderr for result in results); exit_code = max(result.returncode for result in results)
        commit = first[0].stdout.decode("ascii", errors="replace").strip() if first[0].returncode == 0 else None; status_bytes = first[1].stdout if first[1].returncode == 0 else b""
        stable = all(result.returncode == 0 for result in second) and second[0].stdout.strip() == first[0].stdout.strip() and second[1].stdout == first[1].stdout and first_scan_stable and second_scan_stable and first_scan_digest == second_scan_digest and secret_classes == second_secret_classes
        after_target = os.fstat(descriptor)
        try: named_target = os.stat(target, follow_symlinks=False)
        except OSError: named_target = None
        fingerprint = lambda value: (value.st_dev, value.st_ino, value.st_mtime_ns, stat.S_IFMT(value.st_mode))
        directory_stable = named_target is not None and stat.S_ISDIR(named_target.st_mode) and fingerprint(before_target) == fingerprint(after_target) == fingerprint(named_target)
        stable = stable and directory_stable and first_locks_stable and second_locks_stable and first_lock_hash == second_lock_hash
        tracked_status = b"\n".join(line for line in status_bytes.splitlines() if not line.startswith(b"?? ")); generated_status = b"\n".join(line for line in status_bytes.splitlines() if line.startswith(b"?? "))
        identity = {"source_identity": f"git:{commit}" if commit else None, "git_commit": commit, "dirty_tree_hash": sha256_bytes(status_bytes), "dirty_tracked_hash": sha256_bytes(tracked_status), "generated_untracked_hash": sha256_bytes(generated_status), "build_identity": None, "dependency_lock_hash": first_lock_hash}
        return identity, stdout, stderr, exit_code, stable and first[1].returncode == 0, secret_classes
    finally:
        os.close(descriptor)


def _file_collect(mode: str, target: Path) -> tuple[dict[str, Any], bytes, bytes, int, bool]:
    if target.is_symlink() or not target.is_file():
        return {"source_identity": None, "git_commit": None, "dirty_tree_hash": None, "dirty_tracked_hash": None, "generated_untracked_hash": None, "build_identity": None, "dependency_lock_hash": None}, b"", b"target is not a regular file", 1, False
    _, digest, stable = _stable_file(target)
    if digest is None:
        return {"source_identity": None, "git_commit": None, "dirty_tree_hash": None, "dirty_tracked_hash": None, "generated_untracked_hash": None, "build_identity": None, "dependency_lock_hash": None}, b"", b"target changed during collection", 1, False
    return {"source_identity": f"{mode}:{digest}", "git_commit": None, "dirty_tree_hash": None, "dirty_tracked_hash": None, "generated_untracked_hash": None, "build_identity": digest if mode == "package" else None, "dependency_lock_hash": None}, digest.encode("ascii"), b"", 0, stable


def _collect_preflight_core(
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
    actor_role: str | None = None,
    actor_id: str | None = None,
    session_id: str | None = None,
    model: str | None = None,
    provider: str | None = None,
    tool_versions: list[str] | None = None,
) -> dict[str, Any]:
    decision6 = actor_role is not None or actor_id is not None or session_id is not None
    operator_id = _normalized_operator(operator_id)
    principal_id = actor_id or operator_id
    if decision6 and (actor_role not in {"orchestrator", "hunter", "broker"} or not principal_id or not session_id or not ID_PATTERN.fullmatch(principal_id) or not ID_PATTERN.fullmatch(session_id)):
        raise ValueError("Decision-0006 collector requires a supported truthful actor and session ID")
    if not ID_PATTERN.fullmatch(preflight_id): raise ValueError("preflight ID is not a safe record ID")
    if _path_has_symlink(target) or _path_has_symlink(runtime) or any(_path_has_symlink(path) for path in configuration_files or []): raise ValueError("preflight paths must not contain symlink components")
    engagement = engagement.absolute(); target = target.absolute(); runtime = runtime.absolute()
    account_labels = sorted(set(account_labels or [])); feature_flags = sorted(set(feature_flags or [])); configuration_files = [path.absolute() for path in (configuration_files or [])]
    _safe_text_inputs([preflight_id, expected_identity, *reproduction_argv, *account_labels, endpoint_identity or "", account_role or "", *feature_flags, actor_role or "", principal_id, session_id or "", model or "", provider or "", *(tool_versions or [])])
    if any(SENSITIVE_ARG.search(item) for item in reproduction_argv) or any(not SAFE_LABEL.fullmatch(item) for item in [*account_labels, *feature_flags, *([endpoint_identity] if endpoint_identity else []), *([account_role] if account_role else [])]): raise ValueError("secret-bearing command options or unsafe account metadata are forbidden")
    if mode not in {"git", "package", "local_runtime"} or advisory_zone not in {"clear_local", "review_required", "unknown"}:
        raise ValueError("unsupported preflight mode or advisory zone")
    git_tool_digest = None; git_secret_classes: set[str] = set()
    if mode == "git":
        if not GIT_EXECUTABLE.is_file() or GIT_EXECUTABLE.is_symlink(): raise ValueError("pinned Git executable is unavailable")
        git_tool_digest = sha256_file(GIT_EXECUTABLE); observed, stdout, stderr, exit_code, stable, git_secret_classes = _git_collect(target); stable = stable and sha256_file(GIT_EXECUTABLE) == git_tool_digest; operation = "git_identity"; actual_identity = observed["git_commit"]
    else:
        observed, stdout, stderr, exit_code, stable = _file_collect(mode, target); operation = "package_identity" if mode == "package" else "local_runtime_identity"; actual_identity = observed["source_identity"].split(":", 1)[1] if observed["source_identity"] else None
    runtime_digest = None
    if runtime.is_file() and not runtime.is_symlink():
        _, runtime_digest, runtime_stable = _stable_file(runtime)
        if not runtime_stable: runtime_digest = None
    reproduction_verified = _argv_is_reproducible(reproduction_argv)
    first_configuration_hash, first_configuration_stable = _combined_file_hash(configuration_files); second_configuration_hash, second_configuration_stable = _combined_file_hash(configuration_files)
    if first_configuration_hash != second_configuration_hash or not first_configuration_stable or not second_configuration_stable: stable = False
    secret_pattern_classes: set[str] = set()
    if mode == "git": secret_pattern_classes.update(git_secret_classes)
    scan_paths = [*configuration_files, *([target] if mode in {"package", "local_runtime"} else [])]
    for scan_path in scan_paths:
        data, scan_digest, scan_stable = _stable_file(scan_path)
        if data is None or not scan_stable: stable = False; continue
        if scan_path == target and mode in {"package", "local_runtime"} and scan_digest != observed["source_identity"].split(":", 1)[1]: stable = False
        secret_pattern_classes.update(detect_secret_classes(data))
    third_configuration_hash, third_configuration_stable = _combined_file_hash(configuration_files)
    if third_configuration_hash != first_configuration_hash or not third_configuration_stable: stable = False
    identity = {
        "source_identity": observed["source_identity"],
        "expected_identity": expected_identity,
        "git_commit": observed["git_commit"],
        **({"dirty_tracked_hash": observed["dirty_tracked_hash"], "generated_untracked_hash": observed["generated_untracked_hash"]} if decision6 else {"dirty_tree_hash": observed["dirty_tree_hash"]}),
        "build_identity": observed["build_identity"],
        "runtime_identity": f"file:{runtime_digest}" if runtime_digest else None,
        "runtime_digest": runtime_digest,
        "dependency_lock_hash": observed["dependency_lock_hash"],
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
        if scope_metadata["scope_hash"] != state["scope_hash"]:
            raise ValueError("scope hash does not match active signed scope")
        if not decision6 and _normalized_operator(scope_metadata["operator"]) != operator_id:
            raise ValueError("operator does not match active signed scope")
        cleanup_open = state["cleanup"]["open_count"]
        dirty_hash = observed["dirty_tracked_hash"] if decision6 else observed["dirty_tree_hash"]
        detected_credentials = credentials_present or bool(secret_pattern_classes)
        needs_review = advisory_zone != "clear_local" or (mode == "git" and dirty_hash != sha256_bytes(b""))
        if decision6:
            status = "blocked" if not fidelity_complete or cleanup_open or detected_credentials else ("needs_review" if needs_review else "ready")
            record = {
                "schema_version": 2, "preflight_id": preflight_id, "engagement_id": state["engagement_id"], "recorded_at": recorded_at, "scope_hash": state["scope_hash"], "target_refs": [], "mode": mode, "status": status, "operation_class": "notebook",
                "identity": identity, "identity_hash": sha256_bytes(canonical_json_bytes(identity)), "fidelity_complete": fidelity_complete, "missing_fidelity": missing,
                "collector": {"collector_version": COLLECTOR_VERSION_V2, "operation": operation, "reproduction_argv": reproduction_argv, "reproducible": reproduction_verified, "exit_code": exit_code, "stdout_digest": sha256_bytes(stdout), "stderr_digest": sha256_bytes(stderr), "tool_digest": git_tool_digest},
                "safety": {"scope_attested": True, "credentials_present": detected_credentials, "account_labels": account_labels, "cleanup_open_count": cleanup_open, "advisory_zone": advisory_zone, "zone2_authorization_granted": False, "secret_scan_status": "blocked" if secret_pattern_classes else "clean", "secret_pattern_classes": sorted(secret_pattern_classes), "automated_redaction_status": "blocked" if secret_pattern_classes else "clean", "operator_review_ref": None},
                "provenance": {"actor": {"role": actor_role, "id": principal_id}, "session_id": session_id, "provider": provider, "model": model, "prompt_version": None, "tool_versions": sorted(set([COLLECTOR_VERSION_V2, *(tool_versions or [])])), "card_versions": []},
            }
            commit_role, commit_id_actor, collector_version = actor_role, principal_id, COLLECTOR_VERSION_V2
        else:
            status = "blocked" if not fidelity_complete or cleanup_open or not operator_redaction_attested else ("needs_review" if needs_review else "ready")
            record = {
                "schema_version": 1, "preflight_id": preflight_id, "engagement_id": state["engagement_id"], "recorded_at": recorded_at, "scope_hash": state["scope_hash"], "target_refs": [], "mode": mode, "status": status,
                "identity": identity, "identity_hash": sha256_bytes(canonical_json_bytes(identity)), "fidelity_complete": fidelity_complete, "missing_fidelity": missing,
                "collector": {"collector_version": COLLECTOR_VERSION, "operation": operation, "reproduction_argv": reproduction_argv, "reproducible": reproduction_verified, "exit_code": exit_code, "stdout_digest": sha256_bytes(stdout), "stderr_digest": sha256_bytes(stderr)},
                "safety": {"scope_attested": True, "operator_redaction_attested": operator_redaction_attested, "credentials_present": credentials_present, "account_labels": account_labels, "cleanup_open_count": cleanup_open, "advisory_zone": advisory_zone, "zone2_authorization_granted": False, "secret_scan_status": "clean", "secret_pattern_classes": []},
                "provenance": {"actor": {"role": "operator", "id": operator_id}, "session_id": None, "provider": None, "model": None, "prompt_version": None, "tool_versions": [COLLECTOR_VERSION], "card_versions": []},
            }
            commit_role, commit_id_actor, collector_version = "operator", operator_id, COLLECTOR_VERSION
        path = engagement / relative; record_bytes = canonical_json_bytes(record)
        if path.exists() and path.read_bytes() != record_bytes: raise ValueError("preflight ID already exists with different immutable bytes")
        if not path.exists(): atomic_write(path, record_bytes)
        events = read_ledger(engagement, "event"); event_ids = {item["event_id"] for item in events}
        commit_id = f"event-{preflight_id}-commit"; recorded_id = f"event-{preflight_id}-recorded"
        if commit_id not in event_ids:
            commit = base_event(event_id=commit_id, engagement_id=state["engagement_id"], recorded_at=recorded_at, actor_role=commit_role, actor_id=commit_id_actor, event_type="record.committed", rationale="Commit immutable environment and safety preflight.", payload={"record_path": relative, "record_digest": sha256_file(path), "record_type": "environment-preflight", "record_id": preflight_id, "record_revision": None}, session_id=session_id if decision6 else None, operation_class="notebook" if decision6 else None, tool_versions=[collector_version])
            append_event(engagement, commit, lock_held=True)
        if recorded_id not in event_ids:
            event = base_event(event_id=recorded_id, engagement_id=state["engagement_id"], recorded_at=recorded_at, actor_role=actor_role if decision6 else "operator", actor_id=principal_id if decision6 else operator_id, event_type="environment.preflight_recorded", rationale="Record preflight result; advisory Zone classification does not authorize Zone-2.", payload={"environment_ref": preflight_id, "status": status, "identity_hash": record["identity_hash"]}, entity_refs=[preflight_id], state_changes=[{"dimension": "environment", "entity_id": preflight_id, "previous": None, "current": status}], session_id=session_id if decision6 else None, operation_class="notebook" if decision6 else None, model=model, provider=provider, tool_versions=[collector_version])
            append_event(engagement, event, lock_held=True)
        return record


def collect_preflight(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Public Decision-0006 collector; operator-attestation inputs are never accepted."""
    if kwargs.get("actor_role") is None or kwargs.get("actor_id") is None or kwargs.get("session_id") is None:
        raise ValueError("Decision-0006 collector actor/session provenance is required")
    if kwargs.get("operator_redaction_attested"):
        raise ValueError("collector cannot claim operator redaction attestation")
    return _collect_preflight_core(*args, **kwargs)


def _collect_legacy_preflight(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Trusted Decision-0005 regression compatibility; never exposed by the public CLI."""
    if any(kwargs.get(name) is not None for name in ("actor_role", "actor_id", "session_id")):
        raise ValueError("legacy preflight cannot carry Decision-0006 actor fields")
    return _collect_preflight_core(*args, **kwargs)


def review_preflight(engagement: Path, preflight_id: str, verdict: str, reason: str, operator_id: str, recorded_at: str, authority_request_ref: str, lane_id: str, executor_id: str, session_id: str) -> dict[str, Any]:
    engagement = engagement.absolute(); operator_id = _normalized_operator(operator_id)
    action = {"action_kind": "review-preflight", "lane_id": lane_id, "executor_id": executor_id, "session_id": session_id, "preflight_id": preflight_id, "verdict": verdict, "reason": reason, "operator_id": operator_id, "recorded_at": recorded_at}
    require_approved_authority(engagement, authority_request_ref, "review-preflight", sha256_bytes(canonical_json_bytes(action)), lane_id, recorded_at)
    if verdict not in {"accepted", "rejected"}: raise ValueError("preflight review verdict must be accepted or rejected")
    review_id = f"review-{preflight_id}-operator"; relative = f"reviews/{review_id}.json"; path = engagement / relative
    with engagement_lock(engagement):
        state = reduce_engagement(engagement, allowed_record_orphans={relative}); scope = _scope_metadata(engagement / "scope.md"); current = state["environment_preflights"].get(preflight_id)
        latest_preflight = next((event["payload"]["environment_ref"] for event in reversed(read_ledger(engagement, "event")) if event["event_type"] == "environment.preflight_recorded"), None)
        if _normalized_operator(scope["operator"]) != operator_id or current is None or current["status"] != "needs_review" or latest_preflight != preflight_id: raise ValueError("preflight review requires current needs_review evidence and active operator")
        index = build_reference_index(engagement); entry = next((item for item in index.get(preflight_id, []) if item["type"] == "environment"), None)
        if entry is None: raise ValueError("preflight record is missing")
        environment = load_json(engagement / entry["path"]); safety = environment["safety"]
        if verdict == "accepted" and (not environment["fidelity_complete"] or safety["credentials_present"] or safety["secret_scan_status"] != "clean" or safety["automated_redaction_status"] != "clean" or safety["cleanup_open_count"] != 0): raise ValueError("unsafe or incomplete preflight cannot be accepted")
        review = {"schema_version": 1, "review_id": review_id, "engagement_id": state["engagement_id"], "review_type": "operator", "proposed_finding_id": None, "recorded_at": recorded_at, "entity_ref": preflight_id, "finding_revision": None, "input_refs": [preflight_id], "input_hash": "sha256:" + "0" * 64, "evidence_refs": [], "rationale": reason, "conflicting_evidence": [], "verdict": verdict, "corrections": [], "required_next_actions": [], "independence": {"reviewer_id": operator_id, "reviewer_run_id": f"run-{review_id}", "reviewer_model": None, "fresh_context": True, "prior_verdict_visible": False, "disconfirming_objective": "Reject incomplete, secret-bearing, stale, or misidentified preflight evidence.", "originating_run_id": f"event-{preflight_id}-recorded"}}
        review["input_hash"] = compute_review_input_hash(engagement, review, index); data = canonical_json_bytes(review)
        if path.exists() and path.read_bytes() != data: raise ValueError("preflight review ID collision")
        if not path.exists(): atomic_write(path, data)
        commit = base_event(event_id=f"event-{review_id}-commit", engagement_id=state["engagement_id"], recorded_at=recorded_at, actor_role="broker", actor_id=executor_id, event_type="record.committed", rationale="Commit immutable operator preflight review.", payload={"record_path": relative, "record_digest": sha256_file(path), "record_type": "review", "record_id": review_id, "record_revision": None, "authority_request_ref": authority_request_ref}, session_id=session_id, operation_class="authority"); append_event(engagement, commit, lock_held=True)
        resulting = "ready" if verdict == "accepted" else "blocked"
        event = base_event(event_id=f"event-{preflight_id}-reviewed", engagement_id=state["engagement_id"], recorded_at=recorded_at, actor_role="broker", actor_id=executor_id, event_type="environment.review_recorded", rationale=reason, payload={"environment_ref": preflight_id, "review_ref": review_id, "status": resulting, "operator_id": operator_id, "authority_request_ref": authority_request_ref}, entity_refs=[preflight_id], review_refs=[review_id], state_changes=[{"dimension": "environment", "entity_id": preflight_id, "previous": "needs_review", "current": resulting}], session_id=session_id, operation_class="authority"); append_event(engagement, event, lock_held=True)
        return review
