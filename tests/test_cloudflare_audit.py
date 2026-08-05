from __future__ import annotations

import unittest
from datetime import UTC, datetime
from urllib.parse import parse_qs, urlparse

from wirtelprimpf_platform.cloudflare_audit import (
    RULESET_PHASE,
    CloudflareAuditError,
    collect_snapshot,
)
from wirtelprimpf_platform.cloudflare_aliases import load_alias_catalog


class FakeTransport:
    def __init__(self, *, rulesets: list[dict] | None = None, dns_pages: list[list[dict]] | None = None) -> None:
        self.rulesets = rulesets if rulesets is not None else [
            {
                "id": "ruleset-1",
                "phase": RULESET_PHASE,
                "version": "15",
                "rules": [{"ref": f"rule-{i}"} for i in range(1, 5)]
                + [{"ref": "security-rule-id", "description": "Telacore_SecurityRule1", "expression": "true"}],
            }
        ]
        self.dns_pages = dns_pages if dns_pages is not None else [
            [{"id": "record-1", "name": "existing.telacore.org", "type": "A", "content": "192.0.2.2"}]
        ]
        self.calls: list[tuple[str, str]] = []

    def request(self, method: str, path: str, payload: dict | None = None) -> dict:
        del payload
        self.calls.append((method, path))
        if path.startswith("/zones?"):
            return {"success": True, "result": [{"id": "zone-1", "name": "telacore.org"}]}
        if path == "/zones/zone-1/rulesets":
            return {
                "success": True,
                "result": [{key: value for key, value in ruleset.items() if key not in {"rules"}} for ruleset in self.rulesets],
            }
        if path.startswith("/zones/zone-1/rulesets/"):
            ruleset_id = path.rsplit("/", 1)[-1]
            for ruleset in self.rulesets:
                if ruleset.get("id") == ruleset_id:
                    return {"success": True, "result": ruleset}
            raise AssertionError(f"unknown ruleset: {ruleset_id}")
        if path.startswith("/zones/zone-1/dns_records?"):
            page = int(parse_qs(urlparse(path).query)["page"][0])
            records = self.dns_pages[page - 1] if page <= len(self.dns_pages) else []
            return {
                "success": True,
                "result": records,
                "result_info": {"page": page, "total_pages": len(self.dns_pages)},
            }
        raise AssertionError(f"unexpected request: {method} {path}")


class CloudflareAuditTests(unittest.TestCase):
    def test_collects_paginated_dns_and_ruleset_into_validated_snapshot(self) -> None:
        transport = FakeTransport(
            dns_pages=[
                [{"id": "record-1", "name": "existing.telacore.org", "type": "A", "content": "192.0.2.2"}],
                [{"id": "record-2", "name": "other.telacore.org", "type": "AAAA", "content": "2001:db8::1"}],
            ]
        )
        snapshot = collect_snapshot(
            transport,
            captured_at=datetime(2026, 8, 5, 7, 0, tzinfo=UTC),
        )
        self.assertEqual(snapshot["ruleset"]["id"], "ruleset-1")
        self.assertEqual(snapshot["ruleset"]["version"], 15)
        self.assertEqual(snapshot["quota"], {"used": 2, "limit": 1000})
        self.assertEqual(len(snapshot["alias_dns_answers"]), 120)
        self.assertEqual(len(snapshot["dns_records"]), 2)
        self.assertEqual(snapshot["captured_at"], "2026-08-05T07:00:00Z")

    def test_rejects_ambiguous_rulesets_and_missing_security_rule(self) -> None:
        for rulesets in (
            [],
            [{"id": "one", "phase": RULESET_PHASE, "version": 1, "rules": []}, {"id": "two", "phase": RULESET_PHASE, "version": 2, "rules": []}],
            [{"id": "one", "phase": RULESET_PHASE, "version": 1, "rules": [{"ref": "other"}]}],
        ):
            with self.subTest(rulesets=rulesets), self.assertRaises(CloudflareAuditError):
                collect_snapshot(FakeTransport(rulesets=rulesets))

    def test_rejects_dns_records_without_stable_identity(self) -> None:
        with self.assertRaises(CloudflareAuditError):
            collect_snapshot(FakeTransport(dns_pages=[[{"name": "bad.telacore.org", "type": "A"}]]))


if __name__ == "__main__":
    unittest.main()
