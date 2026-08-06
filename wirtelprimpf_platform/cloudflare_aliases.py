"""Fail-closed local contracts for the Cloudflare alias rollout."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CATALOG_VERSION = "cloudflare-alias-catalog/v1"
EXPECTED_GROUPS = ("wirtelprimpf", "desinfect", "tierarztpraxis-schaffer", "cheatsheets")
EXPECTED_GROUP_TARGETS = (
    ("wirtelprimpf", "wirtelprimpf.telacore.org"),
    ("desinfect", "desinfect.telacore.org"),
    ("tierarztpraxis-schaffer", "tierarztpraxis-schaffer.telacore.org"),
    ("cheatsheets", "cheatsheets.telacore.org"),
)
ALIAS_GROUP_SIZE = 30
ALIAS_LABEL_MAX_LENGTH = 36
_LABEL_RE = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z")


class CloudflareAliasError(ValueError):
    """The local named-alias contract is invalid."""


@dataclass(frozen=True)
class AliasCatalog:
    zone: str
    canonical_host: str
    group_targets: tuple[tuple[str, str], ...]
    groups: tuple[tuple[str, tuple[str, ...]], ...]

    @property
    def aliases(self) -> tuple[str, ...]:
        return tuple(alias for _, aliases in self.groups for alias in aliases)

    def target_for_group(self, group_name: str) -> str:
        for name, target in self.group_targets:
            if name == group_name:
                return target
        raise CloudflareAliasError(f"unknown alias group: {group_name}")


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CloudflareAliasError(f"{label} must be an object")
    return value


def validate_alias_catalog(payload: Any) -> AliasCatalog:
    root = _require_mapping(payload, "catalog")
    if set(root) != {"schema_version", "zone", "canonical_host", "group_targets", "groups"}:
        raise CloudflareAliasError("catalog contains fields outside the single-hub alias contract")
    if root.get("schema_version") != CATALOG_VERSION:
        raise CloudflareAliasError("unsupported Cloudflare alias catalog version")

    zone = root.get("zone")
    canonical_host = root.get("canonical_host")
    if zone != "telacore.org" or canonical_host != "wirtelprimpf.telacore.org":
        raise CloudflareAliasError("Cloudflare alias catalog has an unexpected zone or canonical host")

    raw_targets = _require_mapping(root.get("group_targets"), "group_targets")
    if tuple(raw_targets) != EXPECTED_GROUPS:
        raise CloudflareAliasError("group targets must use the four normative groups in order")
    expected_targets = dict(EXPECTED_GROUP_TARGETS)
    group_targets: list[tuple[str, str]] = []
    for group_name in EXPECTED_GROUPS:
        target = raw_targets[group_name]
        if target != expected_targets[group_name]:
            raise CloudflareAliasError(f"unexpected redirect target for alias group: {group_name}")
        group_targets.append((group_name, target))

    raw_groups = _require_mapping(root.get("groups"), "groups")
    if tuple(raw_groups) != EXPECTED_GROUPS:
        raise CloudflareAliasError("alias groups must use the four normative groups in order")

    groups: list[tuple[str, tuple[str, ...]]] = []
    seen: set[str] = set()
    for group_name in EXPECTED_GROUPS:
        raw_aliases = raw_groups[group_name]
        if not isinstance(raw_aliases, list) or len(raw_aliases) != ALIAS_GROUP_SIZE:
            raise CloudflareAliasError(f"alias group {group_name} must contain exactly 30 labels")
        aliases: list[str] = []
        for alias in raw_aliases:
            if not isinstance(alias, str) or not _LABEL_RE.fullmatch(alias) or len(alias) > ALIAS_LABEL_MAX_LENGTH:
                raise CloudflareAliasError(f"invalid or oversized alias label: {alias!r}")
            if alias in seen:
                raise CloudflareAliasError(f"duplicate alias label: {alias}")
            seen.add(alias)
            aliases.append(alias)
        groups.append((group_name, tuple(aliases)))

    return AliasCatalog(
        zone=zone,
        canonical_host=canonical_host,
        group_targets=tuple(group_targets),
        groups=tuple(groups),
    )


def load_alias_catalog(path: Path | None = None) -> AliasCatalog:
    source = path or Path(__file__).resolve().parents[1] / "config" / "cloudflare-aliases.json"
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CloudflareAliasError(f"cannot read alias catalog: {type(exc).__name__}") from exc
    return validate_alias_catalog(payload)
