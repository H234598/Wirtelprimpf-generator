"""Fail-closed planning for retiring numeric and wildcard Wirtelprimpf hosts."""

from __future__ import annotations

from dataclasses import dataclass
import copy
import re
from typing import Any

from .cloudflare_preflight import SECURITY_RULE_DESCRIPTION
from .cloudflare_snapshot import validate_snapshot

NUMERIC_RULE_REF = "wirtelprimpf-numeric-alias-v1"
NUMERIC_RULE_DESCRIPTION = "Wirtelprimpf numeric aliases 0001-9999"
_NUMERIC_HOST = re.compile(r"wirtelprimpf-[0-9]{4}\.telacore\.org", re.IGNORECASE)
_NUMERIC_HOST_CLAUSE = re.compile(
    r'\(http\.host eq "wirtelprimpf-[0-9]{4}\.telacore\.org"\)',
    re.IGNORECASE,
)
_SERVER_FIELDS = frozenset({"id", "version", "last_updated"})


class CloudflareSingleHubError(ValueError):
    """The live state cannot be retired without risking unrelated rules."""


@dataclass(frozen=True)
class SingleHubRetirementPlan:
    zone: str
    ruleset_id: str
    ruleset_version: int
    wildcard_record_id: str | None
    numeric_record_ids: tuple[str, ...]
    rules: tuple[dict[str, Any], ...]

    @property
    def deleted_record_ids(self) -> tuple[str, ...]:
        return tuple(record_id for record_id in (self.wildcard_record_id, *self.numeric_record_ids) if record_id)


def retire_numeric_security_exceptions(expression: str) -> str:
    """Remove only numeric-host clauses from the existing SecurityRule."""
    if not isinstance(expression, str) or not expression:
        raise CloudflareSingleHubError("SecurityRule expression is missing")
    updated, removed = _NUMERIC_HOST_CLAUSE.subn("", expression)
    if removed:
        # The current expression joins the clauses with `or`; clean the join
        # without changing any unrelated country, URI, cookie, or protocol term.
        updated = re.sub(r"\s+or\s+or\s+", " or ", updated)
        updated = re.sub(r"\s+or\s+\)", ")", updated)
        updated = re.sub(r"\(\s*or\s+", "(", updated)
    if _NUMERIC_HOST.search(updated):
        raise CloudflareSingleHubError("numeric host survived SecurityRule retirement")
    return updated


def _record_id_map(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for record in records:
        record_id = record.get("id")
        if not isinstance(record_id, str) or not record_id:
            raise CloudflareSingleHubError("DNS record lacks a stable id")
        if record_id in result:
            raise CloudflareSingleHubError(f"duplicate DNS record id: {record_id}")
        result[record_id] = record
    return result


def _rule_update_shape(rule: dict[str, Any]) -> dict[str, Any]:
    return {key: copy.deepcopy(value) for key, value in rule.items() if key not in _SERVER_FIELDS}


def build_single_hub_retirement_plan(snapshot: Any) -> SingleHubRetirementPlan:
    """Plan deletion of wildcard/numeric DNS and removal of the numeric rule.

    A fully retired snapshot is a validated no-op. Any partial retirement still
    fails closed so a caller cannot silently leave the DNS and ruleset split.
    """
    current = validate_snapshot(snapshot)
    records = _record_id_map(current["dns_records"])
    wildcard = [
        record for record in records.values() if str(record.get("name", "")).rstrip(".").lower() == "*.telacore.org"
    ]
    numeric_records = sorted(
        record["id"]
        for record in records.values()
        if _NUMERIC_HOST.fullmatch(str(record.get("name", "")).rstrip("."))
    )
    if not any(
        str(record.get("name", "")).rstrip(".").lower() == "wirtelprimpf.telacore.org"
        for record in records.values()
    ):
        raise CloudflareSingleHubError("canonical Wirtelprimpf hub record is missing")

    rules = current["ruleset"]["rules"]
    numeric_rules = [
        rule
        for rule in rules
        if rule.get("ref") == NUMERIC_RULE_REF or rule.get("description") == NUMERIC_RULE_DESCRIPTION
    ]
    security_rules = [rule for rule in rules if rule.get("description") == SECURITY_RULE_DESCRIPTION]
    if len(security_rules) != 1:
        raise CloudflareSingleHubError("expected exactly one Telacore_SecurityRule1")
    security_rule = security_rules[0]

    if not wildcard and not numeric_records and not numeric_rules:
        if _NUMERIC_HOST.search(str(security_rule.get("expression", ""))):
            raise CloudflareSingleHubError("retirement state is incomplete: numeric host remains in SecurityRule")
        updated_rules = []
        for rule in rules:
            shaped = _rule_update_shape(rule)
            if rule is security_rule:
                shaped["expression"] = retire_numeric_security_exceptions(str(rule.get("expression", "")))
            updated_rules.append(shaped)
        if any(rule.get("ref") == NUMERIC_RULE_REF for rule in updated_rules):
            raise CloudflareSingleHubError("numeric rule survived retirement")
        if any(_NUMERIC_HOST.search(str(rule.get("expression", ""))) for rule in updated_rules):
            raise CloudflareSingleHubError("numeric host survived ruleset retirement")
        return SingleHubRetirementPlan(
            zone=current["zone"],
            ruleset_id=current["ruleset"]["id"],
            ruleset_version=current["ruleset"]["version"],
            wildcard_record_id=None,
            numeric_record_ids=(),
            rules=tuple(updated_rules),
        )

    if len(wildcard) != 1:
        raise CloudflareSingleHubError("expected exactly one wildcard DNS record (*.telacore.org)")
    if len(numeric_rules) != 1:
        raise CloudflareSingleHubError("expected exactly one active numeric redirect rule")
    numeric_rule = numeric_rules[0]
    if numeric_rule.get("action") != "redirect":
        raise CloudflareSingleHubError("numeric rule is not a redirect rule")

    updated_rules: list[dict[str, Any]] = []
    for rule in rules:
        if rule is numeric_rule:
            continue
        shaped = _rule_update_shape(rule)
        if rule is security_rule:
            shaped["expression"] = retire_numeric_security_exceptions(str(rule.get("expression", "")))
        updated_rules.append(shaped)
    if any(rule.get("ref") == NUMERIC_RULE_REF for rule in updated_rules):
        raise CloudflareSingleHubError("numeric rule survived retirement")
    if any(_NUMERIC_HOST.search(str(rule.get("expression", ""))) for rule in updated_rules):
        raise CloudflareSingleHubError("numeric host survived ruleset retirement")

    return SingleHubRetirementPlan(
        zone=current["zone"],
        ruleset_id=current["ruleset"]["id"],
        ruleset_version=current["ruleset"]["version"],
        wildcard_record_id=wildcard[0]["id"],
        numeric_record_ids=tuple(numeric_records),
        rules=tuple(updated_rules),
    )


def ruleset_update_payload(plan: SingleHubRetirementPlan) -> dict[str, Any]:
    """Return the complete rules list required by Cloudflare's PUT contract."""
    return {"rules": [copy.deepcopy(rule) for rule in plan.rules]}
