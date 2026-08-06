"""Contract tests for read-only media inventory and static web budgets."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.validate_web_budgets import DEFAULT_LIMITS, measure_budgets
from scripts.measure_web_media import media_cache_key
from scripts.web_inventory import InventoryError, InventoryOutputError, build_inventory, write_report


def _record(asset_id: str, source: str, digest: str) -> dict[str, object]:
    return {
        "asset_id": asset_id,
        "source_path": source,
        "kind": "classic",
        "sha256": digest,
        "byte_size": 100,
        "mime_type": "image/png",
        "width": 100,
        "height": 80,
        "prompt_path": source.removesuffix(".png") + ".txt",
        "story_part_path": None,
        "original": {"asset_name": source, "url": "https://github.com/a/b/releases/download/t/" + source},
        "variants": [
            {
                "requested_width": 640,
                "actual_width": 100,
                "actual_height": 80,
                "asset_name": source + ".webp",
                "url": "https://github.com/a/b/releases/download/t/" + source + ".webp",
                "sha256": "b" * 64,
                "byte_size": 20,
                "mime_type": "image/webp",
            }
        ],
    }


class WebInventoryTests(unittest.TestCase):
    def test_inventory_reports_dimensions_variants_and_gaps(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "media-manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "archive_repository": "Wirtelprimpf-0001",
                        "media_count": 1,
                        "media": [_record("one", "one.png", "a" * 64)],
                        "shards": [
                            {"record_count": 1, "asset_count": 4, "open": False},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            report = build_inventory(manifest, strict=True)
        self.assertEqual(report["media_count"], 1)
        self.assertEqual(report["variants"]["640"]["bytes"], 20)
        self.assertEqual(report["relationship_gaps"]["missing_story_part_path"], 1)
        self.assertEqual(report["errors"], [])

    def test_inventory_rejects_incomplete_release_in_strict_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "media-manifest.json"
            payload = {
                "schema_version": "1.0.0",
                "media_count": 1,
                "media": [_record("one", "one.png", "a" * 64)],
                "shards": [{"record_count": 1, "asset_count": 4, "open": True}],
            }
            manifest.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(InventoryError):
                build_inventory(manifest, strict=True)

    def test_source_scan_reports_duplicates_and_rejects_unsafe_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "media-manifest.json"
            manifest.write_text(
                json.dumps({
                    "schema_version": "1.0.0",
                    "media_count": 1,
                    "media": [_record("one", "one.png", "a" * 64)],
                    "shards": [{"record_count": 1, "asset_count": 4, "open": False}],
                }),
                encoding="utf-8",
            )
            source = root / "source"
            source.mkdir()
            (source / "A.png").write_bytes(b"same")
            (source / "a.png").write_bytes(b"same")
            (source / "story.epub").write_bytes(b"epub")
            (source / "story.md").write_text("story", encoding="utf-8")
            (source / "copy.txt").hardlink_to(source / "story.md")
            (source / "outside-link").symlink_to(Path(temporary).parent)
            report = build_inventory(manifest, source_root=source, strict=False)
        scan = report["source_scan"]
        self.assertEqual(scan["epub_files"], ["story.epub"])
        self.assertEqual(scan["story_files"], ["story.md"])
        self.assertTrue(scan["case_collisions"])
        self.assertTrue(scan["duplicate_content_groups"])
        self.assertTrue(scan["duplicate_hardlink_groups"])
        self.assertIn("symlink escapes source root: outside-link", report["errors"])
        with self.assertRaises(InventoryError):
            build_inventory(manifest, source_root=source, strict=True)

    def test_report_writes_atomically_only_below_build_reports(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "media-manifest.json"
            manifest.write_text(
                json.dumps({
                    "schema_version": "1.0.0",
                    "media_count": 1,
                    "media": [_record("one", "one.png", "a" * 64)],
                    "shards": [{"record_count": 1, "asset_count": 4, "open": False}],
                }),
                encoding="utf-8",
            )
            report = build_inventory(manifest, strict=True)
            write_report(report, Path("build/reports/inventory.json"), root=root)
            self.assertTrue((root / "build/reports/inventory.json").is_file())
            with self.assertRaises(InventoryOutputError):
                write_report(report, Path("reports/inventory.json"), root=root)

    def test_budget_measurement_accepts_static_runtime_and_rejects_foreign_script(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "bilder").mkdir()
            (root / "_assets").mkdir()
            (root / "_assets/site.js").write_text("console.log('ok');", encoding="utf-8")
            (root / "_assets/site.css").write_text("body { color: black; }", encoding="utf-8")
            html = '<link rel="stylesheet" href="/_assets/site.css"><script src="/_assets/site.js"></script>'
            (root / "index.html").write_text(html, encoding="utf-8")
            (root / "bilder/index.html").write_text(html + '<img src="x.webp" loading="lazy">', encoding="utf-8")
            (root / "bilder/x.webp").write_bytes(b"image")
            report = measure_budgets(root, limits=DEFAULT_LIMITS)
            self.assertEqual(report["errors"], [])
            (root / "index.html").write_text('<script src="https://example.invalid/app.js"></script>', encoding="utf-8")
            report = measure_budgets(root, limits=DEFAULT_LIMITS)
        self.assertIn("foreign runtime requests exceed max_external_runtime_requests", report["errors"])

    def test_media_cache_key_binds_all_transform_inputs(self) -> None:
        first = media_cache_key("a" * 64, "0.35.3", "media-transform-v1", "webp", 640)
        second = media_cache_key("a" * 64, "0.35.3", "media-transform-v1", "webp", 1280)
        self.assertEqual(len(first), 64)
        self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
