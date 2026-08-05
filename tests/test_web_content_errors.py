"""Contract tests for content error codes and hash-bound exceptions."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.web_content_errors import ContentErrorRegistryError, ERROR_CATALOG, load_exception_registry, validate_exception_registry
from scripts.web_content_model import build_content_model


class WebContentErrorTests(unittest.TestCase):
    def test_persistent_fixture_matrix_covers_every_pairing_error_code(self) -> None:
        fixture_root = Path(__file__).resolve().parent / "fixtures" / "web-content"
        fixture_names = (
            "case-collision",
            "ambiguous-heading",
            "timestamp-collision",
            "timestamp-missing",
            "orphan-prompt",
            "orphan-story",
            "orphan-sidecar",
        )
        observed: set[str] = set()
        for name in fixture_names:
            report = build_content_model(fixture_root / name)
            observed.update(item["code"] for item in report["errors"])
            observed.update(item["code"] for item in report["warnings"])

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            os.symlink("missing-target.png", root / "escape.png")
            report = build_content_model(root)
        observed.update(item["code"] for item in report["errors"])
        observed.update(item["code"] for item in report["warnings"])
        self.assertEqual(observed, set(ERROR_CATALOG))

    def test_repository_registry_is_empty_and_catalog_has_explicit_severities(self) -> None:
        path = Path(__file__).resolve().parents[1] / "config/web-content-exceptions.json"
        self.assertEqual(load_exception_registry(path), [])
        self.assertEqual(ERROR_CATALOG["PAIR_CASE_COLLISION"]["severity"], "block")
        self.assertEqual(ERROR_CATALOG["PAIR_ORPHAN_STORY"]["severity"], "warn")

    def test_unknown_codes_paths_hashes_and_severity_mismatches_fail_closed(self) -> None:
        base = {
            "schema_version": "1.0.0",
            "exceptions": [{
                "code": "PAIR_CASE_COLLISION",
                "path": "Wirtelprimpf/file.png",
                "sha256": "a" * 64,
                "reason": "temporary source exception",
                "expires_on": "2099-01-01",
                "severity": "block",
            }],
        }
        validate_exception_registry(base)
        for mutation in (
            {"code": "UNKNOWN"},
            {"path": "../escape.png"},
            {"sha256": "bad"},
            {"severity": "warn"},
        ):
            with self.subTest(mutation=mutation):
                invalid = {**base, "exceptions": [{**base["exceptions"][0], **mutation}]}
                with self.assertRaises(ContentErrorRegistryError):
                    validate_exception_registry(invalid)


if __name__ == "__main__":
    unittest.main()
