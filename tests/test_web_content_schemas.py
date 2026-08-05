"""Contract tests for versioned image, story-volume and chapter schemas."""

from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = ROOT / "config" / "schemas"


def load_schema(name: str) -> dict[str, object]:
    return json.loads((SCHEMA_ROOT / name).read_text(encoding="utf-8"))


def assert_known_fields(test: unittest.TestCase, payload: dict[str, object], schema: dict[str, object]) -> None:
    properties = schema["properties"]
    test.assertIsInstance(properties, dict)
    test.assertEqual(set(payload) - set(properties), set())
    required = schema["required"]
    test.assertTrue(set(required) <= set(payload))


def chapter_fixture(volume: int = 2) -> dict[str, object]:
    timestamp = "2026-08-05 12:00:00"
    markdown = "Ein geprüfter Storyabschnitt."
    digest = hashlib.sha256(f"{volume}\0{timestamp}\0{markdown}".encode()).hexdigest()[:12]
    return {
        "schema_version": "1.0.0",
        "id": f"band-{volume:04d}-teil-{digest}",
        "timestamp": timestamp,
        "markdown": markdown,
        "html": "<p>Ein geprüfter Storyabschnitt.</p>",
        "sequence": 1,
    }


class WebContentSchemaTests(unittest.TestCase):
    def test_all_schemas_are_strict_versioned_draft_2020_12_documents(self) -> None:
        for name in (
            "web-image.schema.json",
            "web-story-volume.schema.json",
            "web-story-chapter.schema.json",
        ):
            with self.subTest(name=name):
                schema = load_schema(name)
                self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
                self.assertEqual(schema["additionalProperties"], False)
                self.assertEqual(schema["properties"]["schema_version"]["const"], "1.0.0")

    def test_real_manifest_record_maps_to_the_image_contract(self) -> None:
        manifest = json.loads((ROOT / "data/media-manifest.json").read_text(encoding="utf-8"))
        record = dict(manifest["media"][0])
        record["schema_version"] = "1.0.0"
        schema = load_schema("web-image.schema.json")
        assert_known_fields(self, record, schema)
        self.assertEqual(record["kind"], "classic")
        self.assertEqual(record["mime_type"], "image/png")
        self.assertEqual(len(record["variants"]), 2)

    def test_volume_and_chapter_fixtures_share_stable_ids(self) -> None:
        chapter = chapter_fixture()
        volume = {
            "schema_version": "1.0.0",
            "volume": 2,
            "book": 1,
            "storyInBook": 2,
            "filename": "current-story.md",
            "title": "Wirtelprimpf",
            "parts": [chapter],
        }
        assert_known_fields(self, chapter, load_schema("web-story-chapter.schema.json"))
        assert_known_fields(self, volume, load_schema("web-story-volume.schema.json"))
        self.assertTrue(str(chapter["id"]).startswith("band-0002-teil-"))
        self.assertEqual(volume["parts"][0]["id"], chapter["id"])

    def test_unknown_fields_and_wrong_versions_are_rejected_by_contract(self) -> None:
        schema = load_schema("web-story-chapter.schema.json")
        invalid = chapter_fixture()
        invalid["debug"] = True
        with self.assertRaises(AssertionError):
            assert_known_fields(self, invalid, schema)
        invalid = chapter_fixture()
        invalid["schema_version"] = "2.0.0"
        self.assertNotEqual(invalid["schema_version"], schema["properties"]["schema_version"]["const"])


if __name__ == "__main__":
    unittest.main()
