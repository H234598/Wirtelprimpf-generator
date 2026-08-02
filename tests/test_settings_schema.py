#!/usr/bin/env python3
"""Static packaging checks for Cinnamon settings that do not require GTK."""

from __future__ import annotations

import ast
import fcntl
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
APPLET_ROOT = ROOT / "files" / "wirtelprimfgenerator@H234598"
SETTINGS_LOGO_PATH = APPLET_ROOT / "SettingsLogo.py"
SYNC_PATH = APPLET_ROOT / "settings_sync.py"


def editor_literal(name: str):
    tree = ast.parse(
        SETTINGS_LOGO_PATH.read_text(encoding="utf-8"),
        filename=str(SETTINGS_LOGO_PATH),
    )
    editor = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "GeneratorConfigEditor"
    )
    assignment = next(
        node
        for node in editor.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)
    )
    return ast.literal_eval(assignment.value)


def load_settings_logo_module():
    module_names = ("JsonSettingsWidgets", "gi", "gi.repository", "settings_sync")
    previous_modules = {name: sys.modules.get(name) for name in module_names}
    json_widgets = ModuleType("JsonSettingsWidgets")
    json_widgets.SettingsWidget = object
    gi_module = ModuleType("gi")
    repository_module = ModuleType("gi.repository")
    for name in ("Gdk", "GdkPixbuf", "Gio", "GLib", "Gtk"):
        setattr(repository_module, name, SimpleNamespace())
    sync_spec = importlib.util.spec_from_file_location("settings_sync", SYNC_PATH)
    if sync_spec is None or sync_spec.loader is None:
        raise AssertionError(f"Cannot load {SYNC_PATH}")
    sync_module = importlib.util.module_from_spec(sync_spec)
    sys.modules.update(
        {
            "JsonSettingsWidgets": json_widgets,
            "gi": gi_module,
            "gi.repository": repository_module,
            "settings_sync": sync_module,
        }
    )
    try:
        sync_spec.loader.exec_module(sync_module)
        logo_spec = importlib.util.spec_from_file_location(
            "settings_logo_interaction_under_test",
            SETTINGS_LOGO_PATH,
        )
        if logo_spec is None or logo_spec.loader is None:
            raise AssertionError(f"Cannot load {SETTINGS_LOGO_PATH}")
        logo_module = importlib.util.module_from_spec(logo_spec)
        logo_spec.loader.exec_module(logo_module)
        return logo_module
    finally:
        for name, previous in previous_modules.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous


class SensitiveWidget:
    def __init__(self, sensitive: bool = True) -> None:
        self.sensitive = sensitive

    def set_sensitive(self, sensitive: bool) -> None:
        self.sensitive = bool(sensitive)


class CatalogCombo:
    def __init__(self, observe_mutation=None) -> None:
        self.observe_mutation = observe_mutation or (lambda: None)
        self.options = []
        self.active_id = None
        self.hexpand = False

    def set_hexpand(self, enabled: bool) -> None:
        self.hexpand = bool(enabled)

    def remove_all(self) -> None:
        self.observe_mutation()
        self.options = []
        self.active_id = None

    def append(self, value: str, label: str) -> None:
        self.observe_mutation()
        self.options.append((value, label))

    def set_active_id(self, value: str) -> None:
        self.observe_mutation()
        self.active_id = value if any(option == value for option, _label in self.options) else None


def bare_editor(module):
    editor = object.__new__(module.GeneratorConfigEditor)
    editor._save_busy = False
    editor._operation_busy = False
    editor._disposed = False
    editor.widgets = {}
    editor.secret_entries = {}
    editor.secret_delete_checks = {}
    editor.sync_state = None
    editor.save_button = SensitiveWidget(False)
    editor.discard_all_button = SensitiveWidget(False)
    editor.run_button = SensitiveWidget()
    editor.timer_button = SensitiveWidget()
    editor.status = SimpleNamespace(set_text=lambda text: setattr(editor, "status_text", text))
    return editor


