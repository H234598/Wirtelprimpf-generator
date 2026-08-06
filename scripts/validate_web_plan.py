#!/usr/bin/env python3
"""Fail-closed validation for canonical web-plan governance artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

PLAN_PATH = Path("docs/plans/WIRTELPRIMPF-WEBSEITE-IMPLEMENTIERUNGSPLAN.md")
STATUS_PATH = Path("config/web-plan-status.json")
SUPERSESSION_PATH = Path("config/web-plan-supersession.json")
STATUSES = {"umgesetzt", "teilweise umgesetzt", "in Arbeit", "offen"}
MILESTONES = {"M00", "M01", "M02", "M03", "M04", "M05", "M06", "Pflege"}
HISTORICAL_SHA = "c072535f7e2997ffd3e4ee250bf16b333819ba26fad16fcffabb6213a9f24ab3"
FREEZE_SHAS = {
    "274b25c9e1f9ea97d3b060997ed5c425d2b30e9f",
    "79274c1fef77306eb9ee0e9bd2682f4b28b74849",
    "3bed7ac358b861490727adce36a418db133f8daf",
    "ee91741ec71a1232a4c3b90f42b805591a0d9359",
    "71bcad7a8ab183144e8ff007b85aea8bb6cff3b9",
}
FACTORY_PIN = "01971ea3eed05d00a1c50a31834496f8dfab65c4"
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
PACKAGE_PATTERN = re.compile(r"^### (WEB-P\d{2}-\d{2}) – ", re.MULTILINE)
REQUIREMENT_PATTERN = re.compile(r"WEB-REQ-\d{3}")
STATUS_ROW_PATTERN = re.compile(
    r"^\| `(WEB-P\d{2}-\d{2})` \|.*?\| \*\*(.*?)\*\* \|.*?\| `(M\d{2}(?:/M\d{2})*|Pflege)` \|$",
    re.MULTILINE,
)


class ValidationError(Exception):
    pass


def unique_json_object(pairs: list[tuple[str, object]]) -> dict:
    value: dict = {}
    for key, member in pairs:
        if key in value:
            fail(f"duplicate JSON key: {key}")
        value[key] = member
    return value


def fail(message: str) -> None:
    raise ValidationError(message)


def read_json(root: Path, relative: Path) -> dict:
    path = root / relative
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=unique_json_object,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        fail(f"malformed {relative}: {error}")
    if not isinstance(value, dict):
        fail(f"malformed {relative}: object required")
    return value


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def validate(root: Path) -> None:
    plan_path = root / PLAN_PATH
    try:
        plan_bytes = plan_path.read_bytes()
        plan = plan_bytes.decode("utf-8")
    except (OSError, UnicodeDecodeError) as error:
        fail(f"malformed {PLAN_PATH}: {error}")
    status = read_json(root, STATUS_PATH)
    supersession = read_json(root, SUPERSESSION_PATH)

    require(set(status) == {
        "archive_factory_pin", "canonical_plan", "historical_plan_sha256",
        "packages", "requirements", "schema_version",
    }, "status record fields")
    require(set(supersession) == {
        "authority_order", "generator_pr_4", "legacy_web_plan", "old_p00_pr", "schema_version",
    }, "supersession record fields")
    require(type(status.get("schema_version")) is int and status["schema_version"] == 1, "status schema version")
    require(
        type(supersession.get("schema_version")) is int and supersession["schema_version"] == 2,
        "supersession schema version",
    )
    canonical = status.get("canonical_plan")
    require(
        isinstance(canonical, dict) and set(canonical) == {"document_id", "sha256", "version"},
        "canonical plan metadata",
    )
    require(canonical.get("document_id") == "WIRTEL-WEB-PLAN-001", "canonical document ID")
    require(canonical.get("version") == "2.0.0", "canonical plan version")
    digest = hashlib.sha256(plan_bytes).hexdigest()
    require(canonical.get("sha256") == digest, "plan digest mismatch")
    require(status.get("historical_plan_sha256") == HISTORICAL_SHA, "historical plan digest")
    require(HISTORICAL_SHA in plan, "historical plan digest inconsistent with canonical plan")

    current_parts = plan.split("# Anhang B", 1)
    require(len(current_parts) == 2, "current plan boundary")
    current_plan = current_parts[0]
    require(
        current_plan.count(
            "## 11. Meilenstein M01 – Factory-Pin, Hub und Archiv kontrolliert ausrollen\n\n"
            "**Status:** in Arbeit."
        ) == 1,
        "M01 milestone status",
    )
    freeze_parts = current_plan.split("### 3.1", 1)
    require(len(freeze_parts) == 2, "freeze section boundary")
    freeze_section = freeze_parts[0]
    freezes = set(re.findall(r"\| `H234598/[^`]+` \|.*?\| `main` \| `([0-9a-f]+)` \|", freeze_section))
    require(freezes == FREEZE_SHAS, "frozen repository SHA")
    # The pin is retained as historical evidence after the Single-Hub
    # decision; it no longer belongs to the active archive publication path.
    require(FACTORY_PIN in plan, "Factory pin")
    require(status.get("archive_factory_pin") == FACTORY_PIN, "Factory pin")
    require(re.fullmatch(r"[0-9a-f]{40}", status["archive_factory_pin"]) is not None, "Factory pin")

    # The historical appendix carries the detailed package headings; later
    # evidence notes are kept outside this exact title form.
    headings = PACKAGE_PATTERN.findall(plan)
    require(len(headings) == 48 and len(set(headings)) == 48, "historical package headings")
    expected_packages = set(headings)
    raw_rows = STATUS_ROW_PATTERN.findall(current_plan)
    rows = {package: (state, milestone) for package, state, milestone in raw_rows}
    require(len(raw_rows) == 48 and len(rows) == 48 and set(rows) == expected_packages, "plan status rows")

    packages = status.get("packages")
    require(isinstance(packages, list), "package register")
    require(
        all(isinstance(entry, dict) and set(entry) == {"id", "milestone", "status"} for entry in packages),
        "package register",
    )
    package_ids = [entry.get("id") for entry in packages]
    require(all(isinstance(package_id, str) for package_id in package_ids), "package IDs")
    require(len(package_ids) == 48 and len(set(package_ids)) == 48 and set(package_ids) == expected_packages, "package IDs")
    for entry in packages:
        package_id, state, milestone = entry.get("id"), entry.get("status"), entry.get("milestone")
        require(isinstance(state, str) and state in STATUSES, "invalid status")
        require(isinstance(milestone, str) and all(part in MILESTONES for part in milestone.split("/")), "unknown milestone")
        require(rows[package_id] == (state, milestone), "plan/register consistency")
    for milestone in MILESTONES - {"Pflege"}:
        require(any(milestone in entry["milestone"].split("/") for entry in packages), "required milestone")

    requirements = status.get("requirements")
    expected_requirements = {f"WEB-REQ-{number:03d}" for number in range(1, 61)}
    require(isinstance(requirements, list), "requirement register")
    require(all(isinstance(requirement, str) for requirement in requirements), "requirement IDs")
    require(len(requirements) == 60 and len(set(requirements)) == 60 and set(requirements) == expected_requirements, "requirement IDs")
    plan_requirements = REQUIREMENT_PATTERN.findall(plan)
    require(
        len(plan_requirements) == 66
        and len(set(plan_requirements)) == 60
        and set(plan_requirements) == expected_requirements,
        "plan requirement IDs",
    )

    require(supersession.get("authority_order") == [
        "v2.0.0 chapters 0-28", "approved generator and rollout plans", "v1 historical appendix"
    ], "authority order")
    require(supersession.get("legacy_web_plan") == LEGACY_WEB_PLAN, "legacy web plan supersession")
    old_p00 = supersession.get("old_p00_pr")
    require(
        isinstance(old_p00, dict)
        and set(old_p00) == {"github_pr_merged", "github_pr_state", "number", "solution_path"},
        "old P00 evidence",
    )
    require(type(old_p00.get("number")) is int and old_p00["number"] == 1, "old P00 evidence")
    require(old_p00.get("github_pr_state") == "closed" and old_p00.get("github_pr_merged") is False, "old P00 evidence")
    require(old_p00.get("solution_path") == "abgelöst", "old P00 solution path must be superseded")
    pr4 = supersession.get("generator_pr_4")
    require(
        isinstance(pr4, dict)
        and set(pr4) == {
            "commit_message_mentions_pr", "content_present_on_main", "evidence_class",
            "github_pr_merged", "github_pr_state", "integration_commit",
        },
        "PR #4 evidence",
    )
    require(pr4.get("integration_commit") == "274b25c9e1f9ea97d3b060997ed5c425d2b30e9f", "PR #4 integration commit")
    require(type(pr4.get("commit_message_mentions_pr")) is int and pr4["commit_message_mentions_pr"] == 4, "PR #4 commit message")
    require(
        pr4.get("github_pr_state") == "closed" and pr4.get("github_pr_merged") is False,
        "PR #4 must be closed and not merged",
    )
    require(pr4.get("content_present_on_main") is True, "PR #4 main evidence")
    require(pr4.get("evidence_class") == "manual-main-integration", "PR #4 evidence class")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    try:
        validate(args.root)
    except ValidationError as error:
        print(f"web plan validation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
