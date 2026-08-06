#!/usr/bin/env python3
"""Build a deterministic, read-only image/story pairing report."""

from __future__ import annotations

import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Mapping

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
FILENAME_TIMESTAMP = re.compile(r"(?<!\d)(\d{4}-\d{2}-\d{2})[_T -](\d{2})[-:](\d{2})[-:](\d{2})")
HEADING_TIMESTAMP = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s+(\d{2}):(\d{2}):(\d{2})\s*$", re.MULTILINE)
GIT_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
FULL_STORY = re.compile(r"^(?:full_story|wirtelprimpf_story_[ivxlcdm]+)\.md$", re.IGNORECASE)
TEST_IMAGE = re.compile(r"(?:^|[/_.-])(?:test|testbild)(?:$|[/_.-])", re.IGNORECASE)


class ContentModelError(RuntimeError):
    """The content model cannot inspect a source tree safely."""


def _timestamp(date: str, hour: str, minute: str, second: str) -> str:
    return f"{date} {hour}:{minute}:{second}"


def _filename_timestamp(path: Path) -> str | None:
    match = FILENAME_TIMESTAMP.search(path.name)
    return _timestamp(*match.groups()) if match else None


def _heading_timestamps(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ContentModelError(f"cannot read story sidecar {path}: {exc}") from exc
    return [_timestamp(*match.groups()) for match in HEADING_TIMESTAMP.finditer(text)]


def _kind_for(image: Path, story_path: Path | None) -> str:
    lower = image.name.lower()
    if TEST_IMAGE.search(lower):
        return "unknown"
    if story_path is not None:
        return "story"
    if "geburtstag" in lower or "_classic-" in lower or _filename_timestamp(image):
        return "classic"
    return "legacy"


def _safe_files(root: Path) -> list[Path]:
    if root.is_symlink() or not root.is_dir():
        raise ContentModelError(f"content root must be a non-symlink directory: {root}")
    files: list[Path] = []
    stack = [root]
    while stack:
        directory = stack.pop()
        try:
            entries = sorted(os.scandir(directory), key=lambda entry: entry.name.casefold())
        except OSError as exc:
            raise ContentModelError(f"cannot scan content directory {directory}: {exc}") from exc
        for entry in entries:
            path = Path(entry.path)
            if entry.is_symlink():
                files.append(path)
            elif entry.is_dir(follow_symlinks=False):
                stack.append(path)
            elif entry.is_file(follow_symlinks=False):
                files.append(path)
            else:
                files.append(path)
    return sorted(files, key=lambda path: path.relative_to(root).as_posix().casefold())


def build_content_model(
    root: Path,
    *,
    git_times: Mapping[str, str] | None = None,
    fallback_timestamp: str | None = None,
) -> dict[str, object]:
    """Pair image sidecars and report all unresolved relationships without writes."""
    source_root = Path(root)
    files = _safe_files(source_root)
    git_times = git_times or {}
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    casefold_paths: defaultdict[str, list[str]] = defaultdict(list)
    by_name = {path.relative_to(source_root).as_posix(): path for path in files if not path.is_symlink() and path.is_file()}
    image_paths = [path for path in files if not path.is_symlink() and path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES]
    ignored_working: list[str] = []
    full_story_files: list[str] = []
    unsupported_files: list[str] = []
    for path in files:
        relative = path.relative_to(source_root).as_posix()
        casefold_paths[relative.casefold()].append(relative)
        if path.is_symlink():
            target = Path(os.path.realpath(path))
            if not path.exists() or not str(target).startswith(str(source_root.resolve()) + os.sep):
                errors.append({"code": "PAIR_SYMLINK", "path": relative})
            continue
        if relative.split("/", 1)[0].casefold() == "working":
            ignored_working.append(relative)
            continue
        if FULL_STORY.fullmatch(path.name):
            full_story_files.append(relative)
            continue
        if path.is_file() and path.suffix.lower() not in IMAGE_SUFFIXES and path.suffix.lower() not in {".md", ".txt"}:
            unsupported_files.append(relative)
    for paths in casefold_paths.values():
        if len(paths) > 1:
            errors.append({"code": "PAIR_CASE_COLLISION", "path": "|".join(sorted(paths))})

    records: list[dict[str, object]] = []
    paired_sidecars: set[str] = set()
    for image in image_paths:
        relative = image.relative_to(source_root).as_posix()
        if relative.split("/", 1)[0].casefold() == "working":
            continue
        stem = image.with_suffix("")
        prompt = stem.with_suffix(".txt")
        story = stem.with_suffix(".md")
        prompt_relative = prompt.relative_to(source_root).as_posix() if prompt.is_file() and not prompt.is_symlink() else None
        story_relative = story.relative_to(source_root).as_posix() if story.is_file() and not story.is_symlink() else None
        if prompt_relative:
            paired_sidecars.add(prompt_relative)
        if story_relative:
            paired_sidecars.add(story_relative)
        if prompt_relative is None:
            warnings.append({"code": "PAIR_ORPHAN_PROMPT", "path": relative})
        if story_relative is None:
            warnings.append({"code": "PAIR_ORPHAN_STORY", "path": relative})
        timestamp: str | None = None
        timestamp_source: str | None = None
        heading_values = _heading_timestamps(story) if story_relative else []
        if len(set(heading_values)) == 1:
            timestamp, timestamp_source = heading_values[0], "heading"
        elif len(set(heading_values)) > 1:
            errors.append({"code": "PAIR_AMBIGUOUS_HEADING", "path": relative})
        if timestamp is None:
            timestamp = _filename_timestamp(image)
            timestamp_source = "filename" if timestamp else None
        if timestamp is None:
            git_timestamp = git_times.get(relative)
            if git_timestamp and GIT_TIMESTAMP.fullmatch(git_timestamp):
                timestamp, timestamp_source = git_timestamp, "git"
        if timestamp is None and fallback_timestamp and GIT_TIMESTAMP.fullmatch(fallback_timestamp):
            timestamp, timestamp_source = fallback_timestamp, "fallback"
        if timestamp is None:
            errors.append({"code": "PAIR_TIMESTAMP_MISSING", "path": relative})
        records.append({
            "source_path": relative,
            "kind": _kind_for(image, story if story_relative else None),
            "prompt_path": prompt_relative,
            "story_part_path": story_relative,
            "timestamp": timestamp,
            "timestamp_source": timestamp_source,
        })

    for path in files:
        if path.is_symlink() or not path.is_file():
            continue
        relative = path.relative_to(source_root).as_posix()
        if relative in paired_sidecars or relative in full_story_files or relative.split("/", 1)[0].casefold() == "working":
            continue
        if path.suffix.lower() in {".md", ".txt"}:
            warnings.append({"code": "PAIR_ORPHAN_SIDECAR", "path": relative})

    by_timestamp: defaultdict[str, list[str]] = defaultdict(list)
    for record in records:
        timestamp = record["timestamp"]
        if isinstance(timestamp, str):
            by_timestamp[timestamp].append(str(record["source_path"]))
    for timestamp, paths in sorted(by_timestamp.items()):
        if len(paths) > 1:
            errors.append({"code": "PAIR_TIMESTAMP_COLLISION", "path": f"{timestamp}|{'|'.join(sorted(paths))}"})

    records.sort(key=lambda record: str(record["source_path"]).casefold())
    return {
        "schema_version": "1.0.0",
        "source_root": source_root.as_posix(),
        "records": records,
        "full_story_files": sorted(full_story_files),
        "ignored_working_paths": sorted(ignored_working),
        "unsupported_files": sorted(unsupported_files),
        "warnings": sorted(warnings, key=lambda item: (item["code"], item["path"])),
        "errors": sorted(errors, key=lambda item: (item["code"], item["path"])),
    }


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    print(json.dumps(build_content_model(args.root), ensure_ascii=False, indent=2, sort_keys=True))
