from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class OptionalScopeTests(unittest.TestCase):
    def test_register_has_independent_decision_and_rollback_for_each_option(self) -> None:
        content = (ROOT / "docs" / "WEB-OPTIONS.md").read_text(encoding="utf-8")
        for option in ("Suche mit Pagefind/MiniSearch", "PWA/Vollarchiv offline", "TTS/Audio", "Autoplay/Slideshow", "Zufallsbild/Überraschung"):
            self.assertIn(option, content)
        self.assertGreaterEqual(content.count("zurückgestellt"), 2)
        self.assertGreaterEqual(content.count("Rollback"), 1)
        self.assertIn("No-JS", content)
        self.assertIn("Kernbuild", content)


if __name__ == "__main__":
    unittest.main()
