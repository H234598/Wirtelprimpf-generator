"""Public, deterministic catalog of verified Wirtelprimpf archives."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from .naming import ARCHIVE_CAPACITY, STORIES_PER_BOOK, archive_domain, archive_name

CATALOG_SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    archive_index: int
    repository: str
    github_url: str
    pages_url: str
    volume_start: int
    volume_end: int
    active: bool
    sealed: bool
    verified: bool
    revision: str | None = None
    media_manifest_url: str | None = None
    media_manifest_sha256: str | None = None

    @property
    def book_start(self) -> int:
        return ((self.volume_start - 1) // STORIES_PER_BOOK) + 1

    @property
    def book_end(self) -> int:
        return ((self.volume_end - 1) // STORIES_PER_BOOK) + 1

    @classmethod
    def for_archive(
        cls,
        archive_index: int,
        *,
        owner: str,
        active: bool,
        sealed: bool,
        verified: bool,
        revision: str | None = None,
    ) -> CatalogEntry:
        repository = archive_name(archive_index)
        first_volume = ((archive_index - 1) * ARCHIVE_CAPACITY) + 1
        return cls(
            archive_index=archive_index,
            repository=repository,
            github_url=f"https://github.com/{owner}/{repository}",
            pages_url=f"https://{archive_domain(archive_index)}",
            volume_start=first_volume,
            volume_end=first_volume + ARCHIVE_CAPACITY - 1,
            active=active,
            sealed=sealed,
            verified=verified,
            revision=revision,
        )

    def __post_init__(self) -> None:
        if self.repository != archive_name(self.archive_index):
            raise ValueError("catalog repository violates archive naming contract")
        if self.pages_url != f"https://{archive_domain(self.archive_index)}":
            raise ValueError("catalog Pages URL violates archive domain contract")
        expected_start = ((self.archive_index - 1) * ARCHIVE_CAPACITY) + 1
        if (self.volume_start, self.volume_end) != (expected_start, expected_start + ARCHIVE_CAPACITY - 1):
            raise ValueError("catalog story range violates five-book / 50-story contract")


@dataclass(frozen=True, slots=True)
class PublicationCatalog:
    schema_version: str = CATALOG_SCHEMA_VERSION
    active_archive_index: int = 1
    archives: tuple[CatalogEntry, ...] = ()

    def __post_init__(self) -> None:
        if self.schema_version != CATALOG_SCHEMA_VERSION:
            raise ValueError(f"unsupported catalog schema: {self.schema_version!r}")
        indices = [entry.archive_index for entry in self.archives]
        if indices != sorted(set(indices)):
            raise ValueError("catalog archives must be unique and sorted")
        active_entries = [entry.archive_index for entry in self.archives if entry.active]
        if active_entries and active_entries != [self.active_archive_index]:
            raise ValueError("catalog must contain at most the declared active archive")
        if any(not entry.verified for entry in self.archives):
            raise ValueError("unverified archives must not enter the public catalog")

    def entry(self, archive_index: int) -> CatalogEntry | None:
        return next((entry for entry in self.archives if entry.archive_index == archive_index), None)

    def upsert(self, entry: CatalogEntry) -> PublicationCatalog:
        if not entry.verified:
            raise ValueError("cannot publish an unverified catalog entry")
        entries = {item.archive_index: item for item in self.archives}
        entries[entry.archive_index] = entry
        return replace(self, archives=tuple(entries[index] for index in sorted(entries)))

    def with_active(self, archive_index: int) -> PublicationCatalog:
        entries = tuple(
            replace(entry, active=entry.archive_index == archive_index, sealed=entry.archive_index < archive_index)
            for entry in self.archives
        )
        return replace(self, active_archive_index=archive_index, archives=entries)


def _catalog_from_dict(payload: object) -> PublicationCatalog:
    if not isinstance(payload, dict):
        raise RuntimeError("publication catalog must be a JSON object")
    try:
        entries = tuple(_catalog_entry_from_dict(item) for item in payload.get("archives", []))
        return PublicationCatalog(
            schema_version=payload.get("schema_version", CATALOG_SCHEMA_VERSION),
            active_archive_index=payload.get("active_archive_index", 1),
            archives=entries,
        )
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"invalid publication catalog: {exc}") from exc


def _catalog_entry_from_dict(payload: object) -> CatalogEntry:
    if not isinstance(payload, dict):
        raise TypeError("catalog archive entry must be an object")
    values = dict(payload)
    missing = object()
    provided_book_start = values.pop("book_start", missing)
    provided_book_end = values.pop("book_end", missing)
    entry = CatalogEntry(**values)
    for label, provided, expected in (
        ("book_start", provided_book_start, entry.book_start),
        ("book_end", provided_book_end, entry.book_end),
    ):
        if provided is missing:
            continue
        if not isinstance(provided, int) or isinstance(provided, bool) or provided != expected:
            raise ValueError(f"catalog {label} violates derived ten-story book contract")
    return entry


def _catalog_entry_to_dict(entry: CatalogEntry) -> dict[str, object]:
    return {
        **asdict(entry),
        "book_start": entry.book_start,
        "book_end": entry.book_end,
    }


class CatalogStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def load(self) -> PublicationCatalog:
        if self.path.is_symlink():
            raise RuntimeError(f"catalog must not be a symlink: {self.path}")
        if not self.path.exists():
            return PublicationCatalog()
        try:
            return _catalog_from_dict(json.loads(self.path.read_text(encoding="utf-8")))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"cannot read publication catalog {self.path}: {exc}") from exc

    def save(self, catalog: PublicationCatalog) -> None:
        if self.path.is_symlink():
            raise RuntimeError(f"catalog must not be a symlink: {self.path}")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": catalog.schema_version,
            "active_archive_index": catalog.active_archive_index,
            "archives": [_catalog_entry_to_dict(entry) for entry in catalog.archives],
        }
        encoded = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        part = self.path.with_name(f".{self.path.name}.{os.getpid()}.{uuid.uuid4().hex}.part")
        descriptor = os.open(part, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(part, self.path)
            os.chmod(self.path, 0o644)
        finally:
            part.unlink(missing_ok=True)
