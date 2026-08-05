from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SearchSourceTests(unittest.TestCase):
    def test_mvp_search_decision_is_explicit_and_dependency_free(self) -> None:
        decision = (ROOT / "docs" / "WEB-SEARCH-DECISION.md").read_text(encoding="utf-8")
        self.assertIn("keine sichtbare Volltextsuche", decision)
        self.assertIn("Pagefind", decision)
        self.assertIn("MiniSearch", decision)
        self.assertIn("No-JS", decision)
        self.assertIn("Rückbau", decision)
        package = json.loads((ROOT / "web" / "package.json").read_text(encoding="utf-8"))
        dependencies = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
        self.assertNotIn("pagefind", {name.lower() for name in dependencies})
        self.assertNotIn("minisearch", {name.lower() for name in dependencies})


if __name__ == "__main__":
    unittest.main()
