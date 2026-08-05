"""Fail-closed local contracts for the Cloudflare alias rollout."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

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
NUMERIC_REDIRECT_EXPRESSION = (
    '(len(http.host) eq 30 and starts_with(lower(http.host), "wirtelprimpf-") '
    'and ends_with(lower(http.host), ".telacore.org") '
    'and substring(http.host, 13, 14) in {"0" "1" "2" "3" "4" "5" "6" "7" "8" "9"} '
    'and substring(http.host, 14, 15) in {"0" "1" "2" "3" "4" "5" "6" "7" "8" "9"} '
    'and substring(http.host, 15, 16) in {"0" "1" "2" "3" "4" "5" "6" "7" "8" "9"} '
    'and substring(http.host, 16, 17) in {"0" "1" "2" "3" "4" "5" "6" "7" "8" "9"} '
    'and substring(http.host, 13, 17) ne "0000")'
)
_LABEL_RE = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z")
_NUMERIC_HOST_RE = re.compile(r"\Awirtelprimpf-([0-9]{4})\.telacore\.org\Z", re.IGNORECASE)


class CloudflareAliasError(ValueError):
    """The local alias or numeric redirect contract is invalid."""


@dataclass(frozen=True)
class AliasCatalog:
    zone: str
    canonical_host: str
    group_targets: tuple[tuple[str, str], ...]
    groups: tuple[tuple[str, tuple[str, ...]], ...]
    numeric_prefix: str
    numeric_digits: int
    numeric_minimum: int
    numeric_maximum: int
    numeric_excluded: tuple[str, ...]
    redirect_status: int
    preserve_path: bool
    preserve_query: bool

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

    numeric = _require_mapping(root.get("numeric_rule"), "numeric_rule")
    expected_numeric = {
        "prefix": "wirtelprimpf-",
        "digits": 4,
        "minimum": 1,
        "maximum": 9999,
        "excluded": ["0000"],
        "redirect_status": 301,
        "preserve_path": True,
        "preserve_query": True,
    }
    if dict(numeric) != expected_numeric:
        raise CloudflareAliasError("numeric redirect rule does not match the approved contract")

    return AliasCatalog(
        zone=zone,
        canonical_host=canonical_host,
        group_targets=tuple(group_targets),
        groups=tuple(groups),
        numeric_prefix=numeric["prefix"],
        numeric_digits=numeric["digits"],
        numeric_minimum=numeric["minimum"],
        numeric_maximum=numeric["maximum"],
        numeric_excluded=tuple(numeric["excluded"]),
        redirect_status=numeric["redirect_status"],
        preserve_path=numeric["preserve_path"],
        preserve_query=numeric["preserve_query"],
    )


def load_alias_catalog(path: Path | None = None) -> AliasCatalog:
    source = path or Path(__file__).resolve().parents[1] / "config" / "cloudflare-aliases.json"
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CloudflareAliasError(f"cannot read alias catalog: {type(exc).__name__}") from exc
    return validate_alias_catalog(payload)


def numeric_alias_number(host: str, catalog: AliasCatalog | None = None) -> int | None:
    active = catalog or load_alias_catalog()
    match = _NUMERIC_HOST_RE.fullmatch(host)
    if match is None:
        return None
    value = int(match.group(1))
    if value < active.numeric_minimum or value > active.numeric_maximum:
        return None
    if match.group(1) in active.numeric_excluded:
        return None
    return value


def numeric_alias_host(number: int, catalog: AliasCatalog | None = None) -> str:
    active = catalog or load_alias_catalog()
    if number < active.numeric_minimum or number > active.numeric_maximum:
        raise CloudflareAliasError(f"numeric alias is outside 0001..9999: {number}")
    return f"{active.numeric_prefix}{number:0{active.numeric_digits}d}.{active.zone}"


def numeric_redirect_location(path: str, query: str = "", catalog: AliasCatalog | None = None) -> str:
    active = catalog or load_alias_catalog()
    if not path.startswith("/") or "\r" in path or "\n" in path:
        raise CloudflareAliasError("redirect path must be an absolute URI path")
    if query.startswith("?"):
        query = query[1:]
    if "\r" in query or "\n" in query:
        raise CloudflareAliasError("redirect query contains a forbidden newline")
    suffix = path
    if active.preserve_query and query:
        suffix += "?" + quote(query, safe="=&%/:;,@+$")
    return f"https://{active.canonical_host}{suffix}"
