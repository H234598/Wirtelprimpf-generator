from __future__ import annotations

import subprocess
import unittest

from wirtelprimpf_platform.generation import (
    GenerationBusy,
    GenerationUnavailable,
    SystemdGenerationController,
)


class FakeRunner:
    def __init__(self, *, active: str | None = None, start_status: int = 0) -> None:
        self.active = active
        self.start_status = start_status
        self.commands: list[list[str]] = []

    def __call__(self, command: list[str], _timeout: float) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        if command[2:4] == ["is-active", "--quiet"]:
            status = 0 if command[4] == self.active else 3
        else:
            status = self.start_status
        return subprocess.CompletedProcess(command, status, "", "")


class GenerationControllerTests(unittest.TestCase):
    def test_story_and_atelier_are_fixed_to_predeclared_units(self) -> None:
        runner = FakeRunner()
        controller = SystemdGenerationController(runner=runner)

        self.assertEqual(
            controller.trigger("story"),
            {"mode": "story", "unit": "wirtelprimpf.service", "state": "queued"},
        )
        self.assertEqual(
            controller.trigger("atelier"),
            {"mode": "atelier", "unit": "wirtelprimpf-atelier.service", "state": "queued"},
        )
        starts = [command for command in runner.commands if command[2] == "--no-block"]
        self.assertEqual(
            starts,
            [
                ["systemctl", "--user", "--no-block", "start", "wirtelprimpf.service"],
                ["systemctl", "--user", "--no-block", "start", "wirtelprimpf-atelier.service"],
            ],
        )

    def test_active_generator_blocks_both_modes_without_starting_another(self) -> None:
        runner = FakeRunner(active="wirtelprimpf.service")
        controller = SystemdGenerationController(runner=runner)

        with self.assertRaises(GenerationBusy):
            controller.trigger("atelier")
        self.assertFalse(any(command[2] == "--no-block" for command in runner.commands))

    def test_rejected_start_is_reported_without_claiming_queueing(self) -> None:
        runner = FakeRunner(start_status=1)
        controller = SystemdGenerationController(runner=runner)

        with self.assertRaises(GenerationUnavailable):
            controller.trigger("story")


if __name__ == "__main__":
    unittest.main()
