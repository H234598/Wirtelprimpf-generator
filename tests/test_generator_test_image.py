from __future__ import annotations

import unittest

from Sourcecode.wirtelprimpf_generator import MEDIA_KIND_UNKNOWN, build_test_plans


class GeneratorTestImageTests(unittest.TestCase):
    def test_test_image_plan_is_unknown_and_has_no_story_sidecar(self) -> None:
        plans = build_test_plans()

        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0].kind, MEDIA_KIND_UNKNOWN)
        self.assertIsNone(plans[0].story_entry_markdown)
        self.assertIn("test image", plans[0].prompt.lower())


if __name__ == "__main__":
    unittest.main()
