#!/usr/bin/env python3
"""Static checks for Cinnamon settings that should not require GTK."""

from __future__ import annotations

import ast
import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path


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
    pass


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


if __name__ == "__main__":
    unittest.main()
