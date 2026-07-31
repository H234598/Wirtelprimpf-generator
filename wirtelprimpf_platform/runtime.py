"""Crash-reconciling bridge between story state and publication-platform state."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import replace

from .state import PlatformState, StateStore, complete_volume


class PublicationRuntime:
    """Advance completed volumes exactly once and resume blocked rotations first."""

    def __init__(self, *, state_store: StateStore, resume_rotation: Callable[[], object]) -> None:
        self.state_store = state_store
        self.resume_rotation = resume_rotation

    @staticmethod
    def _revision(value: str | None) -> str | None:
        if value is None:
            return None
        if not re.fullmatch(r"[0-9a-f]{40}", value):
            raise RuntimeError("source revision must be a full lower-case Git commit SHA")
        return value

    @staticmethod
    def _transaction_id(volume: int, source_revision: str | None) -> str:
        suffix = source_revision[:12] if source_revision else "reconcile"
        return f"volume-{volume:06d}-{suffix}"

    def _resume_if_needed(self, state: PlatformState) -> PlatformState:
        if state.rotation is None:
            return state
        self.resume_rotation()
        resumed = self.state_store.load()
        if resumed.rotation is not None:
            raise RuntimeError(
                f"archive rotation remains incomplete at phase {resumed.rotation.phase}; generation stays blocked"
            )
        return resumed

    def record_volume_completion(
        self,
        volume: int,
        *,
        source_revision: str | None = None,
    ) -> PlatformState:
        revision = self._revision(source_revision)
        state = self.state_store.load()
        if state.completed_volumes == volume:
            if state.rotation is not None and revision is not None:
                recorded = state.rotation.source_revision
                if recorded is not None and recorded != revision:
                    raise RuntimeError("completed-volume source revision changed during rotation")
            return self._resume_if_needed(state)
        if state.rotation is not None:
            state = self._resume_if_needed(state)
        if state.current_volume != volume:
            raise RuntimeError(
                f"platform state mismatch: expected completion of volume {state.current_volume}, got {volume}"
            )
        completed = complete_volume(
            state,
            volume,
            transaction_id=self._transaction_id(volume, revision),
        )
        if completed.rotation is not None and revision is not None:
            completed = replace(
                completed,
                rotation=replace(completed.rotation, source_revision=revision),
            )
        # The boundary is durable before the first external mutation. Any error
        # after this point is therefore restartable and keeps generation blocked.
        self.state_store.save(completed)
        return self._resume_if_needed(completed)

    def ensure_generation_ready(
        self,
        *,
        story_volume: int,
        pending_new_volume: bool,
        source_revision: str | None = None,
    ) -> PlatformState:
        revision = self._revision(source_revision)
        state = self._resume_if_needed(self.state_store.load())
        effective_story_volume = story_volume + (1 if pending_new_volume else 0)

        # A crash can occur after the final story commit and story-state write,
        # but before platform-state advancement. That exact one-step condition
        # is safe to reconcile because the generator writes pending=true only
        # after the repository publication has succeeded.
        if pending_new_volume and state.current_volume == story_volume:
            state = self.record_volume_completion(story_volume, source_revision=revision)

        if state.rotation is not None:
            raise RuntimeError("archive rotation is incomplete; generation stays blocked")
        if state.current_volume != effective_story_volume:
            raise RuntimeError(
                "story/platform state mismatch: "
                f"story expects volume {effective_story_volume}, platform expects {state.current_volume}"
            )
        return state
