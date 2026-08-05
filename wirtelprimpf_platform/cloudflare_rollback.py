"""Rollback sequencing based only on a private Cloudflare snapshot and IDs."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from .cloudflare_aliases import AliasCatalog, load_alias_catalog
from .cloudflare_snapshot import validate_snapshot

ROLLBACK_SEQUENCE = (
    "delete-wildcard-by-id",
    "wait-positive-ttl-drain-300s",
    "delete-alias-batch-by-id",
    "restore-full-ruleset",
    "verify-negative-and-canonical-smokes",
)


class CloudflareRollbackError(ValueError):
    """A rollback receipt cannot guarantee that existing state is preserved."""


@dataclass(frozen=True)
class RollbackPlan:
    wildcard_record_id: str
    alias_record_ids: tuple[str, ...]
    ruleset_id: str
    ruleset_version: int
    ruleset: tuple[dict[str, Any], ...]
    sequence: tuple[str, ...] = ROLLBACK_SEQUENCE


def rehearse_rollback(
    baseline_snapshot: Any,
    current_snapshot: Any,
    *,
    plan: RollbackPlan,
) -> dict[str, Any]:
    """Rehearse the destructive rollback in memory without Cloudflare writes."""
    baseline = validate_snapshot(baseline_snapshot)
    current = validate_snapshot(current_snapshot)
    if baseline["zone"] != current["zone"]:
        raise CloudflareRollbackError("rollback rehearsal crossed zone boundaries")
    baseline_ruleset = baseline["ruleset"]
    current_ruleset = current["ruleset"]
    if plan.ruleset_id != baseline_ruleset["id"] or plan.ruleset_version != baseline_ruleset["version"]:
        raise CloudflareRollbackError("rollback plan does not match its baseline ruleset")
    if tuple(baseline_ruleset["rules"]) != plan.ruleset:
        raise CloudflareRollbackError("rollback plan rules differ from its baseline")
    if current_ruleset["id"] != baseline_ruleset["id"]:
        raise CloudflareRollbackError("current ruleset identity differs from baseline")

    def by_id(records: list[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for record in records:
            record_id = record.get("id")
            if not isinstance(record_id, str) or not record_id:
                raise CloudflareRollbackError(f"{label} contains a record without a stable id")
            if record_id in result:
                raise CloudflareRollbackError(f"{label} contains duplicate record id {record_id}")
            result[record_id] = dict(record)
        return result

    baseline_records = by_id(baseline["dns_records"], "baseline")
    current_records = by_id(current["dns_records"], "current")
    created_ids = set(plan.alias_record_ids) | {plan.wildcard_record_id}
    expected_current_ids = set(baseline_records) | created_ids
    if set(current_records) != expected_current_ids:
        raise CloudflareRollbackError("current records do not equal baseline plus created rollback ids")
    if any(current_records[record_id] != baseline_records[record_id] for record_id in baseline_records):
        raise CloudflareRollbackError("a pre-existing DNS record drifted before rollback")

    rehearsed_records = [current_records[record_id] for record_id in baseline_records]
    if {record["id"] for record in rehearsed_records} != set(baseline_records):
        raise CloudflareRollbackError("rollback rehearsal did not remove all created records")
    if json.dumps(rehearsed_records, sort_keys=True) != json.dumps(baseline["dns_records"], sort_keys=True):
        raise CloudflareRollbackError("rollback rehearsal does not reproduce baseline DNS order/content")
    return {
        "ok": True,
        "deleted_record_count": len(created_ids),
        "restored_ruleset_version": plan.ruleset_version,
        "remaining_record_count": len(rehearsed_records),
        "baseline_ruleset_restored": True,
    }


def build_rollback_plan(
    snapshot: Any,
    *,
    wildcard_record_id: str,
    alias_record_ids: tuple[str, ...] | list[str],
    catalog: AliasCatalog | None = None,
) -> RollbackPlan:
    active = catalog or load_alias_catalog()
    current = validate_snapshot(snapshot)
    if not isinstance(wildcard_record_id, str) or not wildcard_record_id:
        raise CloudflareRollbackError("wildcard rollback requires a non-empty record id")
    aliases = tuple(alias_record_ids)
    if len(aliases) != len(active.aliases):
        raise CloudflareRollbackError("rollback must contain exactly 120 alias record ids")
    if any(not isinstance(record_id, str) or not record_id for record_id in aliases):
        raise CloudflareRollbackError("all alias rollback ids must be non-empty strings")
    if len(set(aliases)) != len(aliases):
        raise CloudflareRollbackError("alias rollback ids must be unique")

    existing_ids = {record.get("id") for record in current["dns_records"]}
    if wildcard_record_id in existing_ids or wildcard_record_id in aliases:
        raise CloudflareRollbackError("rollback id collides with existing or another created record")
    if existing_ids.intersection(aliases):
        raise CloudflareRollbackError("alias rollback id collides with an existing record")

    ruleset = current["ruleset"]
    return RollbackPlan(
        wildcard_record_id=wildcard_record_id,
        alias_record_ids=aliases,
        ruleset_id=ruleset["id"],
        ruleset_version=ruleset["version"],
        ruleset=tuple(dict(rule) for rule in ruleset["rules"]),
    )
