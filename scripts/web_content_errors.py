#!/usr/bin/env python3
"""Catalog and validate fail-closed content-model diagnostics."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0.0"
SHA256 = re.compile(r"^[a-f0-9]{64}$")
DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
PATH = re.compile(r"^(?!/)(?!.*(?:^|/)\.\.(?:/|$)).+$")

ERROR_CATALOG: dict[str, dict[str, str]] = {
    "PAIR_SYMLINK": {"severity": "block", "description": "Symlink is broken or escapes the source root."},
    "PAIR_CASE_COLLISION": {"severity": "block", "description": "Portable case-folded paths collide."},
    "PAIR_AMBIGUOUS_HEADING": {"severity": "block", "description": "A story sidecar contains conflicting timestamps."},
    "PAIR_TIMESTAMP_MISSING": {"severity": "warn", "description": "No timestamp source could be resolved."},
    "PAIR_TIMESTAMP_COLLISION": {"severity": "block", "description": "Multiple images resolve to one timestamp."},
    "PAIR_ORPHAN_PROMPT": {"severity": "warn", "description": "An image has no exact prompt sidecar."},
    "PAIR_ORPHAN_STORY": {"severity": "warn", "description": "An image has no exact story sidecar."},
    "PAIR_ORPHAN_SIDECAR": {"severity": "warn", "description": "A prompt/story sidecar has no exact image."},
}


class ContentErrorRegistryError(ValueError):
    """An error catalog or exception registry is invalid."""


def validate_exception_registry(payload: Any) -> list[dict[str, str]]:
    if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
        raise ContentErrorRegistryError("unsupported content exception schema")
    exceptions = payload.get("exceptions")
    if not isinstance(exceptions, list):
        raise ContentErrorRegistryError("exceptions must be a list")
    seen: set[tuple[str, str]] = set()
    validated: list[dict[str, str]] = []
    for index, raw in enumerate(exceptions):
        if not isinstance(raw, dict) or set(raw) != {"code", "path", "sha256", "reason", "expires_on", "severity"}:
            raise ContentErrorRegistryError(f"exception {index} has unknown or missing fields")
        code = raw["code"]
        path = raw["path"]
        if code not in ERROR_CATALOG:
            raise ContentErrorRegistryError(f"unknown content error code: {code!r}")
        if not isinstance(path, str) or PATH.fullmatch(path) is None:
            raise ContentErrorRegistryError(f"exception {index} has an unsafe path")
        key = (code, path)
        if key in seen:
            raise ContentErrorRegistryError(f"duplicate exception: {code}:{path}")
        seen.add(key)
        if not isinstance(raw["sha256"], str) or SHA256.fullmatch(raw["sha256"]) is None:
            raise ContentErrorRegistryError(f"exception {index} requires a lowercase SHA-256")
        if not isinstance(raw["reason"], str) or not raw["reason"].strip():
            raise ContentErrorRegistryError(f"exception {index} requires a reason")
        if not isinstance(raw["expires_on"], str) or DATE.fullmatch(raw["expires_on"]) is None:
            raise ContentErrorRegistryError(f"exception {index} requires an ISO expiry date")
        severity = raw["severity"]
        if severity != ERROR_CATALOG[code]["severity"]:
            raise ContentErrorRegistryError(f"exception {index} severity disagrees with error catalog")
        validated.append({key: str(raw[key]) for key in ("code", "path", "sha256", "reason", "expires_on", "severity")})
    return validated


def load_exception_registry(path: Path) -> list[dict[str, str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContentErrorRegistryError(f"cannot read content exception registry {path}: {exc}") from exc
    return validate_exception_registry(payload)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, default=Path("config/web-content-exceptions.json"), nargs="?")
    args = parser.parse_args()
    try:
        entries = load_exception_registry(args.path)
    except ContentErrorRegistryError as exc:
        parser.exit(2, f"content exceptions rejected: {exc}\n")
    print(json.dumps({"schema_version": SCHEMA_VERSION, "exceptions": len(entries)}, sort_keys=True))
