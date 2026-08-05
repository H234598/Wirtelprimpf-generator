"""Read-only Cloudflare rollout preflight and deterministic DNS payloads."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .cloudflare_aliases import AliasCatalog, load_alias_catalog
from .cloudflare_snapshot import validate_snapshot

ALIAS_RECORD_CONTENT = "192.0.2.1"
ALIAS_RECORD_COMMENT = "Wirtelprimpf Cloudflare alias rollout v1"
SECURITY_RULE_DESCRIPTION = "Telacore_SecurityRule1"
_HASH = re.compile(r"[0-9a-f]{64}\Z")


class CloudflarePreflightError(ValueError):
    """The live read-only baseline is unsafe or has drifted."""


@dataclass(frozen=True)
class PreflightReport:
    ruleset_id: str
    ruleset_version: int
    security_rule_hash: str
    existing_rule_count: int
    dns_record_count: int
    dns_quota_limit: int
    alias_count: int


def _canonical_record_name(value: Any) -> str:
    if not isinstance(value, str):
        raise CloudflarePreflightError("DNS record name must be a string")
    return value.rstrip(".").lower()


def validate_preflight(
    snapshot: Any,
    *,
    catalog: AliasCatalog | None = None,
    expected_ruleset_id: str | None = None,
    expected_ruleset_version: int | None = None,
    expected_security_rule_hash: str | None = None,
    expected_dns_record_count: int | None = None,
) -> PreflightReport:
    active = catalog or load_alias_catalog()
    current = validate_snapshot(snapshot)
    ruleset = current["ruleset"]
    if expected_ruleset_id is not None and ruleset["id"] != expected_ruleset_id:
        raise CloudflarePreflightError("ruleset id drifted from the approved baseline")
    if expected_ruleset_version is not None and ruleset["version"] != expected_ruleset_version:
        raise CloudflarePreflightError("ruleset version drifted from the approved baseline")
    if (
        expected_security_rule_hash is not None
        and (
            not _HASH.fullmatch(expected_security_rule_hash)
            or ruleset["security_rule_hash"] != expected_security_rule_hash
        )
    ):
        raise CloudflarePreflightError("security rule hash drifted from the approved baseline")

    rules = ruleset["rules"]
    if len(rules) != 5:
        raise CloudflarePreflightError("pre-mutation ruleset must contain exactly five existing rules")
    refs = [rule.get("ref") for rule in rules]
    if any(not isinstance(ref, str) or not ref for ref in refs) or len(set(refs)) != len(refs):
        raise CloudflarePreflightError("existing rules must have unique non-empty refs")
    descriptions = [rule.get("description") for rule in rules]
    if descriptions[-1] != SECURITY_RULE_DESCRIPTION:
        raise CloudflarePreflightError("existing SecurityRule is not the final rule")

    records = current["dns_records"]
    if expected_dns_record_count is not None and len(records) != expected_dns_record_count:
        raise CloudflarePreflightError("DNS record count drifted from the approved baseline")
    record_ids: list[str] = []
    for record in records:
        record_id = record.get("id")
        if not isinstance(record_id, str) or not record_id:
            raise CloudflarePreflightError("every DNS record needs a stable read-only id")
        record_ids.append(record_id)
        if _canonical_record_name(record.get("name")) == f"*.{active.zone}":
            raise CloudflarePreflightError("wildcard DNS record already exists")
    if len(set(record_ids)) != len(record_ids):
        raise CloudflarePreflightError("DNS record ids are not unique")

    quota = current["quota"]
    if quota["used"] != len(records):
        raise CloudflarePreflightError("DNS inventory count does not match quota usage")
    if len(records) + len(active.aliases) > quota["limit"]:
        raise CloudflarePreflightError("DNS quota cannot accommodate the 120 planned alias records")

    expected_answers = {f"{alias}.{active.zone}" for alias in active.aliases}
    answers = current["alias_dns_answers"]
    if set(answers) != expected_answers:
        raise CloudflarePreflightError("alias DNS preflight does not cover exactly all 120 names")
    if any(values for values in answers.values()):
        raise CloudflarePreflightError("an alias already has a DNS answer; aborting before mutation")

    return PreflightReport(
        ruleset_id=ruleset["id"],
        ruleset_version=ruleset["version"],
        security_rule_hash=ruleset["security_rule_hash"],
        existing_rule_count=len(rules),
        dns_record_count=len(records),
        dns_quota_limit=quota["limit"],
        alias_count=len(expected_answers),
    )


def build_alias_record_payloads(catalog: AliasCatalog | None = None) -> tuple[dict[str, Any], ...]:
    active = catalog or load_alias_catalog()
    return tuple(
        {
            "type": "A",
            "name": f"{alias}.{active.zone}",
            "content": ALIAS_RECORD_CONTENT,
            "ttl": 1,
            "proxied": True,
            "comment": ALIAS_RECORD_COMMENT,
        }
        for alias in sorted(active.aliases)
    )
