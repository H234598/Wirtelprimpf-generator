from __future__ import annotations

import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from wirtelprimpf_platform.catalog import CatalogEntry, CatalogStore, PublicationCatalog
from wirtelprimpf_platform.cli import main as cli_main
from wirtelprimpf_platform.naming import (
    ARCHIVE_CAPACITY,
    BOOKS_PER_ARCHIVE,
    STORIES_PER_BOOK,
    archive_name,
    archive_target_for_volume,
    book_target_for_story,
)
from wirtelprimpf_platform.state import (
    PlatformState,
    RotationPhase,
    StateStore,
    complete_volume,
    finish_rotation,
    status_to_dict,
)

ROOT = Path(__file__).resolve().parents[2]


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

    def test_mapping_cli_reports_book_position_without_renaming_legacy_fields(self) -> None:
        output = StringIO()

        with redirect_stdout(output):
            result = cli_main(["mapping", "51"])

        self.assertEqual(result, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["global_volume"], 51)
        self.assertEqual(payload["repository"], "Wirtelprimpf-0002")
        self.assertEqual(payload["book"], {
            "book_in_archive": 1,
            "global_book": 6,
            "story_in_book": 1,
            "story_end": 60,
            "story_start": 51,
        })

    def test_ten_stories_form_one_global_book_without_changing_archive_boundaries(self) -> None:
        self.assertEqual(STORIES_PER_BOOK, 10)
        self.assertEqual(BOOKS_PER_ARCHIVE, 5)
        cases = {
            1: (1, 1, 1, 1, 10, 1),
            10: (1, 10, 1, 1, 10, 1),
            11: (2, 1, 2, 11, 20, 1),
            50: (5, 10, 5, 41, 50, 1),
            51: (6, 1, 1, 51, 60, 2),
            100: (10, 10, 5, 91, 100, 2),
            101: (11, 1, 1, 101, 110, 3),
        }
        for story, expected in cases.items():
            with self.subTest(story=story):
                target = book_target_for_story(story)
                self.assertEqual(
                    (
                        target.global_book,
                        target.story_in_book,
                        target.book_in_archive,
                        target.story_start,
                        target.story_end,
                        target.archive_index,
                    ),
                    expected,
                )

        for value in (0, -1, True, 1.2, "1"):
            with self.subTest(value=value), self.assertRaises((TypeError, ValueError)):
                book_target_for_story(value)  # type: ignore[arg-type]


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

    def test_book_progress_is_derived_without_changing_persisted_state_schema(self) -> None:
        state = PlatformState(completed_volumes=10, current_volume=11, active_archive_index=1)

        status = status_to_dict(state)

        self.assertEqual(status["completed_volumes"], 10)
        self.assertEqual(status["current_volume"], 11)
        self.assertEqual(status["book"], {
            "books_per_archive": 5,
            "completed_books": 1,
            "current_book": 2,
            "story_in_book": 1,
            "stories_per_book": 10,
        })
        persisted = json.loads(json.dumps({
            "schema_version": state.schema_version,
            "completed_volumes": state.completed_volumes,
            "current_volume": state.current_volume,
            "active_archive_index": state.active_archive_index,
            "rotation": None,
        }))
        self.assertNotIn("book", persisted)


class CatalogBookContractTests(unittest.TestCase):
    def test_checked_in_book_fixture_loads_and_store_round_trip_preserves_fields(self) -> None:
        fixture = ROOT / "web" / "fixtures" / "site" / "publication-catalog.json"

        catalog = CatalogStore(fixture).load()

        entry = catalog.entry(1)
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual((entry.book_start, entry.book_end), (1, 5))

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "publication-catalog.json"
            stored = PublicationCatalog(
                active_archive_index=1,
                archives=(
                    CatalogEntry.for_archive(
                        1,
                        owner="H234598",
                        active=True,
                        sealed=False,
                        verified=True,
                        revision="a" * 40,
                    ),
                ),
            )
            CatalogStore(target).save(stored)
            payload = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(payload["archives"][0]["book_start"], 1)
            self.assertEqual(payload["archives"][0]["book_end"], 5)
            self.assertEqual(CatalogStore(target).load(), stored)


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
