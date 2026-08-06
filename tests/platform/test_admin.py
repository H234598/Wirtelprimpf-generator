from __future__ import annotations

import io
import json
import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

from wirtelprimpf_platform.admin import (
    SECURITY_HEADERS,
    AdminApplication,
    AdminError,
    AdminResponse,
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


class FakeGeneration:
    def __init__(self, result: dict[str, str] | Exception | None = None) -> None:
        self.result = result or {"mode": "story", "unit": "wirtelprimpf.service", "state": "queued"}
        self.calls: list[str] = []

    def trigger(self, mode: str) -> dict[str, str]:
        self.calls.append(mode)
        if isinstance(self.result, Exception):
            raise self.result
        return {**self.result, "mode": mode}


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
        self.generation = FakeGeneration()
        self.app = AdminApplication(
            self.manager,
            self.status_collector,
            csrf_token="csrf-token-for-tests",
            generation=self.generation,
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

    @contextmanager
    def live_server(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        server.application = self.app
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}"
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)

    def raw_http_status(self, port: int, headers: list[str], body: bytes) -> int:
        request = (
            "POST /api/settings HTTP/1.1\r\n"
            + "\r\n".join(headers)
            + f"\r\nContent-Type: application/json\r\nContent-Length: {len(body)}"
            + "\r\nConnection: close\r\n\r\n"
        ).encode("ascii") + body
        with socket.create_connection(("127.0.0.1", port), timeout=2) as client:
            client.sendall(request)
            response = bytearray()
            while chunk := client.recv(8_192):
                response.extend(chunk)
        return int(bytes(response).split(b"\r\n", 1)[0].split()[1])

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

    def test_real_urllib_post_accepts_case_normalized_security_headers(self) -> None:
        with self.live_server() as base_url:
            with urllib.request.urlopen(f"{base_url}/api/settings", timeout=2) as response:
                initial = json.load(response)
            payload = json.dumps(
                {
                    "base_revision": initial["revision"],
                    "changes": {"output_resolution": "source"},
                    "base_values": {
                        "output_resolution": initial["settings"]["output_resolution"]
                    },
                    "secret_actions": {},
                }
            ).encode("utf-8")
            request = urllib.request.Request(
                f"{base_url}/api/settings",
                data=payload,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Origin": base_url,
                    "X-Wirtelprimpf-CSRF": "csrf-token-for-tests",
                },
                method="POST",
            )
            try:
                opened = urllib.request.urlopen(request, timeout=2)
            except urllib.error.HTTPError as error:
                with error:
                    status = error.code
                    decoded = json.load(error)
            else:
                with opened as response:
                    status = response.status
                    decoded = json.load(response)

        self.assertEqual(status, 200, decoded)
        self.assertEqual(decoded["settings"]["output_resolution"], "source")

    def test_manual_generation_endpoints_start_only_the_requested_fixed_mode(self) -> None:
        headers = {
            "Origin": "http://127.0.0.1:8765",
            "X-Wirtelprimpf-CSRF": "csrf-token-for-tests",
        }
        story = self.request("POST", "/api/generate/story", headers=headers, body={})
        atelier = self.request("POST", "/api/generate/atelier", headers=headers, body={})

        self.assertEqual(story.status, 202)
        self.assertEqual(atelier.status, 202)
        self.assertEqual(self.generation.calls, ["story", "atelier"])
        self.assertEqual(json.loads(story.body)["state"], "queued")
        self.assertEqual(json.loads(atelier.body)["mode"], "atelier")

    def test_manual_generation_requires_csrf_and_exact_empty_envelope(self) -> None:
        missing = self.request("POST", "/api/generate/story", body={})
        malformed = self.request(
            "POST",
            "/api/generate/story",
            headers={
                "Origin": "http://127.0.0.1:8765",
                "X-Wirtelprimpf-CSRF": "csrf-token-for-tests",
            },
            body={"unexpected": True},
        )

        self.assertEqual(missing.status, 403)
        self.assertEqual(malformed.status, 422)
        self.assertEqual(self.generation.calls, [])

    def test_real_socket_rejects_case_variant_duplicate_security_headers(self) -> None:
        before = self.env_file.read_bytes()
        snapshot = self.manager.snapshot().to_public_dict()
        body = json.dumps(
            {
                "base_revision": snapshot["revision"],
                "changes": {},
                "base_values": {},
                "secret_actions": {},
            }
        ).encode("utf-8")
        with self.live_server() as base_url:
            port = int(base_url.rsplit(":", 1)[1])
            host = f"127.0.0.1:{port}"
            common = [
                f"Host: {host}",
                f"Origin: {base_url}",
                "X-Wirtelprimpf-CSRF: csrf-token-for-tests",
            ]
            cases = (
                [common[0], "hOsT: attacker.invalid", *common[1:]],
                [common[0], common[1], "oRiGiN: https://attacker.invalid", common[2]],
                [*common, "x-WIRTELPRIMPF-csrf: attacker-token"],
            )
            statuses = [self.raw_http_status(port, headers, body) for headers in cases]

        self.assertEqual(statuses, [403, 403, 403])
        self.assertEqual(self.env_file.read_bytes(), before)

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

    def test_origin_port_must_exactly_match_even_when_host_omits_a_port(self) -> None:
        response = self.request(
            "POST",
            "/api/settings",
            headers={
                "Host": "localhost",
                "Origin": "http://localhost:8765",
                "X-Wirtelprimpf-CSRF": "csrf-token-for-tests",
            },
            body={
                "base_revision": "a" * 64,
                "changes": {},
                "base_values": {},
                "secret_actions": {},
            },
        )
        self.assertEqual(response.status, 403)

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

    def test_oversized_content_length_closes_the_connection_without_reading(self) -> None:
        class UnreadableBody:
            def read(self, _size: int) -> bytes:
                raise AssertionError("request body must not be read")

        handler = object.__new__(_Handler)
        handler.command = "POST"
        handler.path = "/api/settings"
        handler.headers = {"Content-Length": str(64 * 1024 + 1)}
        handler.rfile = UnreadableBody()
        handler.wfile = io.BytesIO()
        handler.client_address = ("127.0.0.1", 1)
        handler.close_connection = False
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

        self.assertEqual(statuses, [413])
        self.assertTrue(handler.close_connection)

    def test_inherited_request_line_limit_rejects_before_dispatch(self) -> None:
        handler = object.__new__(_Handler)
        handler.rfile = io.BytesIO(b"GET /" + b"x" * (64 * 1024) + b" HTTP/1.1\r\n")
        handler.wfile = io.BytesIO()
        handler.close_connection = False
        statuses: list[int] = []
        handler.send_error = lambda status, *_args, **_kwargs: statuses.append(status)

        handler.handle_one_request()

        self.assertEqual(statuses, [414])
        self.assertEqual(handler.rfile.tell(), 64 * 1024 + 1)

    def test_get_and_head_reject_nonempty_request_bodies_without_reading(self) -> None:
        class UnreadableBody:
            def read(self, _size: int) -> bytes:
                raise AssertionError("request body must not be read")

        for command in ("GET", "HEAD"):
            with self.subTest(command=command):
                handler = object.__new__(_Handler)
                handler.command = command
                handler.path = "/api/settings"
                handler.headers = {"Content-Length": "1"}
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

                self.assertEqual(statuses, [400])

    def test_partial_post_body_times_out_without_waiting_for_peer_close(self) -> None:
        server_socket, client_socket = socket.socketpair()
        handler = object.__new__(_Handler)
        handler.command = "POST"
        handler.path = "/api/settings"
        handler.headers = {"Content-Length": "100"}
        handler.connection = server_socket
        handler.request_body_timeout_seconds = 0.05
        handler.rfile = server_socket.makefile("rb")
        handler.wfile = io.BytesIO()
        handler.client_address = ("127.0.0.1", 1)
        application_calls: list[bytes] = []

        def handle(_method, _path, _headers, body, *, client_host):
            del client_host
            application_calls.append(body)
            return AdminResponse(200, "{}")

        handler.server = SimpleNamespace(application=SimpleNamespace(handle=handle))
        statuses: list[int] = []
        handler.send_response = statuses.append
        handler.send_header = lambda *_args: None
        handler.end_headers = lambda: None
        worker = threading.Thread(target=handler._dispatch, daemon=True)
        client_socket.sendall(b"{}")
        worker.start()
        worker.join(timeout=0.5)
        completed_before_peer_close = not worker.is_alive()
        restored_timeout = server_socket.gettimeout()
        try:
            if worker.is_alive():
                client_socket.shutdown(socket.SHUT_WR)
                worker.join(timeout=1)
        finally:
            handler.rfile.close()
            server_socket.close()
            client_socket.close()

        self.assertTrue(completed_before_peer_close)
        self.assertIsNone(restored_timeout)
        self.assertEqual(statuses, [408])
        self.assertEqual(application_calls, [])

    def test_slow_drip_post_body_hits_one_absolute_total_deadline(self) -> None:
        server_socket, client_socket = socket.socketpair()
        server_socket.settimeout(0.7)
        handler = object.__new__(_Handler)
        handler.command = "POST"
        handler.path = "/api/settings"
        handler.headers = {"Content-Length": "100"}
        handler.connection = server_socket
        handler.request_body_timeout_seconds = 0.08
        handler.rfile = server_socket.makefile("rb")
        handler.wfile = io.BytesIO()
        handler.client_address = ("127.0.0.1", 1)
        application_calls: list[bytes] = []

        def handle(_method, _path, _headers, body, *, client_host):
            del client_host
            application_calls.append(body)
            return AdminResponse(200, "{}")

        handler.server = SimpleNamespace(application=SimpleNamespace(handle=handle))
        statuses: list[int] = []
        handler.send_response = statuses.append
        handler.send_header = lambda *_args: None
        handler.end_headers = lambda: None
        response_write_timeouts: list[float | None] = []

        def write_response(response: AdminResponse) -> None:
            response_write_timeouts.append(server_socket.gettimeout())
            _Handler._write_admin_response(handler, response)

        handler._write_admin_response = write_response
        stop_drip = threading.Event()

        def drip() -> None:
            while not stop_drip.is_set():
                try:
                    client_socket.sendall(b"x")
                except OSError:
                    return
                time.sleep(0.02)

        worker = threading.Thread(target=handler._dispatch, daemon=True)
        dripper = threading.Thread(target=drip, daemon=True)
        worker.start()
        dripper.start()
        worker.join(timeout=0.8)
        completed_with_dripping_peer = not worker.is_alive()
        restored_timeout = server_socket.gettimeout()
        stop_drip.set()
        try:
            if worker.is_alive():
                client_socket.shutdown(socket.SHUT_WR)
                worker.join(timeout=1)
            dripper.join(timeout=1)
        finally:
            handler.rfile.close()
            server_socket.close()
            client_socket.close()

        self.assertTrue(completed_with_dripping_peer)
        self.assertEqual(restored_timeout, 0.7)
        self.assertEqual(response_write_timeouts, [0.7])
        self.assertEqual(statuses, [408])
        self.assertEqual(application_calls, [])

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

    def test_http_handler_emits_every_security_header(self) -> None:
        handler = object.__new__(_Handler)
        handler.command = "GET"
        handler.wfile = io.BytesIO()
        statuses: list[int] = []
        headers: list[tuple[str, str]] = []
        handler.send_response = statuses.append
        handler.send_header = lambda name, value: headers.append((name, value))
        handler.end_headers = lambda: None

        handler._write_admin_response(AdminResponse(200, "{}"))

        self.assertEqual(statuses, [200])
        for item in SECURITY_HEADERS.items():
            self.assertIn(item, headers)

    def test_snapshot_status_and_apply_internal_errors_are_redacted(self) -> None:
        secret = "CLOUDFLARE_API_TOKEN=must-never-escape"

        class RaisingStatus:
            def collect(self):
                raise RuntimeError(secret)

        application = AdminApplication(
            SimpleNamespace(
                snapshot=lambda: (_ for _ in ()).throw(RuntimeError(secret)),
                apply=lambda _request: (_ for _ in ()).throw(RuntimeError(secret)),
            ),
            RaisingStatus(),
            csrf_token="csrf-token-for-tests",
        )
        settings_response = application.handle(
            "GET",
            "/api/settings",
            {"Host": "127.0.0.1:8765"},
            b"",
            client_host="127.0.0.1",
        )
        status_response = application.handle(
            "GET",
            "/api/status",
            {"Host": "127.0.0.1:8765"},
            b"",
            client_host="127.0.0.1",
        )
        apply_response = application.handle(
            "POST",
            "/api/settings",
            {
                "Host": "127.0.0.1:8765",
                "Origin": "http://127.0.0.1:8765",
                "X-Wirtelprimpf-CSRF": "csrf-token-for-tests",
            },
            json.dumps(
                {
                    "base_revision": "a" * 64,
                    "changes": {},
                    "base_values": {},
                    "secret_actions": {},
                }
            ).encode("utf-8"),
            client_host="127.0.0.1",
        )

        self.assertEqual(settings_response.status, 500)
        self.assertEqual(status_response.status, 500)
        self.assertEqual(apply_response.status, 503)
        for response in (settings_response, status_response, apply_response):
            self.assertNotIn(secret, response.body)


if __name__ == "__main__":
    unittest.main()
