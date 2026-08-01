#!/usr/bin/env python3
"""Persist per-volume Wirtelprimpf directives and project the active one."""

from __future__ import annotations

import argparse
import errno
import fcntl
import json
import os
import re
import shlex
import stat
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

SCHEMA_VERSION: Final = 1
LEDGER_FILE_NAME: Final = "story_directives.json"
STORY_STATE_FILE_NAME: Final = "wirtelprimpf_story_state.json"
STORY_PROMPT_FILE_NAME: Final = "story_prompt_config.md"
MAX_DIRECTIVE_CHARS: Final = 20_000
MANAGED_SECTION_HEADING: Final = "Story-Vorgaben (verwaltet)"
LEGACY_MANAGED_SECTION_HEADINGS: Final = ("Zwingende Story-Vorgaben (verwaltet)",)
MANAGED_SECTION_MARKER: Final = f"## {MANAGED_SECTION_HEADING}"

STORY_III_DIRECTIVE: Final = """Actionstory.
Blutig: sichtbare Verletzungen, Blutspuren und harte Konsequenzen dürfen Teil der Handlung sein, sofern sie der Spannung und Geschichte dienen und nicht nur Selbstzweck sind.
Eine düstere, schnörkellose Thriller- und Horrorenergie mit eskalierender Bedrohung, moralischem Druck und kompromisslosen Konsequenzen; als abstrakte Mischung aus Motiven, für die Markus Heitz und Richard Bachman (Stephen King) bekannt sind, ohne deren individuelle Stimmen oder konkrete Formulierungen nachzuahmen.
James-Bond-Filmenergie: eine riskante Mission, elegante Täuschungen, überraschende Wendungen, ungewöhnliche Hilfsmittel, markante Schauplätze und ein gefährlicher Gegenspieler – alles organisch auf Morticia, Gomez, Maus und Möhre zugeschnitten.
Trotz Härte bleiben Morticia und Gomez erkennbare, nicht vermenschlichte Hauskatzen mit grünen Augen; Spannung, schwarzer Humor und emotionale Bindung tragen die Action."""

_MANAGED_SECTION_NAMES_RE: Final = "|".join(
    re.escape(name) for name in (MANAGED_SECTION_HEADING, *LEGACY_MANAGED_SECTION_HEADINGS)
)
_MANAGED_SECTION_RE: Final = re.compile(
    rf"(?ms)^##[ \t]+(?:{_MANAGED_SECTION_NAMES_RE})[ \t]*\n.*?(?=^##[ \t]+|\Z)"
)


