#!/usr/bin/env python3
"""Regression tests for the generator's Git object-store fallback."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = ROOT / "Sourcecode" / "wirtelprimpf_generator.py"


def load_generator():
    spec = importlib.util.spec_from_file_location("wirtelprimpf_generator_git_fallback", GENERATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load generator module from {GENERATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class GitObjectFallbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generator = load_generator()

    def test_detects_git_object_permission_failure(self):
        exc = RuntimeError(
            "Command failed: git commit: error: insufficient permission for adding an object "
            "to repository database .git/objects\nerror: Error building trees"
        )

        self.assertTrue(self.generator._git_object_permission_failure(exc))

    def test_registers_fallback_object_store_idempotently(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "repo"
            objects = repo / ".git" / "objects"
            (objects / "info").mkdir(parents=True)

            first = self.generator._git_object_fallback_env(repo)
            second = self.generator._git_object_fallback_env(repo)

            fallback = repo / ".git" / self.generator.GIT_FALLBACK_OBJECT_DIR
            alternates = objects / "info" / "alternates"
            lines = alternates.read_text(encoding="utf-8").splitlines()

        self.assertEqual(first, second)
        self.assertEqual(lines, [str(fallback.resolve())])
        self.assertEqual(first["GIT_OBJECT_DIRECTORY"], str(fallback.resolve()))
        self.assertIn(str(objects.resolve()), first["GIT_ALTERNATE_OBJECT_DIRECTORIES"])


if __name__ == "__main__":
    unittest.main()
