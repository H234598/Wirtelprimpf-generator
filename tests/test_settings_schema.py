#!/usr/bin/env python3
"""Static packaging checks for Cinnamon settings that do not require GTK."""

from __future__ import annotations

import ast
import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APPLET_ROOT = ROOT / "files" / "wirtelprimfgenerator@H234598"
SETTINGS_LOGO_PATH = APPLET_ROOT / "SettingsLogo.py"
SYNC_PATH = APPLET_ROOT / "settings_sync.py"


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
                self.assertIn(key, source)

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


if __name__ == "__main__":
    unittest.main()
