#!/usr/bin/env python3
"""Static checks for Cinnamon settings that should not require GTK."""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SETTINGS_LOGO_PATH = ROOT / "files" / "wirtelprimfgenerator@H234598" / "SettingsLogo.py"

OFFICIAL_IMAGE_MODELS = (
    "gpt-image-2",
    "gpt-image-1.5",
    "gpt-image-1",
    "gpt-image-1-mini",
)


def extract_constant_tuple(path: Path, name: str) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            continue
        if not isinstance(node.value, ast.Tuple):
            raise AssertionError(f"{name} must be a tuple literal")
        values = []
        for element in node.value.elts:
            if not isinstance(element, ast.Constant) or not isinstance(element.value, str):
                raise AssertionError(f"{name} must contain only string literals")
            values.append(element.value)
        return tuple(values)
    raise AssertionError(f"{name} not found in {path}")


class FakeComboBoxText:
    def __init__(self):
        self.ids = []
        self.active_id = None
        self.hexpand = False

    def append(self, row_id, _label):
        self.ids.append(row_id)

    def set_hexpand(self, value):
        self.hexpand = bool(value)

    def set_active_id(self, row_id):
        if row_id in self.ids:
            self.active_id = row_id
            return True
        self.active_id = None
        return False

    def get_active_id(self):
        return self.active_id


class FakeSwitch:
    pass


class FakeSpinButton:
    pass


class FakeEntry:
    def __init__(self, text=""):
        self.text = text
        self.placeholder = ""
        self.hexpand = False
        self.visible = True

    def get_text(self):
        return self.text

    def set_text(self, value):
        self.text = value

    def set_placeholder_text(self, value):
        self.placeholder = value

    def set_hexpand(self, value):
        self.hexpand = bool(value)

    def set_visibility(self, value):
        self.visible = bool(value)

    def set_invisible_char(self, _value):
        return None


def load_settings_logo_with_fake_gtk():
    module_name = "settings_logo_under_test"
    fake_gtk = types.SimpleNamespace(
        ComboBoxText=FakeComboBoxText,
        Switch=FakeSwitch,
        SpinButton=FakeSpinButton,
        Entry=FakeEntry,
    )
    replacements = {
        "JsonSettingsWidgets": types.SimpleNamespace(SettingsWidget=object),
        "gi": types.SimpleNamespace(repository=types.SimpleNamespace()),
        "gi.repository": types.SimpleNamespace(
            Gdk=types.SimpleNamespace(),
            GdkPixbuf=types.SimpleNamespace(),
            GLib=types.SimpleNamespace(),
            Gtk=fake_gtk,
        ),
    }
    original = {name: sys.modules.get(name) for name in replacements}
    try:
        for name, module in replacements.items():
            sys.modules[name] = module
        spec = importlib.util.spec_from_file_location(module_name, SETTINGS_LOGO_PATH)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Cannot load {SETTINGS_LOGO_PATH}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        for name, module in original.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module
        sys.modules.pop(module_name, None)


