#!/usr/bin/env python3
"""Contract tests for the current Astro build facade and its CI wiring."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = ROOT / "scripts" / "build_web_site.py"
WORKFLOW = ROOT / ".github" / "workflows" / "check.yml"


class WebBuildContractTests(unittest.TestCase):
    def test_build_facade_has_a_read_only_check_mode(self) -> None:
        source = BUILD_SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"npm", "--prefix", "web", "run", "build"', source)
        self.assertIn("validate_artifact", source)
        self.assertIn("measure_budgets", source)
        result = subprocess.run(
            ["python3", str(BUILD_SCRIPT), "--help"],
            cwd=ROOT,
            check=False,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--check", result.stdout)

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
        self.assertIn("npm --prefix web run build", workflow)
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
