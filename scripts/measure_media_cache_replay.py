#!/usr/bin/env python3
"""Verify a full migration archive and measure its warm derivative-cache replay."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from PIL import Image

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wirtelprimpf_platform.media import DERIVATIVE_WIDTHS, MEDIA_TRANSFORM_TOOL_VERSION, _materialize_variant
from wirtelprimpf_platform.media_cache import (
    TRANSFORM_CONFIG_VERSION,
    MediaDerivativeCache,
    media_cache_key,
)


class CacheReplayError(RuntimeError):
    """The source or replay cache does not satisfy the measured contract."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _asset_path(root: Path, name: str) -> Path:
    if not name or Path(name).name != name:
        raise CacheReplayError(f"asset name is not a flat filename: {name!r}")
    matches = sorted(root.rglob(name))
    if len(matches) != 1:
        raise CacheReplayError(f"expected exactly one asset {name!r}, found {len(matches)}")
    path = matches[0]
    if path.is_symlink() or not path.is_file():
        raise CacheReplayError(f"asset is not a regular file: {name!r}")
    return path


def _image_shape(path: Path) -> tuple[int, int]:
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            return image.size
    except (OSError, ValueError) as exc:
        raise CacheReplayError(f"invalid image asset: {path.name}") from exc


def _copy_or_link(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(source, target)
    except OSError:
        shutil.copyfile(source, target)


def _require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CacheReplayError(f"{label} must be an object")
    return value


def _prepare_cache(
    source_root: Path,
    records: list[dict[str, Any]],
    cache_root: Path,
) -> dict[str, int | bool]:
    originals = 0
    derivatives = 0
    for record in records:
        original = _require_mapping(record.get("original"), "original")
        original_name = original.get("asset_name")
        original_sha = record.get("sha256")
        if not isinstance(original_name, str) or not isinstance(original_sha, str):
            raise CacheReplayError("manifest record has invalid original identity")
        original_path = _asset_path(source_root, original_name)
        if _sha256(original_path) != original_sha:
            raise CacheReplayError(f"original hash mismatch: {original_name}")
        if original_path.stat().st_size != record.get("byte_size"):
            raise CacheReplayError(f"original byte-size mismatch: {original_name}")
        originals += 1

        variants = record.get("variants")
        if not isinstance(variants, list) or not variants:
            raise CacheReplayError(f"missing variants: {original_name}")
        for raw_variant in variants:
            variant = _require_mapping(raw_variant, "variant")
            name = variant.get("asset_name")
            width = variant.get("requested_width")
            digest = variant.get("sha256")
            byte_size = variant.get("byte_size")
            actual_width = variant.get("actual_width")
            actual_height = variant.get("actual_height")
            if (
                not isinstance(name, str)
                or isinstance(width, bool)
                or not isinstance(width, int)
                or not isinstance(digest, str)
                or isinstance(byte_size, bool)
                or not isinstance(byte_size, int)
                or isinstance(actual_width, bool)
                or not isinstance(actual_width, int)
                or isinstance(actual_height, bool)
                or not isinstance(actual_height, int)
            ):
                raise CacheReplayError(f"invalid variant metadata: {original_name}")
            variant_path = _asset_path(source_root, name)
            if _sha256(variant_path) != digest or variant_path.stat().st_size != byte_size:
                raise CacheReplayError(f"variant hash/size mismatch: {name}")
            if _image_shape(variant_path) != (actual_width, actual_height):
                raise CacheReplayError(f"variant dimensions mismatch: {name}")

            key = media_cache_key(
                original_sha,
                MEDIA_TRANSFORM_TOOL_VERSION,
                TRANSFORM_CONFIG_VERSION,
                "webp",
                width,
            )
            entry = cache_root / key
            entry.mkdir(parents=True, exist_ok=False)
            _copy_or_link(variant_path, entry / "derivative.webp")
            metadata = {
                "actual_height": actual_height,
                "actual_width": actual_width,
                "byte_size": byte_size,
                "cache_key": key,
                "original_sha256": original_sha,
                "schema_version": "1.0.0",
                "sha256": digest,
                "target_format": "webp",
                "target_width": width,
                "tool_version": MEDIA_TRANSFORM_TOOL_VERSION,
                "transform_config_version": TRANSFORM_CONFIG_VERSION,
            }
            (entry / "metadata.json").write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            derivatives += 1
    return {"originals": originals, "derivatives": derivatives, "hashes_match": True}


def _cold_transform(
    source_root: Path,
    records: list[dict[str, Any]],
    cache_root: Path,
    target_root: Path,
) -> dict[str, Any]:
    """Materialize every derivative from an empty cache and verify its manifest bytes."""
    cache = MediaDerivativeCache(cache_root, tool_version=MEDIA_TRANSFORM_TOOL_VERSION, writable=True)
    target_root.mkdir(parents=True, exist_ok=True)
    expected_requests = sum(len(record["variants"]) for record in records)
    started = time.perf_counter()
    for record in records:
        original = _require_mapping(record.get("original"), "original")
        original_name = original.get("asset_name")
        original_sha = record.get("sha256")
        if not isinstance(original_name, str) or not isinstance(original_sha, str):
            raise CacheReplayError("manifest record has invalid original identity")
        source = _asset_path(source_root, original_name)
        for raw_variant in record["variants"]:
            variant = _require_mapping(raw_variant, "variant")
            width = variant.get("requested_width")
            name = variant.get("asset_name")
            if (
                isinstance(width, bool)
                or not isinstance(width, int)
                or not isinstance(name, str)
            ):
                raise CacheReplayError(f"invalid cold-transform variant: {original_name}")
            target = target_root / name
            result = cache.materialize(
                original_sha256=original_sha,
                target_width=width,
                target=target,
                producer=lambda path, source=source, width=width: _materialize_variant(source, path, width),
            )
            expected = (
                variant.get("sha256"),
                variant.get("byte_size"),
                variant.get("actual_width"),
                variant.get("actual_height"),
            )
            if result != expected:
                raise CacheReplayError(
                    f"cold transform differs from manifest: {name} ({result!r} != {expected!r})"
                )
    report = cache.report()
    report.update(
        {
            "duration_seconds": round(time.perf_counter() - started, 3),
            "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "cold_transform": True,
        }
    )
    if (
        report["requests"] != expected_requests
        or report["hits"] != 0
        or report["misses"] != expected_requests
        or report["writes"] != expected_requests
        or report["invalid_entries"] != 0
    ):
        raise CacheReplayError(f"cold transform did not start from an empty cache: {report}")
    return report


def _replay(
    records: list[dict[str, Any]],
    cache_root: Path,
    target_root: Path,
) -> dict[str, Any]:
    cache = MediaDerivativeCache(cache_root, tool_version=MEDIA_TRANSFORM_TOOL_VERSION, writable=False)
    target_root.mkdir(parents=True, exist_ok=True)
    for record in records:
        original_sha = record["sha256"]
        for variant in record["variants"]:
            target = target_root / variant["asset_name"]

            def must_not_transform(_: Path) -> tuple[str, int, int, int]:
                raise CacheReplayError("warm replay attempted a derivative transformation")

            cache.materialize(
                original_sha256=original_sha,
                target_width=variant["requested_width"],
                target=target,
                producer=must_not_transform,
            )
    report = cache.report()
    expected_requests = sum(len(record["variants"]) for record in records)
    if report["requests"] != expected_requests or report["hits"] != expected_requests:
        raise CacheReplayError(f"cache replay was not a full hit: {report}")
    return report


def _measure_new_story_baseline(
    records: list[dict[str, Any]],
    cache_root: Path,
    target_root: Path,
    story_images: int,
) -> dict[str, Any]:
    """Measure cache reuse for a deterministic synthetic story fixture."""
    if story_images < 1 or story_images > 100:
        raise ValueError("story_images must be between 1 and 100")

    archive_replay = _replay(records, cache_root, target_root / "archive")
    cache = MediaDerivativeCache(
        cache_root,
        tool_version=MEDIA_TRANSFORM_TOOL_VERSION,
        writable=True,
    )
    new_story_requests = story_images * len(DERIVATIVE_WIDTHS)
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="wirtelprimpf-new-story-") as directory:
        source_root = Path(directory)
        for index in range(story_images):
            width = 1024 + index * 17
            height = 768 + index * 11
            source = source_root / f"story-{index + 1:02d}.png"
            Image.new(
                "RGB",
                (width, height),
                ((index * 37) % 256, (index * 71) % 256, (index * 113) % 256),
            ).save(source, format="PNG")
            original_sha = _sha256(source)
            for target_width in DERIVATIVE_WIDTHS:
                target = target_root / "new-story" / f"story-{index + 1:02d}.w{target_width}.webp"
                cache.materialize(
                    original_sha256=original_sha,
                    target_width=target_width,
                    target=target,
                    producer=lambda path, source=source, width=target_width: _materialize_variant(
                        source, path, width
                    ),
                )
    new_story = cache.report()
    new_story["duration_seconds"] = round(time.perf_counter() - started, 3)
    if (
        new_story["requests"] != new_story_requests
        or new_story["hits"] != 0
        or new_story["misses"] != new_story_requests
        or new_story["writes"] != new_story_requests
        or new_story["invalid_entries"] != 0
    ):
        raise CacheReplayError(f"synthetic new-story run did not start with new keys: {new_story}")

    combined_requests = archive_replay["requests"] + new_story["requests"]
    combined_hits = archive_replay["hits"] + new_story["hits"]
    return {
        "synthetic_fixture": True,
        "story_images": story_images,
        "variants_per_image": 2,
        "archive_replay": archive_replay,
        "new_story": new_story,
        "combined": {
            "requests": combined_requests,
            "hits": combined_hits,
            "misses": new_story["misses"],
            "writes": new_story["writes"],
            "invalid_entries": archive_replay["invalid_entries"] + new_story["invalid_entries"],
            "cache_hit_rate": combined_hits / combined_requests if combined_requests else None,
        },
    }


