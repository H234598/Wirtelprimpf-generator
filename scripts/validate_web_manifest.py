#!/usr/bin/env python3
"""Fail-closed validation for the release-bound web image manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


SHA256 = re.compile(r"^[a-f0-9]{64}$")
PATH = re.compile(r"^(?!/)(?!.*(?:^|/)\.\.(?:/|$)).+$")
ASSET_ID = re.compile(r"^archive-[0-9]{4}-[a-f0-9]{16}-[a-f0-9]{8}$")
TAG = re.compile(r"^archive-[0-9]{4}-media-[0-9]{4}$")


class WebManifestError(ValueError):
    """The manifest violates the release and derivative contract."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise WebManifestError(message)


def _sha(value: Any, label: str) -> str:
    _require(isinstance(value, str) and SHA256.fullmatch(value) is not None, f"{label} must be a lowercase SHA-256")
    return value


def _path(value: Any, label: str, *, nullable: bool = False) -> str | None:
    if nullable and value is None:
        return None
    _require(isinstance(value, str) and PATH.fullmatch(value) is not None, f"{label} must be a safe relative path")
    return value


def _object(value: Any, label: str, fields: set[str], *, required: set[str] | None = None) -> dict[str, Any]:
    _require(isinstance(value, dict), f"{label} must be an object")
    required = fields if required is None else required
    _require(set(value) <= fields and required <= set(value), f"{label} has unknown or missing fields")
    return value


