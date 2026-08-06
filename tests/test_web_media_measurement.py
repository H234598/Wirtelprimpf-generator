from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.measure_web_media import (
    MediaMeasurementError,
    _growth_report,
    _git_status,
    _manifest_stats,
    _percentile,
    _write_report,
)


ROOT = Path(__file__).resolve().parents[1]


class WebMediaMeasurementTests(unittest.TestCase):
    def test_generated_status_is_ignored_but_other_worktree_changes_are_not(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "--quiet"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            generated = root / "web/src/generated/status.json"
            generated.parent.mkdir(parents=True)
            generated.write_text("{}\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "--quiet", "-m", "initial"], cwd=root, check=True)

            generated.write_text('{"changed": true}\n', encoding="utf-8")
            (root / "unrelated.txt").write_text("changed\n", encoding="utf-8")

            status = _git_status(root)
            self.assertNotIn("web/src/generated/status.json", status)
            self.assertIn("unrelated.txt", status)

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

    def test_external_growth_history_uses_archive_anchor_and_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "--quiet"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)

            manifest = root / "media-manifest.json"
            manifest.write_text(json.dumps({"media": [{"byte_size": 10}, {"byte_size": 20}]}), encoding="utf-8")
            first_env = os.environ.copy()
            first_env.update(
                GIT_AUTHOR_DATE="2026-01-01T00:00:00+00:00",
                GIT_COMMITTER_DATE="2026-01-01T00:00:00+00:00",
            )
            subprocess.run(["git", "add", "media-manifest.json"], cwd=root, check=True)
            subprocess.run(["git", "commit", "--quiet", "-m", "first"], cwd=root, check=True, env=first_env)
            baseline = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()

            manifest.write_text(
                json.dumps({"media": [{"byte_size": 10}, {"byte_size": 20}, {"byte_size": 30}]}),
                encoding="utf-8",
            )
            second_env = os.environ.copy()
            second_env.update(
                GIT_AUTHOR_DATE="2026-01-02T00:00:00+00:00",
                GIT_COMMITTER_DATE="2026-01-02T00:00:00+00:00",
            )
            subprocess.run(["git", "add", "media-manifest.json"], cwd=root, check=True)
            subprocess.run(["git", "commit", "--quiet", "-m", "second"], cwd=root, check=True, env=second_env)

            report = _growth_report(
                ROOT,
                {"media_count": 999, "source_bytes": 999},
                history_root=root,
                relative_path="media-manifest.json",
                baseline_commit=baseline,
            )

            self.assertEqual(report["history_source"], "external_git")
            self.assertEqual(report["point_count"], 2)
            self.assertEqual(report["long_term_status"], "insufficient_history")
            self.assertEqual(report["anchor"]["media_count"], 3)
            self.assertEqual(report["anchor"]["source_bytes"], 60)
            self.assertGreater(report["projections"]["12"]["projected_media_count"], 3)


if __name__ == "__main__":
    unittest.main()