def measure(
    *,
    source_root: Path,
    manifest_path: Path,
    passes: int = 2,
    cold: bool = False,
    new_story_images: int = 0,
) -> dict[str, Any]:
    if passes < 1 or passes > 5:
        raise ValueError("passes must be between 1 and 5")
    if new_story_images < 0 or new_story_images > 100:
        raise ValueError("new_story_images must be between 0 and 100")
    source_root = source_root.resolve()
    if source_root.is_symlink() or not source_root.is_dir():
        raise CacheReplayError(f"source root must be a regular directory: {source_root}")
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CacheReplayError("cannot read media manifest") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("media"), list):
        raise CacheReplayError("media manifest has no media list")
    records = [_require_mapping(record, "media record") for record in payload["media"]]
    with tempfile.TemporaryDirectory(prefix="wirtelprimpf-cache-replay-", dir=source_root.parent) as directory:
        root = Path(directory)
        cache_root = root / "cache"
        if cold:
            verified_cache = root / "manifest-verified-cache"
            source_report = _prepare_cache(source_root, records, verified_cache)
            shutil.rmtree(verified_cache)
            cold_report = _cold_transform(
                source_root,
                records,
                cache_root,
                root / "cold-targets",
            )
        else:
            source_report = _prepare_cache(source_root, records, cache_root)
            cold_report = None
        replay_reports = [
            _replay(records, cache_root, root / f"targets-{index:02d}")
            for index in range(1, passes + 1)
        ]
        new_story_report = (
            _measure_new_story_baseline(
                records,
                cache_root,
                root / "new-story-targets",
                new_story_images,
            )
            if new_story_images
            else None
        )
    return {
        "schema_version": "1.0.0",
        "source": {
            "root": str(source_root),
            "manifest_records": len(records),
            **source_report,
        },
        "cache_contract": {
            "tool_version": MEDIA_TRANSFORM_TOOL_VERSION,
            "transform_config_version": TRANSFORM_CONFIG_VERSION,
            "target_format": "webp",
            "replay_only": not cold,
            "cold_transform_measured": cold,
            "new_story_baseline_measured": bool(new_story_images),
        },
        "cold_transform": cold_report,
        "replays": replay_reports,
        "new_story_baseline": new_story_report,
        "errors": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=Path("data/media-manifest.json"))
    parser.add_argument("--passes", type=int, default=2)
    parser.add_argument(
        "--measure-cold",
        action="store_true",
        help="transform every manifest derivative from the original into an empty cache",
    )
    parser.add_argument(
        "--new-story-images",
        type=int,
        default=0,
        metavar="N",
        help="measure N deterministic synthetic new-story images against the warm archive cache",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    try:
        report = measure(
            source_root=args.source_root,
            manifest_path=args.manifest,
            passes=args.passes,
            cold=args.measure_cold,
            new_story_images=args.new_story_images,
        )
        rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if args.output:
            output = args.output.resolve()
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
    except (CacheReplayError, OSError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(2, f"media cache replay failed: {exc}\n")
    if args.strict and report["errors"]:
        parser.exit(2, "media cache replay rejected\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
