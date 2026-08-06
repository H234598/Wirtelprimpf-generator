"""Contract tests for the read-only web pull-request workflow."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "check.yml"
GROWTH_WORKFLOW = ROOT / ".github" / "workflows" / "web-growth-history.yml"


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
        self.assertIn("actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a", web)
        self.assertIn("web/test-results", web)
        self.assertIn("web/playwright-report", web)
        self.assertIn("WIRTELPRIMPF_SOURCE_REVISION: ${{ steps.source.outputs.revision }}", ROOT.joinpath(".github/workflows/hub-pages.yml").read_text(encoding="utf-8"))
        self.assertIn("WIRTELPRIMPF_STORY_FILES: ${{ steps.catalog.outputs.story_files || steps.source.outputs.story_files }}", ROOT.joinpath(".github/workflows/hub-pages.yml").read_text(encoding="utf-8"))
        self.assertNotIn("actions/deploy-pages", web)
        self.assertNotIn("pages: write", web)
        self.assertNotIn("id-token: write", web)

    def test_growth_history_workflow_is_read_only_and_keeps_dated_reports(self) -> None:
        workflow = GROWTH_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('cron: "17 2 * * *"', workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertIn("cancel-in-progress: false", workflow)
        self.assertIn("git ls-remote https://github.com/H234598/Wirtelprimpf-0001.git", workflow)
        self.assertIn("fetch-depth: 0", workflow)
        self.assertIn("filter: blob:none", workflow)
        self.assertIn("sparse-checkout: media-manifest.json", workflow)
        self.assertIn("--growth-root", workflow)
        self.assertIn("--growth-baseline-commit db5500b743b68dd47cdc2bb3d7f8896bea7557e1", workflow)
        self.assertIn('growth["history_source"] == "external_git"', workflow)
        self.assertIn("actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a", workflow)
        self.assertIn("retention-days: 90", workflow)
        self.assertNotIn("pages: write", workflow)
        self.assertNotIn("id-token: write", workflow)


if __name__ == "__main__":
    unittest.main()
