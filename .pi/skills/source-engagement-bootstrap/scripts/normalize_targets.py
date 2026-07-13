#!/usr/bin/env python3
"""Normalize a source-engagement CSV/TSV intake without network access."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

SOURCE_KEYS = (
    "repository_url", "repo_url", "repository", "repo", "source_url",
    "source_path", "local_path", "source", "github", "gitlab",
)
NAME_KEYS = ("target_name", "target", "name", "asset", "project")
REVISION_KEYS = ("commit", "tag", "branch", "version", "release", "revision")
REPO_HOSTS = {"github.com", "gitlab.com", "bitbucket.org", "codeberg.org"}


def normalized_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def first(record: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = record.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def source_kind(locator: str, input_dir: Path) -> tuple[str | None, str | None]:
    candidate = Path(locator).expanduser()
    if not candidate.is_absolute():
        candidate = input_dir / candidate
    if candidate.is_dir():
        return "local_source_tree", str(candidate.resolve())
    match = re.match(r"^(?:https?://|ssh://|git@)(?:[^@/]+@)?([^/:]+)", locator)
    if match and match.group(1).lower() in REPO_HOSTS:
        return "repository_url", locator
    if re.match(r"^[\w.-]+/[\w.-]+(?:\.git)?$", locator):
        return "repository_slug", locator
    return None, None


def read_rows(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = data.get("targets", data.get("entries"))
        if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
            raise ValueError("JSON intake must be an array of objects or {targets:[...]} object")
        return data
    delimiter = "\t" if suffix == ".tsv" else ","
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def normalize(path: Path) -> dict[str, Any]:
    rows = read_rows(path)
    entries = []
    for number, raw in enumerate(rows, 2):
        record = {normalized_key(str(key)): value for key, value in raw.items() if key is not None}
        locator = first(record, SOURCE_KEYS)
        name = first(record, NAME_KEYS) or locator or f"row-{number}"
        revision = first(record, REVISION_KEYS)
        kind = resolved = None
        reasons = []
        if locator:
            kind, resolved = source_kind(locator, path.parent)
        if not locator:
            reasons.append("missing source repository/local source path")
        elif kind is None:
            reasons.append("locator is not a recognized source repository or existing local source tree")
        status = "eligible_for_review" if not reasons else "rejected"
        entries.append({
            "row": number,
            "name": name,
            "status": status,
            "source_kind": kind,
            "source_locator": resolved,
            "revision_supplied": revision,
            "identity_status": "declared_unverified" if revision else "missing",
            "reasons": reasons,
            "input": record,
        })
    return {
        "input": str(path.resolve()),
        "source_only": True,
        "network_access": False,
        "entry_count": len(entries),
        "eligible_for_review": sum(item["status"] == "eligible_for_review" for item in entries),
        "entries": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not args.input.is_file():
        parser.error(f"input does not exist: {args.input}")
    try:
        result = normalize(args.input)
    except (ValueError, json.JSONDecodeError, csv.Error) as exc:
        parser.error(str(exc))
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
