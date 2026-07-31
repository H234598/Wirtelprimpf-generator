from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from wirtelprimpf_platform.admin import (
    AdminApplication,
    AdminError,
    SettingsStore,
    validate_bind_host,
)


class AdminTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.env_file = self.root / "private" / "openai.env"
        self.env_file.parent.mkdir(mode=0o700)
        self.env_file.write_text(
            "# local settings\n"
            "OPENAI_API_KEY=super-secret-value\n"
            "CLOUDFLARE_API_TOKEN=cloudflare-secret-value\n"
            "WIRTELPRIMPF_OPERANDI=story\n"
            "WIRTELPRIMPF_IMAGE_MODEL=gpt-image-2\n"
            "WIRTELPRIMPF_STORY_MODEL=gpt-5-mini\n"
            "WIRTELPRIMPF_IMAGE_SIZE=1536x1024\n"
            "WIRTELPRIMPF_OUTPUT_RESOLUTION=2k\n"
            "WIRTELPRIMPF_GENERATION_INTERVAL_MINUTES=120\n",
            encoding="utf-8",
        )
        os.chmod(self.env_file, 0o600)
        self.store = SettingsStore(self.env_file)
        self.app = AdminApplication(self.store, csrf_token="csrf-token-for-tests")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def request(
        self,
        method: str,
        path: str,
        *,
        body: dict | None = None,
        headers: dict[str, str] | None = None,
        client_host: str = "127.0.0.1",
    ):
        request_headers = {"Host": "127.0.0.1:8765", **(headers or {})}
        payload = b"" if body is None else json.dumps(body).encode("utf-8")
        return self.app.handle(method, path, request_headers, payload, client_host=client_host)

    def test_only_loopback_bind_addresses_are_accepted(self) -> None:
        self.assertEqual(validate_bind_host("127.0.0.1"), "127.0.0.1")
        self.assertEqual(validate_bind_host("::1"), "::1")
        for value in ("0.0.0.0", "::", "192.168.1.20", "localhost.example"):
            with self.subTest(value=value), self.assertRaises(AdminError):
                validate_bind_host(value)

    def test_status_and_settings_never_return_secret_material(self) -> None:
        response = self.request("GET", "/api/settings")

        self.assertEqual(response.status, 200)
        decoded = json.loads(response.body)
        serialized = json.dumps(decoded)
        self.assertNotIn("super-secret-value", serialized)
        self.assertNotIn("cloudflare-secret-value", serialized)
        self.assertTrue(decoded["secrets"]["openai_api_key_present"])
        self.assertTrue(decoded["secrets"]["cloudflare_api_token_present"])
        self.assertNotIn("OPENAI_API_KEY", decoded["settings"])

    def test_foreign_host_origin_and_client_are_rejected(self) -> None:
        foreign_host = self.request("GET", "/api/settings", headers={"Host": "attacker.invalid"})
        foreign_origin = self.request(
            "POST",
            "/api/settings",
            headers={"Origin": "https://attacker.invalid", "X-Wirtelprimpf-CSRF": "csrf-token-for-tests"},
            body={"operandi": "classic"},
        )
        foreign_client = self.request("GET", "/api/settings", client_host="192.0.2.1")

        self.assertEqual(foreign_host.status, 403)
        self.assertEqual(foreign_origin.status, 403)
        self.assertEqual(foreign_client.status, 403)

    def test_missing_csrf_keeps_previous_configuration_byte_identical(self) -> None:
        before = self.env_file.read_bytes()

        response = self.request(
            "POST",
            "/api/settings",
            headers={"Origin": "http://127.0.0.1:8765"},
            body={"operandi": "classic"},
        )

        self.assertEqual(response.status, 403)
        self.assertEqual(self.env_file.read_bytes(), before)

    def test_valid_update_is_atomic_private_validated_and_secret_stays_write_only(self) -> None:
        response = self.request(
            "POST",
            "/api/settings",
            headers={
                "Origin": "http://127.0.0.1:8765",
                "X-Wirtelprimpf-CSRF": "csrf-token-for-tests",
            },
            body={
                "operandi": "both",
                "image_model": "gpt-image-2",
                "story_model": "gpt-5-mini",
                "image_size": "1536x1024",
                "output_resolution": "4k",
                "generation_interval_minutes": 180,
                "publish_immediately": True,
                "site_title": "Wirtelprimpfs Geschichtenatelier",
                "site_intro": "Zwei Katzen, eine Möhre und ziemlich viel Unfug.",
                "openai_api_key": "replacement-secret",
                "cloudflare_api_token": "replacement-cloudflare-secret",
            },
        )

        self.assertEqual(response.status, 200)
        self.assertEqual(os.stat(self.env_file).st_mode & 0o777, 0o600)
        self.assertFalse(list(self.env_file.parent.glob("*.part")))
        raw = self.env_file.read_text(encoding="utf-8")
        self.assertIn("WIRTELPRIMPF_OPERANDI=both", raw)
        self.assertIn("WIRTELPRIMPF_OUTPUT_RESOLUTION=4k", raw)
        self.assertIn("OPENAI_API_KEY=replacement-secret", raw)
        self.assertIn("CLOUDFLARE_API_TOKEN=replacement-cloudflare-secret", raw)
        self.assertNotIn("replacement-secret", response.body)
        self.assertNotIn("replacement-cloudflare-secret", response.body)
        self.assertTrue(json.loads(response.body)["secrets"]["openai_api_key_present"])

    def test_invalid_update_is_fail_closed(self) -> None:
        before = self.env_file.read_bytes()

        response = self.request(
            "POST",
            "/api/settings",
            headers={
                "Origin": "http://127.0.0.1:8765",
                "X-Wirtelprimpf-CSRF": "csrf-token-for-tests",
            },
            body={"generation_interval_minutes": 1, "operandi": "destructive"},
        )

        self.assertEqual(response.status, 422)
        self.assertEqual(self.env_file.read_bytes(), before)

    def test_config_symlink_is_rejected(self) -> None:
        other = self.root / "other.env"
        other.write_text("OPENAI_API_KEY=do-not-touch\n", encoding="utf-8")
        link = self.root / "linked.env"
        link.symlink_to(other)

        with self.assertRaisesRegex(AdminError, "symlink"):
            SettingsStore(link).update({"operandi": "story"})
        self.assertEqual(other.read_text(encoding="utf-8"), "OPENAI_API_KEY=do-not-touch\n")

    def test_path_traversal_is_not_served(self) -> None:
        response = self.request("GET", "/../../.config/wirtelprimpf/openai.env")
        self.assertEqual(response.status, 404)
        self.assertNotIn("super-secret-value", response.body)


if __name__ == "__main__":
    unittest.main()
