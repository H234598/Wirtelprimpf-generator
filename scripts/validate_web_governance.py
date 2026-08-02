#!/usr/bin/env python3
"""Fail-closed validation for revision-baseline governance."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import re
import sys
from pathlib import Path


PLAN_PATH = Path("docs/plans/WIRTELPRIMPF-WEBSEITE-IMPLEMENTIERUNGSPLAN.md")
BASELINE_PATH = Path("docs/REVISIONSBASELINE.md")
REVISIONS_PATH = Path("config/reference-revisions.json")
STATUS_PATH = Path("config/web-plan-status.json")
REQUIREMENTS_PATH = Path("config/web-requirements.json")
DECISIONS_PATH = Path("config/architecture-decisions.json")
REQUIREMENTS_DOC_PATH = Path("docs/requirements/WIRTELPRIMPF-WEBSEITE.md")
ADR_DOC_PATH = Path("docs/adr/README.md")
PROVENANCE_PATH = Path("PROVENANCE.md")
WORKFLOW_PATH = Path(".github/workflows/check.yml")
MAKEFILE_PATH = Path("Makefile")
README_PATH = Path("README.md")
GITIGNORE_PATH = Path(".gitignore")
EXPECTED_REPOSITORIES = {
    "H234598/Wirtelprimpf-generator": (
        "Generator, Plattform, Applet, Admin, Seitenfabrik, Hub",
        "274b25c9e1f9ea97d3b060997ed5c425d2b30e9f",
        "2026-08-02 13:00:40 Europe/Berlin",
    ),
    "H234598/Wirtelprimpf-0001": (
        "Story-/Medienmanifest, Archivvertrag, dünner Pages-Aufrufer",
        "79274c1fef77306eb9ee0e9bd2682f4b28b74849",
        "2026-08-02 00:58:57 Europe/Berlin",
    ),
    "H234598/desinfect": (
        "Governance-/Storage-/Statusreferenz",
        "3bed7ac358b861490727adce36a418db133f8daf",
        "2026-07-31 23:24:24 Europe/Berlin",
    ),
    "H234598/ADHS-Lernpfad": (
        "Browser-/Recovery-/Reviewreferenz",
        "ee91741ec71a1232a4c3b90f42b805591a0d9359",
        "2026-08-01 06:10:04 Europe/Berlin",
    ),
    "H234598/Cheatsheets": (
        "Pages-/Artefakt-/IO-Referenz",
        "71bcad7a8ab183144e8ff007b85aea8bb6cff3b9",
        "2026-07-28 16:11:05 Europe/Berlin",
    ),
}
GENERATOR_OBSERVED_SHA = "3a60129417659bed9939755baf56d649510454d1"
FACTORY_PIN = "b00d824adee47341e3251bc18e09239fde1c5939"
EXPECTED_PHASE_IDS = {f"P{number:02d}" for number in range(13)}
EXPECTED_HISTORICAL_ADRS = {f"ADR-WEB-{number:03d}" for number in range(1, 14)}
EXPECTED_CURRENT_ADRS = {f"ADR-WEB-{number:03d}" for number in range(1, 16)}
EXPECTED_BOUNDARIES = {
    "Pages source configuration",
    "github-pages environment protection",
    "rulesets, required checks, and branch protection",
    "CodeRabbit organization configuration",
    "custom-domain verification",
    "DNS and aliases",
    "HTTPS enforcement",
    "secrets",
    "Actions policy",
    "live content of both domains",
}
EXPECTED_CI_JOBS = {"applet", "platform", "web"}
EXPECTED_APPLET_PATHS = {
    ".github", "Makefile", "Sourcecode", "files", "scripts", "tests", "docs",
    "config", "README.md", "PROVENANCE.md", "wirtelprimpf_platform", "pyproject.toml",
}
EXPECTED_ACTIONS = Counter({
    "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1": 3,
    "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1": 2,
    "actions/setup-node@820762786026740c76f36085b0efc47a31fe5020": 2,
})
CI_JOB_ACTIONS = {
    "applet": (
        "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
        "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1",
        "actions/setup-node@820762786026740c76f36085b0efc47a31fe5020",
    ),
    "platform": (
        "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
        "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1",
    ),
    "web": (
        "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
        "actions/setup-node@820762786026740c76f36085b0efc47a31fe5020",
    ),
}
CI_STEP_NAMES = {
    "applet": (
        "Checkout relevant repository paths", "Set up Python", "Set up Node.js",
        "Install runtime test dependencies", "Run repository checks",
    ),
    "platform": (
        "Checkout generator sources", "Set up Python", "Install generator package",
        "Verify transactional settings entrypoint", "Run platform contract tests",
        "Compile all Python sources", "Verify CLI entrypoint",
    ),
    "web": (
        "Checkout site factory", "Set up Node.js", "Install exact web dependencies",
        "Test and type-check the site factory", "Build and validate hub profile",
        "Build and validate archive profile",
    ),
}
CI_JOB_COMMANDS = {
    "applet": (
        "python -m pip install --disable-pip-version-check -r Sourcecode/requirements.txt",
        "make check",
    ),
    "platform": (
        "python -m pip install --disable-pip-version-check -e .",
        "wirtelprimpf-settings --help >/dev/null",
        "python -m unittest discover -s tests/platform -p 'test_*.py' -v",
        "python -m compileall -q Sourcecode wirtelprimpf_platform scripts",
        "wirtelprimpf-platform mapping 51",
    ),
    "web": (
        "npm ci --ignore-scripts",
        "npm test",
        "npm run check",
        "npm --prefix web run build",
        "python3 scripts/validate_pages_artifact.py web/dist --expected-domain wirtelprimpf.telacore.org",
        "npm --prefix web run build",
        "python3 scripts/validate_pages_artifact.py web/dist --expected-domain wirtelprimpf-0001.telacore.org",
    ),
}
REQUIRED_MAKE_CHECK_COMMANDS = (
    "$(PYTHON) -m json.tool files/$(UUID)/metadata.json >/dev/null",
    "$(PYTHON) -m json.tool files/$(UUID)/settings-schema.json >/dev/null",
    "$(PYTHON) -m py_compile Sourcecode/wirtelprimpf_generator.py",
    "$(PYTHON) -m py_compile files/$(UUID)/helper.py files/$(UUID)/SettingsLogo.py files/$(UUID)/settings_sync.py",
    "$(PYTHON) -m py_compile files/$(UUID)/story_directives_core.py files/$(UUID)/StoryDirectives.py",
    "$(PYTHON) -m py_compile scripts/validate_web_plan.py scripts/validate_web_governance.py",
    "node --check files/$(UUID)/applet.js", "node tests/test_applet_runtime.js",
    "node --test tests/test_admin_ui.mjs", "$(PYTHON) -m unittest tests.test_semver",
    "$(PYTHON) -m unittest tests.test_git_object_fallback",
    "$(PYTHON) -m unittest tests.test_release_publication",
    "$(PYTHON) -m unittest tests.test_helper_env",
    "$(PYTHON) -m unittest tests.test_applet_settings_sync",
    "$(PYTHON) -m unittest tests.test_settings_schema",
    "$(PYTHON) -m unittest tests.test_story_directives",
    "$(PYTHON) -m unittest tests.test_rollout_plan_contract",
    "$(PYTHON) -m unittest tests.test_web_plan", "$(PYTHON) tests/test_web_governance.py",
    "$(PYTHON) scripts/validate_web_plan.py --root .",
    "$(PYTHON) scripts/validate_web_governance.py --root .",
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
README_LINKS = (
    "docs/plans/WIRTELPRIMPF-WEBSEITE-IMPLEMENTIERUNGSPLAN.md",
    "docs/REVISIONSBASELINE.md", "docs/requirements/WIRTELPRIMPF-WEBSEITE.md",
    "docs/adr/README.md", "PROVENANCE.md",
)
README_COMMANDS = (
    "make check", "python3 scripts/validate_web_plan.py --root .",
    "python3 scripts/validate_web_governance.py --root .",
)
PROVENANCE_MODES = {
    "H234598/Wirtelprimpf-generator": "adapted",
    "H234598/Wirtelprimpf-0001": "concept",
    "H234598/desinfect": "concept",
    "H234598/ADHS-Lernpfad": "concept",
    "H234598/Cheatsheets": "concept",
}


class ValidationError(Exception):
    """Controlled validation failure."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def read_text(root: Path, relative: Path) -> str:
    try:
        return (root / relative).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise ValidationError(f"malformed {relative}: {error}") from error


