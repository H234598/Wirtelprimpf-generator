#!/usr/bin/env python3
"""Regression tests for applet-helper environment expansion edge cases."""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = ROOT / "files" / "wirtelprimfgenerator@H234598" / "helper.py"


def load_helper():
    spec = importlib.util.spec_from_file_location("wirtel_helper_under_test", HELPER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load helper module from {HELPER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class HelperEnvExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.helper = load_helper()

    def test_custom_env_expansion_does_not_replace_variable_prefixes(self):
        env = {"WIRTEL_TEST_ROOT": "/tmp/wirtel-root"}

        self.assertEqual(
            str(self.helper.expand_path("$WIRTEL_TEST_ROOT/story", env=env)),
            "/tmp/wirtel-root/story",
        )
        self.assertEqual(
            str(self.helper.expand_path("${WIRTEL_TEST_ROOT}/story", env=env)),
            "/tmp/wirtel-root/story",
        )
        self.assertEqual(
            str(self.helper.expand_path("$WIRTEL_TEST_ROOT2/story", env=env)),
            "$WIRTEL_TEST_ROOT2/story",
        )

    def test_env_file_expansion_uses_prior_keys_without_prefix_bleed(self):
        old_value = os.environ.pop("WIRTEL_TEST_BASE2", None)
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                env_path = Path(tmpdir) / "openai.env"
                env_path.write_text(
                    "\n".join(
                        [
                            "WIRTEL_TEST_BASE=/tmp/base",
                            "WIRTEL_TEST_CHILD=${WIRTEL_TEST_BASE}/child",
                            "WIRTEL_TEST_LITERAL=$WIRTEL_TEST_BASE2/literal",
                        ]
                    )
                    + "\n",
                    encoding="utf-8",
                )

                parsed = self.helper.parse_shell_env_file(env_path)
        finally:
            if old_value is not None:
                os.environ["WIRTEL_TEST_BASE2"] = old_value

        self.assertEqual(parsed["WIRTEL_TEST_CHILD"], "/tmp/base/child")
        self.assertEqual(parsed["WIRTEL_TEST_LITERAL"], "$WIRTEL_TEST_BASE2/literal")

    def test_scan_returns_only_newest_50_full_story_volumes_but_keeps_total_count(self):
        stories = [
            {
                "label": f"Story_{index:03d}",
                "roman": "I",
                "roman_int": index,
                "path": f"/stories/{index:03d}.md",
                "mtime": float(index),
            }
            for index in range(1, 76)
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            output = root / "output"
            output.mkdir()
            args = self.helper.ScanArgs(output_dir=str(output), state_dir=root / "state", max_depth=1)
            with patch.object(
                self.helper,
                "scan_full_stories",
                return_value=stories,
            ), patch.object(
                self.helper,
                "scan_images",
                return_value={"story": None, "generated": None},
            ), patch.object(
                self.helper,
                "scan_parts",
                return_value=([], [], []),
            ):
                result = self.helper.scan(args)

        self.assertEqual(len(result["full_stories"]), 50)
        self.assertEqual(result["full_stories"][0]["roman_int"], 26)
        self.assertEqual(result["full_stories"][-1]["roman_int"], 75)
        self.assertEqual(result["stats"]["current_full_story_count"], 75)
        self.assertEqual(result["stats"]["known_full_story_count"], 75)


if __name__ == "__main__":
    unittest.main()
