from __future__ import annotations

import os
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from wirtelprimpf_platform.cloudflare_credentials import CloudflareCredentialResolver


class CloudflareCredentialTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "default.toml"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_explicit_api_token_has_precedence_without_reading_wrangler(self) -> None:
        resolver = CloudflareCredentialResolver(
            config_path=self.path,
            runner=lambda command: self.fail(f"unexpected refresh: {command}"),
        )
        self.assertEqual(resolver.resolve(explicit_token="explicit-token"), "explicit-token")

    def test_rest_api_token_requires_explicit_token_and_never_falls_back_to_oauth(self) -> None:
        resolver = CloudflareCredentialResolver(
            config_path=self.path,
            runner=lambda command: self.fail(f"unexpected refresh: {command}"),
        )
        with self.assertRaisesRegex(RuntimeError, "explicit CLOUDFLARE_API_TOKEN"):
            resolver.resolve_api_token()
        self.assertEqual(resolver.resolve_api_token(explicit_token="explicit-token"), "explicit-token")

    def test_unexpired_private_wrangler_oauth_token_is_reused(self) -> None:
        self.path.write_text(
            'oauth_token = "oauth-current"\nexpiration_time = "2099-01-01T00:00:00Z"\n',
            encoding="utf-8",
        )
        os.chmod(self.path, 0o600)
        resolver = CloudflareCredentialResolver(
            config_path=self.path,
            runner=lambda command: self.fail(f"unexpected refresh: {command}"),
        )

        token = resolver.resolve(now=datetime(2026, 7, 31, tzinfo=UTC))

        self.assertEqual(token, "oauth-current")

    def test_expired_oauth_token_is_refreshed_without_exposing_it(self) -> None:
        self.path.write_text(
            'oauth_token = "oauth-expired"\nrefresh_token = "private-refresh"\n'
            'expiration_time = "2020-01-01T00:00:00Z"\n',
            encoding="utf-8",
        )
        os.chmod(self.path, 0o600)
        calls: list[list[str]] = []

        def refresh(command: list[str]) -> None:
            calls.append(command)
            self.path.write_text(
                'oauth_token = "oauth-refreshed"\nrefresh_token = "private-refresh"\n'
                'expiration_time = "2099-01-01T00:00:00Z"\n',
                encoding="utf-8",
            )
            os.chmod(self.path, 0o600)

        token = CloudflareCredentialResolver(config_path=self.path, runner=refresh).resolve(
            now=datetime(2026, 7, 31, tzinfo=UTC)
        )

        self.assertEqual(token, "oauth-refreshed")
        self.assertEqual(calls, [["npx", "--yes", "wrangler@4.118.0", "whoami"]])


if __name__ == "__main__":
    unittest.main()
