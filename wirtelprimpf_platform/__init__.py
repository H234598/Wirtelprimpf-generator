"""Operational contracts for the Wirtelprimpf publication platform."""

from .naming import (
    ARCHIVE_CAPACITY,
    BOOKS_PER_ARCHIVE,
    STORIES_PER_BOOK,
    ArchiveTarget,
    BookTarget,
    archive_target_for_volume,
    book_target_for_story,
)
from .state import PlatformState, RotationPhase

__all__ = [
    "ARCHIVE_CAPACITY",
    "BOOKS_PER_ARCHIVE",
    "STORIES_PER_BOOK",
    "ArchiveTarget",
    "BookTarget",
    "PlatformState",
    "RotationPhase",
    "archive_target_for_volume",
    "book_target_for_story",
]

__version__ = "1.0.0"
