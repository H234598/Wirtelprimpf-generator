"""Contract tests for canonical web-plan governance."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_web_plan.py"
PLAN = Path("docs/plans/WIRTELPRIMPF-WEBSEITE-IMPLEMENTIERUNGSPLAN.md")
STATUS = Path("config/web-plan-status.json")
SUPERSESSION = Path("config/web-plan-supersession.json")
LEGACY_WEB_PLAN = {
    "archive_destination": "Done/Wirtelprimpf-Webseite-Implementierungsplan.md",
    "document_id": "WIRTEL-WEB-PLAN-001",
    "original_sha256": "97ef89d0e80e9efc6c2573e644ec51bcb7ec122feadc6b057534298a52b7a7c6",
    "section_mappings": [
        {
            "chapters": "47-77",
            "replacement": "v2.0.0 chapters 0-28 and approved generator/rollout plans",
            "source_sha256": None,
        },
        {
            "chapters": "78-79",
            "replacement": "Wirtelprimpf Cloudflare Alias- und Wildcard-Rollout",
            "source_sha256": "ea3473941129702ca5245d62858cce659b94c9c228344ecf04a8ab2e5ddd3828",
        },
        {
            "chapters": "80-80.53",
            "replacement": "v2.0.0 chapters 0-28 and approved generator/rollout plans",
            "source_sha256": None,
        },
    ],
    "status": "superseded",
}


class WebPlanValidationTests(unittest.TestCase):
    """Each test names one invalid governance state the validator must reject."""

    def copied_root(self) -> tempfile.TemporaryDirectory[str]:
        temporary = tempfile.TemporaryDirectory()
        target = Path(temporary.name)
        for relative in (PLAN, STATUS, SUPERSESSION):
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, destination)
        return temporary

    def validate(self, root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VALIDATOR), "--root", str(root)],
            text=True,
            capture_output=True,
            check=False,
        )

    def read_json(self, root: Path, relative: Path) -> dict:
        return json.loads((root / relative).read_text(encoding="utf-8"))

    def write_json(self, root: Path, relative: Path, value: dict) -> None:
        (root / relative).write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def test_accepts_canonical_repository(self) -> None:
        """Rejects regressions that make canonical artifacts mutually inconsistent."""
        result = self.validate(ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_plan_digest_mismatch(self) -> None:
        """Rejects altered plan even when frozen digest remains unchanged."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            (root / PLAN).write_text("mutated\n", encoding="utf-8")
            result = self.validate(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("plan digest", result.stderr)

    def test_rejects_missing_package(self) -> None:
        """Rejects status register that silently drops historical package."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            status = self.read_json(root, STATUS)
            status["packages"].pop()
            self.write_json(root, STATUS, status)
            result = self.validate(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("package IDs", result.stderr)

    def test_rejects_duplicate_requirement(self) -> None:
        """Rejects requirement register losing unique v1 traceability."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            status = self.read_json(root, STATUS)
            status["requirements"][-1] = status["requirements"][0]
            self.write_json(root, STATUS, status)
            result = self.validate(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requirement IDs", result.stderr)

    def test_rejects_boolean_schema_version(self) -> None:
        """Rejects JSON booleans masquerading as integer schema versions."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            status = self.read_json(root, STATUS)
            status["schema_version"] = True
            self.write_json(root, STATUS, status)
            result = self.validate(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("status schema version", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_rejects_top_level_duplicate_json_keys(self) -> None:
        """Rejects duplicate top-level members in every plan JSON register."""
        for relative in (STATUS, SUPERSESSION):
            with self.subTest(relative=relative), self.copied_root() as temporary:
                root = Path(temporary)
                path = root / relative
                content = path.read_text(encoding="utf-8")
                version = re.search(r'^  "schema_version": (\d+)', content, re.MULTILINE)
                self.assertIsNotNone(version)
                path.write_text(
                    content.replace(
                        version.group(0),
                        f'  "schema_version": 999,\n{version.group(0)}',
                        1,
                    ),
                    encoding="utf-8",
                )
                result = self.validate(root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("duplicate JSON key", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_rejects_nested_duplicate_json_keys(self) -> None:
        """Rejects duplicate nested members in every plan JSON register."""
        mutations = (
            (
                STATUS,
                '"version": "2.0.0"',
                '"version": "0.0.0",\n    "version": "2.0.0"',
            ),
            (
                SUPERSESSION,
                '"solution_path": "abgelöst"',
                '"solution_path": "umgesetzt", "solution_path": "abgelöst"',
            ),
        )
        for relative, original, mutated in mutations:
            with self.subTest(relative=relative), self.copied_root() as temporary:
                root = Path(temporary)
                path = root / relative
                content = path.read_text(encoding="utf-8")
                self.assertIn(original, content)
                path.write_text(content.replace(original, mutated, 1), encoding="utf-8")
                result = self.validate(root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("duplicate JSON key", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_rejects_invalid_utf8_status_without_traceback(self) -> None:
        """Rejects non-UTF-8 status bytes through controlled stderr."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            (root / STATUS).write_bytes(b'{"schema_version": "\xff"}')
            result = self.validate(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"malformed {STATUS}", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_rejects_invalid_utf8_supersession_without_traceback(self) -> None:
        """Rejects non-UTF-8 supersession bytes through controlled stderr."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            (root / SUPERSESSION).write_bytes(b'{"schema_version": "\xff"}')
            result = self.validate(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"malformed {SUPERSESSION}", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_rejects_unhashable_package_id_without_traceback(self) -> None:
        """Rejects malformed package identifiers through controlled stderr."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            status = self.read_json(root, STATUS)
            status["packages"][0]["id"] = []
            self.write_json(root, STATUS, status)
            result = self.validate(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("package IDs", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_rejects_unhashable_requirement_without_traceback(self) -> None:
        """Rejects malformed requirement identifiers through controlled stderr."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            status = self.read_json(root, STATUS)
            status["requirements"][0] = []
            self.write_json(root, STATUS, status)
            result = self.validate(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requirement IDs", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_rejects_invalid_status(self) -> None:
        """Rejects package state outside controlled status vocabulary."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            status = self.read_json(root, STATUS)
            status["packages"][0]["status"] = "abgelöst"
            self.write_json(root, STATUS, status)
            result = self.validate(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid status", result.stderr)

    def test_rejects_short_archive_factory_pin(self) -> None:
        """Rejects abbreviated immutable archive Factory pins."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            status = self.read_json(root, STATUS)
            status["archive_factory_pin"] = "b00d824"
            self.write_json(root, STATUS, status)
            result = self.validate(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Factory pin", result.stderr)

    def test_rejects_short_frozen_repository_sha(self) -> None:
        """Rejects abbreviated repository Freeze SHA despite refreshed digest."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            plan = root / PLAN
            plan.write_text(
                plan.read_text(encoding="utf-8").replace(
                    "| `H234598/Wirtelprimpf-generator` | Generator, Plattform, Applet, Admin, Seitenfabrik, Hub | `main` | `274b25c9e1f9ea97d3b060997ed5c425d2b30e9f`",
                    "| `H234598/Wirtelprimpf-generator` | Generator, Plattform, Applet, Admin, Seitenfabrik, Hub | `main` | `274b25c`",
                    1,
                ),
                encoding="utf-8",
            )
            status = self.read_json(root, STATUS)
            status["canonical_plan"]["sha256"] = hashlib.sha256(plan.read_bytes()).hexdigest()
            self.write_json(root, STATUS, status)
            result = self.validate(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("frozen repository SHA", result.stderr)

    def test_rejects_duplicate_plan_status_row(self) -> None:
        """Rejects extra historical status row even after digest refresh."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            plan = root / PLAN
            row = next(
                line for line in plan.read_text(encoding="utf-8").splitlines()
                if line.startswith("| `WEB-P00-01`")
            )
            plan.write_text(
                plan.read_text(encoding="utf-8").replace(row, row + "\n" + row, 1),
                encoding="utf-8",
            )
            status = self.read_json(root, STATUS)
            status["canonical_plan"]["sha256"] = hashlib.sha256(plan.read_bytes()).hexdigest()
            self.write_json(root, STATUS, status)
            result = self.validate(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("plan status rows", result.stderr)

    def test_rejects_duplicate_plan_requirement(self) -> None:
        """Rejects extra historical requirement ID even after digest refresh."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            plan = root / PLAN
            plan.write_text(plan.read_text(encoding="utf-8") + "\nWEB-REQ-001\n", encoding="utf-8")
            status = self.read_json(root, STATUS)
            status["canonical_plan"]["sha256"] = hashlib.sha256(plan.read_bytes()).hexdigest()
            self.write_json(root, STATUS, status)
            result = self.validate(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("plan requirement IDs", result.stderr)

    def test_rejects_implemented_old_p00_pr(self) -> None:
        """Rejects false implementation claim for superseded P00 PR #1."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            supersession = self.read_json(root, SUPERSESSION)
            supersession["old_p00_pr"]["solution_path"] = "umgesetzt"
            self.write_json(root, SUPERSESSION, supersession)
            result = self.validate(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("old P00", result.stderr)

    def test_requires_complete_legacy_web_plan_supersession(self) -> None:
        """Accepts only the hash-bound three-way mapping needed to archive the legacy plan."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            supersession = self.read_json(root, SUPERSESSION)
            supersession["schema_version"] = 2
            supersession["legacy_web_plan"] = copy.deepcopy(LEGACY_WEB_PLAN)
            self.write_json(root, SUPERSESSION, supersession)
            result = self.validate(root)
        self.assertEqual(result.returncode, 0, result.stderr)

        mutations = (
            ("original_sha256", "0" * 64),
            ("status", "pending"),
            ("archive_destination", "Baupläne!/legacy.md"),
        )
        for field, value in mutations:
            with self.subTest(field=field), self.copied_root() as temporary:
                root = Path(temporary)
                supersession = self.read_json(root, SUPERSESSION)
                supersession["schema_version"] = 2
                supersession["legacy_web_plan"] = copy.deepcopy(LEGACY_WEB_PLAN)
                supersession["legacy_web_plan"][field] = value
                self.write_json(root, SUPERSESSION, supersession)
                result = self.validate(root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("legacy web plan supersession", result.stderr)

    def test_rejects_merged_pr4_claim(self) -> None:
        """Rejects fabricated GitHub merge evidence for PR #4."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            supersession = self.read_json(root, SUPERSESSION)
            supersession["generator_pr_4"]["github_pr_merged"] = True
            self.write_json(root, SUPERSESSION, supersession)
            result = self.validate(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PR #4", result.stderr)


if __name__ == "__main__":
    unittest.main()