class SettingsSchemaTests(unittest.TestCase):
    def test_no_stale_about_version_setting_key(self) -> None:
        schema = json.loads((APPLET_ROOT / "settings-schema.json").read_text(encoding="utf-8"))
        self.assertNotIn("about-version", schema)

    def test_version_watch_controls_are_not_in_settings_editor(self) -> None:
        source = SETTINGS_LOGO_PATH.read_text(encoding="utf-8")
        forbidden = (
            "SLEEP_SECONDS",
            "DEFAULT_RETRY_DELAY_SECONDS",
            "MAX_STALE_LOCK_SECONDS",
            "watch_timer_enabled",
            "watch_on_boot",
            "watch_persistent",
            "watch_restart_sec",
            "wirtelprimpf-version-watch.timer",
            "wirtelprimpf-version-watch.service",
        )
        for needle in forbidden:
            with self.subTest(needle=needle):
                self.assertNotIn(needle, source)

    def test_applet_uses_split_generator_identity_and_canonical_platform_keys(self) -> None:
        schema = json.loads((APPLET_ROOT / "settings-schema.json").read_text(encoding="utf-8"))
        source = SETTINGS_LOGO_PATH.read_text(encoding="utf-8")
        helper_source = (APPLET_ROOT / "helper.py").read_text(encoding="utf-8")
        field_keys = {
            field[0]
            for _section, fields in editor_literal("field_sections")
            for field in fields
        }
        secret_keys = {secret[0] for secret in editor_literal("secret_specs")}
        self.assertEqual(
            schema["github-url"]["default"],
            "https://github.com/H234598/Wirtelprimpf-generator",
        )
        for text in (source, helper_source):
            self.assertNotIn("H234598/Katzenbilder", text)
        for key in (
            "media_mode",
            "platform_state",
            "hub_dispatch_state",
            "generator_root",
            "archive_root",
            "platform_catalog",
            "cloudflare_api_token",
            "image_model",
            "story_model",
        ):
            with self.subTest(key=key):
                self.assertIn(key, field_keys | secret_keys)

    def test_applet_has_no_independent_configuration_writer_methods(self) -> None:
        tree = ast.parse(SETTINGS_LOGO_PATH.read_text(encoding="utf-8"), filename=str(SETTINGS_LOGO_PATH))
        defined = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        forbidden = {
            "_read_env_file",
            "_existing_env_lines",
            "_atomic_write_text",
            "_write_env_file",
            "_write_dropin",
            "_write_systemd_dropins",
            "_apply_enabled_state",
        }
        self.assertEqual(defined & forbidden, set())

    def test_choice_and_model_widgets_preserve_external_legacy_values_during_refresh(self) -> None:
        module = load_settings_logo_module()
        module.Gtk.ComboBoxText = CatalogCombo
        editor = bare_editor(module)
        editor._suppress_dirty = False

        choice = editor._make_value_widget(
            "operandi",
            "choice",
            ["classic", "story", "both"],
            "external-operandi",
        )
        model = editor._make_value_widget(
            "story_model",
            "model",
            ["gpt-5.5"],
            "external-story-model",
        )
        self.assertEqual(choice.options[0][0], "external-operandi")
        self.assertIn("nicht mehr im empfohlenen Katalog", choice.options[0][1])
        self.assertEqual(model.options[0][0], "external-story-model")

        suppress_states = []
        choice.observe_mutation = lambda: suppress_states.append(editor._suppress_dirty)
        model.observe_mutation = lambda: suppress_states.append(editor._suppress_dirty)
        editor.widgets = {"operandi": choice, "story_model": model}
        editor._apply_visible_values(
            {
                "choices": {
                    "operandi": ["classic", "story", "both"],
                    "story_model": ["gpt-5.5"],
                }
            },
            {
                "operandi": "remote-custom-operandi",
                "story_model": "remote-custom-story-model",
            },
        )

        self.assertEqual(choice.active_id, "remote-custom-operandi")
        self.assertEqual(model.active_id, "remote-custom-story-model")
        self.assertTrue(suppress_states)
        self.assertTrue(all(suppress_states))
        self.assertFalse(editor._suppress_dirty)

    def test_sync_helper_is_packaged_and_exports_the_coordinator(self) -> None:
        self.assertTrue(SYNC_PATH.is_file())
        spec = importlib.util.spec_from_file_location("settings_sync_schema_smoke", SYNC_PATH)
        self.assertIsNotNone(spec)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
        finally:
            sys.modules.pop(spec.name, None)
        self.assertTrue(callable(module.SettingsSyncCoordinator))
        self.assertTrue(callable(module.SettingsCliClient))

    def test_generator_dropin_does_not_clear_private_runtime_environment(self) -> None:
        source = SETTINGS_LOGO_PATH.read_text(encoding="utf-8")
        self.assertNotIn('"Environment=",', source)

    def test_discard_confirmation_is_modal_for_the_settings_toplevel(self) -> None:
        module = load_settings_logo_module()

        class Window:
            pass

        captured = {}

        class Dialog:
            def __init__(self, **kwargs) -> None:
                captured["kwargs"] = kwargs
                captured["destroyed"] = False

            def run(self):
                return "cancel"

            def destroy(self) -> None:
                captured["destroyed"] = True

        module.Gtk = SimpleNamespace(
            Window=Window,
            MessageDialog=Dialog,
            DialogFlags=SimpleNamespace(MODAL="modal"),
            MessageType=SimpleNamespace(QUESTION="question"),
            ButtonsType=SimpleNamespace(OK_CANCEL="ok-cancel"),
            ResponseType=SimpleNamespace(OK="ok"),
        )
        editor = bare_editor(module)
        editor.sync_state = SimpleNamespace()
        toplevel = Window()
        editor.get_toplevel = lambda: toplevel

        editor._on_discard_all(None)

        self.assertIs(captured["kwargs"]["transient_for"], toplevel)
        self.assertEqual(captured["kwargs"]["flags"], "modal")
        self.assertTrue(captured["destroyed"])

    def test_operational_buttons_follow_the_shared_interaction_guard_behavior(self) -> None:
        module = load_settings_logo_module()
        editor = bare_editor(module)
        for save_busy, operation_busy, expected_busy in (
            (False, False, False),
            (True, False, True),
            (False, True, True),
            (True, True, True),
        ):
            with self.subTest(save_busy=save_busy, operation_busy=operation_busy):
                editor._save_busy = save_busy
                editor._operation_busy = operation_busy
                self.assertEqual(editor._interaction_busy(), expected_busy)
                editor._update_operation_sensitivity()
                self.assertEqual(editor.run_button.sensitive, not expected_busy)
                self.assertEqual(editor.timer_button.sensitive, not expected_busy)

    def test_background_operation_cannot_start_while_save_is_busy(self) -> None:
        module = load_settings_logo_module()
        editor = bare_editor(module)
        editor._save_busy = True
        with mock.patch.object(module.threading, "Thread") as thread:
            editor._run_operation((("systemctl", "--user", "start", "unit"),), "ok", "failed")
        thread.assert_not_called()
        self.assertFalse(editor._operation_busy)

    def test_save_cannot_start_while_background_operation_is_busy(self) -> None:
        module = load_settings_logo_module()
        editor = bare_editor(module)
        editor._operation_busy = True
        state = mock.Mock()
        state.build_request.side_effect = AssertionError("save must not build a request")
        editor.sync_coordinator = SimpleNamespace(state=state)

        editor._on_save(None)

        state.build_request.assert_not_called()

    def test_busy_sensitivity_never_reenables_actions_owned_by_other_operation(self) -> None:
        module = load_settings_logo_module()
        editor = bare_editor(module)

        editor._on_sync_busy(True)
        self.assertFalse(editor.run_button.sensitive)
        self.assertFalse(editor.timer_button.sensitive)

        editor._operation_busy = True
        editor._on_sync_busy(False)
        self.assertFalse(editor.run_button.sensitive)
        self.assertFalse(editor.timer_button.sensitive)

        editor._save_busy = True
        editor._finish_operation_idle("done")
        self.assertFalse(editor.run_button.sensitive)
        self.assertFalse(editor.timer_button.sensitive)

    def test_operation_success_failure_and_thread_start_failure_release_gate(self) -> None:
        module = load_settings_logo_module()
        module.GLib = SimpleNamespace(
            idle_add=lambda callback, *args: callback(*args),
        )
        with tempfile.TemporaryDirectory() as temporary:
            lock_path = Path(temporary) / "private" / "settings.lock"
            for error, expected_status in (
                (None, "ok"),
                (RuntimeError("injected"), "failed: injected"),
            ):
                with self.subTest(error=error):
                    editor = bare_editor(module)
                    editor.settings_lock_path = str(lock_path)
                    editor._operation_busy = True

                    def run(_command, operation_error=error):
                        if operation_error is not None:
                            raise operation_error

                    editor._run = run
                    editor._operation_worker((("command",),), "ok", "failed")
                    self.assertFalse(editor._operation_busy)
                    self.assertTrue(editor.run_button.sensitive)
                    self.assertTrue(editor.timer_button.sensitive)
                    self.assertEqual(editor.status_text, expected_status)

        editor = bare_editor(module)
        failing_thread = mock.Mock()
        failing_thread.start.side_effect = RuntimeError("cannot start")
        with mock.patch.object(module.threading, "Thread", return_value=failing_thread):
            editor._run_operation((("command",),), "ok", "failed")
        self.assertFalse(editor._operation_busy)
        self.assertTrue(editor.run_button.sensitive)
        self.assertTrue(editor.timer_button.sensitive)
        self.assertEqual(editor.status_text, "failed")

    def test_operational_command_sequence_holds_the_settings_lock_until_completion(self) -> None:
        module = load_settings_logo_module()
        module.GLib = SimpleNamespace(
            idle_add=lambda callback, *args: callback(*args),
        )
        with tempfile.TemporaryDirectory() as temporary:
            lock_path = Path(temporary) / "private" / "settings.lock"
            editor = bare_editor(module)
            editor.settings_lock_path = str(lock_path)
            editor._operation_busy = True
            observed_commands = []

            def run(command):
                observed_commands.append(command)
                with (
                    lock_path.open("a+b") as competitor,
                    self.assertRaises(BlockingIOError),
                ):
                    fcntl.flock(
                        competitor.fileno(),
                        fcntl.LOCK_EX | fcntl.LOCK_NB,
                    )

            editor._run = run
            commands = (("first",), ("second",))

            editor._operation_worker(commands, "ok", "failed")

            self.assertEqual(observed_commands, list(commands))
            self.assertEqual(editor.status_text, "ok")
            self.assertFalse(editor._operation_busy)

    def test_competing_settings_lock_blocks_systemctl_and_releases_ui_gate_redacted(self) -> None:
        module = load_settings_logo_module()
        module.GLib = SimpleNamespace(
            idle_add=lambda callback, *args: callback(*args),
        )
        with tempfile.TemporaryDirectory() as temporary:
            lock_path = Path(temporary) / "private" / "settings.lock"
            lock_path.parent.mkdir(parents=True)
            lock_path.touch()
            editor = bare_editor(module)
            editor.settings_lock_path = str(lock_path)
            editor._operation_busy = True
            editor._run = mock.Mock()

            with lock_path.open("a+b") as competitor:
                fcntl.flock(
                    competitor.fileno(),
                    fcntl.LOCK_EX | fcntl.LOCK_NB,
                )
                editor._operation_worker(
                    (("systemctl", "--user", "start", "wirtelprimpf.service"),),
                    "ok",
                    "failed",
                )

            editor._run.assert_not_called()
            self.assertFalse(editor._operation_busy)
            self.assertTrue(editor.run_button.sensitive)
            self.assertTrue(editor.timer_button.sensitive)
            self.assertEqual(
                editor.status_text,
                "failed: Einstellungen sind vorübergehend gesperrt",
            )
            self.assertNotIn(str(lock_path), editor.status_text)


if __name__ == "__main__":
    unittest.main()
