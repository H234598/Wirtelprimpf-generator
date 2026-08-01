"""Revisioned transactional authority for Wirtelprimpf configuration."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import stat
import subprocess
import time
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .settings_io import EnvironmentDocument, FileBackup, SecureFile, SettingsIOError, SingleSecretStore
from .settings_schema import (
    SETTING_SPECS,
    SETTINGS_SCHEMA_VERSION,
    SettingsValidationError,
    choices_payload,
    invariants_payload,
    validate_changes,
)
from .systemd_user import SystemdUserManager, TimerConfiguration, TimerObservation

Validator = Callable[[Mapping[str, str]], None]
_REVISION_RE = re.compile(r"[0-9a-f]{64}")
_SECRET_NAMES = frozenset({"openai_api_key", "cloudflare_api_token"})
_TIMER_KEYS = frozenset(
    {
        "generation_interval_minutes",
        "timer_enabled",
        "timer_randomized_delay_seconds",
        "timer_persistent",
    }
)


class SettingsError(RuntimeError):
    pass


class SettingsValidationFailure(SettingsError):
    pass


class SettingsLockBusy(SettingsError):
    pass


class SettingsConflict(SettingsError):
    def __init__(self, fields: tuple[str, ...], snapshot: SettingsSnapshot) -> None:
        self.fields = tuple(sorted(fields))
        self.snapshot = snapshot
        super().__init__(f"settings conflict: {', '.join(self.fields)}")


class SettingsApplyFailure(SettingsError):
    def __init__(self, phase: str, *, rollback_succeeded: bool) -> None:
        self.phase = phase
        self.rollback_succeeded = rollback_succeeded
        super().__init__(phase)


@dataclass(frozen=True, slots=True)
class SettingsPaths:
    env_file: Path
    cloudflare_token_file: Path
    timer_dropin: Path
    lock_file: Path
    state_file: Path
    generator_root: Path
    platform_state: Path
    publication_catalog: Path
    hub_outbox: Path

    @classmethod
    def for_home(cls, home: Path) -> SettingsPaths:
        home = Path(home)
        return cls(
            env_file=home / ".config/wirtelprimpf/openai.env",
            cloudflare_token_file=home / ".config/cloudflare/api-token.env",
            timer_dropin=home / ".config/systemd/user/wirtelprimpf.timer.d/override.conf",
            lock_file=home / ".config/wirtelprimpf/settings.lock",
            state_file=home / ".config/wirtelprimpf/settings-state.json",
            generator_root=home / ".local/share/wirtelprimpf-generator",
            platform_state=home / ".local/state/wirtelprimpf/platform-state.json",
            publication_catalog=home / ".local/share/wirtelprimpf-generator/data/publication-catalog.json",
            hub_outbox=home / ".local/state/wirtelprimpf/hub-dispatch.json",
        )


@dataclass(frozen=True, slots=True)
class SecretAction:
    action: Literal["replace", "delete"]
    value: str | None = None


def _parse_secret_actions(actions: Mapping[object, object]) -> dict[str, SecretAction]:
    parsed: dict[str, SecretAction] = {}
    for raw_name, raw_action in actions.items():
        if not isinstance(raw_name, str) or raw_name not in _SECRET_NAMES:
            raise SettingsValidationFailure("secret_actions contains an unknown secret")
        if not isinstance(raw_action, dict) or "action" not in raw_action:
            raise SettingsValidationFailure("secret action has an invalid envelope")
        action = raw_action.get("action")
        if action == "replace":
            if set(raw_action) != {"action", "value"}:
                raise SettingsValidationFailure("secret replacement has an invalid envelope")
            value = raw_action.get("value")
            if (
                not isinstance(value, str)
                or not 8 <= len(value) <= 512
                or any(character in value for character in "\x00\r\n")
            ):
                raise SettingsValidationFailure("secret replacement is invalid")
            parsed[raw_name] = SecretAction("replace", value)
        elif action == "delete":
            if set(raw_action) not in ({"action"}, {"action", "value"}) or raw_action.get("value") not in (None,):
                raise SettingsValidationFailure("secret deletion has an invalid envelope")
            parsed[raw_name] = SecretAction("delete")
        else:
            raise SettingsValidationFailure("secret action must be replace or delete")
    return parsed


@dataclass(frozen=True, slots=True)
class ChangeRequest:
    base_revision: str
    changes: dict[str, object]
    base_values: dict[str, object]
    secret_actions: dict[str, SecretAction]

    @classmethod
    def from_payload(cls, payload: object) -> ChangeRequest:
        if not isinstance(payload, dict) or set(payload) != {
            "base_revision",
            "changes",
            "base_values",
            "secret_actions",
        }:
            raise SettingsValidationFailure("settings request has an invalid envelope")
        base_revision = payload["base_revision"]
        changes = payload["changes"]
        base_values = payload["base_values"]
        actions = payload["secret_actions"]
        if not isinstance(base_revision, str) or not _REVISION_RE.fullmatch(base_revision):
            raise SettingsValidationFailure("base_revision must be a 64-character opaque revision")
        if (
            not isinstance(changes, dict)
            or not all(isinstance(key, str) for key in changes)
            or not isinstance(base_values, dict)
            or set(base_values) != set(changes)
        ):
            raise SettingsValidationFailure("base_values must match sparse change fields exactly")
        if not isinstance(actions, dict) or set(actions) - _SECRET_NAMES:
            raise SettingsValidationFailure("secret_actions contains an unknown secret")
        return cls(
            base_revision,
            dict(changes),
            dict(base_values),
            _parse_secret_actions(actions),
        )


@dataclass(frozen=True, slots=True)
class SettingsSnapshot:
    schema_version: str
    revision: str
    settings: dict[str, object]
    choices: dict[str, list[object]]
    secrets: dict[str, bool]
    invariants: dict[str, object]
    warnings: tuple[str, ...]

    def to_public_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "revision": self.revision,
            "settings": dict(self.settings),
            "choices": {key: list(values) for key, values in self.choices.items()},
            "secrets": dict(self.secrets),
            "invariants": dict(self.invariants),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class _FileFingerprint:
    exists: bool
    inode: int | None
    size: int | None
    mtime_ns: int | None


@dataclass(frozen=True, slots=True)
class _Backups:
    environment: FileBackup
    cloudflare_token: FileBackup
    timer_dropin: FileBackup
    state_signal: FileBackup


def _parse_bool(raw: str) -> bool:
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError("invalid boolean")


def _fingerprint(path: Path) -> _FileFingerprint:
    if path.is_symlink():
        raise SettingsIOError(f"configuration target must not be a symlink: {path}")
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return _FileFingerprint(False, None, None, None)
    except OSError as exc:
        raise SettingsIOError("cannot fingerprint configuration file") from exc
    if not stat.S_ISREG(metadata.st_mode):
        raise SettingsIOError(f"configuration target must be a regular file: {path}")
    return _FileFingerprint(True, metadata.st_ino, metadata.st_size, metadata.st_mtime_ns)


def _safe_process_environment() -> dict[str, str]:
    fragments = ("TOKEN", "SECRET", "PASSWORD", "API_KEY", "PRIVATE_KEY")
    return {
        key: value
        for key, value in os.environ.items()
        if not any(fragment in key.upper() for fragment in fragments)
    }


def _close_quietly(descriptor: int) -> None:
    try:
        os.close(descriptor)
    except OSError:
        return


def validate_generator_environment(generator_root: Path, environment: Mapping[str, str]) -> None:
    executable = Path(generator_root) / ".venv/bin/wirtelprimpf-generator"
    try:
        result = subprocess.run(
            [str(executable), "--check-config", "--json"],
            cwd=generator_root,
            env=dict(environment),
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        payload = json.loads(result.stdout)
    except (OSError, subprocess.SubprocessError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("generator configuration validation failed") from exc
    if (
        result.returncode != 0
        or not isinstance(payload, dict)
        or payload.get("ok") is not True
        or payload.get("mode") != "check_config"
        or payload.get("exit_code") != 0
    ):
        raise RuntimeError("generator configuration validation failed")


class SettingsManager:
    def __init__(
        self,
        paths: SettingsPaths,
        *,
        systemd: SystemdUserManager,
        validator: Validator | None = None,
        lock_timeout_seconds: float = 2.0,
    ) -> None:
        self.paths = paths
        self.systemd = systemd
        self.validator = validator or (
            lambda environment: validate_generator_environment(self.paths.generator_root, environment)
        )
        self.lock_timeout_seconds = max(0.0, float(lock_timeout_seconds))
        self._environment_file = SecureFile(paths.env_file, private=True)
        self._cloudflare_store = SingleSecretStore(paths.cloudflare_token_file, "CLOUDFLARE_API_TOKEN")
        self._timer_file = SecureFile(paths.timer_dropin, private=False)
        self._state_file = SecureFile(paths.state_file, private=True)
        self._home = paths.env_file.parents[2]

    @contextmanager
    def _lock(self, *, exclusive: bool) -> Iterator[None]:
        parent = self.paths.lock_file.parent
        for candidate in (parent, *parent.parents):
            if candidate.is_symlink():
                raise SettingsError("settings lock parent must not contain a symlink")
            if candidate.exists() and not candidate.is_dir():
                raise SettingsError("settings lock parent must contain directories only")
        try:
            parent.mkdir(parents=True, mode=0o700, exist_ok=True)
            os.chmod(parent, 0o700)
            flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(self.paths.lock_file, flags, 0o600)
        except OSError as exc:
            raise SettingsError("cannot open settings lock") from exc
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                raise SettingsError("settings lock must be a regular file")
            os.fchmod(descriptor, 0o600)
        except OSError as exc:
            _close_quietly(descriptor)
            raise SettingsError("cannot open settings lock") from exc
        except BaseException:
            _close_quietly(descriptor)
            raise
        operation = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
        deadline = time.monotonic() + self.lock_timeout_seconds
        try:
            while True:
                try:
                    fcntl.flock(descriptor, operation | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise SettingsLockBusy("settings lock is busy") from None
                    time.sleep(min(0.02, max(0.0, deadline - time.monotonic())))
            yield
        finally:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)

    def snapshot(self) -> SettingsSnapshot:
        try:
            with self._lock(exclusive=False):
                return self._read_snapshot_unlocked()
        except SettingsIOError as exc:
            raise SettingsError("settings snapshot unavailable") from exc

    def _environment_document(self) -> EnvironmentDocument:
        content = self._environment_file.read_bytes()
        try:
            return EnvironmentDocument.parse(content.decode("utf-8"))
        except UnicodeDecodeError as exc:
            raise SettingsIOError("settings environment is not UTF-8") from exc

    def _normalized_settings(
        self,
        values: Mapping[str, str],
        timer: TimerObservation,
    ) -> tuple[dict[str, object], list[str]]:
        normalized: dict[str, object] = {}
        warnings: list[str] = []
        for key, spec in SETTING_SPECS.items():
            if spec.env_name is None:
                continue
            raw = values.get(spec.env_name)
            if raw is None:
                normalized[key] = spec.default
                continue
            try:
                if spec.kind == "boolean":
                    normalized[key] = _parse_bool(raw)
                elif spec.kind == "integer":
                    if not re.fullmatch(r"[+-]?[0-9]+", raw.strip()):
                        raise ValueError("invalid integer")
                    parsed = int(raw)
                    if spec.minimum is not None and parsed < spec.minimum:
                        raise ValueError("integer below minimum")
                    if spec.maximum is not None and parsed > spec.maximum:
                        raise ValueError("integer above maximum")
                    normalized[key] = parsed
                else:
                    parsed = raw.strip()
                    if not parsed and not spec.allow_empty:
                        raise ValueError("empty string")
                    if any(character in parsed for character in "\x00\r\n"):
                        raise ValueError("multiline string")
                    if spec.max_length is not None and len(parsed) > spec.max_length:
                        raise ValueError("string too long")
                    if parsed and spec.pattern is not None and spec.pattern.fullmatch(parsed) is None:
                        raise ValueError("invalid string format")
                    if spec.choices and key not in {"image_model", "story_model"} and parsed not in spec.choices:
                        raise ValueError("invalid choice")
                    normalized[key] = parsed
            except ValueError:
                normalized[key] = spec.default
                warnings.append(f"invalid_persisted_setting:{key}")
        if int(normalized["story_finish_parts_min"]) > int(normalized["story_finish_parts_max"]):
            for key in ("story_finish_parts_min", "story_finish_parts_max"):
                normalized[key] = SETTING_SPECS[key].default
                warnings.append(f"invalid_persisted_setting:{key}")
        normalized.update(
            {
                "timer_enabled": timer.enabled,
                "timer_randomized_delay_seconds": timer.randomized_delay_seconds,
                "timer_persistent": timer.persistent,
            }
        )
        if normalized["generation_interval_minutes"] != timer.interval_minutes:
            warnings.append("timer_interval_drift")
        return normalized, warnings

    def _read_snapshot_unlocked(self) -> SettingsSnapshot:
        document = self._environment_document()
        values = document.values
        timer = self.systemd.observe_timer()
        normalized, warnings = self._normalized_settings(values, timer)
        if "CLOUDFLARE_API_TOKEN" in values:
            warnings.append("legacy_cloudflare_token_in_wirtel_env")
        secret_presence = {
            "openai_api_key_present": bool(values.get("OPENAI_API_KEY")),
            "cloudflare_api_token_present": self._cloudflare_store.present(),
            "github_auth_present": bool(
                os.environ.get("GH_TOKEN")
                or os.environ.get("GITHUB_TOKEN")
                or (self._home / ".config/gh/hosts.yml").is_file()
            ),
        }
        paths = {
            "environment": self.paths.env_file,
            "cloudflare_token": self.paths.cloudflare_token_file,
            "timer_dropin": self.paths.timer_dropin,
        }
        fingerprints = {name: _fingerprint(path) for name, path in paths.items()}
        revision_source = {
            "settings": normalized,
            "secret_presence": secret_presence,
            "files": {
                name: {
                    "exists": fingerprint.exists,
                    "inode": fingerprint.inode,
                    "size": fingerprint.size,
                    "mtime_ns": fingerprint.mtime_ns,
                }
                for name, fingerprint in fingerprints.items()
            },
            "timer": {
                "enabled": timer.enabled,
                "interval_minutes": timer.interval_minutes,
                "randomized_delay_seconds": timer.randomized_delay_seconds,
                "persistent": timer.persistent,
            },
        }
        revision = hashlib.sha256(
            json.dumps(
                revision_source,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return SettingsSnapshot(
            schema_version=SETTINGS_SCHEMA_VERSION,
            revision=revision,
            settings=normalized,
            choices=choices_payload(),
            secrets=secret_presence,
            invariants=invariants_payload(),
            warnings=tuple(sorted(set(warnings))),
        )

    def _expand_from_home(self, raw: object) -> Path:
        if not isinstance(raw, str):
            raise SettingsValidationFailure("settings_path must be a path string")
        if raw == "~":
            return self._home
        if raw.startswith("~/"):
            return self._home / raw[2:]
        return Path(raw)

    def _capture_backups(self) -> _Backups:
        return _Backups(
            environment=self._environment_file.capture(),
            cloudflare_token=self._cloudflare_store.capture(),
            timer_dropin=self._timer_file.capture(),
            state_signal=self._state_file.capture(),
        )

    def _write_environment(
        self,
        validated: Mapping[str, object],
        secret_actions: Mapping[str, SecretAction],
    ) -> None:
        updates: dict[str, str | None] = {}
        for key, value in validated.items():
            env_name = SETTING_SPECS[key].env_name
            if env_name is None:
                continue
            if isinstance(value, bool):
                updates[env_name] = "1" if value else "0"
            else:
                updates[env_name] = str(value)
        openai = secret_actions.get("openai_api_key")
        if openai is not None:
            updates["OPENAI_API_KEY"] = openai.value if openai.action == "replace" else None
        if not updates:
            return
        rendered = self._environment_document().render(updates)
        self._environment_file.replace_bytes(rendered.encode("utf-8"))

    def _write_cloudflare_secret(self, secret_actions: Mapping[str, SecretAction]) -> None:
        action = secret_actions.get("cloudflare_api_token")
        if action is None:
            return
        if action.action == "replace":
            assert action.value is not None
            self._cloudflare_store.replace(action.value)
        else:
            self._cloudflare_store.delete()

    def _generator_environment(self) -> dict[str, str]:
        environment = _safe_process_environment()
        environment.update(self._environment_document().values)
        return environment

    @staticmethod
    def _timer_configuration(proposed: Mapping[str, object]) -> TimerConfiguration:
        return TimerConfiguration(
            enabled=bool(proposed["timer_enabled"]),
            interval_minutes=int(proposed["generation_interval_minutes"]),
            randomized_delay_seconds=int(proposed["timer_randomized_delay_seconds"]),
            persistent=bool(proposed["timer_persistent"]),
        )

    @staticmethod
    def _require_effective_timer(requested: TimerConfiguration, effective: TimerObservation) -> None:
        if effective.configuration() != requested or effective.active != requested.enabled:
            raise RuntimeError("effective timer verification failed")

    def _write_revision_signal(self, revision: str) -> None:
        payload = json.dumps(
            {"schema_version": SETTINGS_SCHEMA_VERSION, "revision": revision},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        self._state_file.replace_bytes(f"{payload}\n".encode())

    def _rollback(
        self,
        backups: _Backups,
        old_timer: TimerObservation,
        *,
        environment_touched: bool,
        cloudflare_touched: bool,
        state_signal_touched: bool,
        timer_touched: bool,
    ) -> bool:
        succeeded = True
        restore_targets = []
        if environment_touched:
            restore_targets.append((self._environment_file, backups.environment))
        if cloudflare_touched:
            restore_targets.append((self._cloudflare_store, backups.cloudflare_token))
        if state_signal_touched:
            restore_targets.append((self._state_file, backups.state_signal))
        for store, backup in restore_targets:
            try:
                store.restore(backup)
            except Exception:
                succeeded = False
        if timer_touched:
            try:
                self.systemd.restore_timer(
                    old_timer.configuration(),
                    old_timer.active,
                    backups.timer_dropin,
                )
            except Exception:
                succeeded = False
        return succeeded

    def apply(self, request: ChangeRequest) -> SettingsSnapshot:
        with self._lock(exclusive=True):
            try:
                before = self._read_snapshot_unlocked()
            except SettingsIOError as exc:
                raise SettingsError("settings transaction unavailable") from exc
            conflicts = tuple(
                sorted(
                    key
                    for key, base_value in request.base_values.items()
                    if type(before.settings.get(key)) is not type(base_value)
                    or before.settings.get(key) != base_value
                )
            )
            if request.secret_actions and request.base_revision != before.revision:
                raise SettingsConflict(tuple(sorted(request.secret_actions)), before)
            if conflicts:
                raise SettingsConflict(conflicts, before)
            try:
                validated = validate_changes(request.changes, before.settings)
            except SettingsValidationError as exc:
                raise SettingsValidationFailure(str(exc)) from None
            proposed = {**before.settings, **validated}
            if self._expand_from_home(proposed["settings_path"]) != self.paths.env_file:
                raise SettingsValidationFailure("settings_path must match the transactional manager path")
            if not validated and not request.secret_actions:
                return before
            backups = self._capture_backups()
            old_timer = self.systemd.observe_timer()
            environment_touched = any(SETTING_SPECS[key].env_name is not None for key in validated) or (
                "openai_api_key" in request.secret_actions
            )
            cloudflare_touched = "cloudflare_api_token" in request.secret_actions
            state_signal_touched = False
            timer_touched = False
            try:
                self._write_environment(validated, request.secret_actions)
                self._write_cloudflare_secret(request.secret_actions)
                self.validator(self._generator_environment())
                if _TIMER_KEYS.intersection(validated):
                    requested_timer = self._timer_configuration(proposed)
                    timer_touched = True
                    effective_timer = self.systemd.apply_timer(requested_timer)
                    self._require_effective_timer(requested_timer, effective_timer)
                result = self._read_snapshot_unlocked()
                state_signal_touched = True
                self._write_revision_signal(result.revision)
                return result
            except SettingsConflict:
                raise
            except Exception as exc:
                rollback_succeeded = self._rollback(
                    backups,
                    old_timer,
                    environment_touched=environment_touched,
                    cloudflare_touched=cloudflare_touched,
                    state_signal_touched=state_signal_touched,
                    timer_touched=timer_touched,
                )
                raise SettingsApplyFailure(
                    "settings transaction failed",
                    rollback_succeeded=rollback_succeeded,
                ) from exc
