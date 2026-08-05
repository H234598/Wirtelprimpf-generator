"""Contract tests for versioned image, story-volume and chapter schemas."""

from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = ROOT / "config" / "schemas"


def load_schema(name: str) -> dict[str, object]:
    return json.loads((SCHEMA_ROOT / name).read_text(encoding="utf-8"))


def assert_schema_valid(test: unittest.TestCase, payload: dict[str, object], schema: dict[str, object]) -> None:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.absolute_path))
    test.assertEqual(errors, [], "\n".join(error.message for error in errors))


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
            "web-content-aliases.schema.json",
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
        for item in manifest["media"]:
            candidate = dict(item)
            candidate["schema_version"] = "1.0.0"
            assert_schema_valid(self, candidate, schema)
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
        assert_schema_valid(self, chapter, load_schema("web-story-chapter.schema.json"))
        assert_schema_valid(self, volume, load_schema("web-story-volume.schema.json"))
        self.assertTrue(str(chapter["id"]).startswith("band-0002-teil-"))
        self.assertEqual(volume["parts"][0]["id"], chapter["id"])

    def test_unknown_fields_and_wrong_versions_are_rejected_by_contract(self) -> None:
        schema = load_schema("web-story-chapter.schema.json")
        invalid = chapter_fixture()
        invalid["debug"] = True
        with self.assertRaises(ValidationError):
            Draft202012Validator(schema).validate(invalid)
        invalid = chapter_fixture()
        invalid["schema_version"] = "2.0.0"
        with self.assertRaises(ValidationError):
            Draft202012Validator(schema).validate(invalid)

    def test_type_and_path_constraints_are_enforced(self) -> None:
        schema = load_schema("web-image.schema.json")
        manifest = json.loads((ROOT / "data/media-manifest.json").read_text(encoding="utf-8"))
        invalid = dict(manifest["media"][0])
        invalid["schema_version"] = "1.0.0"
        invalid["width"] = "1280"
        invalid["source_path"] = "../escape.png"
        with self.assertRaises(ValidationError):
            Draft202012Validator(schema).validate(invalid)


if __name__ == "__main__":
    unittest.main()
