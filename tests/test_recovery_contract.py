from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RecoveryContractTests(unittest.TestCase):
    def read(self, name: str) -> str:
        return (ROOT / "docs" / name).read_text(encoding="utf-8")

    def test_runbook_has_fail_closed_recovery_steps(self) -> None:
        runbook = self.read("WEB-RUNBOOK.md")
        recovery = self.read("WEB-RECOVERY.md")
        self.assertIn("validate_pages_artifact.py", runbook)
        self.assertIn("validate_web_budgets.py", runbook)
        self.assertIn("letzte geprüfte", runbook)
        self.assertIn("kein", runbook.lower())
        self.assertIn("Budgetvalidator", recovery)
        self.assertIn("letzte gute", recovery)
        self.assertIn("--cache-read-only", recovery)
        self.assertIn("Baumhash", recovery)

    def test_recovery_docs_do_not_recommend_destructive_git_operations(self) -> None:
        content = "\n".join(self.read(name) for name in ("WEB-OPERATIONS.md", "WEB-RUNBOOK.md", "WEB-RECOVERY.md"))
        self.assertNotIn("git reset --hard", content)
        self.assertNotIn("git push --force", content)
        self.assertNotIn("wrangler", content.lower())

    def test_hub_workflow_supports_exact_generator_rollback_pin(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "hub-pages.yml").read_text(encoding="utf-8")
        recovery = self.read("WEB-RECOVERY.md")
        self.assertIn("generator_ref:", workflow)
        self.assertIn("Full generator commit SHA", workflow)
        self.assertIn("ref: ${{ inputs.generator_ref || github.sha }}", workflow)
        self.assertIn("Validate manual revision inputs", workflow)
        self.assertIn("^[0-9a-fA-F]{40}$", workflow)
        self.assertIn("generator_revision", workflow)
        self.assertIn("archive_revision", workflow)
        self.assertIn("-f generator_ref=<40-stellige-Generator-SHA>", recovery)
        self.assertIn("-f archive_ref=<40-stellige-Archiv-SHA>", recovery)
        self.assertIn("HTTP/2", recovery)


if __name__ == "__main__":
    unittest.main()
