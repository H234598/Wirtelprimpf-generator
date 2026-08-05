#!/usr/bin/env python3
"""Validate and resolve stable web IDs and their explicit alias register."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0.0"
IMAGE_ID = re.compile(r"^(?:archive|hub)-[0-9]{4}-[a-f0-9]{16}-[a-f0-9]{8}$")
VOLUME_ID = re.compile(r"^band-[0-9]{4}$")
CHAPTER_ID = re.compile(r"^band-[0-9]{4}-teil-[a-f0-9]{12}$")
SHA256 = re.compile(r"^[a-f0-9]{64}$")
KINDS = {"image", "volume", "chapter"}


class WebIdError(ValueError):
    """A stable ID or alias register is invalid."""


def normalize_id(kind: str, value: str) -> str:
    if kind not in KINDS:
        raise WebIdError(f"unknown web ID kind: {kind}")
    if not isinstance(value, str):
        raise WebIdError("web ID must be a string")
    normalized = value.strip().lower()
    pattern = {"image": IMAGE_ID, "volume": VOLUME_ID, "chapter": CHAPTER_ID}[kind]
    if pattern.fullmatch(normalized) is None:
        raise WebIdError(f"invalid {kind} ID: {value!r}")
    return normalized


def id_kind(value: str) -> str:
    normalized = value.strip().lower() if isinstance(value, str) else ""
    if IMAGE_ID.fullmatch(normalized):
        return "image"
    if CHAPTER_ID.fullmatch(normalized):
        return "chapter"
    if VOLUME_ID.fullmatch(normalized):
        return "volume"
    raise WebIdError(f"unrecognized web ID: {value!r}")


def chapter_id(volume: int, timestamp: str, markdown: str) -> str:
    if not isinstance(volume, int) or isinstance(volume, bool) or volume < 1:
        raise WebIdError(f"invalid chapter volume: {volume!r}")
    if not isinstance(timestamp, str) or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}", timestamp) is None:
        raise WebIdError("invalid chapter timestamp")
    if not isinstance(markdown, str):
        raise WebIdError("chapter markdown must be a string")
    digest = hashlib.sha256(f"{volume}\0{timestamp}\0{markdown}".encode("utf-8")).hexdigest()[:12]
    return f"band-{volume:04d}-teil-{digest}"


def validate_aliases(payload: Any) -> dict[str, str]:
    if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
        raise WebIdError("unsupported alias register schema")
    aliases = payload.get("aliases")
    if not isinstance(aliases, list):
        raise WebIdError("alias register must contain an aliases list")
    targets: dict[str, str] = {}
    for index, raw in enumerate(aliases):
        if not isinstance(raw, dict):
            raise WebIdError(f"alias {index} must be an object")
        if set(raw) != {"kind", "old_id", "new_id", "source_sha256", "reason"}:
            raise WebIdError(f"alias {index} has unknown or missing fields")
        kind = raw["kind"]
        old_id = normalize_id(kind, raw["old_id"])
        new_id = normalize_id(kind, raw["new_id"])
        if old_id == new_id:
            raise WebIdError(f"alias {index} maps an ID to itself")
        source_sha256 = raw["source_sha256"]
        if not isinstance(source_sha256, str) or SHA256.fullmatch(source_sha256) is None:
            raise WebIdError(f"alias {index} requires a lowercase source SHA-256")
        reason = raw["reason"]
        if not isinstance(reason, str) or not reason.strip():
            raise WebIdError(f"alias {index} requires a reason")
        if old_id in targets:
            raise WebIdError(f"duplicate alias source: {old_id}")
        targets[old_id] = new_id
    for source in targets:
        resolve_alias(source, targets)
    return targets


def resolve_alias(value: str, aliases: dict[str, str]) -> str:
    current = value
    visited: set[str] = set()
    while current in aliases:
        if current in visited:
            raise WebIdError(f"alias cycle detected at {current}")
        visited.add(current)
        current = aliases[current]
    return current


def load_aliases(path: Path) -> dict[str, str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WebIdError(f"cannot read alias register {path}: {exc}") from exc
    return validate_aliases(payload)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, default=Path("config/web-content-aliases.json"), nargs="?")
    args = parser.parse_args()
    try:
        aliases = load_aliases(args.path)
    except WebIdError as exc:
        parser.exit(2, f"web IDs rejected: {exc}\n")
    print(json.dumps({"schema_version": SCHEMA_VERSION, "aliases": len(aliases)}, sort_keys=True))