def read_json(root: Path) -> dict:
    try:
        value = json.loads(read_text(root, REVISIONS_PATH))
    except json.JSONDecodeError as error:
        raise ValidationError(f"malformed {REVISIONS_PATH}: {error}") from error
    require(isinstance(value, dict), "revision register object")
    return value


def read_json_path(root: Path, path: Path) -> dict:
    try:
        value = json.loads(read_text(root, path))
    except json.JSONDecodeError as error:
        raise ValidationError(f"malformed {path}: {error}") from error
    require(isinstance(value, dict), f"{path} object")
    return value


def plan_packages(plan: str) -> dict[str, dict[str, object]]:
    parts = re.split(r"^### (WEB-P\d\d-\d\d) – .+$", plan, flags=re.MULTILINE)
    result: dict[str, dict[str, object]] = {}
    for index in range(1, len(parts), 2):
        package, body = parts[index], parts[index + 1]
        requirement_line = re.search(r"\*\*Anforderungs-IDs:\*\*(.*)", body)
        if requirement_line is None:
            continue
        command_block = re.search(r"\*\*Lokale Prüfkommandos:\*\*\n\n```bash\n(.*?)\n```", body, re.DOTALL)
        result[package] = {
            "requirements": re.findall(r"WEB-REQ-\d{3}", requirement_line.group(1)),
            "verification": command_block.group(1).splitlines() if command_block else [],
        }
    return result


