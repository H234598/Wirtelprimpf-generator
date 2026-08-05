#!/usr/bin/env python3
"""Verify that the repository check surface remains covered after CI migration."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"
WORKFLOW = ROOT / ".github" / "workflows" / "check.yml"
MATRIX = ROOT / "docs" / "WEB-CHECK-EQUIVALENCE.md"


class CheckEquivalenceTests(unittest.TestCase):
    def test_make_check_retains_core_generator_and_web_contracts(self) -> None:
        makefile = MAKEFILE.read_text(encoding="utf-8")
        check = makefile.split("\ninstall-local:", 1)[0]
        required = (
            "metadata.json",
            "settings-schema.json",
            "Sourcecode/wirtelprimpf_generator.py",
            "node tests/test_applet_runtime.js",
            "node --test tests/test_admin_ui.mjs",
            "tests.test_semver",
            "tests.test_git_object_fallback",
            "tests.test_release_publication",
            "tests.test_helper_env",
            "tests.test_settings_schema",
            "tests.test_story_directives",
            "tests.test_flex_contract",
            "tests.test_story_blueprint",
            "tests/test_epub_contract.py",
            "tests/test_pages_artifact.py",
            "tests/test_web_build.py",
            "tests/test_check_equivalence.py",
            "tests.test_web_workflows",
            "tests/test_web_governance.py",
            "scripts/validate_web_plan.py",
            "scripts/validate_web_governance.py",
        )
        for item in required:
            with self.subTest(item=item):
                self.assertIn(item, check)

    def test_workflow_preserves_read_only_split_and_applet_check(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("pull_request:", workflow)
        self.assertNotIn("pull_request_target", workflow)
        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertRegex(workflow, r"(?ms)^  applet:.*?^        run: make check-applet$")
        self.assertIn("npm --prefix web run build", workflow)
        self.assertIn("validate_pages_artifact.py", workflow)
        self.assertIn("validate_web_budgets.py", workflow)
        self.assertNotIn("pages: write", workflow)
        self.assertNotIn("id-token: write", workflow)

    def test_equivalence_matrix_documents_the_contract(self) -> None:
        matrix = MATRIX.read_text(encoding="utf-8")
        for heading in (
            "Generator and applet",
            "Web contracts",
            "Web artifact and budgets",
            "Read-only CI policy",
        ):
            with self.subTest(heading=heading):
                self.assertIn(heading, matrix)
        self.assertIn("make check", matrix)
        self.assertIn("npm --prefix web run build", matrix)
        self.assertIn("validate_pages_artifact.py", matrix)


if __name__ == "__main__":
    unittest.main(verbosity=2)
