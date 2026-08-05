from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.measure_web_media import MediaMeasurementError, _manifest_stats, _percentile, _write_report


ROOT = Path(__file__).resolve().parents[1]


class WebMediaMeasurementTests(unittest.TestCase):
    def test_percentile_is_deterministic(self) -> None:
        self.assertEqual(_percentile([3.0, 1.0, 2.0], 50), 2.0)
        self.assertEqual(_percentile([1.0, 2.0, 3.0, 4.0], 95), 3.85)

    def test_current_manifest_stats_are_release_bound(self) -> None:
        report = _manifest_stats(ROOT / "data/media-manifest.json")
        self.assertEqual(report["media_count"], 779)
        self.assertEqual(report["shard_count"], 4)
        self.assertEqual(report["variant_widths"], [640, 1280])
        self.assertGreater(report["source_bytes"], 0)

    def test_measurement_report_output_is_atomic_and_allowlisted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rendered = json.dumps({"ok": True}) + "\n"
            _write_report(root, Path("build/reports/report.json"), rendered)
            self.assertEqual((root / "build/reports/report.json").read_text(encoding="utf-8"), rendered)
            with self.assertRaises(MediaMeasurementError):
                _write_report(root, Path("outside.json"), rendered)


if __name__ == "__main__":
    unittest.main()
