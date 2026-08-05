"""Rollback sequencing based only on a private Cloudflare snapshot and IDs."""

from __future__ import annotations

from dataclasses import dataclass
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
