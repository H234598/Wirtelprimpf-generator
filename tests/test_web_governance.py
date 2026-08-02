"""Contract tests for revision-baseline governance."""

from __future__ import annotations

import json
import hashlib
import re
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
MAKEFILE = Path("Makefile")
WORKFLOW = Path(".github/workflows/check.yml")
README = Path("README.md")
GITIGNORE = Path(".gitignore")

PRESERVED_CHECK_COMMANDS = (
    "$(PYTHON) -m json.tool files/$(UUID)/metadata.json >/dev/null",
    "$(PYTHON) -m json.tool files/$(UUID)/settings-schema.json >/dev/null",
    "$(PYTHON) -m py_compile Sourcecode/wirtelprimpf_generator.py",
    "$(PYTHON) -m py_compile files/$(UUID)/helper.py files/$(UUID)/SettingsLogo.py files/$(UUID)/settings_sync.py",
    "$(PYTHON) -m py_compile files/$(UUID)/story_directives_core.py files/$(UUID)/StoryDirectives.py",
    "node --check files/$(UUID)/applet.js",
    "node tests/test_applet_runtime.js",
    "node --test tests/test_admin_ui.mjs",
    "$(PYTHON) -m unittest tests.test_semver",
    "$(PYTHON) -m unittest tests.test_git_object_fallback",
    "$(PYTHON) -m unittest tests.test_release_publication",
    "$(PYTHON) -m unittest tests.test_helper_env",
    "$(PYTHON) -m unittest tests.test_applet_settings_sync",
    "$(PYTHON) -m unittest tests.test_settings_schema",
    "$(PYTHON) -m unittest tests.test_story_directives",
    "$(PYTHON) -m unittest tests.test_rollout_plan_contract",
    "@test -f files/$(UUID)/assets/settings-header-logo.png",
    "@test -f files/$(UUID)/assets/settings-footer-logo.png",
    "@test -f files/$(UUID)/assets/settings-generator-atelier.png",
    "@test -f files/$(UUID)/assets/settings-generator-machine.png",
    "@test -f files/$(UUID)/assets/settings-about-story.png",
    "@test -f files/$(UUID)/assets/settings-about-book.png",
    "@test -f files/$(UUID)/assets/panel-icon.png",
    "@test -f files/$(UUID)/assets/panel-icon-moon.png",
    "@test -f files/$(UUID)/assets/panel-icon-spark.png",
)

GOVERNANCE_CHECK_COMMANDS = (
    "$(PYTHON) -m py_compile scripts/validate_web_plan.py scripts/validate_web_governance.py",
    "$(PYTHON) -m unittest tests.test_web_plan",
    "$(PYTHON) tests/test_web_governance.py",
    "$(PYTHON) scripts/validate_web_plan.py --root .",
    "$(PYTHON) scripts/validate_web_governance.py --root .",
)


