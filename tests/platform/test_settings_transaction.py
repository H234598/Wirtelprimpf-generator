from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from wirtelprimpf_platform.settings import (
    ChangeRequest,
    SettingsApplyFailure,
    SettingsConflict,
    SettingsError,
    SettingsLockBusy,
    SettingsManager,
    SettingsPaths,
    SettingsValidationFailure,
)
from wirtelprimpf_platform.settings_io import SettingsIOError
from wirtelprimpf_platform.systemd_user import TimerConfiguration, TimerObservation


class FakeSystemd:
    def __init__(self) -> None:
        self.configuration = TimerConfiguration(True, 120, 120, True)
        self.active = True
        self.fail_apply = False
        self.apply_calls = 0
        self.restore_calls = 0
        self.observe_calls = 0

    def observe_timer(self) -> TimerObservation:
        self.observe_calls += 1
        return TimerObservation.from_configuration(self.configuration, active=self.active)

    def apply_timer(self, configuration: TimerConfiguration) -> TimerObservation:
        self.apply_calls += 1
        if self.fail_apply:
            raise RuntimeError("injected systemd failure with secret=do-not-echo")
        self.configuration = configuration
        self.active = configuration.enabled
        return self.observe_timer()

    def restore_timer(
        self,
        configuration: TimerConfiguration,
        was_active: bool,
        dropin_backup: object | None = None,
    ) -> TimerObservation:
        self.restore_calls += 1
        self.configuration = configuration
        self.active = was_active
        return self.observe_timer()


class SettingsTransactionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.paths = SettingsPaths.for_home(root)
        self.paths.env_file.parent.mkdir(parents=True, mode=0o700)
        self.paths.env_file.write_text(
            "OPENAI_API_KEY=original-openai-secret\n"
            "WIRTELPRIMPF_OPERANDI=story\n"
            "WIRTELPRIMPF_SITE_TITLE=Original\n"
            "WIRTELPRIMPF_GENERATION_INTERVAL_MINUTES=120\n",
            encoding="utf-8",
        )
        os.chmod(self.paths.env_file, 0o600)
        self.systemd = FakeSystemd()
        self.manager = SettingsManager(self.paths, systemd=self.systemd, validator=lambda values: None)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def request(
        self,
        base_revision: str,
        changes: dict[str, object],
        base_values: dict[str, object],
        secret_actions: dict[str, object] | None = None,
    ) -> ChangeRequest:
        return ChangeRequest.from_payload(
            {
                "base_revision": base_revision,
                "changes": changes,
                "base_values": base_values,
                "secret_actions": secret_actions or {},
            }
        )

    def test_stale_non_overlapping_changes_merge_without_lost_update(self) -> None:
        base = self.manager.snapshot()
        document = self.paths.env_file.read_text(encoding="utf-8").replace(
            "WIRTELPRIMPF_OPERANDI=story", "WIRTELPRIMPF_OPERANDI=both"
        )
        self.paths.env_file.write_text(document, encoding="utf-8")
        result = self.manager.apply(
            self.request(
                base.revision,
                {"site_title": "Extern sicher zusammengeführt"},
                {"site_title": "Original"},
            )
        )
        self.assertEqual(result.settings["operandi"], "both")
        self.assertEqual(result.settings["site_title"], "Extern sicher zusammengeführt")

    def test_stale_same_field_change_rejects_the_whole_transaction(self) -> None:
        base = self.manager.snapshot()
        before = self.paths.env_file.read_bytes()
        self.paths.env_file.write_text(
            before.decode().replace("Original", "Andere Oberfläche"), encoding="utf-8"
        )
        external = self.paths.env_file.read_bytes()
        with self.assertRaises(SettingsConflict) as caught:
            self.manager.apply(
                self.request(
                    base.revision,
                    {"site_title": "Mein Entwurf"},
                    {"site_title": "Original"},
                )
            )
        self.assertEqual(caught.exception.fields, ("site_title",))
        self.assertEqual(self.paths.env_file.read_bytes(), external)

    def test_base_value_comparison_does_not_coerce_boolean_to_integer(self) -> None:
        base = self.manager.snapshot()
        self.paths.env_file.write_text(
            self.paths.env_file.read_text(encoding="utf-8")
            + "WIRTELPRIMPF_STORY_FINISH_PARTS_MIN=1\n",
            encoding="utf-8",
        )
        external = self.paths.env_file.read_bytes()

        with self.assertRaises(SettingsConflict) as caught:
            self.manager.apply(
                self.request(
                    base.revision,
                    {"story_finish_parts_min": 2},
                    {"story_finish_parts_min": True},
                )
            )

        self.assertEqual(caught.exception.fields, ("story_finish_parts_min",))
        self.assertEqual(self.paths.env_file.read_bytes(), external)

    def test_every_stale_secret_action_is_rejected_without_exposing_the_secret(self) -> None:
        base = self.manager.snapshot()
        self.paths.env_file.write_text(
            self.paths.env_file.read_text(encoding="utf-8")
            + "WIRTELPRIMPF_OUTPUT_RESOLUTION=4k\n",
            encoding="utf-8",
        )
        with self.assertRaises(SettingsConflict) as caught:
            self.manager.apply(
                self.request(
                    base.revision,
                    {},
                    {},
                    {
                        "cloudflare_api_token": {
                            "action": "replace",
                            "value": "new-cloudflare-secret",
                        }
                    },
                )
            )
        self.assertNotIn("new-cloudflare-secret", str(caught.exception))
        self.assertFalse(self.paths.cloudflare_token_file.exists())

    def test_validator_failure_restores_every_file_without_touching_timer(self) -> None:
        before_env = self.paths.env_file.read_bytes()
        before_timer = self.systemd.configuration
        manager = SettingsManager(
            self.paths,
            systemd=self.systemd,
            validator=lambda values: (_ for _ in ()).throw(
                RuntimeError("invalid generator configuration secret=do-not-echo")
            ),
        )
        base = manager.snapshot()
        with self.assertRaises(SettingsApplyFailure) as caught:
            manager.apply(
                self.request(
                    base.revision,
                    {"site_title": "Rejected"},
                    {"site_title": "Original"},
                    {
                        "cloudflare_api_token": {
                            "action": "replace",
                            "value": "new-cloudflare-secret",
                        }
                    },
                )
            )
        self.assertTrue(caught.exception.rollback_succeeded)
        self.assertNotIn("do-not-echo", str(caught.exception))
        self.assertEqual(self.paths.env_file.read_bytes(), before_env)
        self.assertFalse(self.paths.cloudflare_token_file.exists())
        self.assertEqual(self.systemd.configuration, before_timer)
        self.assertEqual(self.systemd.apply_calls, 0)
        self.assertEqual(self.systemd.restore_calls, 0)

    def test_validator_receives_exact_post_write_raw_environment_and_rolls_back(self) -> None:
        self.paths.env_file.write_text(
            self.paths.env_file.read_text(encoding="utf-8")
            + "WIRTELPRIMPF_STORY_FINISH_PARTS_MIN=99\n"
            + "WIRTELPRIMPF_STORY_FINISH_PARTS_MAX=5\n",
            encoding="utf-8",
        )
        before = self.paths.env_file.read_bytes()
        observed_raw_values: list[str | None] = []

        def validate_raw(values: dict[str, str]) -> None:
            raw_value = values.get("WIRTELPRIMPF_STORY_FINISH_PARTS_MIN")
            observed_raw_values.append(raw_value)
            if raw_value == "99":
                raise RuntimeError("raw persisted setting is invalid")

        manager = SettingsManager(
            self.paths,
            systemd=self.systemd,
            validator=validate_raw,
        )
        base = manager.snapshot()
        self.assertIn(
            "invalid_persisted_setting:story_finish_parts_min",
            base.warnings,
        )

        with self.assertRaises(SettingsApplyFailure) as caught:
            manager.apply(
                self.request(
                    base.revision,
                    {"site_title": "Unrelated change"},
                    {"site_title": "Original"},
                )
            )

        self.assertTrue(caught.exception.rollback_succeeded)
        self.assertEqual(observed_raw_values, ["99"])
        self.assertEqual(self.paths.env_file.read_bytes(), before)
        self.assertEqual(self.systemd.apply_calls, 0)
        self.assertEqual(self.systemd.restore_calls, 0)

    def test_success_writes_secret_free_revision_signal(self) -> None:
        base = self.manager.snapshot()
        result = self.manager.apply(
            self.request(base.revision, {"operandi": "classic"}, {"operandi": "story"})
        )
        signal = self.paths.state_file.read_text(encoding="utf-8")
        self.assertEqual(json.loads(signal)["revision"], result.revision)
        self.assertNotIn("original-openai-secret", signal)

    def test_success_reuses_the_result_snapshot_after_writing_the_signal(self) -> None:
        base = self.manager.snapshot()
        self.systemd.observe_calls = 0
        self.manager.apply(
            self.request(base.revision, {"operandi": "classic"}, {"operandi": "story"})
        )
        self.assertEqual(self.systemd.observe_calls, 3)

    def test_initial_read_errors_are_wrapped_at_the_manager_boundary(self) -> None:
        secret = "OPENAI_API_KEY=must-never-escape"
        base = self.manager.snapshot()
        request = self.request(base.revision, {}, {})
        for operation in (
            lambda: self.manager.snapshot(),
            lambda: self.manager.apply(request),
        ):
            with self.subTest(operation=operation):
                with (
                patch.object(
                    self.manager,
                    "_read_snapshot_unlocked",
                    side_effect=SettingsIOError(secret),
                ),
                self.assertRaises(SettingsError) as caught,
                ):
                    operation()
                self.assertNotIsInstance(caught.exception, SettingsIOError)
                self.assertNotIn(secret, str(caught.exception))

    def test_lock_descriptor_closes_when_post_open_validation_fails(self) -> None:
        real_open = os.open
        descriptors: list[int] = []

        def tracking_open(*args, **kwargs):
            descriptor = real_open(*args, **kwargs)
            descriptors.append(descriptor)
            return descriptor

        with (
            patch("wirtelprimpf_platform.settings.os.open", side_effect=tracking_open),
            patch(
                "wirtelprimpf_platform.settings.os.fstat",
                side_effect=OSError("injected fstat failure"),
            ),
            self.assertRaisesRegex(SettingsError, "cannot open settings lock"),
        ):
            self.manager.snapshot()
        self.assertEqual(len(descriptors), 1)
        with self.assertRaises(OSError):
            os.fstat(descriptors[0])

    def test_snapshot_validates_persisted_cross_field_values_as_one_configuration(self) -> None:
        self.paths.env_file.write_text(
            self.paths.env_file.read_text(encoding="utf-8")
            + "WIRTELPRIMPF_STORY_FINISH_PARTS_MIN=8\n"
            + "WIRTELPRIMPF_STORY_FINISH_PARTS_MAX=9\n",
            encoding="utf-8",
        )
        snapshot = self.manager.snapshot()
        self.assertEqual(snapshot.settings["story_finish_parts_min"], 8)
        self.assertEqual(snapshot.settings["story_finish_parts_max"], 9)
        self.assertNotIn("invalid_persisted_setting:story_finish_parts_min", snapshot.warnings)

    def test_timer_runtime_events_do_not_change_the_settings_revision(self) -> None:
        first = self.manager.snapshot()
        base = self.systemd.observe_timer()
        self.systemd.observe_timer = lambda: TimerObservation(
            enabled=base.enabled,
            active=False,
            active_state="inactive",
            interval_minutes=base.interval_minutes,
            randomized_delay_seconds=base.randomized_delay_seconds,
            persistent=base.persistent,
            last_trigger="Sat 2026-08-01 18:00:00 CEST",
            next_run="Sat 2026-08-01 20:00:00 CEST",
            result="failure",
        )
        second = self.manager.snapshot()
        self.assertEqual(second.revision, first.revision)

    def test_failed_non_timer_change_rolls_back_files_without_touching_systemd(self) -> None:
        before = self.paths.env_file.read_bytes()
        manager = SettingsManager(
            self.paths,
            systemd=self.systemd,
            validator=lambda values: (_ for _ in ()).throw(RuntimeError("invalid website value")),
        )
        base = manager.snapshot()
        with self.assertRaises(SettingsApplyFailure):
            manager.apply(
                self.request(base.revision, {"site_title": "Rejected"}, {"site_title": "Original"})
            )
        self.assertEqual(self.paths.env_file.read_bytes(), before)
        self.assertEqual(self.systemd.apply_calls, 0)
        self.assertEqual(self.systemd.restore_calls, 0)

    def test_rollback_does_not_rewrite_a_revision_signal_the_transaction_never_touched(self) -> None:
        self.paths.state_file.write_text('{"revision":"old"}\n', encoding="utf-8")
        before = self.paths.state_file.stat()
        manager = SettingsManager(
            self.paths,
            systemd=self.systemd,
            validator=lambda values: (_ for _ in ()).throw(RuntimeError("invalid website value")),
        )
        base = manager.snapshot()
        with self.assertRaises(SettingsApplyFailure):
            manager.apply(
                self.request(base.revision, {"site_title": "Rejected"}, {"site_title": "Original"})
            )
        after = self.paths.state_file.stat()
        self.assertEqual((after.st_ino, after.st_mtime_ns), (before.st_ino, before.st_mtime_ns))

    def test_schema_validation_failure_occurs_before_backup_or_systemd_mutation(self) -> None:
        base = self.manager.snapshot()
        before = self.paths.env_file.read_bytes()
        with self.assertRaises(SettingsValidationFailure):
            self.manager.apply(
                self.request(
                    base.revision,
                    {"generation_interval_minutes": 29},
                    {"generation_interval_minutes": 120},
                )
            )
        self.assertEqual(self.paths.env_file.read_bytes(), before)
        self.assertEqual(self.systemd.apply_calls, 0)
        self.assertEqual(self.systemd.restore_calls, 0)

    def test_systemd_failure_restores_files_and_old_effective_timer(self) -> None:
        base = self.manager.snapshot()
        before_env = self.paths.env_file.read_bytes()
        before_timer = self.systemd.configuration
        self.systemd.fail_apply = True
        with self.assertRaises(SettingsApplyFailure) as caught:
            self.manager.apply(
                self.request(
                    base.revision,
                    {"generation_interval_minutes": 180},
                    {"generation_interval_minutes": 120},
                    {
                        "cloudflare_api_token": {
                            "action": "replace",
                            "value": "new-cloudflare-secret",
                        }
                    },
                )
            )
        self.assertTrue(caught.exception.rollback_succeeded)
        self.assertEqual(self.paths.env_file.read_bytes(), before_env)
        self.assertFalse(self.paths.cloudflare_token_file.exists())
        self.assertEqual(self.systemd.configuration, before_timer)
        self.assertEqual(self.systemd.apply_calls, 1)
        self.assertEqual(self.systemd.restore_calls, 1)

    def test_settings_path_cannot_redirect_transaction_writes(self) -> None:
        base = self.manager.snapshot()
        with self.assertRaisesRegex(SettingsValidationFailure, "settings_path"):
            self.manager.apply(
                self.request(
                    base.revision,
                    {"settings_path": "/tmp/attacker.env"},
                    {"settings_path": "~/.config/wirtelprimpf/openai.env"},
                )
            )
        self.assertFalse(Path("/tmp/attacker.env").exists())

    def test_busy_lock_times_out_without_touching_configuration(self) -> None:
        import fcntl

        self.paths.lock_file.parent.mkdir(parents=True, exist_ok=True)
        before = self.paths.env_file.read_bytes()
        with self.paths.lock_file.open("a+b") as lock_handle:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            manager = SettingsManager(
                self.paths,
                systemd=self.systemd,
                validator=lambda values: None,
                lock_timeout_seconds=0.05,
            )
            with self.assertRaises(SettingsLockBusy):
                manager.snapshot()
        self.assertEqual(self.paths.env_file.read_bytes(), before)

    def test_request_envelope_and_secret_actions_are_strict(self) -> None:
        invalid = (
            {},
            {
                "base_revision": "short",
                "changes": {},
                "base_values": {},
                "secret_actions": {},
            },
            {
                "base_revision": "a" * 64,
                "changes": {"operandi": "both"},
                "base_values": {},
                "secret_actions": {},
            },
            {
                "base_revision": "a" * 64,
                "changes": {},
                "base_values": {},
                "secret_actions": {"openai_api_key": {"action": "replace"}},
            },
        )
        for payload in invalid:
            with self.subTest(payload=payload), self.assertRaises(SettingsValidationFailure):
                ChangeRequest.from_payload(payload)


if __name__ == "__main__":
    unittest.main()
