"""Operational contracts for the Wirtelprimpf publication platform."""

from .naming import ARCHIVE_CAPACITY, ArchiveTarget, archive_target_for_volume
from .state import PlatformState, RotationPhase

__all__ = [
    "ARCHIVE_CAPACITY",
    "ArchiveTarget",
    "PlatformState",
    "RotationPhase",
    "archive_target_for_volume",
]

__version__ = "1.0.0"
