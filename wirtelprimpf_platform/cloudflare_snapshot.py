"""Private, redacted Cloudflare read-only snapshot contracts."""

from __future__ import annotations

import hashlib
import json
import re
import stat
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .settings_io import SecureFile, SettingsIOError

SNAPSHOT_VERSION = "cloudflare-readonly-snapshot/v1"
_ISO_TIMESTAMP = re.compile(r"\A\d{4}-\d{2}-\d{2}T[^\r\n]+\Z")
_FORBIDDEN_KEY_PARTS = (
    "authorization",
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "refresh",
    "cookie",
)


class CloudflareSnapshotError(ValueError):
    """A snapshot is malformed or contains credential material."""


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CloudflareSnapshotError(f"{label} must be an object")
    return value


def _reject_credentials(value: Any, path: str = "snapshot") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise CloudflareSnapshotError(f"{path} contains a non-string key")
            lowered = key.lower()
            if any(part in lowered for part in _FORBIDDEN_KEY_PARTS):
                raise CloudflareSnapshotError(f"credential-like field is forbidden: {path}.{key}")
            _reject_credentials(child, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _reject_credentials(child, f"{path}[{index}]")
        return
    if isinstance(value, str):
        lowered = value.lower()
        if "bearer " in lowered or "authorization:" in lowered:
            raise CloudflareSnapshotError("authorization material is forbidden in snapshots")


def validate_snapshot(payload: Any) -> dict[str, Any]:
    root = _mapping(payload, "snapshot")
    _reject_credentials(root)
    expected = {"schema_version", "captured_at", "zone", "ruleset", "dns_records", "quota", "alias_dns_answers"}
    if set(root) != expected:
        raise CloudflareSnapshotError("snapshot fields are incomplete or unknown")
    if root["schema_version"] != SNAPSHOT_VERSION:
        raise CloudflareSnapshotError("unsupported Cloudflare snapshot version")
    if not isinstance(root["captured_at"], str) or not _ISO_TIMESTAMP.fullmatch(root["captured_at"]):
        raise CloudflareSnapshotError("snapshot captured_at must be an ISO-like timestamp")
    if root["zone"] != "telacore.org":
        raise CloudflareSnapshotError("snapshot zone is not telacore.org")

    ruleset = _mapping(root["ruleset"], "ruleset")
    if set(ruleset) != {"id", "version", "security_rule_hash", "rules"}:
        raise CloudflareSnapshotError("ruleset snapshot fields are incomplete or unknown")
    if not isinstance(ruleset["id"], str) or not ruleset["id"]:
        raise CloudflareSnapshotError("ruleset id is required")
    if not isinstance(ruleset["version"], int) or ruleset["version"] < 1:
        raise CloudflareSnapshotError("ruleset version is invalid")
    if (
        not isinstance(ruleset["security_rule_hash"], str)
        or not re.fullmatch(r"[0-9a-f]{64}", ruleset["security_rule_hash"])
    ):
        raise CloudflareSnapshotError("security rule hash is invalid")
    if not isinstance(ruleset["rules"], list) or not all(isinstance(rule, Mapping) for rule in ruleset["rules"]):
        raise CloudflareSnapshotError("ruleset rules must be a list of objects")

    records = root["dns_records"]
    if not isinstance(records, list) or not all(isinstance(record, Mapping) for record in records):
        raise CloudflareSnapshotError("dns_records must be a list of objects")
    quota = _mapping(root["quota"], "quota")
    if set(quota) != {"used", "limit"} or not all(isinstance(quota[key], int) for key in ("used", "limit")):
        raise CloudflareSnapshotError("quota must contain integer used and limit")
    if quota["used"] < 0 or quota["limit"] < quota["used"]:
        raise CloudflareSnapshotError("quota values are inconsistent")

    answers = _mapping(root["alias_dns_answers"], "alias_dns_answers")
    for name, values in answers.items():
        if (
            not isinstance(name, str)
            or not isinstance(values, list)
            or not all(isinstance(value, str) for value in values)
        ):
            raise CloudflareSnapshotError("alias DNS answers must map names to string lists")
    return json.loads(json.dumps(root, sort_keys=True))


def _canonical_bytes(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def write_snapshot(path: Path, payload: Any) -> str:
    validated = validate_snapshot(payload)
    content = _canonical_bytes(validated)
    try:
        SecureFile(Path(path), private=True).replace_bytes(content)
    except SettingsIOError as exc:
        raise CloudflareSnapshotError("cannot atomically write private Cloudflare snapshot") from exc
    return hashlib.sha256(content).hexdigest()


def read_snapshot(path: Path) -> tuple[dict[str, Any], str]:
    target = Path(path)
    try:
        metadata = target.stat()
    except OSError as exc:
        raise CloudflareSnapshotError("cannot inspect private Cloudflare snapshot") from exc
    if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600:
        raise CloudflareSnapshotError("private Cloudflare snapshot must be a regular mode-0600 file")
    try:
        content = SecureFile(target, private=True).read_bytes()
    except SettingsIOError as exc:
        raise CloudflareSnapshotError("cannot read private Cloudflare snapshot") from exc
    if not content:
        raise CloudflareSnapshotError("private Cloudflare snapshot is empty")
    try:
        payload = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CloudflareSnapshotError("private Cloudflare snapshot is not valid UTF-8 JSON") from exc
    return validate_snapshot(payload), hashlib.sha256(content).hexdigest()
