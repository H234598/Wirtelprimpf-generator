"""Secret-free operational status assembled exclusively from bounded local sources."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .catalog import CatalogStore
from .naming import book_target_for_story
from .settings import SettingsPaths, SettingsSnapshot
from .state import StateStore
from .systemd_user import TimerObservation


@dataclass(frozen=True, slots=True)
class StatusPaths:
    platform_state: Path
    settings_state: Path
    hub_outbox: Path
    hub_source: Path
    media_manifest: Path
    publication_catalog: Path
    github_hosts: Path
    cloudflare_token: Path

    @classmethod
    def for_home(cls, home: Path) -> StatusPaths:
        settings_paths = SettingsPaths.for_home(home)
        generator = settings_paths.generator_root
        state = settings_paths.platform_state.parent
        return cls(
            platform_state=settings_paths.platform_state,
            settings_state=settings_paths.state_file,
            hub_outbox=state / "hub-dispatch.json",
            hub_source=generator / "data/hub-source.json",
            media_manifest=generator / "data/media-manifest.json",
            publication_catalog=generator / "data/publication-catalog.json",
            github_hosts=Path(home) / ".config/gh/hosts.yml",
            cloudflare_token=Path(home) / ".config/cloudflare/api-token.env",
        )

    @classmethod
    def for_root(cls, root: Path) -> StatusPaths:
        return cls.for_home(Path(root))


def _default_local_runner(command: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def _read_json_object(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise RuntimeError("local status source must not be a symlink")
    if not path.is_file():
        raise RuntimeError("local status source must be a regular file")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("local status JSON must be an object")
    return payload


def _mtime(path: Path) -> str | None:
    try:
        timestamp = path.stat().st_mtime
    except OSError:
        return None
    return datetime.fromtimestamp(timestamp, tz=UTC).isoformat().replace("+00:00", "Z")


class OperationalStatusCollector:
    def __init__(
        self,
        *,
        paths: StatusPaths,
        snapshot_reader: Callable[[], SettingsSnapshot],
        timer_reader: Callable[[], TimerObservation],
        service_reader: Callable[[], dict[str, object]] | None = None,
        local_runner: Callable[[list[str], float], object] = _default_local_runner,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.paths = paths
        self.snapshot_reader = snapshot_reader
        self.timer_reader = timer_reader
        self.local_runner = local_runner
        self.clock = clock
        self.service_reader = service_reader or self._read_generator_service

    def _read_generator_service(self) -> dict[str, object]:
        command = [
            "systemctl",
            "--user",
            "show",
            "wirtelprimpf.service",
            "--property",
            "ActiveState",
            "--property",
            "SubState",
            "--property",
            "Result",
            "--property",
            "ExecMainStatus",
            "--property",
            "InactiveExitTimestamp",
        ]
        result = self.local_runner(command, 2)
        if not isinstance(result, subprocess.CompletedProcess) or result.returncode != 0:
            raise RuntimeError("local service observation failed")
        raw: dict[str, str] = {}
        for line in result.stdout.splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                raw[key] = value
        status: dict[str, object] = {
            "active_state": raw.get("ActiveState") or "unknown",
            "sub_state": raw.get("SubState") or "unknown",
            "result": raw.get("Result") or "unknown",
            "last_run": raw.get("InactiveExitTimestamp") or None,
            "exec_main_status": None,
        }
        exec_status = raw.get("ExecMainStatus")
        if exec_status not in (None, ""):
            try:
                status["exec_main_status"] = int(exec_status)
            except ValueError as exc:
                raise RuntimeError("invalid local service status") from exc
        return status

    @staticmethod
    def _empty_status(observed_at: str) -> dict[str, object]:
        def unknown_publication() -> dict[str, object]:
            return {
                "state": "unknown",
                "value": None,
                "observed_at": None,
                "source": None,
            }

        return {
            "schema_version": "1.0.0",
            "observed_at": observed_at,
            "health": "ok",
            "configuration": {
                "revision": None,
                "valid": None,
                "drift": [],
                "state": "unknown",
                "observed_at": None,
            },
            "generator": {
                "active_state": "unknown",
                "sub_state": "unknown",
                "result": "unknown",
                "exec_main_status": None,
                "last_run": None,
            },
            "timer": {
                "enabled": None,
                "active": None,
                "interval_minutes": None,
                "randomized_delay_seconds": None,
                "persistent": None,
                "last_trigger": None,
                "next_run": None,
            },
            "story": {
                "state": "unknown",
                "completed_volumes": None,
                "current_volume": None,
                "book": None,
                "story_in_book": None,
                "stories_per_book": 10,
            },
            "archive": {"index": None, "repository": None},
            "rotation": {"blocked": None, "target": None, "phase": None},
            "publication": {
                "git": unknown_publication(),
                "release": unknown_publication(),
                "hub": unknown_publication(),
                "pages": unknown_publication(),
                "dns": unknown_publication(),
            },
            "auth": {
                "openai_present": False,
                "github_present": False,
                "cloudflare_present": False,
            },
            "warnings": [],
            "errors": [],
        }

    @staticmethod
    def _source_error(status: dict[str, object], source: str) -> None:
        status["health"] = "degraded"
        errors = status["errors"]
        assert isinstance(errors, list)
        errors.append({"source": source, "message": "local source unavailable"})

    def _collect_source(
        self,
        status: dict[str, object],
        source: str,
        reader: Callable[[], object],
    ) -> object | None:
        try:
            return reader()
        except (
            OSError,
            RuntimeError,
            ValueError,
            json.JSONDecodeError,
            subprocess.SubprocessError,
        ):
            self._source_error(status, source)
            return None

    def _collect_configuration(self, status: dict[str, object]) -> SettingsSnapshot | None:
        snapshot = self._collect_source(status, "configuration", self.snapshot_reader)
        if not isinstance(snapshot, SettingsSnapshot):
            if snapshot is not None:
                self._source_error(status, "configuration")
            return None
        drift = list(snapshot.warnings)
        configuration = {
            "revision": snapshot.revision,
            "valid": not any(warning.startswith("invalid_persisted_setting:") for warning in drift),
            "drift": drift,
            "state": "drift" if drift else "valid",
            "observed_at": None,
        }
        if self.paths.settings_state.exists():
            signal = self._collect_source(
                status,
                "revision_signal",
                lambda: _read_json_object(self.paths.settings_state),
            )
            if isinstance(signal, dict):
                signal_revision = signal.get("revision")
                if signal_revision != snapshot.revision:
                    drift.append("revision_signal_mismatch")
                    configuration["state"] = "drift"
                configuration["observed_at"] = _mtime(self.paths.settings_state)
        status["configuration"] = configuration
        status["auth"] = {
            "openai_present": bool(snapshot.secrets.get("openai_api_key_present")),
            "github_present": bool(snapshot.secrets.get("github_auth_present")),
            "cloudflare_present": bool(snapshot.secrets.get("cloudflare_api_token_present")),
        }
        warnings = status["warnings"]
        assert isinstance(warnings, list)
        warnings.extend(drift)
        return snapshot

    def _collect_service(self, status: dict[str, object]) -> None:
        service = self._collect_source(status, "generator_service", self.service_reader)
        if not isinstance(service, dict):
            if service is not None:
                self._source_error(status, "generator_service")
            return
        generator = status["generator"]
        assert isinstance(generator, dict)
        for key in generator:
            if key in service:
                generator[key] = service[key]

    def _collect_timer(self, status: dict[str, object]) -> None:
        timer = self._collect_source(status, "timer", self.timer_reader)
        if not isinstance(timer, TimerObservation):
            if timer is not None:
                self._source_error(status, "timer")
            return
        status["timer"] = {
            "enabled": timer.enabled,
            "active": timer.active,
            "interval_minutes": timer.interval_minutes,
            "randomized_delay_seconds": timer.randomized_delay_seconds,
            "persistent": timer.persistent,
            "last_trigger": timer.last_trigger,
            "next_run": timer.next_run,
        }

    def _collect_story(self, status: dict[str, object]) -> None:
        if not self.paths.platform_state.exists():
            self._source_error(status, "platform_state")
            return

        def read_story_state() -> tuple[object, object]:
            state = StateStore(self.paths.platform_state).load()
            try:
                target = book_target_for_story(state.current_volume)
            except TypeError as exc:
                raise ValueError("platform story position is invalid") from exc
            return state, target

        story_source = self._collect_source(
            status,
            "platform_state",
            read_story_state,
        )
        if not isinstance(story_source, tuple) or len(story_source) != 2:
            if story_source is not None:
                self._source_error(status, "platform_state")
            return
        state, target = story_source
        status["story"] = {
            "state": "blocked" if state.generation_blocked else "active",
            "completed_volumes": state.completed_volumes,
            "current_volume": state.current_volume,
            "book": target.global_book,
            "story_in_book": target.story_in_book,
            "stories_per_book": 10,
        }
        status["archive"] = {
            "index": state.active_archive_index,
            "repository": state.active_repository,
        }
        status["rotation"] = {
            "blocked": state.generation_blocked,
            "target": state.rotation.target_repository if state.rotation else None,
            "phase": state.rotation.phase.value if state.rotation else None,
        }

    def _collect_git(self, status: dict[str, object], snapshot: SettingsSnapshot | None) -> None:
        if snapshot is None:
            return
        raw_repo = snapshot.settings.get("repo_path")
        if not isinstance(raw_repo, str) or not raw_repo:
            return
        repository = Path(raw_repo).expanduser()
        if not repository.exists():
            return

        def read_revision() -> str:
            if repository.is_symlink() or not repository.is_dir():
                raise RuntimeError("local repository is unsafe")
            result = self.local_runner(["git", "-C", str(repository), "rev-parse", "HEAD"], 2)
            if not isinstance(result, subprocess.CompletedProcess) or result.returncode != 0:
                raise RuntimeError("local git observation failed")
            revision = result.stdout.strip()
            if len(revision) != 40 or any(character not in "0123456789abcdef" for character in revision):
                raise ValueError("local git revision is invalid")
            return revision

        revision = self._collect_source(status, "publication_git", read_revision)
        if isinstance(revision, str):
            status["publication"]["git"] = {
                "state": "observed",
                "value": revision,
                "observed_at": _mtime(repository / ".git/HEAD"),
                "source": "local-git",
            }

    def _collect_release(self, status: dict[str, object]) -> None:
        if not self.paths.media_manifest.exists():
            return
        manifest = self._collect_source(
            status,
            "media_manifest",
            lambda: _read_json_object(self.paths.media_manifest),
        )
        if not isinstance(manifest, dict):
            return
        media = manifest.get("media")
        if not isinstance(media, list):
            self._source_error(status, "media_manifest")
            return
        tags = sorted(
            {
                item.get("release_tag")
                for item in media
                if isinstance(item, dict) and isinstance(item.get("release_tag"), str)
            }
        )
        if tags:
            status["publication"]["release"] = {
                "state": "observed",
                "value": tags[-1],
                "observed_at": _mtime(self.paths.media_manifest),
                "source": "media-manifest.json",
            }

    def _collect_hub(self, status: dict[str, object]) -> None:
        source_path: Path | None = None
        state = "unknown"
        if self.paths.hub_outbox.exists():
            source_path = self.paths.hub_outbox
            state = "pending"
        elif self.paths.hub_source.exists():
            source_path = self.paths.hub_source
            state = "observed"
        if source_path is None:
            return
        payload = self._collect_source(
            status,
            "hub",
            lambda: _read_json_object(source_path),
        )
        if not isinstance(payload, dict):
            return
        repository = payload.get("archive_repository", payload.get("repository"))
        revision = payload.get("archive_revision", payload.get("revision"))
        if not isinstance(repository, str):
            self._source_error(status, "hub")
            return
        value = repository if not isinstance(revision, str) else f"{repository}@{revision}"
        status["publication"]["hub"] = {
            "state": state,
            "value": value,
            "observed_at": _mtime(source_path),
            "source": source_path.name,
        }
        archive = status["archive"]
        assert isinstance(archive, dict)
        archive["repository"] = repository

    def _collect_catalog(self, status: dict[str, object]) -> None:
        if not self.paths.publication_catalog.exists():
            return
        catalog = self._collect_source(
            status,
            "publication_catalog",
            lambda: CatalogStore(self.paths.publication_catalog).load(),
        )
        if catalog is None:
            return
        entry = catalog.entry(catalog.active_archive_index)
        if entry is None or not entry.verified:
            return
        observed_at = _mtime(self.paths.publication_catalog)
        status["publication"]["pages"] = {
            "state": "verified",
            "value": entry.pages_url,
            "observed_at": observed_at,
            "source": "publication-catalog.json",
        }
        status["publication"]["dns"] = {
            "state": "verified",
            "value": urlsplit(entry.pages_url).hostname,
            "observed_at": observed_at,
            "source": "publication-catalog.json",
        }

    def collect(self) -> dict[str, object]:
        observed_at = self.clock().astimezone(UTC).isoformat().replace("+00:00", "Z")
        status = self._empty_status(observed_at)
        snapshot = self._collect_configuration(status)
        self._collect_service(status)
        self._collect_timer(status)
        self._collect_story(status)
        self._collect_git(status, snapshot)
        self._collect_release(status)
        self._collect_hub(status)
        self._collect_catalog(status)
        return status
