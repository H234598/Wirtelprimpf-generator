#!/usr/bin/env python3
"""Static checks for Cinnamon settings that should not require GTK."""

from __future__ import annotations

import ast
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


class SettingsSchemaTests(unittest.TestCase):
    def test_image_model_dropdown_uses_official_image_models(self):
        self.assertEqual(extract_constant_tuple(SETTINGS_LOGO_PATH, "IMAGE_MODEL_CHOICES"), OFFICIAL_IMAGE_MODELS)


if __name__ == "__main__":
    unittest.main()
