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
FACTORY_PIN = "b00d824adee47341e3251bc18e09239fde1c5939"
PACKAGE_PATTERN = re.compile(r"^### (WEB-P\d{2}-\d{2}) – ", re.MULTILINE)
REQUIREMENT_PATTERN = re.compile(r"WEB-REQ-\d{3}")
STATUS_ROW_PATTERN = re.compile(
    r"^\| `(WEB-P\d{2}-\d{2})` \|.*?\| \*\*(.*?)\*\* \|.*?\| `(M\d{2}(?:/M\d{2})*|Pflege)` \|$",
    re.MULTILINE,
)


class ValidationError(Exception):
    pass


def fail(message: str) -> None:
    raise ValidationError(message)


def read_json(root: Path, relative: Path) -> dict:
    path = root / relative
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
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

    require(status.get("schema_version") == 1, "status schema version")
    require(supersession.get("schema_version") == 1, "supersession schema version")
    canonical = status.get("canonical_plan")
    require(isinstance(canonical, dict), "canonical plan metadata")
    require(canonical.get("document_id") == "WIRTEL-WEB-PLAN-001", "canonical document ID")
    require(canonical.get("version") == "2.0.0", "canonical plan version")
    digest = hashlib.sha256(plan_bytes).hexdigest()
    require(canonical.get("sha256") == digest, "plan digest mismatch")
    require(status.get("historical_plan_sha256") == HISTORICAL_SHA, "historical plan digest")
    require(HISTORICAL_SHA in plan, "historical plan digest inconsistent with canonical plan")

    current_plan = plan.split("# Anhang B", 1)[0]
    freeze_section = current_plan.split("### 3.1", 1)[0]
    freezes = set(re.findall(r"\| `H234598/[^`]+` \|.*?\| `main` \| `([0-9a-f]+)` \|", freeze_section))
    require(freezes == FREEZE_SHAS, "frozen repository SHA")
    require(FACTORY_PIN in current_plan, "Factory pin")
    require(status.get("archive_factory_pin") == FACTORY_PIN, "Factory pin")
    require(re.fullmatch(r"[0-9a-f]{40}", status["archive_factory_pin"]) is not None, "Factory pin")

    headings = PACKAGE_PATTERN.findall(plan)
    require(len(headings) == 48 and len(set(headings)) == 48, "historical package headings")
    expected_packages = set(headings)
    raw_rows = STATUS_ROW_PATTERN.findall(current_plan)
    rows = {package: (state, milestone) for package, state, milestone in raw_rows}
    require(len(raw_rows) == 48 and len(rows) == 48 and set(rows) == expected_packages, "plan status rows")

    packages = status.get("packages")
    require(isinstance(packages, list), "package register")
    package_ids = [entry.get("id") for entry in packages if isinstance(entry, dict)]
    require(len(package_ids) == 48 and len(set(package_ids)) == 48 and set(package_ids) == expected_packages, "package IDs")
    for entry in packages:
        require(isinstance(entry, dict), "package register")
        package_id, state, milestone = entry.get("id"), entry.get("status"), entry.get("milestone")
        require(state in STATUSES, "invalid status")
        require(isinstance(milestone, str) and all(part in MILESTONES for part in milestone.split("/")), "unknown milestone")
        require(rows[package_id] == (state, milestone), "plan/register consistency")
    for milestone in MILESTONES - {"Pflege"}:
        require(any(milestone in entry["milestone"].split("/") for entry in packages), "required milestone")

    requirements = status.get("requirements")
    expected_requirements = {f"WEB-REQ-{number:03d}" for number in range(1, 61)}
    require(isinstance(requirements, list), "requirement register")
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
    old_p00 = supersession.get("old_p00_pr")
    require(isinstance(old_p00, dict) and old_p00.get("number") == 1, "old P00 evidence")
    require(old_p00.get("github_pr_state") == "closed" and old_p00.get("github_pr_merged") is False, "old P00 evidence")
    require(old_p00.get("solution_path") == "abgelöst", "old P00 classified as implemented")
    pr4 = supersession.get("generator_pr_4")
    require(isinstance(pr4, dict), "PR #4 evidence")
    require(pr4.get("integration_commit") == "274b25c9e1f9ea97d3b060997ed5c425d2b30e9f", "PR #4 integration commit")
    require(pr4.get("commit_message_mentions_pr") == 4, "PR #4 commit message")
    require(pr4.get("github_pr_state") == "closed" and pr4.get("github_pr_merged") is False, "PR #4 classified as merged")
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
