"""Contract tests for the read-only web pull-request workflow."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "check.yml"


class WebWorkflowTests(unittest.TestCase):
    def test_web_job_is_read_only_and_covers_the_static_gates(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        web_match = re.search(r"^  web:\n(?P<body>.*)$", workflow, re.MULTILINE | re.DOTALL)
        self.assertIsNotNone(web_match)
        assert web_match is not None
        web = web_match.group("body")

        self.assertIn("pull_request:", workflow)
        self.assertNotIn("pull_request_target", workflow)
        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertIn("npm run test:browser", web)
        self.assertIn("npm run test:performance", web)
        self.assertIn("validate_pages_artifact.py", web)
        self.assertIn("validate_web_budgets.py", web)
        self.assertIn("git diff --exit-code -- .", web)
        self.assertIn("git ls-files --others --exclude-standard", web)
        self.assertIn("web/src/generated/status\\.json", web)
        self.assertIn("if: always()", web)
        self.assertIn("actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02", web)
        self.assertIn("web/test-results", web)
        self.assertIn("web/playwright-report", web)
        self.assertIn("WIRTELPRIMPF_SOURCE_REVISION: ${{ steps.source.outputs.revision }}", ROOT.joinpath(".github/workflows/hub-pages.yml").read_text(encoding="utf-8"))
        self.assertNotIn("actions/deploy-pages", web)
        self.assertNotIn("pages: write", web)
        self.assertNotIn("id-token: write", web)


if __name__ == "__main__":
    unittest.main()
