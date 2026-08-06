from __future__ import annotations

import copy
import unittest

from wirtelprimpf_platform.cloudflare_aliases import (
    EXPECTED_GROUPS,
    EXPECTED_GROUP_TARGETS,
    CloudflareAliasError,
    load_alias_catalog,
    validate_alias_catalog,
)


class CloudflareAliasContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = load_alias_catalog()

    def test_catalog_contains_the_four_normative_groups_and_120_unique_labels(self) -> None:
        self.assertEqual(tuple(name for name, _ in self.catalog.groups), EXPECTED_GROUPS)
        self.assertEqual(self.catalog.group_targets, EXPECTED_GROUP_TARGETS)
        self.assertEqual(self.catalog.target_for_group("desinfect"), "desinfect.telacore.org")
        self.assertEqual(len(self.catalog.aliases), 120)
        self.assertEqual(len(set(self.catalog.aliases)), 120)
        self.assertLessEqual(max(map(len, self.catalog.aliases)), 36)

    def test_catalog_rejects_duplicate_aliases_and_retired_numeric_policy(self) -> None:
        payload = {
            "schema_version": "cloudflare-alias-catalog/v1",
            "zone": self.catalog.zone,
            "canonical_host": self.catalog.canonical_host,
            "group_targets": dict(self.catalog.group_targets),
            "groups": {name: list(aliases) for name, aliases in self.catalog.groups},
        }
        duplicate = copy.deepcopy(payload)
        duplicate["groups"][EXPECTED_GROUPS[1]][0] = duplicate["groups"][EXPECTED_GROUPS[0]][0]
        with self.assertRaises(CloudflareAliasError):
            validate_alias_catalog(duplicate)
        retired_policy = copy.deepcopy(payload)
        retired_policy["numeric_rule"] = {
            "prefix": "wirtelprimpf-",
            "digits": 4,
            "minimum": 1,
            "maximum": 9999,
        }
        with self.assertRaises(CloudflareAliasError):
            validate_alias_catalog(retired_policy)
        target_drifted = copy.deepcopy(payload)
        target_drifted["group_targets"]["desinfect"] = "other.telacore.org"
        with self.assertRaises(CloudflareAliasError):
            validate_alias_catalog(target_drifted)


if __name__ == "__main__":
    unittest.main()