class SettingsSchemaTests(unittest.TestCase):
    def test_image_model_dropdown_uses_official_image_models(self):
        self.assertEqual(extract_constant_tuple(SETTINGS_LOGO_PATH, "IMAGE_MODEL_CHOICES"), OFFICIAL_IMAGE_MODELS)

    def test_unknown_combo_value_falls_back_to_default(self):
        module = load_settings_logo_with_fake_gtk()
        editor = module.GeneratorConfigEditor.__new__(module.GeneratorConfigEditor)
        widget = editor._make_value_widget("combo", OFFICIAL_IMAGE_MODELS, "gpt-image-2")

        editor._set_widget_value(widget, "gpt-image-2-2026-04-21")

        self.assertEqual(widget.ids, list(OFFICIAL_IMAGE_MODELS))
        self.assertEqual(widget.get_active_id(), "gpt-image-2")

    def test_no_stale_about_version_setting_key(self):
        schema_path = ROOT / "files" / "wirtelprimfgenerator@H234598" / "settings-schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))

        self.assertNotIn("about-version", schema)

    def test_version_watch_controls_are_not_in_settings_editor(self):
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

    def test_applet_uses_split_generator_identity_and_preserves_platform_settings(self):
        schema_path = ROOT / "files" / "wirtelprimfgenerator@H234598" / "settings-schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        settings_source = SETTINGS_LOGO_PATH.read_text(encoding="utf-8")
        helper_source = (SETTINGS_LOGO_PATH.parent / "helper.py").read_text(encoding="utf-8")

        self.assertEqual(
            schema["github-url"]["default"],
            "https://github.com/H234598/Wirtelprimpf-generator",
        )
        for source in (settings_source, helper_source):
            self.assertNotIn("H234598/Katzenbilder", source)
        for env_name in (
            "WIRTELPRIMPF_MEDIA_MODE",
            "WIRTELPRIMPF_PLATFORM_STATE",
            "WIRTELPRIMPF_HUB_DISPATCH_STATE",
            "WIRTELPRIMPF_GENERATOR_ROOT",
            "WIRTELPRIMPF_ARCHIVE_ROOT",
            "WIRTELPRIMPF_PLATFORM_CATALOG",
            "CLOUDFLARE_API_TOKEN",
        ):
            with self.subTest(env_name=env_name):
                self.assertIn(env_name, settings_source)

    def test_private_settings_reader_never_returns_secret_values(self):
        module = load_settings_logo_with_fake_gtk()
        editor = module.GeneratorConfigEditor.__new__(module.GeneratorConfigEditor)
        with tempfile.TemporaryDirectory() as tmpdir:
            editor.env_path = os.path.join(tmpdir, "openai.env")
            Path(editor.env_path).write_text(
                "OPENAI_API_KEY=fake-openai-secret\n"
                "CLOUDFLARE_API_TOKEN=fake-cloudflare-secret\n"
                "WIRTELPRIMPF_REPO_SLUG=H234598/Wirtelprimpf-0001\n",
                encoding="utf-8",
            )

            values = editor._read_env_file()

        self.assertNotIn("OPENAI_API_KEY", values)
        self.assertNotIn("CLOUDFLARE_API_TOKEN", values)
        self.assertEqual(values["WIRTELPRIMPF_REPO_SLUG"], "H234598/Wirtelprimpf-0001")

    def test_private_settings_write_preserves_blank_secrets_and_unknown_keys(self):
        module = load_settings_logo_with_fake_gtk()
        editor = module.GeneratorConfigEditor.__new__(module.GeneratorConfigEditor)
        editor.env_fields = (
            ("OPENAI_API_KEY", "OpenAI", "secret", ()),
            ("CLOUDFLARE_API_TOKEN", "Cloudflare", "secret", ()),
            ("WIRTELPRIMPF_REPO_SLUG", "Repo", "entry", ()),
        )
        editor.env_widgets = {
            "OPENAI_API_KEY": FakeEntry(""),
            "CLOUDFLARE_API_TOKEN": FakeEntry(""),
            "WIRTELPRIMPF_REPO_SLUG": FakeEntry("H234598/Wirtelprimpf-0001"),
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            editor.env_path = os.path.join(tmpdir, "config", "openai.env")
            path = Path(editor.env_path)
            path.parent.mkdir()
            path.write_text(
                "# custom comment\n"
                "OPENAI_API_KEY='fake preserved openai'\n"
                "CLOUDFLARE_API_TOKEN=fake-preserved-cloudflare\n"
                "FUTURE_SETTING=keep-me\n"
                "WIRTELPRIMPF_REPO_SLUG=old/repository\n",
                encoding="utf-8",
            )

            editor._write_env_file()
            content = path.read_text(encoding="utf-8")
            mode = path.stat().st_mode & 0o777
            parts = list(path.parent.glob(".*.part"))

        self.assertIn("# custom comment", content)
        self.assertIn("OPENAI_API_KEY='fake preserved openai'", content)
        self.assertIn("CLOUDFLARE_API_TOKEN=fake-preserved-cloudflare", content)
        self.assertIn("FUTURE_SETTING=keep-me", content)
        self.assertIn("WIRTELPRIMPF_REPO_SLUG=H234598/Wirtelprimpf-0001", content)
        self.assertEqual(mode, 0o600)
        self.assertEqual(parts, [])
        self.assertEqual(editor.env_widgets["OPENAI_API_KEY"].get_text(), "")
        self.assertEqual(editor.env_widgets["CLOUDFLARE_API_TOKEN"].get_text(), "")

    def test_private_settings_replace_failure_leaves_original_bytes(self):
        module = load_settings_logo_with_fake_gtk()
        editor = module.GeneratorConfigEditor.__new__(module.GeneratorConfigEditor)
        editor.env_fields = (("WIRTELPRIMPF_REPO_SLUG", "Repo", "entry", ()),)
        editor.env_widgets = {
            "WIRTELPRIMPF_REPO_SLUG": FakeEntry("H234598/Wirtelprimpf-0001"),
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            editor.env_path = os.path.join(tmpdir, "openai.env")
            path = Path(editor.env_path)
            original = b"WIRTELPRIMPF_REPO_SLUG=old/repository\n"
            path.write_bytes(original)

            with patch.object(module.os, "replace", side_effect=OSError("injected replace failure")):
                with self.assertRaises(OSError):
                    editor._write_env_file()

            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(path.parent.glob(".*.part")), [])

    def test_systemd_dropin_replace_failure_leaves_original_bytes(self):
        module = load_settings_logo_with_fake_gtk()
        editor = module.GeneratorConfigEditor.__new__(module.GeneratorConfigEditor)
        with tempfile.TemporaryDirectory() as tmpdir:
            editor.systemd_user_dir = tmpdir
            dropin = Path(tmpdir) / "wirtelprimpf.timer.d" / "override.conf"
            dropin.parent.mkdir()
            original = b"[Timer]\nOnUnitActiveSec=120min\n"
            dropin.write_bytes(original)

            with patch.object(module.os, "replace", side_effect=OSError("injected replace failure")):
                with self.assertRaises(OSError):
                    editor._write_dropin("wirtelprimpf.timer", "[Timer]\nOnUnitActiveSec=60min\n")

            self.assertEqual(dropin.read_bytes(), original)
            self.assertEqual(list(dropin.parent.glob(".*.part")), [])

    def test_generator_dropin_does_not_clear_private_runtime_environment(self):
        source = SETTINGS_LOGO_PATH.read_text(encoding="utf-8")

        self.assertNotIn('"Environment=",', source)


if __name__ == "__main__":
    unittest.main()
