from __future__ import annotations

import copy
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from unittest import mock

from wirtelprimpf_platform.settings_schema import (
    SETTING_SPECS,
    choices_payload,
    invariants_payload,
)

ROOT = Path(__file__).resolve().parents[1]
SYNC_PATH = ROOT / "files" / "wirtelprimfgenerator@H234598" / "settings_sync.py"
SPEC = importlib.util.spec_from_file_location(
    "wirtelprimpf_applet_settings_sync_test",
    SYNC_PATH,
)
assert SPEC is not None and SPEC.loader is not None
SYNC = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SYNC
SPEC.loader.exec_module(SYNC)
DirtySnapshotState = SYNC.DirtySnapshotState
SettingsCliClient = SYNC.SettingsCliClient
SettingsSyncCoordinator = SYNC.SettingsSyncCoordinator


def snapshot(revision: str, **settings: object) -> dict[str, object]:
    public_settings = {
        key: spec.default
        for key, spec in SETTING_SPECS.items()
        if spec.applet_visible
    }
    public_settings.update(settings)
    return {
        "ok": True,
        "schema_version": "2.0.0",
        "revision": revision,
        "settings": public_settings,
        "choices": choices_payload(),
        "secrets": {
            "openai_api_key_present": False,
            "cloudflare_api_token_present": False,
        },
        "invariants": invariants_payload(),
        "warnings": [],
    }


class DeferredExecutor:
    def __init__(self) -> None:
        self.pending: list[tuple[Future, object, tuple[object, ...]]] = []
        self.submitted = 0
        self.shutdown_calls: list[dict[str, object]] = []

    def submit(self, function, *args):
        future = Future()
        self.pending.append((future, function, args))
        self.submitted += 1
        return future

    def run_next(self, index: int = 0) -> Future:
        future, function, args = self.pending.pop(index)
        try:
            future.set_result(function(*args))
        except BaseException as exc:  # deliberate future simulation
            future.set_exception(exc)
        return future

    def shutdown(self, **kwargs) -> None:
        self.shutdown_calls.append(dict(kwargs))
        for future, _function, _args in self.pending:
            future.cancel()
        self.pending.clear()


class CompletionQueue:
    def __init__(self) -> None:
        self.pending: list[tuple[object, tuple[object, ...]]] = []

    def __call__(self, callback, *args):
        self.pending.append((callback, args))
        return len(self.pending)

    def run_next(self, index: int = 0):
        callback, args = self.pending.pop(index)
        return callback(*args)


class FakeScheduler:
    def __init__(self) -> None:
        self.handles: list[dict[str, object]] = []

    def call_later(self, milliseconds: int, callback):
        handle = {
            "kind": "later",
            "delay": milliseconds,
            "callback": callback,
            "cancelled": False,
        }
        self.handles.append(handle)
        return handle

    def call_repeated(self, seconds: int, callback):
        handle = {
            "kind": "repeated",
            "delay": seconds,
            "callback": callback,
            "cancelled": False,
        }
        self.handles.append(handle)
        return handle

    def cancel(self, handle) -> None:
        handle["cancelled"] = True

    def fire(self, handle):
        if handle["cancelled"]:
            return None
        return handle["callback"]()


class FakeMonitor:
    def __init__(self, target: str, callback) -> None:
        self.target = target
        self.callback = callback
        self.cancelled = False

    def emit(self, changed_path: str) -> None:
        self.callback(changed_path)

    def cancel(self) -> None:
        self.cancelled = True


class FakeMonitorFactory:
    def __init__(self) -> None:
        self.monitors: list[FakeMonitor] = []

    def __call__(self, target: str, callback) -> FakeMonitor:
        monitor = FakeMonitor(target, callback)
        self.monitors.append(monitor)
        return monitor


class RecoveringMonitorFactory(FakeMonitorFactory):
    def __init__(self, failing_target: str) -> None:
        super().__init__()
        self.failing_target = failing_target
        self.failed_once = False

    def __call__(self, target: str, callback) -> FakeMonitor:
        if target == self.failing_target and not self.failed_once:
            self.failed_once = True
            raise OSError("simulated missing monitor parent")
        return super().__call__(target, callback)


class QueueClient:
    def __init__(self, snapshots=(), applies=()) -> None:
        self.snapshots = list(snapshots)
        self.applies = list(applies)
        self.snapshot_calls = 0
        self.apply_requests: list[dict[str, object]] = []
        self.call_threads: list[int] = []
        self.called = threading.Event()

    def snapshot(self):
        self.snapshot_calls += 1
        self.call_threads.append(threading.get_ident())
        self.called.set()
        result = self.snapshots.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result

    def apply(self, request):
        self.apply_requests.append(request)
        self.call_threads.append(threading.get_ident())
        self.called.set()
        result = self.applies.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result


def coordinator_for(
    client: QueueClient,
    *,
    on_snapshot=lambda *_args: None,
    on_error=lambda *_args: None,
    on_busy=lambda *_args: None,
    on_save_result=lambda *_args: None,
):
    scheduler = FakeScheduler()
    monitors = FakeMonitorFactory()
    executor = DeferredExecutor()
    completions = CompletionQueue()
    coordinator = SettingsSyncCoordinator(
        client=client,
        scheduler=scheduler,
        monitor_factory=monitors,
        executor=executor,
        completion_dispatch=completions,
        on_snapshot=on_snapshot,
        on_error=on_error,
        on_busy=on_busy,
        on_save_result=on_save_result,
    )
    return coordinator, scheduler, monitors, executor, completions


