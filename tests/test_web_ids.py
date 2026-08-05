"""Contract tests for stable web IDs and alias migrations."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.web_ids import WebIdError, chapter_id, id_kind, load_aliases, normalize_id, resolve_alias, validate_aliases


class WebIdTests(unittest.TestCase):
    def test_alias_register_schema_accepts_current_and_migration_fixture(self) -> None:
        root = Path(__file__).resolve().parents[1]
        schema = json.loads((root / "config/schemas/web-content-aliases.schema.json").read_text(encoding="utf-8"))
        current = json.loads((root / "config/web-content-aliases.json").read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(current)
        migration = {
            "schema_version": "1.0.0",
            "aliases": [{
                "kind": "chapter",
                "old_id": "band-0002-teil-aaaaaaaaaaaa",
                "new_id": "band-0002-teil-bbbbbbbbbbbb",
                "source_sha256": "a" * 64,
                "reason": "source correction",
            }],
        }
        Draft202012Validator(schema).validate(migration)
        invalid = json.loads(json.dumps(migration))
        invalid["aliases"][0]["new_id"] = "band-0002"
        with self.assertRaises(ValidationError):
            Draft202012Validator(schema).validate(invalid)

    def test_ids_are_portable_and_chapter_ids_match_typescript_algorithm(self) -> None:
        self.assertEqual(normalize_id("image", " ARCHIVE-0001-D1F75722EDAEBFA8-10035CC1 "), "archive-0001-d1f75722edaebfa8-10035cc1")
        self.assertEqual(normalize_id("volume", "BAND-0002"), "band-0002")
        identifier = chapter_id(2, "2026-08-05 12:00:00", "Ein Abschnitt")
        self.assertEqual(len(identifier), len("band-0002-teil-000000000000"))
        self.assertEqual(id_kind(identifier), "chapter")

    def test_repository_alias_register_is_valid_and_resolves_chains(self) -> None:
        payload = {
            "schema_version": "1.0.0",
            "aliases": [
                {"kind": "chapter", "old_id": "band-0002-teil-aaaaaaaaaaaa", "new_id": "band-0002-teil-bbbbbbbbbbbb", "source_sha256": "a" * 64, "reason": "source correction"},
                {"kind": "chapter", "old_id": "band-0002-teil-bbbbbbbbbbbb", "new_id": "band-0002-teil-cccccccccccc", "source_sha256": "b" * 64, "reason": "canonical migration"},
            ],
        }
        aliases = validate_aliases(payload)
        self.assertEqual(resolve_alias("band-0002-teil-aaaaaaaaaaaa", aliases), "band-0002-teil-cccccccccccc")

    def test_alias_cycles_duplicate_sources_and_cross_kind_targets_fail_closed(self) -> None:
        base = {"schema_version": "1.0.0", "aliases": []}
        cases = [
            [{"kind": "chapter", "old_id": "band-0002-teil-aaaaaaaaaaaa", "new_id": "band-0002-teil-aaaaaaaaaaaa", "source_sha256": "a" * 64, "reason": "same"}],
            [
                {"kind": "chapter", "old_id": "band-0002-teil-aaaaaaaaaaaa", "new_id": "band-0002-teil-bbbbbbbbbbbb", "source_sha256": "a" * 64, "reason": "cycle"},
                {"kind": "chapter", "old_id": "band-0002-teil-bbbbbbbbbbbb", "new_id": "band-0002-teil-aaaaaaaaaaaa", "source_sha256": "b" * 64, "reason": "cycle"},
            ],
            [{"kind": "chapter", "old_id": "band-0002-teil-aaaaaaaaaaaa", "new_id": "band-0002-teil-bbbbbbbbbbbb", "source_sha256": "a" * 64, "reason": "duplicate"}, {"kind": "chapter", "old_id": "band-0002-teil-aaaaaaaaaaaa", "new_id": "band-0002-teil-cccccccccccc", "source_sha256": "b" * 64, "reason": "duplicate"}],
        ]
        for aliases in cases:
            with self.subTest(aliases=aliases):
                with self.assertRaises(WebIdError):
                    validate_aliases({**base, "aliases": aliases})
        with self.assertRaises(WebIdError):
            normalize_id("image", "not-an-image-id")

    def test_repository_alias_file_is_empty_until_a_real_migration_is_evidenced(self) -> None:
        path = Path(__file__).resolve().parents[1] / "config/web-content-aliases.json"
        self.assertEqual(load_aliases(path), {})


if __name__ == "__main__":
    unittest.main()
