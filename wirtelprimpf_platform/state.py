"""Persistent, restart-safe state for volume completion and archive rotation."""

from __future__ import annotations

import json
import os
import stat
import uuid
from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from pathlib import Path
from typing import Any

from .naming import (
    ARCHIVE_CAPACITY,
    BOOKS_PER_ARCHIVE,
    STORIES_PER_BOOK,
    archive_domain,
    archive_name,
    book_target_for_story,
)

STATE_SCHEMA_VERSION = "1.0.0"


class RotationPhase(StrEnum):
    ARCHIVE_FINALIZED = "ARCHIVE_FINALIZED"
    NEXT_REPOSITORY_RESERVED = "NEXT_REPOSITORY_RESERVED"
    REMOTE_CREATED = "REMOTE_CREATED"
    LOCAL_CLONE_READY = "LOCAL_CLONE_READY"
    RELEASE_AND_PAGES_READY = "RELEASE_AND_PAGES_READY"
    DNS_CREATED = "DNS_CREATED"
    PAGES_DOMAIN_VERIFIED = "PAGES_DOMAIN_VERIFIED"
    CATALOG_UPDATED = "CATALOG_UPDATED"
    ACTIVE_TARGET_SWITCHED = "ACTIVE_TARGET_SWITCHED"
    ROTATION_COMPLETE = "ROTATION_COMPLETE"


@dataclass(frozen=True, slots=True)
class RotationTransaction:
    transaction_id: str
    source_archive_index: int
    target_archive_index: int
    source_repository: str
    target_repository: str
    target_domain: str
    triggering_volume: int
    phase: RotationPhase = RotationPhase.ARCHIVE_FINALIZED
    remote_id: int | None = None
    target_branch: str = "main"
    source_revision: str | None = None
    target_revision: str | None = None
    manifest_sha256: str | None = None

    def __post_init__(self) -> None:
        if not self.transaction_id or len(self.transaction_id) > 128:
            raise ValueError("transaction_id must contain 1 to 128 characters")
        if self.target_archive_index != self.source_archive_index + 1:
            raise ValueError("rotation target must immediately follow source archive")
        if self.target_repository != archive_name(self.target_archive_index):
            raise ValueError("rotation target repository violates naming contract")
        if self.target_domain != archive_domain(self.target_archive_index):
            raise ValueError("rotation target domain violates naming contract")