class WebGovernanceValidationTests(unittest.TestCase):
    """Each test names one invalid baseline state the validator must reject."""

    def copied_root(self) -> tempfile.TemporaryDirectory[str]:
        temporary = tempfile.TemporaryDirectory()
        target = Path(temporary.name)
        for relative in (
            PLAN, BASELINE, REVISIONS, STATUS, REQUIREMENTS, DECISIONS,
            REQUIREMENTS_DOC, ADR_DOC, PROVENANCE, WORKFLOW, MAKEFILE,
            README, GITIGNORE,
        ):
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

    def test_rejects_mutated_provenance_projection(self) -> None:
        """Rejects changed rows, reuse modes, exclusions, or surrounding claims."""
        mutations = (
            ("Generator, Plattform, Applet, Admin, Seitenfabrik, Hub", "Generator"),
            ("| adapted |", "| concept |"),
            ("H234598/Cheatsheets |", "H234598/extra |"),
            ("Direkte Watchdog-/RKI-Logik aus `H234598/desinfect` wird nicht übernommen.", ""),
            ("MkDocs-/Material-Theme aus `H234598/Cheatsheets` wird nicht übernommen.", ""),
            ("Lizenzfreigaben werden hier nicht behauptet.", "Lizenzfreigaben liegen vor."),
        )
        for original, mutated in mutations:
            with self.subTest(original=original), self.copied_root() as temporary:
                root = Path(temporary)
                provenance = root / PROVENANCE
                content = provenance.read_text(encoding="utf-8")
                self.assertIn(original, content)
                provenance.write_text(content.replace(original, mutated, 1), encoding="utf-8")
                self.assert_rejected(self.validate(root), "provenance")

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

    def test_make_check_preserves_existing_gates_and_runs_governance(self) -> None:
        """Protects existing check order while adding every governance command."""
        commands = re.search(r"^check:\n(?P<commands>(?:\t.*\n)+)", MAKEFILE.read_text(encoding="utf-8"), re.MULTILINE)
        self.assertIsNotNone(commands)
        check_commands = commands.group("commands")
        positions = [check_commands.index(command) for command in PRESERVED_CHECK_COMMANDS]
        self.assertEqual(positions, sorted(positions))
        for command in GOVERNANCE_CHECK_COMMANDS:
            self.assertIn(command, check_commands)

    def test_applet_ci_checkout_includes_governance_inputs_without_deploy_scope(self) -> None:
        """Keeps governance inputs available in read-only, non-deploy applet CI."""
        workflow = (ROOT / WORKFLOW).read_text(encoding="utf-8")
        applet = re.search(r"^  applet:\n(?P<body>.*?)(?=^  [a-z]+:)", workflow, re.MULTILINE | re.DOTALL)
        self.assertIsNotNone(applet)
        applet_body = applet.group("body")
        sparse_checkout = re.search(r"sparse-checkout: \|\n(?P<paths>(?:            .*\n)+)", applet_body)
        self.assertIsNotNone(sparse_checkout)
        paths = sparse_checkout.group("paths")
        for required in ("config", "README.md", "PROVENANCE.md"):
            self.assertRegex(paths, rf"(?m)^            {re.escape(required)}$")
        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertNotRegex(workflow, r"(?i)\bwrite\b")
        self.assertNotRegex(workflow, r"(?i)\bdeploy(?:ment)?\b")

    def test_rejects_weakened_ci_safeguards(self) -> None:
        """Rejects mutations that weaken pinned, read-only repository checks."""
        mutations = (
            ("contents: read", "contents: write"),
            ("runs-on: ubuntu-24.04", "runs-on: ubuntu-22.04"),
            ("timeout-minutes: 20", "timeout-minutes: 19"),
            ("actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1", "actions/checkout@main"),
            ("actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1", "actions/setup-python@main"),
            ("actions/setup-node@820762786026740c76f36085b0efc47a31fe5020", "actions/setup-node@main"),
            ('python-version: "3.12"', 'python-version: "3.11"'),
            ('node-version: "24.13.1"', 'node-version: "24.13.0"'),
            ("persist-credentials: false", "persist-credentials: true"),
            ("lfs: false", "lfs: true"),
            ("  platform:\n", "  platform-removed:\n"),
            ("run: make check", "run: true"),
            ("run: wirtelprimpf-platform mapping 51", "run: true"),
            ("          npm test", "          true"),
            ("actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1", "actions/checkout@0000000000000000000000000000000000000000"),
            ("          npm test", "          # npm test"),
        )
        for original, mutated in mutations:
            with self.subTest(original=original), self.copied_root() as temporary:
                root = Path(temporary)
                workflow = root / WORKFLOW
                content = workflow.read_text(encoding="utf-8")
                self.assertIn(original, content)
                workflow.write_text(content.replace(original, mutated, 1), encoding="utf-8")
                self.assert_rejected(self.validate(root), "CI")

    def test_rejects_executable_ci_publication_command(self) -> None:
        """Rejects publication added to an executable run block."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            workflow = root / WORKFLOW
            content = workflow.read_text(encoding="utf-8")
            workflow.write_text(
                content.replace("          npm run check", "          npm run check\n          wrangler pages publish web/dist", 1),
                encoding="utf-8",
            )
            result = self.validate(root)
        self.assert_rejected(result, "CI")

    def test_readme_links_governance_authority_and_local_checks(self) -> None:
        """Makes governance artifacts and commands discoverable from README."""
        readme = (ROOT / README).read_text(encoding="utf-8")
        self.assertIn("## Web-Governance", readme)
        for link in (
            "docs/plans/WIRTELPRIMPF-WEBSEITE-IMPLEMENTIERUNGSPLAN.md",
            "docs/REVISIONSBASELINE.md",
            "docs/requirements/WIRTELPRIMPF-WEBSEITE.md",
            "docs/adr/README.md",
            "PROVENANCE.md",
        ):
            self.assertIn(f"]({link})", readme)
        for command in (
            "make check",
            "python3 scripts/validate_web_plan.py --root .",
            "python3 scripts/validate_web_governance.py --root .",
        ):
            self.assertIn(command, readme)

    def test_gitignore_ignores_governance_reports(self) -> None:
        """Keeps nested build reports outside version control through build/."""
        result = subprocess.run(
            ["git", "check-ignore", "-q", "build/reports/web-governance.json"],
            cwd=ROOT,
            check=False,
        )
        self.assertEqual(result.returncode, 0)

    def test_direct_validator_rejects_missing_make_gate(self) -> None:
        """Keeps Make integration in direct governance validation."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            makefile = root / MAKEFILE
            content = makefile.read_text(encoding="utf-8")
            makefile.write_text(content.replace("\t$(PYTHON) -m unittest tests.test_web_plan\n", "", 1), encoding="utf-8")
            result = self.validate(root)
        self.assert_rejected(result, "Make check")

    def test_direct_validator_rejects_missing_readme_command(self) -> None:
        """Keeps README integration in direct governance validation."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            readme = root / README
            content = readme.read_text(encoding="utf-8")
            readme.write_text(content.replace("python3 scripts/validate_web_plan.py --root .", "", 1), encoding="utf-8")
            result = self.validate(root)
        self.assert_rejected(result, "README governance")

    def test_direct_validator_rejects_missing_build_ignore(self) -> None:
        """Keeps generated governance reports ignored through build/."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            gitignore = root / GITIGNORE
            content = gitignore.read_text(encoding="utf-8")
            gitignore.write_text(content.replace("build/\n", "", 1), encoding="utf-8")
            result = self.validate(root)
        self.assert_rejected(result, "build reports ignore")


if __name__ == "__main__":
    unittest.main()
