from __future__ import annotations

import copy
import unittest

from wirtelprimpf_platform.cloudflare_aliases import load_alias_catalog
from wirtelprimpf_platform.cloudflare_preflight import (
    ALIAS_RECORD_COMMENT,
    ALIAS_RECORD_CONTENT,
    CloudflarePreflightError,
    build_alias_record_payloads,
    validate_preflight,
)
from wirtelprimpf_platform.cloudflare_snapshot import SNAPSHOT_VERSION


def valid_snapshot() -> dict:
    catalog = load_alias_catalog()
    return {
        "schema_version": SNAPSHOT_VERSION,
        "captured_at": "2026-08-05T07:00:00Z",
        "zone": "telacore.org",
        "ruleset": {
            "id": "ruleset-1",
            "version": 15,
            "security_rule_hash": "a" * 64,
            "rules": [{"ref": f"rule-{index}"} for index in range(1, 5)]
            + [{"ref": "security-rule-id", "description": "Telacore_SecurityRule1"}],
        },
        "dns_records": [
            {"id": f"record-{index}", "name": f"existing-{index}.telacore.org", "type": "A"}
            for index in range(52)
        ],
        "quota": {"used": 52, "limit": 1000},
        "alias_dns_answers": {f"{alias}.telacore.org": [] for alias in catalog.aliases},
    }


class CloudflarePreflightTests(unittest.TestCase):
    def test_preflight_accepts_complete_unchanged_baseline(self) -> None:
        report = validate_preflight(
            valid_snapshot(),
            expected_ruleset_id="ruleset-1",
            expected_ruleset_version=15,
            expected_security_rule_hash="a" * 64,
            expected_dns_record_count=52,
        )
        self.assertEqual(report.alias_count, 120)
        self.assertEqual(report.existing_rule_count, 5)
        self.assertEqual(report.dns_record_count, 52)

    def test_preflight_rejects_drift_wildcard_and_existing_alias_answer(self) -> None:
        cases: list[tuple[str, dict, str]] = []
        drifted = copy.deepcopy(valid_snapshot())
        drifted["ruleset"]["version"] = 16
        cases.append(("version", drifted, "version"))
        wildcard = copy.deepcopy(valid_snapshot())
        wildcard["dns_records"][0]["name"] = "*.telacore.org"
        cases.append(("wildcard", wildcard, "wildcard"))
        answered = copy.deepcopy(valid_snapshot())
        answered["alias_dns_answers"]["wirtelprimpf-story.telacore.org"] = ["192.0.2.1"]
        cases.append(("answer", answered, "answer"))
        for name, payload, message in cases:
            with self.subTest(name=name), self.assertRaisesRegex(CloudflarePreflightError, message):
                validate_preflight(payload, expected_ruleset_version=15)

    def test_preflight_rejects_security_order_and_inventory_drift(self) -> None:
        wrong_security = copy.deepcopy(valid_snapshot())
        wrong_security["ruleset"]["rules"][-1]["description"] = "other"
        with self.assertRaises(CloudflarePreflightError):
            validate_preflight(wrong_security)
        wrong_count = copy.deepcopy(valid_snapshot())
        wrong_count["quota"]["used"] = 53
        with self.assertRaises(CloudflarePreflightError):
            validate_preflight(wrong_count)

    def test_preflight_rejects_insufficient_remaining_dns_quota(self) -> None:
        insufficient = copy.deepcopy(valid_snapshot())
        insufficient["quota"]["limit"] = 171
        with self.assertRaisesRegex(CloudflarePreflightError, "quota"):
            validate_preflight(insufficient)

    def test_alias_payloads_are_sorted_and_have_the_approved_contract(self) -> None:
        payloads = build_alias_record_payloads()
        self.assertEqual(len(payloads), 120)
        self.assertEqual([payload["name"] for payload in payloads], sorted(payload["name"] for payload in payloads))
        self.assertTrue(all(payload["type"] == "A" for payload in payloads))
        self.assertTrue(all(payload["content"] == ALIAS_RECORD_CONTENT for payload in payloads))
        self.assertTrue(all(payload["proxied"] is True and payload["ttl"] == 1 for payload in payloads))
        self.assertTrue(all(payload["comment"] == ALIAS_RECORD_COMMENT for payload in payloads))


if __name__ == "__main__":
    unittest.main()
