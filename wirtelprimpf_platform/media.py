"""Deterministic GitHub Releases media planning, staging, and verification."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import unicodedata
import warnings
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import PIL
from PIL import Image, ImageOps, UnidentifiedImageError

from .media_cache import MediaDerivativeCache
from .naming import archive_name

MEDIA_SCHEMA_VERSION = "1.0.0"
MAX_RELEASE_ASSETS = 1_000
DEFAULT_SOURCE_BYTES_PER_SHARD = 1_500_000_000
MAX_SOURCE_BYTES = 25 * 1024 * 1024
MAX_SOURCE_PIXELS = 50_000_000
UPSCALED_4K_WIDTH = 3840
DERIVATIVE_WIDTHS = (640, 1280, UPSCALED_4K_WIDTH)
DEFAULT_ORIGINALS_PER_SHARD = (MAX_RELEASE_ASSETS - 2) // (1 + len(DERIVATIVE_WIDTHS))
SUPPORTED_SUFFIXES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
TIMESTAMP_IMAGE_RE = re.compile(r"^wirtelprimpf_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}(?:-\d{6})?", re.IGNORECASE)
TEST_IMAGE_RE = re.compile(r"(?:^|[/_.-])(?:test|testbild)(?:$|[/_.-])", re.IGNORECASE)
SAFE_ASSET_RE = re.compile(r"[^A-Za-z0-9._-]+")
PUBLIC_DOWNLOAD_RETRY_DELAYS_SECONDS = (1.0, 2.0, 4.0, 8.0, 15.0, 30.0, 30.0)
DEFAULT_PUBLIC_DOWNLOAD_TIMEOUT_SECONDS = 120.0
MEDIA_TRANSFORM_TOOL_VERSION = f"pillow-{PIL.__version__}"


class MediaError(RuntimeError):
    """Raised when a media migration cannot proceed without data risk."""


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _stable_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _safe_asset_stem(stem: str) -> str:
    normalized = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode("ascii")
    cleaned = SAFE_ASSET_RE.sub("-", normalized).strip(".-_")
    return (cleaned or "media")[:160]


def _path_fingerprint(source_path: str) -> str:
    return hashlib.sha256(source_path.encode("utf-8")).hexdigest()[:8]


def _asset_id(archive_index: int, source_path: str, content_sha256: str) -> str:
    """Return a stable identity that distinguishes byte-identical source records."""
    return f"archive-{archive_index:04d}-{content_sha256[:16]}-{_path_fingerprint(source_path)}"


def _download_url(owner: str, repository: str, tag: str, asset_name: str) -> str:
    return (
        f"https://github.com/{quote(owner, safe='')}/{quote(repository, safe='')}"
        f"/releases/download/{quote(tag, safe='')}/{quote(asset_name, safe='')}"
    )


@dataclass(frozen=True, slots=True)
class MediaRecord:
    source_path: str
    kind: str
    sha256: str
    byte_size: int
    mime_type: str
    width: int
    height: int
    prompt_path: str | None = None
    story_part_path: str | None = None
    alt_text: str | None = None
    alt_text_source: str = "fallback"


@dataclass(frozen=True, slots=True)
class MediaInventory:
    archive_index: int
    records: tuple[MediaRecord, ...]
    ignored_working_paths: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MediaVariant:
    width: int
    asset_name: str
    url: str
    sha256: str | None = None
    byte_size: int | None = None
    actual_width: int | None = None
    actual_height: int | None = None


@dataclass(frozen=True, slots=True)
class PlannedMediaRecord:
    source_path: str
    kind: str
    sha256: str
    byte_size: int
    mime_type: str
    width: int
    height: int
    prompt_path: str | None
    story_part_path: str | None
    asset_id: str
    release_tag: str
    original_asset_name: str
    original_url: str
    variants: tuple[MediaVariant, ...]
    alt_text: str | None = None
    alt_text_source: str = "fallback"


@dataclass(frozen=True, slots=True)
class ReleaseShard:
    tag: str
    index: int
    records: tuple[PlannedMediaRecord, ...]
    bundle_asset_name: str
    manifest_asset_name: str

    @property
    def assets(self) -> tuple[str, ...]:
        names: list[str] = []
        for record in self.records:
            names.append(record.original_asset_name)
            names.extend(variant.asset_name for variant in record.variants)
        names.extend((self.bundle_asset_name, self.manifest_asset_name))
        return tuple(names)


@dataclass(frozen=True, slots=True)
class ReleasePlan:
    owner: str
    repository: str
    archive_index: int
    shards: tuple[ReleaseShard, ...]


@dataclass(frozen=True, slots=True)
class PreparedShard:
    tag: str
    index: int
    records: tuple[PlannedMediaRecord, ...]
    asset_paths: tuple[Path, ...]
    bundle_path: Path
    manifest_path: Path

    @property
    def asset_count(self) -> int:
        return len(self.asset_paths)


@dataclass(frozen=True, slots=True)
class PreparedReleasePlan:
    owner: str
    repository: str
    archive_index: int
    shards: tuple[PreparedShard, ...]
    manifest_path: Path
    cache_report: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class PublishReport:
    expected_assets: int
    uploaded_assets: int
    reused_assets: int
    verified_assets: int


def _kind_for(path: Path, *, story_path: Path | None) -> str:
    lower = path.name.lower()
    if TEST_IMAGE_RE.search(lower):
        return "unknown"
    if story_path is not None:
        return "story"
    if "geburtstag" in lower or "_classic-" in lower or TIMESTAMP_IMAGE_RE.match(path.stem):
        return "classic"
    return "legacy"


def build_media_inventory(source_root: Path, *, archive_index: int) -> MediaInventory:
    """Hash and classify canonical image files without following symlinks."""
    expected_repository = archive_name(archive_index)
    del expected_repository  # validates the index through the canonical naming function
    root = Path(source_root)
    if root.is_symlink() or not root.is_dir():
        raise MediaError(f"media source root must be a non-symlink directory: {root}")
    root = root.resolve()
    records: list[MediaRecord] = []
    ignored: list[str] = []
    casefold_paths: dict[str, str] = {}

    for candidate in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix().casefold()):
        relative = candidate.relative_to(root)
        relative_text = relative.as_posix()
        if relative.parts and relative.parts[0].casefold() == "working":
            if candidate.suffix.lower() in SUPPORTED_SUFFIXES:
                ignored.append(relative_text)
            continue
        if candidate.is_symlink():
            if candidate.suffix.lower() in SUPPORTED_SUFFIXES:
                raise MediaError(f"media source must not be a symlink: {relative_text}")
            continue
        if not candidate.is_file() or candidate.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        folded = relative_text.casefold()
        previous = casefold_paths.get(folded)
        if previous is not None and previous != relative_text:
            raise MediaError(f"case-insensitive path collision: {previous!r} and {relative_text!r}")
        casefold_paths[folded] = relative_text
        source_size = candidate.stat().st_size
        if source_size > MAX_SOURCE_BYTES:
            raise MediaError(
                f"image exceeds source byte limit for {relative_text}: {source_size} > {MAX_SOURCE_BYTES}"
            )
        try:
            prefix = candidate.read_bytes()[:120]
        except OSError as exc:
            raise MediaError(f"cannot inspect image {relative_text}: {exc}") from exc
        if b"git-lfs.github.com/spec/v1" in prefix:
            raise MediaError(f"LFS pointer is not an image: {relative_text}")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(candidate) as image:
                    raw_width, raw_height = image.size
                    if raw_width * raw_height > MAX_SOURCE_PIXELS:
                        raise MediaError(
                            f"image exceeds source pixel limit for {relative_text}: "
                            f"{raw_width * raw_height} > {MAX_SOURCE_PIXELS}"
                        )
                    image.verify()
                with Image.open(candidate) as image:
                    oriented = ImageOps.exif_transpose(image)
                    width, height = oriented.size
                    image_format = (image.format or "").upper()
                    oriented.close()
        except (OSError, UnidentifiedImageError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            raise MediaError(f"invalid image {relative_text}: {exc}") from exc
        expected_formats = {
            ".png": "PNG",
            ".jpg": "JPEG",
            ".jpeg": "JPEG",
            ".webp": "WEBP",
        }
        if image_format != expected_formats[candidate.suffix.lower()]:
            raise MediaError(
                f"image extension/format mismatch for {relative_text}: {candidate.suffix} vs {image_format}"
            )
        stem = candidate.with_suffix("")
        prompt = stem.with_suffix(".txt")
        story = stem.with_suffix(".md")
        prompt_path = prompt.relative_to(root).as_posix() if prompt.is_file() and not prompt.is_symlink() else None
        story_path = story.relative_to(root).as_posix() if story.is_file() and not story.is_symlink() else None
        records.append(
            MediaRecord(
                source_path=relative_text,
                kind=_kind_for(candidate, story_path=story if story_path else None),
                sha256=_sha256_path(candidate),
                byte_size=candidate.stat().st_size,
                mime_type=SUPPORTED_SUFFIXES[candidate.suffix.lower()],
                width=width,
                height=height,
                prompt_path=prompt_path,
                story_part_path=story_path,
            )
        )

    return MediaInventory(
        archive_index=archive_index,
        records=tuple(sorted(records, key=lambda record: record.source_path.casefold())),
        ignored_working_paths=tuple(sorted(ignored)),
    )


def _validate_repository_component(value: str, *, label: str) -> str:
    if not value or not re.fullmatch(r"[A-Za-z0-9_.-]+", value):
        raise ValueError(f"invalid GitHub {label}: {value!r}")
    return value


def build_release_plan(
    inventory: MediaInventory,
    *,
    owner: str,
    repository: str,
    max_originals_per_shard: int = DEFAULT_ORIGINALS_PER_SHARD,
    max_source_bytes_per_shard: int = DEFAULT_SOURCE_BYTES_PER_SHARD,
) -> ReleasePlan:
    """Assign originals and three web derivatives to deterministic release shards."""
    _validate_repository_component(owner, label="owner")
    _validate_repository_component(repository, label="repository")
    if repository != archive_name(inventory.archive_index):
        raise ValueError(
            f"repository {repository!r} does not match archive {inventory.archive_index:04d}"
        )
    max_allowed_originals = (MAX_RELEASE_ASSETS - 2) // (1 + len(DERIVATIVE_WIDTHS))
    if isinstance(max_originals_per_shard, bool) or not 1 <= max_originals_per_shard <= max_allowed_originals:
        raise ValueError(f"max_originals_per_shard must be between 1 and {max_allowed_originals}")
    if max_source_bytes_per_shard < 1:
        raise ValueError("max_source_bytes_per_shard must be positive")

    groups: list[list[MediaRecord]] = []
    current: list[MediaRecord] = []
    current_bytes = 0
    for record in inventory.records:
        exceeds_count = len(current) >= max_originals_per_shard
        exceeds_bytes = bool(current) and current_bytes + record.byte_size > max_source_bytes_per_shard
        if exceeds_count or exceeds_bytes:
            groups.append(current)
            current = []
            current_bytes = 0
        current.append(record)
        current_bytes += record.byte_size
    if current:
        groups.append(current)

    shards: list[ReleaseShard] = []
    for shard_index, source_records in enumerate(groups, start=1):
        tag = f"archive-{inventory.archive_index:04d}-media-{shard_index:04d}"
        planned_records: list[PlannedMediaRecord] = []
        for source in source_records:
            suffix = PurePosixPath(source.source_path).suffix.lower()
            stem = _safe_asset_stem(PurePosixPath(source.source_path).stem)
            path_fingerprint = _path_fingerprint(source.source_path)
            asset_id = _asset_id(inventory.archive_index, source.source_path, source.sha256)
            original_name = f"{stem}--{source.sha256[:16]}--{path_fingerprint}{suffix}"
            variants = tuple(
                MediaVariant(
                    width=width,
                    asset_name=f"{stem}--{source.sha256[:16]}--{path_fingerprint}.w{width}.webp",
                    url=_download_url(
                        owner,
                        repository,
                        tag,
                        f"{stem}--{source.sha256[:16]}--{path_fingerprint}.w{width}.webp",
                    ),
                )
                for width in DERIVATIVE_WIDTHS
            )
            planned_records.append(
                PlannedMediaRecord(
                    **source.__dict__ if hasattr(source, "__dict__") else {
                        "source_path": source.source_path,
                        "kind": source.kind,
                        "sha256": source.sha256,
                        "byte_size": source.byte_size,
                        "mime_type": source.mime_type,
                        "width": source.width,
                        "height": source.height,
                        "prompt_path": source.prompt_path,
                        "story_part_path": source.story_part_path,
                    },
                    asset_id=asset_id,
                    release_tag=tag,
                    original_asset_name=original_name,
                    original_url=_download_url(owner, repository, tag, original_name),
                    variants=variants,
                )
            )
        shard = ReleaseShard(
            tag=tag,
            index=shard_index,
            records=tuple(planned_records),
            bundle_asset_name=f"{tag}-originals.zip",
            manifest_asset_name=f"{tag}-manifest.json",
        )
        if len(shard.assets) >= MAX_RELEASE_ASSETS:
            raise ValueError(f"release shard {tag} would contain {len(shard.assets)} assets")
        shards.append(shard)

    return ReleasePlan(
        owner=owner,
        repository=repository,
        archive_index=inventory.archive_index,
        shards=tuple(shards),
    )


def _assert_source(path: Path, root: Path, expected_sha256: str) -> None:
    try:
        display_path = path.relative_to(root).as_posix()
    except ValueError:
        display_path = path.name or "<outside-media-root>"
    if path.is_symlink() or not path.is_file():
        raise MediaError(f"source is no longer a regular file: {display_path}")
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise MediaError(f"source escaped media root: {display_path}") from exc
    actual = _sha256_path(path)
    if actual != expected_sha256:
        raise MediaError(f"source changed after inventory: {display_path} ({expected_sha256} != {actual})")


def _materialize_variant(source: Path, target: Path, target_width: int) -> tuple[str, int, int, int]:
    with Image.open(source) as image:
        converted = ImageOps.exif_transpose(image).convert("RGB")
    converted.info.clear()
    try:
        if converted.width > target_width or target_width == UPSCALED_4K_WIDTH:
            height = max(1, round(converted.height * target_width / converted.width))
            converted = converted.resize((target_width, height), Image.Resampling.LANCZOS)
        if target_width == UPSCALED_4K_WIDTH:
            converted.save(target, format="WEBP", lossless=True, quality=100, method=6, exif=b"")
        else:
            converted.save(target, format="WEBP", quality=82, method=6, exif=b"")
        actual_width, actual_height = converted.size
    finally:
        converted.close()
    return _sha256_path(target), target.stat().st_size, actual_width, actual_height


def _write_deterministic_bundle(
    path: Path,
    records: Sequence[PlannedMediaRecord],
    asset_paths: dict[str, Path],
) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as bundle:
        for record in sorted(records, key=lambda item: item.source_path.casefold()):
            source = asset_paths[record.original_asset_name]
            info = zipfile.ZipInfo(record.source_path, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            with source.open("rb") as handle:
                bundle.writestr(info, handle.read())


def _record_manifest(record: PlannedMediaRecord) -> dict[str, Any]:
    return {
        "asset_id": record.asset_id,
        "source_path": record.source_path,
        "kind": record.kind,
        "sha256": record.sha256,
        "byte_size": record.byte_size,
        "mime_type": record.mime_type,
        "width": record.width,
        "height": record.height,
        "prompt_path": record.prompt_path,
        "story_part_path": record.story_part_path,
        "alt_text": record.alt_text,
        "alt_text_source": record.alt_text_source,
        "release_tag": record.release_tag,
        "original": {
            "asset_name": record.original_asset_name,
            "url": record.original_url,
        },
        "variants": [
            {
                "requested_width": variant.width,
                "actual_width": variant.actual_width,
                "actual_height": variant.actual_height,
                "asset_name": variant.asset_name,
                "url": variant.url,
                "sha256": variant.sha256,
                "byte_size": variant.byte_size,
                "mime_type": "image/webp",
            }
            for variant in record.variants
        ],
    }


def materialize_release_plan(
    plan: ReleasePlan,
    *,
    source_root: Path,
    staging_root: Path,
    cache_root: Path | None = None,
    cache_read_only: bool = False,
) -> PreparedReleasePlan:
    """Create verified originals, WebP derivatives, deterministic bundles, and manifests."""
    source_root = Path(source_root).resolve()
    staging = Path(staging_root)
    if staging.is_symlink():
        raise MediaError(f"staging root must not be a symlink: {staging}")
    staging.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(staging, 0o700)
    cache = (
        MediaDerivativeCache(
            cache_root,
            tool_version=MEDIA_TRANSFORM_TOOL_VERSION,
            writable=not cache_read_only,
        )
        if cache_root is not None
        else None
    )
    prepared_shards: list[PreparedShard] = []
    all_records: list[PlannedMediaRecord] = []

    for shard in plan.shards:
        shard_dir = staging / shard.tag
        if shard_dir.is_symlink():
            raise MediaError(f"shard staging path must not be a symlink: {shard_dir}")
        shard_dir.mkdir(parents=True, exist_ok=True)
        prepared_records: list[PlannedMediaRecord] = []
        asset_paths_by_name: dict[str, Path] = {}
        ordered_asset_paths: list[Path] = []

        for record in shard.records:
            source = source_root / PurePosixPath(record.source_path)
            _assert_source(source, source_root, record.sha256)
            original = shard_dir / record.original_asset_name
            shutil.copyfile(source, original)
            if _sha256_path(original) != record.sha256:
                raise MediaError(f"staged original hash mismatch: {record.source_path}")
            asset_paths_by_name[record.original_asset_name] = original
            ordered_asset_paths.append(original)
            variants: list[MediaVariant] = []
            for variant in record.variants:
                variant_path = shard_dir / variant.asset_name
                if cache is None:
                    digest, size, actual_width, actual_height = _materialize_variant(source, variant_path, variant.width)
                else:
                    digest, size, actual_width, actual_height = cache.materialize(
                        original_sha256=record.sha256,
                        target_width=variant.width,
                        target=variant_path,
                        producer=lambda target, source=source, width=variant.width: _materialize_variant(
                            source, target, width
                        ),
                    )
                prepared_variant = replace(
                    variant,
                    sha256=digest,
                    byte_size=size,
                    actual_width=actual_width,
                    actual_height=actual_height,
                )
                variants.append(prepared_variant)
                asset_paths_by_name[variant.asset_name] = variant_path
                ordered_asset_paths.append(variant_path)
            prepared_records.append(replace(record, variants=tuple(variants)))

        bundle_path = shard_dir / shard.bundle_asset_name
        _write_deterministic_bundle(bundle_path, prepared_records, asset_paths_by_name)
        ordered_asset_paths.append(bundle_path)
        shard_manifest = {
            "schema_version": MEDIA_SCHEMA_VERSION,
            "archive_repository": plan.repository,
            "release_tag": shard.tag,
            "bundle": {
                "asset_name": bundle_path.name,
                "sha256": _sha256_path(bundle_path),
                "byte_size": bundle_path.stat().st_size,
            },
            "media": [_record_manifest(record) for record in prepared_records],
        }
        manifest_path = shard_dir / shard.manifest_asset_name
        manifest_path.write_text(_stable_json(shard_manifest), encoding="utf-8", newline="\n")
        ordered_asset_paths.append(manifest_path)
        if len(ordered_asset_paths) >= MAX_RELEASE_ASSETS:
            raise MediaError(f"prepared shard {shard.tag} exceeds GitHub asset limit")
        prepared = PreparedShard(
            tag=shard.tag,
            index=shard.index,
            records=tuple(prepared_records),
            asset_paths=tuple(ordered_asset_paths),
            bundle_path=bundle_path,
            manifest_path=manifest_path,
        )
        prepared_shards.append(prepared)
        all_records.extend(prepared_records)

    manifest = {
        "schema_version": MEDIA_SCHEMA_VERSION,
        "archive_index": plan.archive_index,
        "archive_repository": plan.repository,
        "owner": plan.owner,
        "media_count": len(all_records),
        "shards": [
            {
                "index": shard.index,
                "tag": shard.tag,
                "open": False,
                "record_count": len(shard.records),
                "asset_count": shard.asset_count,
                "manifest_asset_name": shard.manifest_path.name,
                "manifest_sha256": _sha256_path(shard.manifest_path),
                "bundle_asset_name": shard.bundle_path.name,
                "bundle_sha256": _sha256_path(shard.bundle_path),
            }
            for shard in prepared_shards
        ],
        "media": [_record_manifest(record) for record in all_records],
    }
    manifest_path = staging / f"archive-{plan.archive_index:04d}-media-manifest.json"
    manifest_path.write_text(_stable_json(manifest), encoding="utf-8", newline="\n")
    return PreparedReleasePlan(
        owner=plan.owner,
        repository=plan.repository,
        archive_index=plan.archive_index,
        shards=tuple(prepared_shards),
        manifest_path=manifest_path,
        cache_report=cache.report() if cache is not None else None,
    )


class ReleaseBackend(Protocol):
    def ensure_release(self, tag: str, *, title: str, notes: str) -> None: ...

    def asset_names(self, tag: str) -> set[str]: ...

    def upload_asset(self, tag: str, path: Path) -> None: ...

    def download_asset(self, tag: str, asset_name: str, destination: Path) -> None: ...


def publish_release_plan(plan: PreparedReleasePlan, *, backend: ReleaseBackend) -> PublishReport:
    """Upload idempotently and download-reverify every local/remote byte pair."""
    expected = sum(shard.asset_count for shard in plan.shards)
    uploaded = 0
    reused = 0
    verified = 0
    with tempfile.TemporaryDirectory(prefix="wirtelprimpf-release-verify-") as temporary:
        verification_root = Path(temporary)
        for shard in plan.shards:
            backend.ensure_release(
                shard.tag,
                title=f"Wirtelprimpf Archiv {plan.archive_index:04d} - Medien {shard.index:04d}",
                notes=(
                    "Automatisch erzeugter, SHA-256-verifizierter Medienschwarm. "
                    "Originale, Webderivate, Manifest und reproduzierbares Originalpaket."
                ),
            )
            existing = backend.asset_names(shard.tag)
            for local in shard.asset_paths:
                destination = verification_root / f"{shard.index:04d}-{local.name}"
                if local.name in existing:
                    backend.download_asset(shard.tag, local.name, destination)
                    if _sha256_path(destination) != _sha256_path(local):
                        raise MediaError(
                            f"remote asset hash mismatch; refusing overwrite: {shard.tag}/{local.name}"
                        )
                    reused += 1
                    verified += 1
                    destination.unlink()
                    continue
                backend.upload_asset(shard.tag, local)
                uploaded += 1
                backend.download_asset(shard.tag, local.name, destination)
                if _sha256_path(destination) != _sha256_path(local):
                    raise MediaError(f"uploaded asset hash mismatch: {shard.tag}/{local.name}")
                verified += 1
                destination.unlink()
    return PublishReport(
        expected_assets=expected,
        uploaded_assets=uploaded,
        reused_assets=reused,
        verified_assets=verified,
    )


class GitHubReleaseBackend:
    """Release backend using authenticated ``gh`` writes and public HTTP reads."""

    def __init__(
        self,
        owner: str,
        repository: str,
        *,
        timeout_seconds: int = 1_800,
        public_download_timeout_seconds: float = DEFAULT_PUBLIC_DOWNLOAD_TIMEOUT_SECONDS,
    ) -> None:
        self.owner = _validate_repository_component(owner, label="owner")
        self.repository = _validate_repository_component(repository, label="repository")
        self.slug = f"{self.owner}/{self.repository}"
        self.timeout_seconds = timeout_seconds
        if public_download_timeout_seconds <= 0:
            raise ValueError("public_download_timeout_seconds must be positive")
        self.public_download_timeout_seconds = public_download_timeout_seconds

    def _run(self, command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                command,
                check=check,
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise MediaError(f"GitHub command failed: {command[0]} {command[1]}: {exc}") from exc

    def ensure_release(self, tag: str, *, title: str, notes: str) -> None:
        result = self._run(["gh", "release", "view", tag, "--repo", self.slug], check=False)
        if result.returncode == 0:
            return
        create = self._run(
            [
                "gh",
                "release",
                "create",
                tag,
                "--repo",
                self.slug,
                "--title",
                title,
                "--notes",
                notes,
                "--latest=false",
            ],
            check=False,
        )
        if create.returncode != 0:
            raise MediaError(f"cannot create release {tag}: {create.stderr.strip()}")

    def asset_names(self, tag: str) -> set[str]:
        result = self._run(["gh", "release", "view", tag, "--repo", self.slug, "--json", "assets"])
        try:
            payload = json.loads(result.stdout)
            return {asset["name"] for asset in payload.get("assets", []) if isinstance(asset, dict)}
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise MediaError(f"invalid asset listing for release {tag}") from exc

    def upload_asset(self, tag: str, path: Path) -> None:
        result = self._run(
            ["gh", "release", "upload", tag, str(path), "--repo", self.slug],
            check=False,
        )
        if result.returncode != 0:
            raise MediaError(f"cannot upload {tag}/{path.name}: {result.stderr.strip()}")

    def download_asset(self, tag: str, asset_name: str, destination: Path) -> None:
        url = _download_url(self.owner, self.repository, tag, asset_name)
        request = Request(url, headers={"User-Agent": "Wirtelprimpf-generator/1.0"})
        for attempt in range(len(PUBLIC_DOWNLOAD_RETRY_DELAYS_SECONDS) + 1):
            try:
                with (
                    urlopen(request, timeout=self.public_download_timeout_seconds) as response,
                    destination.open("xb") as output,
                ):
                    shutil.copyfileobj(response, output, length=1024 * 1024)
                return
            except HTTPError as exc:
                destination.unlink(missing_ok=True)
                exc.close()
                if exc.code == 404 and attempt < len(PUBLIC_DOWNLOAD_RETRY_DELAYS_SECONDS):
                    time.sleep(PUBLIC_DOWNLOAD_RETRY_DELAYS_SECONDS[attempt])
                    continue
                raise MediaError(f"cannot download public asset {tag}/{asset_name}: {exc}") from exc
            except (TimeoutError, URLError) as exc:
                destination.unlink(missing_ok=True)
                if attempt < len(PUBLIC_DOWNLOAD_RETRY_DELAYS_SECONDS):
                    time.sleep(PUBLIC_DOWNLOAD_RETRY_DELAYS_SECONDS[attempt])
                    continue
                raise MediaError(f"cannot download public asset {tag}/{asset_name}: {exc}") from exc
            except (OSError, ValueError) as exc:
                destination.unlink(missing_ok=True)
                raise MediaError(f"cannot download public asset {tag}/{asset_name}: {exc}") from exc
