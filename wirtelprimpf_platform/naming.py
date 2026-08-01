"""Canonical global-volume, repository, and domain naming rules."""

from __future__ import annotations

from dataclasses import dataclass

ARCHIVE_CAPACITY = 50
STORIES_PER_BOOK = 10
BOOKS_PER_ARCHIVE = ARCHIVE_CAPACITY // STORIES_PER_BOOK
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


@dataclass(frozen=True, slots=True)
class BookTarget:
    global_story: int
    global_book: int
    story_in_book: int
    story_start: int
    story_end: int
    archive_index: int
    book_in_archive: int
    repository: str
    domain: str


def archive_target_for_volume(global_volume: int) -> ArchiveTarget:
    """Map one positive global story to exactly one five-book archive."""
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


def book_target_for_story(global_story: int) -> BookTarget:
    """Map one positive global story to its ten-story book and archive."""
    story = _positive_integer(global_story, label="global_story")
    archive = archive_target_for_volume(story)
    global_book = ((story - 1) // STORIES_PER_BOOK) + 1
    story_start = ((global_book - 1) * STORIES_PER_BOOK) + 1
    return BookTarget(
        global_story=story,
        global_book=global_book,
        story_in_book=((story - 1) % STORIES_PER_BOOK) + 1,
        story_start=story_start,
        story_end=story_start + STORIES_PER_BOOK - 1,
        archive_index=archive.archive_index,
        book_in_archive=((archive.slot - 1) // STORIES_PER_BOOK) + 1,
        repository=archive.repository,
        domain=archive.domain,
    )
