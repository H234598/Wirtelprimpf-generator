#!/usr/bin/env python3
"""Focused SemVer regression tests for the Wirtelprimpf generator."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


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
        self.assertEqual(self.version_for(state), "0.6.65")

    def test_matching_semver_base_uses_stored_patch_offset(self):
        state = self.read_state(
            {
                "patch_count": 65,
                "publish_push_count": 0,
                "semver_base": self.generator.VERSION,
                "semver_base_patch_count": 60,
            }
        )

        self.assertEqual(self.version_for(state), "0.6.5")
        self.assertEqual(self.version_for(state, patch_count=66), "0.6.6")

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
        self.assertEqual(self.version_for(state), "0.6.0")
        self.assertEqual(self.version_for(state, patch_count=66), "0.6.1")


if __name__ == "__main__":
    unittest.main()
