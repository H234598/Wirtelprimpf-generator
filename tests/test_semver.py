#!/usr/bin/env python3
"""Focused SemVer regression tests for the Wirtelprimpf generator."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import tomllib
import unittest
from importlib import resources
from pathlib import Path

from wirtelprimpf_platform import __version__ as platform_version


ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = ROOT / "Sourcecode" / "wirtelprimpf_generator.py"


def load_generator():
    spec = importlib.util.spec_from_file_location("wirtelprimpf_generator_under_test", GENERATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load generator module from {GENERATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class SemVerStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generator = load_generator()

    def read_state(self, payload):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "publish_state.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return self.generator.read_publish_state(path)

    def version_for(self, state, patch_count=None):
        return self.generator.resolve_runtime_version(
            patch_count=state.patch_count if patch_count is None else patch_count,
            semver_base_patch_count=state.semver_base_patch_count,
        )

    def test_legacy_state_without_semver_base_preserves_existing_patch_count(self):
        state = self.read_state({"patch_count": 65, "minor_push_count": 0})

        self.assertEqual(state.semver_base, self.generator.VERSION)
        self.assertEqual(state.semver_base_patch_count, 0)
        self.assertEqual(self.version_for(state), "1.0.65")

    def test_matching_semver_base_uses_stored_patch_offset(self):
        state = self.read_state(
            {
                "patch_count": 65,
                "publish_push_count": 0,
                "semver_base": self.generator.VERSION,
                "semver_base_patch_count": 60,
            }
        )

        self.assertEqual(self.version_for(state), "1.0.5")
        self.assertEqual(self.version_for(state, patch_count=66), "1.0.6")

    def test_changed_semver_base_resets_patch_offset(self):
        state = self.read_state(
            {
                "patch_count": 65,
                "publish_push_count": 0,
                "semver_base": "0.5.0",
                "semver_base_patch_count": 0,
            }
        )

        self.assertEqual(state.semver_base, self.generator.VERSION)
        self.assertEqual(state.semver_base_patch_count, 65)
        self.assertEqual(self.version_for(state), "1.0.0")
        self.assertEqual(self.version_for(state, patch_count=66), "1.0.1")


class PackagingVersionTests(unittest.TestCase):
    def test_admin_static_assets_are_available_as_package_resources(self) -> None:
        static = resources.files("wirtelprimpf_platform").joinpath("static")
        for name in ("admin.html", "admin.css", "admin.mjs"):
            with self.subTest(name=name):
                asset = static.joinpath(name)
                self.assertTrue(asset.is_file())
                self.assertGreater(len(asset.read_bytes()), 0)

    def test_transactional_release_versions_and_installer_gate(self) -> None:
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        metadata = json.loads(
            (ROOT / "files/wirtelprimfgenerator@H234598/metadata.json").read_text(
                encoding="utf-8"
            )
        )
        installer = (ROOT / "scripts/install-local.sh").read_text(encoding="utf-8")
        self.assertEqual(project["project"]["version"], "1.1.0")
        self.assertEqual(platform_version, "1.1.0")
        self.assertEqual(metadata["version"], "0.9.0")
        self.assertEqual(metadata["comments"], "Version: 0.9.0")
        gate = installer.index(
            'if [[ ! -f "${SETTINGS_CLI}" || ! -x "${SETTINGS_CLI}" || -L "${SETTINGS_CLI}" ]]'
        )
        replace = installer.index('rm -rf -- "${DEST}"')
        self.assertLess(gate, replace)

    def test_installer_prepares_only_private_transaction_directories(self) -> None:
        installer = (ROOT / "scripts/install-local.sh").read_text(encoding="utf-8")
        self.assertIn(
            'install -d -m0700 -- "${HOME}/.config/wirtelprimpf" "${HOME}/.config/cloudflare"',
            installer,
        )
        self.assertIn(
            'install -d -m0700 -- "${HOME}/.config/systemd/user/wirtelprimpf.timer.d"',
            installer,
        )
        self.assertNotIn('install -d -m0700 -- "${HOME}/.config"', installer)

    def test_uninstaller_and_ci_preserve_state_and_verify_settings_entrypoint(self) -> None:
        uninstaller = (ROOT / "scripts/uninstall-local.sh").read_text(encoding="utf-8")
        workflow = (ROOT / ".github/workflows/check.yml").read_text(encoding="utf-8")
        for retained in (
            ".venv/bin/wirtelprimpf-settings",
            ".config/wirtelprimpf/openai.env",
            ".config/cloudflare/api-token.env",
            ".config/wirtelprimpf/settings-state.json",
            ".config/systemd/user/wirtelprimpf.timer.d/override.conf",
        ):
            with self.subTest(retained=retained):
                self.assertIn(retained, uninstaller)
        self.assertIn("- name: Verify transactional settings entrypoint", workflow)
        self.assertIn("run: wirtelprimpf-settings --help >/dev/null", workflow)

    def test_transactional_operational_contract_is_documented(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        applet_readme = (
            ROOT / "files/wirtelprimfgenerator@H234598/README.md"
        ).read_text(encoding="utf-8")
        for required in (
            "wirtelprimpf-settings snapshot",
            "wirtelprimpf-settings apply",
            "~/.config/cloudflare/api-token.env",
            "gpt-image-2",
            "gpt-5.5",
            "/api/status",
            "2 Sekunden",
            "5 Sekunden",
            "250 ms",
            "30 Sekunden",
            "settings-state.json",
            "deploy-backups",
            "Cloudflare-Redirects/DNS",
            "Cinnamon-Upstream-Fix",
        ):
            with self.subTest(document="root", required=required):
                self.assertIn(required, readme)
        for required in (
            "Version `0.9.0`",
            "wirtelprimpf-settings",
            "250 ms",
            "30 Sekunden",
            "gpt-image-2",
            "gpt-5.5",
            "Externen Wert übernehmen",
        ):
            with self.subTest(document="applet", required=required):
                self.assertIn(required, applet_readme)


if __name__ == "__main__":
    unittest.main()
