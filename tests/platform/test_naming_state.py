from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from wirtelprimpf_platform.naming import (
    ARCHIVE_CAPACITY,
    archive_name,
    archive_target_for_volume,
)
from wirtelprimpf_platform.state import (
    PlatformState,
    RotationPhase,
    StateStore,
    complete_volume,
    finish_rotation,
)


class NamingTests(unittest.TestCase):
    def test_global_volume_mapping_is_contiguous_at_boundaries(self) -> None:
        self.assertEqual(ARCHIVE_CAPACITY, 50)
        cases = {
            1: (1, 1, "Wirtelprimpf-0001", "wirtelprimpf-0001.telacore.org"),
            50: (1, 50, "Wirtelprimpf-0001", "wirtelprimpf-0001.telacore.org"),
            51: (2, 1, "Wirtelprimpf-0002", "wirtelprimpf-0002.telacore.org"),
            100: (2, 50, "Wirtelprimpf-0002", "wirtelprimpf-0002.telacore.org"),
            101: (3, 1, "Wirtelprimpf-0003", "wirtelprimpf-0003.telacore.org"),
        }
        for volume, expected in cases.items():
            with self.subTest(volume=volume):
                target = archive_target_for_volume(volume)
                self.assertEqual(
                    (target.archive_index, target.slot, target.repository, target.domain),
                    expected,
                )

    def test_invalid_volumes_and_indices_are_rejected(self) -> None:
        for value in (0, -1, True, 1.2, "1"):
            with self.subTest(value=value), self.assertRaises((TypeError, ValueError)):
                archive_target_for_volume(value)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            archive_name(10_000)


class PlatformStateTests(unittest.TestCase):
    def test_completing_volume_fifty_stages_rotation_and_blocks_volume_fifty_one(self) -> None:
        state = PlatformState(
            completed_volumes=49,
            current_volume=50,
            active_archive_index=1,
        )

        staged = complete_volume(state, 50, transaction_id="rotation-0001-0002")

        self.assertEqual(staged.completed_volumes, 50)
        self.assertEqual(staged.current_volume, 51)
        self.assertIsNotNone(staged.rotation)
        assert staged.rotation is not None
        self.assertEqual(staged.rotation.phase, RotationPhase.ARCHIVE_FINALIZED)
        self.assertEqual(staged.rotation.source_repository, "Wirtelprimpf-0001")
        self.assertEqual(staged.rotation.target_repository, "Wirtelprimpf-0002")
        self.assertEqual(staged.rotation.target_domain, "wirtelprimpf-0002.telacore.org")
        self.assertTrue(staged.generation_blocked)

        with self.assertRaisesRegex(ValueError, "rotation"):
            complete_volume(staged, 51, transaction_id="must-not-run")

    def test_rotation_completion_switches_target_without_precreating_later_repositories(self) -> None:
        staged = complete_volume(
            PlatformState(completed_volumes=49, current_volume=50, active_archive_index=1),
            50,
            transaction_id="rotation-0001-0002",
        )

        completed = finish_rotation(staged)

        self.assertEqual(completed.active_archive_index, 2)
        self.assertEqual(completed.active_repository, "Wirtelprimpf-0002")
        self.assertEqual(completed.current_volume, 51)
        self.assertIsNone(completed.rotation)
        self.assertFalse(completed.generation_blocked)

    def test_non_boundary_completion_advances_without_rotation(self) -> None:
        result = complete_volume(PlatformState(), 1, transaction_id="unused")
        self.assertEqual(result.completed_volumes, 1)
        self.assertEqual(result.current_volume, 2)
        self.assertIsNone(result.rotation)
        self.assertEqual(result.active_repository, "Wirtelprimpf-0001")

    def test_out_of_order_completion_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "expected volume 1"):
            complete_volume(PlatformState(), 2, transaction_id="invalid")


class StateStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_state_round_trip_is_deterministic_private_and_leaves_no_part_file(self) -> None:
        path = self.root / "state" / "platform-state.json"
        store = StateStore(path)
        state = complete_volume(PlatformState(), 1, transaction_id="unused")

        store.save(state)

        self.assertEqual(store.load(), state)
        self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
        self.assertFalse(list(path.parent.glob("*.part")))
        encoded = path.read_text(encoding="utf-8")
        self.assertEqual(encoded, json.dumps(json.loads(encoded), ensure_ascii=False, indent=2, sort_keys=True) + "\n")

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_symlink_state_target_is_rejected(self) -> None:
        target = self.root / "real.json"
        target.write_text("{}\n", encoding="utf-8")
        link = self.root / "state.json"
        link.symlink_to(target)

        with self.assertRaisesRegex(RuntimeError, "symlink"):
            StateStore(link).save(PlatformState())


if __name__ == "__main__":
    unittest.main()
