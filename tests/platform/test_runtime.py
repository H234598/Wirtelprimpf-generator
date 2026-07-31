from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from wirtelprimpf_platform.runtime import PublicationRuntime
from wirtelprimpf_platform.state import PlatformState, StateStore, finish_rotation


class RuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "private" / "platform-state.json"
        self.store = StateStore(self.path)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_non_boundary_completion_advances_once_without_remote_work(self) -> None:
        self.store.save(PlatformState(completed_volumes=1, current_volume=2, active_archive_index=1))
        calls = 0

        def resume() -> None:
            nonlocal calls
            calls += 1

        runtime = PublicationRuntime(state_store=self.store, resume_rotation=resume)
        first = runtime.record_volume_completion(2, source_revision="a" * 40)
        second = runtime.record_volume_completion(2, source_revision="a" * 40)

        self.assertEqual(first.current_volume, 3)
        self.assertEqual(second, first)
        self.assertEqual(calls, 0)

    def test_boundary_is_persisted_before_external_rotation_failure(self) -> None:
        self.store.save(PlatformState(completed_volumes=49, current_volume=50, active_archive_index=1))

        def fail() -> None:
            raise RuntimeError("external certificate pending")

        runtime = PublicationRuntime(state_store=self.store, resume_rotation=fail)
        with self.assertRaisesRegex(RuntimeError, "certificate pending"):
            runtime.record_volume_completion(50, source_revision="b" * 40)

        persisted = self.store.load()
        self.assertEqual(persisted.completed_volumes, 50)
        self.assertEqual(persisted.current_volume, 51)
        self.assertIsNotNone(persisted.rotation)
        self.assertEqual(persisted.rotation.source_revision, "b" * 40)
        self.assertTrue(persisted.generation_blocked)

    def test_next_run_resumes_rotation_before_allowing_volume_fifty_one(self) -> None:
        self.store.save(PlatformState(completed_volumes=49, current_volume=50, active_archive_index=1))

        def finish() -> None:
            state = self.store.load()
            if state.rotation is not None:
                self.store.save(finish_rotation(state))

        runtime = PublicationRuntime(state_store=self.store, resume_rotation=finish)
        runtime_with_failure = PublicationRuntime(
            state_store=self.store,
            resume_rotation=lambda: (_ for _ in ()).throw(RuntimeError("stop after staging")),
        )
        with self.assertRaises(RuntimeError):
            runtime_with_failure.record_volume_completion(50, source_revision="c" * 40)

        ready = runtime.ensure_generation_ready(story_volume=50, pending_new_volume=True)

        self.assertEqual(ready.current_volume, 51)
        self.assertEqual(ready.active_archive_index, 2)
        self.assertFalse(ready.generation_blocked)

    def test_pending_story_state_reconciles_crash_after_repository_publish(self) -> None:
        self.store.save(PlatformState(completed_volumes=1, current_volume=2, active_archive_index=1))
        runtime = PublicationRuntime(state_store=self.store, resume_rotation=lambda: None)

        ready = runtime.ensure_generation_ready(
            story_volume=2,
            pending_new_volume=True,
            source_revision="d" * 40,
        )

        self.assertEqual(ready.completed_volumes, 2)
        self.assertEqual(ready.current_volume, 3)

    def test_story_and_platform_drift_is_fail_closed(self) -> None:
        self.store.save(PlatformState(completed_volumes=3, current_volume=4, active_archive_index=1))
        runtime = PublicationRuntime(state_store=self.store, resume_rotation=lambda: None)

        with self.assertRaisesRegex(RuntimeError, "state mismatch"):
            runtime.ensure_generation_ready(story_volume=2, pending_new_volume=False)


if __name__ == "__main__":
    unittest.main()
