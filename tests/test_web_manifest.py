"""Contract tests for the release-bound image manifest and derivative cache."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.validate_web_manifest import WebManifestError, validate_manifest


ROOT = Path(__file__).resolve().parents[1]


class WebManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = json.loads((ROOT / "data/media-manifest.json").read_text(encoding="utf-8"))

    def test_current_manifest_is_complete_and_reports_variant_widths(self) -> None:
        report = validate_manifest(self.payload)
        self.assertEqual(report["media_count"], 779)
        self.assertEqual(report["shard_count"], 4)
        self.assertEqual(report["variant_widths"], [640, 1280])

    def test_unknown_fields_duplicate_ids_and_shard_drift_fail_closed(self) -> None:
        cases = []
        unknown = copy.deepcopy(self.payload)
        unknown["unexpected"] = True
        cases.append(unknown)
        duplicate = copy.deepcopy(self.payload)
        duplicate["media"][1]["asset_id"] = duplicate["media"][0]["asset_id"]
        cases.append(duplicate)
        shard_drift = copy.deepcopy(self.payload)
        shard_drift["shards"][0]["asset_count"] += 1
        cases.append(shard_drift)
        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertRaises(WebManifestError):
                    validate_manifest(payload)

    def test_corrupt_derivative_metadata_and_release_tags_fail_closed(self) -> None:
        invalid = copy.deepcopy(self.payload)
        invalid["media"][0]["variants"][0]["sha256"] = "not-a-sha"
        with self.assertRaises(WebManifestError):
            validate_manifest(invalid)
        invalid = copy.deepcopy(self.payload)
        invalid["media"][0]["release_tag"] = "archive-0001-media-9999"
        with self.assertRaises(WebManifestError):
            validate_manifest(invalid)


if __name__ == "__main__":
    unittest.main()
