#!/usr/bin/env python3
"""Fail-closed validation for revision-baseline governance."""

from __future__ import annotations

import argparse
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
    provenance = read_text(root, PROVENANCE_PATH)
    require("keine Implementierungscodes oder Assets Dritter" in provenance and "main" not in provenance, "provenance")
    for repository, (_, frozen_sha, _) in EXPECTED_REPOSITORIES.items():
        require(repository in provenance and frozen_sha in provenance, "provenance")


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
