#!/usr/bin/env python3
"""Validate media-to-story relations without rewriting source content."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any


HEADING = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s*$", re.MULTILINE)
TIMESTAMP_PATH = re.compile(r"(?:^|[/_])(?P<date>\d{4}-\d{2}-\d{2})[_T](?P<hour>\d{2})[-:](?P<minute>\d{2})[-:](?P<second>\d{2})(?:[-_.]|$)")
SAFE_CHAPTER_ID = re.compile(r"^band-\d{4}-teil-[a-f0-9]{12}$")
TIMESTAMP_TOLERANCE_SECONDS = 300


class RelationError(RuntimeError):
    """The relation source cannot support a trustworthy report."""


def chapter_id(volume: int, timestamp: str, markdown: str) -> str:
    if not isinstance(volume, int) or volume < 1:
        raise RelationError(f"invalid story volume: {volume}")
    digest = hashlib.sha256(f"{volume}\x00{timestamp}\x00{markdown}".encode("utf-8")).hexdigest()[:12]
    return f"band-{volume:04d}-teil-{digest}"


def load_story_parts(path: Path, volume: int) -> tuple[dict[str, str], dict[str, list[str]]]:
    try:
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    except OSError as exc:
        raise RelationError(f"cannot read story source {path}: {exc}") from exc
    matches = list(HEADING.finditer(text))
    by_id: dict[str, str] = {}
    by_timestamp: dict[str, list[str]] = defaultdict(list)
    for index, match in enumerate(matches):
        timestamp = match.group(1)
        if timestamp is None:
            raise RelationError(f"invalid story heading in {path}")
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        markdown = text[match.end():end].strip()
        identifier = chapter_id(volume, timestamp, markdown)
        if identifier in by_id:
            raise RelationError(f"duplicate chapter id: {identifier}")
        by_id[identifier] = timestamp
        by_timestamp[timestamp].append(identifier)
    return by_id, dict(by_timestamp)


def _relation_path(value: Any, label: str) -> tuple[str, str | None]:
    if not isinstance(value, str) or not value.strip():
        raise RelationError(f"{label} must be a non-empty relative path")
    normalized = value.replace("\\", "/")
    path, separator, fragment = normalized.partition("#")
    pure = PurePosixPath(path)
    if not path or pure.is_absolute() or ".." in pure.parts:
        raise RelationError(f"{label} contains path traversal")
    return path, fragment if separator else None


def _path_timestamp(value: Any, label: str) -> str | None:
    path, fragment = _relation_path(value, label)
    if fragment:
        return None
    match = TIMESTAMP_PATH.search(path)
    if not match:
        return None
    return f"{match.group('date')} {match.group('hour')}:{match.group('minute')}:{match.group('second')}"


def resolve_relation(
    value: Any,
    *,
    label: str,
    chapters: dict[str, str],
    timestamps: dict[str, list[str]],
) -> str:
    path, fragment = _relation_path(value, label)
    if fragment:
        if not SAFE_CHAPTER_ID.fullmatch(fragment) or fragment not in chapters:
            raise RelationError(f"{label} references an unpublished chapter: {fragment}")
        return fragment
    match = TIMESTAMP_PATH.search(path)
    if not match:
        raise RelationError(f"{label} has no stable chapter ID or source timestamp")
    timestamp = f"{match.group('date')} {match.group('hour')}:{match.group('minute')}:{match.group('second')}"
    return resolve_timestamp(timestamp, label=label, chapters=chapters, timestamps=timestamps)


def resolve_timestamp(
    timestamp: str,
    *,
    label: str,
    chapters: dict[str, str],
    timestamps: dict[str, list[str]],
) -> str:
    candidates = timestamps.get(timestamp, [])
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        try:
            source_time = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            nearby: list[tuple[float, str]] = []
            for chapter_timestamp, identifiers in timestamps.items():
                chapter_time = datetime.strptime(chapter_timestamp, "%Y-%m-%d %H:%M:%S")
                distance = abs((source_time - chapter_time).total_seconds())
                if distance <= TIMESTAMP_TOLERANCE_SECONDS:
                    nearby.extend((distance, identifier) for identifier in identifiers)
            if nearby:
                nearest_distance = min(distance for distance, _ in nearby)
                nearest = [identifier for distance, identifier in nearby if distance == nearest_distance]
                if len(nearest) == 1:
                    return nearest[0]
        except ValueError:
            pass
    raise RelationError(f"{label} timestamp is not unique or published: {timestamp}")


def _sidecar_timestamp(value: Any, *, source_root: Path | None, label: str) -> str | None:
    if source_root is None:
        return None
    path, fragment = _relation_path(value, label)
    if fragment:
        return None
    root = source_root.resolve()
    candidates = [(root / PurePosixPath(path)).resolve(), (root / "Wirtelprimpf" / PurePosixPath(path)).resolve()]
    headings: list[str] = []
    for candidate in candidates:
        try:
            candidate.relative_to(root)
        except ValueError:
            continue
        try:
            text = candidate.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
        except (OSError, UnicodeDecodeError):
            continue
        matches = HEADING.findall(text)
        if len(matches) == 1:
            headings.append(matches[0])
    unique_headings = set(headings)
    if len(unique_headings) > 1:
        raise RelationError(f"{label} sidecar path resolves to conflicting headings")
    return next(iter(unique_headings), None)


def validate_relations(
    manifest_path: Path,
    story_path: Path,
    volume: int,
    *,
    strict: bool = False,
    story_sources: list[tuple[Path, int]] | None = None,
    source_root: Path | None = None,
) -> dict[str, Any]:
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RelationError(f"cannot read media manifest {manifest_path}: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != "1.0.0" or not isinstance(payload.get("media"), list):
        raise RelationError("unsupported media manifest schema")

    sources = story_sources or [(story_path, volume)]
    if not sources:
        raise RelationError("at least one story source is required")
    chapters: dict[str, str] = {}
    timestamps: dict[str, list[str]] = defaultdict(list)
    for source_path, source_volume in sources:
        source_chapters, source_timestamps = load_story_parts(source_path, source_volume)
        duplicate_ids = set(chapters).intersection(source_chapters)
        if duplicate_ids:
            raise RelationError(f"duplicate chapter ids across story sources: {sorted(duplicate_ids)}")
        chapters.update(source_chapters)
        for timestamp, identifiers in source_timestamps.items():
            timestamps[timestamp].extend(identifiers)
    errors: list[str] = []
    seen_assets: set[str] = set()
    resolved = 0
    relation_count = 0
    historical_orphan_count = 0
    historical_timestamps: list[str] = []
    approximate_resolved_count = 0
    sidecar_resolved_count = 0
    for index, record in enumerate(payload["media"]):
        label = f"media[{index}]"
        if not isinstance(record, dict):
            errors.append(f"{label} is not an object")
            continue
        asset_id = record.get("asset_id")
        if not isinstance(asset_id, str) or not asset_id.strip():
            errors.append(f"{label}.asset_id is missing")
            asset_id = label
        if asset_id in seen_assets:
            errors.append(f"duplicate asset_id: {asset_id}")
        seen_assets.add(asset_id)
        relation = record.get("story_part_path")
        if relation is None:
            continue
        relation_count += 1
        try:
            path_timestamp = _path_timestamp(relation, f"{label}.story_part_path")
        except RelationError:
            path_timestamp = None
        relation_timestamp = path_timestamp
        try:
            resolved_identifier = resolve_relation(
                relation,
                label=f"{label}.story_part_path",
                chapters=chapters,
                timestamps=timestamps,
            )
        except RelationError as exc:
            sidecar_error: RelationError | None = None
            try:
                sidecar_timestamp = _sidecar_timestamp(
                    relation,
                    source_root=source_root,
                    label=f"{label}.story_part_path",
                )
            except RelationError as error:
                sidecar_timestamp = None
                sidecar_error = error
            if sidecar_timestamp is None or "#" in str(relation):
                if sidecar_error is None and relation_timestamp is not None and timestamps and relation_timestamp < min(timestamps):
                    historical_orphan_count += 1
                    historical_timestamps.append(relation_timestamp)
                    continue
                errors.append(f"{asset_id}: {sidecar_error or exc}")
                continue
            try:
                resolved_identifier = resolve_timestamp(
                    sidecar_timestamp,
                    label=f"{label}.story_part_path sidecar heading",
                    chapters=chapters,
                    timestamps=timestamps,
                )
            except RelationError as sidecar_error:
                if timestamps and sidecar_timestamp < min(timestamps):
                    historical_orphan_count += 1
                    historical_timestamps.append(sidecar_timestamp)
                    continue
                errors.append(f"{asset_id}: {sidecar_error}")
                continue
            relation_timestamp = sidecar_timestamp
            sidecar_resolved_count += 1
        if relation_timestamp is not None and timestamps and relation_timestamp < min(timestamps):
            historical_orphan_count += 1
            historical_timestamps.append(relation_timestamp)
            continue
        resolved += 1
        if path_timestamp is not None and path_timestamp != chapters[resolved_identifier]:
            approximate_resolved_count += 1

    report: dict[str, Any] = {
        "schema_version": "1.0.0",
        "manifest": str(manifest_path.resolve()),
        "story": str(story_path.resolve()),
        "stories": [
            {"path": str(source_path.resolve()), "volume": source_volume}
            for source_path, source_volume in sources
        ],
        "volume": volume,
        "chapter_count": len(chapters),
        "media_count": len(payload["media"]),
        "relation_count": relation_count,
        "resolved_count": resolved,
        "approximate_resolved_count": approximate_resolved_count,
        "sidecar_resolved_count": sidecar_resolved_count,
        "orphan_count": relation_count - resolved,
        "historical_orphan_count": historical_orphan_count,
        "historical_timestamp_range": {
            "first": min(historical_timestamps) if historical_timestamps else None,
            "last": max(historical_timestamps) if historical_timestamps else None,
        },
        "errors": sorted(errors),
    }
    if strict and errors:
        raise RelationError("; ".join(errors))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--story", type=Path, action="append")
    parser.add_argument("--volume", type=int, action="append")
    parser.add_argument("--source-root", type=Path, help="optional root for safe sidecar-heading fallback")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    data_root = root / "data"
    manifest = (args.manifest or data_root / "media-manifest.json").resolve()
    stories = [path.resolve() for path in args.story] if args.story else [
        (data_root / "current-story.md").resolve()
    ]
    volumes = list(args.volume or [])
    if not volumes:
        try:
            source = json.loads((data_root / "hub-source.json").read_text(encoding="utf-8"))
            volumes = [int(source["current_volume"])]
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            parser.error(f"cannot infer story volume: {exc}")
    if len(stories) != len(volumes):
        parser.error("--story and --volume must be supplied the same number of times")
    story = stories[0]
    volume = volumes[0]
    try:
        report = validate_relations(
            manifest,
            story,
            volume,
            strict=args.strict,
            story_sources=list(zip(stories, volumes)),
            source_root=args.source_root.resolve() if args.source_root else None,
        )
    except RelationError as exc:
        parser.exit(2, f"web relations rejected: {exc}\n")
    print(json.dumps(report, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
