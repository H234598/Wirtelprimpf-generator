"""Canonical global-volume, repository, and domain naming rules."""

from __future__ import annotations

from dataclasses import dataclass

ARCHIVE_CAPACITY = 50
MAX_ARCHIVE_INDEX = 9_999
REPOSITORY_PREFIX = "Wirtelprimpf"
DOMAIN_SUFFIX = "telacore.org"


def _positive_integer(value: int, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an integer")
    if value < 1:
        raise ValueError(f"{label} must be positive")
    return value


def archive_name(archive_index: int) -> str:
    """Return the canonical case-preserving GitHub repository name."""
    index = _positive_integer(archive_index, label="archive_index")
    if index > MAX_ARCHIVE_INDEX:
        raise ValueError(f"archive_index must be <= {MAX_ARCHIVE_INDEX}")
    return f"{REPOSITORY_PREFIX}-{index:04d}"


def archive_domain(archive_index: int) -> str:
    """Return the canonical lower-case custom domain for an archive."""
    return f"{archive_name(archive_index).lower()}.{DOMAIN_SUFFIX}"


@dataclass(frozen=True, slots=True)
class ArchiveTarget:
    global_volume: int
    archive_index: int
    slot: int
    repository: str
    domain: str


def archive_target_for_volume(global_volume: int) -> ArchiveTarget:
    """Map one positive global story volume to exactly one 50-volume archive."""
    volume = _positive_integer(global_volume, label="global_volume")
    archive_index = ((volume - 1) // ARCHIVE_CAPACITY) + 1
    slot = ((volume - 1) % ARCHIVE_CAPACITY) + 1
    return ArchiveTarget(
        global_volume=volume,
        archive_index=archive_index,
        slot=slot,
        repository=archive_name(archive_index),
        domain=archive_domain(archive_index),
    )
