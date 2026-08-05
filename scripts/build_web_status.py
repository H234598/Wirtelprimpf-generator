#!/usr/bin/env python3
"""Build a redacted, deterministic public freshness status document."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0.0"
DEFAULT_FRESHNESS_SLA_SECONDS = 6 * 60 * 60
SHA1 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
STORY_FILE = re.compile(r"^Wirtelprimpf_Story_([IVXLCDM]+)\.md$")
PART_HEADING = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s*$", re.MULTILINE)


class StatusError(RuntimeError):
    """Status inputs cannot produce a trustworthy public result."""


def _read_json(path: Path, *, required: bool = True) -> dict[str, Any] | None:
    if path.is_symlink():
        raise StatusError(f"status input must not be a symlink: {path.name}")
    if not path.is_file():
        if not required:
            return None
        raise StatusError(f"required status input is missing: {path.name}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise StatusError(f"invalid status input {path.name}: {exc}") from exc
    if not isinstance(payload, dict):
        raise StatusError(f"status input must be an object: {path.name}")
    return payload


def _configured_path(name: str, data_root: Path) -> Path | None:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return None
    configured = Path(raw.strip()).expanduser()
    return configured if configured.is_absolute() else data_root / configured


def _parse_timestamp(value: str, *, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise StatusError(f"invalid {label}: {value!r}") from exc
    if parsed.tzinfo is None:
        raise StatusError(f"{label} must include a timezone")
    return parsed.astimezone(UTC)


def _format_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _git_revision(root: Path) -> str | None:
    if not root.exists():
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    revision = result.stdout.strip()
    return revision if SHA1.fullmatch(revision) else None


def _roman(value: str) -> int:
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    if not value or any(character not in values for character in value):
        raise StatusError(f"invalid story volume: {value!r}")
    result = 0
    previous = 0
    for character in reversed(value):
        current = values[character]
        result += -current if current < previous else current
        previous = max(previous, current)
    return result


def _story_records(
    data_root: Path,
    *,
    explicit_story: Path | None = None,
    explicit_volume: int | None = None,
) -> list[dict[str, Any]]:
    candidates: list[tuple[Path, int]] = []
    if explicit_story is not None:
        if explicit_story.is_symlink() or not explicit_story.is_file():
            raise StatusError(f"explicit current story is missing or unsafe: {explicit_story.name}")
        if explicit_volume is None or isinstance(explicit_volume, bool) or explicit_volume < 1:
            raise StatusError("explicit current volume must be a positive integer")
        candidates.append((explicit_story, explicit_volume))
    else:
        directories = (data_root, data_root / "Wirtelprimpf")
        for directory in directories:
            if not directory.is_dir():
                continue
            for path in sorted(directory.iterdir(), key=lambda item: item.name.casefold()):
                match = STORY_FILE.fullmatch(path.name)
                if match and path.is_file() and not path.is_symlink():
                    candidates.append((path, _roman(match.group(1))))
        current_story = data_root / "current-story.md"
        hub_source = _read_json(data_root / "hub-source.json", required=False)
        if current_story.is_file() and not current_story.is_symlink() and isinstance(hub_source, dict):
            volume = hub_source.get("current_volume")
            if isinstance(volume, int) and not isinstance(volume, bool) and volume > 0:
                candidates.append((current_story, volume))

    records: list[dict[str, Any]] = []
    seen: set[tuple[int, str]] = set()
    for path, volume in candidates:
        key = (volume, path.name)
        if key in seen:
            continue
        seen.add(key)
        normalized = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
        matches = list(PART_HEADING.finditer(normalized))
        for sequence, match in enumerate(matches, start=1):
            timestamp = match.group(1)
            if timestamp is None:
                raise StatusError(f"story heading has no timestamp: {path.name}")
            end = matches[sequence].start() if sequence < len(matches) else len(normalized)
            markdown = normalized[match.end():end].strip()
            digest = hashlib.sha256(f"{volume}\0{timestamp}\0{markdown}".encode("utf-8")).hexdigest()[:12]
            records.append({
                "id": f"band-{volume:04d}-teil-{digest}",
                "timestamp": timestamp,
                "volume": volume,
                "sequence": sequence,
            })
    return records


def _media_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    raw_media = manifest.get("media")
    if not isinstance(raw_media, list):
        raise StatusError("media manifest media must be a list")
    records = [item for item in raw_media if isinstance(item, dict)]
    if len(records) != len(raw_media):
        raise StatusError("media manifest contains a non-object record")
    for item in records:
        asset_id = item.get("asset_id")
        source_path = item.get("source_path")
        digest = item.get("sha256")
        if not isinstance(asset_id, str) or not asset_id or not isinstance(source_path, str) or not source_path:
            raise StatusError("media record lacks a public identity")
        source_parts = Path(source_path).parts
        if Path(source_path).is_absolute() or "\\" in source_path or ".." in source_parts:
            raise StatusError("media record contains a local path")
        if not isinstance(digest, str) or not SHA256.fullmatch(digest):
            raise StatusError("media record has an invalid source hash")
    latest = max(records, key=lambda item: (str(item["source_path"]), str(item["asset_id"])), default=None)
    return {
        "count": len(records),
        "latest_id": latest["asset_id"] if latest else None,
        "latest_source_path": latest["source_path"] if latest else None,
        "latest_sha256": latest["sha256"] if latest else None,
    }


def _freshness(*, published_at: str | None, built_at: datetime, sla_seconds: int) -> dict[str, Any]:
    if published_at is None:
        return {
            "state": "unknown",
            "last_published_at": None,
            "age_seconds": None,
            "warning_after_seconds": sla_seconds // 2,
            "stale_after_seconds": sla_seconds,
        }
    published = _parse_timestamp(published_at, label="manifest generated_at")
    age = max(0, int((built_at - published).total_seconds()))
    warning_after = max(1, sla_seconds // 2)
    state = "fresh" if age <= warning_after else "warning" if age <= sla_seconds else "stale"
    return {
        "state": state,
        "last_published_at": _format_timestamp(published),
        "age_seconds": age,
        "warning_after_seconds": warning_after,
        "stale_after_seconds": sla_seconds,
    }


def build_status(
    *,
    root: Path,
    data_root: Path,
    profile: str,
    repository: str | None = None,
    built_at: datetime | None = None,
    freshness_sla_seconds: int = DEFAULT_FRESHNESS_SLA_SECONDS,
) -> dict[str, Any]:
    if profile not in {"hub", "archive"}:
        raise StatusError(f"invalid site profile: {profile!r}")
    if isinstance(freshness_sla_seconds, bool) or freshness_sla_seconds < 1:
        raise StatusError("freshness SLA must be positive")
    manifest_path = _configured_path("WIRTELPRIMPF_MEDIA_MANIFEST", data_root) or (data_root / "media-manifest.json")
    manifest = _read_json(manifest_path, required=manifest_path != data_root / "media-manifest.json") or {
        "media": [],
        "generated_at": None,
    }
    if manifest.get("schema_version") not in {None, "1.0.0"}:
        raise StatusError("unsupported media manifest schema")
    media = _media_summary(manifest)
    current_story = _configured_path("WIRTELPRIMPF_CURRENT_STORY", data_root)
    current_volume_raw = os.environ.get("WIRTELPRIMPF_CURRENT_VOLUME")
    current_volume: int | None = None
    if current_volume_raw is not None and current_volume_raw.strip():
        try:
            current_volume = int(current_volume_raw.strip())
        except ValueError as exc:
            raise StatusError("WIRTELPRIMPF_CURRENT_VOLUME must be an integer") from exc
    stories = _story_records(
        data_root,
        explicit_story=current_story,
        explicit_volume=current_volume,
    )
    latest_story = max(stories, key=lambda item: (item["volume"], item["sequence"], item["id"]), default=None)
    archive_index = manifest.get("archive_index")
    if not isinstance(archive_index, int) or isinstance(archive_index, bool) or archive_index < 1:
        archive_index = None
    if profile == "hub":
        resolved_repository = repository or "Wirtelprimpf-generator"
    else:
        resolved_repository = repository or manifest.get("archive_repository")
        if not isinstance(resolved_repository, str) or not resolved_repository:
            resolved_repository = "Wirtelprimpf-0001"
    source_date_epoch_raw = os.environ.get("SOURCE_DATE_EPOCH")
    source_date_epoch: int | None = None
    if source_date_epoch_raw is not None:
        try:
            source_date_epoch = int(source_date_epoch_raw)
        except ValueError as exc:
            raise StatusError("SOURCE_DATE_EPOCH must be an integer") from exc
        if source_date_epoch < 0:
            raise StatusError("SOURCE_DATE_EPOCH must be non-negative")
    if built_at is None:
        built_at = datetime.fromtimestamp(source_date_epoch, tz=UTC) if source_date_epoch is not None else datetime.now(UTC)
    published_at = manifest.get("generated_at")
    if published_at is not None and not isinstance(published_at, str):
        raise StatusError("media manifest generated_at must be a string or null")
    source_revision_raw = os.environ.get("WIRTELPRIMPF_SOURCE_REVISION")
    if source_revision_raw is not None:
        source_revision = source_revision_raw.strip() or None
        if source_revision is not None and not SHA1.fullmatch(source_revision):
            raise StatusError("WIRTELPRIMPF_SOURCE_REVISION must be a full lower-case Git commit SHA")
    else:
        source_revision = _git_revision(data_root) or _git_revision(root)
    return {
        "schema_version": SCHEMA_VERSION,
        "profile": profile,
        "repository": resolved_repository,
        "archive_index": archive_index,
        "source_revision": source_revision,
        "media": media,
        "stories": {
            "count": len({item["volume"] for item in stories}),
            "chapter_count": len(stories),
            "latest_id": latest_story["id"] if latest_story else None,
            "latest_volume": latest_story["volume"] if latest_story else None,
            "latest_timestamp": latest_story["timestamp"] if latest_story else None,
        },
        "publication": {
            "manifest_generated_at": _format_timestamp(_parse_timestamp(published_at, label="manifest generated_at"))
            if published_at
            else None,
        },
        "build": {
            "built_at": _format_timestamp(built_at),
            "source_date_epoch": source_date_epoch,
        },
        "freshness": _freshness(
            published_at=published_at,
            built_at=built_at,
            sla_seconds=freshness_sla_seconds,
        ),
    }


def write_status(path: Path, status: dict[str, Any]) -> None:
    if path.is_symlink():
        raise StatusError(f"status output must not be a symlink: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(status, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--profile", choices=("hub", "archive"), default=os.environ.get("WIRTELPRIMPF_SITE_PROFILE", "hub"))
    parser.add_argument("--repository")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--built-at")
    parser.add_argument("--freshness-sla-seconds", type=int, default=DEFAULT_FRESHNESS_SLA_SECONDS)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    configured_data_root = args.data_root or Path(os.environ.get("WIRTELPRIMPF_DATA_ROOT", str(root / "data")))
    data_root = configured_data_root.expanduser().resolve()
    built_at = _parse_timestamp(args.built_at, label="built-at") if args.built_at else None
    try:
        status = build_status(
            root=root,
            data_root=data_root,
            profile=args.profile,
            repository=args.repository,
            built_at=built_at,
            freshness_sla_seconds=args.freshness_sla_seconds,
        )
        write_status(args.output, status)
    except (OSError, StatusError) as exc:
        parser.exit(2, f"web status build failed: {exc}\n")
    print(json.dumps(status, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
