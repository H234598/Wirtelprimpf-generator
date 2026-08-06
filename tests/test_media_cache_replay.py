from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.measure_media_cache_replay import CacheReplayError, _materialize_variant, measure


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class MediaCacheReplayTests(unittest.TestCase):
    def test_full_replay_is_hash_bound_and_does_not_transform(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "migration"
            source.mkdir()
            original = source / "original.png"
            Image.new("RGB", (32, 24), (20, 40, 60)).save(original, format="PNG")
            variants = []
            for width in (640, 1280):
                path = source / f"original.w{width}.webp"
                Image.open(original).resize((width, width * 24 // 32)).save(path, format="WEBP")
                variants.append(
                    {
                        "actual_height": width * 24 // 32,
                        "actual_width": width,
                        "asset_name": path.name,
                        "byte_size": path.stat().st_size,
                        "mime_type": "image/webp",
                        "requested_width": width,
                        "sha256": _sha256(path),
                    }
                )
            manifest = {
                "media": [
                    {
                        "byte_size": original.stat().st_size,
                        "original": {"asset_name": original.name},
                        "sha256": _sha256(original),
                        "variants": variants,
                    }
                ]
            }
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            report = measure(source_root=source, manifest_path=manifest_path, passes=2)
            self.assertEqual(report["source"]["manifest_records"], 1)
            self.assertTrue(report["source"]["hashes_match"])
            self.assertEqual([item["cache_hit_rate"] for item in report["replays"]], [1.0, 1.0])
            self.assertFalse(report["cache_contract"]["cold_transform_measured"])

    def test_missing_manifest_asset_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "migration"
            source.mkdir()
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "media": [
                            {
                                "byte_size": 1,
                                "original": {"asset_name": "missing.png"},
                                "sha256": "a" * 64,
                                "variants": [],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(CacheReplayError):
                measure(source_root=source, manifest_path=manifest)

    def test_cold_transform_starts_empty_and_matches_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "migration"
            source.mkdir()
            original = source / "original.png"
            Image.new("RGB", (160, 120), (20, 40, 60)).save(original, format="PNG")
            variants = []
            for width in (64, 128):
                path = source / f"original.w{width}.webp"
                digest, byte_size, actual_width, actual_height = _materialize_variant(original, path, width)
                variants.append(
                    {
                        "actual_height": actual_height,
                        "actual_width": actual_width,
                        "asset_name": path.name,
                        "byte_size": byte_size,
                        "mime_type": "image/webp",
                        "requested_width": width,
                        "sha256": digest,
                    }
                )
            manifest_path = root / "manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "media": [
                            {
                                "byte_size": original.stat().st_size,
                                "original": {"asset_name": original.name},
                                "sha256": _sha256(original),
                                "variants": variants,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            report = measure(source_root=source, manifest_path=manifest_path, passes=1, cold=True)
            cold = report["cold_transform"]
            self.assertTrue(report["cache_contract"]["cold_transform_measured"])
            self.assertEqual(cold["requests"], 2)
            self.assertEqual(cold["hits"], 0)
            self.assertEqual(cold["misses"], 2)
            self.assertEqual(cold["writes"], 2)
            self.assertEqual(report["replays"][0]["cache_hit_rate"], 1.0)

    def test_new_story_baseline_reuses_archive_cache(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "migration"
            source.mkdir()
            original = source / "original.png"
            Image.new("RGB", (160, 120), (20, 40, 60)).save(original, format="PNG")
            variants = []
            for width in (64, 128):
                path = source / f"original.w{width}.webp"
                digest, byte_size, actual_width, actual_height = _materialize_variant(original, path, width)
                variants.append(
                    {
                        "actual_height": actual_height,
                        "actual_width": actual_width,
                        "asset_name": path.name,
                        "byte_size": byte_size,
                        "mime_type": "image/webp",
                        "requested_width": width,
                        "sha256": digest,
                    }
                )
            manifest_path = root / "manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "media": [
                            {
                                "byte_size": original.stat().st_size,
                                "original": {"asset_name": original.name},
                                "sha256": _sha256(original),
                                "variants": variants,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            report = measure(
                source_root=source,
                manifest_path=manifest_path,
                passes=1,
                new_story_images=2,
            )
            baseline = report["new_story_baseline"]
            self.assertTrue(report["cache_contract"]["new_story_baseline_measured"])
            self.assertTrue(baseline["synthetic_fixture"])
            self.assertEqual(baseline["archive_replay"]["cache_hit_rate"], 1.0)
            self.assertEqual(baseline["new_story"]["misses"], 6)
            self.assertEqual(baseline["new_story"]["writes"], 6)
            self.assertEqual(baseline["combined"]["requests"], 8)
            self.assertAlmostEqual(baseline["combined"]["cache_hit_rate"], 2 / 8)


if __name__ == "__main__":
    unittest.main()
