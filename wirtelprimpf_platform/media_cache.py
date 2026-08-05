"""Trusted, content-addressed caching for deterministic media derivatives."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

CACHE_SCHEMA_VERSION = "1.0.0"
TRANSFORM_CONFIG_VERSION = "media-transform-v1"
TARGET_FORMAT = "webp"


class MediaCacheError(RuntimeError):
    """The cache cannot be used without weakening the media contract."""


def media_cache_key(
    original_sha256: str,
    sharp_version: str,
    transform_config_version: str,
    target_format: str,
    target_width: int,
) -> str:
    """Bind every input that can change a derivative to one cache identity."""
    if len(original_sha256) != 64 or any(character not in "0123456789abcdef" for character in original_sha256):
        raise MediaCacheError("original_sha256 must be a lowercase SHA-256")
    if not sharp_version or not transform_config_version or not target_format:
        raise MediaCacheError("cache tool, transform, and format versions are required")
    if isinstance(target_width, bool) or not isinstance(target_width, int) or target_width < 1:
        raise MediaCacheError("target_width must be positive")
    material = "\0".join(
        (original_sha256, sharp_version, transform_config_version, target_format, str(target_width))
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class CacheStats:
    requests: int = 0
    hits: int = 0
    misses: int = 0
    writes: int = 0
    invalid_entries: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "requests": self.requests,
            "hits": self.hits,
            "misses": self.misses,
            "writes": self.writes,
            "invalid_entries": self.invalid_entries,
            "cache_hit_rate": (self.hits / self.requests) if self.requests else None,
        }


@dataclass(frozen=True, slots=True)
class CachedDerivative:
    path: Path
    sha256: str
    byte_size: int
    actual_width: int
    actual_height: int


class MediaDerivativeCache:
    """Cache complete derivative entries, never individual unverified bytes."""

    def __init__(
        self,
        root: Path,
        *,
        tool_version: str,
        transform_config_version: str = TRANSFORM_CONFIG_VERSION,
        target_format: str = TARGET_FORMAT,
        writable: bool = True,
    ) -> None:
        self.root = Path(root)
        if self.root.is_symlink():
            raise MediaCacheError(f"cache root must not be a symlink: {self.root}")
        if writable:
            self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
            os.chmod(self.root, 0o700)
        elif self.root.exists() and not self.root.is_dir():
            raise MediaCacheError(f"read-only cache root must be a directory: {self.root}")
        self.tool_version = tool_version
        self.transform_config_version = transform_config_version
        self.target_format = target_format
        self.writable = writable
        self._stats = CacheStats()

    @property
    def stats(self) -> CacheStats:
        return self._stats

    def report(self) -> dict[str, Any]:
        return {
            "schema_version": CACHE_SCHEMA_VERSION,
            "root": str(self.root),
            "tool_version": self.tool_version,
            "transform_config_version": self.transform_config_version,
            "target_format": self.target_format,
            "writable": self.writable,
            **self._stats.as_dict(),
        }

    def _key(self, original_sha256: str, target_width: int) -> str:
        return media_cache_key(
            original_sha256,
            self.tool_version,
            self.transform_config_version,
            self.target_format,
            target_width,
        )

    def _load(self, key: str, *, original_sha256: str, target_width: int) -> CachedDerivative | None:
        entry = self.root / key
        if entry.is_symlink() or not entry.is_dir():
            return None
        metadata_path = entry / "metadata.json"
        derivative = entry / f"derivative.{self.target_format}"
        if (
            metadata_path.is_symlink()
            or derivative.is_symlink()
            or not metadata_path.is_file()
            or not derivative.is_file()
        ):
            return None
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        expected = {
            "schema_version": CACHE_SCHEMA_VERSION,
            "cache_key": key,
            "original_sha256": original_sha256,
            "tool_version": self.tool_version,
            "transform_config_version": self.transform_config_version,
            "target_format": self.target_format,
            "target_width": target_width,
        }
        if any(payload.get(name) != value for name, value in expected.items()):
            return None
        digest = payload.get("sha256")
        byte_size = payload.get("byte_size")
        actual_width = payload.get("actual_width")
        actual_height = payload.get("actual_height")
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
            or isinstance(byte_size, bool)
            or not isinstance(byte_size, int)
            or byte_size < 1
            or isinstance(actual_width, bool)
            or not isinstance(actual_width, int)
            or actual_width < 1
            or isinstance(actual_height, bool)
            or not isinstance(actual_height, int)
            or actual_height < 1
            or derivative.stat().st_size != byte_size
        ):
            return None
        if _sha256_path(derivative) != digest:
            return None
        try:
            with Image.open(derivative) as image:
                image.verify()
            with Image.open(derivative) as image:
                if image.size != (actual_width, actual_height):
                    return None
        except (OSError, ValueError):
            return None
        return CachedDerivative(derivative, digest, byte_size, actual_width, actual_height)

    def _write_metadata(
        self,
        path: Path,
        *,
        key: str,
        original_sha256: str,
        target_width: int,
        result: tuple[str, int, int, int],
    ) -> None:
        digest, byte_size, actual_width, actual_height = result
        payload = {
            "schema_version": CACHE_SCHEMA_VERSION,
            "cache_key": key,
            "original_sha256": original_sha256,
            "tool_version": self.tool_version,
            "transform_config_version": self.transform_config_version,
            "target_format": self.target_format,
            "target_width": target_width,
            "sha256": digest,
            "byte_size": byte_size,
            "actual_width": actual_width,
            "actual_height": actual_height,
        }
        rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())

    def materialize(
        self,
        *,
        original_sha256: str,
        target_width: int,
        target: Path,
        producer: Callable[[Path], tuple[str, int, int, int]],
    ) -> tuple[str, int, int, int]:
        """Copy a verified hit or atomically publish one complete new entry."""
        key = self._key(original_sha256, target_width)
        self._stats = CacheStats(
            requests=self._stats.requests + 1,
            hits=self._stats.hits,
            misses=self._stats.misses,
            writes=self._stats.writes,
            invalid_entries=self._stats.invalid_entries,
        )
        entry = self.root / key
        cached = (
            self._load(key, original_sha256=original_sha256, target_width=target_width)
            if self.root.is_dir()
            else None
        )
        if cached is None and entry.exists() and not entry.is_symlink():
            self._stats = CacheStats(
                requests=self._stats.requests,
                hits=self._stats.hits,
                misses=self._stats.misses,
                writes=self._stats.writes,
                invalid_entries=self._stats.invalid_entries + 1,
            )
        if cached is not None:
            self._stats = CacheStats(
                requests=self._stats.requests,
                hits=self._stats.hits + 1,
                misses=self._stats.misses,
                writes=self._stats.writes,
                invalid_entries=self._stats.invalid_entries,
            )
            if target.is_symlink():
                raise MediaCacheError(f"derivative target must not be a symlink: {target}")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(cached.path, target)
            return cached.sha256, cached.byte_size, cached.actual_width, cached.actual_height

        self._stats = CacheStats(
            requests=self._stats.requests,
            hits=self._stats.hits,
            misses=self._stats.misses + 1,
            writes=self._stats.writes,
            invalid_entries=self._stats.invalid_entries,
        )
        if not self.writable:
            return producer(target)

        temporary = Path(tempfile.mkdtemp(prefix=f".{key}.", dir=self.root))
        produced = temporary / f"derivative.{self.target_format}"
        try:
            result = producer(produced)
            self._write_metadata(
                temporary / "metadata.json",
                key=key,
                original_sha256=original_sha256,
                target_width=target_width,
                result=result,
            )
            try:
                if entry.is_symlink():
                    raise MediaCacheError(f"cache entry must not be a symlink: {entry}")
                if entry.exists():
                    existing = self._load(key, original_sha256=original_sha256, target_width=target_width)
                    if existing is not None:
                        selected = existing
                        temporary = Path()
                        if target.is_symlink():
                            raise MediaCacheError(f"derivative target must not be a symlink: {target}")
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(selected.path, target)
                        return selected.sha256, selected.byte_size, selected.actual_width, selected.actual_height
                    if entry.is_dir():
                        shutil.rmtree(entry)
                    else:
                        entry.unlink()
                os.replace(temporary, entry)
                directory_descriptor = os.open(self.root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
                try:
                    os.fsync(directory_descriptor)
                finally:
                    os.close(directory_descriptor)
                temporary = Path()
                self._stats = CacheStats(
                    requests=self._stats.requests,
                    hits=self._stats.hits,
                    misses=self._stats.misses,
                    writes=self._stats.writes + 1,
                    invalid_entries=self._stats.invalid_entries,
                )
                selected = CachedDerivative(entry / produced.name, result[0], result[1], result[2], result[3])
            except FileExistsError:
                selected = self._load(key, original_sha256=original_sha256, target_width=target_width)
                if selected is None:
                    raise MediaCacheError(
                        f"cache entry race produced an invalid entry: {key}"
                    ) from None
            if target.is_symlink():
                raise MediaCacheError(f"derivative target must not be a symlink: {target}")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(selected.path, target)
            return selected.sha256, selected.byte_size, selected.actual_width, selected.actual_height
        finally:
            if temporary != Path():
                shutil.rmtree(temporary, ignore_errors=True)
