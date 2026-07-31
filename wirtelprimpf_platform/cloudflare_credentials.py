"""Private Cloudflare credential resolution with Wrangler OAuth refresh fallback."""

from __future__ import annotations

import os
import stat
import subprocess
import tomllib
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

WRANGLER_VERSION = "4.118.0"


def _default_runner(command: list[str]) -> None:
    environment = dict(os.environ)
    # This host intentionally has a non-public /tmp; Wrangler/Node need a
    # writable temporary directory, and /var/tmp is already correctly 1777.
    environment.setdefault("TMPDIR", "/var/tmp")
    try:
        result = subprocess.run(
            command,
            env=environment,
            text=True,
            capture_output=True,
            timeout=180,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError("cannot execute private Wrangler OAuth refresh") from exc
    if result.returncode != 0:
        # Do not include stdout/stderr: authentication tools may print account
        # details, URLs or diagnostics that do not belong in generator logs.
        raise RuntimeError("private Wrangler OAuth refresh failed")


class CloudflareCredentialResolver:
    def __init__(
        self,
        *,
        config_path: Path | None = None,
        runner: Callable[[list[str]], None] = _default_runner,
    ) -> None:
        self.config_path = Path(config_path or Path.home() / ".config/.wrangler/config/default.toml")
        self.runner = runner

    @staticmethod
    def _validate_token(value: object, *, label: str) -> str:
        if not isinstance(value, str) or len(value) < 8 or any(character.isspace() for character in value):
            raise RuntimeError(f"{label} is missing or malformed")
        return value

    def _read(self) -> dict:
        path = self.config_path
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"private Wrangler configuration is unavailable: {path}")
        mode = stat.S_IMODE(path.stat().st_mode)
        if mode & 0o077:
            raise RuntimeError(f"private Wrangler configuration permissions are too broad: {mode:04o}")
        try:
            payload = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
            raise RuntimeError("cannot read private Wrangler configuration") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("private Wrangler configuration is malformed")
        return payload

    @staticmethod
    def _expiration(payload: dict) -> datetime:
        raw = payload.get("expiration_time")
        if not isinstance(raw, str):
            raise RuntimeError("Wrangler OAuth expiration time is missing")
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError as exc:
            raise RuntimeError("Wrangler OAuth expiration time is malformed") from exc
        if parsed.tzinfo is None:
            raise RuntimeError("Wrangler OAuth expiration time lacks a timezone")
        return parsed.astimezone(UTC)

    def resolve(
        self,
        *,
        explicit_token: str | None = None,
        now: datetime | None = None,
    ) -> str:
        if explicit_token:
            return self._validate_token(explicit_token, label="CLOUDFLARE_API_TOKEN")
        current_time = (now or datetime.now(UTC)).astimezone(UTC)
        payload = self._read()
        token = self._validate_token(payload.get("oauth_token"), label="Wrangler OAuth token")
        if self._expiration(payload) > current_time + timedelta(minutes=5):
            return token
        self._validate_token(payload.get("refresh_token"), label="Wrangler OAuth refresh token")
        self.runner(["npx", "--yes", f"wrangler@{WRANGLER_VERSION}", "whoami"])
        refreshed = self._read()
        if self._expiration(refreshed) <= current_time + timedelta(minutes=5):
            raise RuntimeError("Wrangler OAuth refresh did not produce a usable expiration time")
        return self._validate_token(refreshed.get("oauth_token"), label="refreshed Wrangler OAuth token")