def validate_manifest(payload: Any) -> dict[str, Any]:
    fields = {"schema_version", "archive_index", "archive_repository", "owner", "media_count", "shards", "media"}
    manifest = _object(payload, "manifest", fields)
    _require(manifest["schema_version"] == "1.0.0", "unsupported manifest schema")
    archive_index = manifest["archive_index"]
    _require(isinstance(archive_index, int) and not isinstance(archive_index, bool) and archive_index >= 1, "invalid archive index")
    repository = manifest["archive_repository"]
    _require(repository == f"Wirtelprimpf-{archive_index:04d}", "archive repository does not match index")
    _require(isinstance(manifest["owner"], str) and re.fullmatch(r"[A-Za-z0-9_.-]+", manifest["owner"]), "invalid owner")
    media = manifest["media"]
    shards = manifest["shards"]
    _require(isinstance(media, list), "media must be a list")
    _require(isinstance(manifest["media_count"], int) and manifest["media_count"] == len(media), "media count mismatch")
    _require(isinstance(shards, list) and shards, "shards must be a non-empty list")
    shard_count = 0
    shard_tags: set[str] = set()
    for index, raw in enumerate(shards):
        shard = _object(raw, f"shard {index}", {"index", "tag", "open", "record_count", "asset_count", "manifest_asset_name", "manifest_sha256", "bundle_asset_name", "bundle_sha256"})
        _require(shard["index"] == index + 1, f"shard {index} index is not contiguous")
        _require(isinstance(shard["tag"], str) and TAG.fullmatch(shard["tag"]), f"shard {index} tag is invalid")
        _require(shard["tag"] not in shard_tags, f"duplicate shard tag: {shard['tag']}")
        shard_tags.add(shard["tag"])
        _require(shard["open"] is False, f"shard {index} is open")
        record_count = shard["record_count"]
        _require(isinstance(record_count, int) and record_count >= 1, f"shard {index} record count is invalid")
        _require(shard["asset_count"] == record_count * 3 + 2, f"shard {index} asset count mismatch")
        _sha(shard["manifest_sha256"], f"shard {index} manifest sha256")
        _sha(shard["bundle_sha256"], f"shard {index} bundle sha256")
        shard_count += record_count
    _require(shard_count == len(media), "shard record counts mismatch")

    ids: set[str] = set()
    source_paths: set[str] = set()
    release_counts: dict[str, int] = {}
    for index, raw in enumerate(media):
        item = _object(
            raw,
            f"media {index}",
            {"asset_id", "source_path", "kind", "sha256", "byte_size", "mime_type", "width", "height", "prompt_path", "story_part_path", "alt_text", "alt_text_source", "release_tag", "original", "variants"},
            required={"asset_id", "source_path", "kind", "sha256", "byte_size", "mime_type", "width", "height", "prompt_path", "story_part_path", "release_tag", "original", "variants"},
        )
        asset_id = item["asset_id"]
        _require(isinstance(asset_id, str) and ASSET_ID.fullmatch(asset_id), f"media {index} asset ID is invalid")
        _require(asset_id not in ids, f"duplicate asset ID: {asset_id}")
        ids.add(asset_id)
        source_path = _path(item["source_path"], f"media {index} source path")
        assert source_path is not None
        _require(source_path not in source_paths, f"duplicate source path: {source_path}")
        source_paths.add(source_path)
        _require(item["kind"] in {"story", "classic", "legacy", "unknown"}, f"media {index} kind is invalid")
        _sha(item["sha256"], f"media {index} sha256")
        _require(isinstance(item["byte_size"], int) and item["byte_size"] >= 1, f"media {index} byte size is invalid")
        _require(item["mime_type"] in {"image/png", "image/jpeg", "image/webp"}, f"media {index} MIME is invalid")
        _require(isinstance(item["width"], int) and item["width"] >= 1, f"media {index} width is invalid")
        _require(isinstance(item["height"], int) and item["height"] >= 1, f"media {index} height is invalid")
        _path(item["prompt_path"], f"media {index} prompt path", nullable=True)
        _path(item["story_part_path"], f"media {index} story path", nullable=True)
        _require(item.get("alt_text") is None or isinstance(item["alt_text"], str), f"media {index} alt text is invalid")
        _require(item.get("alt_text_source", "fallback") in {"manifest", "prompt", "fallback"}, f"media {index} alt text source is invalid")
        release_tag = item["release_tag"]
        _require(isinstance(release_tag, str) and release_tag in shard_tags, f"media {index} release tag is unknown")
        release_counts[release_tag] = release_counts.get(release_tag, 0) + 1
        original = _object(item["original"], f"media {index} original", {"asset_name", "url"})
        _require(isinstance(original["asset_name"], str) and original["asset_name"], f"media {index} original name is invalid")
        _require(isinstance(original["url"], str) and original["url"].startswith("https://github.com/"), f"media {index} original URL is invalid")
        variants = item["variants"]
        _require(isinstance(variants, list) and variants, f"media {index} variants are missing")
        widths: list[int] = []
        for variant_index, variant_raw in enumerate(variants):
            variant = _object(variant_raw, f"media {index} variant {variant_index}", {"requested_width", "actual_width", "actual_height", "asset_name", "url", "sha256", "byte_size", "mime_type"})
            _require(isinstance(variant["requested_width"], int) and variant["requested_width"] >= 1, "variant width is invalid")
            widths.append(variant["requested_width"])
            _require(isinstance(variant["actual_width"], int) and variant["actual_width"] >= 1, "variant actual width is invalid")
            _require(isinstance(variant["actual_height"], int) and variant["actual_height"] >= 1, "variant actual height is invalid")
            _require(isinstance(variant["asset_name"], str) and variant["asset_name"], "variant asset name is invalid")
            _require(isinstance(variant["url"], str) and variant["url"].startswith("https://github.com/"), "variant URL is invalid")
            _sha(variant["sha256"], "variant sha256")
            _require(isinstance(variant["byte_size"], int) and variant["byte_size"] >= 1, "variant byte size is invalid")
            _require(variant["mime_type"] == "image/webp", "variant MIME is invalid")
        _require(widths == sorted(set(widths)), f"media {index} variant widths are not sorted and unique")
    for shard in shards:
        _require(release_counts.get(shard["tag"], 0) == shard["record_count"], f"shard media count mismatch: {shard['tag']}")
    return {"schema_version": "1.0.0", "media_count": len(media), "shard_count": len(shards), "variant_widths": sorted({width for item in media for width in (variant["requested_width"] for variant in item["variants"])})}


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WebManifestError(f"cannot read manifest {path}: {exc}") from exc
    return validate_manifest(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    manifest = args.manifest or args.root / "data" / "media-manifest.json"
    try:
        report = load_manifest(manifest)
    except WebManifestError as exc:
        parser.exit(2, f"web manifest rejected: {exc}\n")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
