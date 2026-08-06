from __future__ import annotations

import copy
import unittest

from wirtelprimpf_platform.cloudflare_aliases import load_alias_catalog
from wirtelprimpf_platform.cloudflare_single_hub import (
    NUMERIC_RULE_REF,
    CloudflareSingleHubError,
    build_single_hub_retirement_plan,
    retire_numeric_security_exceptions,
    ruleset_update_payload,
)
from wirtelprimpf_platform.cloudflare_snapshot import SNAPSHOT_VERSION


def live_like_snapshot() -> dict:
    catalog = load_alias_catalog()
    return {
        "schema_version": SNAPSHOT_VERSION,
        "captured_at": "2026-08-06T01:00:00Z",
        "zone": "telacore.org",
        "ruleset": {
            "id": "ruleset-1",
            "version": 20,
            "security_rule_hash": "a" * 64,
            "rules": [
                {"id": "rule-1", "version": 1, "last_updated": "now", "ref": "redirect-1", "action": "redirect", "expression": "http.host eq \"wirtel.telacore.org\""},
                {"id": "rule-2", "version": 1, "last_updated": "now", "ref": "redirect-2", "action": "redirect", "expression": "http.host eq \"primpf.telacore.org\""},
                {"id": "rule-3", "version": 1, "last_updated": "now", "ref": "redirect-3", "action": "redirect", "expression": "http.host eq \"katzen.telacore.org\""},
                {"id": "rule-4", "version": 1, "last_updated": "now", "ref": NUMERIC_RULE_REF, "description": "Wirtelprimpf numeric aliases 0001-9999", "action": "redirect", "expression": "http.host eq \"wirtelprimpf-0001.telacore.org\""},
                {"id": "rule-5", "version": 1, "last_updated": "now", "ref": "security", "description": "Telacore_SecurityRule1", "action": "redirect", "expression": 'not ((http.host eq "wirtelprimpf.telacore.org") or (http.host eq "wirtelprimpf-0001.telacore.org") or (http.host eq "catgpt.wirtelprimpf.telacore.org")) or (ip.geoip.country eq "RU")'},
            ],
        },
        "dns_records": [
            {"id": "hub", "name": "wirtelprimpf.telacore.org", "type": "CNAME", "content": "h234598.github.io"},
            {"id": "wildcard", "name": "*.telacore.org", "type": "A", "content": "192.0.2.1"},
            {"id": "archive-0001", "name": "wirtelprimpf-0001.telacore.org", "type": "CNAME", "content": "h234598.github.io"},
            {"id": "other", "name": "unrelated.telacore.org", "type": "A", "content": "192.0.2.2"},
        ],
        "quota": {"used": 4, "limit": 1000},
        "alias_dns_answers": {f"{alias}.telacore.org": [] for alias in catalog.aliases},
    }


class CloudflareSingleHubTests(unittest.TestCase):
    def test_plan_removes_only_wildcard_numeric_records_and_rule(self) -> None:
        snapshot = live_like_snapshot()
        original = copy.deepcopy(snapshot)
        plan = build_single_hub_retirement_plan(snapshot)

        self.assertEqual(plan.wildcard_record_id, "wildcard")
        self.assertEqual(plan.numeric_record_ids, ("archive-0001",))
        self.assertEqual(plan.deleted_record_ids, ("wildcard", "archive-0001"))
        self.assertEqual(len(plan.rules), 4)
        self.assertFalse(any(rule.get("ref") == NUMERIC_RULE_REF for rule in plan.rules))
        security = plan.rules[-1]
        self.assertNotIn("wirtelprimpf-0001.telacore.org", security["expression"])
        self.assertIn("ip.geoip.country eq \"RU\"", security["expression"])
        self.assertEqual(snapshot, original)

        payload = ruleset_update_payload(plan)
        self.assertTrue(all("id" not in rule and "version" not in rule for rule in payload["rules"]))

    def test_security_exception_removal_preserves_other_terms(self) -> None:
        expression = 'not ((http.host eq "wirtelprimpf.telacore.org") or (http.host eq "wirtelprimpf-0001.telacore.org") or (http.host eq "catgpt.wirtelprimpf.telacore.org")) or (http.cookie eq "1337")'
        updated = retire_numeric_security_exceptions(expression)
        self.assertNotIn("wirtelprimpf-0001", updated)
        self.assertIn("catgpt.wirtelprimpf.telacore.org", updated)
        self.assertIn("http.cookie eq \"1337\"", updated)

    def test_plan_rejects_missing_wildcard_or_numeric_rule(self) -> None:
        no_wildcard = live_like_snapshot()
        no_wildcard["dns_records"] = [record for record in no_wildcard["dns_records"] if record["id"] != "wildcard"]
        no_wildcard["quota"]["used"] = 3
        with self.assertRaisesRegex(CloudflareSingleHubError, "wildcard"):
            build_single_hub_retirement_plan(no_wildcard)

        no_rule = live_like_snapshot()
        no_rule["ruleset"]["rules"] = [rule for rule in no_rule["ruleset"]["rules"] if rule.get("ref") != NUMERIC_RULE_REF]
        with self.assertRaisesRegex(CloudflareSingleHubError, "numeric redirect"):
            build_single_hub_retirement_plan(no_rule)


if __name__ == "__main__":
    unittest.main()
