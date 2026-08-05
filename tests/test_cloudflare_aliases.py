from __future__ import annotations

import copy
import unittest

from wirtelprimpf_platform.cloudflare_aliases import (
    EXPECTED_GROUPS,
    NUMERIC_REDIRECT_EXPRESSION,
    CloudflareAliasError,
    load_alias_catalog,
    numeric_alias_host,
    numeric_alias_number,
    numeric_redirect_location,
    validate_alias_catalog,
)


class CloudflareAliasContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = load_alias_catalog()

    def test_catalog_contains_the_four_normative_groups_and_120_unique_labels(self) -> None:
        self.assertEqual(tuple(name for name, _ in self.catalog.groups), EXPECTED_GROUPS)
        self.assertEqual(len(self.catalog.aliases), 120)
        self.assertEqual(len(set(self.catalog.aliases)), 120)
        self.assertLessEqual(max(map(len, self.catalog.aliases)), 36)

    def test_numeric_rule_accepts_exactly_0001_to_9999(self) -> None:
        accepted = [numeric_alias_number(numeric_alias_host(number, self.catalog), self.catalog) for number in range(1, 10_000)]
        self.assertEqual(accepted, list(range(1, 10_000)))
        for host in (
            "wirtelprimpf-0000.telacore.org",
            "wirtelprimpf-10000.telacore.org",
            "wirtelprimpf-001.telacore.org",
            "wirtelprimpf-abcd.telacore.org",
            "wirtelprimpf-0001.example.org",
            "wirtelprimpf-0001.telacore.org.",
            "wirtelprimpf-0001.telacore.org/path",
        ):
            with self.subTest(host=host):
                self.assertIsNone(numeric_alias_number(host, self.catalog))
        self.assertEqual(numeric_alias_number("WIRTELPRIMPF-0042.TELACORE.ORG", self.catalog), 42)

    def test_numeric_expression_and_redirect_preserve_the_approved_contract(self) -> None:
        self.assertIn('substring(http.host, 13, 17) ne "0000"', NUMERIC_REDIRECT_EXPRESSION)
        self.assertIn('lower(http.host)', NUMERIC_REDIRECT_EXPRESSION)
        self.assertEqual(
            numeric_redirect_location("/bilder/cat-1/", "utm_source=rollout", self.catalog),
            "https://wirtelprimpf.telacore.org/bilder/cat-1/?utm_source=rollout",
        )
        self.assertEqual(numeric_redirect_location("/", "?a=1", self.catalog), "https://wirtelprimpf.telacore.org/?a=1")

    def test_catalog_rejects_duplicate_aliases_and_numeric_drift(self) -> None:
        payload = {
            "schema_version": "cloudflare-alias-catalog/v1",
            "zone": self.catalog.zone,
            "canonical_host": self.catalog.canonical_host,
            "groups": {name: list(aliases) for name, aliases in self.catalog.groups},
            "numeric_rule": {
                "prefix": self.catalog.numeric_prefix,
                "digits": self.catalog.numeric_digits,
                "minimum": self.catalog.numeric_minimum,
                "maximum": self.catalog.numeric_maximum,
                "excluded": list(self.catalog.numeric_excluded),
                "redirect_status": self.catalog.redirect_status,
                "preserve_path": self.catalog.preserve_path,
                "preserve_query": self.catalog.preserve_query,
            },
        }
        duplicate = copy.deepcopy(payload)
        duplicate["groups"][EXPECTED_GROUPS[1]][0] = duplicate["groups"][EXPECTED_GROUPS[0]][0]
        with self.assertRaises(CloudflareAliasError):
            validate_alias_catalog(duplicate)
        drifted = copy.deepcopy(payload)
        drifted["numeric_rule"]["maximum"] = 9998
        with self.assertRaises(CloudflareAliasError):
            validate_alias_catalog(drifted)

    def test_redirect_location_rejects_header_injection(self) -> None:
        with self.assertRaises(CloudflareAliasError):
            numeric_redirect_location("/ok\nLocation: https://evil.example", catalog=self.catalog)
        with self.assertRaises(CloudflareAliasError):
            numeric_redirect_location("/ok", "a=1\r\n", self.catalog)


if __name__ == "__main__":
    unittest.main()
