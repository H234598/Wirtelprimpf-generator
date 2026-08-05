#!/usr/bin/env python3
"""Contract tests for the current Astro build facade and its CI wiring."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_web_site import WebBuildError, build_site


ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = ROOT / "scripts" / "build_web_site.py"
WORKFLOW = ROOT / ".github" / "workflows" / "check.yml"


class WebBuildContractTests(unittest.TestCase):
    def test_build_facade_has_a_read_only_check_mode(self) -> None:
        source = BUILD_SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"npm", "--prefix", "web", "run", "build"', source)
        self.assertIn("validate_artifact", source)
        self.assertIn("measure_budgets", source)
        self.assertIn("WIRTELPRIMPF_OUTPUT_DIR", source)
        self.assertIn("SOURCE_DATE_EPOCH", source)
        self.assertIn("_publish_atomically", source)
        self.assertIn("_git_status", source)
        result = subprocess.run(
            ["python3", str(BUILD_SCRIPT), "--help"],
            cwd=ROOT,
            check=False,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--check", result.stdout)

    @staticmethod
    def _write_artifact(output_dir: Path, domain: str, *, complete: bool = True) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "index.html").write_text(
            f'<link rel="canonical" href="https://{domain}/">\n',
            encoding="utf-8",
        )
        if complete:
            (output_dir / "404.html").write_text("not found\n", encoding="utf-8")
            (output_dir / "robots.txt").write_text("User-agent: *\n", encoding="utf-8")
            (output_dir / "sitemap.xml").write_text("<urlset/>\n", encoding="utf-8")
            (output_dir / "feed.xml").write_text("<feed/>\n", encoding="utf-8")
            gallery = output_dir / "bilder" / "index.html"
            gallery.parent.mkdir(parents=True, exist_ok=True)
            gallery.write_text(
                f'<link rel="canonical" href="https://{domain}/bilder/">\n<h1>Bilder</h1>\n',
                encoding="utf-8",
            )

    def test_failed_validation_preserves_the_last_complete_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "web").mkdir()
            (root / "web" / "package.json").write_text("{}\n", encoding="utf-8")
            existing = root / "web" / "dist"
            existing.mkdir()
            sentinel = existing / "sentinel.txt"
            sentinel.write_text("last-good\n", encoding="utf-8")

            def failed_build(*_: object, output_dir: Path, **__: object) -> float:
                self._write_artifact(output_dir, "example.org", complete=False)
                return 0.001

            with patch("scripts.build_web_site._git_status", return_value=()), patch(
                "scripts.build_web_site._run_build", side_effect=failed_build
            ), self.assertRaises(WebBuildError):
                build_site(
                    root,
                    profile="hub",
                    site_url="https://example.org",
                    data_root=root,
                    expected_domain="example.org",
                    budget_config=root / "missing.json",
                    check=True,
                )

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "last-good\n")
            self.assertFalse((root / "web" / ".staging").exists())

    def test_repeated_builds_publish_the_same_tree_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "web").mkdir()
            (root / "web" / "package.json").write_text("{}\n", encoding="utf-8")

            def successful_build(*_: object, output_dir: Path, **__: object) -> float:
                self._write_artifact(output_dir, "example.org")
                return 0.001

            with patch("scripts.build_web_site._git_status", return_value=()), patch(
                "scripts.build_web_site._run_build", side_effect=successful_build
            ):
                first = build_site(
                    root,
                    profile="hub",
                    site_url="https://example.org",
                    data_root=root,
                    expected_domain="example.org",
                    budget_config=root / "missing.json",
                    check=True,
                )
                second = build_site(
                    root,
                    profile="hub",
                    site_url="https://example.org",
                    data_root=root,
                    expected_domain="example.org",
                    budget_config=root / "missing.json",
                    check=True,
                )

            first_hash = first["artifact"]["tree_sha256"]
            second_hash = second["artifact"]["tree_sha256"]
            self.assertEqual(first_hash, second_hash)
            self.assertTrue((root / "web" / "dist" / "index.html").is_file())
            self.assertFalse((root / "web" / ".staging").exists())

    def test_current_web_package_keeps_status_build_and_static_output(self) -> None:
        package = ROOT / "web" / "package.json"
        if not package.is_file():
            self.skipTest("web source is absent in the applet sparse checkout")
        payload = json.loads(package.read_text(encoding="utf-8"))
        scripts = payload["scripts"]
        self.assertIn("build", scripts)
        self.assertIn("build:status", scripts["build"])
        self.assertIn("astro build", scripts["build"])
        self.assertIn("check", scripts)
        self.assertIn("test", scripts)

    def test_ci_builds_both_profiles_with_fail_closed_validators(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 scripts/build_web_site.py --profile hub", workflow)
        self.assertIn("python3 scripts/build_web_site.py --profile archive", workflow)
        self.assertIn("WIRTELPRIMPF_SITE_PROFILE: hub", workflow)
        self.assertIn("WIRTELPRIMPF_SITE_PROFILE: archive", workflow)
        self.assertIn("--expected-domain wirtelprimpf.telacore.org", workflow)
        self.assertIn("--expected-domain wirtelprimpf-0001.telacore.org", workflow)
        self.assertIn("validate_pages_artifact.py", workflow)
        self.assertIn("validate_web_budgets.py", workflow)

    def test_javascript_only_controls_are_gated_by_the_early_runtime_marker(self) -> None:
        layout = (ROOT / "web" / "src" / "layouts" / "BaseLayout.astro").read_text(encoding="utf-8")
        styles = (ROOT / "web" / "src" / "styles" / "global.css").read_text(encoding="utf-8")
        self.assertIn('document.documentElement.dataset.js = "enabled"', layout)
        self.assertIn('html[data-js="enabled"] .settings-shell', styles)
        self.assertIn('html[data-js="enabled"] .catgpt-shell', styles)


if __name__ == "__main__":
    unittest.main(verbosity=2)
