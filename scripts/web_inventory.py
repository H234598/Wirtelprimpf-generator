#!/usr/bin/env python3
"""Create a deterministic, read-only inventory report for a media manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import stat
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

HEX64 = re.compile(r"[0-9a-f]{64}")
SAFE_RELATIVE = re.compile(r"^[^/][^\x00]*$")


class InventoryError(RuntimeError):
    """The manifest cannot support a trustworthy inventory."""


class InventoryOutputError(InventoryError):
    """The requested report path is outside the write allowlist."""


def _number(value: Any, *, label: str, minimum: float = 0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise InventoryError(f"{label} must be a finite number")
    if value < minimum:
        raise InventoryError(f"{label} must be >= {minimum}")
    return value


def _percentiles(values: list[int]) -> dict[str, int | None]:
    if not values:
        return {key: None for key in ("median", "p90", "p95", "p99", "maximum")}
    ordered = sorted(values)

    def nearest_rank(percent: float) -> int:
        index = max(0, math.ceil(percent * len(ordered)) - 1)
        return ordered[index]

    return {
        "median": nearest_rank(0.50),
        "p90": nearest_rank(0.90),
        "p95": nearest_rank(0.95),
        "p99": nearest_rank(0.99),
        "maximum": ordered[-1],
    }


def _relative_path(value: Any, *, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not SAFE_RELATIVE.fullmatch(value):
        raise InventoryError(f"{label} must be a relative path")
    pure = PurePosixPath(value)
    if ".." in pure.parts or pure.is_absolute():
        raise InventoryError(f"{label} contains path traversal")
    return value


def _sha256(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or HEX64.fullmatch(value) is None:
        raise InventoryError(f"{label} must be a lowercase SHA-256")
    return value


def _load_manifest(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryError(f"cannot read manifest {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise InventoryError("media manifest must be an object")
    if payload.get("schema_version") != "1.0.0":
        raise InventoryError("unsupported media manifest schema")
    if not isinstance(payload.get("media"), list):
        raise InventoryError("media manifest must contain a media list")
    return payload


def _within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise InventoryError(f"cannot hash source file {path}: {exc}") from exc
    return digest.hexdigest()


def _source_scan(root: Path) -> dict[str, Any]:
    if root.is_symlink() or not root.is_dir():
        raise InventoryError(f"source root must be a non-symlink directory: {root}")
    resolved_root = root.resolve()
    image_suffixes = {".png", ".jpg", ".jpeg", ".webp"}
    image_files: list[str] = []
    symlinks: list[dict[str, Any]] = []
    lfs_pointers: list[str] = []
    hardlink_groups: dict[int, list[str]] = defaultdict(list)
    content_hashes: defaultdict[str, list[str]] = defaultdict(list)
    casefold_paths: defaultdict[str, list[str]] = defaultdict(list)
    special_files: list[str] = []
    epub_files: list[str] = []
    story_files: list[str] = []
    prompt_files: list[str] = []
    errors: list[str] = []
    file_sizes: list[int] = []
    file_count = 0
    file_bytes = 0
    directories = [root]
    while directories:
        directory = directories.pop()
        try:
            entries = sorted(os.scandir(directory), key=lambda item: item.name.casefold())
        except OSError as exc:
            raise InventoryError(f"cannot scan source directory {directory}: {exc}") from exc
        for entry in entries:
            path = Path(entry.path)
            relative = path.relative_to(root).as_posix()
            try:
                entry_stat = entry.stat(follow_symlinks=False)
            except OSError as exc:
                raise InventoryError(f"cannot inspect source path {relative}: {exc}") from exc
            if stat.S_ISLNK(entry_stat.st_mode):
                target = Path(os.path.realpath(path))
                broken = not path.exists()
                outside_root = not broken and not _within(target, resolved_root)
                symlinks.append({
                    "path": relative,
                    "target": os.readlink(path),
                    "broken": broken,
                    "outside_root": outside_root,
                })
                if broken:
                    errors.append(f"broken symlink: {relative}")
                elif outside_root:
                    errors.append(f"symlink escapes source root: {relative}")
                continue
            casefold_paths[relative.casefold()].append(relative)
            if stat.S_ISDIR(entry_stat.st_mode):
                directories.append(path)
                continue
            if not stat.S_ISREG(entry_stat.st_mode):
                special_files.append(relative)
                errors.append(f"special file: {relative}")
                continue
            file_count += 1
            file_bytes += entry_stat.st_size
            file_sizes.append(entry_stat.st_size)
            hardlink_groups[entry_stat.st_ino].append(relative)
            suffix = path.suffix.lower()
            if suffix in image_suffixes:
                image_files.append(relative)
            if suffix == ".epub":
                epub_files.append(relative)
            if suffix == ".md":
                story_files.append(relative)
            if suffix in {".txt", ".md"} and not path.name.lower().startswith("full_story"):
                prompt_files.append(relative)
            digest = _file_sha256(path)
            content_hashes[digest].append(relative)
            try:
                with path.open("rb") as handle:
                    prefix = handle.read(120)
            except OSError as exc:
                raise InventoryError(f"cannot inspect source file {relative}: {exc}") from exc
            if b"git-lfs.github.com/spec/v1" in prefix:
                lfs_pointers.append(relative)
                errors.append(f"LFS pointer file: {relative}")
    case_collisions = [sorted(paths) for paths in casefold_paths.values() if len(paths) > 1]
    duplicate_hardlinks = [sorted(paths) for paths in hardlink_groups.values() if len(paths) > 1]
    duplicate_content = [sorted(paths) for paths in content_hashes.values() if len(paths) > 1]
    errors.extend(f"portable case collision: {', '.join(paths)}" for paths in case_collisions)
    return {
        "root": root.as_posix(),
        "file_count": file_count,
        "file_bytes": file_bytes,
        "file_size_bytes": _percentiles(file_sizes),
        "image_files": len(image_files),
        "symlinks": symlinks,
        "lfs_pointer_files": lfs_pointers,
        "epub_files": sorted(epub_files),
        "story_files": sorted(story_files),
        "prompt_files": sorted(prompt_files),
        "special_files": sorted(special_files),
        "case_collisions": sorted(case_collisions, key=lambda paths: paths[0]),
        "duplicate_content_groups": sorted(duplicate_content, key=lambda paths: paths[0]),
        "duplicate_hardlink_groups": duplicate_hardlinks,
        "errors": sorted(set(errors)),
    }


def build_inventory(manifest_path: Path, *, source_root: Path | None = None, strict: bool = False) -> dict[str, Any]:
    payload = _load_manifest(manifest_path)
    records = payload["media"]
    errors: list[str] = []
    ids: Counter[str] = Counter()
    hashes: defaultdict[str, list[str]] = defaultdict(list)
    source_paths: Counter[str] = Counter()
    bytes_by_kind: Counter[str] = Counter()
    bytes_by_mime: Counter[str] = Counter()
    width_values: list[int] = []
    height_values: list[int] = []
    pixel_values: list[int] = []
    original_sizes: list[int] = []
    variant_sizes: Counter[str] = Counter()
    variant_counts: Counter[str] = Counter()
    missing_prompt = 0
    missing_story = 0
    release_asset_counts: Counter[str] = Counter()
    record_asset_units = 0

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"media[{index}] is not an object")
            continue
        label = f"media[{index}]"
        asset_id = record.get("asset_id")
        if not isinstance(asset_id, str) or not asset_id:
            errors.append(f"{label}.asset_id is missing")
            asset_id = f"<invalid-{index}>"
        ids[asset_id] += 1
        source_path = _relative_path(record.get("source_path"), label=f"{label}.source_path")
        if source_path is not None:
            source_paths[source_path] += 1
        try:
            digest = _sha256(record.get("sha256"), label=f"{label}.sha256")
            size = int(_number(record.get("byte_size"), label=f"{label}.byte_size", minimum=1))
            width = int(_number(record.get("width"), label=f"{label}.width", minimum=1))
            height = int(_number(record.get("height"), label=f"{label}.height", minimum=1))
        except (InventoryError, ValueError) as exc:
            errors.append(str(exc))
            continue
        hashes[digest].append(asset_id)
        original_sizes.append(size)
        bytes_by_kind[str(record.get("kind", "unknown"))] += size
        bytes_by_mime[str(record.get("mime_type", "unknown"))] += size
        width_values.append(width)
        height_values.append(height)
        pixel_values.append(width * height)
        prompt = _relative_path(record.get("prompt_path"), label=f"{label}.prompt_path")
        story = _relative_path(record.get("story_part_path"), label=f"{label}.story_part_path")
        missing_prompt += prompt is None
        missing_story += story is None
        variants = record.get("variants", [])
        if not isinstance(variants, list):
            errors.append(f"{label}.variants must be a list")
            continue
        for variant_index, variant in enumerate(variants):
            if not isinstance(variant, dict):
                errors.append(f"{label}.variants[{variant_index}] is not an object")
                continue
            variant_label = f"{label}.variants[{variant_index}]"
            requested = variant.get("requested_width")
            try:
                requested_width = int(_number(requested, label=f"{variant_label}.requested_width", minimum=1))
                variant_size = int(_number(variant.get("byte_size"), label=f"{variant_label}.byte_size", minimum=1))
                _sha256(variant.get("sha256"), label=f"{variant_label}.sha256")
            except (InventoryError, ValueError) as exc:
                errors.append(str(exc))
                continue
            key = str(requested_width)
            variant_counts[key] += 1
            variant_sizes[key] += variant_size
        record_asset_units += 1 + len(variants)
        release_tag = record.get("release_tag")
        if isinstance(release_tag, str) and release_tag:
            release_asset_counts[release_tag] += 1 + len(variants)

    shard_errors: list[str] = []
    shards = payload.get("shards", [])
    if not isinstance(shards, list):
        shard_errors.append("shards must be a list")
        shards = []
    shard_record_count = 0
    for index, shard in enumerate(shards):
        if not isinstance(shard, dict):
            shard_errors.append(f"shards[{index}] is not an object")
            continue
        record_count = shard.get("record_count")
        asset_count = shard.get("asset_count")
        if not isinstance(record_count, int) or record_count < 1:
            shard_errors.append(f"shards[{index}].record_count is invalid")
            continue
        shard_record_count += record_count
        release_tag = shard.get("tag")
        if isinstance(release_tag, str) and release_tag in release_asset_counts:
            expected_asset_count = release_asset_counts[release_tag] + 2
        elif len(shards) == 1 and record_count == len(records):
            expected_asset_count = record_asset_units + 2
        else:
            expected_asset_count = record_count * 3 + 2
        if asset_count != expected_asset_count:
            shard_errors.append(f"shards[{index}].asset_count does not match the media variants plus bundle/manifest")
        if shard.get("open") is not False:
            shard_errors.append(f"shards[{index}] is not closed")
    errors.extend(shard_errors)
    if payload.get("media_count") != len(records):
        errors.append("media_count does not match media list length")
    if shards and shard_record_count != len(records):
        errors.append("shard record counts do not match media list length")
    errors.extend(f"duplicate asset_id: {key}" for key, value in ids.items() if value > 1)
    errors.extend(f"duplicate source_path: {key}" for key, value in source_paths.items() if value > 1)

    source_scan = _source_scan(source_root) if source_root is not None else None
    if source_scan is not None:
        errors.extend(source_scan["errors"])
    source_date_epoch: int | None = None
    if os.environ.get("SOURCE_DATE_EPOCH"):
        try:
            source_date_epoch = int(os.environ["SOURCE_DATE_EPOCH"])
        except ValueError as exc:
            raise InventoryError("SOURCE_DATE_EPOCH must be an integer") from exc
    report: dict[str, Any] = {
        "schema_version": payload["schema_version"],
        "manifest": manifest_path.as_posix(),
        "archive_repository": payload.get("archive_repository"),
        "media_count": len(records),
        "source_bytes": sum(original_sizes),
        "source_bytes_by_kind": dict(sorted(bytes_by_kind.items())),
        "source_bytes_by_mime": dict(sorted(bytes_by_mime.items())),
        "source_size_bytes": _percentiles(original_sizes),
        "dimensions": {
            "width": _percentiles(width_values),
            "height": _percentiles(height_values),
            "pixels": _percentiles(pixel_values),
        },
        "variants": {
            key: {"count": variant_counts[key], "bytes": variant_sizes[key]}
            for key in sorted(variant_counts, key=lambda item: int(item))
        },
        "relationship_gaps": {
            "missing_prompt_path": missing_prompt,
            "missing_story_part_path": missing_story,
        },
        "duplicates": {
            "content_hash_groups": sorted(
                [sorted(values) for values in hashes.values() if len(values) > 1],
                key=lambda values: values[0],
            ),
            "duplicate_asset_ids": sorted(key for key, value in ids.items() if value > 1),
            "duplicate_source_paths": sorted(key for key, value in source_paths.items() if value > 1),
        },
        "release_completeness": {
            "shards": len(shards),
            "record_count_from_shards": shard_record_count,
            "closed_shards": sum(isinstance(shard, dict) and shard.get("open") is False for shard in shards),
            "expected_asset_count": sum(
                (
                    release_asset_counts.get(shard.get("tag"), 0) + 2
                    if isinstance(shard, dict) and isinstance(shard.get("tag"), str) and shard.get("tag") in release_asset_counts
                    else record_asset_units + 2
                    if len(shards) == 1 and isinstance(shard, dict) and shard.get("record_count") == len(records)
                    else shard.get("record_count", 0) * 3 + 2
                )
                for shard in shards
                if isinstance(shard, dict) and isinstance(shard.get("record_count"), int)
            ),
            "declared_asset_count": sum(
                shard.get("asset_count", 0)
                for shard in shards
                if isinstance(shard, dict) and isinstance(shard.get("asset_count"), int)
            ),
        },
        "source_scan": source_scan,
        "source_date_epoch": source_date_epoch,
        "errors": sorted(set(errors)),
    }
    if strict and report["errors"]:
        raise InventoryError("; ".join(report["errors"]))
    return report


def write_report(report: dict[str, Any], output: Path, *, root: Path = Path(".")) -> None:
    """Atomically write only below ``build/reports`` in the selected root."""
    allowed_root = (root / "build" / "reports").resolve()
    candidate = output if output.is_absolute() else root / output
    target = candidate.resolve()
    if not _within(target, allowed_root) or target == allowed_root:
        raise InventoryOutputError("inventory output must stay below build/reports")
    target.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(rendered, encoding="utf-8", newline="\n")
        os.replace(temporary, target)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise InventoryOutputError(f"cannot write inventory report: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    manifest = args.manifest or args.root / "data" / "media-manifest.json"
    source_root = args.source_root
    if source_root is None:
        candidate = args.root / "Wirtelprimpf"
        source_root = candidate if candidate.exists() else None
    try:
        report = build_inventory(manifest, source_root=source_root, strict=args.strict)
    except InventoryError as exc:
        parser.exit(2, f"web inventory rejected: {exc}\n")
    if args.output:
        try:
            write_report(report, args.output, root=args.root)
        except InventoryOutputError as exc:
            parser.exit(3, f"web inventory output rejected: {exc}\n")
    else:
        rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