class AppletSettingsSyncTests(unittest.TestCase):
    def test_public_contract_exports_operation_lock_api(self) -> None:
        self.assertTrue(
            {"SettingsOperationLockError", "exclusive_settings_lock"}.issubset(
                set(SYNC.__all__)
            )
        )

    def test_operation_lock_accepts_expanduser_absolute_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / "home"
            home.mkdir()
            lock_path = home / ".config" / "wirtelprimpf" / "settings.lock"

            with (
                mock.patch.dict(os.environ, {"HOME": str(home)}),
                SYNC.exclusive_settings_lock(
                    "~/.config/wirtelprimpf/settings.lock", timeout_seconds=0
                ),
            ):
                self.assertTrue(lock_path.is_file())

            self.assertEqual(lock_path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(lock_path.parent.stat().st_mode & 0o777, 0o700)

    def test_operation_lock_still_rejects_relative_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            previous_directory = os.getcwd()
            os.chdir(temporary)
            try:
                with (
                    self.assertRaisesRegex(
                        SYNC.SettingsOperationLockError,
                        "Einstellungen konnten nicht sicher gesperrt werden",
                    ),
                    SYNC.exclusive_settings_lock(
                        "relative/settings.lock", timeout_seconds=0
                    ),
                ):
                    self.fail("relative lock path unexpectedly accepted")
                self.assertFalse(Path("relative/settings.lock").exists())
            finally:
                os.chdir(previous_directory)

    def test_operation_lock_rejects_a_symlinked_parent_without_leaking_its_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            real_parent = root / "real-private-parent"
            real_parent.mkdir()
            linked_parent = root / "linked-private-parent"
            linked_parent.symlink_to(real_parent, target_is_directory=True)
            lock_path = linked_parent / "settings.lock"

            with (
                self.assertRaisesRegex(
                    SYNC.SettingsOperationLockError,
                    "Einstellungen konnten nicht sicher gesperrt werden",
                ) as caught,
                SYNC.exclusive_settings_lock(str(lock_path), timeout_seconds=0),
            ):
                self.fail("symlinked parent unexpectedly accepted")

            self.assertNotIn(str(lock_path), str(caught.exception))

    def test_operation_lock_rejects_a_nonregular_target_without_leaking_its_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            lock_path = Path(temporary) / "settings.lock"
            os.mkfifo(lock_path)

            with (
                self.assertRaisesRegex(
                    SYNC.SettingsOperationLockError,
                    "Einstellungen konnten nicht sicher gesperrt werden",
                ) as caught,
                SYNC.exclusive_settings_lock(str(lock_path), timeout_seconds=0),
            ):
                self.fail("nonregular target unexpectedly accepted")

            self.assertNotIn(str(lock_path), str(caught.exception))

    def test_dirty_state_keeps_local_value_and_marks_external_conflict(self) -> None:
        state = DirtySnapshotState(
            snapshot("r1", operandi="story", image_model="gpt-image-2")
        )
        state.change("image_model", "gpt-image-1.5")
        visible = state.merge_snapshot(
            snapshot("r2", operandi="both", image_model="gpt-image-1")
        )
        self.assertEqual(visible["operandi"], "both")
        self.assertEqual(visible["image_model"], "gpt-image-1.5")
        self.assertEqual(state.conflicts, {"image_model"})

    def test_returning_to_typed_server_value_clears_the_public_draft(self) -> None:
        state = DirtySnapshotState(
            snapshot("r1", timer_enabled=True, story_document="story-old.md")
        )
        state.change("story_document", "story-new.md")
        state.change("story_document", "story-old.md")

        self.assertEqual(state.dirty, set())
        self.assertEqual(state.base_values, {})
        self.assertIsNone(state.base_revision)

        state.change("timer_enabled", 1)
        self.assertEqual(state.dirty, {"timer_enabled"})

    def test_catalog_options_keep_one_labeled_legacy_value_without_cataloguing_it(self) -> None:
        self.assertEqual(
            SYNC.catalog_options(
                ["gpt-5.5", "gpt-5-mini"],
                "retired-story-model",
            ),
            [
                (
                    "retired-story-model",
                    "retired-story-model · konfiguriert · nicht mehr im empfohlenen Katalog",
                    True,
                ),
                ("gpt-5.5", "gpt-5.5", False),
                ("gpt-5-mini", "gpt-5-mini", False),
            ],
        )
        self.assertEqual(
            SYNC.catalog_options(["gpt-image-2"], "gpt-image-2"),
            [("gpt-image-2", "gpt-image-2", False)],
        )

    def test_cli_apply_keeps_secrets_out_of_argv_and_receives_the_watchdog_bound(self) -> None:
        calls = []

        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return subprocess.CompletedProcess(command, 0, json.dumps(snapshot("b" * 64)), "")

        client = SettingsCliClient(
            "/trusted/wirtelprimpf-settings",
            runner=runner,
            executable_check=lambda _path: True,
        )
        client.apply(
            {
                "base_revision": "a" * 64,
                "changes": {},
                "base_values": {},
                "secret_actions": {
                    "openai_api_key": {
                        "action": "replace",
                        "value": "private-secret-value",
                    }
                },
            }
        )
        command, kwargs = calls[0]
        self.assertNotIn("private-secret-value", " ".join(command))
        self.assertIn("private-secret-value", kwargs["input"])
        self.assertEqual(kwargs["timeout"], SYNC.APPLY_WATCHDOG_SECONDS)
        self.assertFalse(kwargs["shell"])

    def test_snapshot_uses_the_short_read_timeout(self) -> None:
        calls = []

        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return subprocess.CompletedProcess(command, 0, json.dumps(snapshot("b" * 64)), "")

        client = SettingsCliClient(
            "/trusted/wirtelprimpf-settings",
            runner=runner,
            executable_check=lambda _path: True,
        )
        client.snapshot()
        self.assertEqual(calls[0][1]["timeout"], 10)

    def test_apply_watchdog_returns_without_signalling_and_allows_only_one_reaper(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-apply-watchdog-") as temporary:
            root = Path(temporary)
            executable = root / "settings-cli"
            starts = root / "starts"
            pid_file = root / "pid"
            signalled = root / "signalled"
            completed = root / "completed"
            payload = json.dumps(snapshot("d" * 64))
            executable.write_text(
                f"#!{sys.executable}\n"
                "import pathlib, signal, sys, time\n"
                f"starts = pathlib.Path({str(starts)!r})\n"
                f"pid_file = pathlib.Path({str(pid_file)!r})\n"
                f"signalled = pathlib.Path({str(signalled)!r})\n"
                f"completed = pathlib.Path({str(completed)!r})\n"
                "with starts.open('a', encoding='utf-8') as stream:\n"
                "    stream.write(sys.argv[1] + '\\n')\n"
                "sys.stdin.read()\n"
                "def record_signal(number, _frame):\n"
                "    signalled.write_text(str(number), encoding='utf-8')\n"
                "signal.signal(signal.SIGTERM, record_signal)\n"
                "signal.signal(signal.SIGINT, record_signal)\n"
                "if sys.argv[1] == 'apply':\n"
                "    pid_file.write_text(str(__import__('os').getpid()), encoding='utf-8')\n"
                "    time.sleep(0.5)\n"
                "completed.write_text(sys.argv[1], encoding='utf-8')\n"
                f"print({payload!r})\n",
                encoding="utf-8",
            )
            executable.chmod(0o700)
            client = SettingsCliClient(
                str(executable),
                apply_watchdog_seconds=0.05,
            )

            started = time.monotonic()
            with self.assertRaisesRegex(SYNC.SettingsCliError, "Hintergrund"):
                client.apply(
                    {
                        "base_revision": "a" * 64,
                        "changes": {},
                        "base_values": {},
                        "secret_actions": {},
                    }
                )
            self.assertLess(time.monotonic() - started, 0.3)
            pid_deadline = time.monotonic() + 1
            while not pid_file.is_file() and time.monotonic() < pid_deadline:
                threading.Event().wait(0.01)
            self.assertTrue(pid_file.is_file())
            child_pid = int(pid_file.read_text(encoding="utf-8"))
            os.kill(child_pid, 0)
            self.assertFalse(signalled.exists())
            reaper = client._active_reaper
            self.assertIsNotNone(reaper)
            assert reaper is not None
            self.assertTrue(reaper.is_alive())

            with self.assertRaisesRegex(SYNC.SettingsCliError, "läuft noch"):
                client.snapshot()
            self.assertIs(client._active_reaper, reaper)
            self.assertEqual(starts.read_text(encoding="utf-8").splitlines(), ["apply"])

            deadline = time.monotonic() + 2
            while not completed.exists() and time.monotonic() < deadline:
                threading.Event().wait(0.01)
            self.assertTrue(completed.exists())
            while client._active_reaper is not None and time.monotonic() < deadline:
                threading.Event().wait(0.01)
            self.assertIsNone(client._active_reaper)
            self.assertFalse(signalled.exists())
            self.assertEqual(client.snapshot()["revision"], "d" * 64)
            self.assertEqual(
                starts.read_text(encoding="utf-8").splitlines(),
                ["apply", "snapshot"],
            )

    def test_apply_pump_failure_detaches_without_signalling_and_reaps_later(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-apply-pump-") as temporary:
            root = Path(temporary)
            executable = root / "settings-cli"
            pid_file = root / "pid"
            signalled = root / "signalled"
            completed = root / "completed"
            executable.write_text(
                f"#!{sys.executable}\n"
                "import os, pathlib, signal, sys, time\n"
                f"pid_file = pathlib.Path({str(pid_file)!r})\n"
                f"signalled = pathlib.Path({str(signalled)!r})\n"
                f"completed = pathlib.Path({str(completed)!r})\n"
                "def record_signal(number, _frame):\n"
                "    signalled.write_text(str(number), encoding='utf-8')\n"
                "signal.signal(signal.SIGTERM, record_signal)\n"
                "signal.signal(signal.SIGINT, record_signal)\n"
                "pid_file.write_text(str(os.getpid()), encoding='utf-8')\n"
                "sys.stdin.read()\n"
                "time.sleep(0.1)\n"
                "completed.write_text('done', encoding='utf-8')\n"
                f"print({json.dumps(snapshot('e' * 64))!r})\n",
                encoding="utf-8",
            )
            executable.chmod(0o700)
            client = SettingsCliClient(str(executable), apply_watchdog_seconds=2)
            original_pump = SYNC._BoundedProcessIO.pump
            failed_once = False

            def fail_once(process_io, timeout_seconds):
                nonlocal failed_once
                if not failed_once:
                    failed_once = True
                    raise OSError("simulated selector/pump failure")
                return original_pump(process_io, timeout_seconds)

            with (
                mock.patch.object(SYNC._BoundedProcessIO, "pump", new=fail_once),
                self.assertRaisesRegex(SYNC.SettingsCliError, "sicher ausgeführt"),
            ):
                client.apply(
                    {
                        "base_revision": "a" * 64,
                        "changes": {},
                        "base_values": {},
                        "secret_actions": {},
                    }
                )

            pid_deadline = time.monotonic() + 1
            while not pid_file.is_file() and time.monotonic() < pid_deadline:
                threading.Event().wait(0.01)
            self.assertTrue(pid_file.is_file())
            os.kill(int(pid_file.read_text(encoding="utf-8")), 0)
            self.assertFalse(signalled.exists())
            deadline = time.monotonic() + 2
            while client._active_process is not None and time.monotonic() < deadline:
                threading.Event().wait(0.01)
            self.assertTrue(completed.is_file())
            self.assertIsNone(client._active_process)
            self.assertIsNone(client._active_process_io)
            self.assertFalse(signalled.exists())

    def test_reaper_start_failure_keeps_live_apply_tracked_and_fail_closed(self) -> None:
        client = SettingsCliClient(
            "/trusted/wirtelprimpf-settings",
            executable_check=lambda _path: True,
        )
        process = mock.Mock()
        process.poll.return_value = None
        process_io = mock.Mock(process=process)
        failed_thread = mock.Mock()
        failed_thread.is_alive.return_value = False
        failed_thread.start.side_effect = RuntimeError("no thread capacity")

        with mock.patch.object(SYNC.threading, "Thread", return_value=failed_thread):
            self.assertFalse(client._detach_for_reap(process_io))

        self.assertIs(client._active_process, process)
        self.assertIs(client._active_process_io, process_io)
        self.assertIs(client._active_reaper, failed_thread)
        process.kill.assert_not_called()
        process.wait.assert_not_called()
        process_io.close.assert_not_called()
        with self.assertRaisesRegex(SYNC.SettingsCliError, "läuft noch"):
            client._reject_if_process_still_active()

    def test_bounded_pipe_close_is_idempotent_and_drops_delivered_secret_input(self) -> None:
        process = subprocess.Popen(  # nosec B603 -- fixed local executable
            ["/bin/cat"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
            bufsize=0,
            shell=False,
        )
        process_io = SYNC._BoundedProcessIO(process, b"private-secret-input")
        process_io.initialize()
        deadline = time.monotonic() + 2
        while not process_io.complete and time.monotonic() < deadline:
            process_io.pump(0.05)

        self.assertTrue(process_io.complete)
        self.assertEqual(process_io.input_bytes, b"")
        self.assertEqual(bytes(process_io.stdout), b"private-secret-input")
        process.wait()
        process_io.close()
        process_io.close()
        assert process.stdin is not None
        assert process.stdout is not None
        assert process.stderr is not None
        self.assertTrue(process.stdin.closed)
        self.assertTrue(process.stdout.closed)
        self.assertTrue(process.stderr.closed)

    def test_selector_setup_failure_uses_bounded_direct_pipe_fallback(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-selector-fallback-") as temporary:
            executable = Path(temporary) / "settings-cli"
            executable.write_text(
                f"#!{sys.executable}\n"
                "import sys\n"
                "sys.stdin.read()\n"
                f"print({json.dumps(snapshot('f' * 64))!r})\n",
                encoding="utf-8",
            )
            executable.chmod(0o700)
            client = SettingsCliClient(str(executable))

            with mock.patch.object(
                SYNC.selectors,
                "DefaultSelector",
                side_effect=OSError("simulated selector setup failure"),
            ):
                self.assertEqual(client.snapshot()["revision"], "f" * 64)

    def test_snapshot_pump_failure_kills_reaps_and_closes_every_pipe(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-snapshot-pump-") as temporary:
            executable = Path(temporary) / "settings-cli"
            executable.write_text(
                f"#!{sys.executable}\n"
                "import time\n"
                "time.sleep(30)\n",
                encoding="utf-8",
            )
            executable.chmod(0o700)
            client = SettingsCliClient(str(executable))
            spawned = []
            real_popen = SYNC.subprocess.Popen

            def capture_popen(*args, **kwargs):
                process = real_popen(*args, **kwargs)
                spawned.append(process)
                return process

            with (
                mock.patch.object(SYNC.subprocess, "Popen", new=capture_popen),
                mock.patch.object(
                    SYNC._BoundedProcessIO,
                    "pump",
                    side_effect=OSError("simulated pump failure"),
                ),
                self.assertRaisesRegex(SYNC.SettingsCliError, "sicher ausgeführt"),
            ):
                client.snapshot()

            self.assertEqual(len(spawned), 1)
            process = spawned[0]
            self.assertIsNotNone(process.poll())
            for stream in (process.stdin, process.stdout, process.stderr):
                assert stream is not None
                self.assertTrue(stream.closed)
            self.assertIsNone(client._active_process)
            self.assertIsNone(client._active_process_io)

    def test_invalid_utf8_snapshot_is_reaped_and_closed_before_decode_error(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-snapshot-decode-") as temporary:
            executable = Path(temporary) / "settings-cli"
            executable.write_text(
                f"#!{sys.executable}\n"
                "import sys\n"
                "sys.stdout.buffer.write(b'\\xff')\n",
                encoding="utf-8",
            )
            executable.chmod(0o700)
            client = SettingsCliClient(str(executable))
            spawned = []
            real_popen = SYNC.subprocess.Popen

            def capture_popen(*args, **kwargs):
                process = real_popen(*args, **kwargs)
                spawned.append(process)
                return process

            with (
                mock.patch.object(SYNC.subprocess, "Popen", new=capture_popen),
                self.assertRaisesRegex(SYNC.SettingsCliError, "gültiges JSON"),
            ):
                client.snapshot()

            self.assertEqual(len(spawned), 1)
            process = spawned[0]
            self.assertIsNotNone(process.poll())
            for stream in (process.stdin, process.stdout, process.stderr):
                assert stream is not None
                self.assertTrue(stream.closed)

    def test_oversized_apply_output_is_bounded_without_killing_the_child(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-apply-output-") as temporary:
            root = Path(temporary)
            executable = root / "settings-cli"
            pid_file = root / "pid"
            signalled = root / "signalled"
            completed = root / "completed"
            executable.write_text(
                f"#!{sys.executable}\n"
                "import os, pathlib, signal, sys, time\n"
                f"pid_file = pathlib.Path({str(pid_file)!r})\n"
                f"signalled = pathlib.Path({str(signalled)!r})\n"
                f"completed = pathlib.Path({str(completed)!r})\n"
                "sys.stdin.read()\n"
                "def record_signal(number, _frame):\n"
                "    signalled.write_text(str(number), encoding='utf-8')\n"
                "signal.signal(signal.SIGTERM, record_signal)\n"
                "signal.signal(signal.SIGINT, record_signal)\n"
                "pid_file.write_text(str(os.getpid()), encoding='utf-8')\n"
                f"sys.stdout.buffer.write(b'x' * ({SYNC.MAX_RESPONSE_BYTES} + 65536))\n"
                "sys.stdout.buffer.flush()\n"
                "time.sleep(0.5)\n"
                "completed.write_text('done', encoding='utf-8')\n",
                encoding="utf-8",
            )
            executable.chmod(0o700)
            client = SettingsCliClient(
                str(executable),
                apply_watchdog_seconds=2,
            )

            started = time.monotonic()
            with self.assertRaisesRegex(SYNC.SettingsCliError, "zu groß"):
                client.apply(
                    {
                        "base_revision": "a" * 64,
                        "changes": {},
                        "base_values": {},
                        "secret_actions": {},
                    }
                )
            self.assertLess(time.monotonic() - started, 0.4)
            os.kill(int(pid_file.read_text(encoding="utf-8")), 0)
            self.assertFalse(signalled.exists())
            deadline = time.monotonic() + 2
            while not completed.exists() and time.monotonic() < deadline:
                threading.Event().wait(0.01)
            self.assertTrue(completed.exists())
            while client._active_reaper is not None and time.monotonic() < deadline:
                threading.Event().wait(0.01)
            self.assertIsNone(client._active_reaper)
            self.assertFalse(signalled.exists())

    def test_successful_cli_snapshot_rejects_incomplete_state_or_empty_catalog(self) -> None:
        missing_setting = snapshot("b" * 64)
        missing_setting["settings"].pop("operandi")
        empty_catalog = snapshot("b" * 64)
        empty_catalog["choices"]["operandi"] = []

        for malformed in (missing_setting, empty_catalog):
            client = SettingsCliClient(
                "/trusted/wirtelprimpf-settings",
                runner=lambda command, _payload=malformed, **kwargs: subprocess.CompletedProcess(
                    command,
                    0,
                    json.dumps(_payload),
                    "",
                ),
                executable_check=lambda _path: True,
            )

            with self.subTest(malformed=malformed), self.assertRaisesRegex(
                SYNC.SettingsCliError,
                "vollständig",
            ):
                client.snapshot()

    def test_applet_snapshot_rejects_invalid_numeric_invariants_and_story_range(self) -> None:
        valid = snapshot("b" * 64)
        self.assertTrue(SYNC._is_complete_public_snapshot(valid))

        malformed = []
        missing_bounds = copy.deepcopy(valid)
        missing_bounds["invariants"] = {}
        malformed.append(missing_bounds)
        out_of_bounds = copy.deepcopy(valid)
        out_of_bounds["settings"]["generation_interval_minutes"] = 29
        malformed.append(out_of_bounds)
        reversed_story_range = copy.deepcopy(valid)
        reversed_story_range["settings"]["story_finish_parts_min"] = 8
        reversed_story_range["settings"]["story_finish_parts_max"] = 4
        malformed.append(reversed_story_range)

        for payload in malformed:
            with self.subTest(payload=payload):
                self.assertFalse(SYNC._is_complete_public_snapshot(payload))

    def test_applet_snapshot_contract_matches_the_canonical_visible_schema(self) -> None:
        expected = {
            key: spec.kind
            for key, spec in SETTING_SPECS.items()
            if spec.applet_visible
        }
        self.assertEqual(SYNC.APPLET_SETTING_KINDS, expected)
        self.assertEqual(
            SYNC._APPLET_CHOICE_KEYS,
            frozenset(
                key
                for key, spec in SETTING_SPECS.items()
                if spec.applet_visible and spec.choices
            ),
        )

    def test_nonzero_invalid_and_oversized_cli_responses_fail_closed(self) -> None:
        cases = (
            (
                subprocess.CompletedProcess(
                    ["cli"], 3, json.dumps({"ok": False, "error": "conflict"}), ""
                ),
                "Konflikt",
            ),
            (
                subprocess.CompletedProcess(
                    ["cli"], 7, json.dumps({"ok": False, "error": "unavailable"}), ""
                ),
                "nicht verfügbar",
            ),
            (subprocess.CompletedProcess(["cli"], 0, "not-json", ""), "gültiges JSON"),
            (subprocess.CompletedProcess(["cli"], 0, "[]", ""), "JSON-Objekt"),
            (
                subprocess.CompletedProcess(["cli"], 0, "x" * (1024 * 1024 + 1), ""),
                "zu groß",
            ),
        )
        for result, message in cases:
            client = SettingsCliClient(
                "/trusted/wirtelprimpf-settings",
                runner=lambda command, _result=result, **kwargs: _result,
                executable_check=lambda _path: True,
            )
            with self.subTest(message=message), self.assertRaisesRegex(
                SYNC.SettingsCliError, message
            ):
                client.snapshot()

    def test_saved_snapshot_clears_dirty_state_and_sparse_request_keeps_bases(self) -> None:
        state = DirtySnapshotState(
            snapshot("r1", operandi="story", image_model="gpt-image-2")
        )
        state.change("operandi", "both")
        self.assertEqual(
            state.build_request({"operandi": "both"}, {}),
            {
                "base_revision": "r1",
                "changes": {"operandi": "both"},
                "base_values": {"operandi": "story"},
                "secret_actions": {},
            },
        )
        state.accept_saved_snapshot(
            snapshot("r2", operandi="both", image_model="gpt-image-2")
        )
        self.assertEqual(state.dirty, set())
        self.assertEqual(state.conflicts, set())

    def test_discard_accepts_server_value_and_clears_one_conflict(self) -> None:
        state = DirtySnapshotState(snapshot("r1", story_model="gpt-5-mini"))
        state.change("story_model", "gpt-5.4-mini")
        state.merge_snapshot(snapshot("r2", story_model="gpt-5.5"))
        self.assertEqual(state.discard("story_model"), "gpt-5.5")
        self.assertEqual(state.dirty, set())
        self.assertEqual(state.conflicts, set())
        self.assertEqual(state.base_values, {})
        self.assertIsNone(state.base_revision)

    def test_secret_edit_keeps_original_revision_across_refresh(self) -> None:
        state = DirtySnapshotState(snapshot("r1", operandi="story"))
        state.mark_secret_dirty("openai_api_key")
        state.merge_snapshot(snapshot("r2", operandi="both"))
        request = state.build_request(
            {},
            {
                "openai_api_key": {
                    "action": "replace",
                    "value": "private-secret-value",
                }
            },
        )
        self.assertEqual(request["base_revision"], "r1")
        self.assertEqual(state.secret_dirty, {"openai_api_key"})
        state.discard_secret("openai_api_key")
        self.assertIsNone(state.base_revision)

    def test_discard_secret_removes_its_server_conflict_marker(self) -> None:
        state = DirtySnapshotState(snapshot("r1", operandi="story"))
        state.mark_secret_dirty("cloudflare_api_token")
        state.conflicts.add("cloudflare_api_token")
        state.discard_secret("cloudflare_api_token")
        self.assertNotIn("cloudflare_api_token", state.conflicts)
        self.assertEqual(state.secret_dirty, set())
        self.assertIsNone(state.base_revision)

    def test_default_executable_check_rejects_relative_missing_and_symlink_paths(self) -> None:
        with self.assertRaisesRegex(SYNC.SettingsCliError, "absolut"):
            SettingsCliClient("relative/wirtelprimpf-settings")
        with self.assertRaisesRegex(SYNC.SettingsCliError, "vertrauenswürdige"):
            SettingsCliClient("/definitely/missing/wirtelprimpf-settings")
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "real-cli"
            target.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            os.chmod(target, 0o700)
            link = Path(temporary) / "linked-cli"
            link.symlink_to(target)
            with self.assertRaisesRegex(SYNC.SettingsCliError, "vertrauenswürdige"):
                SettingsCliClient(str(link))

    def test_refresh_coalesces_and_preserves_dirty_fields_observably(self) -> None:
        observed = []
        client = QueueClient(
            snapshots=[
                snapshot("r1", operandi="story", image_model="gpt-image-2"),
                snapshot("r2", operandi="both", image_model="gpt-image-1"),
                snapshot("r3", operandi="classic", image_model="gpt-image-1"),
            ]
        )
        coordinator, _scheduler, _monitors, executor, completions = coordinator_for(
            client,
            on_snapshot=lambda _payload, visible, state: observed.append(
                (dict(visible), set(state.conflicts))
            ),
        )
        coordinator.queue_refresh()
        executor.run_next()
        completions.run_next()
        coordinator.state.change("image_model", "gpt-image-1.5")

        coordinator.queue_refresh()
        coordinator.queue_refresh()
        coordinator.queue_refresh()
        self.assertEqual(executor.submitted, 2)
        executor.run_next()
        completions.run_next()
        self.assertEqual(executor.submitted, 3)
        self.assertEqual(observed[-1][0]["image_model"], "gpt-image-1.5")
        self.assertEqual(observed[-1][0]["operandi"], "both")
        self.assertEqual(observed[-1][1], {"image_model"})
        executor.run_next()
        completions.run_next()
        self.assertEqual(client.snapshot_calls, 3)

    def test_save_epoch_rejects_a_pre_save_refresh_completion(self) -> None:
        client = QueueClient(
            snapshots=[
                snapshot("r1", operandi="story"),
                snapshot("r2-stale", operandi="classic"),
                snapshot("r4", operandi="both"),
            ],
            applies=[snapshot("r3", operandi="both")],
        )
        coordinator, _scheduler, _monitors, executor, completions = coordinator_for(client)
        coordinator.queue_refresh()
        executor.run_next()
        completions.run_next()
        coordinator.state.change("operandi", "both")

        coordinator.queue_refresh()
        executor.run_next()
        request = coordinator.state.build_request({"operandi": "both"}, {})
        self.assertTrue(coordinator.submit_save(request))
        executor.run_next()

        completions.run_next(index=1)
        self.assertEqual(coordinator.state.revision, "r3")
        completions.run_next(index=0)
        self.assertEqual(coordinator.state.revision, "r3")
        self.assertEqual(coordinator.state.visible["operandi"], "both")
        executor.run_next()
        completions.run_next()
        self.assertEqual(coordinator.state.revision, "r4")

    def test_monitor_debounce_focus_and_fallback_are_observable(self) -> None:
        client = QueueClient(snapshots=[snapshot("r1", operandi="story"), snapshot("r2", operandi="both")])
        coordinator, scheduler, monitors, executor, completions = coordinator_for(client)
        paths = ("/config/openai.env", "/systemd/override.conf", "/config/settings-state.json")
        coordinator.start(paths)
        executor.run_next()
        completions.run_next()
        self.assertEqual(len(monitors.monitors), 3)
        repeated = [handle for handle in scheduler.handles if handle["kind"] == "repeated"]
        self.assertEqual([handle["delay"] for handle in repeated], [30])

        monitors.monitors[0].emit("/config/unrelated")
        self.assertEqual(len([h for h in scheduler.handles if h["kind"] == "later"]), 0)
        monitors.monitors[0].emit("/config/openai.env")
        first = scheduler.handles[-1]
        monitors.monitors[0].emit("/config/openai.env")
        second = scheduler.handles[-1]
        self.assertTrue(first["cancelled"])
        self.assertEqual(second["delay"], 250)
        scheduler.fire(second)
        coordinator.focus_refresh()
        self.assertEqual(executor.submitted, 2)
        executor.run_next()
        completions.run_next()
        self.assertEqual(executor.submitted, 3)

    def test_one_monitor_failure_preserves_initial_fallback_focus_and_later_retry(self) -> None:
        paths = (
            "/config/openai.env",
            "/systemd/wirtelprimpf.timer.d/override.conf",
            "/config/settings-state.json",
        )
        client = QueueClient(
            snapshots=[
                snapshot("r1", operandi="story"),
                snapshot("r2", operandi="both"),
                snapshot("r3", operandi="classic"),
            ]
        )
        scheduler = FakeScheduler()
        monitors = RecoveringMonitorFactory(paths[1])
        executor = DeferredExecutor()
        completions = CompletionQueue()
        errors = []
        coordinator = SettingsSyncCoordinator(
            client=client,
            scheduler=scheduler,
            monitor_factory=monitors,
            executor=executor,
            completion_dispatch=completions,
            on_error=errors.append,
        )

        self.assertTrue(coordinator.start(paths))
        self.assertEqual(len(monitors.monitors), 2)
        self.assertEqual(executor.submitted, 1)
        executor.run_next()
        completions.run_next()
        self.assertEqual(coordinator.state.revision, "r1")

        fallback = next(
            handle for handle in scheduler.handles if handle["kind"] == "repeated"
        )
        self.assertTrue(scheduler.fire(fallback))
        self.assertEqual(len(monitors.monitors), 3)
        executor.run_next()
        completions.run_next()
        self.assertEqual(coordinator.state.revision, "r2")

        self.assertFalse(coordinator.focus_refresh())
        executor.run_next()
        completions.run_next()
        self.assertEqual(coordinator.state.revision, "r3")
        self.assertEqual(
            errors,
            ["Eine lokale Einstellungsdatei kann derzeit nicht überwacht werden"],
        )

    def test_dispose_cancels_sources_monitors_executor_and_late_completion(self) -> None:
        observed = []
        client = QueueClient(snapshots=[snapshot("r1", operandi="story")])
        coordinator, scheduler, monitors, executor, completions = coordinator_for(
            client, on_snapshot=lambda *_args: observed.append("snapshot")
        )
        coordinator.start(("/config/openai.env",))
        monitors.monitors[0].emit("/config/openai.env")
        handles = list(scheduler.handles)
        executor.run_next()
        self.assertEqual(len(completions.pending), 1)
        coordinator.dispose()
        completions.run_next()

        self.assertTrue(all(handle["cancelled"] for handle in handles))
        self.assertTrue(all(monitor.cancelled for monitor in monitors.monitors))
        self.assertEqual(
            executor.shutdown_calls,
            [{"wait": False, "cancel_futures": True}],
        )
        self.assertEqual(observed, [])
        self.assertFalse(coordinator.queue_refresh())

    def test_dispose_logs_monitor_cancellation_type_without_sensitive_text(self) -> None:
        secret = "OPENAI_API_KEY=must-never-escape"

        class FailingMonitor:
            def cancel(self) -> None:
                raise RuntimeError(secret)

        coordinator, _scheduler, _monitors, _executor, _completions = coordinator_for(
            QueueClient()
        )
        coordinator._monitors.append(FailingMonitor())
        with self.assertLogs(SYNC.__name__, level="DEBUG") as captured:
            coordinator.dispose()

        rendered = "\n".join(captured.output)
        self.assertIn("RuntimeError", rendered)
        self.assertNotIn(secret, rendered)
        self.assertEqual(coordinator._monitors, [])

    def test_watchdog_save_failure_releases_coordinator_for_a_later_save(self) -> None:
        busy = []
        client = QueueClient(
            snapshots=[snapshot("r1", operandi="story")],
            applies=[SYNC.SettingsCliError("watchdog")],
        )
        coordinator, _scheduler, _monitors, executor, completions = coordinator_for(
            client,
            on_busy=busy.append,
        )
        coordinator.queue_refresh()
        executor.run_next()
        completions.run_next()
        coordinator.state.change("operandi", "both")
        request = coordinator.state.build_request({"operandi": "both"}, {})

        self.assertTrue(coordinator.submit_save(request))
        executor.run_next()
        completions.run_next()

        self.assertEqual(busy, [True, False])
        self.assertFalse(coordinator._save_in_flight)
        self.assertTrue(coordinator.submit_save(request))

    def test_blocking_cli_runs_off_caller_thread_and_completion_is_dispatched(self) -> None:
        caller_thread = threading.get_ident()
        client = QueueClient(snapshots=[snapshot("r1", operandi="story")])
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="test-wirtel-settings")
        completions = CompletionQueue()
        observed = []
        coordinator = SettingsSyncCoordinator(
            client=client,
            scheduler=FakeScheduler(),
            monitor_factory=FakeMonitorFactory(),
            executor=executor,
            completion_dispatch=completions,
            on_snapshot=lambda *_args: observed.append(threading.get_ident()),
        )
        self.addCleanup(coordinator.dispose)
        self.assertTrue(coordinator.queue_refresh())
        self.assertTrue(client.called.wait(timeout=2))
        for _attempt in range(100):
            if completions.pending:
                break
            threading.Event().wait(0.01)
        self.assertTrue(completions.pending)
        self.assertNotEqual(client.call_threads[0], caller_thread)
        self.assertEqual(observed, [])
        completions.run_next()
        self.assertEqual(observed, [caller_thread])

    def test_safe_error_logs_only_the_exception_type(self) -> None:
        secret = "OPENAI_API_KEY=must-never-escape"
        with self.assertLogs(SYNC.__name__, level="WARNING") as captured:
            message = SettingsSyncCoordinator._safe_error(
                RuntimeError(secret),
                "Einstellungen konnten nicht aktualisiert werden",
            )
        rendered = "\n".join(captured.output)
        self.assertEqual(message, "Einstellungen konnten nicht aktualisiert werden")
        self.assertIn("RuntimeError", rendered)
        self.assertNotIn(secret, rendered)

    def test_conflict_save_keeps_dirty_value_and_reports_conflict(self) -> None:
        results = []
        conflict = SYNC.SettingsCliError(
            "conflict",
            payload={
                "ok": False,
                "error": "conflict",
                "conflicts": ["story_model"],
                "snapshot": snapshot("r2", story_model="gpt-5.5"),
            },
        )
        client = QueueClient(
            snapshots=[snapshot("r1", story_model="gpt-5-mini"), snapshot("r3", story_model="gpt-5.5")],
            applies=[conflict],
        )
        coordinator, _scheduler, _monitors, executor, completions = coordinator_for(
            client,
            on_save_result=lambda kind, _message, _payload: results.append(kind),
        )
        coordinator.queue_refresh()
        executor.run_next()
        completions.run_next()
        coordinator.state.change("story_model", "gpt-5.4-mini")
        request = coordinator.state.build_request({"story_model": "gpt-5.4-mini"}, {})
        coordinator.submit_save(request)
        executor.run_next()
        completions.run_next()
        self.assertEqual(coordinator.state.visible["story_model"], "gpt-5.4-mini")
        self.assertEqual(coordinator.state.conflicts, {"story_model"})
        self.assertEqual(results, ["conflict"])

    def test_malformed_conflict_snapshots_fail_closed_without_losing_the_draft(self) -> None:
        semantically_partial = snapshot("r2", story_model="gpt-5.5")
        semantically_partial["settings"].pop("operandi")
        malformed_snapshots = (
            {},
            {
                "revision": "r2",
                "settings": {"story_model": "gpt-5.5"},
            },
            semantically_partial,
        )
        for malformed_snapshot in malformed_snapshots:
            with self.subTest(snapshot=malformed_snapshot):
                errors = []
                results = []
                client = QueueClient(
                    snapshots=[
                        snapshot(
                            "r1",
                            operandi="story",
                            story_model="gpt-5-mini",
                        )
                    ],
                    applies=[
                        SYNC.SettingsCliError(
                            "conflict",
                            payload={
                                "ok": False,
                                "error": "conflict",
                                "conflicts": ["story_model"],
                                "snapshot": malformed_snapshot,
                            },
                        )
                    ],
                )
                coordinator, _scheduler, _monitors, executor, completions = coordinator_for(
                    client,
                    on_error=errors.append,
                    on_save_result=lambda kind, message, payload, _results=results: _results.append(
                        (kind, message, payload)
                    ),
                )
                coordinator.queue_refresh()
                executor.run_next()
                completions.run_next()
                coordinator.state.change("story_model", "gpt-5.4-mini")
                request = coordinator.state.build_request(
                    {"story_model": "gpt-5.4-mini"},
                    {},
                )
                coordinator.submit_save(request)
                executor.run_next()
                callback_errors = []
                try:
                    completions.run_next()
                except BaseException as exc:  # regression: callback must never escape
                    callback_errors.append(exc)

                self.assertEqual(callback_errors, [])
                self.assertEqual(
                    coordinator.state.visible["story_model"],
                    "gpt-5.4-mini",
                )
                self.assertEqual(coordinator.state.dirty, {"story_model"})
                self.assertEqual(
                    errors,
                    ["Einstellungen konnten nicht gespeichert werden"],
                )
                self.assertEqual(
                    results,
                    [("error", "Einstellungen konnten nicht gespeichert werden", {})],
                )

    def test_malicious_cli_error_text_never_reaches_ui_callbacks(self) -> None:
        leaked = "OPENAI_API_KEY=private-secret-like-text"
        errors = []
        results = []
        client = QueueClient(
            snapshots=[snapshot("r1", operandi="story"), snapshot("r3", operandi="story")],
            applies=[
                SYNC.SettingsCliError(
                    leaked,
                    payload={"ok": False, "error": leaked, "details": leaked},
                )
            ],
        )
        coordinator, _scheduler, _monitors, executor, completions = coordinator_for(
            client,
            on_error=lambda message: errors.append(message),
            on_save_result=lambda kind, message, payload: results.append(
                (kind, message, payload)
            ),
        )
        coordinator.queue_refresh()
        executor.run_next()
        completions.run_next()
        coordinator.state.change("operandi", "both")
        request = coordinator.state.build_request({"operandi": "both"}, {})
        coordinator.submit_save(request)
        executor.run_next()
        completions.run_next()

        rendered = repr((errors, results))
        self.assertNotIn(leaked, rendered)
        self.assertEqual(errors, ["Einstellungen konnten nicht gespeichert werden"])
        self.assertEqual(
            results,
            [("error", "Einstellungen konnten nicht gespeichert werden", {})],
        )


if __name__ == "__main__":
    unittest.main()
