"""Lossless environment documents and symlink-safe atomic file primitives."""

from __future__ import annotations

import os
import re
import shlex
import stat
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

_ENV_NAME = re.compile(r"[A-Z][A-Z0-9_]*")


class SettingsIOError(RuntimeError):
    """A configuration file cannot be handled without weakening safety."""


@dataclass(frozen=True, slots=True)
class EnvironmentDocument:
    """Parsed environment text whose untouched lines survive rendering exactly."""

    _lines: tuple[str, ...]
    _values: dict[str, str]

    @classmethod
    def parse(cls, text: str) -> EnvironmentDocument:
        lines = tuple(text.splitlines(keepends=True))
        if text and not lines:
            lines = (text,)
        values: dict[str, str] = {}
        for line in lines:
            content = line.rstrip("\r\n")
            stripped = content.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" not in content:
                raise SettingsIOError("malformed environment line")
            key_text, raw = content.split("=", 1)
            key = key_text.strip()
            if not _ENV_NAME.fullmatch(key):
                raise SettingsIOError(f"invalid environment key: {key!r}")
            if key in values:
                raise SettingsIOError(f"duplicate environment key: {key}")
            try:
                words = shlex.split(raw.strip(), comments=False, posix=True)
            except ValueError as exc:
                raise SettingsIOError("invalid quoted environment value") from exc
            values[key] = " ".join(words)
        return cls(lines, values)

    @property
    def values(self) -> dict[str, str]:
        return dict(self._values)

    def render(self, updates: Mapping[str, str | None]) -> str:
        for key, value in updates.items():
            if not _ENV_NAME.fullmatch(key):
                raise SettingsIOError(f"invalid environment key: {key!r}")
            if value is not None and any(character in value for character in "\x00\r\n"):
                raise SettingsIOError(f"environment value for {key} must be single-line")

        rendered: list[str] = []
        consumed: set[str] = set()
        for line in self._lines:
            content = line.rstrip("\r\n")
            if not content.strip() or content.lstrip().startswith("#") or "=" not in content:
                rendered.append(line)
                continue
            key = content.split("=", 1)[0].strip()
            if key not in updates:
                rendered.append(line)
                continue
            consumed.add(key)
            value = updates[key]
            if value is not None:
                ending = line[len(content) :]
                rendered.append(f"{key}={shlex.quote(value)}{ending or os.linesep}")

        for key, value in updates.items():
            if key in consumed or value is None:
                continue
            if rendered and not rendered[-1].endswith(("\n", "\r")):
                rendered[-1] += os.linesep
            rendered.append(f"{key}={shlex.quote(value)}{os.linesep}")
        return "".join(rendered)


@dataclass(frozen=True, slots=True)
class FileBackup:
    existed: bool
    content: bytes
    mode: int | None


def _reject_existing_parent_chain(parent: Path) -> None:
    for candidate in (parent, *parent.parents):
        if candidate.is_symlink():
            raise SettingsIOError(f"parent path must not contain a symlink: {candidate}")
        if candidate.exists() and not candidate.is_dir():
            raise SettingsIOError(f"parent path must contain directories only: {candidate}")


def _prepare_parent(parent: Path, *, private: bool) -> None:
    _reject_existing_parent_chain(parent)
    mode = 0o700 if private else 0o755
    missing: list[Path] = []
    candidate = parent
    while not candidate.exists():
        missing.append(candidate)
        candidate = candidate.parent
    try:
        for candidate in reversed(missing):
            created = False
            try:
                candidate.mkdir(mode=mode)
                created = True
            except FileExistsError:
                pass
            if created and private:
                os.chmod(candidate, mode)
    except OSError as exc:
        raise SettingsIOError("cannot prepare configuration parent directory") from exc
    _reject_existing_parent_chain(parent)


