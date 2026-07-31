"""Fail-closed Cloudflare DNS-only CNAME provisioning."""

from __future__ import annotations

import json
import re
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

HOSTNAME_RE = re.compile(r"(?=^.{1,253}\.?$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}\.?$")


class DNSConflictError(RuntimeError):
    """A foreign or incompatible DNS record already owns the requested name."""


class CloudflareAPIError(RuntimeError):
    """Cloudflare returned an unsuccessful or malformed API response."""


class CloudflareTransport(Protocol):
    def request(self, method: str, path: str, payload: dict | None = None) -> dict: ...


def _normalize_hostname(value: str) -> str:
    candidate = value.strip().rstrip(".").lower()
    if not HOSTNAME_RE.fullmatch(candidate):
        raise ValueError(f"invalid DNS hostname: {value!r}")
    return candidate


class CloudflareDNS:
    def __init__(self, *, zone_id: str, zone_name: str, transport: CloudflareTransport) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_-]{16,64}", zone_id):
            raise ValueError("invalid Cloudflare zone ID")
        self.zone_id = zone_id
        self.zone_name = _normalize_hostname(zone_name)
        self.transport = transport

    def _records_for_name(self, name: str) -> list[dict[str, Any]]:
        query = urlencode({"name": name, "per_page": 100})
        response = self.transport.request("GET", f"/zones/{self.zone_id}/dns_records?{query}")
        if response.get("success") is not True or not isinstance(response.get("result"), list):
            raise CloudflareAPIError("Cloudflare DNS listing was unsuccessful or malformed")
        return [
            record
            for record in response["result"]
            if isinstance(record, dict) and str(record.get("name", "")).rstrip(".").lower() == name
        ]

    def ensure_cname(self, name: str, target: str, *, comment: str) -> None:
        canonical_name = _normalize_hostname(name)
        canonical_target = _normalize_hostname(target)
        if canonical_name == self.zone_name or not canonical_name.endswith(f".{self.zone_name}"):
            raise ValueError(f"DNS name must be a subdomain of {self.zone_name}: {canonical_name}")
        if canonical_name.startswith("*."):
            raise ValueError("wildcard records are forbidden")
        if len(comment) > 100:
            raise ValueError("DNS comment must not exceed 100 characters")

        existing = self._records_for_name(canonical_name)
        if existing:
            if len(existing) == 1:
                record = existing[0]
                content = str(record.get("content", "")).rstrip(".").lower()
                if record.get("type") == "CNAME" and content == canonical_target and record.get("proxied") is False:
                    return
            summary = [
                {
                    "id": record.get("id"),
                    "type": record.get("type"),
                    "name": record.get("name"),
                    "content": record.get("content"),
                    "proxied": record.get("proxied"),
                }
                for record in existing
            ]
            raise DNSConflictError(
                f"DNS name {canonical_name} is already occupied; refusing update or deletion: {summary}"
            )

        payload = {
            "type": "CNAME",
            "name": canonical_name,
            "content": canonical_target,
            "ttl": 1,
            "proxied": False,
            "comment": comment,
        }
        response = self.transport.request("POST", f"/zones/{self.zone_id}/dns_records", payload)
        if response.get("success") is not True or not isinstance(response.get("result"), dict):
            raise CloudflareAPIError(f"Cloudflare refused CNAME creation for {canonical_name}")


class CloudflareHTTPTransport:
    """Small authenticated REST transport; the token is never serialized or logged."""

    def __init__(self, api_token: str, *, timeout_seconds: int = 60) -> None:
        if not api_token or any(character.isspace() for character in api_token):
            raise ValueError("a non-empty Cloudflare API token is required")
        self._api_token = api_token
        self.timeout_seconds = timeout_seconds
        self.base_url = "https://api.cloudflare.com/client/v4"

    def request(self, method: str, path: str, payload: dict | None = None) -> dict:
        body = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
        request = Request(
            f"{self.base_url}{path}",
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {self._api_token}",
                "Content-Type": "application/json",
                "User-Agent": "Wirtelprimpf-generator/1.0",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                decoded = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            try:
                details = json.loads(exc.read().decode("utf-8"))
                errors = details.get("errors", [])
            except Exception:
                errors = []
            raise CloudflareAPIError(f"Cloudflare API returned HTTP {exc.code}: {errors}") from exc
        except (URLError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CloudflareAPIError(f"Cloudflare API request failed: {type(exc).__name__}") from exc
        if not isinstance(decoded, dict):
            raise CloudflareAPIError("Cloudflare API returned a non-object response")
        return decoded


def resolve_zone_id(transport: CloudflareTransport, zone_name: str) -> str:
    canonical = _normalize_hostname(zone_name)
    response = transport.request("GET", f"/zones?{urlencode({'name': canonical, 'status': 'active', 'per_page': 50})}")
    if response.get("success") is not True or not isinstance(response.get("result"), list):
        raise CloudflareAPIError("Cloudflare zone lookup was unsuccessful or malformed")
    matches = [
        zone
        for zone in response["result"]
        if isinstance(zone, dict) and str(zone.get("name", "")).lower() == canonical
    ]
    if len(matches) != 1 or not isinstance(matches[0].get("id"), str):
        raise CloudflareAPIError(f"expected exactly one active Cloudflare zone for {canonical}")
    return matches[0]["id"]
