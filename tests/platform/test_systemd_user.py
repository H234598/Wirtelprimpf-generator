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
    _duration_seconds,
)


class FakeRunner:
    def __init__(
        self,
        *,
        interval: str = "2h",
        delay: str = "2min",
        monotonic_entries: tuple[str, ...] | None = None,
    ) -> None:
        self.commands: list[list[str]] = []
        self.interval = interval
        self.delay = delay
        self.monotonic_entries = monotonic_entries or (
            f"{{ OnUnitActiveUSec={self.interval} ; next_elapse=12h 4min 6.248989s }}",
        )

    def __call__(self, command: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        if command[2:4] == ["is-enabled", "wirtelprimpf.timer"]:
            return subprocess.CompletedProcess(command, 0, "enabled\n", "")
        if command[2] == "show":
            monotonic_lines = "".join(
                f"TimersMonotonic={entry}\n"
                for entry in self.monotonic_entries
            )
            return subprocess.CompletedProcess(
                command,
                0,
                (
                    "ActiveState=active\nResult=success\nPersistent=yes\n"
                    f"RandomizedDelayUSec={self.delay}\n"
                    f"{monotonic_lines}"
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
            return subprocess.CompletedProcess(
                command,
                0 if self.enabled else 1,
                "enabled\n" if self.enabled else "disabled\n",
                "",
            )
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
            original = (
                b"# local operator note\n[Timer]\nOnUnitActiveSec = 2h\n"
                b"RandomizedDelaySec=120\nPersistent=true\n"
            )
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

    def test_compound_duration_components_are_summed(self) -> None:
        self.assertEqual(_duration_seconds("1h 30min"), 5_400)
        self.assertEqual(_duration_seconds("3min 20s"), 200)
        self.assertEqual(_duration_seconds("1.5s 499ms 1000us"), 2)

    def test_exact_unitless_zero_is_accepted_but_other_unitless_values_are_rejected(self) -> None:
        runner = FakeRunner(delay="0")
        with tempfile.TemporaryDirectory() as temporary:
            observation = SystemdUserManager(
                Path(temporary) / "override.conf",
                runner=runner,
            ).observe_timer()

        self.assertEqual(_duration_seconds("0"), 0)
        self.assertEqual(observation.randomized_delay_seconds, 0)
        with self.assertRaises(SystemdCommandError):
            _duration_seconds("1")

    def test_full_timers_monotonic_duration_is_extracted(self) -> None:
        runner = FakeRunner(interval="1h 30min", delay="3min 20s")
        with tempfile.TemporaryDirectory() as temporary:
            observation = SystemdUserManager(
                Path(temporary) / "override.conf",
                runner=runner,
            ).observe_timer()
        self.assertEqual(observation.interval_minutes, 90)
        self.assertEqual(observation.randomized_delay_seconds, 200)

    def test_repeated_timers_monotonic_selects_on_unit_active_in_either_order(self) -> None:
        on_unit_active = "{ OnUnitActiveUSec=2h ; next_elapse=4h }"
        on_boot = "{ OnBootUSec=2h ; next_elapse=4h }"
        for entries in (
            (on_unit_active, on_boot),
            (on_boot, on_unit_active),
        ):
            with self.subTest(entries=entries), tempfile.TemporaryDirectory() as temporary:
                observation = SystemdUserManager(
                    Path(temporary) / "override.conf",
                    runner=FakeRunner(monotonic_entries=entries),
                ).observe_timer()
                self.assertEqual(observation.interval_minutes, 120)


if __name__ == "__main__":
    unittest.main()
