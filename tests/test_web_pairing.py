"""Contract tests for deterministic media/story pairing."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.web_content_model import build_content_model


class WebPairingTests(unittest.TestCase):
    def write_image(self, root: Path, name: str, content: bytes = b"image") -> None:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def test_heading_timestamp_wins_over_filename_and_git_time(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_image(root, "wirtelprimpf_2026-01-01_01-02-03.png")
            (root / "wirtelprimpf_2026-01-01_01-02-03.md").write_text("## 2026-02-02 02:03:04\n\nText", encoding="utf-8")
            report = build_content_model(root, git_times={"wirtelprimpf_2026-01-01_01-02-03.png": "2026-03-03 03:04:05"})
        record = report["records"][0]
        self.assertEqual(record["timestamp"], "2026-02-02 02:03:04")
        self.assertEqual(record["timestamp_source"], "heading")
        self.assertEqual(record["kind"], "story")

    def test_filename_wins_over_git_and_git_wins_over_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_image(root, "wirtelprimpf_2026-01-01_01-02-03.png")
            self.write_image(root, "without-time.png")
            report = build_content_model(
                root,
                git_times={"wirtelprimpf_2026-01-01_01-02-03.png": "2026-03-03 03:04:05", "without-time.png": "2026-04-04 04:05:06"},
                fallback_timestamp="2026-05-05 05:06:07",
            )
        by_path = {record["source_path"]: record for record in report["records"]}
        self.assertEqual(by_path["wirtelprimpf_2026-01-01_01-02-03.png"]["timestamp_source"], "filename")
        self.assertEqual(by_path["without-time.png"]["timestamp_source"], "git")

    def test_working_and_full_story_are_separate_and_orphans_are_classified(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_image(root, "working/latest.png")
            self.write_image(root, "legacy.png")
            (root / "Full_Story.md").write_text("# Full story", encoding="utf-8")
            (root / "orphan.txt").write_text("prompt", encoding="utf-8")
            report = build_content_model(root, fallback_timestamp="2026-05-05 05:06:07")
        self.assertEqual(report["records"][0]["source_path"], "legacy.png")
        self.assertEqual(report["ignored_working_paths"], ["working/latest.png"])
        self.assertEqual(report["full_story_files"], ["Full_Story.md"])
        self.assertIn({"code": "PAIR_ORPHAN_SIDECAR", "path": "orphan.txt"}, report["warnings"])

    def test_ambiguous_heading_and_case_collision_block_pairing_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_image(root, "A.png")
            self.write_image(root, "a.png", b"different")
            (root / "A.md").write_text("## 2026-01-01 00:00:00\n## 2026-01-02 00:00:00", encoding="utf-8")
            report = build_content_model(root)
        codes = {item["code"] for item in report["errors"]}
        self.assertIn("PAIR_CASE_COLLISION", codes)
        self.assertIn("PAIR_AMBIGUOUS_HEADING", codes)
        self.assertIn("PAIR_TIMESTAMP_MISSING", codes)


if __name__ == "__main__":
    unittest.main()
