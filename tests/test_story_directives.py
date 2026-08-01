#!/usr/bin/env python3
"""Behavior and integration tests for per-story Wirtelprimpf directives."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
CORE_PATH = ROOT / "files" / "wirtelprimfgenerator@H234598" / "story_directives_core.py"
GENERATOR_PATH = ROOT / "Sourcecode" / "wirtelprimpf_generator.py"
SERVICE_PATH = ROOT / "Sourcecode" / "systemd-user" / "wirtelprimpf.service"
SOURCE_README_PATH = ROOT / "Sourcecode" / "README.md"
STORY_GUIDE_PATH = ROOT / "Sourcecode" / "STORY_DIRECTIVES.md"
IMPLEMENTATION_PLAN_PATH = ROOT / "docs" / "superpowers" / "plans" / "2026-07-31-story-directives-implementation.md"
CHECK_WORKFLOW_PATH = ROOT / ".github" / "workflows" / "check.yml"
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

    def test_story_volume_rejects_boolean_even_when_key_is_one(self):
        ledger = {
            "schema_version": 1,
            "created_at": "2026-07-31T17:00:12Z",
            "updated_at": "2026-07-31T17:00:12Z",
            "migrations": {"story_iii_seeded": True},
            "stories": {
                "1": {
                    "volume": True,
                    "directive": "Ungültiger Bool-Band",
                    "created_at": "2026-07-31T17:00:12Z",
                    "updated_at": "2026-07-31T17:00:12Z",
                    "source": "test",
                }
            },
        }

        with self.assertRaisesRegex(ValueError, "positive integer"):
            self.core.validate_ledger(ledger)

    def test_story_key_must_be_canonical_decimal(self):
        ledger = {
            "schema_version": 1,
            "created_at": "2026-07-31T17:00:12Z",
            "updated_at": "2026-07-31T17:00:12Z",
            "migrations": {"story_iii_seeded": True},
            "stories": {
                "01": {
                    "volume": 1,
                    "directive": "Darf nicht still ignoriert werden",
                    "created_at": "2026-07-31T17:00:12Z",
                    "updated_at": "2026-07-31T17:00:12Z",
                    "source": "test",
                }
            },
        }

        with self.assertRaisesRegex(ValueError, "canonical positive integer"):
            self.core.validate_ledger(ledger)

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
        state_path = self.root / "story_state.json"
        state_path.write_text(json.dumps({"current_volume": 3}), encoding="utf-8")
        self.core.load_ledger(ledger_path, seed_story_iii=True)

        with self.assertRaises(self.core.EditableWindowChanged) as captured:
            self.core.save_editable_window(
                ledger_path,
                state_path=state_path,
                current_volume=3,
                directives={2: "Vergangenheit ändern", 3: "Aktuell", 4: "Nächste"},
            )
        self.assertIn("editable story window changed", str(captured.exception))

    def test_editable_window_rejects_story_state_that_advanced_after_reload(self):
        ledger_path = self.root / "story_directives.json"
        state_path = self.root / "story_state.json"
        state_path.write_text(json.dumps({"current_volume": 4}), encoding="utf-8")
        self.core.load_ledger(ledger_path, seed_story_iii=True)

        with self.assertRaises(self.core.EditableWindowChanged) as captured:
            self.core.save_editable_window(
                ledger_path,
                state_path=state_path,
                current_volume=3,
                directives={3: "Inzwischen vergangen", 4: "Aktuell", 5: "Nächste"},
            )
        self.assertIn("editable story window changed", str(captured.exception))

        ledger = self.core.load_ledger(ledger_path, seed_story_iii=True)
        self.assertNotIn("Inzwischen vergangen", json.dumps(ledger, ensure_ascii=False))

    def test_generator_state_write_waits_for_editable_window_transaction(self):
        generator = load_generator()
        ledger_path = self.root / "story_directives.json"
        state_path = self.root / "story_state.json"
        state_path.write_text(json.dumps({"current_volume": 3}), encoding="utf-8")
        save_entered = threading.Event()
        release_save = threading.Event()
        writer_done = threading.Event()
        failures = []

        def delayed_save(*_args, **_kwargs):
            save_entered.set()
            if not release_save.wait(5):
                raise RuntimeError("test timed out while holding the state transaction")
            return {}

        def save_window():
            try:
                self.core.save_editable_window(
                    ledger_path,
                    state_path=state_path,
                    current_volume=3,
                    directives={3: "Aktuell", 4: "Nächste", 5: "Übernächste"},
                )
            except Exception as exc:
                failures.append(exc)

        def advance_state():
            try:
                generator.write_story_state(
                    state_path,
                    generator.StoryState(current_volume=4),
                )
            except Exception as exc:
                failures.append(exc)
            finally:
                writer_done.set()

        with mock.patch.object(self.core, "save_directives", side_effect=delayed_save):
            saver = threading.Thread(target=save_window, name="directive-save")
            saver.start()
            reached_transaction = save_entered.wait(0.5)
            writer = threading.Thread(target=advance_state, name="state-write")
            if reached_transaction:
                writer.start()
                writer_finished_while_save_was_open = writer_done.wait(0.25)
            else:
                writer_finished_while_save_was_open = True
            release_save.set()
            saver.join(5)
            if writer.ident is not None:
                writer.join(5)

        self.assertTrue(reached_transaction, failures)
        self.assertFalse(
            writer_finished_while_save_was_open,
            "story state writer bypassed the editable-window transaction lock",
        )
        self.assertFalse(failures)
        self.assertFalse(saver.is_alive())
        self.assertFalse(writer.is_alive())

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

    def test_parent_creation_secures_every_new_directory_level(self):
        ledger_path = self.root / "private" / "nested" / "story_directives.json"

        self.core.load_ledger(ledger_path, seed_story_iii=True)

        self.assertEqual(stat.S_IMODE((self.root / "private").stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((self.root / "private" / "nested").stat().st_mode), 0o700)

    def test_parent_creation_rejects_intermediate_symlink(self):
        real_parent = self.root / "real-parent"
        real_parent.mkdir()
        linked_parent = self.root / "linked-parent"
        linked_parent.symlink_to(real_parent, target_is_directory=True)
        ledger_path = linked_parent / "nested" / "story_directives.json"

        with self.assertRaisesRegex(ValueError, "symlink"):
            self.core.load_ledger(ledger_path, seed_story_iii=True)

        self.assertFalse((real_parent / "nested").exists())

    def test_regular_file_reader_keeps_open_descriptor_when_path_is_replaced(self):
        env_path = self.root / "openai.env"
        moved_path = self.root / "openai.original"
        attacker_path = self.root / "attacker.env"
        env_path.write_text("SAFE=original\n", encoding="utf-8")
        attacker_path.write_text("SAFE=attacker\n", encoding="utf-8")
        original_fdopen = os.fdopen
        swapped = threading.Event()

        def replace_path_after_open(descriptor, *args, **kwargs):
            if not swapped.is_set():
                env_path.rename(moved_path)
                env_path.symlink_to(attacker_path)
                swapped.set()
            return original_fdopen(descriptor, *args, **kwargs)

        with mock.patch.object(self.core.os, "fdopen", side_effect=replace_path_after_open):
            values = self.core.read_env_file(env_path)

        self.assertTrue(swapped.is_set(), "reader did not consume the already-open descriptor")
        self.assertEqual(values["SAFE"], "original")

    def test_concurrent_directive_saves_do_not_lose_an_update(self):
        ledger_path = self.root / "story_directives.json"
        self.core.load_ledger(ledger_path, seed_story_iii=True)
        original_atomic_write_json = self.core.atomic_write_json
        first_at_write = threading.Event()
        release_first = threading.Event()
        second_started = threading.Event()
        second_done = threading.Event()
        failures = []

        def delayed_first_write(path, payload):
            if threading.current_thread().name == "first-save":
                first_at_write.set()
                if not release_first.wait(5):
                    raise RuntimeError("test timed out while holding the first write")
            return original_atomic_write_json(path, payload)

        def save(volume, directive, done=None):
            try:
                if done is second_done:
                    second_started.set()
                self.core.save_directives(ledger_path, {volume: directive})
            except Exception as exc:  # collected and asserted in the test thread
                failures.append(exc)
            finally:
                if done is not None:
                    done.set()

        with mock.patch.object(
            self.core, "atomic_write_json", side_effect=delayed_first_write
        ):
            first = threading.Thread(
                target=save, args=(4, "Vorgabe vier"), name="first-save"
            )
            second = threading.Thread(
                target=save,
                args=(5, "Vorgabe fünf", second_done),
                name="second-save",
            )
            first.start()
            self.assertTrue(first_at_write.wait(5), "first save did not reach its write")
            second.start()
            self.assertTrue(second_started.wait(5), "second save thread did not start")
            second_finished_while_first_was_open = second_done.wait(0.25)
            release_first.set()
            first.join(5)
            second.join(5)

        self.assertFalse(
            second_finished_while_first_was_open,
            "second save bypassed the exclusive ledger transaction",
        )
        self.assertFalse(failures)
        self.assertFalse(first.is_alive())
        self.assertFalse(second.is_alive())
        ledger = self.core.load_ledger(ledger_path, seed_story_iii=True)
        self.assertEqual(ledger["stories"]["4"]["directive"], "Vorgabe vier")
        self.assertEqual(ledger["stories"]["5"]["directive"], "Vorgabe fünf")


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

    def test_source_readme_installs_directives_cli_before_service(self):
        readme = SOURCE_README_PATH.read_text(encoding="utf-8")
        helper_source = "files/wirtelprimfgenerator@H234598/story_directives_core.py"
        helper_target = "~/.local/bin/wirtelprimpf-story-directives"
        service_source = "Sourcecode/systemd-user/wirtelprimpf.service"

        self.assertIn(helper_source, readme)
        self.assertIn(helper_target, readme)
        self.assertLess(readme.index(helper_source), readme.index(service_source))
        checkout = "cd ~/.local/share/wirtelprimpf-generator"
        venv = "python3 -m venv ~/.local/share/wirtelprimpf-generator/.venv"
        pip_install = "~/.local/share/wirtelprimpf-generator/.venv/bin/pip install"
        self.assertIn(checkout, readme)
        self.assertLess(readme.index(venv), readme.index(checkout))
        self.assertLess(readme.index(checkout), readme.index(pip_install))

    def test_source_guides_use_only_the_current_generator_runtime_paths(self):
        for path in (SOURCE_README_PATH, STORY_GUIDE_PATH):
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("~/.local/share/wirtelprimpf-venv", text)
                self.assertNotIn("~/.local/bin/wirtelprimpf_generator.py", text)
                self.assertIn("~/.local/share/wirtelprimpf-generator/.venv", text)

    def test_source_readme_documents_exit_code_two_for_any_per_plan_failure(self):
        readme = SOURCE_README_PATH.read_text(encoding="utf-8")

        self.assertIn(
            "one or more per-plan generation, write, transform, or repository-publication operations failed",
            readme,
        )
        self.assertNotIn(
            "partial failure; at least one prompt or image failed while another succeeded",
            readme,
        )

    def test_repo_plan_documents_state_path_in_editable_window_signature(self):
        plan = IMPLEMENTATION_PLAN_PATH.read_text(encoding="utf-8")

        self.assertIn(
            "save_editable_window(path, *, state_path, current_volume, directives, ...)",
            plan,
        )

    def test_applet_ci_pins_the_node_runtime_used_by_make_check(self):
        workflow = CHECK_WORKFLOW_PATH.read_text(encoding="utf-8")
        applet_job = workflow.split("  applet:\n", 1)[1].split("  platform:\n", 1)[0]

        self.assertIn("actions/setup-node@", applet_job)
        self.assertIn('node-version: "24.13.1"', applet_job)

    def test_make_check_compiles_and_runs_story_directives(self):
        make_executable = shutil.which("make")
        if make_executable is None:
            self.skipTest("make is not available")
        result = subprocess.run(
            [make_executable, "-n", "check"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

        makefile = MAKEFILE_PATH.read_text(encoding="utf-8")
        self.assertIn("story_directives_core.py", makefile)
        self.assertIn("StoryDirectives.py", makefile)
        self.assertIn("-m unittest tests.test_story_directives", result.stdout)

    def test_story_editor_catches_typed_stale_window_exception(self):
        source = STORY_UI_PATH.read_text(encoding="utf-8")

        self.assertIn("except core.EditableWindowChanged:", source)
        self.assertNotIn('"editable story window changed" in str(exc)', source)

    def test_projection_failure_is_reported_after_successful_ledger_save(self):
        ui_module_name = "story_directives_ui_under_test"
        json_widgets = ModuleType("JsonSettingsWidgets")
        json_widgets.SettingsWidget = object
        gi_module = ModuleType("gi")
        repository_module = ModuleType("gi.repository")
        repository_module.Gtk = SimpleNamespace()
        previous_modules = {
            name: sys.modules.get(name)
            for name in ("JsonSettingsWidgets", "gi", "gi.repository")
        }
        sys.modules["JsonSettingsWidgets"] = json_widgets
        sys.modules["gi"] = gi_module
        sys.modules["gi.repository"] = repository_module
        try:
            spec = importlib.util.spec_from_file_location(ui_module_name, STORY_UI_PATH)
            if spec is None or spec.loader is None:
                self.fail(f"Cannot load {STORY_UI_PATH}")
            ui = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(ui)
        finally:
            for name, previous in previous_modules.items():
                if previous is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = previous

        editor = object.__new__(ui.StoryDirectivesEditor)
        editor.env_path = Path("/test/openai.env")
        editor.editable_buffers = {3: object(), 4: object(), 5: object()}
        editor._buffer_text = mock.Mock(side_effect=lambda _buffer: "Vorgabe")
        editor._read_context = mock.Mock(
            return_value=(
                {
                    "ledger": Path("/test/ledger.json"),
                    "state": Path("/test/story-state.json"),
                },
                3,
                {},
                {},
            )
        )
        editor._reload = mock.Mock()
        editor._set_status = mock.Mock()

        with mock.patch.object(ui.core, "save_editable_window") as save, mock.patch.object(
            ui.core,
            "apply_active_directive",
            side_effect=RuntimeError("Prompt ist nicht erreichbar"),
        ):
            editor._on_save(None)

        save.assert_called_once()
        editor._reload.assert_called_once()
        status_text = editor._set_status.call_args.args[0]
        self.assertIn("gespeichert", status_text.lower())
        self.assertIn("prompt", status_text.lower())
        self.assertIn("nicht erreichbar", status_text.lower())
        self.assertNotIn("speichern fehlgeschlagen", status_text.lower())


if __name__ == "__main__":
    unittest.main()
