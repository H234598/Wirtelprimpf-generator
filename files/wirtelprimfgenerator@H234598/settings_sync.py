"""Pure transactional-settings bridge for the Cinnamon settings UI.

This module deliberately imports neither GTK nor Gio.  Blocking CLI work is
submitted to an injected single-worker executor; an injected completion
dispatcher is the only route back to the UI thread.
"""

from __future__ import annotations

import copy
import fcntl
import json
import logging
import os
import stat
import subprocess
import time
from collections.abc import Callable, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

MAX_RESPONSE_BYTES = 1024 * 1024
SNAPSHOT_TIMEOUT_SECONDS = 10
_LOGGER = logging.getLogger(__name__)

# Cinnamon cannot import the platform package reliably.  This presentation
# contract intentionally mirrors settings_schema.SETTING_SPECS entries with
# applet_visible=True; a parity regression test prevents silent drift.
APPLET_SETTING_KINDS = {
    "operandi": "string",
    "image_model": "string",
    "story_model": "string",
    "image_size": "string",
    "output_resolution": "string",
    "generation_interval_minutes": "integer",
    "publish_immediately": "boolean",
    "story_finish_parts_min": "integer",
    "story_finish_parts_max": "integer",
    "local_outdir": "string",
    "working_dir": "string",
    "repo_path": "string",
    "repo_slug": "string",
    "repo_subdir": "string",
    "repo_branch": "string",
    "github_owner": "string",
    "media_mode": "string",
    "media_staging": "string",
    "platform_state": "string",
    "hub_dispatch_state": "string",
    "generator_root": "string",
    "archive_root": "string",
    "platform_catalog": "string",
    "settings_path": "string",
    "cloudflare_zone": "string",
    "cloudflare_zone_id": "string",
    "git_author_name": "string",
    "git_author_email": "string",
    "flex_processing": "string",
    "prompt_config": "string",
    "story_prompt_config": "string",
    "story_document": "string",
    "story_state": "string",
    "story_finish": "boolean",
    "timer_enabled": "boolean",
    "timer_randomized_delay_seconds": "integer",
    "timer_persistent": "boolean",
}
_APPLET_CHOICE_KEYS = frozenset(
    {
        "operandi",
        "image_model",
        "story_model",
        "image_size",
        "output_resolution",
        "media_mode",
        "flex_processing",
    }
)


class SettingsCliError(RuntimeError):
    def __init__(self, message: str, *, payload: object = None) -> None:
        super().__init__(message)
        self.payload = copy.deepcopy(payload) if isinstance(payload, dict) else {}


class SettingsOperationLockError(RuntimeError):
    """Redacted failure while acquiring the shared settings operation lock."""


def _open_settings_operation_lock(path: str) -> int:
    expanded = os.path.expanduser(path)
    if not os.path.isabs(expanded):
        raise SettingsOperationLockError(
            "Einstellungen konnten nicht sicher gesperrt werden"
        )
    candidate = Path(os.path.abspath(expanded))
    parent = candidate.parent
    try:
        for directory in (parent, *parent.parents):
            if directory.is_symlink():
                raise SettingsOperationLockError(
                    "Einstellungen konnten nicht sicher gesperrt werden"
                )
            if directory.exists() and not directory.is_dir():
                raise SettingsOperationLockError(
                    "Einstellungen konnten nicht sicher gesperrt werden"
                )
        parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        os.chmod(parent, 0o700)
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(candidate, flags, 0o600)
    except SettingsOperationLockError:
        raise
    except (OSError, ValueError) as exc:
        raise SettingsOperationLockError(
            "Einstellungen konnten nicht sicher gesperrt werden"
        ) from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise SettingsOperationLockError(
                "Einstellungen konnten nicht sicher gesperrt werden"
            )
        os.fchmod(descriptor, 0o600)
    except SettingsOperationLockError:
        os.close(descriptor)
        raise
    except OSError as exc:
        os.close(descriptor)
        raise SettingsOperationLockError(
            "Einstellungen konnten nicht sicher gesperrt werden"
        ) from exc
    return descriptor


