#!/usr/bin/env python3
"""Build a fail-closed web EPUB manifest from verified release evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote

from build_epub import EPUB_MIME, is_valid_epub_bytes


SCHEMA_VERSION = "1.0.0"
_IDENTIFIER = re.compile(r"^[A-Za-z0-9_.-]+$")
_ASSET_NAME = re.compile(r"^[A-Za-z0-9._-]+\.epub$", re.IGNORECASE)
_SHA256 = re.compile(r"^[a-f0-9]{64}$")


class EpubManifestError(ValueError):
    """The local EPUB or its external release evidence is not trustworthy."""


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EpubManifestError(f"{label} must be an object")
    return value


def _positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 1:
        raise EpubManifestError(f"{label} must be a positive integer")
    return value


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _volume_argument(value: str) -> tuple[int, Path]:
    volume_text, separator, path_text = value.partition("=")
    if not separator or not volume_text.isdigit() or not path_text:
        raise argparse.ArgumentTypeError("volume must have the form NUMBER=PATH")
    volume = int(volume_text)
    if volume < 1:
        raise argparse.ArgumentTypeError("volume must be positive")
    return volume, Path(path_text)


def _load_inventory(path: Path, *, release_tag: str) -> dict[str, dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise EpubManifestError(f"cannot read release inventory: {error}") from error
    root = _object(payload, "release inventory")
    if root.get("schema_version") != SCHEMA_VERSION or not isinstance(root.get("assets"), list):
        raise EpubManifestError("unsupported release inventory schema")
    assets: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(root["assets"]):
        item = _object(raw, f"release asset {index}")
        name = item.get("asset_name")
        if not isinstance(name, str) or not _ASSET_NAME.fullmatch(name):
            raise EpubManifestError(f"invalid release asset name: {name!r}")
        if name in assets:
            raise EpubManifestError(f"duplicate release asset: {name}")
        if item.get("release_tag") != release_tag:
            raise EpubManifestError(f"release asset has unexpected tag: {name}")
        if item.get("mime_type") != EPUB_MIME or item.get("header_verified") is not True:
            raise EpubManifestError(f"release asset lacks validated EPUB metadata: {name}")
        if item.get("release_asset_verified") is not True:
            raise EpubManifestError(f"release asset is not externally verified: {name}")
        size = _positive_int(item.get("size_bytes"), f"release asset size ({name})")
        digest = item.get("sha256")
        if not isinstance(digest, str) or not _SHA256.fullmatch(digest.lower()):
            raise EpubManifestError(f"invalid release asset SHA-256: {name}")
        assets[name] = {
            "size_bytes": size,
            "sha256": digest.lower(),
            "mime_type": EPUB_MIME,
        }
    return assets


def _local_path(data_root: Path | None, source: Path) -> str | None:
    if data_root is None:
        return None
    root = data_root.resolve()
    candidate = source.resolve()
    try:
        relative = candidate.relative_to(root)
    except ValueError:
        return None
    if not relative.parts:
        return None
    return relative.as_posix()


def build_manifest(
    entries: list[tuple[int, Path]],
    *,
    owner: str,
    repository: str,
    release_tag: str,
    inventory_path: Path,
    data_root: Path | None = None,
) -> dict[str, Any]:
    if not _IDENTIFIER.fullmatch(owner) or not _IDENTIFIER.fullmatch(repository):
        raise EpubManifestError("owner and repository must be safe GitHub identifiers")
    if not _IDENTIFIER.fullmatch(release_tag):
        raise EpubManifestError("release tag must be a safe identifier")
    if not entries:
        raise EpubManifestError("at least one EPUB is required")
    volumes = [volume for volume, _ in entries]
    if len(set(volumes)) != len(volumes):
        raise EpubManifestError("duplicate EPUB volume")
    inventory = _load_inventory(inventory_path, release_tag=release_tag)
    downloads: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for volume, source in sorted(entries, key=lambda item: item[0]):
        if not source.is_file() or source.is_symlink():
            raise EpubManifestError(f"EPUB source is not a regular file: {source}")
        asset_name = source.name
        if not _ASSET_NAME.fullmatch(asset_name):
            raise EpubManifestError(f"invalid EPUB asset name: {asset_name}")
        if asset_name in seen_names:
            raise EpubManifestError(f"duplicate EPUB asset name: {asset_name}")
        seen_names.add(asset_name)
        data = source.read_bytes()
        if not is_valid_epub_bytes(data):
            raise EpubManifestError(f"invalid EPUB mimetype header: {source}")
        digest = _sha256(data)
        evidence = inventory.get(asset_name)
        if evidence is None:
            raise EpubManifestError(f"missing verified release evidence: {asset_name}")
        if evidence["size_bytes"] != len(data) or evidence["sha256"] != digest:
            raise EpubManifestError(f"local EPUB differs from verified release evidence: {asset_name}")
        url = (
            f"https://github.com/{owner}/{repository}/releases/download/"
            f"{quote(release_tag, safe='')}/{quote(asset_name, safe='')}"
        )
        item: dict[str, Any] = {
            "asset_name": asset_name,
            "header_verified": True,
            "mime_type": EPUB_MIME,
            "release_asset_verified": True,
            "sha256": digest,
            "size_bytes": len(data),
            "url": url,
            "volume": volume,
        }
        local_path = _local_path(data_root, source)
        if local_path is not None:
            item["local_path"] = local_path
        downloads.append(item)
    return {"downloads": downloads, "schema_version": SCHEMA_VERSION}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--release-tag", required=True)
    parser.add_argument("--release-inventory", type=Path, required=True)
    parser.add_argument("--volume", action="append", type=_volume_argument, required=True)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payload = build_manifest(
            args.volume,
            owner=args.owner,
            repository=args.repository,
            release_tag=args.release_tag,
            inventory_path=args.release_inventory,
            data_root=args.data_root,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (EpubManifestError, OSError) as error:
        print(f"build_epub_manifest: {error}", file=sys.stderr)
        return 2
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
