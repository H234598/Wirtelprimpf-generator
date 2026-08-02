"""Contract tests for revision-baseline governance."""

from __future__ import annotations

import json
import hashlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_web_governance.py"
PLAN = Path("docs/plans/WIRTELPRIMPF-WEBSEITE-IMPLEMENTIERUNGSPLAN.md")
BASELINE = Path("docs/REVISIONSBASELINE.md")
REVISIONS = Path("config/reference-revisions.json")
STATUS = Path("config/web-plan-status.json")
REQUIREMENTS = Path("config/web-requirements.json")
DECISIONS = Path("config/architecture-decisions.json")
REQUIREMENTS_DOC = Path("docs/requirements/WIRTELPRIMPF-WEBSEITE.md")
ADR_DOC = Path("docs/adr/README.md")
PROVENANCE = Path("PROVENANCE.md")


class WebGovernanceValidationTests(unittest.TestCase):
    """Each test names one invalid baseline state the validator must reject."""

    def copied_root(self) -> tempfile.TemporaryDirectory[str]:
        temporary = tempfile.TemporaryDirectory()
        target = Path(temporary.name)
        for relative in (PLAN, BASELINE, REVISIONS, STATUS, REQUIREMENTS, DECISIONS, REQUIREMENTS_DOC, ADR_DOC, PROVENANCE):
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

    def read_revisions(self, root: Path) -> dict:
        return json.loads((root / REVISIONS).read_text(encoding="utf-8"))

    def write_revisions(self, root: Path, value: dict) -> None:
        (root / REVISIONS).write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def read_json(self, root: Path, relative: Path) -> dict:
        return json.loads((root / relative).read_text(encoding="utf-8"))

    def write_json(self, root: Path, relative: Path, value: dict) -> None:
        (root / relative).write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def assert_rejected(self, result: subprocess.CompletedProcess[str], message: str) -> None:
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(message, result.stderr)

    def test_accepts_canonical_revision_baseline(self) -> None:
        """Rejects regressions that make frozen and observed evidence inconsistent."""
        result = self.validate(ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_duplicate_repository(self) -> None:
        """Rejects a second frozen record for one repository."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            revisions = self.read_revisions(root)
            revisions["repositories"].append(revisions["repositories"][0])
            self.write_revisions(root, revisions)
            result = self.validate(root)
        self.assert_rejected(result, "repository IDs")

    def test_rejects_missing_repository(self) -> None:
        """Rejects baseline that silently drops a required reference repository."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            revisions = self.read_revisions(root)
            revisions["repositories"].pop()
            self.write_revisions(root, revisions)
            result = self.validate(root)
        self.assert_rejected(result, "repository IDs")

    def test_rejects_short_frozen_sha(self) -> None:
        """Rejects abbreviated immutable frozen revision."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            revisions = self.read_revisions(root)
            revisions["repositories"][0]["frozen_sha"] = "274b25c"
            self.write_revisions(root, revisions)
            result = self.validate(root)
        self.assert_rejected(result, "frozen SHA")

    def test_rejects_false_no_drift(self) -> None:
        """Rejects generator state claiming no drift despite different observed SHA."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            revisions = self.read_revisions(root)
            revisions["repositories"][0]["drift_classification"] = "no-drift"
            self.write_revisions(root, revisions)
            result = self.validate(root)
        self.assert_rejected(result, "drift classification")

    def test_rejects_checked_external_repository_without_sha(self) -> None:
        """Rejects invented checked state without observed revision evidence."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            revisions = self.read_revisions(root)
            revisions["repositories"][1]["observed"] = {"sha": None, "source": "local-git", "status": "checked"}
            self.write_revisions(root, revisions)
            result = self.validate(root)
        self.assert_rejected(result, "observed state")

    def test_rejects_missing_phase(self) -> None:
        """Rejects loss of P12 rollout phase coverage."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            revisions = self.read_revisions(root)
            revisions["phase_ids"].pop()
            self.write_revisions(root, revisions)
            result = self.validate(root)
        self.assert_rejected(result, "phase IDs")

    def test_rejects_missing_current_adr(self) -> None:
        """Rejects loss of current ADR-WEB-015 coverage."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            revisions = self.read_revisions(root)
            revisions["adr_ids"]["current"].pop()
            self.write_revisions(root, revisions)
            result = self.validate(root)
        self.assert_rejected(result, "current ADR IDs")

    def test_rejects_missing_manual_boundary(self) -> None:
        """Rejects omission of an operator-owned external verification boundary."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            revisions = self.read_revisions(root)
            revisions["manual_verification_boundaries"].pop()
            self.write_revisions(root, revisions)
            result = self.validate(root)
        self.assert_rejected(result, "manual verification boundaries")

    def test_rejects_plan_digest_mismatch(self) -> None:
        """Rejects baseline when canonical plan bytes changed after freeze."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            (root / PLAN).write_text("mutated\n", encoding="utf-8")
            result = self.validate(root)
        self.assert_rejected(result, "plan digest")

    def test_rejects_baseline_claiming_unverified_remote_state(self) -> None:
        """Rejects human prose that upgrades local evidence to remote verification."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            baseline = root / BASELINE
            baseline.write_text(
                baseline.read_text(encoding="utf-8") + "\nRemote state verified.\n",
                encoding="utf-8",
            )
            result = self.validate(root)
        self.assert_rejected(result, "baseline doc")

    def test_rejects_unhashable_repository_id_without_traceback(self) -> None:
        """Rejects malformed repository identifiers through controlled stderr."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            revisions = self.read_revisions(root)
            revisions["repositories"][0]["id"] = []
            self.write_revisions(root, revisions)
            result = self.validate(root)
        self.assert_rejected(result, "repository IDs")
        self.assertNotIn("Traceback", result.stderr)

    def test_rejects_missing_requirement(self) -> None:
        """Rejects requirement register that silently loses one canonical ID."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            requirements = self.read_json(root, REQUIREMENTS)
            requirements["requirements"].pop()
            self.write_json(root, REQUIREMENTS, requirements)
            result = self.validate(root)
        self.assert_rejected(result, "requirement IDs")

    def test_rejects_unknown_requirement_package(self) -> None:
        """Rejects requirement assigned outside status register."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            requirements = self.read_json(root, REQUIREMENTS)
            requirements["requirements"][0]["packages"] = ["WEB-P99-99"]
            self.write_json(root, REQUIREMENTS, requirements)
            result = self.validate(root)
        self.assert_rejected(result, "requirement packages")

    def test_rejects_empty_requirement_verification(self) -> None:
        """Rejects requirement with no executable or test trace."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            requirements = self.read_json(root, REQUIREMENTS)
            requirements["requirements"][0]["verification"] = []
            self.write_json(root, REQUIREMENTS, requirements)
            result = self.validate(root)
        self.assert_rejected(result, "requirement verification")

    def test_rejects_requirement_package_mapping_drift(self) -> None:
        """Rejects requirement mapped to a package absent from plan section."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            requirements = self.read_json(root, REQUIREMENTS)
            requirements["requirements"][0]["packages"].append("WEB-P00-02")
            self.write_json(root, REQUIREMENTS, requirements)
            result = self.validate(root)
        self.assert_rejected(result, "requirement package mapping")

    def test_rejects_altered_current_adr(self) -> None:
        """Rejects current ADR decision text divergent from v2 authority."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            decisions = self.read_json(root, DECISIONS)
            decisions["decisions"][0]["decision"] = "mutated"
            self.write_json(root, DECISIONS, decisions)
            result = self.validate(root)
        self.assert_rejected(result, "current ADR rows")

    def test_rejects_duplicate_adr(self) -> None:
        """Rejects duplicate current ADR identifier."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            decisions = self.read_json(root, DECISIONS)
            decisions["decisions"].append(decisions["decisions"][0])
            self.write_json(root, DECISIONS, decisions)
            result = self.validate(root)
        self.assert_rejected(result, "current ADR IDs")

    def test_rejects_requirement_document_mismatch(self) -> None:
        """Rejects readable requirements projection with untracked edit."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            (root / REQUIREMENTS_DOC).write_text("mutated\n", encoding="utf-8")
            result = self.validate(root)
        self.assert_rejected(result, "requirements doc")

    def test_rejects_adr_document_mismatch(self) -> None:
        """Rejects readable ADR projection with untracked edit."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            (root / ADR_DOC).write_text("mutated\n", encoding="utf-8")
            result = self.validate(root)
        self.assert_rejected(result, "ADR doc")

    def test_rejects_missing_or_moving_provenance_sha(self) -> None:
        """Rejects provenance that replaces immutable reference with branch name."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            provenance = root / PROVENANCE
            provenance.write_text(provenance.read_text(encoding="utf-8").replace("274b25c9e1f9ea97d3b060997ed5c425d2b30e9f", "main"), encoding="utf-8")
            result = self.validate(root)
        self.assert_rejected(result, "provenance")

    def test_rejects_unhashable_requirement_package_without_traceback(self) -> None:
        """Rejects malformed nested package list through controlled stderr."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            requirements = self.read_json(root, REQUIREMENTS)
            requirements["requirements"][0]["packages"] = [[]]
            self.write_json(root, REQUIREMENTS, requirements)
            result = self.validate(root)
        self.assert_rejected(result, "requirement packages")
        self.assertNotIn("Traceback", result.stderr)

    def test_rejects_manual_verification_not_derived_from_p11_04_source(self) -> None:
        """Rejects P11-04 verification when plan no longer supplies its manual check."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            plan = root / PLAN
            plan.write_text(plan.read_text(encoding="utf-8").replace("manuelle Checkliste plus HTTP-Smoke", "manuelle Domainprüfung"), encoding="utf-8")
            digest = hashlib.sha256(plan.read_bytes()).hexdigest()
            revisions = self.read_revisions(root)
            revisions["plan_sha256"] = digest
            self.write_revisions(root, revisions)
            status = self.read_json(root, STATUS)
            status["canonical_plan"]["sha256"] = digest
            self.write_json(root, STATUS, status)
            for path in (REQUIREMENTS, DECISIONS):
                value = self.read_json(root, path)
                value["plan_sha256"] = digest
                self.write_json(root, path, value)
            for path in (REQUIREMENTS_DOC, ADR_DOC):
                document = root / path
                document.write_text(document.read_text(encoding="utf-8").replace("b4b3427e80cabff59e82f9aa9be52978de1d930ea63e06b2433045b8c0dc38fe", digest), encoding="utf-8")
            result = self.validate(root)
        self.assert_rejected(result, "requirement verification")

    def test_ignores_adr_looking_row_outside_current_chapter(self) -> None:
        """Uses only chapter 20 rather than an ADR-looking historical row."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            plan = root / PLAN
            plan.write_text(plan.read_text(encoding="utf-8").replace("## 20. Aktive Architekturentscheidungen", "| ADR-WEB-001 | forged | forged | forged |\n\n## 20. Aktive Architekturentscheidungen"), encoding="utf-8")
            digest = hashlib.sha256(plan.read_bytes()).hexdigest()
            revisions = self.read_revisions(root)
            revisions["plan_sha256"] = digest
            self.write_revisions(root, revisions)
            status = self.read_json(root, STATUS)
            status["canonical_plan"]["sha256"] = digest
            self.write_json(root, STATUS, status)
            for path in (REQUIREMENTS, DECISIONS):
                value = self.read_json(root, path)
                value["plan_sha256"] = digest
                self.write_json(root, path, value)
            for path in (REQUIREMENTS_DOC, ADR_DOC):
                document = root / path
                document.write_text(document.read_text(encoding="utf-8").replace("b4b3427e80cabff59e82f9aa9be52978de1d930ea63e06b2433045b8c0dc38fe", digest), encoding="utf-8")
            result = self.validate(root)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
