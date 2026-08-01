from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from wirtelprimpf_platform.settings_io import SecureFile
from wirtelprimpf_platform.systemd_user import (
    SystemdCommandError,
    SystemdUserManager,
    TimerConfiguration,
)


class FakeRunner:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def __call__(self, command: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        if command[2:4] == ["is-enabled", "wirtelprimpf.timer"]:
            return subprocess.CompletedProcess(command, 0, "enabled\n", "")
        if command[2] == "show":
            return subprocess.CompletedProcess(
                command,
                0,
                (
                    "ActiveState=active\nResult=success\nPersistent=yes\n"
                    "RandomizedDelayUSec=2min\nTimersMonotonic={ OnUnitActiveUSec=2h ; }\n"
                    "LastTriggerUSec=Sat 2026-08-01 05:26:37 CEST\n"
                    "NextElapseUSecRealtime=Sat 2026-08-01 07:28:15 CEST\n"
                ),
                "",
            )
        return subprocess.CompletedProcess(command, 0, "", "")


class StatefulRunner:
    def __init__(self) -> None:
        self.enabled = True
        self.active = False
        self.commands: list[list[str]] = []

    def __call__(self, command: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        action = command[2]
        if action == "is-enabled":
            return subprocess.CompletedProcess(command, 0 if self.enabled else 1, "enabled\n" if self.enabled else "disabled\n", "")
        if action == "show":
            return subprocess.CompletedProcess(
                command,
                0,
                (
                    f"ActiveState={'active' if self.active else 'inactive'}\n"
                    "Result=success\nPersistent=yes\nRandomizedDelayUSec=2min\n"
                    "TimersMonotonic={ OnUnitActiveUSec=2h ; }\n"
                    "LastTriggerUSec=\nNextElapseUSecRealtime=\n"
                ),
                "",
            )
        if action == "enable":
            self.enabled = True
            if "--now" in command:
                self.active = True
        elif action == "disable":
            self.enabled = False
            if "--now" in command:
                self.active = False
        elif action in {"start", "restart"}:
            self.active = True
        elif action == "stop":
            self.active = False
        return subprocess.CompletedProcess(command, 0, "", "")


class SystemdUserTests(unittest.TestCase):
    def test_dropin_is_deterministic_and_clears_vendor_timer_values(self) -> None:
        runner = FakeRunner()
        with tempfile.TemporaryDirectory() as temporary:
            manager = SystemdUserManager(Path(temporary) / "override.conf", runner=runner)
            text = manager.render_dropin(TimerConfiguration(True, 180, 90, True))
        self.assertEqual(
            text,
            (
                "[Timer]\nOnCalendar=\nOnBootSec=\nOnUnitActiveSec=\n"
                "OnBootSec=180min\nOnUnitActiveSec=180min\nRandomizedDelaySec=90\nPersistent=true\n"
            ),
        )

    def test_apply_reloads_restarts_and_verifies_effective_state(self) -> None:
        runner = FakeRunner()
        with tempfile.TemporaryDirectory() as temporary:
            manager = SystemdUserManager(Path(temporary) / "override.conf", runner=runner)
            manager.apply_timer(TimerConfiguration(True, 120, 120, True))
        self.assertIn(["systemctl", "--user", "daemon-reload"], runner.commands)
        self.assertIn(["systemctl", "--user", "enable", "--now", "wirtelprimpf.timer"], runner.commands)
        self.assertIn(["systemctl", "--user", "restart", "wirtelprimpf.timer"], runner.commands)
        self.assertEqual(manager.observe_timer().interval_minutes, 120)

    def test_nonzero_systemctl_result_is_redacted(self) -> None:
        def failed(command: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(command, 1, "", "token=must-not-echo")

        with tempfile.TemporaryDirectory() as temporary:
            manager = SystemdUserManager(Path(temporary) / "override.conf", runner=failed)
            with self.assertRaisesRegex(SystemdCommandError, "systemctl command failed") as caught:
                manager.apply_timer(TimerConfiguration(True, 120, 120, True))
            self.assertNotIn("must-not-echo", str(caught.exception))

    def test_restore_keeps_original_bytes_and_enabled_but_inactive_state(self) -> None:
        runner = StatefulRunner()
        with tempfile.TemporaryDirectory() as temporary:
            dropin = Path(temporary) / "override.conf"
            file = SecureFile(dropin, private=False)
            original = b"# local operator note\n[Timer]\nOnUnitActiveSec = 2h\nRandomizedDelaySec=120\nPersistent=true\n"
            file.replace_bytes(original)
            backup = file.capture()
            file.replace_bytes(b"[Timer]\nOnUnitActiveSec=3h\n")
            manager = SystemdUserManager(dropin, runner=runner)
            observation = manager.restore_timer(
                TimerConfiguration(True, 120, 120, True),
                was_active=False,
                dropin_backup=backup,
            )
            self.assertEqual(dropin.read_bytes(), original)
        self.assertTrue(observation.enabled)
        self.assertFalse(observation.active)
        self.assertIn(["systemctl", "--user", "enable", "wirtelprimpf.timer"], runner.commands)
        self.assertIn(["systemctl", "--user", "stop", "wirtelprimpf.timer"], runner.commands)

    def test_duration_units_are_normalized_to_seconds_and_minutes(self) -> None:
        runner = FakeRunner()
        with tempfile.TemporaryDirectory() as temporary:
            observation = SystemdUserManager(Path(temporary) / "override.conf", runner=runner).observe_timer()
        self.assertEqual(observation.interval_minutes, 120)
        self.assertEqual(observation.randomized_delay_seconds, 120)
        self.assertEqual(observation.last_trigger, "Sat 2026-08-01 05:26:37 CEST")


if __name__ == "__main__":
    unittest.main()
