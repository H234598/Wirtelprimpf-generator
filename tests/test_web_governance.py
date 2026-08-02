"""Contract tests for revision-baseline governance."""

from __future__ import annotations

import json
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


class WebGovernanceValidationTests(unittest.TestCase):
    """Each test names one invalid baseline state the validator must reject."""

    def copied_root(self) -> tempfile.TemporaryDirectory[str]:
        temporary = tempfile.TemporaryDirectory()
        target = Path(temporary.name)
        for relative in (PLAN, BASELINE, REVISIONS):
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


if __name__ == "__main__":
    unittest.main()
