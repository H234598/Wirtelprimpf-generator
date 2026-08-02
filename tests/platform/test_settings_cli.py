from __future__ import annotations

import io
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

if __package__:
    from ._settings_fixtures import snapshot_for_test
else:
    from _settings_fixtures import snapshot_for_test

from wirtelprimpf_platform import cli
from wirtelprimpf_platform.settings import (
    SettingsApplyFailure,
    SettingsConflict,
    SettingsLockBusy,
    SettingsPaths,
    SettingsSnapshot,
    SettingsValidationFailure,
)


class FakeManager:
    def __init__(self, snapshot: SettingsSnapshot) -> None:
        self.value = snapshot
        self.applied = None

    def snapshot(self) -> SettingsSnapshot:
        return self.value

    def apply(self, request):
        self.applied = request
        return self.value


class SettingsCLITests(unittest.TestCase):
    def test_admin_rejects_a_noncanonical_settings_path_as_redacted_json(self) -> None:
        supplied_path = Path("/private/CLOUDFLARE_API_TOKEN=must-never-escape.env")
        manager = SimpleNamespace(
            paths=SimpleNamespace(env_file=Path("/expected/openai.env")),
        )
        output = io.StringIO()
        with (
            patch.object(cli, "build_settings_manager", return_value=manager),
            patch.object(cli, "serve_admin") as serve_admin,
            patch("sys.stdout", output),
        ):
            code = cli.main(["admin", "--settings", str(supplied_path)])

        self.assertEqual(code, cli.VALIDATION_ERROR_EXIT_CODE)
        self.assertEqual(
            json.loads(output.getvalue()),
            {
                "ok": False,
                "error": "admin settings path must match the transactional manager path",
            },
        )
        self.assertNotIn(str(supplied_path), output.getvalue())
        serve_admin.assert_not_called()

    def test_snapshot_prints_only_the_public_contract(self) -> None:
        snapshot = snapshot_for_test(revision="a" * 64, settings={"operandi": "story"})
        output = io.StringIO()
        with (
            patch.object(cli, "build_settings_manager", return_value=FakeManager(snapshot)),
            patch("sys.stdout", output),
        ):
            code = cli.settings_main(["snapshot"])
        payload = json.loads(output.getvalue())
        self.assertEqual(code, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["settings"], {"operandi": "story"})

    def test_apply_reads_sparse_request_from_stdin_and_prints_only_public_snapshot(self) -> None:
        snapshot = snapshot_for_test(revision="a" * 64, settings={"operandi": "both"})
        manager = FakeManager(snapshot)
        request = {
            "base_revision": "a" * 64,
            "changes": {"operandi": "both"},
            "base_values": {"operandi": "story"},
            "secret_actions": {
                "openai_api_key": {
                    "action": "replace",
                    "value": "never-print-this-secret",
                }
            },
        }
        output = io.StringIO()
        with (
            patch.object(cli, "build_settings_manager", return_value=manager),
            patch("sys.stdin", io.StringIO(json.dumps(request))),
            patch("sys.stdout", output),
        ):
            code = cli.settings_main(["apply"])
        self.assertEqual(code, 0)
        self.assertEqual(manager.applied.changes, {"operandi": "both"})
        self.assertNotIn("never-print-this-secret", output.getvalue())

    def test_oversized_stdin_is_rejected_before_json_parsing(self) -> None:
        output = io.StringIO()
        manager = FakeManager(snapshot_for_test(revision="a" * 64, settings={}))
        with (
            patch.object(cli, "build_settings_manager", return_value=manager),
            patch("sys.stdin", io.StringIO("x" * (64 * 1024 + 1))),
            patch("sys.stdout", output),
        ):
            self.assertEqual(cli.settings_main(["apply"]), 4)
        self.assertEqual(json.loads(output.getvalue())["error"], "settings request exceeds 65536 bytes")

    def test_byte_stdin_rejects_oversize_and_invalid_utf8(self) -> None:
        class BinaryStdin:
            def __init__(self, payload: bytes) -> None:
                self.buffer = io.BytesIO(payload)

        manager = FakeManager(snapshot_for_test(revision="a" * 64, settings={}))
        cases = (
            (b"x" * (64 * 1024 + 1), "settings request exceeds 65536 bytes"),
            (b"{\xff}", "settings request must be UTF-8"),
        )
        for payload, expected_error in cases:
            with self.subTest(expected_error=expected_error):
                output = io.StringIO()
                with (
                    patch.object(cli, "build_settings_manager", return_value=manager),
                    patch("sys.stdin", BinaryStdin(payload)),
                    patch("sys.stdout", output),
                ):
                    code = cli.settings_main(["apply"])
                self.assertEqual(code, cli.VALIDATION_ERROR_EXIT_CODE)
                self.assertEqual(json.loads(output.getvalue())["error"], expected_error)

    def test_exception_exit_codes_are_stable_and_redacted(self) -> None:
        snapshot = snapshot_for_test(revision="a" * 64, settings={"operandi": "story"})
        cases = (
            (SettingsConflict(("operandi",), snapshot), 3, "conflict"),
            (SettingsValidationFailure("invalid field"), 4, "invalid field"),
            (SettingsLockBusy("busy"), 5, "settings lock is busy"),
            (SettingsApplyFailure("failed", rollback_succeeded=True), 6, "settings transaction failed"),
        )
        for exception, expected_code, expected_error in cases:
            with self.subTest(expected_code=expected_code):
                manager = FakeManager(snapshot)
                manager.apply = lambda request, error=exception: (_ for _ in ()).throw(error)
                output = io.StringIO()
                valid_request = json.dumps(
                    {
                        "base_revision": "a" * 64,
                        "changes": {},
                        "base_values": {},
                        "secret_actions": {},
                    }
                )
                with (
                    patch.object(cli, "build_settings_manager", return_value=manager),
                    patch("sys.stdin", io.StringIO(valid_request)),
                    patch("sys.stdout", output),
                ):
                    code = cli.settings_main(["apply"])
                self.assertEqual(code, expected_code)
                self.assertEqual(json.loads(output.getvalue())["error"], expected_error)

    def test_unexpected_snapshot_and_apply_failures_are_stable_and_redacted(self) -> None:
        secret = "CLOUDFLARE_API_TOKEN=must-never-escape"
        snapshot = snapshot_for_test(revision="a" * 64, settings={})
        valid_request = json.dumps(
            {
                "base_revision": "a" * 64,
                "changes": {},
                "base_values": {},
                "secret_actions": {},
            }
        )
        for command in ("snapshot", "apply"):
            with self.subTest(command=command):
                manager = FakeManager(snapshot)
                if command == "snapshot":
                    manager.snapshot = lambda: (_ for _ in ()).throw(RuntimeError(secret))
                else:
                    manager.apply = lambda _request: (_ for _ in ()).throw(RuntimeError(secret))
                output = io.StringIO()
                with (
                    patch("sys.stdin", io.StringIO(valid_request)),
                    patch("sys.stdout", output),
                ):
                    code = cli._run_settings_command(command, manager)
                self.assertEqual(code, cli.UNAVAILABLE_ERROR_EXIT_CODE)
                self.assertEqual(
                    json.loads(output.getvalue()),
                    {"ok": False, "error": "settings operation unavailable"},
                )
                self.assertNotIn(secret, output.getvalue())

    def test_status_collector_uses_the_managers_exact_validated_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = replace(
                SettingsPaths.for_home(root),
                platform_state=root / "custom/platform.json",
                state_file=root / "custom/settings.json",
                hub_outbox=root / "custom/hub.json",
                publication_catalog=root / "custom/catalog.json",
                cloudflare_token_file=root / "custom/cloudflare.env",
                generator_root=root / "custom/generator",
            )
            manager = SimpleNamespace(
                paths=paths,
                snapshot=lambda: None,
                systemd=SimpleNamespace(observe_timer=lambda: None),
            )

            collector = cli.build_status_collector(manager)

        self.assertEqual(collector.paths.platform_state, paths.platform_state)
        self.assertEqual(collector.paths.settings_state, paths.state_file)
        self.assertEqual(collector.paths.hub_outbox, paths.hub_outbox)
        self.assertEqual(collector.paths.publication_catalog, paths.publication_catalog)
        self.assertEqual(collector.paths.cloudflare_token, paths.cloudflare_token_file)
        self.assertEqual(
            collector.paths.media_manifest,
            paths.generator_root / "data/media-manifest.json",
        )


if __name__ == "__main__":
    unittest.main()