def _reject_unsafe_target(path: Path) -> None:
    if path.is_symlink():
        raise SettingsIOError(f"configuration target must not be a symlink: {path}")
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return
    except OSError as exc:
        raise SettingsIOError("cannot inspect configuration target") from exc
    if not stat.S_ISREG(metadata.st_mode):
        raise SettingsIOError(f"configuration target must be a regular file: {path}")


def _fsync_directory(parent: Path) -> None:
    directory_fd = os.open(parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


class SecureFile:
    """One atomic file with explicit permissions and byte-exact rollback."""

    def __init__(self, path: Path, private: bool) -> None:
        self.path = Path(path)
        self.private = bool(private)

    def read_bytes(self) -> bytes:
        _reject_existing_parent_chain(self.path.parent)
        _reject_unsafe_target(self.path)
        try:
            return self.path.read_bytes() if self.path.exists() else b""
        except OSError as exc:
            raise SettingsIOError("cannot read configuration file") from exc

    def capture(self) -> FileBackup:
        _reject_existing_parent_chain(self.path.parent)
        _reject_unsafe_target(self.path)
        if not self.path.exists():
            return FileBackup(False, b"", None)
        try:
            metadata = self.path.stat()
            return FileBackup(True, self.path.read_bytes(), stat.S_IMODE(metadata.st_mode))
        except OSError as exc:
            raise SettingsIOError("cannot capture configuration file") from exc

    def replace_bytes(self, content: bytes) -> None:
        parent = self.path.parent
        _prepare_parent(parent, private=self.private)
        _reject_unsafe_target(self.path)
        mode = 0o600 if self.private else 0o644
        part = parent / f".{self.path.name}.{os.getpid()}.{uuid.uuid4().hex}.part"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(part, flags, mode)
            try:
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(content)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.chmod(part, mode)
                _reject_unsafe_target(self.path)
                os.replace(part, self.path)
                os.chmod(self.path, mode)
                _fsync_directory(parent)
            finally:
                part.unlink(missing_ok=True)
        except OSError as exc:
            raise SettingsIOError("cannot atomically replace configuration file") from exc

    def restore(self, backup: FileBackup) -> None:
        if backup.existed:
            self.replace_bytes(backup.content)
            if backup.mode is not None:
                try:
                    os.chmod(self.path, backup.mode)
                    _fsync_directory(self.path.parent)
                except OSError as exc:
                    raise SettingsIOError("cannot restore configuration mode") from exc
            return

        _reject_existing_parent_chain(self.path.parent)
        _reject_unsafe_target(self.path)
        if not self.path.exists():
            return
        try:
            self.path.unlink()
            _fsync_directory(self.path.parent)
        except OSError as exc:
            raise SettingsIOError("cannot remove newly created configuration file") from exc


class SingleSecretStore:
    """A write-only public interface for one environment-file secret."""

    def __init__(self, path: Path, env_name: str) -> None:
        if not _ENV_NAME.fullmatch(env_name):
            raise SettingsIOError("invalid secret environment name")
        self.file = SecureFile(Path(path), private=True)
        self.env_name = env_name

    @property
    def path(self) -> Path:
        return self.file.path

    def present(self) -> bool:
        backup = self.file.capture()
        if not backup.existed:
            return False
        try:
            text = backup.content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SettingsIOError("secret file is not UTF-8") from exc
        values = EnvironmentDocument.parse(text).values
        if set(values) != {self.env_name}:
            raise SettingsIOError("secret file contains unexpected keys")
        return bool(values[self.env_name])

    def replace(self, value: str) -> None:
        if (
            not isinstance(value, str)
            or not 8 <= len(value) <= 512
            or any(character in value for character in "\x00\r\n")
        ):
            raise SettingsIOError("secret replacement is invalid")
        self.file.replace_bytes(f"{self.env_name}={shlex.quote(value)}\n".encode())

    def delete(self) -> None:
        self.file.restore(FileBackup(False, b"", None))

    def capture(self) -> FileBackup:
        return self.file.capture()

    def restore(self, backup: FileBackup) -> None:
        self.file.restore(backup)
