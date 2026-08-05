from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_web_relations import RelationError, chapter_id, validate_relations


class WebRelationTests(unittest.TestCase):
    def test_current_manifest_resolves_all_published_relations(self) -> None:
        root = Path(__file__).resolve().parents[1]
        report = validate_relations(
            root / "data/media-manifest.json",
            root / "data/current-story.md",
            2,
            strict=True,
        )
        self.assertEqual(report["relation_count"], 440)
        self.assertEqual(report["resolved_count"], 194)
        self.assertEqual(report["approximate_resolved_count"], 193)
        self.assertEqual(report["historical_orphan_count"], 246)
        self.assertEqual(report["errors"], [])

    def test_id_and_timestamp_relations_resolve_to_published_chapters(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            story = root / "story.md"
            body = "Text."
            story.write_text(f"## 2026-08-05 12:00:00\n\n{body}\n", encoding="utf-8")
            identifier = chapter_id(2, "2026-08-05 12:00:00", body)
            manifest = root / "media-manifest.json"
            manifest.write_text(json.dumps({
                "schema_version": "1.0.0",
                "media": [
                    {"asset_id": "by-id", "story_part_path": f"asset.png#{identifier}"},
                    {"asset_id": "by-time", "story_part_path": "asset_2026-08-05_12-02-00.png"},
                    {"asset_id": "unrelated", "story_part_path": None},
                ],
            }), encoding="utf-8")
            report = validate_relations(manifest, story, 2, strict=True)
        self.assertEqual(report["relation_count"], 2)
        self.assertEqual(report["resolved_count"], 2)
        self.assertEqual(report["approximate_resolved_count"], 1)
        self.assertEqual(report["orphan_count"], 0)

    def test_unpublished_id_is_rejected_without_rewriting_the_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            story = root / "story.md"
            story.write_text("## 2026-08-05 12:00:00\n\nText.\n", encoding="utf-8")
            manifest = root / "media-manifest.json"
            original = {"schema_version": "1.0.0", "media": [{"asset_id": "bad", "story_part_path": "asset.png#band-0002-teil-aaaaaaaaaaaa"}]}
            manifest.write_text(json.dumps(original), encoding="utf-8")
            report = validate_relations(manifest, story, 2)
            self.assertEqual(report["orphan_count"], 1)
            self.assertTrue(report["errors"])
            with self.assertRaises(RelationError):
                validate_relations(manifest, story, 2, strict=True)
            self.assertEqual(json.loads(manifest.read_text(encoding="utf-8")), original)

    def test_timestamp_before_current_story_is_explicit_historical_warning(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            story = root / "story.md"
            story.write_text("## 2026-08-05 12:00:00\n\nText.\n", encoding="utf-8")
            manifest = root / "media-manifest.json"
            manifest.write_text(json.dumps({
                "schema_version": "1.0.0",
                "media": [{"asset_id": "historical", "story_part_path": "asset_2026-08-04_12-00-00.png"}],
            }), encoding="utf-8")
            report = validate_relations(manifest, story, 2, strict=True)
        self.assertEqual(report["resolved_count"], 0)
        self.assertEqual(report["orphan_count"], 1)
        self.assertEqual(report["historical_orphan_count"], 1)
        self.assertEqual(report["historical_timestamp_range"], {"first": "2026-08-04 12:00:00", "last": "2026-08-04 12:00:00"})
        self.assertEqual(report["errors"], [])

    def test_multiple_story_sources_and_sidecar_heading_resolve_archive_relations(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            story_one = root / "Wirtelprimpf_Story_I.md"
            story_two = root / "Wirtelprimpf_Story_II.md"
            story_one.write_text("## 2026-06-16 04:08:16\n\nOne.\n", encoding="utf-8")
            story_two.write_text("## 2026-07-06 18:03:59\n\nTwo.\n", encoding="utf-8")
            sidecar = root / "generated.md"
            sidecar.write_text("## 2026-07-06 18:03:59\n\nGenerated later.\n", encoding="utf-8")
            manifest = root / "media-manifest.json"
            manifest.write_text(json.dumps({
                "schema_version": "1.0.0",
                "media": [
                    {"asset_id": "first", "story_part_path": "old_2026-06-16_03-37-30.md"},
                    {"asset_id": "sidecar", "story_part_path": "generated-at_2026-07-06_16-12-54.md"},
                    {"asset_id": "exact", "story_part_path": "chapter_2026-07-06_18-03-59.md"},
                ],
            }), encoding="utf-8")
            (root / "old_2026-06-16_03-37-30.md").write_text(
                "## 2026-06-16 03:37:30\n\nHistorical.\n", encoding="utf-8"
            )
            (root / "generated-at_2026-07-06_16-12-54.md").write_text(
                sidecar.read_text(encoding="utf-8"), encoding="utf-8"
            )
            (root / "chapter_2026-07-06_18-03-59.md").write_text(
                "## 2026-07-06 18:03:59\n\nExact.\n", encoding="utf-8"
            )

            report = validate_relations(
                manifest,
                story_one,
                1,
                story_sources=[(story_one, 1), (story_two, 2)],
                source_root=root,
                strict=True,
            )

        self.assertEqual(report["relation_count"], 3)
        self.assertEqual(report["resolved_count"], 2)
        self.assertEqual(report["historical_orphan_count"], 1)
        self.assertEqual(report["sidecar_resolved_count"], 1)
        self.assertEqual(report["errors"], [])

    def test_conflicting_sidecar_layouts_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            story = root / "story.md"
            story.write_text(
                "## 2026-08-05 12:00:00\n\nOne.\n"
                "## 2026-08-05 13:00:00\n\nTwo.\n",
                encoding="utf-8",
            )
            relation = "generated_2026-08-05_11-00-00.md"
            (root / relation).write_text("## 2026-08-05 12:00:00\n\nOne.\n", encoding="utf-8")
            (root / "Wirtelprimpf").mkdir()
            (root / "Wirtelprimpf" / relation).write_text(
                "## 2026-08-05 13:00:00\n\nTwo.\n", encoding="utf-8"
            )
            manifest = root / "media-manifest.json"
            manifest.write_text(json.dumps({
                "schema_version": "1.0.0",
                "media": [{"asset_id": "ambiguous", "story_part_path": relation}],
            }), encoding="utf-8")
            report = validate_relations(manifest, story, 1, source_root=root)

        self.assertEqual(report["resolved_count"], 0)
        self.assertEqual(report["sidecar_resolved_count"], 0)
        self.assertEqual(report["orphan_count"], 1)
        self.assertTrue(any("conflicting headings" in error for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()
