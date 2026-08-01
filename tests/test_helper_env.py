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

    def test_story_part_numbers_follow_canonical_story_when_a_sidecar_is_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            story = root / "Wirtelprimpf_Story_II.md"
            story.write_text(
                "\n".join(
                    [
                        "## 2026-08-01 01:00:00",
                        "",
                        "Erster Teil.",
                        "## 2026-08-01 02:00:00",
                        "",
                        "Zweiter Teil ohne Sidecar.",
                        "## 2026-08-01 03:00:00",
                        "",
                        "Dritter Teil.",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            first = root / "wirtelprimpf_2026-08-01_01-00-00-000001.md"
            first.write_text("## 2026-08-01 01:00:00\n\nErster Teil.\n", encoding="utf-8")
            third = root / "wirtelprimpf_2026-08-01_03-00-00-000003.md"
            third.write_text("## 2026-08-01 03:00:00\n\nDritter Teil.\n", encoding="utf-8")
            args = self.helper.ScanArgs(output_dir=str(root), state_dir=root / "state", max_depth=1)
            full_stories = [{
                "label": "Story_II",
                "roman": "II",
                "roman_int": 2,
                "path": str(story),
                "mtime": story.stat().st_mtime,
            }]

            recent, all_parts, _infos = self.helper.scan_parts(
                root,
                [story, first, third],
                args,
                full_stories,
            )

        self.assertEqual([item["part_no"] for item in all_parts], [3, 1])
        self.assertEqual(recent[0]["tooltip"].split(" – ", 1)[0], "Part3")

    def test_story_part_numbers_consume_duplicate_heading_positions_in_sidecar_order(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            story = root / "Wirtelprimpf_Story_II.md"
            story.write_text(
                "\n".join(
                    [
                        "## 2026-08-01 01:00:00",
                        "",
                        "Erster Teil.",
                        "## 2026-08-01 01:00:00",
                        "",
                        "Zweiter Teil mit identischem Sekunden-Zeitstempel.",
                        "## 2026-08-01 02:00:00",
                        "",
                        "Dritter Teil.",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            first = root / "wirtelprimpf_2026-08-01_01-00-00-000001.md"
            first.write_text("## 2026-08-01 01:00:00\n\nErster Teil.\n", encoding="utf-8")
            second = root / "wirtelprimpf_2026-08-01_01-00-00-000002.md"
            second.write_text(
                "## 2026-08-01 01:00:00\n\nZweiter Teil mit identischem Sekunden-Zeitstempel.\n",
                encoding="utf-8",
            )
            third = root / "wirtelprimpf_2026-08-01_02-00-00-000003.md"
            third.write_text("## 2026-08-01 02:00:00\n\nDritter Teil.\n", encoding="utf-8")
            for path in (first, second, third):
                os.utime(path, (1_785_550_000, 1_785_550_000))
            args = self.helper.ScanArgs(output_dir=str(root), state_dir=root / "state", max_depth=1)
            full_stories = [{
                "label": "Story_II",
                "roman": "II",
                "roman_int": 2,
                "path": str(story),
                "mtime": story.stat().st_mtime,
            }]

            recent, all_parts, _infos = self.helper.scan_parts(
                root,
                [story, third, second, first],
                args,
                full_stories,
            )

        self.assertEqual([item["part_no"] for item in all_parts], [3, 2, 1])
        self.assertEqual([item["part_no"] for item in recent], [3, 2, 1])

    def test_duplicate_heading_content_identifies_a_later_sidecar_when_the_first_is_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            story = root / "Wirtelprimpf_Story_II.md"
            story.write_text(
                "\n".join(
                    [
                        "## 2026-08-01 01:00:00",
                        "",
                        "Erster Teil ohne Sidecar.",
                        "## 2026-08-01 01:00:00",
                        "",
                        "Zweiter Teil mit Sidecar.",
                        "## 2026-08-01 02:00:00",
                        "",
                        "Dritter Teil.",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            second = root / "wirtelprimpf_2026-08-01_01-00-00-000002.md"
            second.write_text("## 2026-08-01 01:00:00\n\nZweiter Teil mit Sidecar.\n", encoding="utf-8")
            third = root / "wirtelprimpf_2026-08-01_02-00-00-000003.md"
            third.write_text("## 2026-08-01 02:00:00\n\nDritter Teil.\n", encoding="utf-8")
            args = self.helper.ScanArgs(output_dir=str(root), state_dir=root / "state", max_depth=1)
            full_stories = [{
                "label": "Story_II",
                "roman": "II",
                "roman_int": 2,
                "path": str(story),
                "mtime": story.stat().st_mtime,
            }]

            recent, all_parts, _infos = self.helper.scan_parts(
                root,
                [story, third, second],
                args,
                full_stories,
            )

        self.assertEqual([item["part_no"] for item in all_parts], [3, 2])
        self.assertEqual(recent[-1]["tooltip"].split(" – ", 1)[0], "Part2")

    def test_unresolvable_duplicate_heading_is_marked_as_ambiguous(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            story = root / "Wirtelprimpf_Story_II.md"
            story.write_text(
                "## 2026-08-01 01:00:00\n\nGleicher Inhalt.\n"
                "## 2026-08-01 01:00:00\n\nGleicher Inhalt.\n",
                encoding="utf-8",
            )
            sidecar = root / "wirtelprimpf_2026-08-01_01-00-00-000002.md"
            sidecar.write_text("## 2026-08-01 01:00:00\n\nGleicher Inhalt.\n", encoding="utf-8")
            args = self.helper.ScanArgs(output_dir=str(root), state_dir=root / "state", max_depth=1)
            full_stories = [{
                "label": "Story_II",
                "roman": "II",
                "roman_int": 2,
                "path": str(story),
                "mtime": story.stat().st_mtime,
            }]

            recent, all_parts, infos = self.helper.scan_parts(
                root,
                [story, sidecar],
                args,
                full_stories,
            )

        self.assertEqual(all_parts[0]["part_no"], None)
        self.assertEqual(recent[0]["tooltip"].split(" – ", 1)[0], "Part?")
        self.assertEqual(infos[0].part_no, None)


if __name__ == "__main__":
    unittest.main()
