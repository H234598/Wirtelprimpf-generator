from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from wirtelprimpf_platform.admin import (
    SECURITY_HEADERS,
    AdminApplication,
    AdminError,
    _Handler,
    validate_bind_host,
)
from wirtelprimpf_platform.settings import (
    SettingsApplyFailure,
    SettingsConflict,
    SettingsLockBusy,
    SettingsManager,
    SettingsPaths,
    SettingsValidationFailure,
)
from wirtelprimpf_platform.systemd_user import TimerConfiguration, TimerObservation


class FakeSystemd:
    def __init__(self) -> None:
        self.configuration = TimerConfiguration(True, 120, 120, True)

    def observe_timer(self) -> TimerObservation:
        return TimerObservation.from_configuration(self.configuration, active=True)

    def apply_timer(self, configuration: TimerConfiguration) -> TimerObservation:
        self.configuration = configuration
        return TimerObservation.from_configuration(configuration, active=configuration.enabled)

    def restore_timer(
        self,
        configuration: TimerConfiguration,
        was_active: bool,
        dropin_backup: object | None = None,
    ) -> TimerObservation:
        self.configuration = configuration
        return TimerObservation.from_configuration(configuration, active=was_active)


class FakeStatusCollector:
    def collect(self) -> dict[str, object]:
        return {
            "schema_version": "1.0.0",
            "health": "ok",
            "generator": {"active_state": "inactive"},
            "timer": {"interval_minutes": 120},
        }


class RaisingSettingsManager:
    def __init__(self, failure: Exception) -> None:
        self.failure = failure

    def apply(self, request):
        raise self.failure


class AdminTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.paths = SettingsPaths.for_home(self.root)
        self.env_file = self.paths.env_file
        self.env_file.parent.mkdir(parents=True, mode=0o700)
        self.env_file.write_text(
            "# local settings\n"
            "OPENAI_API_KEY=super-secret-value\n"
            "WIRTELPRIMPF_OPERANDI=story\n"
            "WIRTELPRIMPF_IMAGE_MODEL=gpt-image-2\n"
            "WIRTELPRIMPF_STORY_MODEL=gpt-5-mini\n"
            "WIRTELPRIMPF_IMAGE_SIZE=1536x1024\n"
            "WIRTELPRIMPF_OUTPUT_RESOLUTION=2k\n"
            "WIRTELPRIMPF_GENERATION_INTERVAL_MINUTES=120\n",
            encoding="utf-8",
        )
        os.chmod(self.env_file, 0o600)
        self.paths.cloudflare_token_file.parent.mkdir(parents=True, mode=0o700)
        self.paths.cloudflare_token_file.write_text(
            "CLOUDFLARE_API_TOKEN=cloudflare-secret-value\n",
            encoding="utf-8",
        )
        os.chmod(self.paths.cloudflare_token_file, 0o600)
        self.manager = SettingsManager(
            self.paths,
            systemd=FakeSystemd(),
            validator=lambda values: None,
        )
        self.status_collector = FakeStatusCollector()
        self.app = AdminApplication(
            self.manager,
            self.status_collector,
            csrf_token="csrf-token-for-tests",
        )

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

    def test_status_is_structurally_independent_from_settings(self) -> None:
        settings = json.loads(self.request("GET", "/api/settings").body)
        status = json.loads(self.request("GET", "/api/status").body)
        self.assertEqual(settings["schema_version"], "2.0.0")
        self.assertIn("revision", settings)
        self.assertIn("settings", settings)
        self.assertNotIn("generator", settings)
        self.assertEqual(status["schema_version"], "1.0.0")
        self.assertIn("generator", status)
        self.assertIn("timer", status)
        self.assertNotIn("settings", status)

    def test_settings_never_return_secret_material(self) -> None:
        decoded = json.loads(self.request("GET", "/api/settings").body)
        serialized = json.dumps(decoded)
        self.assertNotIn("super-secret-value", serialized)
        self.assertNotIn("cloudflare-secret-value", serialized)
        self.assertTrue(decoded["secrets"]["openai_api_key_present"])
        self.assertTrue(decoded["secrets"]["cloudflare_api_token_present"])
        self.assertNotIn("OPENAI_API_KEY", decoded["settings"])
        self.assertEqual(decoded["invariants"]["stories_per_book"], 10)
        self.assertEqual(decoded["invariants"]["books_per_archive"], 5)

    def test_sparse_update_requires_revision_and_returns_fresh_snapshot(self) -> None:
        base = json.loads(self.request("GET", "/api/settings").body)
        response = self.request(
            "POST",
            "/api/settings",
            headers={
                "Origin": "http://127.0.0.1:8765",
                "X-Wirtelprimpf-CSRF": "csrf-token-for-tests",
            },
            body={
                "base_revision": base["revision"],
                "changes": {"operandi": "both"},
                "base_values": {"operandi": base["settings"]["operandi"]},
                "secret_actions": {},
            },
        )
        decoded = json.loads(response.body)
        self.assertEqual(response.status, 200)
        self.assertEqual(decoded["settings"]["operandi"], "both")
        self.assertNotEqual(decoded["revision"], base["revision"])

    def test_same_field_conflict_is_409_and_returns_public_snapshot(self) -> None:
        base = json.loads(self.request("GET", "/api/settings").body)
        self.env_file.write_text(
            self.env_file.read_text(encoding="utf-8").replace(
                "WIRTELPRIMPF_OPERANDI=story",
                "WIRTELPRIMPF_OPERANDI=classic",
            ),
            encoding="utf-8",
        )
        response = self.request(
            "POST",
            "/api/settings",
            headers={
                "Origin": "http://127.0.0.1:8765",
                "X-Wirtelprimpf-CSRF": "csrf-token-for-tests",
            },
            body={
                "base_revision": base["revision"],
                "changes": {"operandi": "both"},
                "base_values": {"operandi": "story"},
                "secret_actions": {},
            },
        )
        decoded = json.loads(response.body)
        self.assertEqual(response.status, 409)
        self.assertEqual(decoded["conflicts"], ["operandi"])
        self.assertEqual(decoded["snapshot"]["settings"]["operandi"], "classic")

    def test_validation_lock_and_apply_failures_have_distinct_status_codes(self) -> None:
        snapshot = self.manager.snapshot()
        cases = (
            (SettingsValidationFailure("invalid field"), 422),
            (SettingsLockBusy("busy"), 423),
            (SettingsApplyFailure("failed", rollback_succeeded=True), 503),
            (SettingsConflict(("operandi",), snapshot), 409),
        )
        body = {
            "base_revision": "a" * 64,
            "changes": {},
            "base_values": {},
            "secret_actions": {},
        }
        for failure, expected_status in cases:
            with self.subTest(expected_status=expected_status):
                application = AdminApplication(
                    RaisingSettingsManager(failure),
                    self.status_collector,
                    csrf_token="csrf-token-for-tests",
                )
                response = application.handle(
                    "POST",
                    "/api/settings",
                    {
                        "Host": "127.0.0.1:8765",
                        "Origin": "http://127.0.0.1:8765",
                        "X-Wirtelprimpf-CSRF": "csrf-token-for-tests",
                    },
                    json.dumps(body).encode("utf-8"),
                    client_host="127.0.0.1",
                )
                self.assertEqual(response.status, expected_status)

    def test_foreign_host_origin_and_client_are_rejected(self) -> None:
        foreign_host = self.request("GET", "/api/settings", headers={"Host": "attacker.invalid"})
        foreign_origin = self.request(
            "POST",
            "/api/settings",
            headers={
                "Origin": "https://attacker.invalid",
                "X-Wirtelprimpf-CSRF": "csrf-token-for-tests",
            },
            body={
                "base_revision": "a" * 64,
                "changes": {},
                "base_values": {},
                "secret_actions": {},
            },
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
            body={
                "base_revision": "a" * 64,
                "changes": {"operandi": "classic"},
                "base_values": {"operandi": "story"},
                "secret_actions": {},
            },
        )
        self.assertEqual(response.status, 403)
        self.assertEqual(self.env_file.read_bytes(), before)

    def test_oversized_body_is_rejected_before_json_or_store_access(self) -> None:
        response = self.app.handle(
            "POST",
            "/api/settings",
            {
                "Host": "127.0.0.1:8765",
                "Origin": "http://127.0.0.1:8765",
                "X-Wirtelprimpf-CSRF": "csrf-token-for-tests",
            },
            b"x" * (64 * 1024 + 1),
            client_host="127.0.0.1",
        )
        self.assertEqual(response.status, 413)

    def test_invalid_post_content_lengths_are_rejected_without_reading(self) -> None:
        class UnreadableBody:
            def read(self, _size: int) -> bytes:
                raise AssertionError("request body must not be read")

        for raw_length, expected_status in ((None, 411), ("invalid", 400), ("-1", 400)):
            with self.subTest(raw_length=raw_length):
                handler = object.__new__(_Handler)
                handler.command = "POST"
                handler.path = "/api/settings"
                handler.headers = {} if raw_length is None else {"Content-Length": raw_length}
                handler.rfile = UnreadableBody()
                handler.wfile = io.BytesIO()
                handler.client_address = ("127.0.0.1", 1)
                handler.server = SimpleNamespace(
                    application=SimpleNamespace(
                        handle=lambda *_args, **_kwargs: self.fail("application must not run")
                    )
                )
                statuses: list[int] = []
                handler.send_response = statuses.append
                handler.send_header = lambda *_args: None
                handler.end_headers = lambda: None

                handler._dispatch()

                self.assertEqual(statuses, [expected_status])

    def test_path_traversal_is_not_served(self) -> None:
        response = self.request("GET", "/../../.config/wirtelprimpf/openai.env")
        self.assertEqual(response.status, 404)
        self.assertNotIn("super-secret-value", response.body)

    def test_admin_page_explains_book_and_archive_boundaries(self) -> None:
        response = self.request("GET", "/")
        self.assertEqual(response.status, 200)
        self.assertIn("10 vollständige Storys", response.body)
        self.assertIn("5 Bücher", response.body)
        self.assertIn("50 Storys", response.body)

    def test_admin_assets_are_fixed_local_routes_with_strict_csp(self) -> None:
        page = self.request("GET", "/")
        stylesheet = self.request("GET", "/assets/admin.css")
        script = self.request("GET", "/assets/admin.mjs")
        missing = self.request("GET", "/assets/../../openai.env")
        self.assertEqual(page.status, 200)
        self.assertIn(
            '<meta name="csrf-token" content="csrf-token-for-tests">',
            page.body,
        )
        self.assertNotIn("__CSRF_TOKEN__", page.body)
        self.assertIn('<select id="image_model" name="image_model">', page.body)
        self.assertIn('<select id="story_model" name="story_model">', page.body)
        self.assertIn('href="/assets/admin.css"', page.body)
        self.assertIn('src="/assets/admin.mjs"', page.body)
        self.assertEqual(stylesheet.content_type, "text/css; charset=utf-8")
        self.assertEqual(script.content_type, "text/javascript; charset=utf-8")
        self.assertEqual(missing.status, 404)

    def test_http_handler_security_headers_disallow_inline_assets(self) -> None:
        csp = SECURITY_HEADERS["Content-Security-Policy"]
        self.assertEqual(
            csp,
            "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; "
            "frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
        )
        self.assertNotIn("unsafe-inline", csp)
        self.assertNotIn("https://", csp)
        self.assertEqual(SECURITY_HEADERS["Cache-Control"], "no-store")
        self.assertEqual(SECURITY_HEADERS["X-Frame-Options"], "DENY")
        self.assertEqual(SECURITY_HEADERS["X-Content-Type-Options"], "nosniff")
        self.assertEqual(SECURITY_HEADERS["Referrer-Policy"], "no-referrer")


if __name__ == "__main__":
    unittest.main()
