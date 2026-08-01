"""Bounded, shell-free observation and mutation of the Wirtel user timer."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .settings_io import FileBackup, SecureFile

_TIMER_UNIT = "wirtelprimpf.timer"
_DURATION_COMPONENT_RE = re.compile(
    r"([0-9]+(?:\.[0-9]+)?)(us|µs|μs|ms|min|s|h|d)"
)
Runner = Callable[[list[str], float], subprocess.CompletedProcess[str]]


class SystemdCommandError(RuntimeError):
    """A redacted systemd operation failure."""


@dataclass(frozen=True, slots=True)
class TimerConfiguration:
    enabled: bool
    interval_minutes: int
    randomized_delay_seconds: int
    persistent: bool


@dataclass(frozen=True, slots=True)
class TimerObservation:
    enabled: bool
    active: bool
    active_state: str
    interval_minutes: int
    randomized_delay_seconds: int
    persistent: bool
    last_trigger: str | None
    next_run: str | None
    result: str

    @classmethod
    def from_configuration(
        cls,
        configuration: TimerConfiguration,
        active: bool,
    ) -> TimerObservation:
        return cls(
            enabled=configuration.enabled,
            active=bool(active),
            active_state="active" if active else "inactive",
            interval_minutes=configuration.interval_minutes,
            randomized_delay_seconds=configuration.randomized_delay_seconds,
            persistent=configuration.persistent,
            last_trigger=None,
            next_run=None,
            result="unknown",
        )

    def configuration(self) -> TimerConfiguration:
        return TimerConfiguration(
            self.enabled,
            self.interval_minutes,
            self.randomized_delay_seconds,
            self.persistent,
        )

    def revision_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "active": self.active,
            "active_state": self.active_state,
            "interval_minutes": self.interval_minutes,
            "randomized_delay_seconds": self.randomized_delay_seconds,
            "persistent": self.persistent,
            "last_trigger": self.last_trigger,
            "next_run": self.next_run,
            "result": self.result,
        }


def _default_runner(command: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        raise SystemdCommandError("cannot execute bounded systemctl command") from exc


def _duration_seconds(value: str) -> int:
    normalized = value.strip()
    if normalized == "0":
        return 0
    total_seconds = 0.0
    position = 0
    component_found = False
    multipliers = {
        "us": 0.000001,
        "µs": 0.000001,
        "μs": 0.000001,
        "ms": 0.001,
        "s": 1.0,
        "min": 60.0,
        "h": 3600.0,
        "d": 86_400.0,
    }
    for match in _DURATION_COMPONENT_RE.finditer(normalized):
        if normalized[position : match.start()].strip():
            raise SystemdCommandError("systemctl returned an invalid timer duration")
        component_found = True
        total_seconds += float(match.group(1)) * multipliers[match.group(2)]
        position = match.end()
    if not component_found or normalized[position:].strip():
        raise SystemdCommandError("systemctl returned an invalid timer duration")
    return round(total_seconds)


def _boolean(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"yes", "true", "1"}:
        return True
    if normalized in {"no", "false", "0"}:
        return False
    raise SystemdCommandError("systemctl returned an invalid boolean")


class SystemdUserManager:
    def __init__(
        self,
        dropin_path: Path,
        *,
        runner: Runner = _default_runner,
        command_timeout_seconds: float = 10.0,
    ) -> None:
        self.dropin_path = Path(dropin_path)
        self.runner = runner
        self.command_timeout_seconds = command_timeout_seconds

    def _run(self, arguments: list[str], *, allow_disabled: bool = False) -> subprocess.CompletedProcess[str]:
        command = ["systemctl", "--user", *arguments]
        try:
            result = self.runner(command, self.command_timeout_seconds)
        except SystemdCommandError:
            raise
        except (OSError, subprocess.SubprocessError) as exc:
            raise SystemdCommandError("cannot execute bounded systemctl command") from exc
        if result.returncode != 0 and not (allow_disabled and result.returncode in {1, 3, 4}):
            raise SystemdCommandError("systemctl command failed")
        return result

    def render_dropin(self, configuration: TimerConfiguration) -> str:
        if configuration.interval_minutes < 1:
            raise SystemdCommandError("timer interval must be positive")
        if configuration.randomized_delay_seconds < 0:
            raise SystemdCommandError("timer randomized delay must not be negative")
        persistent = "true" if configuration.persistent else "false"
        return (
            "[Timer]\n"
            "OnCalendar=\n"
            "OnBootSec=\n"
            "OnUnitActiveSec=\n"
            f"OnBootSec={configuration.interval_minutes}min\n"
            f"OnUnitActiveSec={configuration.interval_minutes}min\n"
            f"RandomizedDelaySec={configuration.randomized_delay_seconds}\n"
            f"Persistent={persistent}\n"
        )

    def observe_timer(self) -> TimerObservation:
        enabled_result = self._run(["is-enabled", _TIMER_UNIT], allow_disabled=True)
        enabled = enabled_result.returncode == 0 and enabled_result.stdout.strip() in {
            "enabled",
            "enabled-runtime",
            "linked",
            "linked-runtime",
            "alias",
        }
        properties = (
            "ActiveState",
            "Result",
            "Persistent",
            "RandomizedDelayUSec",
            "TimersMonotonic",
            "LastTriggerUSec",
            "NextElapseUSecRealtime",
        )
        arguments = ["show", _TIMER_UNIT]
        for name in properties:
            arguments.extend(["--property", name])
        result = self._run(arguments)
        values: dict[str, list[str]] = {}
        for line in result.stdout.splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                values.setdefault(key, []).append(value.strip())
        try:
            interval_value = next(
                (
                    match
                    for value in values["TimersMonotonic"]
                    if (
                        match := re.search(
                            r"(?:^|[ {;])OnUnitActiveUSec=([^;}]+)",
                            value,
                        )
                    )
                ),
                None,
            )
            if interval_value is None:
                raise KeyError("OnUnitActiveUSec")
            interval_seconds = _duration_seconds(interval_value.group(1))
            delay_seconds = _duration_seconds(values["RandomizedDelayUSec"][-1])
            persistent = _boolean(values["Persistent"][-1])
            active_state = values["ActiveState"][-1]
        except (IndexError, KeyError) as exc:
            raise SystemdCommandError("systemctl returned incomplete timer state") from exc
        if interval_seconds <= 0 or interval_seconds % 60:
            raise SystemdCommandError("effective timer interval is not a whole positive minute")
        return TimerObservation(
            enabled=enabled,
            active=active_state == "active",
            active_state=active_state or "unknown",
            interval_minutes=interval_seconds // 60,
            randomized_delay_seconds=delay_seconds,
            persistent=persistent,
            last_trigger=(values.get("LastTriggerUSec") or [""])[-1] or None,
            next_run=(values.get("NextElapseUSecRealtime") or [""])[-1] or None,
            result=(values.get("Result") or [""])[-1] or "unknown",
        )

    @staticmethod
    def _require(
        configuration: TimerConfiguration,
        observation: TimerObservation,
        *,
        active: bool | None = None,
    ) -> None:
        matches = (
            observation.enabled == configuration.enabled
            and observation.interval_minutes == configuration.interval_minutes
            and observation.randomized_delay_seconds == configuration.randomized_delay_seconds
            and observation.persistent == configuration.persistent
        )
        if active is not None:
            matches = matches and observation.active == active
        if not matches:
            raise SystemdCommandError("effective timer state does not match requested configuration")

    def apply_timer(self, configuration: TimerConfiguration) -> TimerObservation:
        SecureFile(self.dropin_path, private=False).replace_bytes(self.render_dropin(configuration).encode("utf-8"))
        self._run(["daemon-reload"])
        if configuration.enabled:
            self._run(["enable", "--now", _TIMER_UNIT])
            self._run(["restart", _TIMER_UNIT])
        else:
            self._run(["disable", "--now", _TIMER_UNIT])
        observation = self.observe_timer()
        self._require(configuration, observation, active=configuration.enabled)
        return observation

    def restore_timer(
        self,
        configuration: TimerConfiguration,
        was_active: bool,
        dropin_backup: FileBackup | None,
    ) -> TimerObservation:
        if dropin_backup is not None:
            SecureFile(self.dropin_path, private=False).restore(dropin_backup)
        self._run(["daemon-reload"])
        self._run(["enable" if configuration.enabled else "disable", _TIMER_UNIT])
        self._run(["start" if was_active else "stop", _TIMER_UNIT])
        observation = self.observe_timer()
        self._require(configuration, observation, active=was_active)
        return observation