def ci_job(workflow: str, name: str) -> str:
    job = re.search(
        rf"^  {re.escape(name)}:\n(?P<body>.*?)(?=^  [a-z][a-z0-9_-]*:|\Z)",
        workflow,
        re.MULTILINE | re.DOTALL,
    )
    require(job is not None, "CI jobs")
    return job.group("body")


def ci_run_commands(job: str) -> tuple[str, ...]:
    """Extract executable scalar and literal-block run commands from one job."""
    lines = job.splitlines()
    commands: list[str] = []
    index = 0
    while index < len(lines):
        match = re.fullmatch(r"        run:\s*(.*)", lines[index])
        if match is None:
            index += 1
            continue
        value = match.group(1).strip()
        if value not in {"|", ">", "|-", ">-"}:
            require(bool(value) and not value.startswith("#"), "CI job commands")
            commands.append(value)
            index += 1
            continue
        index += 1
        while index < len(lines):
            line = lines[index]
            if line and len(line) - len(line.lstrip(" ")) <= 8:
                break
            command = line.strip()
            if command and not command.startswith("#"):
                commands.append(command)
            index += 1
    return tuple(commands)


def validate_ci_integration(root: Path) -> None:
    """Keep fixed, read-only CI safeguards and required checks intact."""
    workflow = read_text(root, WORKFLOW_PATH)
    require("permissions:\n  contents: read\n\n" in workflow, "CI permissions")
    require(re.search(r"\bwrite\b", workflow, re.IGNORECASE) is None, "CI permissions")
    parts = workflow.split("\njobs:\n", 1)
    require(len(parts) == 2, "CI jobs")
    jobs_section = parts[1]
    jobs = set(re.findall(r"^  ([a-z][a-z0-9_-]*):\n", jobs_section, re.MULTILINE))
    require(jobs == EXPECTED_CI_JOBS, "CI jobs")
    actions = Counter(re.findall(r"^\s+uses:\s+(\S+)(?:\s+#.*)?$", workflow, re.MULTILINE))
    require(actions == EXPECTED_ACTIONS, "CI action pin")

    bodies = {name: ci_job(jobs_section, name) for name in EXPECTED_CI_JOBS}
    for body in bodies.values():
        require("runs-on: ubuntu-24.04" in body, "CI runner")
        require("timeout-minutes: 20" in body, "CI timeout")
        require("persist-credentials: false" in body, "CI checkout credentials")
    require("lfs: false" in bodies["applet"], "CI checkout LFS")

    for name in ("applet", "platform"):
        require(re.search(r"uses: actions/setup-python@[0-9a-f]{40}(?:\s|$)", bodies[name]) is not None, "CI action pin")
        require('python-version: "3.12"' in bodies[name], "CI Python runtime")
    for name in ("applet", "web"):
        require(re.search(r"uses: actions/setup-node@[0-9a-f]{40}(?:\s|$)", bodies[name]) is not None, "CI action pin")
        require('node-version: "24.13.1"' in bodies[name], "CI Node runtime")

    sparse_checkout = re.search(r"sparse-checkout: \|\n(?P<paths>(?:            .*\n)+)", bodies["applet"])
    require(sparse_checkout is not None, "CI applet sparse checkout")
    paths = {line.strip() for line in sparse_checkout.group("paths").splitlines()}
    require(paths == EXPECTED_APPLET_PATHS, "CI applet sparse checkout")
    for name, commands in CI_JOB_COMMANDS.items():
        job_actions = tuple(re.findall(r"^\s+uses:\s+(\S+)(?:\s+#.*)?$", bodies[name], re.MULTILINE))
        require(job_actions == CI_JOB_ACTIONS[name], "CI action pin")
        steps = tuple(re.findall(r"^      - (.+)$", bodies[name], re.MULTILINE))
        require(steps == tuple(f"name: {step}" for step in CI_STEP_NAMES[name]), "CI job steps")
        executable = ci_run_commands(bodies[name])
        require(
            not any(re.search(r"\b(?:deploy|publish)\b", command, re.IGNORECASE) for command in executable),
            "CI publication command",
        )
        require(executable == commands, "CI job commands")