@dataclass(frozen=True, slots=True)
class PlatformState:
    schema_version: str = STATE_SCHEMA_VERSION
    completed_volumes: int = 0
    current_volume: int = 1
    active_archive_index: int = 1
    rotation: RotationTransaction | None = None

    def __post_init__(self) -> None:
        for label, value, minimum in (
            ("completed_volumes", self.completed_volumes, 0),
            ("current_volume", self.current_volume, 1),
            ("active_archive_index", self.active_archive_index, 1),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
                raise ValueError(f"{label} must be an integer >= {minimum}")
        if self.schema_version != STATE_SCHEMA_VERSION:
            raise ValueError(f"unsupported platform state schema: {self.schema_version!r}")
        if self.current_volume != self.completed_volumes + 1:
            raise ValueError("current_volume must immediately follow completed_volumes")
        expected_active = ((max(1, self.current_volume) - 1) // ARCHIVE_CAPACITY) + 1
        if self.rotation is None and self.active_archive_index != expected_active:
            raise ValueError("active_archive_index does not match current_volume")
        if self.rotation is not None:
            if self.active_archive_index != self.rotation.source_archive_index:
                raise ValueError("active archive must remain the rotation source until cutover")
            if self.rotation.triggering_volume != self.completed_volumes:
                raise ValueError("rotation triggering volume must equal completed volume")

    @property
    def active_repository(self) -> str:
        return archive_name(self.active_archive_index)

    @property
    def generation_blocked(self) -> bool:
        return self.rotation is not None


def complete_volume(state: PlatformState, volume: int, *, transaction_id: str) -> PlatformState:
    """Record exactly the expected full-volume completion.

    Completing each fifth ten-story book (50 stories) stages the next repository transaction and
    blocks generation until ``finish_rotation`` performs the verified cutover.
    """
    if state.rotation is not None:
        raise ValueError("cannot complete a volume while rotation is pending")
    if isinstance(volume, bool) or not isinstance(volume, int):
        raise TypeError("volume must be an integer")
    if volume != state.current_volume:
        raise ValueError(f"expected volume {state.current_volume}, got {volume}")

    next_volume = volume + 1
    if volume % ARCHIVE_CAPACITY:
        return replace(
            state,
            completed_volumes=volume,
            current_volume=next_volume,
        )

    source = state.active_archive_index
    target = source + 1
    transaction = RotationTransaction(
        transaction_id=transaction_id,
        source_archive_index=source,
        target_archive_index=target,
        source_repository=archive_name(source),
        target_repository=archive_name(target),
        target_domain=archive_domain(target),
        triggering_volume=volume,
    )
    return replace(
        state,
        completed_volumes=volume,
        current_volume=next_volume,
        rotation=transaction,
    )


def finish_rotation(state: PlatformState) -> PlatformState:
    """Atomically switch to a fully provisioned rotation target."""
    if state.rotation is None:
        raise ValueError("no rotation is pending")
    return replace(
        state,
        active_archive_index=state.rotation.target_archive_index,
        rotation=None,
    )


def state_to_dict(state: PlatformState) -> dict[str, Any]:
    payload = asdict(state)
    rotation = payload.get("rotation")
    if isinstance(rotation, dict) and isinstance(rotation.get("phase"), RotationPhase):
        rotation["phase"] = rotation["phase"].value
    return payload


def status_to_dict(state: PlatformState) -> dict[str, Any]:
    """Return private operational status plus derived, non-persisted book progress."""
    payload = state_to_dict(state)
    current = book_target_for_story(state.current_volume)
    payload["book"] = {
        "books_per_archive": BOOKS_PER_ARCHIVE,
        "completed_books": state.completed_volumes // STORIES_PER_BOOK,
        "current_book": current.global_book,
        "story_in_book": current.story_in_book,
        "stories_per_book": STORIES_PER_BOOK,
    }
    return payload


def state_from_dict(payload: object) -> PlatformState:
    if not isinstance(payload, dict):
        raise RuntimeError("platform state must be a JSON object")
    allowed = {"schema_version", "completed_volumes", "current_volume", "active_archive_index", "rotation"}
    unknown = set(payload) - allowed
    if unknown:
        raise RuntimeError(f"unknown platform state fields: {sorted(unknown)}")
    rotation_payload = payload.get("rotation")
    rotation: RotationTransaction | None
    if rotation_payload is None:
        rotation = None
    elif isinstance(rotation_payload, dict):
        try:
            rotation = RotationTransaction(
                **{
                    **rotation_payload,
                    "phase": RotationPhase(rotation_payload.get("phase", RotationPhase.ARCHIVE_FINALIZED)),
                }
            )
        except (TypeError, ValueError) as exc:
            raise RuntimeError(f"invalid rotation state: {exc}") from exc
    else:
        raise RuntimeError("rotation state must be an object or null")
    try:
        return PlatformState(
            schema_version=payload.get("schema_version", STATE_SCHEMA_VERSION),
            completed_volumes=payload.get("completed_volumes", 0),
            current_volume=payload.get("current_volume", 1),
            active_archive_index=payload.get("active_archive_index", 1),
            rotation=rotation,
        )
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"invalid platform state: {exc}") from exc


class StateStore:
    """Atomic JSON state store with symlink and permission defenses."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def _reject_symlink(self) -> None:
        if self.path.is_symlink():
            raise RuntimeError(f"platform state path must not be a symlink: {self.path}")
        existing = self.path.parent
        while existing != existing.parent and not existing.exists():
            existing = existing.parent
        if existing.is_symlink():
            raise RuntimeError(f"platform state parent must not be a symlink: {existing}")

    def load(self) -> PlatformState:
        self._reject_symlink()
        if not self.path.exists():
            return PlatformState()
        if not self.path.is_file():
            raise RuntimeError(f"platform state must be a regular file: {self.path}")
        mode = stat.S_IMODE(self.path.stat().st_mode)
        if mode & 0o077:
            raise RuntimeError(f"platform state permissions are too broad: {mode:04o}")
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"cannot read platform state {self.path}: {exc}") from exc
        return state_from_dict(payload)

    def save(self, state: PlatformState) -> None:
        self._reject_symlink()
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.path.parent, 0o700)
        encoded = json.dumps(state_to_dict(state), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        part = self.path.with_name(f".{self.path.name}.{os.getpid()}.{uuid.uuid4().hex}.part")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(part, flags, 0o600)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(part, self.path)
            os.chmod(self.path, 0o600)
            directory_fd = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            part.unlink(missing_ok=True)
