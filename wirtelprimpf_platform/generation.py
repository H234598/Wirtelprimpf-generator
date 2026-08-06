"""Safe, fixed-mode starts for the local Wirtelprimpf generator."""

from __future__ import annotations

import subprocess
import threading
from collections.abc import Callable
from typing import Literal

GenerationMode = Literal["story", "atelier"]
GENERATION_UNITS: dict[GenerationMode, str] = {
    "story": "wirtelprimpf.service",
    "atelier": "wirtelprimpf-atelier.service",
}
_ALL_GENERATION_UNITS = tuple(GENERATION_UNITS.values())
Runner = Callable[[list[str], float], subprocess.CompletedProcess[str]]


class GenerationError(RuntimeError):
    """Base class for bounded local generation-control failures."""


class GenerationBusy(GenerationError):
    """A generator run is already active."""


class GenerationUnavailable(GenerationError):
    """The user service manager could not accept a generation request."""


def _default_runner(command: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        raise GenerationUnavailable("generator control unavailable") from exc


class SystemdGenerationController:
    """Start only the two predeclared user services, never arbitrary commands."""

    def __init__(
        self,
        *,
        runner: Runner = _default_runner,
        command_timeout_seconds: float = 5.0,
    ) -> None:
        self.runner = runner
        self.command_timeout_seconds = command_timeout_seconds
        self._lock = threading.Lock()

    def _run(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        try:
            result = self.runner(command, self.command_timeout_seconds)
        except GenerationUnavailable:
            raise
        except (OSError, subprocess.SubprocessError) as exc:
            raise GenerationUnavailable("generator control unavailable") from exc
        if not isinstance(result, subprocess.CompletedProcess):
            raise GenerationUnavailable("generator control returned no result")
        return result

    def _is_active(self, unit: str) -> bool:
        result = self._run(["systemctl", "--user", "is-active", "--quiet", unit])
        if result.returncode == 0:
            return True
        if result.returncode in {3, 4}:
            return False
        raise GenerationUnavailable("generator status unavailable")

    def trigger(self, mode: GenerationMode) -> dict[str, str]:
        if mode not in GENERATION_UNITS:
            raise GenerationUnavailable("unknown generation mode")
        unit = GENERATION_UNITS[mode]
        with self._lock:
            if any(self._is_active(candidate) for candidate in _ALL_GENERATION_UNITS):
                raise GenerationBusy("a generator run is already active")
            result = self._run(["systemctl", "--user", "--no-block", "start", unit])
            if result.returncode != 0:
                raise GenerationUnavailable("generator start was rejected")
        return {"mode": mode, "unit": unit, "state": "queued"}
