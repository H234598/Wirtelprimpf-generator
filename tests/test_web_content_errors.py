"""Contract tests for content error codes and hash-bound exceptions."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.web_content_errors import ContentErrorRegistryError, ERROR_CATALOG, load_exception_registry, validate_exception_registry


class WebContentErrorTests(unittest.TestCase):
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
