from __future__ import annotations

import io
import json
import unittest
from unittest.mock import patch

from wirtelprimpf_platform import cli
from wirtelprimpf_platform.settings import (
    SettingsApplyFailure,
    SettingsConflict,
    SettingsLockBusy,
    SettingsSnapshot,
    SettingsValidationFailure,
)


def snapshot_for_test(*, revision: str, settings: dict[str, object]) -> SettingsSnapshot:
    return SettingsSnapshot(
        schema_version="2.0.0",
        revision=revision,
        settings=settings,
        choices={},
        secrets={
            "openai_api_key_present": False,
            "cloudflare_api_token_present": False,
            "github_auth_present": False,
        },
        invariants={},
        warnings=(),
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


if __name__ == "__main__":
    unittest.main()
