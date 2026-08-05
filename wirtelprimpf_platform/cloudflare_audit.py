"""Read-only Cloudflare zone audit that produces the private snapshot shape."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

from .cloudflare_aliases import AliasCatalog, load_alias_catalog
from .cloudflare_dns import CloudflareAPIError, CloudflareTransport, resolve_zone_id
from .cloudflare_preflight import SECURITY_RULE_DESCRIPTION
from .cloudflare_snapshot import SNAPSHOT_VERSION, validate_snapshot

RULESET_PHASE = "http_request_dynamic_redirect"
DNS_QUOTA_LIMIT = 1000


class CloudflareAuditError(RuntimeError):
    """Cloudflare read-only state is unavailable or ambiguous."""


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _success_list(response: dict[str, Any], label: str) -> list[dict[str, Any]]:
    if response.get("success") is not True or not isinstance(response.get("result"), list):
        raise CloudflareAuditError(f"Cloudflare {label} response was unsuccessful or malformed")
    result = response["result"]
    if not all(isinstance(item, dict) for item in result):
        raise CloudflareAuditError(f"Cloudflare {label} result contains non-object entries")
    return result


def _success_object(response: dict[str, Any], label: str) -> dict[str, Any]:
    if response.get("success") is not True or not isinstance(response.get("result"), dict):
        raise CloudflareAuditError(f"Cloudflare {label} response was unsuccessful or malformed")
    return response["result"]


def _read_all_dns_records(transport: CloudflareTransport, zone_id: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    page = 1
    while True:
        query = urlencode({"per_page": 100, "page": page})
        try:
            response = transport.request("GET", f"/zones/{zone_id}/dns_records?{query}")
        except CloudflareAPIError as exc:
            raise CloudflareAuditError("Cloudflare DNS record lookup failed") from exc
        records.extend(_success_list(response, "DNS record"))
        result_info = response.get("result_info")
        if not isinstance(result_info, dict):
            raise CloudflareAuditError("Cloudflare DNS response lacks pagination metadata")
        try:
            total_pages = int(result_info["total_pages"])
        except (KeyError, TypeError, ValueError) as exc:
            raise CloudflareAuditError("Cloudflare DNS pagination metadata is invalid") from exc
        if total_pages < page:
            raise CloudflareAuditError("Cloudflare DNS pagination moved backwards")
        if page == total_pages:
            return records
        page += 1


def _minimal_dns_record(record: dict[str, Any]) -> dict[str, Any]:
    allowed = ("id", "name", "type", "content", "ttl", "proxied", "comment", "priority", "data")
    minimal = {key: record[key] for key in allowed if key in record}
    if not isinstance(minimal.get("id"), str) or not minimal["id"]:
        raise CloudflareAuditError("Cloudflare DNS record lacks a stable id")
    if not isinstance(minimal.get("name"), str) or not minimal["name"]:
        raise CloudflareAuditError("Cloudflare DNS record lacks a name")
    if not isinstance(minimal.get("type"), str) or not minimal["type"]:
        raise CloudflareAuditError("Cloudflare DNS record lacks a type")
    return minimal


def collect_snapshot(
    transport: CloudflareTransport,
    *,
    zone_name: str = "telacore.org",
    catalog: AliasCatalog | None = None,
    captured_at: datetime | None = None,
) -> dict[str, Any]:
    active = catalog or load_alias_catalog()
    try:
        zone_id = resolve_zone_id(transport, zone_name)
    except CloudflareAPIError as exc:
        raise CloudflareAuditError("Cloudflare zone lookup failed") from exc
    records = _read_all_dns_records(transport, zone_id)
    try:
        rulesets_response = transport.request("GET", f"/zones/{zone_id}/rulesets")
    except CloudflareAPIError as exc:
        raise CloudflareAuditError("Cloudflare ruleset lookup failed") from exc
    rulesets = _success_list(rulesets_response, "ruleset")
    candidates = [ruleset for ruleset in rulesets if ruleset.get("phase") == RULESET_PHASE]
    if len(candidates) != 1:
        raise CloudflareAuditError("expected exactly one Dynamic Redirect ruleset")
    ruleset_id = candidates[0].get("id")
    if not isinstance(ruleset_id, str) or not ruleset_id:
        raise CloudflareAuditError("Dynamic Redirect ruleset identity is invalid")
    try:
        ruleset_response = transport.request("GET", f"/zones/{zone_id}/rulesets/{ruleset_id}")
    except CloudflareAPIError as exc:
        raise CloudflareAuditError("Cloudflare ruleset detail lookup failed") from exc
    ruleset = _success_object(ruleset_response, "ruleset detail")
    rules = ruleset.get("rules")
    if not isinstance(rules, list) or not all(isinstance(rule, dict) for rule in rules):
        raise CloudflareAuditError("Dynamic Redirect ruleset lacks a valid rules list")
    security_rules = [rule for rule in rules if rule.get("description") == SECURITY_RULE_DESCRIPTION]
    if len(security_rules) != 1:
        raise CloudflareAuditError("expected exactly one SecurityRule in Dynamic Redirect ruleset")
    raw_version = ruleset.get("version")
    try:
        version = int(raw_version)
    except (TypeError, ValueError) as exc:
        raise CloudflareAuditError("Dynamic Redirect ruleset version is invalid") from exc
    if not isinstance(ruleset_id, str) or not ruleset_id or version < 1:
        raise CloudflareAuditError("Dynamic Redirect ruleset identity is invalid")

    minimal_records = [_minimal_dns_record(record) for record in records]
    answers = {
        f"{alias}.{active.zone}": [
            record.get("content", "")
            for record in minimal_records
            if str(record["name"]).rstrip(".").lower() == f"{alias}.{active.zone}"
        ]
        for alias in active.aliases
    }
    timestamp = (captured_at or datetime.now(UTC)).astimezone(UTC).isoformat().replace("+00:00", "Z")
    snapshot = {
        "schema_version": SNAPSHOT_VERSION,
        "captured_at": timestamp,
        "zone": zone_name,
        "ruleset": {
            "id": ruleset_id,
            "version": version,
            "security_rule_hash": hashlib.sha256(_canonical_json(security_rules[0])).hexdigest(),
            "rules": rules,
        },
        "dns_records": minimal_records,
        "quota": {"used": len(minimal_records), "limit": DNS_QUOTA_LIMIT},
        "alias_dns_answers": answers,
    }
    try:
        return validate_snapshot(snapshot)
    except ValueError as exc:
        raise CloudflareAuditError("collected Cloudflare snapshot failed local validation") from exc
