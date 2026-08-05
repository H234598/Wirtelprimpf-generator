from __future__ import annotations

import copy
import unittest

from wirtelprimpf_platform.cloudflare_aliases import load_alias_catalog
from wirtelprimpf_platform.cloudflare_rollback import (
    ROLLBACK_SEQUENCE,
    CloudflareRollbackError,
    build_rollback_plan,
    rehearse_rollback,
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


class CloudflareRollbackTests(unittest.TestCase):
    def current_snapshot(self, baseline: dict, plan_ids: list[str], wildcard_id: str) -> dict:
        current = copy.deepcopy(baseline)
        current["ruleset"]["version"] = baseline["ruleset"]["version"] + 2
        current["ruleset"]["rules"].append({"ref": "created-rule"})
        current["dns_records"].extend(
            [{"id": record_id, "name": f"created-{index}.telacore.org", "type": "A"}
             for index, record_id in enumerate([*plan_ids, wildcard_id])]
        )
        current["quota"]["used"] += len(plan_ids) + 1
        return current

    def test_rollback_preserves_snapshot_ruleset_and_uses_id_only_sequence(self) -> None:
        snapshot = valid_snapshot()
        alias_ids = [f"created-alias-{index}" for index in range(120)]
        plan = build_rollback_plan(snapshot, wildcard_record_id="created-wildcard", alias_record_ids=alias_ids)
        self.assertEqual(plan.alias_record_ids, tuple(alias_ids))
        self.assertEqual(plan.ruleset_id, "ruleset-1")
        self.assertEqual(plan.ruleset_version, 15)
        self.assertEqual(plan.sequence, ROLLBACK_SEQUENCE)
        self.assertTrue(all("name" not in action for action in plan.sequence))

    def test_rollback_rejects_wrong_count_duplicates_and_preexisting_ids(self) -> None:
        snapshot = valid_snapshot()
        with self.assertRaises(CloudflareRollbackError):
            build_rollback_plan(snapshot, wildcard_record_id="created-wildcard", alias_record_ids=["one"])
        duplicate_ids = ["same"] * 120
        with self.assertRaises(CloudflareRollbackError):
            build_rollback_plan(snapshot, wildcard_record_id="created-wildcard", alias_record_ids=duplicate_ids)
        existing = [f"created-alias-{index}" for index in range(119)] + ["record-1"]
        with self.assertRaises(CloudflareRollbackError):
            build_rollback_plan(snapshot, wildcard_record_id="created-wildcard", alias_record_ids=existing)
        with self.assertRaises(CloudflareRollbackError):
            build_rollback_plan(snapshot, wildcard_record_id="record-1", alias_record_ids=[f"created-{i}" for i in range(120)])

    def test_rollback_receipt_is_not_derived_from_mutated_snapshot(self) -> None:
        snapshot = valid_snapshot()
        original_rules = copy.deepcopy(snapshot["ruleset"]["rules"])
        plan = build_rollback_plan(
            snapshot,
            wildcard_record_id="created-wildcard",
            alias_record_ids=[f"created-alias-{index}" for index in range(120)],
        )
        snapshot["ruleset"]["rules"][0]["ref"] = "changed-after-capture"
        self.assertEqual(plan.ruleset[0], original_rules[0])

    def test_rollback_rehearsal_removes_only_created_records_and_restores_baseline(self) -> None:
        baseline = valid_snapshot()
        alias_ids = [f"created-alias-{index}" for index in range(120)]
        plan = build_rollback_plan(baseline, wildcard_record_id="created-wildcard", alias_record_ids=alias_ids)
        result = rehearse_rollback(
            baseline,
            self.current_snapshot(baseline, alias_ids, "created-wildcard"),
            plan=plan,
        )
        self.assertEqual(result, {
            "ok": True,
            "deleted_record_count": 121,
            "restored_ruleset_version": 15,
            "remaining_record_count": 52,
            "baseline_ruleset_restored": True,
        })

    def test_rollback_rehearsal_rejects_foreign_record_drift(self) -> None:
        baseline = valid_snapshot()
        alias_ids = [f"created-alias-{index}" for index in range(120)]
        plan = build_rollback_plan(baseline, wildcard_record_id="created-wildcard", alias_record_ids=alias_ids)
        current = self.current_snapshot(baseline, alias_ids, "created-wildcard")
        current["dns_records"][0]["content"] = "changed"
        with self.assertRaisesRegex(CloudflareRollbackError, "pre-existing DNS record"):
            rehearse_rollback(baseline, current, plan=plan)


if __name__ == "__main__":
    unittest.main()
