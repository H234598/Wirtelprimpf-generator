#!/usr/bin/env python3
"""Behavior and integration tests for per-story Wirtelprimpf directives."""

from __future__ import annotations

import importlib.util
import json
import stat
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE_PATH = ROOT / "files" / "wirtelprimfgenerator@H234598" / "story_directives_core.py"
GENERATOR_PATH = ROOT / "Sourcecode" / "wirtelprimpf_generator.py"
SERVICE_PATH = ROOT / "Sourcecode" / "systemd-user" / "wirtelprimpf.service"
MAKEFILE_PATH = ROOT / "Makefile"
SETTINGS_SCHEMA_PATH = ROOT / "files" / "wirtelprimfgenerator@H234598" / "settings-schema.json"
STORY_UI_PATH = ROOT / "files" / "wirtelprimfgenerator@H234598" / "StoryDirectives.py"
INSTALL_SCRIPT_PATH = ROOT / "scripts" / "install-local.sh"
UNINSTALL_SCRIPT_PATH = ROOT / "scripts" / "uninstall-local.sh"


def load_core():
    spec = importlib.util.spec_from_file_location("story_directives_core_under_test", CORE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {CORE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_generator():
    spec = importlib.util.spec_from_file_location("wirtelprimpf_generator_under_test", GENERATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {GENERATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class StoryDirectivesCoreTests(unittest.TestCase):
    def setUp(self):
        self.core = load_core()
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_story_iii_seed_is_created_without_overwriting_user_value(self):
        ledger_path = self.root / "story_directives.json"

        seeded = self.core.load_ledger(ledger_path, seed_story_iii=True)

        story_iii = seeded["stories"]["3"]
        self.assertEqual(story_iii["volume"], 3)
        self.assertIn("Actionstory", story_iii["directive"])
        self.assertIn("Blutig", story_iii["directive"])
        self.assertIn("Richard Bachman", story_iii["directive"])
        self.assertIn("James-Bond", story_iii["directive"])

        custom = "Eigene Story-III-Vorgabe"
        self.core.save_directives(ledger_path, {3: custom}, now="2026-07-31T18:00:00Z")
        loaded_again = self.core.load_ledger(ledger_path, seed_story_iii=True)

        self.assertEqual(loaded_again["stories"]["3"]["directive"], custom)

    def test_cleared_story_iii_is_not_seeded_again(self):
        ledger_path = self.root / "story_directives.json"
        self.core.load_ledger(ledger_path, seed_story_iii=True, now="2026-07-31T17:00:12Z")

        self.core.save_directives(
            ledger_path,
            {3: ""},
            now="2026-07-31T18:00:00Z",
        )
        loaded_again = self.core.load_ledger(
            ledger_path,
            seed_story_iii=True,
            now="2026-07-31T19:00:00Z",
        )

        self.assertNotIn("3", loaded_again["stories"])
        self.assertTrue(loaded_again["migrations"]["story_iii_seeded"])

    def test_runtime_paths_expand_home_placeholders_from_env_file(self):
        env_path = self.root / "openai.env"
        env_path.write_text(
            "WIRTELPRIMPF_STORY_DIRECTIVES=$HOME/.config/wirtelprimpf/custom.json\n",
            encoding="utf-8",
        )

        paths = self.core.resolve_runtime_paths(env_path)

        self.assertEqual(
            paths["ledger"],
            Path.home() / ".config" / "wirtelprimpf" / "custom.json",
        )

    def test_editable_window_rejects_stale_or_past_volume(self):
        ledger_path = self.root / "story_directives.json"
        self.core.load_ledger(ledger_path, seed_story_iii=True)

        with self.assertRaisesRegex(ValueError, "editable story window changed"):
            self.core.save_editable_window(
                ledger_path,
                current_volume=3,
                directives={2: "Vergangenheit ändern", 3: "Aktuell", 4: "Nächste"},
            )

    def test_pending_new_volume_advances_effective_volume(self):
        self.assertEqual(
            self.core.effective_current_volume({"current_volume": 2, "pending_new_volume": True}),
            3,
        )
        self.assertEqual(
            self.core.effective_current_volume({"current_volume": 2, "pending_new_volume": False}),
            2,
        )

    def test_only_current_and_next_two_are_editable(self):
        ledger = {
            "schema_version": 1,
            "stories": {
                str(volume): {
                    "volume": volume,
                    "directive": f"Vorgabe {volume}",
                    "created_at": "2026-07-31T17:00:12Z",
                    "updated_at": "2026-07-31T17:00:12Z",
                    "source": "test",
                }
                for volume in range(1, 7)
            },
        }

        roles = self.core.story_roles(3, ledger)

        self.assertEqual([item["volume"] for item in roles["editable"]], [3, 4, 5])
        self.assertEqual([item["role"] for item in roles["editable"]], ["current", "next", "upcoming"])
        self.assertTrue(all(item["editable"] for item in roles["editable"]))
        self.assertEqual([item["volume"] for item in roles["past"]], [2, 1])
        self.assertTrue(all(not item["editable"] for item in roles["past"]))

    def test_active_directive_is_appended_as_single_selected_section(self):
        original = "# Konfiguration\n\n## Hauptteil\nBasisregel\n\n## Ort\n- Dachboden\n"

        rendered = self.core.replace_managed_prompt_section(
            original,
            "Actionstory.\nBlutig.\nRiskante Mission.",
        )

        self.assertIn("## Story-Vorgaben (verwaltet)", rendered)
        self.assertIn("- Actionstory. Blutig. Riskante Mission.", rendered)
        managed_block = rendered.split("## Story-Vorgaben (verwaltet)", 1)[1]
        self.assertEqual(sum(1 for line in managed_block.splitlines() if line.startswith("- ")), 1)
        self.assertTrue(rendered.endswith("\n"))
        self.assertEqual(rendered.count("## Story-Vorgaben (verwaltet)"), 1)

    def test_existing_managed_section_is_replaced_once(self):
        original = (
            "## Hauptteil\nBasis\n\n"
            "## Zwingende Story-Vorgaben (verwaltet)\n- Alt\n- Weg damit\n\n"
            "## Stimmung\n- Warm\n"
        )

        rendered = self.core.replace_managed_prompt_section(original, "Neu\nNoch neuer")

        self.assertNotIn("- Alt", rendered)
        self.assertNotIn("- Weg damit", rendered)
        self.assertIn("## Stimmung\n- Warm", rendered)
        self.assertEqual(rendered.count("## Story-Vorgaben (verwaltet)"), 1)

    def test_managed_directive_reaches_story_text_and_image_configs(self):
        generator = load_generator()
        prompt_path = self.root / "story_prompt_config.md"
        original = "## Hauptteil\nBasis\n\n## Ort\n- Hafen\n"
        rendered = self.core.replace_managed_prompt_section(
            original,
            "Actionstory.\nBlutig.\nRiskante Mission.",
        )
        prompt_path.write_text(rendered, encoding="utf-8")

        text_config, image_config = generator.build_story_generation_configs(prompt_path)

        for expected in ("Actionstory.", "Blutig.", "Riskante Mission."):
            self.assertIn(expected, text_config)
            self.assertIn(expected, image_config)

    def test_blank_directive_removes_managed_section(self):
        original = (
            "## Hauptteil\nBasis\n\n"
            "## Zwingende Story-Vorgaben (verwaltet)\n- Alt\n\n"
            "## Stimmung\n- Warm\n"
        )

        rendered = self.core.replace_managed_prompt_section(original, " \n ")

        self.assertNotIn("Zwingende Story-Vorgaben", rendered)
        self.assertIn("## Stimmung\n- Warm", rendered)

    def test_apply_uses_pending_next_volume_and_writes_private_files(self):
        env_path = self.root / "openai.env"
        state_path = self.root / "state.json"
        ledger_path = self.root / "ledger.json"
        prompt_path = self.root / "story_prompt_config.md"
        output_dir = self.root / "out"
        output_dir.mkdir()
        env_path.write_text(
            "\n".join(
                [
                    f"WIRTELPRIMPF_LOCAL_OUTDIR={output_dir}",
                    f"WIRTELPRIMPF_STORY_STATE={state_path}",
                    f"WIRTELPRIMPF_STORY_DIRECTIVES={ledger_path}",
                    f"WIRTELPRIMPF_STORY_PROMPT_CONFIG={prompt_path}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        state_path.write_text(
            json.dumps({"current_volume": 2, "pending_new_volume": True}),
            encoding="utf-8",
        )
        prompt_path.write_text("## Hauptteil\nBasis\n\n## Ort\n- Hafen\n", encoding="utf-8")

        result = self.core.apply_active_directive(env_path=env_path)

        self.assertEqual(result["current_volume"], 3)
        self.assertTrue(result["directive_applied"])
        prompt_text = prompt_path.read_text(encoding="utf-8")
        self.assertIn("Actionstory", prompt_text)
        self.assertIn("Blutig", prompt_text)
        self.assertEqual(stat.S_IMODE(prompt_path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(ledger_path.stat().st_mode), 0o600)

    def test_apply_rejects_symlink_prompt_target(self):
        env_path = self.root / "openai.env"
        state_path = self.root / "state.json"
        ledger_path = self.root / "ledger.json"
        real_prompt = self.root / "real.md"
        prompt_link = self.root / "story_prompt_config.md"
        real_prompt.write_text("## Hauptteil\nBasis\n", encoding="utf-8")
        prompt_link.symlink_to(real_prompt)
        state_path.write_text(json.dumps({"current_volume": 3}), encoding="utf-8")
        env_path.write_text(
            "\n".join(
                [
                    f"WIRTELPRIMPF_STORY_STATE={state_path}",
                    f"WIRTELPRIMPF_STORY_DIRECTIVES={ledger_path}",
                    f"WIRTELPRIMPF_STORY_PROMPT_CONFIG={prompt_link}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "symlink"):
            self.core.apply_active_directive(env_path=env_path)


class StoryDirectivesIntegrationTests(unittest.TestCase):
    def test_settings_schema_exposes_story_directives_page(self):
        schema = json.loads(SETTINGS_SCHEMA_PATH.read_text(encoding="utf-8"))

        self.assertIn("story-directives-page", schema["layout"]["pages"])
        page = schema["layout"]["story-directives-page"]
        self.assertIn("story-directives-section", page["sections"])
        widget = schema["story-directives-editor"]
        self.assertEqual(widget["file"], "StoryDirectives.py")
        self.assertEqual(widget["widget"], "StoryDirectivesEditor")
        self.assertTrue(STORY_UI_PATH.is_file())

    def test_systemd_applies_installed_directives_cli_before_generator(self):
        service = SERVICE_PATH.read_text(encoding="utf-8")

        self.assertIn("ExecStartPre=", service)
        self.assertIn("%h/.local/bin/wirtelprimpf-story-directives apply", service)
        self.assertNotIn("cinnamon/applets", service)
        self.assertLess(service.index("ExecStartPre="), service.index("ExecStart="))

    def test_local_install_manages_directives_cli(self):
        install_script = INSTALL_SCRIPT_PATH.read_text(encoding="utf-8")
        uninstall_script = UNINSTALL_SCRIPT_PATH.read_text(encoding="utf-8")

        self.assertIn("wirtelprimpf-story-directives", install_script)
        self.assertIn("story_directives_core.py", install_script)
        self.assertIn("wirtelprimpf-story-directives is preserved", uninstall_script)

    def test_make_check_compiles_and_runs_story_directives(self):
        makefile = MAKEFILE_PATH.read_text(encoding="utf-8")

        self.assertIn("story_directives_core.py", makefile)
        self.assertIn("StoryDirectives.py", makefile)
        self.assertIn("tests/test_story_directives.py", makefile)


if __name__ == "__main__":
    unittest.main()
