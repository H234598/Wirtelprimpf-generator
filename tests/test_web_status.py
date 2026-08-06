from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_web_status import build_status, write_status


class WebStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data = self.root / "data"
        self.data.mkdir()
        self.manifest = {
            "schema_version": "1.0.0",
            "archive_index": 1,
            "archive_repository": "Wirtelprimpf-0001",
            "generated_at": "2026-08-05T02:00:00Z",
            "media": [{
                "asset_id": "archive-0001-a" + "1" * 15,
                "source_path": "Wirtelprimpf/wirtelprimpf_2026-08-05_01-00-00.png",
                "sha256": "a" * 64,
            }],
        }
        (self.data / "media-manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")
        (self.data / "Wirtelprimpf_Story_I.md").write_text(
            "# Story\n\n## 2026-08-05 01:00:00\n\nEin Teil.\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_status_separates_revisions_content_build_and_freshness(self) -> None:
        status = build_status(
            root=self.root,
            data_root=self.data,
            profile="hub",
            built_at=datetime(2026, 8, 5, 4, 0, tzinfo=UTC),
            freshness_sla_seconds=3 * 60 * 60,
        )
        self.assertEqual(status["media"]["count"], 1)
        self.assertEqual(status["stories"]["count"], 1)
        self.assertEqual(status["stories"]["chapter_count"], 1)
        self.assertEqual(status["freshness"]["state"], "warning")
        self.assertEqual(status["freshness"]["age_seconds"], 7200)
        rendered = json.dumps(status)
        self.assertNotIn(str(self.root), rendered)

    def test_missing_publication_is_explicitly_unknown(self) -> None:
        self.manifest["generated_at"] = None
        (self.data / "media-manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")
        status = build_status(
            root=self.root,
            data_root=self.data,
            profile="hub",
            built_at=datetime(2026, 8, 5, 4, 0, tzinfo=UTC),
        )
        self.assertEqual(status["freshness"]["state"], "unknown")
        self.assertIsNone(status["freshness"]["age_seconds"])

    def test_local_media_path_is_rejected_before_publication(self) -> None:
        self.manifest["media"][0]["source_path"] = "/srv/private/image.png"
        (self.data / "media-manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "local path"):
            build_status(root=self.root, data_root=self.data, profile="hub")

    def test_explicit_hub_sources_drive_the_public_status(self) -> None:
        exact = self.root / "archive"
        exact.mkdir()
        exact_manifest = {
            "schema_version": "1.0.0",
            "archive_index": 1,
            "generated_at": "2026-08-05T03:00:00Z",
            "media": [{
                "asset_id": "exact-asset",
                "source_path": "wirtelprimpf_2026-08-05_03-00-00.png",
                "sha256": "c" * 64,
            }],
        }
        (exact / "media-manifest.json").write_text(json.dumps(exact_manifest), encoding="utf-8")
        story = exact / "Wirtelprimpf_Story_II.md"
        previous_story = exact / "Wirtelprimpf_Story_I.md"
        previous_story.write_text(
            "## 2026-07-30 03:00:00\n\nEarlier.\n",
            encoding="utf-8",
        )
        story.write_text(
            "## 2026-08-05 03:00:00\n\nExact one.\n\n"
            "## 2026-08-05 04:00:00\n\nExact two.\n",
            encoding="utf-8",
        )
        with patch.dict(
            os.environ,
            {
                "WIRTELPRIMPF_MEDIA_MANIFEST": str(exact / "media-manifest.json"),
                "WIRTELPRIMPF_CURRENT_STORY": str(story),
                "WIRTELPRIMPF_STORY_FILES": json.dumps([str(previous_story), str(story)]),
                "WIRTELPRIMPF_CURRENT_VOLUME": "2",
                "WIRTELPRIMPF_SOURCE_REVISION": "d" * 40,
            },
        ):
            status = build_status(root=self.root, data_root=self.data, profile="hub")

        self.assertEqual(status["media"]["latest_id"], "exact-asset")
        self.assertEqual(status["stories"]["count"], 2)
        self.assertEqual(status["stories"]["chapter_count"], 3)
        self.assertEqual(status["stories"]["latest_volume"], 2)
        self.assertEqual(status["source_revision"], "d" * 40)

    def test_latest_media_uses_embedded_timestamp_across_legacy_path_formats(self) -> None:
        self.manifest["media"] = [
            {
                "asset_id": "legacy-asset",
                "source_path": "wirtelprimpf_2026-07-31_18-17-30-795563.png",
                "sha256": "b" * 64,
            },
            {
                "asset_id": "current-asset",
                "source_path": "Wirtelprimpf/wirtelprimpf_2026-08-05_20-23-48-880481.png",
                "sha256": "c" * 64,
            },
        ]
        (self.data / "media-manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")

        status = build_status(root=self.root, data_root=self.data, profile="hub")

        self.assertEqual(status["media"]["latest_id"], "current-asset")
        self.assertEqual(
            status["media"]["latest_source_path"],
            "Wirtelprimpf/wirtelprimpf_2026-08-05_20-23-48-880481.png",
        )

    def test_invalid_explicit_source_revision_is_rejected(self) -> None:
        with patch.dict(os.environ, {"WIRTELPRIMPF_SOURCE_REVISION": "not-a-sha"}):
            with self.assertRaisesRegex(RuntimeError, "full lower-case Git commit SHA"):
                build_status(root=self.root, data_root=self.data, profile="hub")

    def test_write_status_uses_a_regular_json_file(self) -> None:
        status = build_status(root=self.root, data_root=self.data, profile="hub")
        output = self.root / "generated" / "status.json"
        write_status(output, status)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8")), status)
        self.assertFalse(output.is_symlink())


if __name__ == "__main__":
    unittest.main()
