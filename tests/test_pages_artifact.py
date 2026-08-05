#!/usr/bin/env python3
"""Root-level compatibility entrypoint for the Pages artifact contract."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
_SPEC = importlib.util.spec_from_file_location(
    "wirtelprimpf_platform_pages_artifact_tests",
    ROOT / "tests" / "platform" / "test_pages_artifact.py",
)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError("cannot load platform Pages artifact tests")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
PagesArtifactTests = _MODULE.PagesArtifactTests


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(PagesArtifactTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