@contextmanager
def exclusive_settings_lock(path: str, *, timeout_seconds: float = 0.1):
    """Serialize applet operations with settings writes without leaking paths."""

    descriptor = _open_settings_operation_lock(path)
    acquired = False
    deadline = time.monotonic() + max(0.0, float(timeout_seconds))
    try:
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise SettingsOperationLockError(
                        "Einstellungen sind vorübergehend gesperrt"
                    ) from None
                time.sleep(min(0.02, max(0.0, deadline - time.monotonic())))
            except OSError as exc:
                raise SettingsOperationLockError(
                    "Einstellungen konnten nicht sicher gesperrt werden"
                ) from exc
        yield
    finally:
        try:
            if acquired:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def trusted_executable(path: str) -> bool:
    """Return true only for an absolute, non-symlink regular executable path."""

    candidate = os.path.abspath(os.path.expanduser(path))
    try:
        if os.path.realpath(candidate) != candidate:
            return False
        metadata = os.lstat(candidate)
    except (OSError, ValueError):
        return False
    return stat.S_ISREG(metadata.st_mode) and os.access(candidate, os.X_OK)


class SettingsCliClient:
    def __init__(
        self,
        executable: str,
        *,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
        executable_check: Callable[[str], bool] = trusted_executable,
    ) -> None:
        expanded = os.path.expanduser(executable)
        if not os.path.isabs(expanded):
            raise SettingsCliError("Der Einstellungen-CLI-Pfad muss absolut sein")
        self.executable = os.path.normpath(expanded)
        self.runner = runner
        self.executable_check = executable_check
        if not self.executable_check(self.executable):
            raise SettingsCliError(
                "Keine vertrauenswürdige reguläre ausführbare Einstellungen-CLI"
            )

    def _run(self, action: str, request: Mapping[str, object] | None = None) -> dict[str, object]:
        if action not in {"snapshot", "apply"}:
            raise SettingsCliError("Unbekannte Einstellungen-CLI-Aktion")
        if not self.executable_check(self.executable):
            raise SettingsCliError(
                "Die vertrauenswürdige Einstellungen-CLI ist nicht mehr verfügbar"
            )
        input_text = None
        if request is not None:
            if not isinstance(request, Mapping):
                raise SettingsCliError("Einstellungsanfrage ist kein JSON-Objekt")
            input_text = json.dumps(
                request,
                ensure_ascii=False,
                separators=(",", ":"),
            )
        # Apply owns a multi-step write/validate/rollback transaction.  The
        # asynchronous UI client must never kill that owner between write and
        # rollback; every external child spawned by the CLI is bounded there.
        timeout = SNAPSHOT_TIMEOUT_SECONDS if action == "snapshot" else None
        command = [self.executable, action]
        try:
            result = self.runner(
                command,
                input=input_text,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=False,
                shell=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise SettingsCliError("Einstellungen-CLI konnte nicht sicher ausgeführt werden") from exc
        stdout = result.stdout
        if not isinstance(stdout, str):
            raise SettingsCliError("Einstellungsantwort ist kein gültiges JSON")
        if len(stdout.encode("utf-8")) > MAX_RESPONSE_BYTES:
            raise SettingsCliError("Einstellungsantwort ist zu groß")
        try:
            payload = json.loads(stdout)
        except (TypeError, ValueError) as exc:
            raise SettingsCliError("Einstellungsantwort ist kein gültiges JSON") from exc
        if not isinstance(payload, dict):
            raise SettingsCliError("Einstellungsantwort ist kein JSON-Objekt")
        if result.returncode != 0 or payload.get("ok") is not True:
            message = {
                3: "Konflikt bei Einstellungen",
                4: "Einstellungsanfrage ist ungültig",
                5: "Einstellungen sind vorübergehend gesperrt",
                6: "Einstellungstransaktion ist fehlgeschlagen",
                7: "Einstellungsdienst ist nicht verfügbar",
            }.get(result.returncode, "Einstellungsantwort wurde abgelehnt")
            raise SettingsCliError(message, payload=payload)
        if not _is_complete_public_snapshot(payload):
            raise SettingsCliError("Einstellungssnapshot ist nicht vollständig")
        return payload

    def snapshot(self) -> dict[str, object]:
        return self._run("snapshot")

    def apply(self, request: Mapping[str, object]) -> dict[str, object]:
        return self._run("apply", request)


def _snapshot_parts(payload: object) -> tuple[str, dict[str, object]]:
    if not isinstance(payload, Mapping):
        raise SettingsCliError("Einstellungssnapshot ist kein JSON-Objekt")
    revision = payload.get("revision")
    settings = payload.get("settings")
    if not isinstance(revision, str) or not revision:
        raise SettingsCliError("Einstellungssnapshot enthält keine Revision")
    if not isinstance(settings, Mapping):
        raise SettingsCliError("Einstellungssnapshot enthält keine Einstellungen")
    return revision, copy.deepcopy(dict(settings))


def _is_complete_public_snapshot(
    payload: object,
    *,
    required_setting_names: Sequence[str] = (),
) -> bool:
    if not isinstance(payload, Mapping):
        return False
    try:
        _snapshot_parts(payload)
    except SettingsCliError:
        return False
    schema_version = payload.get("schema_version")
    settings = payload.get("settings")
    choices = payload.get("choices")
    secrets = payload.get("secrets")
    invariants = payload.get("invariants")
    warnings = payload.get("warnings")
    if not isinstance(settings, Mapping):
        return False
    required_names = set(APPLET_SETTING_KINDS)
    required_names.update(required_setting_names)
    if not required_names.issubset(settings):
        return False
    for name, kind in APPLET_SETTING_KINDS.items():
        value = settings[name]
        if kind == "boolean" and not isinstance(value, bool):
            return False
        if kind == "integer" and (isinstance(value, bool) or not isinstance(value, int)):
            return False
        if kind == "string" and not isinstance(value, str):
            return False
    return (
        isinstance(schema_version, str)
        and bool(schema_version)
        and isinstance(choices, Mapping)
        and _APPLET_CHOICE_KEYS.issubset(choices)
        and all(
            isinstance(values, Sequence)
            and not isinstance(values, (str, bytes))
            and len(values) > 0
            and all(isinstance(value, str) for value in values)
            for values in choices.values()
        )
        and isinstance(secrets, Mapping)
        and isinstance(secrets.get("openai_api_key_present"), bool)
        and isinstance(secrets.get("cloudflare_api_token_present"), bool)
        and isinstance(invariants, Mapping)
        and isinstance(warnings, list)
        and all(isinstance(warning, str) for warning in warnings)
    )


def catalog_options(
    choices: Sequence[object],
    current: object,
) -> list[tuple[str, str, bool]]:
    normalized = [str(choice) for choice in choices]
    current_text = "" if current is None else str(current)
    options: list[tuple[str, str, bool]] = []
    if current_text and current_text not in normalized:
        options.append(
            (
                current_text,
                f"{current_text} · konfiguriert · nicht mehr im empfohlenen Katalog",
                True,
            )
        )
    options.extend((choice, choice, False) for choice in normalized)
    return options


class DirtySnapshotState:
    """Public settings state with sparse bases and local-draft protection."""

    def __init__(self, payload: Mapping[str, object]) -> None:
        revision, settings = _snapshot_parts(payload)
        self.revision = revision
        self.server = settings
        self.visible = copy.deepcopy(settings)
        self.base_revision: str | None = None
        self.base_values: dict[str, object] = {}
        self.dirty: set[str] = set()
        self.secret_dirty: set[str] = set()
        self.conflicts: set[str] = set()

    def change(self, name: str, value: object) -> None:
        server_value = self.server.get(name)
        if type(value) is type(server_value) and value == server_value:
            self.visible[name] = copy.deepcopy(server_value)
            self.dirty.discard(name)
            self.conflicts.discard(name)
            self.base_values.pop(name, None)
            self._clear_base_if_clean()
            return
        if name not in self.dirty:
            self.base_revision = self.base_revision or self.revision
            self.base_values[name] = copy.deepcopy(server_value)
            self.dirty.add(name)
        self.visible[name] = copy.deepcopy(value)

    def mark_secret_dirty(self, name: str) -> None:
        self.base_revision = self.base_revision or self.revision
        self.secret_dirty.add(name)

    def merge_snapshot(self, payload: Mapping[str, object]) -> dict[str, object]:
        revision, settings = _snapshot_parts(payload)
        for name, value in settings.items():
            if name in self.dirty:
                if value == self.base_values.get(name):
                    self.conflicts.discard(name)
                else:
                    self.conflicts.add(name)
                continue
            self.visible[name] = copy.deepcopy(value)
        self.server = settings
        self.revision = revision
        return copy.deepcopy(self.visible)

    def discard(self, name: str) -> object:
        if name not in self.dirty:
            return copy.deepcopy(self.visible.get(name))
        value = copy.deepcopy(self.server.get(name))
        self.visible[name] = value
        self.dirty.discard(name)
        self.conflicts.discard(name)
        self.base_values.pop(name, None)
        self._clear_base_if_clean()
        return copy.deepcopy(value)

    def discard_secret(self, name: str) -> None:
        self.secret_dirty.discard(name)
        self.conflicts.discard(name)
        self._clear_base_if_clean()

    def build_request(
        self,
        values: Mapping[str, object],
        secret_actions: Mapping[str, object],
    ) -> dict[str, object]:
        if set(secret_actions) != self.secret_dirty:
            raise SettingsCliError(
                "Secret-Aktionen müssen den ausdrücklich geänderten Secret-Feldern entsprechen"
            )
        missing = self.dirty - set(values)
        if missing:
            raise SettingsCliError("Lokale Einstellungswerte sind unvollständig")
        return {
            "base_revision": self.base_revision or self.revision,
            "changes": {
                name: copy.deepcopy(values[name])
                for name in sorted(self.dirty)
            },
            "base_values": {
                name: copy.deepcopy(self.base_values[name])
                for name in sorted(self.dirty)
            },
            "secret_actions": copy.deepcopy(dict(secret_actions)),
        }

    def accept_saved_snapshot(self, payload: Mapping[str, object]) -> None:
        revision, settings = _snapshot_parts(payload)
        self.revision = revision
        self.server = settings
        self.visible = copy.deepcopy(settings)
        self.base_revision = None
        self.base_values.clear()
        self.dirty.clear()
        self.secret_dirty.clear()
        self.conflicts.clear()

    def _clear_base_if_clean(self) -> None:
        if not self.dirty and not self.secret_dirty:
            self.base_revision = None


def _noop(*_args: object) -> None:
    return None


class SettingsSyncCoordinator:
    """Serialize settings I/O and coordinate monitor-driven live refreshes."""

    def __init__(
        self,
        *,
        client: SettingsCliClient,
        scheduler: Any,
        monitor_factory: Callable[[str, Callable[[str], None]], Any],
        executor: Any,
        completion_dispatch: Callable[..., object],
        on_snapshot: Callable[[Mapping[str, object], Mapping[str, object], DirtySnapshotState], None] = _noop,
        on_error: Callable[[str], None] = _noop,
        on_busy: Callable[[bool], None] = _noop,
        on_save_result: Callable[[str, str, Mapping[str, object]], None] = _noop,
        debounce_milliseconds: int = 250,
        fallback_seconds: int = 30,
    ) -> None:
        self.client = client
        self.scheduler = scheduler
        self.monitor_factory = monitor_factory
        self.executor = executor
        self.completion_dispatch = completion_dispatch
        self.on_snapshot = on_snapshot
        self.on_error = on_error
        self.on_busy = on_busy
        self.on_save_result = on_save_result
        self.debounce_milliseconds = debounce_milliseconds
        self.fallback_seconds = fallback_seconds
        self.state: DirtySnapshotState | None = None
        self._watched_paths: set[str] = set()
        self._failed_monitor_paths: set[str] = set()
        self._monitors: list[Any] = []
        self._debounce_handle: object | None = None
        self._fallback_handle: object | None = None
        self._refresh_in_flight = False
        self._refresh_pending = False
        self._save_in_flight = False
        self._operation_epoch = 0
        self._disposed = False

    @property
    def disposed(self) -> bool:
        return self._disposed

    @property
    def save_in_flight(self) -> bool:
        return self._save_in_flight

    def start(self, watched_paths: Sequence[str | os.PathLike[str]]) -> bool:
        if self._disposed:
            return False
        for item in watched_paths:
            target = os.path.normpath(os.path.abspath(os.fspath(item)))
            if target in self._watched_paths:
                continue
            self._watched_paths.add(target)
            self._install_monitor(target, report_error=True)
        if self._fallback_handle is None:
            self._fallback_handle = self.scheduler.call_repeated(
                self.fallback_seconds,
                self.fallback_refresh,
            )
        return self.queue_refresh()

    def _install_monitor(self, target: str, *, report_error: bool) -> bool:
        try:
            monitor = self.monitor_factory(target, self.notify_external_change)
        except BaseException:
            self._failed_monitor_paths.add(target)
            if report_error:
                self.on_error(
                    "Eine lokale Einstellungsdatei kann derzeit nicht überwacht werden"
                )
            return False
        self._monitors.append(monitor)
        self._failed_monitor_paths.discard(target)
        return True

    def _retry_failed_monitors(self) -> None:
        for target in tuple(sorted(self._failed_monitor_paths)):
            self._install_monitor(target, report_error=False)

    def notify_external_change(self, changed_path: str | os.PathLike[str]) -> None:
        if self._disposed:
            return
        changed = os.path.normpath(os.path.abspath(os.fspath(changed_path)))
        if changed not in self._watched_paths:
            return
        if self._debounce_handle is not None:
            self.scheduler.cancel(self._debounce_handle)
        self._debounce_handle = self.scheduler.call_later(
            self.debounce_milliseconds,
            self._run_debounced_refresh,
        )

    def _run_debounced_refresh(self) -> bool:
        self._debounce_handle = None
        self.queue_refresh()
        return False

    def focus_refresh(self) -> bool:
        self._retry_failed_monitors()
        self.queue_refresh()
        return False

    def fallback_refresh(self) -> bool:
        if self._disposed:
            return False
        self._retry_failed_monitors()
        self.queue_refresh()
        return True

    def queue_refresh(self) -> bool:
        if self._disposed:
            return False
        if self._refresh_in_flight or self._save_in_flight:
            self._refresh_pending = True
            return True
        self._refresh_in_flight = True
        captured_epoch = self._operation_epoch
        try:
            future = self.executor.submit(self.client.snapshot)
        except BaseException:
            self._refresh_in_flight = False
            self.on_error("Einstellungen konnten nicht aktualisiert werden")
            return False
        future.add_done_callback(
            lambda completed, epoch=captured_epoch: self.completion_dispatch(
                self._finish_refresh,
                epoch,
                completed,
            )
        )
        return True

    def _finish_refresh(self, captured_epoch: int, future: Any) -> bool:
        if self._disposed:
            return False
        self._refresh_in_flight = False
        stale = captured_epoch != self._operation_epoch
        try:
            payload = future.result()
            if not stale:
                self._accept_refresh_payload(payload)
        except BaseException as exc:
            if not stale:
                self.on_error(self._safe_error(exc, "Einstellungen konnten nicht aktualisiert werden"))
        pending = self._refresh_pending
        self._refresh_pending = False
        if pending and not self._save_in_flight:
            self.queue_refresh()
        return False

    def _accept_refresh_payload(self, payload: Mapping[str, object]) -> None:
        required_names = () if self.state is None else tuple(self.state.server)
        if not _is_complete_public_snapshot(
            payload,
            required_setting_names=required_names,
        ):
            raise SettingsCliError("Einstellungssnapshot ist nicht vollständig")
        if self.state is None:
            self.state = DirtySnapshotState(payload)
            visible = copy.deepcopy(self.state.visible)
        else:
            visible = self.state.merge_snapshot(payload)
        self.on_snapshot(payload, visible, self.state)

    def submit_save(self, request: Mapping[str, object]) -> bool:
        if self._disposed or self.state is None or self._save_in_flight:
            return False
        immutable_request = copy.deepcopy(dict(request))
        self._operation_epoch += 1
        captured_epoch = self._operation_epoch
        self._save_in_flight = True
        self.on_busy(True)
        try:
            future = self.executor.submit(self.client.apply, immutable_request)
        except BaseException as exc:
            self._save_in_flight = False
            self.on_busy(False)
            self.on_error(self._safe_error(exc, "Einstellungen konnten nicht gespeichert werden"))
            return False
        future.add_done_callback(
            lambda completed, epoch=captured_epoch: self.completion_dispatch(
                self._finish_save,
                epoch,
                completed,
            )
        )
        return True

    def _finish_save(self, captured_epoch: int, future: Any) -> bool:
        if self._disposed:
            return False
        try:
            payload = future.result()
            if captured_epoch == self._operation_epoch and self.state is not None:
                if not _is_complete_public_snapshot(
                    payload,
                    required_setting_names=tuple(self.state.server),
                ):
                    raise SettingsCliError("Einstellungssnapshot ist nicht vollständig")
                self.state.accept_saved_snapshot(payload)
                self.on_snapshot(payload, copy.deepcopy(self.state.visible), self.state)
                self.on_save_result("success", "Gespeichert.", payload)
        except SettingsCliError as exc:
            try:
                self._handle_save_cli_error(exc)
            except BaseException as handler_error:
                message = self._safe_error(
                    handler_error,
                    "Einstellungen konnten nicht gespeichert werden",
                )
                self.on_error(message)
                self.on_save_result("error", message, {})
        except BaseException as exc:
            message = self._safe_error(exc, "Einstellungen konnten nicht gespeichert werden")
            self.on_error(message)
            self.on_save_result("error", message, {})
        finally:
            self._save_in_flight = False
            self.on_busy(False)
            self._refresh_pending = False
            self.queue_refresh()
        return False

    def _handle_save_cli_error(self, error: SettingsCliError) -> None:
        payload = error.payload
        conflict_snapshot = payload.get("snapshot")
        conflicts = payload.get("conflicts")
        if (
            payload.get("error") == "conflict"
            and _is_complete_public_snapshot(
                conflict_snapshot,
                required_setting_names=tuple(self.state.server) if self.state is not None else (),
            )
            and isinstance(conflicts, list)
            and all(isinstance(name, str) for name in conflicts)
            and self.state is not None
        ):
            visible = self.state.merge_snapshot(conflict_snapshot)
            self.state.conflicts.update(conflicts)
            self.on_snapshot(conflict_snapshot, visible, self.state)
            self.on_save_result(
                "conflict",
                "Konflikt: extern geänderte Felder wurden nicht überschrieben.",
                {
                    "error": "conflict",
                    "conflicts": list(conflicts),
                    "snapshot": copy.deepcopy(dict(conflict_snapshot)),
                },
            )
            return
        message = self._safe_error(error, "Einstellungen konnten nicht gespeichert werden")
        self.on_error(message)
        self.on_save_result("error", message, {})

    @staticmethod
    def _safe_error(error: BaseException, fallback: str) -> str:
        _LOGGER.warning(
            "settings synchronization failure type=%s",
            type(error).__name__,
        )
        return fallback

    def dispose(self) -> None:
        if self._disposed:
            return
        self._disposed = True
        for handle in (self._debounce_handle, self._fallback_handle):
            if handle is not None:
                self.scheduler.cancel(handle)
        self._debounce_handle = None
        self._fallback_handle = None
        for monitor in self._monitors:
            try:
                monitor.cancel()
            except BaseException:
                continue
        self._monitors.clear()
        self._failed_monitor_paths.clear()
        self.executor.shutdown(wait=False, cancel_futures=True)


__all__ = [
    "DirtySnapshotState",
    "SettingsCliClient",
    "SettingsCliError",
    "SettingsOperationLockError",
    "SettingsSyncCoordinator",
    "catalog_options",
    "exclusive_settings_lock",
    "trusted_executable",
]
