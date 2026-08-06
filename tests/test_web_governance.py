"""Contract tests for revision-baseline governance."""

from __future__ import annotations

import importlib.util
import json
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path, PureWindowsPath
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_web_governance.py"
VALIDATOR_SPEC = importlib.util.spec_from_file_location("validate_web_governance_under_test", VALIDATOR)
if VALIDATOR_SPEC is None or VALIDATOR_SPEC.loader is None:
    raise RuntimeError("cannot load web governance validator")
VALIDATOR_MODULE = importlib.util.module_from_spec(VALIDATOR_SPEC)
VALIDATOR_SPEC.loader.exec_module(VALIDATOR_MODULE)
render_baseline = VALIDATOR_MODULE.render_baseline
render_requirements = VALIDATOR_MODULE.render_requirements
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
ARCHIVE_PAGES_WORKFLOW = Path(".github/workflows/archive-pages.yml")
HUB_PAGES_WORKFLOW = Path(".github/workflows/hub-pages.yml")
README = Path("README.md")
GITIGNORE = Path(".gitignore")

PRESERVED_CHECK_COMMANDS = (
    "$(PYTHON) -m json.tool files/$(UUID)/metadata.json >/dev/null",
    "$(PYTHON) -m json.tool files/$(UUID)/settings-schema.json >/dev/null",
    "$(PYTHON) -m json.tool config/web-media-limits.json >/dev/null",
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
    "$(PYTHON) -m py_compile scripts/build_web_site.py scripts/validate_web_plan.py scripts/validate_web_governance.py scripts/validate_web_relations.py scripts/web_inventory.py scripts/web_ids.py scripts/web_content_model.py scripts/web_content_errors.py scripts/validate_web_manifest.py scripts/measure_web_media.py",
    "$(PYTHON) tests/test_epub_contract.py",
    "$(PYTHON) tests/test_pages_artifact.py",
    "$(PYTHON) tests/test_web_build.py",
    "$(PYTHON) tests/test_check_equivalence.py",
    "$(PYTHON) -m unittest tests.test_web_plan",
    "$(PYTHON) -m unittest tests.test_web_inventory",
    "$(PYTHON) -m unittest tests.test_web_content_schemas",
    "$(PYTHON) -m unittest tests.test_web_ids",
    "$(PYTHON) -m unittest tests.test_web_pairing",
    "$(PYTHON) -m unittest tests.test_web_content_errors",
    "$(PYTHON) -m unittest tests.test_web_manifest",
    "$(PYTHON) -m unittest tests.test_web_media_measurement",
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
            REQUIREMENTS_DOC, ADR_DOC, PROVENANCE, WORKFLOW, ARCHIVE_PAGES_WORKFLOW,
            HUB_PAGES_WORKFLOW, MAKEFILE,
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

    def refresh_plan_digest(self, root: Path) -> None:
        digest = hashlib.sha256((root / PLAN).read_bytes()).hexdigest()
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
            document.write_text(
                re.sub(r"SHA-256 `[0-9a-f]{64}`", f"SHA-256 `{digest}`", document.read_text(encoding="utf-8"), count=1),
                encoding="utf-8",
            )
    def test_accepts_canonical_revision_baseline(self) -> None:
        """Rejects regressions that make frozen and observed evidence inconsistent."""
        result = self.validate(ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_pages_workflow_without_dynamic_readme_source(self) -> None:
        """Rejects a Pages build that cannot mirror the repository README."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            workflow = root / HUB_PAGES_WORKFLOW
            content = workflow.read_text(encoding="utf-8")
            workflow.write_text(content.replace("          WIRTELPRIMPF_README_PATH: ${{ github.workspace }}/README.md\n", "", 1), encoding="utf-8")
            result = self.validate(root)
        self.assert_rejected(result, "Pages workflow README source")

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

    def test_renders_recorded_no_drift_classification(self) -> None:
        """Reports a checked no-drift observation without relabeling it as drift."""
        revisions = self.read_revisions(ROOT)
        generator = revisions["repositories"][0]
        generator["observed"]["sha"] = generator["frozen_sha"]
        generator["drift_classification"] = "no-drift"

        baseline = render_baseline(revisions)

        self.assertIn(", no-drift |", baseline)
        self.assertNotIn(", Drift |", baseline)

    def test_renders_document_links_as_posix_paths(self) -> None:
        """Keeps generated Markdown links portable when hosted on Windows."""
        with (
            patch.object(VALIDATOR_MODULE, "PLAN_PATH", PureWindowsPath("docs/plans/PLAN.md")),
            patch.object(
                VALIDATOR_MODULE,
                "REQUIREMENTS_PATH",
                PureWindowsPath("config/requirements.json"),
            ),
        ):
            document = render_requirements({"plan_sha256": "digest", "requirements": []})

        self.assertIn("`docs/plans/PLAN.md`", document)
        self.assertIn("`config/requirements.json`", document)
        self.assertNotIn("\\", document)

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

    def test_rejects_malformed_status_package_register_without_traceback(self) -> None:
        """Rejects status package records before deriving requirement mappings."""
        mutations = (
            {},
            [None],
            [{"id": [], "milestone": "M00"}],
            [{"id": "WEB-P00-01", "milestone": []}],
        )
        for packages in mutations:
            with self.subTest(packages=packages), self.copied_root() as temporary:
                root = Path(temporary)
                status = self.read_json(root, STATUS)
                status["packages"] = packages
                self.write_json(root, STATUS, status)
                result = self.validate(root)
            self.assert_rejected(result, "status package register")
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

    def test_rejects_top_level_duplicate_json_keys(self) -> None:
        """Rejects duplicate top-level members in every governance JSON register."""
        for relative in (REVISIONS, STATUS, REQUIREMENTS, DECISIONS):
            with self.subTest(relative=relative), self.copied_root() as temporary:
                root = Path(temporary)
                path = root / relative
                content = path.read_text(encoding="utf-8")
                path.write_text(
                    content.replace(
                        '"schema_version": 1',
                        '"schema_version": 999,\n  "schema_version": 1',
                        1,
                    ),
                    encoding="utf-8",
                )
                result = self.validate(root)
            self.assert_rejected(result, "duplicate JSON key")
            self.assertNotIn("Traceback", result.stderr)

    def test_rejects_nested_duplicate_json_keys(self) -> None:
        """Rejects duplicate nested members in every governance JSON register."""
        mutations = (
            (
                REVISIONS,
                '"state": "live-verified-repinned"',
                '"state": "mutated", "state": "live-verified-repinned"',
            ),
            (
                STATUS,
                '"version": "2.0.0"',
                '"version": "0.0.0",\n    "version": "2.0.0"',
            ),
            (
                REQUIREMENTS,
                '"id": "WEB-REQ-001"',
                '"id": "WEB-REQ-999",\n      "id": "WEB-REQ-001"',
            ),
            (
                DECISIONS,
                '"id": "ADR-WEB-001"',
                '"id": "ADR-WEB-999", "id": "ADR-WEB-001"',
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
            self.assert_rejected(result, "duplicate JSON key")
            self.assertNotIn("Traceback", result.stderr)

    def test_rejects_unknown_plan_requirement_without_traceback(self) -> None:
        """Rejects unknown package requirement IDs through controlled stderr."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            plan = root / PLAN
            content = plan.read_text(encoding="utf-8")
            original = '- **Anforderungs-IDs:** `WEB-REQ-025`'
            self.assertIn(original, content)
            plan.write_text(
                content.replace(original, '- **Anforderungs-IDs:** `WEB-REQ-999`', 1),
                encoding="utf-8",
            )
            self.refresh_plan_digest(root)
            result = self.validate(root)
        self.assert_rejected(result, "unknown plan requirement ID")
        self.assertNotIn("Traceback", result.stderr)

    def test_rejects_package_without_requirement_back_reference(self) -> None:
        """Rejects a plan package omitted from all requirement back-references."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            plan = root / PLAN
            content = plan.read_text(encoding="utf-8")
            original = '- **Anforderungs-IDs:** `WEB-REQ-025`'
            self.assertEqual(content.count(original), 2)
            first = content.index(original, content.index("### WEB-P01-02"))
            content = (
                content[:first]
                + '- **Anforderungs-IDs:** `WEB-REQ-025`, `WEB-REQ-025`'
                + content[first + len(original):]
            )
            second = content.index(original, content.index("### WEB-P01-03"))
            content = content[:second] + "- **Anforderungs-IDs:**" + content[second + len(original):]
            plan.write_text(content, encoding="utf-8")
            requirements = self.read_json(root, REQUIREMENTS)
            requirement = next(
                item for item in requirements["requirements"]
                if item["id"] == "WEB-REQ-025"
            )
            requirement["packages"].remove("WEB-P01-03")
            requirement["milestones"].remove("M04")
            self.write_json(root, REQUIREMENTS, requirements)
            requirements_doc = root / REQUIREMENTS_DOC
            doc_content = requirements_doc.read_text(encoding="utf-8")
            requirements_doc.write_text(
                doc_content.replace(
                    "`WEB-P01-02`, `WEB-P01-03` | M02, M04",
                    "`WEB-P01-02` | M02",
                    1,
                ),
                encoding="utf-8",
            )
            self.refresh_plan_digest(root)
            result = self.validate(root)
        self.assert_rejected(result, "requirement package coverage")

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
            (
                "Alle im Projekt verwendeten Quelltexte, Texte, Bilder und sonstigen Assets wurden von uns selbst erstellt.",
                "Die Projektinhalte wurden nicht selbst erstellt.",
            ),
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
                document.write_text(re.sub(r"SHA-256 `[0-9a-f]{64}`", f"SHA-256 `{digest}`", document.read_text(encoding="utf-8"), count=1), encoding="utf-8")
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
                document.write_text(re.sub(r"SHA-256 `[0-9a-f]{64}`", f"SHA-256 `{digest}`", document.read_text(encoding="utf-8"), count=1), encoding="utf-8")
            result = self.validate(root)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_make_check_preserves_existing_gates_and_runs_governance(self) -> None:
        """Protects existing check order while adding every governance command."""
        commands = re.search(
            r"^check:\n(?P<commands>(?:\t.*\n)+)",
            (ROOT / MAKEFILE).read_text(encoding="utf-8"),
            re.MULTILINE,
        )
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
        self.assertNotRegex(applet_body, r"(?i)\bwrite\b")
        self.assertNotRegex(applet_body, r"(?i)\bdeploy(?:ment)?\b")

    def test_pages_workflows_isolate_build_from_deploy_permissions(self) -> None:
        """Keeps Pages build validation unprivileged and deploy artifact-only."""
        for path in (ARCHIVE_PAGES_WORKFLOW, HUB_PAGES_WORKFLOW):
            with self.subTest(workflow=path):
                workflow = (ROOT / path).read_text(encoding="utf-8")
                jobs = workflow.split("\njobs:\n", 1)[1]
                names = re.findall(r"^  ([a-z][a-z0-9_-]*):\n", jobs, re.MULTILINE)
                self.assertEqual(names, ["build", "deploy"])
                build = re.search(r"^  build:\n(?P<body>.*?)(?=^  deploy:)", jobs, re.MULTILINE | re.DOTALL)
                deploy = re.search(r"^  deploy:\n(?P<body>.*)$", jobs, re.MULTILINE | re.DOTALL)
                self.assertIsNotNone(build)
                self.assertIsNotNone(deploy)
                assert build is not None and deploy is not None
                self.assertIn("contents: read", build.group("body"))
                self.assertIn("actions/upload-pages-artifact@fc324d3547104276b827a68afc52ff2a11cc49c9", build.group("body"))
                self.assertIn("scripts/build_web_site.py", build.group("body"))
                self.assertIn("validate_pages_artifact.py", build.group("body"))
                self.assertIn("tree_sha256", build.group("body"))
                self.assertEqual(build.group("body").count("python3 scripts/build_web_site.py"), 1)
                self.assertNotIn("npm --prefix web run build", build.group("body"))
                self.assertNotIn("actions/deploy-pages", build.group("body"))
                self.assertIn("needs: build", deploy.group("body"))
                self.assertIn("pages: write", deploy.group("body"))
                self.assertIn("id-token: write", deploy.group("body"))
                self.assertIn("environment:\n      name: github-pages", deploy.group("body"))
                self.assertIn("${{ steps.deployment.outputs.page_url }}", deploy.group("body"))
                self.assertIn("actions/deploy-pages@cd2ce8fcbc39b97be8ca5fce6e763baed58fa128", deploy.group("body"))
                self.assertNotIn("actions/checkout", deploy.group("body"))
                self.assertNotRegex(deploy.group("body"), r"npm .*build")
                self.assertIn("cancel-in-progress: false", workflow)

    def test_hub_workflow_passes_all_dispatch_inputs_to_one_source_command(self) -> None:
        """Keeps required Hub dispatch inputs attached to its source resolver."""
        workflow = (ROOT / HUB_PAGES_WORKFLOW).read_text(encoding="utf-8")
        source = re.search(
            r"- name: Resolve an exact current-story source\n(?P<body>.*?)(?=\n      - name:)",
            workflow,
            re.DOTALL,
        )
        self.assertIsNotNone(source)
        assert source is not None
        self.assertIn(
            '--github-output "${GITHUB_OUTPUT}" \\\n            --repository "${INPUT_REPOSITORY}"',
            source.group("body"),
        )
        self.assertNotRegex(
            source.group("body"),
            r'--(?:data-root|external-root|github-output|repository|revision) "[^\n]+"\n',
        )

    def test_pages_governance_rejects_deploy_privilege_in_build_job(self) -> None:
        """Rejects workflow edits that let a failed build deploy or retain Pages tokens."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            workflow = root / ARCHIVE_PAGES_WORKFLOW
            content = workflow.read_text(encoding="utf-8")
            workflow.write_text(
                content.replace("      contents: read", "      contents: read\n      pages: write", 1),
                encoding="utf-8",
            )
            result = self.validate(root)
        self.assert_rejected(result, "Pages workflow")

    def test_pages_governance_rejects_extra_build_permission(self) -> None:
        """Rejects any build permission beyond read-only repository contents."""
        for path in (ARCHIVE_PAGES_WORKFLOW, HUB_PAGES_WORKFLOW):
            with self.subTest(workflow=path), self.copied_root() as temporary:
                root = Path(temporary)
                workflow = root / path
                content = workflow.read_text(encoding="utf-8")
                workflow.write_text(
                    content.replace("      contents: read\n", "      contents: read\n      issues: read\n", 1),
                    encoding="utf-8",
                )
                result = self.validate(root)
            self.assert_rejected(result, "Pages workflow build permissions")

    def test_pages_governance_rejects_extra_deploy_permission(self) -> None:
        """Rejects any deploy permission beyond Pages write and OIDC token issuance."""
        for path in (ARCHIVE_PAGES_WORKFLOW, HUB_PAGES_WORKFLOW):
            with self.subTest(workflow=path), self.copied_root() as temporary:
                root = Path(temporary)
                workflow = root / path
                content = workflow.read_text(encoding="utf-8")
                workflow.write_text(
                    content.replace("      id-token: write\n", "      id-token: write\n      issues: read\n", 1),
                    encoding="utf-8",
                )
                result = self.validate(root)
            self.assert_rejected(result, "Pages workflow deploy permissions")

    def test_pages_governance_rejects_commented_extra_permission(self) -> None:
        """Rejects inline-commented permissions without truncating their YAML mapping."""
        cases = (
            (
                "      contents: read\n",
                "      contents: read\n      issues: read # extra\n",
                "Pages workflow build permissions",
            ),
            (
                "      id-token: write\n",
                "      id-token: write\n      issues: read # extra\n",
                "Pages workflow deploy permissions",
            ),
        )
        for path in (ARCHIVE_PAGES_WORKFLOW, HUB_PAGES_WORKFLOW):
            for original, mutated, message in cases:
                with self.subTest(workflow=path, permission=message), self.copied_root() as temporary:
                    root = Path(temporary)
                    workflow = root / path
                    content = workflow.read_text(encoding="utf-8")
                    workflow.write_text(content.replace(original, mutated, 1), encoding="utf-8")
                    result = self.validate(root)
                self.assert_rejected(result, message)

    def test_pages_governance_rejects_extra_permission_after_blank_or_comment(self) -> None:
        """Keeps blank and comment lines inside each job permissions mapping."""
        cases = (
            (
                "      contents: read\n",
                "      contents: read\n\n      issues: read\n",
                "Pages workflow build permissions",
            ),
            (
                "      contents: read\n",
                "      contents: read\n      # permissions continue\n      issues: read\n",
                "Pages workflow build permissions",
            ),
            (
                "      id-token: write\n",
                "      id-token: write\n\n      issues: read\n",
                "Pages workflow deploy permissions",
            ),
            (
                "      id-token: write\n",
                "      id-token: write\n      # permissions continue\n      issues: read\n",
                "Pages workflow deploy permissions",
            ),
        )
        for path in (ARCHIVE_PAGES_WORKFLOW, HUB_PAGES_WORKFLOW):
            for original, mutated, message in cases:
                with (
                    self.subTest(workflow=path, permission=message, mutation=mutated),
                    self.copied_root() as temporary,
                ):
                    root = Path(temporary)
                    workflow = root / path
                    content = workflow.read_text(encoding="utf-8")
                    workflow.write_text(content.replace(original, mutated, 1), encoding="utf-8")
                    result = self.validate(root)
                self.assert_rejected(result, message)

    def test_pages_governance_rejects_quoted_extra_hub_trigger(self) -> None:
        """Rejects valid quoted YAML triggers beyond manual dispatch."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            workflow = root / HUB_PAGES_WORKFLOW
            content = workflow.read_text(encoding="utf-8")
            workflow.write_text(
                content.replace("on:\n", 'on:\n  "push":\n', 1),
                encoding="utf-8",
            )
            result = self.validate(root)
        self.assert_rejected(result, "Pages workflow Hub trigger")

    def test_pages_governance_rejects_quoted_or_mixed_case_extra_job(self) -> None:
        """Rejects every extra Pages job regardless of YAML quoting or case."""
        extra_jobs = (
            '  "release":\n    runs-on: ubuntu-24.04\n',
            "  Release:\n    runs-on: ubuntu-24.04\n",
        )
        for path in (ARCHIVE_PAGES_WORKFLOW, HUB_PAGES_WORKFLOW):
            for extra_job in extra_jobs:
                with self.subTest(workflow=path, extra_job=extra_job), self.copied_root() as temporary:
                    root = Path(temporary)
                    workflow = root / path
                    content = workflow.read_text(encoding="utf-8")
                    workflow.write_text(content.replace("jobs:\n", f"jobs:\n{extra_job}", 1), encoding="utf-8")
                    result = self.validate(root)
                self.assert_rejected(result, "Pages workflow jobs")

    def test_rejects_missing_catgpt_worker_ci_job(self) -> None:
        """Rejects a workflow that silently loses CatGPT worker coverage."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            workflow = root / WORKFLOW
            content = workflow.read_text(encoding="utf-8")
            workflow.write_text(
                re.sub(r"^  catgpt-worker:\n.*?(?=^  web:)", "", content, flags=re.MULTILINE | re.DOTALL),
                encoding="utf-8",
            )
            result = self.validate(root)
        self.assert_rejected(result, "CI jobs")

    def test_rejects_catgpt_worker_deploy_without_dry_run(self) -> None:
        """Rejects CatGPT worker deployment when dry-run protection is removed."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            workflow = root / WORKFLOW
            content = workflow.read_text(encoding="utf-8")
            original = "npm --prefix catgpt-worker run deploy -- --dry-run"
            self.assertIn(original, content)
            workflow.write_text(
                content.replace(original, "npm --prefix catgpt-worker run deploy", 1),
                encoding="utf-8",
            )
            result = self.validate(root)
        self.assert_rejected(result, "CI publication command")

    def test_rejects_missing_catgpt_csp_check_in_web_ci(self) -> None:
        """Rejects web CI that stops checking CatGPT CSP output."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            workflow = root / WORKFLOW
            content = workflow.read_text(encoding="utf-8")
            command = 'grep -R -n "connect-src https://catgpt\\.wirtelprimpf\\.telacore\\.org" web/dist'
            self.assertIn(command, content)
            workflow.write_text(content.replace(command, "", 1), encoding="utf-8")
            result = self.validate(root)
        self.assert_rejected(result, "CI job commands")

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

    def test_rejects_quoted_flow_style_ci_job(self) -> None:
        """Rejects an extra quoted flow-style job hidden from block extraction."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            workflow = root / WORKFLOW
            content = workflow.read_text(encoding="utf-8")
            workflow.write_text(
                content
                + '  "release": {runs-on: ubuntu-24.04, steps: [{name: Release, run: "npx --yes wrangler pages deploy web/dist"}]}\n',
                encoding="utf-8",
            )
            result = self.validate(root)
        self.assert_rejected(result, "CI jobs")

    def test_rejects_unnamed_ci_publication_step(self) -> None:
        """Rejects a publication command hidden in an unnamed workflow step."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            workflow = root / WORKFLOW
            content = workflow.read_text(encoding="utf-8")
            workflow.write_text(
                content.replace(
                    "    steps:\n",
                    "    steps:\n      - run: wrangler pages publish web/dist\n",
                    1,
                ),
                encoding="utf-8",
            )
            result = self.validate(root)
        self.assert_rejected(result, "CI")

    def test_rejects_unnamed_ci_external_action_step(self) -> None:
        """Rejects a foreign action hidden in an unnamed workflow step."""
        with self.copied_root() as temporary:
            root = Path(temporary)
            workflow = root / WORKFLOW
            content = workflow.read_text(encoding="utf-8")
            workflow.write_text(
                content.replace(
                    "    steps:\n",
                    "    steps:\n      - uses: attacker/deploy-action@0000000000000000000000000000000000000000\n",
                    1,
                ),
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
