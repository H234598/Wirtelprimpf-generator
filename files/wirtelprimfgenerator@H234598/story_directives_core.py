#!/usr/bin/env python3
"""Manage per-volume Wirtelprimpf story directives.

The module deliberately has no GTK or OpenAI dependency. It owns the versioned
JSON ledger, resolves the effective current story volume from the generator
state, and projects exactly one active directive into the existing Markdown
story prompt configuration.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

SCHEMA_VERSION: Final = 1
LEDGER_FILE_NAME: Final = "story_directives.json"
STORY_STATE_FILE_NAME: Final = "wirtelprimpf_story_state.json"
STORY_PROMPT_FILE_NAME: Final = "story_prompt_config.md"
MANAGED_SECTION_HEADING: Final = "Zwingende Story-Vorgaben (verwaltet)"
MANAGED_SECTION_MARKER: Final = f"## {MANAGED_SECTION_HEADING}"
MAX_DIRECTIVE_CHARS: Final = 20_000

STORY_III_DIRECTIVE: Final = """Actionstory.
Blutig: sichtbare Verletzungen, Blutspuren und harte Konsequenzen dürfen Teil der Handlung sein, sofern sie der Spannung und Geschichte dienen und nicht nur Selbstzweck sind.
Eine düstere, schnörkellose Thriller- und Horrorenergie mit eskalierender Bedrohung, moralischem Druck und kompromisslosen Konsequenzen; als abstrakte Mischung aus Motiven, für die Markus Heitz und Richard Bachman (Stephen King) bekannt sind, ohne deren individuelle Stimmen oder konkrete Formulierungen nachzuahmen.
James-Bond-Filmenergie: eine riskante Mission, elegante Täuschungen, überraschende Wendungen, ungewöhnliche Hilfsmittel, markante Schauplätze und ein gefährlicher Gegenspieler – alles organisch auf Morticia, Gomez, Maus und Möhre zugeschnitten.
Trotz Härte bleiben Morticia und Gomez erkennbare, nicht vermenschlichte Hauskatzen mit grünen Augen; Spannung, schwarzer Humor und emotionale Bindung tragen die Action."""

_MANAGED_SECTION_RE: Final = re.compile(
    rf"(?ms)^##[ \t]+{re.escape(MANAGED_SECTION_HEADING)}[ \t]*\n.*?(?=^##[ \t]+|\Z)"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _require_regular_non_symlink(path: Path, *, label: str, must_exist: bool = True) -> None:
    if path.is_symlink():
        raise ValueError(f"{label} must not be a symlink: {path}")
    if must_exist and not path.is_file():
        raise ValueError(f"{label} must be a regular file: {path}")
    if path.exists() and not path.is_file():
        raise ValueError(f"{label} must be a regular file: {path}")


def _ensure_safe_parent(path: Path) -> None:
    parent = path.parent
    if parent.exists() and parent.is_symlink():
        raise ValueError(f"Parent directory must not be a symlink: {parent}")
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not parent.is_dir() or parent.is_symlink():
        raise ValueError(f"Parent directory must be a regular directory: {parent}")


def atomic_write_text(path: Path, content: str, *, mode: int = 0o600) -> None:
    path = Path(path).expanduser()
    _require_regular_non_symlink(path, label="write target", must_exist=False)
    _ensure_safe_parent(path)
    temporary: Path | None = None
    try:
        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        temporary = Path(temporary_name)
        with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
        os.chmod(path, mode)
    except Exception:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise


def atomic_write_json(path: Path, payload: dict[str, object]) -> None:
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def read_env_file(path: Path) -> dict[str, str]:
    path = Path(path).expanduser()
    _require_regular_non_symlink(path, label="environment file")
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ValueError(f"Environment file is not valid UTF-8: {path}") from exc
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
    if value == "$HOME" or value == "${HOME}":
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
    env_values = read_env_file(env_path)
    home = Path.home()
    local_outdir = _path_from(
        env_values, "WIRTELPRIMPF_LOCAL_OUTDIR", home / "Hintergrundbilder"
    )
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", str(home / ".config"))).expanduser()
    return {
        "env": Path(env_path).expanduser(),
        "local_outdir": local_outdir,
        "state": _path_from(
            env_values,
            "WIRTELPRIMPF_STORY_STATE",
            local_outdir / STORY_STATE_FILE_NAME,
        ),
        "ledger": _path_from(
            env_values,
            "WIRTELPRIMPF_STORY_DIRECTIVES",
            config_home / "wirtelprimpf" / LEDGER_FILE_NAME,
        ),
        "prompt": _path_from(
            env_values,
            "WIRTELPRIMPF_STORY_PROMPT_CONFIG",
            config_home / "wirtelprimpf" / STORY_PROMPT_FILE_NAME,
        ),
    }


def load_story_state(path: Path) -> dict[str, object]:
    path = Path(path).expanduser()
    if not path.exists():
        return {"current_volume": 1, "pending_new_volume": False}
    _require_regular_non_symlink(path, label="story state")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid story state JSON in {path}: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Story state must be a JSON object: {path}")
    current_volume = payload.get("current_volume", 1)
    pending = payload.get("pending_new_volume", False)
    if not isinstance(current_volume, int) or isinstance(current_volume, bool) or current_volume < 1:
        raise ValueError(f"Story state current_volume must be an integer >= 1: {path}")
    if not isinstance(pending, bool):
        raise ValueError(f"Story state pending_new_volume must be boolean: {path}")
    return payload


def effective_current_volume(story_state: dict[str, object]) -> int:
    current_volume = story_state.get("current_volume", 1)
    pending = story_state.get("pending_new_volume", False)
    if not isinstance(current_volume, int) or isinstance(current_volume, bool) or current_volume < 1:
        raise ValueError("current_volume must be an integer >= 1")
    if not isinstance(pending, bool):
        raise ValueError("pending_new_volume must be boolean")
    return current_volume + 1 if pending else current_volume


def _new_ledger(now: str) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": now,
        "updated_at": now,
        "migrations": {"story_iii_seeded": False},
        "stories": {},
    }


def _validate_story_entry(key: str, value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"Story directive {key!r} must be an object")
    try:
        key_volume = int(key)
    except ValueError as exc:
        raise ValueError(f"Story directive key must be a positive integer string: {key!r}") from exc
    volume = value.get("volume")
    directive = value.get("directive")
    if key_volume < 1 or volume != key_volume:
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
    return value


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
    story_iii_seeded = migrations.get("story_iii_seeded", False)
    if not isinstance(story_iii_seeded, bool):
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


def load_ledger(
    path: Path,
    *,
    seed_story_iii: bool = True,
    now: str | None = None,
) -> dict[str, object]:
    path = Path(path).expanduser()
    timestamp = now or utc_now()
    changed = False
    if path.exists():
        _require_regular_non_symlink(path, label="story directive ledger")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid story directive JSON in {path}: {exc.msg}") from exc
        validate_ledger(payload)
    else:
        payload = _new_ledger(timestamp)
        changed = True

    stories = payload["stories"]
    assert isinstance(stories, dict)
    migrations = payload.get("migrations")
    if migrations is None:
        migrations = {}
        payload["migrations"] = migrations
        changed = True
    assert isinstance(migrations, dict)
    story_iii_seeded = migrations.get("story_iii_seeded", False)
    if seed_story_iii and not story_iii_seeded:
        if "3" not in stories:
            stories["3"] = _story_entry(
                3,
                STORY_III_DIRECTIVE,
                now=timestamp,
                source="seed:story-iii",
            )
        migrations["story_iii_seeded"] = True
        changed = True
    if changed:
        payload["updated_at"] = timestamp
        atomic_write_json(path, payload)
    elif path.exists():
        os.chmod(path, 0o600)
    return payload


def save_directives(
    path: Path,
    directives: dict[int, str],
    *,
    now: str | None = None,
    source: str = "cinnamon-settings",
) -> dict[str, object]:
    timestamp = now or utc_now()
    ledger = load_ledger(path, seed_story_iii=True, now=timestamp)
    stories = ledger["stories"]
    assert isinstance(stories, dict)
    for raw_volume, directive in directives.items():
        if not isinstance(raw_volume, int) or isinstance(raw_volume, bool) or raw_volume < 1:
            raise ValueError(f"Story volume must be a positive integer: {raw_volume!r}")
        if not isinstance(directive, str):
            raise ValueError(f"Directive for volume {raw_volume} must be a string")
        key = str(raw_volume)
        cleaned = directive.strip()
        if not cleaned:
            stories.pop(key, None)
            continue
        previous = stories.get(key)
        created_at = previous.get("created_at") if isinstance(previous, dict) else None
        stories[key] = _story_entry(
            raw_volume,
            cleaned,
            now=timestamp,
            source=source,
            created_at=created_at if isinstance(created_at, str) else None,
        )
    ledger["updated_at"] = timestamp
    validate_ledger(ledger)
    atomic_write_json(Path(path).expanduser(), ledger)
    return ledger


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
    lines = []
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
    without_managed = _MANAGED_SECTION_RE.sub("", prompt_text)
    without_managed = without_managed.rstrip()
    lines = _directive_lines(directive)
    if not lines:
        return without_managed + ("\n" if without_managed else "")
    rendered = MANAGED_SECTION_MARKER + "\n" + "\n".join(f"- {line}" for line in lines)
    if without_managed:
        return without_managed + "\n\n" + rendered + "\n"
    return rendered + "\n"


def apply_active_directive(*, env_path: Path | None = None) -> dict[str, object]:
    resolved_env = Path(
        env_path or Path.home() / ".config" / "wirtelprimpf" / "openai.env"
    ).expanduser()
    paths = resolve_runtime_paths(resolved_env)
    state = load_story_state(paths["state"])
    current_volume = effective_current_volume(state)
    ledger = load_ledger(paths["ledger"], seed_story_iii=True)
    stories = ledger["stories"]
    assert isinstance(stories, dict)
    active = stories.get(str(current_volume), {})
    directive = active.get("directive", "") if isinstance(active, dict) else ""
    if not isinstance(directive, str):
        raise ValueError(f"Directive for story {current_volume} is invalid")

    prompt_path = paths["prompt"]
    _require_regular_non_symlink(prompt_path, label="story prompt config")
    try:
        original = prompt_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"Story prompt config is not valid UTF-8: {prompt_path}") from exc
    rendered = replace_managed_prompt_section(original, directive)
    changed = rendered != original
    if changed:
        atomic_write_text(prompt_path, rendered)
    else:
        os.chmod(prompt_path, 0o600)
    return {
        "ok": True,
        "current_volume": current_volume,
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
    state = load_story_state(paths["state"])
    current_volume = effective_current_volume(state)
    ledger = load_ledger(paths["ledger"], seed_story_iii=True)
    return {
        "ok": True,
        "current_volume": current_volume,
        "paths": {key: str(value) for key, value in paths.items()},
        "roles": story_roles(current_volume, ledger),
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
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