def validate_repository_integration(root: Path) -> None:
    """Keep direct validation wired into local checks and documentation."""
    makefile = read_text(root, MAKEFILE_PATH)
    check = re.search(r"^check:\n(?P<body>(?:\t.*\n)+)", makefile, re.MULTILINE)
    require(check is not None, "Make check")
    commands = [line[1:] for line in check.group("body").splitlines()]
    require(all(command in commands for command in REQUIRED_MAKE_CHECK_COMMANDS), "Make check")
    positions = [commands.index(command) for command in REQUIRED_MAKE_CHECK_COMMANDS]
    require(positions == sorted(positions), "Make check order")

    readme = read_text(root, README_PATH)
    require("## Web-Governance" in readme, "README governance")
    require(all(f"]({link})" in readme for link in README_LINKS), "README governance links")
    require(all(command in readme for command in README_COMMANDS), "README governance commands")

    ignore_lines = {
        line.strip() for line in read_text(root, GITIGNORE_PATH).splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    require("build/" in ignore_lines, "build reports ignore")


def render_requirements(requirements: dict) -> str:
    lines = [
        "# Wirtelprimpf-Webseite – Anforderungen", "",
        f"Autorität: `{PLAN_PATH}` (SHA-256 `{requirements['plan_sha256']}`). V2-Kapitel 0–28 hat Vorrang; diese Datei ist deterministische Projektion von `{REQUIREMENTS_PATH}`.", "",
        "| ID | Anforderung | Paket(e) | Meilenstein(e) | Verifikation |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in requirements["requirements"]:
        lines.append("| `{id}` | {text} | {packages} | {milestones} | {verification} |".format(
            id=item["id"], text=item["text"], packages=", ".join(f"`{value}`" for value in item["packages"]),
            milestones=", ".join(item["milestones"]), verification="<br>".join(f"`{value}`" for value in item["verification"])))
    return "\n".join(lines) + "\n"


def render_adrs(decisions: dict) -> str:
    lines = [
        "# Architekturentscheidungen", "",
        f"Autorität: V2-Kapitel 20 des kanonischen Plans (SHA-256 `{decisions['plan_sha256']}`). Historisches Kapitel 37 mit 13 Entwürfen ist bei Konflikten superseded; IDs 001–013 sind historische Kernmenge, 001–015 aktuelle Menge.", "",
        "| ADR | Entscheidung | Status | Neubewertungstrigger |", "| --- | --- | --- | --- |",
    ]
    for item in decisions["decisions"]:
        lines.append(f"| `{item['id']}` | {item['decision']} | {item['status']} | {item['reevaluation_trigger']} |")
    return "\n".join(lines) + "\n"


def render_provenance(revisions: dict) -> str:
    """Render exact reuse claims from validated frozen repository records."""
    lines = [
        "# Provenienz",
        "",
        "M00-Governance übernimmt keine Implementierungscodes oder Assets Dritter.",
        "",
        "| Repository | Freeze-SHA | Beitrag zum Plan | Wiederverwendung |",
        "| --- | --- | --- | --- |",
    ]
    for repository in revisions["repositories"]:
        identifier = repository["id"]
        lines.append(
            f"| {identifier} | `{repository['frozen_sha']}` | {repository['role']} | {PROVENANCE_MODES[identifier]} |"
        )
    lines.extend([
        "",
        "## Nicht übernommen",
        "",
        "- `not-used`: Direkte Watchdog-/RKI-Logik aus `H234598/desinfect` wird nicht übernommen.",
        "- `not-used`: MkDocs-/Material-Theme aus `H234598/Cheatsheets` wird nicht übernommen.",
        "",
        "Alle Referenzen sind eingefrorene Commit-SHAs, keine beweglichen Branches.",
        "Lizenzfreigaben werden hier nicht behauptet.",
        "",
    ])
    return "\n".join(lines)


def exact_set(value: object, expected: set[str], message: str) -> None:
    require(isinstance(value, list), message)
    require(all(isinstance(item, str) for item in value), message)
    require(len(value) == len(expected) and set(value) == expected, message)


def render_baseline(revisions: dict) -> str:
    """Render the human baseline from validated structured evidence."""
    lines = [
        "# Revisionsbaseline",
        "",
        "Diese Baseline trennt frozen von observed Evidenz. Freeze-Werte sind reproduzierbare",
        "Referenzen, keine Behauptung über heutigen Remote-Zustand. Beobachtungen werden nur",
        "nach dokumentierter Prüfung aktualisiert.",
        "",
        "| Repository | Rolle | Freeze-HEAD | Beobachtung |",
        "| --- | --- | --- | --- |",
    ]
    for repository in revisions["repositories"]:
        observed = repository["observed"]
        observation = (
            f"`{observed['sha']}`, lokal via `{observed['source']}`, Drift"
            if observed["status"] == "checked"
            else "not-checked"
        )
        lines.append(
            f"| `{repository['id']}` | {repository['role']} | `{repository['frozen_sha']}` | {observation} |"
        )
    boundaries = "\n".join(f"- {boundary}" for boundary in revisions["manual_verification_boundaries"])
    lines.extend(
        [
            "",
            "Generator-Drift ist explizit: lokales `main` wurde beobachtet, nicht am Freeze.",
            "Dies ist keine Fernabfrage und keine Aussage über den aktuellen Remote-Stand.",
            "",
            f"Archiv-Factory-Pin `{revisions['archive_factory_pin']['sha']}` bleibt unverändert.",
            "Er ist ein eingefrorener Rollout-Rückstand, kein hier erlaubtes Repin-Ziel.",
            "",
            "## Manuelle Grenzen",
            "",
            "Folgende Betreiberprüfungen sind unverified:",
            boundaries,
            "",
            "Keine davon ist als erfolgreich geprüft markiert.",
            "",
            "## Wiederholung",
            "",
            "Nach einer neuen, belegten Beobachtung `config/reference-revisions.json` aktualisieren,",
            "`python3 scripts/validate_web_governance.py --root .` und",
            "`python3 tests/test_web_governance.py` ausführen. Änderungen an Freeze, Pin oder",
            "Plan-Digest benötigen neue Evidenz und erneute vollständige Prüfung.",
            "",
        ]
    )
    return "\n".join(lines)


def validate_repository(entry: object) -> None:
    require(isinstance(entry, dict), "repository record")
    require(
        set(entry) == {"branch", "commit_time", "drift_classification", "frozen_sha", "id", "observed", "role"},
        "repository record fields",
    )
    identifier = entry.get("id")
    require(isinstance(identifier, str), "repository IDs")
    require(identifier in EXPECTED_REPOSITORIES, "repository IDs")
    role, frozen_sha, commit_time = EXPECTED_REPOSITORIES[identifier]
    require(isinstance(entry.get("frozen_sha"), str) and re.fullmatch(r"[0-9a-f]{40}", entry["frozen_sha"]), "frozen SHA")
    require(entry.get("role") == role and entry.get("branch") == "main", "frozen repository data")
    require(entry.get("commit_time") == commit_time, "frozen repository data")
    require(entry.get("frozen_sha") == frozen_sha, "frozen repository data")

    observed = entry.get("observed")
    require(isinstance(observed, dict), "observed state")
    require(set(observed) == {"sha", "source", "status"}, "observed state")
    status, sha, source = observed.get("status"), observed.get("sha"), observed.get("source")
    if identifier == "H234598/Wirtelprimpf-generator":
        require(status == "checked" and source == "local-git", "observed state")
        require(isinstance(sha, str) and re.fullmatch(r"[0-9a-f]{40}", sha), "observed state")
        require(sha == GENERATOR_OBSERVED_SHA, "observed state")
        derived_drift = "no-drift" if sha == frozen_sha else "drift"
        require(entry.get("drift_classification") == derived_drift, "drift classification")
        return
    require(status == "not-checked" and sha is None and source is None, "observed state")
    require(entry.get("drift_classification") == "not-checked", "drift classification")


def validate(root: Path) -> None:
    validate_ci_integration(root)
    validate_repository_integration(root)
    plan = read_text(root, PLAN_PATH)
    baseline = read_text(root, BASELINE_PATH)
    revisions = read_json(root)
    require(
        set(revisions) == {"adr_ids", "archive_factory_pin", "manual_verification_boundaries", "phase_ids", "plan_sha256", "repositories", "schema_version"},
        "revision register fields",
    )
    require(revisions.get("schema_version") == 1 and type(revisions.get("schema_version")) is int, "schema version")
    require(revisions.get("plan_sha256") == hashlib.sha256((root / PLAN_PATH).read_bytes()).hexdigest(), "plan digest mismatch")

    repositories = revisions.get("repositories")
    require(isinstance(repositories, list), "repository IDs")
    require(all(isinstance(entry, dict) and isinstance(entry.get("id"), str) for entry in repositories), "repository IDs")
    identifiers = [entry["id"] for entry in repositories]
    require(len(identifiers) == len(EXPECTED_REPOSITORIES) and set(identifiers) == set(EXPECTED_REPOSITORIES), "repository IDs")
    for entry in repositories:
        validate_repository(entry)

    pin = revisions.get("archive_factory_pin")
    require(isinstance(pin, dict) and set(pin) == {"sha", "state"}, "Factory pin")
    require(isinstance(pin, dict) and pin.get("sha") == FACTORY_PIN and pin.get("state") == "frozen-rollout-drift", "Factory pin")
    require(re.fullmatch(r"[0-9a-f]{40}", pin["sha"]) is not None, "Factory pin")
    exact_set(revisions.get("phase_ids"), EXPECTED_PHASE_IDS, "phase IDs")
    adrs = revisions.get("adr_ids")
    require(isinstance(adrs, dict) and set(adrs) == {"current", "historical"}, "ADR IDs")
    exact_set(adrs.get("historical"), EXPECTED_HISTORICAL_ADRS, "historical ADR IDs")
    exact_set(adrs.get("current"), EXPECTED_CURRENT_ADRS, "current ADR IDs")
    exact_set(revisions.get("manual_verification_boundaries"), EXPECTED_BOUNDARIES, "manual verification boundaries")

    for identifier in EXPECTED_PHASE_IDS | EXPECTED_CURRENT_ADRS:
        require(identifier in plan, f"canonical plan missing {identifier}")
    require(baseline == render_baseline(revisions), "baseline doc differs from revision register")

    status = read_json_path(root, STATUS_PATH)
    requirements = read_json_path(root, REQUIREMENTS_PATH)
    decisions = read_json_path(root, DECISIONS_PATH)
    digest = hashlib.sha256((root / PLAN_PATH).read_bytes()).hexdigest()
    package_milestones = {entry["id"]: entry["milestone"].split("/") for entry in status.get("packages", []) if isinstance(entry, dict) and isinstance(entry.get("id"), str) and isinstance(entry.get("milestone"), str)}
    expected_requirements = {f"WEB-REQ-{number:03d}" for number in range(1, 61)}
    require(set(requirements) == {"plan_sha256", "requirements", "schema_version"}, "requirement register fields")
    require(type(requirements.get("schema_version")) is int and requirements["schema_version"] == 1, "requirement schema version")
    require(requirements.get("plan_sha256") == digest, "requirement plan digest")
    items = requirements.get("requirements")
    require(isinstance(items, list) and len(items) == 60, "requirement IDs")
    require(all(isinstance(item, dict) and set(item) == {"id", "milestones", "packages", "text", "verification"} for item in items), "requirement record fields")
    ids = [item.get("id") for item in items]
    require(all(isinstance(item, str) for item in ids) and set(ids) == expected_requirements and len(set(ids)) == 60, "requirement IDs")
    expected_mapping: dict[str, set[str]] = {identifier: set() for identifier in expected_requirements}
    packages = plan_packages(plan)
    for package, values in packages.items():
        for identifier in values["requirements"]:
            expected_mapping[identifier].add(package)
    for item in items:
        packages_value, milestones, verification = item["packages"], item["milestones"], item["verification"]
        require(isinstance(item["text"], str) and item["text"].strip(), "requirement text")
        require(isinstance(packages_value, list) and packages_value and all(isinstance(value, str) for value in packages_value) and set(packages_value) <= set(package_milestones), "requirement packages")
        require(set(packages_value) == expected_mapping[item["id"]], "requirement package mapping")
        require(isinstance(milestones, list) and milestones and all(isinstance(value, str) for value in milestones), "requirement milestones")
        require(set(milestones) == {milestone for package in packages_value for milestone in package_milestones[package]}, "requirement milestones")
        require(isinstance(verification, list) and verification and all(isinstance(value, str) and value.strip() for value in verification), "requirement verification")
        valid_commands = {command for package in packages_value for command in packages[package]["verification"]}
        require(set(verification) <= valid_commands, "requirement verification")
    require(read_text(root, REQUIREMENTS_DOC_PATH) == render_requirements(requirements), "requirements doc differs from requirement register")

    chapter = re.search(r"^## 20\. Aktive Architekturentscheidungen\n(.*?)(?=^## 21\.)", plan, re.MULTILINE | re.DOTALL)
    require(chapter is not None, "current ADR chapter")
    rows = re.findall(r"^\| (ADR-WEB-\d{3}) \| (.*?) \| (.*?) \| (.*?) \|$", chapter.group(1), re.MULTILINE)
    expected_rows = [(identifier, decision, status, trigger) for identifier, decision, status, trigger in rows]
    require(set(decisions) == {"current_ids", "decisions", "historical_core_ids", "plan_sha256", "schema_version"}, "ADR register fields")
    require(type(decisions.get("schema_version")) is int and decisions["schema_version"] == 1 and decisions.get("plan_sha256") == digest, "ADR schema")
    exact_set(decisions.get("current_ids"), EXPECTED_CURRENT_ADRS, "current ADR IDs")
    exact_set(decisions.get("historical_core_ids"), EXPECTED_HISTORICAL_ADRS, "historical ADR IDs")
    records = decisions.get("decisions")
    require(isinstance(records, list) and all(isinstance(item, dict) and set(item) == {"decision", "id", "reevaluation_trigger", "status"} for item in records), "current ADR rows")
    require(len(records) == 15 and [item.get("id") for item in records] == [f"ADR-WEB-{number:03d}" for number in range(1, 16)], "current ADR IDs")
    actual_rows = [(item.get("id"), item.get("decision"), item.get("status"), item.get("reevaluation_trigger")) for item in records]
    require(actual_rows == expected_rows, "current ADR rows")
    require(read_text(root, ADR_DOC_PATH) == render_adrs(decisions), "ADR doc differs from ADR register")
    require(read_text(root, PROVENANCE_PATH) == render_provenance(revisions), "provenance")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    try:
        validate(args.root)
    except ValidationError as error:
        print(f"web governance validation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