class EditableWindowChanged(ValueError):
    """The editable story window moved between loading and saving."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _require_regular_non_symlink(path: Path, *, label: str, must_exist: bool = True) -> None:
    if path.is_symlink():
        raise ValueError(f"{label} must not be a symlink: {path}")
    if must_exist and not path.is_file():
        raise ValueError(f"{label} must be a regular file: {path}")
    if path.exists() and not path.is_file():
        raise ValueError(f"{label} must be a regular file: {path}")


def _open_regular_fd(
    path: Path,
    *,
    label: str,
    flags: int = os.O_RDONLY,
    mode: int = 0o600,
    missing_ok: bool = False,
) -> int | None:
    """Open a regular file without following a final-component symlink."""

    path = Path(path).expanduser()
    secure_flags = flags | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, secure_flags, mode)
    except FileNotFoundError:
        if missing_ok:
            return None
        raise ValueError(f"{label} must be a regular file: {path}") from None
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise ValueError(f"{label} must not be a symlink: {path}") from exc
        raise

    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError(f"{label} must be a regular file: {path}")
    except Exception:
        os.close(descriptor)
        raise
    return descriptor


def _read_regular_text(
    path: Path,
    *,
    label: str,
    missing_ok: bool = False,
    ensure_mode: int | None = None,
) -> str | None:
    """Read UTF-8 through the descriptor that was validated with ``fstat``."""

    descriptor = _open_regular_fd(path, label=label, missing_ok=missing_ok)
    if descriptor is None:
        return None
    try:
        if ensure_mode is not None:
            os.fchmod(descriptor, ensure_mode)
        with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
            descriptor = -1
            return handle.read()
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label} is not valid UTF-8: {Path(path).expanduser()}") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _ensure_safe_parent(path: Path) -> None:
    parent = Path(path).expanduser().parent
    ancestors = [parent]
    while ancestors[-1].parent != ancestors[-1]:
        ancestors.append(ancestors[-1].parent)

    for directory in reversed(ancestors):
        try:
            metadata = directory.lstat()
        except FileNotFoundError:
            try:
                directory.mkdir(mode=0o700)
            except FileExistsError as exc:
                raise ValueError(
                    f"Parent directory changed while it was being created: {directory}"
                ) from exc
            metadata = directory.lstat()
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
                raise ValueError(f"Parent directory must be a regular directory: {directory}")
            os.chmod(directory, 0o700, follow_symlinks=False)
            continue
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError(f"Parent directory must not be a symlink: {directory}")
        if not stat.S_ISDIR(metadata.st_mode):
            raise ValueError(f"Parent directory must be a regular directory: {directory}")


@contextmanager
def _exclusive_file_lock(path: Path, *, label: str):
    path = Path(path).expanduser()
    _ensure_safe_parent(path)
    lock_path = path.with_name(f".{path.name}.lock")
    descriptor = _open_regular_fd(
        lock_path,
        label=label,
        flags=os.O_RDWR | os.O_CREAT,
    )
    assert descriptor is not None
    locked = False
    try:
        os.fchmod(descriptor, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        locked = True
        yield
    finally:
        if locked:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


@contextmanager
def _exclusive_ledger_lock(path: Path):
    """Serialize complete ledger transactions via a stable sibling lock file."""

    with _exclusive_file_lock(path, label="story directive ledger lock"):
        yield


@contextmanager
def _exclusive_story_state_lock(path: Path):
    """Coordinate editable-window checks with generator state transitions."""

    with _exclusive_file_lock(path, label="story state lock"):
        yield


def atomic_write_text(path: Path, content: str, *, mode: int = 0o600) -> None:
    path = Path(path).expanduser()
    _require_regular_non_symlink(path, label="write target", must_exist=False)
    _ensure_safe_parent(path)
    temporary: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        temporary = Path(temporary_name)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
            os.fchmod(handle.fileno(), mode)
        os.replace(temporary, path)
    except Exception:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise


def atomic_write_json(path: Path, payload: dict[str, object]) -> None:
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def read_env_file(path: Path) -> dict[str, str]:
    path = Path(path).expanduser()
    raw_text = _read_regular_text(path, label="Environment file")
    assert raw_text is not None
    lines = raw_text.splitlines()

    values: dict[str, str] = {}
    for number, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[7:].lstrip()
        if "=" not in stripped:
            continue
        key, raw_value = stripped.split("=", 1)
        key = key.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise ValueError(f"Invalid environment key on line {number} in {path}: {key!r}")
        value = raw_value.strip()
        if not value:
            values[key] = ""
            continue
        try:
            parsed = shlex.split(value, posix=True)
        except ValueError as exc:
            raise ValueError(f"Invalid quoted value on line {number} in {path}") from exc
        values[key] = " ".join(parsed) if parsed else ""
    return values


def _expand_home_placeholder(value: str) -> str:
    home = str(Path.home())
    if value in {"$HOME", "${HOME}"}:
        return home
    if value.startswith("$HOME/"):
        return home + value[len("$HOME") :]
    if value.startswith("${HOME}/"):
        return home + value[len("${HOME}") :]
    return value


def _path_from(values: dict[str, str], key: str, default: Path) -> Path:
    raw = values.get(key, "").strip()
    return Path(_expand_home_placeholder(raw)).expanduser() if raw else default.expanduser()


def resolve_runtime_paths(env_path: Path) -> dict[str, Path]:
    values = read_env_file(env_path)
    home = Path.home()
    output = _path_from(values, "WIRTELPRIMPF_LOCAL_OUTDIR", home / "Hintergrundbilder")
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", str(home / ".config"))).expanduser()
    return {
        "env": Path(env_path).expanduser(),
        "local_outdir": output,
        "state": _path_from(
            values, "WIRTELPRIMPF_STORY_STATE", output / STORY_STATE_FILE_NAME
        ),
        "ledger": _path_from(
            values,
            "WIRTELPRIMPF_STORY_DIRECTIVES",
            config_home / "wirtelprimpf" / LEDGER_FILE_NAME,
        ),
        "prompt": _path_from(
            values,
            "WIRTELPRIMPF_STORY_PROMPT_CONFIG",
            config_home / "wirtelprimpf" / STORY_PROMPT_FILE_NAME,
        ),
    }


def load_story_state(path: Path) -> dict[str, object]:
    path = Path(path).expanduser()
    raw_text = _read_regular_text(path, label="Story state", missing_ok=True)
    if raw_text is None:
        return {"current_volume": 1, "pending_new_volume": False}
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid story state JSON in {path}: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Story state must be a JSON object: {path}")
    current = payload.get("current_volume", 1)
    pending = payload.get("pending_new_volume", False)
    if not isinstance(current, int) or isinstance(current, bool) or current < 1:
        raise ValueError(f"Story state current_volume must be an integer >= 1: {path}")
    if not isinstance(pending, bool):
        raise ValueError(f"Story state pending_new_volume must be boolean: {path}")
    return payload


def effective_current_volume(story_state: dict[str, object]) -> int:
    current = story_state.get("current_volume", 1)
    pending = story_state.get("pending_new_volume", False)
    if not isinstance(current, int) or isinstance(current, bool) or current < 1:
        raise ValueError("current_volume must be an integer >= 1")
    if not isinstance(pending, bool):
        raise ValueError("pending_new_volume must be boolean")
    return current + 1 if pending else current


def _new_ledger(now: str) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": now,
        "updated_at": now,
        "migrations": {"story_iii_seeded": False},
        "stories": {},
    }


def _validate_story_entry(key: str, value: object) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"Story directive {key!r} must be an object")
    try:
        key_volume = int(key)
    except ValueError as exc:
        raise ValueError(f"Story directive key must be a positive integer string: {key!r}") from exc
    if key_volume < 1 or key != str(key_volume):
        raise ValueError(f"Story directive key must be a canonical positive integer string: {key!r}")
    volume = value.get("volume")
    directive = value.get("directive")
    if not isinstance(volume, int) or isinstance(volume, bool):
        raise ValueError(f"Story directive volume must be a positive integer: {key!r}")
    if volume != key_volume:
        raise ValueError(f"Story directive key and volume do not match: {key!r}")
    if not isinstance(directive, str):
        raise ValueError(f"Story directive {key!r} must contain a string directive")
    if len(directive) > MAX_DIRECTIVE_CHARS:
        raise ValueError(f"Story directive {key!r} exceeds {MAX_DIRECTIVE_CHARS} characters")
    for timestamp_key in ("created_at", "updated_at"):
        if not isinstance(value.get(timestamp_key), str) or not str(value[timestamp_key]).strip():
            raise ValueError(f"Story directive {key!r} requires {timestamp_key}")
    if not isinstance(value.get("source"), str) or not str(value["source"]).strip():
        raise ValueError(f"Story directive {key!r} requires source")


def validate_ledger(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise ValueError("Story directive ledger must be a JSON object")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported story directive schema_version: {payload.get('schema_version')!r}"
        )
    migrations = payload.get("migrations", {})
    if not isinstance(migrations, dict):
        raise ValueError("Story directive ledger migrations must be an object")
    if not isinstance(migrations.get("story_iii_seeded", False), bool):
        raise ValueError("Story directive migration story_iii_seeded must be boolean")
    stories = payload.get("stories")
    if not isinstance(stories, dict):
        raise ValueError("Story directive ledger stories must be an object")
    for key, value in stories.items():
        if not isinstance(key, str):
            raise ValueError("Story directive keys must be strings")
        _validate_story_entry(key, value)
    return payload


def _story_entry(
    volume: int,
    directive: str,
    *,
    now: str,
    source: str,
    created_at: str | None = None,
) -> dict[str, object]:
    cleaned = directive.strip()
    if volume < 1:
        raise ValueError("Story volume must be >= 1")
    if len(cleaned) > MAX_DIRECTIVE_CHARS:
        raise ValueError(f"Story directive exceeds {MAX_DIRECTIVE_CHARS} characters")
    return {
        "volume": volume,
        "directive": cleaned,
        "created_at": created_at or now,
        "updated_at": now,
        "source": source,
    }


def _load_ledger_unlocked(
    path: Path,
    *,
    seed_story_iii: bool = True,
    now: str | None = None,
) -> dict[str, object]:
    path = Path(path).expanduser()
    timestamp = now or utc_now()
    changed = False
    raw_text = _read_regular_text(
        path,
        label="Story directive ledger",
        missing_ok=True,
        ensure_mode=0o600,
    )
    if raw_text is not None:
        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid story directive JSON in {path}: {exc.msg}") from exc
        validate_ledger(payload)
    else:
        payload = _new_ledger(timestamp)
        changed = True

    stories = payload["stories"]
    migrations = payload.get("migrations")
    assert isinstance(stories, dict)
    if migrations is None:
        migrations = {}
        payload["migrations"] = migrations
        changed = True
    assert isinstance(migrations, dict)
    if seed_story_iii and not migrations.get("story_iii_seeded", False):
        if "3" not in stories:
            stories["3"] = _story_entry(
                3, STORY_III_DIRECTIVE, now=timestamp, source="seed:story-iii"
            )
        migrations["story_iii_seeded"] = True
        changed = True

    if changed:
        payload["updated_at"] = timestamp
        atomic_write_json(path, payload)
    return payload


def load_ledger(
    path: Path,
    *,
    seed_story_iii: bool = True,
    now: str | None = None,
) -> dict[str, object]:
    path = Path(path).expanduser()
    with _exclusive_ledger_lock(path):
        return _load_ledger_unlocked(path, seed_story_iii=seed_story_iii, now=now)


def save_directives(
    path: Path,
    directives: dict[int, str],
    *,
    now: str | None = None,
    source: str = "cinnamon-settings",
) -> dict[str, object]:
    path = Path(path).expanduser()
    timestamp = now or utc_now()
    with _exclusive_ledger_lock(path):
        ledger = _load_ledger_unlocked(path, seed_story_iii=True, now=timestamp)
        stories = ledger["stories"]
        assert isinstance(stories, dict)
        for volume, directive in directives.items():
            if not isinstance(volume, int) or isinstance(volume, bool) or volume < 1:
                raise ValueError(f"Story volume must be a positive integer: {volume!r}")
            if not isinstance(directive, str):
                raise ValueError(f"Directive for volume {volume} must be a string")
            key = str(volume)
            cleaned = directive.strip()
            if not cleaned:
                stories.pop(key, None)
                continue
            previous = stories.get(key)
            created_at = previous.get("created_at") if isinstance(previous, dict) else None
            stories[key] = _story_entry(
                volume,
                cleaned,
                now=timestamp,
                source=source,
                created_at=created_at if isinstance(created_at, str) else None,
            )
        ledger["updated_at"] = timestamp
        validate_ledger(ledger)
        atomic_write_json(path, ledger)
        return ledger


def save_editable_window(
    path: Path,
    *,
    state_path: Path,
    current_volume: int,
    directives: dict[int, str],
    now: str | None = None,
    source: str = "cinnamon-settings",
) -> dict[str, object]:
    if not isinstance(current_volume, int) or isinstance(current_volume, bool) or current_volume < 1:
        raise ValueError("current_volume must be an integer >= 1")
    state_path = Path(state_path).expanduser()
    with _exclusive_story_state_lock(state_path):
        effective_volume = effective_current_volume(load_story_state(state_path))
        expected = {effective_volume, effective_volume + 1, effective_volume + 2}
        actual = set(directives)
        if effective_volume != current_volume or actual != expected:
            raise EditableWindowChanged(
                "editable story window changed; reload before saving "
                f"(loaded current {current_volume}, effective current {effective_volume}, "
                f"expected {sorted(expected)}, got {sorted(actual)})"
            )
        return save_directives(path, directives, now=now, source=source)


def story_roles(
    current_volume: int,
    ledger: dict[str, object],
) -> dict[str, list[dict[str, object]]]:
    if not isinstance(current_volume, int) or isinstance(current_volume, bool) or current_volume < 1:
        raise ValueError("current_volume must be an integer >= 1")
    validate_ledger(ledger)
    stories = ledger["stories"]
    assert isinstance(stories, dict)

    def record(volume: int, *, role: str, editable: bool) -> dict[str, object]:
        raw = stories.get(str(volume), {})
        directive = raw.get("directive", "") if isinstance(raw, dict) else ""
        return {
            "volume": volume,
            "role": role,
            "editable": editable,
            "directive": directive,
            "created_at": raw.get("created_at", "") if isinstance(raw, dict) else "",
            "updated_at": raw.get("updated_at", "") if isinstance(raw, dict) else "",
            "source": raw.get("source", "") if isinstance(raw, dict) else "",
        }

    editable = [
        record(current_volume, role="current", editable=True),
        record(current_volume + 1, role="next", editable=True),
        record(current_volume + 2, role="upcoming", editable=True),
    ]
    past = [
        record(volume, role="past", editable=False)
        for volume in range(current_volume - 1, 0, -1)
    ]
    return {"editable": editable, "past": past}


def _directive_lines(directive: str) -> list[str]:
    lines: list[str] = []
    for raw_line in directive.splitlines():
        cleaned = re.sub(r"^\s*[-*+]\s+", "", raw_line.strip()).strip()
        if cleaned:
            lines.append(cleaned)
    return lines


def replace_managed_prompt_section(prompt_text: str, directive: str) -> str:
    if not isinstance(prompt_text, str):
        raise TypeError("prompt_text must be a string")
    if not isinstance(directive, str):
        raise TypeError("directive must be a string")
    without_managed = _MANAGED_SECTION_RE.sub("", prompt_text).rstrip()
    lines = _directive_lines(directive)
    if not lines:
        return without_managed + ("\n" if without_managed else "")
    # A regular category with exactly one item is selected for both the story
    # text and image configurations by the existing Markdown prompt parser.
    rendered = MANAGED_SECTION_MARKER + "\n- " + " ".join(lines)
    return (without_managed + "\n\n" if without_managed else "") + rendered + "\n"


def apply_active_directive(*, env_path: Path | None = None) -> dict[str, object]:
    resolved_env = Path(
        env_path or Path.home() / ".config" / "wirtelprimpf" / "openai.env"
    ).expanduser()
    paths = resolve_runtime_paths(resolved_env)
    current = effective_current_volume(load_story_state(paths["state"]))
    ledger_path = paths["ledger"]
    with _exclusive_ledger_lock(ledger_path):
        ledger = _load_ledger_unlocked(ledger_path, seed_story_iii=True)
        stories = ledger["stories"]
        assert isinstance(stories, dict)
        active = stories.get(str(current), {})
        directive = active.get("directive", "") if isinstance(active, dict) else ""
        if not isinstance(directive, str):
            raise ValueError(f"Directive for story {current} is invalid")

        prompt_path = paths["prompt"]
        original = _read_regular_text(
            prompt_path,
            label="Story prompt config",
            ensure_mode=0o600,
        )
        assert original is not None
        rendered = replace_managed_prompt_section(original, directive)
        changed = rendered != original
        if changed:
            atomic_write_text(prompt_path, rendered)
    return {
        "ok": True,
        "current_volume": current,
        "directive_applied": bool(directive.strip()),
        "changed": changed,
        "directive_path": str(paths["ledger"]),
        "prompt_path": str(prompt_path),
    }


def status(*, env_path: Path | None = None) -> dict[str, object]:
    resolved_env = Path(
        env_path or Path.home() / ".config" / "wirtelprimpf" / "openai.env"
    ).expanduser()
    paths = resolve_runtime_paths(resolved_env)
    current = effective_current_volume(load_story_state(paths["state"]))
    ledger = load_ledger(paths["ledger"], seed_story_iii=True)
    return {
        "ok": True,
        "current_volume": current,
        "paths": {key: str(value) for key, value in paths.items()},
        "roles": story_roles(current, ledger),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage per-story Wirtelprimpf directives.")
    parser.add_argument("command", choices=("apply", "status"))
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path.home() / ".config" / "wirtelprimpf" / "openai.env",
        help="Generator environment file (default: ~/.config/wirtelprimpf/openai.env)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = (
            apply_active_directive(env_path=args.env_file)
            if args.command == "apply"
            else status(env_path=args.env_file)
        )
    except Exception as exc:  # CLI boundary
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
