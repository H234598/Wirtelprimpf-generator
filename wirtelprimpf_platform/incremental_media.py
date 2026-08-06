"""Restart-safe publication of newly generated images through GitHub Releases."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from PIL import Image, UnidentifiedImageError

from .media import (
    DERIVATIVE_WIDTHS,
    MAX_RELEASE_ASSETS,
    MEDIA_SCHEMA_VERSION,
    SUPPORTED_SUFFIXES,
    MediaError,
    MediaVariant,
    PlannedMediaRecord,
    ReleaseBackend,
    _asset_id,
    _download_url,
    _materialize_variant,
    _path_fingerprint,
    _record_manifest,
    _safe_asset_stem,
    _sha256_path,
    _stable_json,
    _validate_repository_component,
    MEDIA_TRANSFORM_TOOL_VERSION,
)
from .media_cache import MediaDerivativeCache
from .naming import archive_name

ASSETS_PER_RECORD = 2 + len(DERIVATIVE_WIDTHS)
DEFAULT_RECORDS_PER_SHARD = (MAX_RELEASE_ASSETS - 1) // ASSETS_PER_RECORD


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _repository_path(value: str | None, *, label: str) -> str | None:
    if value is None:
        return None
    candidate = PurePosixPath(value)
    if not value or candidate.is_absolute() or ".." in candidate.parts or "." in candidate.parts:
        raise MediaError(f"invalid repository-relative {label}: {value!r}")
    normalized = candidate.as_posix()
    if normalized != value or value.startswith("/"):
        raise MediaError(f"non-canonical repository-relative {label}: {value!r}")
    return normalized


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    parent = path.parent
    if parent.is_symlink():
        raise MediaError(f"manifest directory must not be a symlink: {parent}")
    parent.mkdir(parents=True, exist_ok=True, mode=0o755)
    if path.is_symlink():
        raise MediaError(f"manifest must not be a symlink: {path}")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(_stable_json(payload))
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
        directory_descriptor = os.open(parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        temporary.unlink(missing_ok=True)


class IncrementalMediaPublisher:
    """Append one immutable, publicly verified media record to an archive."""

    def __init__(
        self,
        *,
        owner: str,
        repository: str,
        archive_index: int,
        manifest_path: Path,
        staging_root: Path,
        backend: ReleaseBackend,
        max_records_per_shard: int = DEFAULT_RECORDS_PER_SHARD,
        cache_root: Path | None = None,
        cache_read_only: bool = False,
    ) -> None:
        self.owner = _validate_repository_component(owner, label="owner")
        self.repository = _validate_repository_component(repository, label="repository")
        if self.repository != archive_name(archive_index):
            raise ValueError(
                f"repository {self.repository!r} does not match archive {archive_index:04d}"
            )
        if (
            isinstance(max_records_per_shard, bool)
            or max_records_per_shard < 1
            or max_records_per_shard * ASSETS_PER_RECORD >= MAX_RELEASE_ASSETS
        ):
            raise ValueError("max_records_per_shard must leave room below the GitHub asset limit")
        self.archive_index = archive_index
        self.manifest_path = Path(manifest_path)
        self.staging_root = Path(staging_root)
        self.backend = backend
        self.max_records_per_shard = max_records_per_shard
        self.cache = (
            MediaDerivativeCache(
                cache_root,
                tool_version=MEDIA_TRANSFORM_TOOL_VERSION,
                writable=not cache_read_only,
            )
            if cache_root is not None
            else None
        )

    @property
    def cache_report(self) -> dict[str, Any] | None:
        return self.cache.report() if self.cache is not None else None

    def _empty_manifest(self) -> dict[str, Any]:
        return {
            "schema_version": MEDIA_SCHEMA_VERSION,
            "archive_index": self.archive_index,
            "archive_repository": self.repository,
            "owner": self.owner,
            "generated_at": None,
            "media_count": 0,
            "shards": [],
            "media": [],
        }

    def _load_manifest(self) -> dict[str, Any]:
        if self.manifest_path.is_symlink():
            raise MediaError(f"manifest must not be a symlink: {self.manifest_path}")
        if not self.manifest_path.exists():
            return self._empty_manifest()
        try:
            payload = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise MediaError(f"cannot read media manifest: {self.manifest_path}") from exc
        if not isinstance(payload, dict):
            raise MediaError("media manifest must be an object")
        if payload.get("schema_version") != MEDIA_SCHEMA_VERSION:
            raise MediaError("unsupported media manifest schema")
        if payload.get("archive_index") != self.archive_index:
            raise MediaError("media manifest archive index mismatch")
        if payload.get("archive_repository") != self.repository:
            raise MediaError("media manifest repository mismatch")
        media = payload.get("media")
        shards = payload.get("shards")
        if not isinstance(media, list) or not isinstance(shards, list):
            raise MediaError("media manifest requires media and shards arrays")
        if payload.get("media_count") != len(media):
            raise MediaError("media manifest count mismatch")
        return payload

    def _select_shard(self, payload: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        shards = payload["shards"]
        seen: set[int] = set()
        highest = 0
        selected: dict[str, Any] | None = None
        for raw in shards:
            if not isinstance(raw, dict):
                raise MediaError("invalid media shard entry")
            index = raw.get("index")
            tag = raw.get("tag")
            if not isinstance(index, int) or isinstance(index, bool) or index < 1 or index in seen:
                raise MediaError("invalid or duplicate media shard index")
            expected_tag = f"archive-{self.archive_index:04d}-media-{index:04d}"
            if tag != expected_tag:
                raise MediaError(f"media shard tag mismatch: {tag!r}")
            seen.add(index)
            highest = max(highest, index)
            # Migration shards created before incremental publishing did not carry
            # an ``open`` field. Missing therefore deliberately means sealed.
            if raw.get("open") is True:
                count = raw.get("record_count")
                if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                    raise MediaError(f"invalid record count for open shard {tag}")
                if count >= self.max_records_per_shard:
                    raw["open"] = False
                elif selected is None or index > selected["index"]:
                    if selected is not None:
                        selected["open"] = False
                    selected = raw
                else:
                    raw["open"] = False
        if selected is not None:
            return selected, False
        index = highest + 1
        selected = {
            "index": index,
            "tag": f"archive-{self.archive_index:04d}-media-{index:04d}",
            "open": True,
            "record_count": 0,
            "asset_count": 0,
        }
        shards.append(selected)
        return selected, True

    def _prepare_record(
        self,
        source: Path,
        *,
        source_path: str,
        kind: str,
        prompt_path: str | None,
        story_part_path: str | None,
        tag: str,
    ) -> tuple[dict[str, Any], tuple[Path, ...]]:
        if source.is_symlink() or not source.is_file():
            raise MediaError(f"media source must be a regular non-symlink file: {source}")
        suffix = source.suffix.lower()
        if suffix not in SUPPORTED_SUFFIXES:
            raise MediaError(f"unsupported media type: {source.suffix}")
        try:
            with Image.open(source) as image:
                image.verify()
            with Image.open(source) as image:
                width, height = image.size
                image_format = (image.format or "").upper()
        except (OSError, UnidentifiedImageError, ValueError) as exc:
            raise MediaError(f"invalid image: {source}") from exc
        expected_format = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG", ".webp": "WEBP"}[suffix]
        if image_format != expected_format:
            raise MediaError(f"image extension/format mismatch: {source}")

        digest = _sha256_path(source)
        safe_stem = _safe_asset_stem(source.stem)
        path_fingerprint = _path_fingerprint(source_path)
        asset_id = _asset_id(self.archive_index, source_path, digest)
        original_name = f"{safe_stem}--{digest[:16]}--{path_fingerprint}{suffix}"
        shard_dir = self.staging_root / tag
        if self.staging_root.is_symlink() or shard_dir.is_symlink():
            raise MediaError("media staging paths must not be symlinks")
        shard_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.staging_root, 0o700)
        os.chmod(shard_dir, 0o700)

        original = shard_dir / original_name
        shutil.copyfile(source, original)
        if _sha256_path(original) != digest:
            raise MediaError(f"staged original hash mismatch: {source}")
        variants: list[MediaVariant] = []
        paths: list[Path] = [original]
        for requested_width in DERIVATIVE_WIDTHS:
            asset_name = f"{safe_stem}--{digest[:16]}--{path_fingerprint}.w{requested_width}.webp"
            target = shard_dir / asset_name
            if self.cache is None:
                variant_digest, byte_size, actual_width, actual_height = _materialize_variant(
                    source, target, requested_width
                )
            else:
                variant_digest, byte_size, actual_width, actual_height = self.cache.materialize(
                    original_sha256=digest,
                    target_width=requested_width,
                    target=target,
                    producer=lambda output, source=source, width=requested_width: _materialize_variant(
                        source, output, width
                    ),
                )
            variants.append(
                MediaVariant(
                    width=requested_width,
                    asset_name=asset_name,
                    url=_download_url(self.owner, self.repository, tag, asset_name),
                    sha256=variant_digest,
                    byte_size=byte_size,
                    actual_width=actual_width,
                    actual_height=actual_height,
                )
            )
            paths.append(target)

        planned = PlannedMediaRecord(
            source_path=source_path,
            kind=kind,
            sha256=digest,
            byte_size=source.stat().st_size,
            mime_type=SUPPORTED_SUFFIXES[suffix],
            width=width,
            height=height,
            prompt_path=prompt_path,
            story_part_path=story_part_path,
            asset_id=asset_id,
            release_tag=tag,
            original_asset_name=original_name,
            original_url=_download_url(self.owner, self.repository, tag, original_name),
            variants=tuple(variants),
        )
        sidecar_payload = _record_manifest(planned)
        sidecar_name = f"{safe_stem}--{digest[:16]}--{path_fingerprint}.record.json"
        sidecar = shard_dir / sidecar_name
        sidecar.write_text(_stable_json(sidecar_payload), encoding="utf-8", newline="\n")
        sidecar_digest = _sha256_path(sidecar)
        record = dict(sidecar_payload)
        record["record"] = {
            "asset_name": sidecar_name,
            "url": _download_url(self.owner, self.repository, tag, sidecar_name),
            "sha256": sidecar_digest,
            "byte_size": sidecar.stat().st_size,
        }
        paths.append(sidecar)
        return record, tuple(paths)

    def _verify_assets(self, tag: str, paths: tuple[Path, ...]) -> None:
        self.backend.ensure_release(
            tag,
            title=f"Wirtelprimpf Archiv {self.archive_index:04d} - Medien",
            notes=(
                "Automatisch erzeugte, unveränderliche und öffentlich SHA-256-verifizierte "
                "Originale, Webderivate und Datensätze."
            ),
        )
        existing = self.backend.asset_names(tag)
        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-incremental-verify-") as temporary:
            root = Path(temporary)
            for local in paths:
                if local.name not in existing:
                    self.backend.upload_asset(tag, local)
                downloaded = root / local.name
                self.backend.download_asset(tag, local.name, downloaded)
                if _sha256_path(downloaded) != _sha256_path(local):
                    action = "existing" if local.name in existing else "uploaded"
                    raise MediaError(f"{action} release asset hash mismatch: {tag}/{local.name}")

    def _verify_existing_record(self, record: dict[str, Any]) -> None:
        tag = record.get("release_tag")
        original = record.get("original")
        variants = record.get("variants")
        sidecar = record.get("record")
        if not isinstance(tag, str) or not isinstance(original, dict) or not isinstance(variants, list):
            raise MediaError("existing incremental media record is malformed")
        expected: list[tuple[str, str]] = []
        original_name = original.get("asset_name")
        original_sha = record.get("sha256")
        if not isinstance(original_name, str) or not isinstance(original_sha, str):
            raise MediaError("existing media original is malformed")
        expected.append((original_name, original_sha))
        for variant in variants:
            if (
                not isinstance(variant, dict)
                or not isinstance(variant.get("asset_name"), str)
                or not isinstance(variant.get("sha256"), str)
            ):
                raise MediaError("existing media variant is malformed")
            expected.append((variant["asset_name"], variant["sha256"]))
        if (
            isinstance(sidecar, dict)
            and isinstance(sidecar.get("asset_name"), str)
            and isinstance(sidecar.get("sha256"), str)
        ):
            expected.append((sidecar["asset_name"], sidecar["sha256"]))
        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-idempotency-verify-") as temporary:
            root = Path(temporary)
            names = self.backend.asset_names(tag)
            for asset_name, expected_sha in expected:
                if asset_name not in names:
                    raise MediaError(f"published release asset is missing: {tag}/{asset_name}")
                destination = root / asset_name
                self.backend.download_asset(tag, asset_name, destination)
                if _sha256_path(destination) != expected_sha:
                    raise MediaError(f"published release asset hash mismatch: {tag}/{asset_name}")

    def publish(
        self,
        source: Path,
        *,
        source_path: str,
        kind: str,
        prompt_path: str | None = None,
        story_part_path: str | None = None,
    ) -> dict[str, Any]:
        """Publish one image and atomically append its verified manifest record."""
        if kind not in {"story", "classic", "legacy", "unknown"}:
            raise MediaError(f"invalid media kind: {kind!r}")
        source_path = _repository_path(source_path, label="source path") or ""
        prompt_path = _repository_path(prompt_path, label="prompt path")
        story_part_path = _repository_path(story_part_path, label="story part path")
        source = Path(source)
        if source.is_symlink() or not source.is_file():
            raise MediaError(f"media source must be a regular non-symlink file: {source}")
        source_digest = _sha256_path(source)
        asset_id = _asset_id(self.archive_index, source_path, source_digest)

        payload = self._load_manifest()
        for raw in payload["media"]:
            if not isinstance(raw, dict):
                raise MediaError("invalid media record in manifest")
            if raw.get("source_path") == source_path and raw.get("sha256") != source_digest:
                raise MediaError(f"immutable media source path changed: {source_path}")
            if raw.get("asset_id") == asset_id:
                if raw.get("source_path") != source_path or raw.get("sha256") != source_digest:
                    raise MediaError(f"media asset identity collision: {asset_id}")
                self._verify_existing_record(raw)
                return raw

        shard, created = self._select_shard(payload)
        try:
            record, paths = self._prepare_record(
                source,
                source_path=source_path,
                kind=kind,
                prompt_path=prompt_path,
                story_part_path=story_part_path,
                tag=shard["tag"],
            )
            self._verify_assets(shard["tag"], paths)
        except Exception:
            # A newly selected shard is not persisted until all assets are verified.
            if created:
                payload["shards"].remove(shard)
            raise

        shard["record_count"] = int(shard.get("record_count", 0)) + 1
        shard["asset_count"] = int(shard.get("asset_count", 0)) + len(paths)
        payload["media"].append(record)
        payload["media_count"] = len(payload["media"])
        payload["generated_at"] = _utc_now()
        payload.setdefault("owner", self.owner)
        _atomic_json(self.manifest_path, payload)
        return record
