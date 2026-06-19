#!/usr/bin/env python3
"""Generate Wirtelprimpf-style cat images and optionally publish them to Git."""

from __future__ import annotations

import base64
import binascii
import argparse
import json
import os
import random
import stat
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final
import re
from datetime import timezone
import time
import tempfile

from openai import OpenAI
from PIL import Image

OPERANDI_CLASSIC: Final = "classic"
OPERANDI_STORY: Final = "story"
OPERANDI_BOTH: Final = "both"
OPERANDI_VALUES: Final = frozenset({OPERANDI_CLASSIC, OPERANDI_STORY, OPERANDI_BOTH})
PROMPT_CONFIG_MAIN_SECTION: Final = "hauptteil"
PROMPT_CONFIG_FIXED_SECTION_WORDS: Final = ("fix", "zwingend", "bildregel")
STORY_HISTORY_COUNT: Final = 10
STORY_ENTRY_TARGET: Final = "ungefaehr eine halbe DIN-A4-Seite"
STORY_FIRST_ENTRY_TARGET: Final = "ungefaehr eine ganze DIN-A4-Seite"
INITIAL_STORY_DIRECTIONS: Final = (
    "Eine kleine Rettungs- und Heimkehrgeschichte: Die Figuren verlieren etwas scheinbar Banales, merken aber nach und nach, dass daran ihr Zuhause, ihre Wuenschbarkeit und ihr Mut haengen.",
    "Eine absurde Entdeckungsreise: Aus einer winzigen Stoerung im Haushalt waechst der Verdacht, dass die Wohnung groesser, aelter und eigensinniger ist, als irgendjemand zugeben will.",
    "Eine leise Rebellion gegen eine laecherliche Ordnung: Die Figuren geraten in Regeln, Formulare und Rituale, die harmlos beginnen und ploetzlich ihr Zusammenleben bedrohen.",
    "Ein warm-komisches Geheimnis: Die Maus weiss von Anfang an mehr, die Moehre ist wichtiger als sie aussieht, und die Katzen muessen lernen, einander auch im Unsinn zu vertrauen.",
    "Eine Reise vom kleinen Zimmer in eine groessere Welt: Der erste Teil soll ein starkes Versprechen setzen, dass hinter Tueren, Ritzen und Alltagsgegenstaenden ein eigenwilliges Abenteuer wartet.",
)
STORY_DOCUMENT_PREFIX: Final = "Wirtelprimpf_Story"
STORY_DOCUMENT_NAME: Final = "Wirtelprimpf_Story_I.md"
LEGACY_STORY_DOCUMENT_NAME: Final = "wirtelprimpf_fortlaufende_geschichte.md"
STORY_STATE_FILE: Final = "wirtelprimpf_story_state.json"
STORY_FINISH_PARTS_MIN: Final = 3
STORY_FINISH_PARTS_MAX: Final = 5
WORKING_DIR_NAME: Final = "working"
WORKING_IMAGE_NAME: Final = "latest.png"
WORKING_PROMPT_NAME: Final = "latest.txt"
WORKING_STORY_NAME: Final = "latest.md"
WORKING_FULL_STORY_NAME: Final = "Full_Story.md"
FLEX_PROCESSING_DEFAULT: str = "flex"
FLEX_PROCESSING_MODES = frozenset({FLEX_PROCESSING_DEFAULT})
FLEX_PROCESSING_ENABLED_VALUES = {"1", "true", "yes", "on", "enabled", "enable"}
FLEX_PROCESSING_LEGACY_ENABLED_VALUES = {"high", "low"}
FLEX_PROCESSING_DISABLED_VALUES = {"0", "false", "no", "off", "disabled", "disable", "default", "standard"}
IMAGE_SIZE_PATTERN: Final = r"^\d+x\d+$"
IMAGE_SIZE_PATTERN_RE: Final = re.compile(IMAGE_SIZE_PATTERN)
OUTPUT_RESOLUTION_ALIASES: Final = {
    "": None,
    "source": None,
    "original": None,
    "none": None,
    "2k": (2560, 1440),
    "qhd": (2560, 1440),
    "1440p": (2560, 1440),
    "4k": (3840, 2160),
    "uhd": (3840, 2160),
    "2160p": (3840, 2160),
}
RESOLUTION_MAX_DIM: Final = 8192
IMAGE_PAYLOAD_MAX_BYTES: Final = 80 * 1024 * 1024
REPO_SLUG_PATTERN: Final = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")
REPO_BRANCH_PATTERN: Final = re.compile(r"^(?!/|.*//|.*\.\.|.*\/$)[A-Za-z0-9._-]{1,120}(?:/[A-Za-z0-9._-]{1,120})*$")
GIT_TIMEOUT_SECONDS: Final = 120
GENERATION_RETRIES: Final = 3
GENERATION_RETRY_BASE_SECONDS: Final = 2
COMMAND_PATHS: Final = ("/usr/local/sbin", "/usr/local/bin", "/usr/sbin", "/usr/bin", "/sbin", "/bin")
ENV_BLACKLIST: Final = frozenset(
    {
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_COMMON_DIR",
        "GIT_CONFIG",
        "GIT_CONFIG_COUNT",
        "GIT_CONFIG_GLOBAL",
        "GIT_CONFIG_NOSYSTEM",
        "GIT_CONFIG_PARAMETERS",
        "GIT_CONFIG_SYSTEM",
        "GIT_DIR",
        "GIT_EXEC_PATH",
        "GIT_EXTERNAL_DIFF",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ASKPASS",
        "GIT_SSH",
        "GIT_SSH_COMMAND",
        "GIT_TEMPLATE_DIR",
        "GIT_WORK_TREE",
        "LD_LIBRARY_PATH",
        "LD_PRELOAD",
        "PYTHONHOME",
        "PYTHONNOUSERSITE",
        "PYTHONPATH",
        "PYTHONSTARTUP",
        "PYTHONUSERBASE",
    }
)
OPENAI_ENV_PREFIXES: Final = ("OPENAI_", "AZURE_OPENAI_")
_COMMAND_ENV_CACHE: dict[str, str] | None = None
_SECURE_EXECUTABLE_CACHE: dict[str, str] = {}
VERSION: Final = "0.6.0"
PUBLISH_STATE_FILE: Final = "wirtelprimpf_publish_state.json"
PUBLISH_PUSH_INTERVAL_PATCHES: Final = 100
PUBLISH_RELEASE_PUSH_INTERVAL: Final = 10
STATUS_OK: Final = "ok"
STATUS_ERROR: Final = "error"
MODE_STATUS: Final = "status"
MODE_CHECK_CONFIG: Final = "check_config"
MODE_DRY_RUN: Final = "dry_run"
MODE_RUN: Final = "run"
MODE_VALUES: Final = frozenset({MODE_STATUS, MODE_CHECK_CONFIG, MODE_DRY_RUN, MODE_RUN})


@dataclass
class RunSummary:
    success: int = 0
    failed: int = 0
    skipped: int = 0
    prompts: int = 0
    total: int = 0
    exit_code: int = 0


@dataclass(frozen=True)
class GenerationPlan:
    prompt: str
    kind: str = OPERANDI_CLASSIC
    story_part: str | None = None
    story_entry_markdown: str | None = None
    story_document_append: str | None = None
    story_document_path: Path | None = None
    story_state_after_success: StoryState | None = None
    story_title_after_success: bool = False


@dataclass(frozen=True)
class PublishState:
    patch_count: int = 0
    publish_push_count: int = 0
    semver_base: str = VERSION
    semver_base_patch_count: int = 0


@dataclass(frozen=True)
class StoryState:
    current_volume: int = 1
    closing_remaining: int = 0
    closing_total: int = 0
    pending_new_volume: bool = False
    close_request_seen: bool = False


def _parse_version_base(version: str) -> tuple[int, int, int, str]:
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)(.*)$", version.strip())
    if not m:
        raise RuntimeError(f"Invalid VERSION value: {version!r}")
    major, minor, patch, suffix = m.groups()
    return int(major), int(minor), int(patch), suffix


BASE_VERSION_MAJOR, BASE_VERSION_MINOR, BASE_VERSION_PATCH, VERSION_SUFFIX = _parse_version_base(VERSION)


def format_json(value: object, *, compact: bool = False, indent: int = 2) -> str:
    if compact:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return json.dumps(value, indent=indent, ensure_ascii=False)


def validate_mode(mode: str) -> str:
    if mode not in MODE_VALUES:
        raise ValueError(f"Unknown mode: {mode!r}")
    return mode


def emit_mode_line(mode: str) -> None:
    print(f"mode: {validate_mode(mode)}")


def extract_minor_version(version: str) -> str:
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)", version.strip())
    if not m:
        raise RuntimeError(f"Invalid VERSION value: {version!r}")
    return f"{m.group(1)}.{m.group(2)}"


def _derive_version_numbers(
    patch_count: int,
    *,
    semver_base_patch_count: int = 0,
) -> tuple[int, int, int]:
    if patch_count < 0:
        raise ValueError(f"patch_count must be >= 0, got {patch_count!r}")
    if semver_base_patch_count < 0:
        raise ValueError(f"semver_base_patch_count must be >= 0, got {semver_base_patch_count!r}")
    if semver_base_patch_count > patch_count:
        raise ValueError(
            f"semver_base_patch_count must be <= patch_count, got {semver_base_patch_count!r} > {patch_count!r}"
        )
    patch_offset = patch_count - semver_base_patch_count
    return BASE_VERSION_MAJOR, BASE_VERSION_MINOR, BASE_VERSION_PATCH + patch_offset


def derive_version_from_patch_count(
    patch_count: int,
    *,
    semver_base_patch_count: int = 0,
) -> str:
    major_version, minor_version, patch_version = _derive_version_numbers(
        patch_count,
        semver_base_patch_count=semver_base_patch_count,
    )
    return f"{major_version}.{minor_version}.{patch_version}{VERSION_SUFFIX}"


def resolve_runtime_version(*, patch_count: int, semver_base_patch_count: int = 0) -> str:
    return derive_version_from_patch_count(
        patch_count,
        semver_base_patch_count=semver_base_patch_count,
    )


def build_status_envelope(
    *,
    ok: bool,
    status: str,
    mode: str,
    version: str = VERSION,
    exit_code: int,
    message: str | None = None,
    summary: dict[str, object] | None = None,
    details: dict[str, object] | None = None,
    checks: list[dict[str, object]] | None = None,
    check_config: bool | None = None,
    prompt_count: int | None = None,
    local_outdir: str | None = None,
    model: str | None = None,
    image_size: str | None = None,
    output_resolution: str | None = None,
    repo_path: str | None = None,
    type: str | None = None,
    index: int | None = None,
    total: int | None = None,
    prompt_preview: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "ok": ok,
        "version": version,
        "timestamp": build_status_timestamp(),
        "mode": validate_mode(mode),
        "status": status,
        "exit_code": exit_code,
    }
    if message is not None:
        payload["message"] = message
    if summary is not None:
        payload["summary"] = summary
    if details is not None:
        payload["details"] = details
    if checks is not None:
        payload["checks"] = checks
    if check_config is not None:
        payload["check_config"] = check_config
    if prompt_count is not None:
        payload["prompt_count"] = prompt_count
    if local_outdir is not None:
        payload["local_outdir"] = local_outdir
    if model is not None:
        payload["model"] = model
    if image_size is not None:
        payload["image_size"] = image_size
    if output_resolution is not None:
        payload["output_resolution"] = output_resolution
    if repo_path is not None:
        payload["repo_path"] = repo_path
    if type is not None:
        payload["type"] = type
    if index is not None:
        payload["index"] = index
    if total is not None:
        payload["total"] = total
    if prompt_preview is not None:
        payload["prompt_preview"] = prompt_preview
    return payload


def env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    cleaned = value.strip()
    if cleaned == "":
        return default
    if "\x00" in cleaned:
        raise RuntimeError(f"Invalid {name} value contains a NUL byte")
    return cleaned


def parse_positive_int(name: str, value: str | None, *, default: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value.strip())
    except ValueError as exc:
        raise RuntimeError(f"Invalid {name} value: {value!r}. Expected an integer >= 1") from exc
    if parsed < 1:
        raise RuntimeError(f"Invalid {name} value: {value!r}. Expected an integer >= 1")
    return parsed


def parse_non_negative_int(name: str, value: str | None, *, default: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value.strip())
    except ValueError as exc:
        raise RuntimeError(f"Invalid {name} value: {value!r}. Expected an integer >= 0") from exc
    if parsed < 0:
        raise RuntimeError(f"Invalid {name} value: {value!r}. Expected an integer >= 0")
    return parsed


def parse_bool_flag(name: str, value: str | None, *, default: bool) -> bool:
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on", "enabled", "enable"}:
        return True
    if normalized in {"0", "false", "no", "off", "disabled", "disable"}:
        return False
    raise RuntimeError(f"Invalid {name} value: {value!r}. Expected a boolean flag")


def _is_world_or_group_writable(mode: int) -> bool:
    return bool(mode & 0o22)


def _is_system_command_path(path: Path) -> bool:
    try:
        resolved = path.resolve(strict=False)
    except OSError:
        return False
    for base in COMMAND_PATHS:
        base_path = Path(base)
        try:
            if resolved == base_path or resolved.is_relative_to(base_path):
                return True
        except ValueError:
            continue
    return False


def _is_trusted_command_owner(uid: int, path: Path) -> bool:
    return uid in {0, os.getuid()} or (uid == 65534 and _is_system_command_path(path))


def _is_trusted_command_group(gid: int, path: Path) -> bool:
    return gid in {0, os.getgid()} or (gid == 65534 and _is_system_command_path(path))


def _resolve_executable_path(candidate: Path) -> str | None:
    if candidate.is_symlink():
        return None

    try:
        status = candidate.lstat()
    except OSError:
        return None

    if not candidate.is_file() or not os.access(candidate, os.X_OK):
        return None
    if not _is_trusted_command_owner(status.st_uid, candidate):
        return None
    if not _is_trusted_command_group(status.st_gid, candidate):
        return None
    if _is_world_or_group_writable(status.st_mode):
        return None
    if status.st_mode & (stat.S_ISUID | stat.S_ISGID):
        return None

    parent = candidate.parent
    if parent.is_symlink() or not parent.is_dir():
        return None

    try:
        parent_status = parent.lstat()
    except OSError:
        return None

    if not _is_trusted_command_owner(parent_status.st_uid, parent):
        return None
    if _is_world_or_group_writable(parent_status.st_mode):
        return None
    return str(candidate)


def _resolve_secure_executable(name: str, *, required: bool = True) -> str | None:
    if not name or "\x00" in name:
        if required:
            raise RuntimeError(f"Invalid executable name: {name!r}")
        return None

    candidates: list[str] = []
    if os.path.isabs(name):
        candidates.append(name)
    else:
        if os.path.sep in name:
            if required:
                raise RuntimeError(f"Invalid executable name: {name!r}")
            return None
        if not re.fullmatch(r"[A-Za-z0-9._+-]+", name):
            if required:
                raise RuntimeError(f"Invalid executable name: {name!r}")
            return None
        for base in COMMAND_PATHS:
            candidates.append(f"{base.rstrip('/')}/{name}")

    for candidate in candidates:
        resolved = _resolve_executable_path(Path(candidate))
        if resolved is not None:
            return resolved

    if required:
        raise RuntimeError(f"Required executable not found or insecure: {name}")
    return None


def _resolve_secure_executable_cached(name: str, *, required: bool = True) -> str | None:
    cached = _SECURE_EXECUTABLE_CACHE.get(name)
    if cached is not None:
        if _is_cached_secure_executable(cached):
            return cached
        _SECURE_EXECUTABLE_CACHE.pop(name, None)

    resolved = _resolve_secure_executable(name, required=required)
    if resolved is not None:
        _SECURE_EXECUTABLE_CACHE[name] = resolved
    return resolved


def _is_cached_secure_executable(path: str) -> bool:
    candidate = Path(path)
    if candidate.is_symlink():
        return False

    try:
        status = candidate.lstat()
    except OSError:
        return False

    if not candidate.is_file() or not os.access(candidate, os.X_OK):
        return False
    if status.st_uid not in {0, os.getuid()}:
        return False
    if status.st_gid not in {0, os.getgid()}:
        return False
    if _is_world_or_group_writable(status.st_mode):
        return False
    if status.st_mode & (stat.S_ISUID | stat.S_ISGID):
        return False

    parent = candidate.parent
    if parent.is_symlink() or not parent.is_dir():
        return False

    try:
        parent_status = parent.lstat()
    except OSError:
        return False

    if parent_status.st_uid not in {0, os.getuid()}:
        return False
    if _is_world_or_group_writable(parent_status.st_mode):
        return False
    return True


def _command_env() -> dict[str, str]:
    global _COMMAND_ENV_CACHE
    if _COMMAND_ENV_CACHE is not None:
        return _COMMAND_ENV_CACHE.copy()

    environment = os.environ.copy()
    for key in ENV_BLACKLIST:
        environment.pop(key, None)
    for key in list(environment):
        if key.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_")):
            environment.pop(key, None)
    for key in list(environment):
        if key.startswith(OPENAI_ENV_PREFIXES):
            environment.pop(key, None)
    environment["PATH"] = ":".join(COMMAND_PATHS)
    environment.setdefault("LANG", "C.UTF-8")
    environment.setdefault("LC_ALL", "C.UTF-8")
    _COMMAND_ENV_CACHE = environment
    return environment.copy()


def _assert_private_directory(path: Path, *, label: str) -> None:
    if path.is_symlink():
        raise RuntimeError(f"{label} must not be a symlink: {path}")
    if not path.is_dir():
        raise RuntimeError(f"{label} is not a directory: {path}")
    mode = path.stat().st_mode
    if _is_world_or_group_writable(mode):
        raise RuntimeError(f"{label} is not secure (group/world writable): {path}")


def _assert_safe_atomic_write_target(path: Path, *, label: str) -> None:
    _assert_private_directory(path.parent, label=f"Parent directory for {label}")
    if path.exists():
        if path.is_symlink():
            raise RuntimeError(f"{label} output must not be a symlink: {path}")
        if not path.is_file():
            raise RuntimeError(f"{label} output must be a regular file: {path}")
        mode = path.stat().st_mode
        if _is_world_or_group_writable(mode):
            raise RuntimeError(f"{label} output must not be group/world writable: {path}")


def normalize_repo_path(path: Path) -> Path:
    if path.is_symlink():
        raise RuntimeError(f"Invalid WIRTELPRIMPF_REPO_PATH: symlink detected: {path}")
    if path.name == ".git" and (path / "config").is_file() and (path / "HEAD").is_file() and path.parent.is_dir():
        return path.parent
    return path


def normalize_repo_slug(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned = value.strip()
    if cleaned == "":
        return None
    normalized = cleaned.replace("https://github.com/", "").replace("http://github.com/", "")
    if normalized.endswith(".git"):
        normalized = normalized[:-4]

    if not REPO_SLUG_PATTERN.match(normalized):
        raise RuntimeError(
            "Invalid WIRTELPRIMPF_REPO_SLUG value. Expected format: <owner>/<repository> ("
            "for example: exampleuser/example-repo)"
        )
    return normalized


def normalize_repo_branch(value: str | None) -> str:
    branch = (value or "main").strip() or "main"
    if len(branch) > 120:
        raise RuntimeError(f"Invalid WIRTELPRIMPF_REPO_BRANCH value: length must be <= 120: {branch!r}")
    if not REPO_BRANCH_PATTERN.match(branch):
        raise RuntimeError(
            "Invalid WIRTELPRIMPF_REPO_BRANCH value. Allowed characters: letters, digits, ., _, -, and /"
        )
    return branch


def ensure_output_directory(path: Path) -> None:
    if path.is_symlink():
        raise RuntimeError(f"WIRTELPRIMPF_LOCAL_OUTDIR must not be a symlink: {path}")
    if path.exists():
        if path.is_symlink() or not path.is_dir():
            raise RuntimeError(f"WIRTELPRIMPF_LOCAL_OUTDIR is not a directory: {path}")
        _assert_private_directory(path, label="WIRTELPRIMPF_LOCAL_OUTDIR")
        if not os.access(path, os.W_OK | os.X_OK):
            raise RuntimeError(f"WIRTELPRIMPF_LOCAL_OUTDIR is not writable: {path}")
        return

    parent = path.parent
    _assert_private_directory(parent, label="WIRTELPRIMPF_LOCAL_OUTDIR parent directory")
    if not parent.is_dir():
        raise RuntimeError(f"WIRTELPRIMPF_LOCAL_OUTDIR parent directory does not exist: {parent}")
    if not os.access(parent, os.W_OK | os.X_OK):
        raise RuntimeError(f"Cannot create WIRTELPRIMPF_LOCAL_OUTDIR in non-writable directory: {parent}")


def ensure_private_output_directory(path: Path, *, env_name: str) -> None:
    if path.is_symlink():
        raise RuntimeError(f"{env_name} must not be a symlink: {path}")
    if path.exists():
        if path.is_symlink() or not path.is_dir():
            raise RuntimeError(f"{env_name} is not a directory: {path}")
        _assert_private_directory(path, label=env_name)
        if not os.access(path, os.W_OK | os.X_OK):
            raise RuntimeError(f"{env_name} is not writable: {path}")
        return

    parent = path.parent
    _assert_private_directory(parent, label=f"{env_name} parent directory")
    if not parent.is_dir():
        raise RuntimeError(f"{env_name} parent directory does not exist: {parent}")
    if not os.access(parent, os.W_OK | os.X_OK):
        raise RuntimeError(f"Cannot create {env_name} in non-writable directory: {parent}")
    path.mkdir(parents=True, exist_ok=True)
    _assert_private_directory(path, label=env_name)


def update_working_full_story_link(config: Config, story_document_path: Path | None) -> None:
    if story_document_path is None or not story_document_path.exists():
        return
    if story_document_path.is_symlink() or not story_document_path.is_file():
        raise RuntimeError(f"Story document must be a regular non-symlink file: {story_document_path}")
    replace_symlink(config.working_dir / WORKING_FULL_STORY_NAME, story_document_path)


def relative_symlink_target(link_path: Path, target_path: Path) -> Path:
    return Path(
        os.path.relpath(
            target_path.resolve(strict=False),
            start=link_path.parent.resolve(strict=False),
        )
    )


def replace_symlink(link_path: Path, target_path: Path) -> None:
    if link_path.exists() or link_path.is_symlink():
        if link_path.is_dir() and not link_path.is_symlink():
            raise RuntimeError(f"Working link path is a directory: {link_path}")
        link_path.unlink()
    link_path.symlink_to(relative_symlink_target(link_path, target_path))


def remove_working_path(path: Path) -> None:
    if path.exists() or path.is_symlink():
        if path.is_dir() and not path.is_symlink():
            raise RuntimeError(f"Working output path is a directory: {path}")
        path.unlink()


def active_story_document_path(config: Config) -> Path | None:
    try:
        state = read_story_state(config.story_state_path)
    except RuntimeError:
        return config.story_document_path if config.story_document_path.exists() else None
    document_path = story_document_path_for_volume(config, state.current_volume)
    return document_path if document_path.exists() else None


def rotate_working_outputs(
    config: Config,
    local_png: Path,
    local_prompt: Path,
    local_story: Path | None,
    story_document_path: Path | None = None,
) -> None:
    ensure_private_output_directory(config.working_dir, env_name="WIRTELPRIMPF_WORKING_DIR")
    replace_symlink(config.working_dir / WORKING_IMAGE_NAME, local_png)
    replace_symlink(config.working_dir / WORKING_PROMPT_NAME, local_prompt)
    story_target = config.working_dir / WORKING_STORY_NAME
    if local_story is not None:
        replace_symlink(story_target, local_story)
    else:
        remove_working_path(story_target)
    update_working_full_story_link(config, story_document_path or active_story_document_path(config))


def sync_repo_working_outputs(
    repo_outdir: Path,
    local_png: Path,
    local_prompt: Path,
    local_story: Path | None,
    story_document_path: Path | None,
) -> list[Path]:
    repo_working_dir = repo_outdir / WORKING_DIR_NAME
    repo_working_dir.mkdir(parents=True, exist_ok=True)
    repo_image = repo_working_dir / WORKING_IMAGE_NAME
    repo_prompt = repo_working_dir / WORKING_PROMPT_NAME
    replace_symlink(repo_image, repo_outdir / local_png.name)
    replace_symlink(repo_prompt, repo_outdir / local_prompt.name)
    repo_paths = [repo_image, repo_prompt]

    repo_story = repo_working_dir / WORKING_STORY_NAME
    if local_story is not None:
        replace_symlink(repo_story, repo_outdir / local_story.name)
        repo_paths.append(repo_story)
    else:
        remove_working_path(repo_story)
        repo_paths.append(repo_story)

    repo_full_story = repo_working_dir / WORKING_FULL_STORY_NAME
    if story_document_path is not None:
        repo_story_document = repo_outdir / story_document_path.name
        replace_symlink(repo_full_story, repo_story_document)
        repo_paths.append(repo_full_story)
    else:
        remove_working_path(repo_full_story)
        repo_paths.append(repo_full_story)

    return repo_paths


def read_publish_state(path: Path) -> PublishState:
    if not path.exists():
        return PublishState()
    if path.is_symlink():
        raise RuntimeError(f"Invalid publish state path (symlink): {path}")
    if not path.is_file():
        raise RuntimeError(f"Invalid publish state path (not a file): {path}")

    try:
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"invalid publish state JSON in {path} (line {exc.lineno}, column {exc.colno}: {exc.msg})"
        ) from exc
    except UnicodeDecodeError as exc:
        raise RuntimeError(f"publish state file is not valid UTF-8: {path}") from exc
    except OSError as exc:
        raise RuntimeError(f"failed to read publish state file: {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise RuntimeError(f"invalid publish state: expected JSON object in {path}, got {type(payload).__name__}")

    if "patch_count" in payload:
        raw_patch_count = payload["patch_count"]
    elif "patch_version" in payload:
        raw_patch_count = payload["patch_version"]
    else:
        raise RuntimeError(f"invalid publish state: missing patch_count and patch_version in {path}")
    if not isinstance(raw_patch_count, int) or isinstance(raw_patch_count, bool):
        raise RuntimeError(f"invalid publish state: patch_count must be a non-boolean integer in {path}: {raw_patch_count!r}")
    patch_count = raw_patch_count
    publish_push_count = payload.get("publish_push_count", payload.get("minor_push_count", 0))
    semver_base = payload.get("semver_base")
    raw_semver_base_patch_count = payload.get("semver_base_patch_count", 0)
    if patch_count < 0:
        raise RuntimeError(f"invalid publish state: patch_count must be >= 0 in {path}: {patch_count!r}")
    if (
        not isinstance(publish_push_count, int)
        or isinstance(publish_push_count, bool)
        or publish_push_count < 0
    ):
        raise RuntimeError(
            f"invalid publish state: publish_push_count must be a non-boolean integer >= 0 in {path}: {publish_push_count!r}"
        )
    if semver_base is None:
        semver_base = VERSION
        semver_base_patch_count = 0
    elif not isinstance(semver_base, str) or not semver_base.strip():
        raise RuntimeError(f"invalid publish state: semver_base must be a non-empty string in {path}: {semver_base!r}")
    elif semver_base != VERSION:
        semver_base = VERSION
        semver_base_patch_count = patch_count
    else:
        if (
            not isinstance(raw_semver_base_patch_count, int)
            or isinstance(raw_semver_base_patch_count, bool)
            or raw_semver_base_patch_count < 0
        ):
            raise RuntimeError(
                "invalid publish state: semver_base_patch_count must be a non-boolean integer "
                f">= 0 in {path}: {raw_semver_base_patch_count!r}"
            )
        semver_base_patch_count = raw_semver_base_patch_count

    if semver_base_patch_count > patch_count:
        raise RuntimeError(
            "invalid publish state: semver_base_patch_count must be <= patch_count in "
            f"{path}: {semver_base_patch_count!r} > {patch_count!r}"
        )
    return PublishState(
        patch_count=patch_count,
        publish_push_count=publish_push_count,
        semver_base=semver_base,
        semver_base_patch_count=semver_base_patch_count,
    )


def write_publish_state(path: Path, state: PublishState) -> None:
    payload = {
        "patch_count": state.patch_count,
        "patch_version": state.patch_count,
        "publish_push_count": state.publish_push_count,
        "semver_base": state.semver_base,
        "semver_base_patch_count": state.semver_base_patch_count,
    }
    write_bytes_atomically(path, json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8"))


def int_to_roman(value: int) -> str:
    if value < 1 or value > 3999:
        raise ValueError(f"Roman story volume must be between 1 and 3999, got {value!r}")
    numerals = (
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    )
    remaining = value
    parts: list[str] = []
    for number, numeral in numerals:
        while remaining >= number:
            parts.append(numeral)
            remaining -= number
    return "".join(parts)


def story_document_name_for_volume(volume: int) -> str:
    return f"{STORY_DOCUMENT_PREFIX}_{int_to_roman(volume)}.md"


def story_document_path_for_volume(config: Config, volume: int) -> Path:
    return config.story_document_path.parent / story_document_name_for_volume(volume)


def read_story_state(path: Path) -> StoryState:
    if not path.exists():
        return StoryState()
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"Story state must be a regular non-symlink file: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid story state JSON in {path} (line {exc.lineno}, column {exc.colno}: {exc.msg})") from exc
    except UnicodeDecodeError as exc:
        raise RuntimeError(f"story state file is not valid UTF-8: {path}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"invalid story state: expected object in {path}")

    def read_int(key: str, default: int) -> int:
        value = payload.get(key, default)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise RuntimeError(f"invalid story state: {key} must be a non-negative integer in {path}")
        return value

    current_volume = read_int("current_volume", 1)
    if current_volume < 1:
        raise RuntimeError(f"invalid story state: current_volume must be >= 1 in {path}")
    pending_new_volume = payload.get("pending_new_volume", False)
    close_request_seen = payload.get("close_request_seen", False)
    if not isinstance(pending_new_volume, bool):
        raise RuntimeError(f"invalid story state: pending_new_volume must be bool in {path}")
    if not isinstance(close_request_seen, bool):
        raise RuntimeError(f"invalid story state: close_request_seen must be bool in {path}")
    return StoryState(
        current_volume=current_volume,
        closing_remaining=read_int("closing_remaining", 0),
        closing_total=read_int("closing_total", 0),
        pending_new_volume=pending_new_volume,
        close_request_seen=close_request_seen,
    )


def write_story_state(path: Path, state: StoryState) -> None:
    payload = {
        "current_volume": state.current_volume,
        "closing_remaining": state.closing_remaining,
        "closing_total": state.closing_total,
        "pending_new_volume": state.pending_new_volume,
        "close_request_seen": state.close_request_seen,
    }
    write_text_atomically(path, json.dumps(payload, indent=2, ensure_ascii=False))


def prepare_story_state_for_plan(config: Config, *, dry_run: bool) -> tuple[StoryState, Path, str]:
    state = read_story_state(config.story_state_path)
    current_volume = state.current_volume
    closing_remaining = state.closing_remaining
    closing_total = state.closing_total
    pending_new_volume = state.pending_new_volume
    close_request_seen = state.close_request_seen

    if pending_new_volume:
        current_volume += 1
        closing_remaining = 0
        closing_total = 0
        pending_new_volume = False

    if not config.story_finish_requested:
        close_request_seen = False
    elif not close_request_seen and closing_remaining == 0:
        closing_remaining = random.randint(config.story_finish_parts_min, config.story_finish_parts_max)
        closing_total = closing_remaining
        close_request_seen = True

    active_state = StoryState(
        current_volume=current_volume,
        closing_remaining=closing_remaining,
        closing_total=closing_total,
        pending_new_volume=pending_new_volume,
        close_request_seen=close_request_seen,
    )
    story_document_path = story_document_path_for_volume(config, current_volume)
    instruction = ""
    if closing_remaining > 0:
        current_closing_part = max(1, closing_total - closing_remaining + 1)
        if closing_remaining == 1:
            instruction = (
                f"Dies ist der letzte Abschluss-Teil {current_closing_part}/{closing_total}. "
                "Fuehre die laufende Geschichte zu einem klaren, befriedigenden Ende. "
                "Schliesse die offenen Motive um die beiden Katzen, die Moehre und die Maus."
            )
        else:
            instruction = (
                f"Die laufende Geschichte soll in insgesamt {closing_total} Teilen auslaufen. "
                f"Dies ist Abschluss-Teil {current_closing_part}/{closing_total}; "
                f"nach diesem Teil bleiben noch {closing_remaining - 1}. "
                "Ziehe offene Motive sichtbar zusammen, aber beende noch nicht alles sofort."
            )
    return active_state, story_document_path, instruction


def story_state_after_success(state: StoryState) -> StoryState:
    if state.closing_remaining <= 0:
        return state
    remaining = state.closing_remaining - 1
    return StoryState(
        current_volume=state.current_volume,
        closing_remaining=remaining,
        closing_total=state.closing_total if remaining > 0 else 0,
        pending_new_volume=remaining == 0,
        close_request_seen=state.close_request_seen,
    )


def publish_state_path(repo_path: Path) -> Path:
    if repo_path.name == ".git":
        return repo_path / PUBLISH_STATE_FILE
    return repo_path / ".git" / PUBLISH_STATE_FILE


@dataclass(frozen=True)
class Config:
    local_outdir: Path
    working_dir: Path
    repo_path: Path | None
    repo_slug: str | None
    repo_subdir: str
    repo_branch: str
    image_model: str
    image_size: str
    output_resolution: str
    flex_processing_mode: str | None
    operandi: str
    prompt_config_path: Path
    story_prompt_config_path: Path
    story_model: str
    story_document_path: Path
    story_state_path: Path
    story_finish_requested: bool
    story_finish_parts_min: int
    story_finish_parts_max: int
    commit_author_name: str
    commit_author_email: str


def load_config() -> Config:
    default_outdir = Path.home() / "Hintergrundbilder"
    config_home = Path(env("XDG_CONFIG_HOME", str(Path.home() / ".config")) or str(Path.home() / ".config"))
    default_prompt_config = config_home / "wirtelprimpf" / "prompt_config.md"
    default_story_prompt_config = config_home / "wirtelprimpf" / "story_prompt_config.md"
    repo_path = env("WIRTELPRIMPF_REPO_PATH")
    resolved_repo_path = normalize_repo_path(Path(repo_path).expanduser()) if repo_path else None
    repo_slug = normalize_repo_slug(env("WIRTELPRIMPF_REPO_SLUG"))
    local_outdir = Path(env("WIRTELPRIMPF_LOCAL_OUTDIR", str(default_outdir))).expanduser()
    story_finish_parts_min = parse_positive_int(
        "WIRTELPRIMPF_STORY_FINISH_PARTS_MIN",
        env("WIRTELPRIMPF_STORY_FINISH_PARTS_MIN"),
        default=STORY_FINISH_PARTS_MIN,
    )
    story_finish_parts_max = parse_positive_int(
        "WIRTELPRIMPF_STORY_FINISH_PARTS_MAX",
        env("WIRTELPRIMPF_STORY_FINISH_PARTS_MAX"),
        default=STORY_FINISH_PARTS_MAX,
    )
    if story_finish_parts_min > story_finish_parts_max:
        raise RuntimeError(
            "Invalid WIRTELPRIMPF_STORY_FINISH_PARTS_MIN/MAX: "
            f"{story_finish_parts_min} > {story_finish_parts_max}"
        )

    return Config(
        local_outdir=local_outdir,
        working_dir=Path(
            env("WIRTELPRIMPF_WORKING_DIR", str(local_outdir / WORKING_DIR_NAME))
            or str(local_outdir / WORKING_DIR_NAME)
        ).expanduser(),
        repo_path=resolved_repo_path,
        repo_slug=repo_slug,
        repo_subdir=env("WIRTELPRIMPF_REPO_SUBDIR", "Wirtelprimpf") or "Wirtelprimpf",
        repo_branch=normalize_repo_branch(env("WIRTELPRIMPF_REPO_BRANCH", "main")),
        image_model=env("WIRTELPRIMPF_IMAGE_MODEL", "gpt-image-2") or "gpt-image-2",
        image_size=parse_image_size(env("WIRTELPRIMPF_IMAGE_SIZE", "1536x1024") or "1536x1024"),
        output_resolution=parse_output_resolution(env("WIRTELPRIMPF_OUTPUT_RESOLUTION", "2k") or "2k"),
        flex_processing_mode=parse_flex_processing(),
        operandi=parse_operandi(env("WIRTELPRIMPF_OPERANDI", OPERANDI_CLASSIC)),
        prompt_config_path=Path(
            env("WIRTELPRIMPF_PROMPT_CONFIG", str(default_prompt_config)) or str(default_prompt_config)
        ).expanduser(),
        story_prompt_config_path=Path(
            env("WIRTELPRIMPF_STORY_PROMPT_CONFIG", str(default_story_prompt_config)) or str(default_story_prompt_config)
        ).expanduser(),
        story_model=env("WIRTELPRIMPF_STORY_MODEL", "gpt-5-mini") or "gpt-5-mini",
        story_document_path=Path(
            env(
                "WIRTELPRIMPF_STORY_DOCUMENT",
                str(Path(env("WIRTELPRIMPF_LOCAL_OUTDIR", str(default_outdir)) or str(default_outdir)) / STORY_DOCUMENT_NAME),
            )
            or str(default_outdir / STORY_DOCUMENT_NAME)
        ).expanduser(),
        story_state_path=Path(
            env("WIRTELPRIMPF_STORY_STATE", str(local_outdir / STORY_STATE_FILE))
            or str(local_outdir / STORY_STATE_FILE)
        ).expanduser(),
        story_finish_requested=parse_bool_flag(
            "WIRTELPRIMPF_STORY_FINISH",
            env("WIRTELPRIMPF_STORY_FINISH"),
            default=False,
        ),
        story_finish_parts_min=story_finish_parts_min,
        story_finish_parts_max=story_finish_parts_max,
        commit_author_name=env("WIRTELPRIMPF_GIT_AUTHOR_NAME", "Wirtelprimpf Bot") or "Wirtelprimpf Bot",
        commit_author_email=env("WIRTELPRIMPF_GIT_AUTHOR_EMAIL", "wirtelprimpf@example.invalid")
        or "wirtelprimpf@example.invalid",
    )


def parse_operandi(value: str | None) -> str:
    raw = (value or OPERANDI_CLASSIC).strip().lower()
    if "," in raw:
        parts = {parse_operandi(part.strip()) for part in raw.split(",") if part.strip()}
        if parts == {OPERANDI_CLASSIC, OPERANDI_STORY} or OPERANDI_BOTH in parts:
            return OPERANDI_BOTH
        if parts == {OPERANDI_CLASSIC}:
            return OPERANDI_CLASSIC
        if parts == {OPERANDI_STORY}:
            return OPERANDI_STORY
    aliases = {
        "1": OPERANDI_CLASSIC,
        "classic": OPERANDI_CLASSIC,
        "klassisch": OPERANDI_CLASSIC,
        "alt": OPERANDI_CLASSIC,
        "old": OPERANDI_CLASSIC,
        "2": OPERANDI_STORY,
        "story": OPERANDI_STORY,
        "geschichte": OPERANDI_STORY,
        "fortlaufend": OPERANDI_STORY,
        "operandi2": OPERANDI_STORY,
        "both": OPERANDI_BOTH,
        "beide": OPERANDI_BOTH,
        "all": OPERANDI_BOTH,
        "parallel": OPERANDI_BOTH,
        "classic+story": OPERANDI_BOTH,
        "story+classic": OPERANDI_BOTH,
    }
    normalized = aliases.get(raw, raw)
    if normalized not in OPERANDI_VALUES:
        raise RuntimeError(
            f"Invalid WIRTELPRIMPF_OPERANDI value: {value!r}. Expected classic/1, story/2, both, or classic,story"
        )
    return normalized


def operandi_includes(config: Config, mode: str) -> bool:
    if mode == OPERANDI_CLASSIC:
        return config.operandi in {OPERANDI_CLASSIC, OPERANDI_BOTH}
    if mode == OPERANDI_STORY:
        return config.operandi in {OPERANDI_STORY, OPERANDI_BOTH}
    return False


def run(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    if not command:
        raise RuntimeError("No command supplied")

    command_path = _resolve_secure_executable_cached(command[0], required=True)
    secure_command = [command_path, *command[1:]]

    try:
        return subprocess.run(
            secure_command,
            cwd=cwd,
            check=True,
            text=True,
            capture_output=True,
            timeout=GIT_TIMEOUT_SECONDS,
            env=_command_env(),
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Command timed out after {GIT_TIMEOUT_SECONDS}s: {' '.join(secure_command)}") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        message = f"Command failed: {' '.join(secure_command)}"
        if stderr:
            message = f"{message}: {stderr}"
        raise RuntimeError(message) from exc


def ensure_repo(config: Config) -> Path | None:
    if config.repo_path is None:
        return None
    if config.repo_path.is_symlink():
        raise RuntimeError(f"WIRTELPRIMPF_REPO_PATH must not be a symlink: {config.repo_path}")

    if not _resolve_secure_executable_cached("git", required=False):
        raise RuntimeError("git is required for repository operations")

    if (config.repo_path / ".git").is_dir():
        run(["git", "fetch", "origin", config.repo_branch], cwd=config.repo_path)
        run(["git", "checkout", config.repo_branch], cwd=config.repo_path)
        run(["git", "pull", "--ff-only", "origin", config.repo_branch], cwd=config.repo_path)
    else:
        if not config.repo_slug:
            raise RuntimeError("WIRTELPRIMPF_REPO_PATH is not a Git checkout and WIRTELPRIMPF_REPO_SLUG is unset")
        if config.repo_path.exists() and not config.repo_path.is_dir():
            raise RuntimeError(f"WIRTELPRIMPF_REPO_PATH is not a directory: {config.repo_path}")
        if not _resolve_secure_executable_cached("gh", required=False):
            raise RuntimeError("gh is required to clone WIRTELPRIMPF_REPO_SLUG")
        if config.repo_path.exists() and any(config.repo_path.iterdir()):
            raise RuntimeError(
                "WIRTELPRIMPF_REPO_PATH exists but is not a git checkout. "
                f"Refusing to clone into non-empty directory: {config.repo_path}"
            )

        config.repo_path.parent.mkdir(parents=True, exist_ok=True)
        run(["gh", "repo", "clone", config.repo_slug, str(config.repo_path)])
        run(["git", "checkout", config.repo_branch], cwd=config.repo_path)

    repo_subdir_name = config.repo_subdir.strip()
    if not repo_subdir_name or "/" in repo_subdir_name or "\\" in repo_subdir_name:
        raise RuntimeError(f"Invalid WIRTELPRIMPF_REPO_SUBDIR: {repo_subdir_name!r}")
    if repo_subdir_name in {"", ".", ".."}:
        raise RuntimeError(f"Invalid WIRTELPRIMPF_REPO_SUBDIR: {repo_subdir_name!r}")

    repo_outdir = config.repo_path / repo_subdir_name
    repo_outdir.mkdir(parents=True, exist_ok=True)
    return repo_outdir


def commit_and_push(config: Config, paths: list[Path], title: str) -> None:
    if config.repo_path is None:
        return

    try:
        relative_paths = [str(path.relative_to(config.repo_path)) for path in paths]
    except ValueError as exc:
        raise RuntimeError(f"Cannot publish paths not in repository path {config.repo_path!r}") from exc

    run(["git", "add", *relative_paths], cwd=config.repo_path)
    status = run(["git", "status", "--porcelain", "--", *relative_paths], cwd=config.repo_path)
    if not status.stdout.strip():
        return

    state_path = publish_state_path(config.repo_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    publish_state = read_publish_state(state_path)
    next_patch_count = publish_state.patch_count + 1
    runtime_version = resolve_runtime_version(
        patch_count=next_patch_count,
        semver_base_patch_count=publish_state.semver_base_patch_count,
    )
    next_publish_push_count = publish_state.publish_push_count
    push_performed = False
    release_ready = False

    run(
        [
            "git",
            "-c",
            f"user.name={config.commit_author_name}",
            "-c",
            f"user.email={config.commit_author_email}",
            "commit",
            "-m",
            f"Add Wirtelprimpf image: {title}",
        ],
        cwd=config.repo_path,
    )

    if next_patch_count % PUBLISH_PUSH_INTERVAL_PATCHES == 0:
        try:
            run(["git", "push", "origin", config.repo_branch], cwd=config.repo_path)
        except RuntimeError as exc:
            write_publish_state(
                state_path,
                PublishState(
                    patch_count=next_patch_count,
                    publish_push_count=next_publish_push_count,
                    semver_base=publish_state.semver_base,
                    semver_base_patch_count=publish_state.semver_base_patch_count,
                ),
            )
            raise RuntimeError(
                f"Publish boundary reached, commit recorded but push failed for {title}: {exc}"
            ) from exc
        push_performed = True
        next_publish_push_count += 1
        release_ready = next_publish_push_count % PUBLISH_RELEASE_PUSH_INTERVAL == 0

    write_publish_state(
        state_path,
        PublishState(
            patch_count=next_patch_count,
            publish_push_count=next_publish_push_count,
            semver_base=publish_state.semver_base,
            semver_base_patch_count=publish_state.semver_base_patch_count,
        ),
    )
    if push_performed and release_ready:
        print(
            f"Release cadence reached: {PUBLISH_RELEASE_PUSH_INTERVAL} publish pushes. "
            "Consider creating a release now."
        )
    print(
        f"version={runtime_version} patches_committed={next_patch_count} publish_pushes={next_publish_push_count} "
        f"pushed={push_performed}"
    )


def parse_resolution(value: str) -> tuple[int, int] | None:
    normalized = value.strip().lower()
    if normalized in OUTPUT_RESOLUTION_ALIASES:
        return OUTPUT_RESOLUTION_ALIASES[normalized]

    parts = normalized.split("x", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid WIRTELPRIMPF_OUTPUT_RESOLUTION: {value!r}")

    width_s, height_s = parts
    try:
        width = int(width_s)
        height = int(height_s)
    except ValueError as exc:
        raise ValueError(f"Invalid WIRTELPRIMPF_OUTPUT_RESOLUTION: {value!r}") from exc
    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid WIRTELPRIMPF_OUTPUT_RESOLUTION: {value!r}")
    return width, height


def resize_cover(path: Path, target_size: tuple[int, int] | None) -> None:
    if target_size is None:
        return

    target_width, target_height = target_size
    with Image.open(path) as image:
        image = image.convert("RGB")
        source_width, source_height = image.size
        scale = max(target_width / source_width, target_height / source_height)
        resized = image.resize(
            (round(source_width * scale), round(source_height * scale)),
            Image.Resampling.LANCZOS,
        )
        left = (resized.width - target_width) // 2
        top = (resized.height - target_height) // 2
        cropped = resized.crop((left, top, left + target_width, top + target_height))
        cropped.save(path, format="PNG", optimize=True)


def parse_image_size(value: str) -> str:
    raw = value.strip().lower()
    if not raw or not IMAGE_SIZE_PATTERN_RE.match(raw):
        raise ValueError(f"Invalid WIRTELPRIMPF_IMAGE_SIZE: {value!r}")

    width, height = raw.split("x", 1)
    width_i = int(width)
    height_i = int(height)
    if width_i <= 0 or height_i <= 0:
        raise ValueError(f"Invalid WIRTELPRIMPF_IMAGE_SIZE: {value!r}")
    if width_i > RESOLUTION_MAX_DIM or height_i > RESOLUTION_MAX_DIM:
        raise ValueError(f"Invalid WIRTELPRIMPF_IMAGE_SIZE: dimensions exceed {RESOLUTION_MAX_DIM}: {value!r}")
    return raw


def parse_output_resolution(value: str) -> str:
    raw = value.strip().lower()
    parsed = parse_resolution(raw)
    if parsed is None:
        return raw

    width, height = parsed
    if width > RESOLUTION_MAX_DIM or height > RESOLUTION_MAX_DIM:
        raise ValueError(
            f"Invalid WIRTELPRIMPF_OUTPUT_RESOLUTION: {value!r}; maximum is {RESOLUTION_MAX_DIM}x{RESOLUTION_MAX_DIM}"
        )
    return raw


def build_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")


def build_status_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def decode_image_bytes(data: str) -> bytes:
    try:
        decoded = base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise RuntimeError("OpenAI API returned malformed base64 image data") from exc

    if not decoded:
        raise RuntimeError("OpenAI API returned an empty image payload")
    if len(decoded) > IMAGE_PAYLOAD_MAX_BYTES:
        raise RuntimeError(f"OpenAI API image payload is unexpectedly large ({len(decoded)} bytes)")
    return decoded


def write_bytes_atomically(path: Path, payload: bytes) -> None:
    _assert_safe_atomic_write_target(path, label="binary output")
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=str(path.parent),
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(payload)
        if temp_path is None:
            raise RuntimeError("Failed to create temporary file for atomic write")
        temp_path.replace(path)
    except OSError:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise


def write_text_atomically(path: Path, content: str, *, encoding: str = "utf-8") -> None:
    write_bytes_atomically(path, content.encode(encoding))


def validate_prompt(text: str) -> str:
    if not text.strip():
        raise ValueError("Generated prompt is empty")
    if len(text) > 6000:
        raise ValueError("Generated prompt is too long")
    return text


def require_list(data: dict[str, object], key: str) -> list[str]:
    values = data.get(key)
    if not isinstance(values, list) or not values or not all(isinstance(value, str) for value in values):
        raise ValueError(f"Prompt config key {key!r} must be a non-empty list of strings")
    return values


def require_dict(data: dict[str, object], key: str) -> dict[str, object]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Prompt config key {key!r} must be an object")
    return value


def require_int(data: dict[str, object], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int):
        raise ValueError(f"Prompt config key {key!r} must be an integer")
    return value


def require_string(data: dict[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Prompt config key {key!r} must be a non-empty string")
    return value


def parse_flex_processing() -> str | None:
    raw = (env("WIRTELPRIMPF_FLEX_PROCESSING") or "").strip().lower()

    normalized = raw
    if not normalized:
        return FLEX_PROCESSING_DEFAULT
    if normalized in FLEX_PROCESSING_ENABLED_VALUES:
        return FLEX_PROCESSING_DEFAULT
    if normalized in FLEX_PROCESSING_DISABLED_VALUES:
        return None
    if normalized in FLEX_PROCESSING_MODES:
        return normalized
    if normalized in FLEX_PROCESSING_LEGACY_ENABLED_VALUES:
        return FLEX_PROCESSING_DEFAULT

    raise ValueError(
        "Invalid WIRTELPRIMPF_FLEX_PROCESSING value. "
        "Use on/off, true/false, yes/no, 1/0, enabled/disabled, default/standard, or flex."
    )


def bullet_list(values: list[str]) -> str:
    return "\n".join(f"- {value}" for value in values)


def load_json_prompt_config(path: Path) -> dict[str, object]:
    if path.is_symlink():
        raise ValueError(f"Invalid prompt config path (symlink): {path}")
    if not path.is_file():
        raise ValueError(f"Prompt config path must be a regular file: {path}")
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"invalid prompt config JSON in {path} (line {exc.lineno}, column {exc.colno}: {exc.msg})"
        ) from exc
    except UnicodeDecodeError as exc:
        raise ValueError(f"prompt config file is not valid UTF-8: {path}") from exc
    except OSError as exc:
        raise ValueError(f"failed to read prompt config file: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Prompt config must be a JSON object, got {type(data).__name__}")
    return data


def _clean_markdown_list_item(line: str) -> str:
    stripped = line.strip()
    stripped = re.sub(r"^\s*[-*+]\s+", "", stripped)
    stripped = re.sub(r"^\s*\d+[.)]\s+", "", stripped)
    return stripped.strip()


def _is_fixed_markdown_section(heading: str) -> bool:
    normalized = heading.casefold()
    return any(word in normalized for word in PROMPT_CONFIG_FIXED_SECTION_WORDS)


def _format_fixed_markdown_section(heading: str, values: list[str]) -> str:
    return f"{heading}:\n" + bullet_list(values)


def load_markdown_prompt_config(path: Path) -> dict[str, object]:
    if path.is_symlink():
        raise ValueError(f"Invalid prompt config path (symlink): {path}")
    if not path.is_file():
        raise ValueError(f"Prompt config path must be a regular file: {path}")
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"prompt config file is not valid UTF-8: {path}") from exc
    except OSError as exc:
        raise ValueError(f"failed to read prompt config file: {path}: {exc}") from exc

    sections: dict[str, list[str]] = {}
    fixed_sections: list[tuple[str, list[str]]] = []
    current: str | None = None
    current_top: str | None = None
    current_is_fixed = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        heading = re.match(r"^(#{2,6})\s+(.+?)\s*$", line)
        if heading:
            level = len(heading.group(1))
            title = heading.group(2).strip()
            if level > 2 and current_top is not None and current_top.strip().lower() == PROMPT_CONFIG_MAIN_SECTION:
                current = title
                current_is_fixed = True
                fixed_sections.append((current, []))
                continue
            current = title
            if level == 2:
                current_top = current
            if not current:
                raise ValueError(f"empty markdown section heading in {path}")
            current_is_fixed = _is_fixed_markdown_section(current)
            if current_is_fixed:
                fixed_sections.append((current, []))
            else:
                sections.setdefault(current, [])
            continue
        if current is None:
            continue
        cleaned = _clean_markdown_list_item(line)
        if cleaned:
            if current_is_fixed:
                fixed_sections[-1][1].append(cleaned)
            else:
                sections[current].append(cleaned)

    if not sections:
        raise ValueError(f"Prompt config Markdown has no '##' sections: {path}")

    main_key = None
    for key in sections:
        if key.strip().lower() == PROMPT_CONFIG_MAIN_SECTION:
            main_key = key
            break
    if main_key is None or not sections[main_key]:
        raise ValueError(f"Prompt config Markdown must contain a non-empty '## Hauptteil' section: {path}")

    pools = {key: values for key, values in sections.items() if key != main_key}
    fixed_sections = [(key, values) for key, values in fixed_sections if values]
    if not pools:
        raise ValueError(f"Prompt config Markdown must contain at least one category section besides Hauptteil: {path}")
    for key, values in pools.items():
        if not values:
            raise ValueError(f"Prompt config Markdown section {key!r} must contain at least one item")

    main_text = "\n".join(sections[main_key]).strip()
    main_blocks = [main_text]
    main_blocks.extend(_format_fixed_markdown_section(key, values) for key, values in fixed_sections)
    return {
        "main_text": main_text,
        "main": "\n\n".join(block for block in main_blocks if block).strip(),
        "sections": pools,
        "fixed_sections": {key: values for key, values in fixed_sections},
    }


def load_prompt_config(path: Path) -> dict[str, object]:
    if path.suffix.lower() == ".json":
        return load_json_prompt_config(path)
    parsed = load_markdown_prompt_config(path)
    return {"_format": "markdown", **parsed}


def is_markdown_prompt_config(data: dict[str, object]) -> bool:
    return data.get("_format") == "markdown"


def _select_markdown_sections(raw_sections: object, *, label: str) -> tuple[list[tuple[str, str]], dict[str, str]]:
    if not isinstance(raw_sections, dict):
        raise ValueError(f"{label} Markdown sections must be an object")
    selected: list[tuple[str, str]] = []
    format_values: dict[str, str] = {}
    for section, raw_values in raw_sections.items():
        if not isinstance(section, str) or not isinstance(raw_values, list) or not raw_values:
            raise ValueError(f"{label} Markdown sections must contain non-empty string lists")
        if not all(isinstance(value, str) for value in raw_values):
            raise ValueError(f"{label} Markdown section {section!r} contains non-string values")
        choice = random.choice(raw_values)
        selected.append((section, choice))
        placeholder = re.sub(r"[^A-Za-z0-9_]+", "_", section.strip().lower()).strip("_")
        if placeholder:
            format_values[placeholder] = choice
    return selected, format_values


def _format_selected_markdown_sections(selected: list[tuple[str, str]], *, heading_level: int) -> str:
    marker = "#" * heading_level
    return "\n\n".join(f"{marker} {section}\n{choice}" for section, choice in selected)


def _format_selected_markdown_bullets(selected: list[tuple[str, str]]) -> str:
    return "\n\n".join(f"{section}:\n- {choice}" for section, choice in selected)


def build_prompt(data: dict[str, object]) -> str:
    if is_markdown_prompt_config(data):
        main = require_string(data, "main")
        selected, format_values = _select_markdown_sections(data.get("sections"), label="Prompt config")
        try:
            main = main.format(**format_values)
        except KeyError as exc:
            raise ValueError(f"Prompt config Markdown Hauptteil expects unknown placeholder: {exc.args[0]!r}") from exc
        prompt = f"{main}\n\nAusgewaehlte Kategorien:\n\n" + _format_selected_markdown_bullets(selected)
        return validate_prompt(prompt)

    template = require_string(data, "template")
    values = {
        "fixed_image_rules": bullet_list(require_list(data, "fixed_image_rules")),
        "setting": random.choice(require_list(data, "settings")),
        "action": random.choice(require_list(data, "actions")),
        "joke": random.choice(require_list(data, "jokes")),
        "mood": random.choice(require_list(data, "moods")),
        "style": random.choice(require_list(data, "styles")),
    }
    try:
        prompt = template.format(**values).strip()
    except KeyError as exc:
        raise ValueError(f"Prompt template expects unknown placeholder: {exc.args[0]!r}") from exc
    return validate_prompt(prompt)


def birthday_config(data: dict[str, object]) -> dict[str, object]:
    if is_markdown_prompt_config(data):
        return {}
    return require_dict(data, "birthday")


def birthday_age(now: datetime, birthday: dict[str, object]) -> int:
    return require_int(birthday, "base_age") + (now.year - require_int(birthday, "base_year"))


def is_birthday_run(now: datetime, birthday: dict[str, object]) -> bool:
    force = os.environ.get("WIRTELPRIMPF_FORCE_BIRTHDAY", "").strip().lower()
    if force in {"1", "true", "yes", "ja"}:
        return True
    return (
        now.month == require_int(birthday, "month")
        and now.day == require_int(birthday, "day")
        and now.hour == require_int(birthday, "hour")
    )


def build_birthday_prompts(now: datetime, birthday: dict[str, object]) -> list[str]:
    template = require_string(birthday, "template")
    age = birthday_age(now, birthday)
    birthday_rules = bullet_list([rule.format(age=age) for rule in require_list(birthday, "shared_rules")])
    variants = birthday.get("variants")
    if not isinstance(variants, list) or not variants or not all(isinstance(variant, dict) for variant in variants):
        raise ValueError("Prompt config key 'birthday.variants' must be a non-empty list of objects")

    prompts = []
    for variant in variants:
        prompts.append(
            template.format(
                age=age,
                birthday_rules=birthday_rules,
                scene=require_string(variant, "scene").format(age=age),
                style=require_string(variant, "style").format(age=age),
            ).strip()
        )
    return [validate_prompt(prompt) for prompt in prompts]


def build_prompts(config_path: Path, now: datetime) -> list[str]:
    data = load_prompt_config(config_path)
    birthday = birthday_config(data)
    if birthday and is_birthday_run(now, birthday):
        return build_birthday_prompts(now, birthday)
    return [build_prompt(data)]


def build_classic_plans(config_path: Path, now: datetime) -> list[GenerationPlan]:
    return [GenerationPlan(prompt=prompt, kind=OPERANDI_CLASSIC) for prompt in build_prompts(config_path, now)]


def _extract_text_response(response: object) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()
    chunks: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if isinstance(text, str) and text.strip():
                chunks.append(text.strip())
    if chunks:
        return "\n\n".join(chunks).strip()
    raise RuntimeError("OpenAI text response did not include text output")


def load_recent_story_entries(story_document_path: Path, *, limit: int = STORY_HISTORY_COUNT) -> list[str]:
    if not story_document_path.exists():
        return []
    if story_document_path.is_symlink() or not story_document_path.is_file():
        raise ValueError(f"Story document must be a regular non-symlink file: {story_document_path}")
    try:
        text = story_document_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"story document is not valid UTF-8: {story_document_path}") from exc
    entries = re.split(r"(?m)^##\s+", text)
    cleaned = []
    for entry in entries[1:]:
        stripped = entry.strip()
        if stripped:
            cleaned.append("## " + stripped)
    return cleaned[-limit:]


def build_story_generation_config(config_path: Path, *, include_fixed_sections: bool = True) -> str:
    data = load_prompt_config(config_path)
    if not is_markdown_prompt_config(data):
        return build_prompt(data)
    main = require_string(data, "main" if include_fixed_sections else "main_text")
    selected, _format_values = _select_markdown_sections(data.get("sections"), label="Story prompt config")
    return f"{main}\n\n" + _format_selected_markdown_sections(selected, heading_level=3)


def build_story_generation_configs(config_path: Path) -> tuple[str, str]:
    data = load_prompt_config(config_path)
    if not is_markdown_prompt_config(data):
        prompt = build_prompt(data)
        return prompt, prompt
    selected, _format_values = _select_markdown_sections(data.get("sections"), label="Story prompt config")
    text_main = require_string(data, "main_text")
    image_main = require_string(data, "main")
    selected_block = _format_selected_markdown_sections(selected, heading_level=3)
    return f"{text_main}\n\n{selected_block}", f"{image_main}\n\n{selected_block}"


def initial_story_direction_block(recent_entries: list[str]) -> str:
    if recent_entries:
        return ""
    direction = random.choice(INITIAL_STORY_DIRECTIONS)
    return (
        "\nEinmalige Initialrichtung fuer den ersten Teil:\n"
        f"{direction}\n"
        "Nutze diese Richtung als inneren Kompass fuer einen starken Auftakt. "
        "Gib sie nicht als Plan, Zusammenfassung oder Meta-Kommentar aus. "
        "Speichere sie nicht in der Geschichte; nach diesem ersten Teil soll die Fortsetzung wieder dynamisch aus Historie und neuen Zufallsregeln entstehen.\n"
    )


def build_story_text_prompt(story_config: str, recent_entries: list[str], closing_instruction: str = "") -> str:
    history = "\n\n".join(recent_entries) if recent_entries else "Noch keine vergangenen Teile vorhanden."
    closing_block = f"\nAbschlusssteuerung:\n{closing_instruction}\n" if closing_instruction else ""
    initial_direction_block = initial_story_direction_block(recent_entries)
    entry_target = STORY_ENTRY_TARGET if recent_entries else STORY_FIRST_ENTRY_TARGET
    return (
        "Schreibe den naechsten Teil einer endlos fortlaufenden Geschichte im aktuellen Generierungstakt.\n"
        "Hauptfiguren sind zwei Hauskatzen, eine Moehre und eine Maus. Jede Folge deckt genau eine Stunde Handlung ab.\n"
        f"Der neue Eintrag soll {entry_target} fuellen, auf Deutsch sein und als Markdown ohne H1 beginnen.\n"
        "Schreibe als lebendige Prosa mit Tempo, Witz, Waerme und konkreten Bildern; kein Drehbuch, keine Szenenanweisungen, keine Dialogliste.\n"
        "Wenn gezogene Regeln oder Einstellungen nicht direkt zusammenpassen, deute sie sinnvoll um und mache diese Reibung zum Teil des Zufalls.\n"
        "Gib keine promptartigen Regel- oder Kategorienamen als Geruest aus. Keine Aufzaehlungen wie Ort, Epoche, Subjekt, Handlung, Licht oder Perspektive, weder am Anfang noch spaeter im Text. Wenn solche Woerter auftauchen, dann nur als bewusst komisches In-World-Material, etwa Formularsprache, Schild, amtliche Kategorie oder trockener Figurenwitz. Verwandle alle Regeln in erzaehlte Szene; wenn es nicht passt, ueberdenke die Umsetzung statt das Geruest sichtbar zu machen.\n"
        "Orientiere dich an den letzten Eintraegen, ohne sie zu wiederholen. Wenn keine Historie existiert, beginne natuerlich.\n\n"
        "Regeln fuer diesen Teil:\n"
        f"{story_config}\n"
        f"{initial_direction_block}"
        f"{closing_block}\n"
        f"Letzte {STORY_HISTORY_COUNT} Eintraege:\n"
        f"{history}\n"
    )


def generate_story_part(
    client: OpenAI,
    *,
    model: str,
    story_config: str,
    recent_entries: list[str],
    closing_instruction: str = "",
) -> str:
    response = client.responses.create(
        model=model,
        input=build_story_text_prompt(story_config, recent_entries, closing_instruction),
    )
    story = _extract_text_response(response)
    if len(story) < 500:
        raise ValueError("Generated story part is unexpectedly short")
    return story.strip()


def story_document_has_title(text: str) -> bool:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        return stripped.startswith("# ") and not stripped.startswith("## ")
    return False


def clean_story_title(value: str) -> str:
    title = value.strip()
    title = re.sub(r"^#+\s*", "", title)
    title = title.strip(" \t\r\n\"'“”„`")
    title = re.sub(r"\s+", " ", title)
    if not title:
        raise ValueError("Generated story title is empty")
    if len(title) > 120:
        title = title[:120].rstrip()
    return title


def generate_story_title(client: OpenAI, *, model: str, story_document: str) -> str:
    excerpt = story_document[-12000:] if len(story_document) > 12000 else story_document
    response = client.responses.create(
        model=model,
        input=(
            "Denk dir einen kurzen, literarischen deutschen Titel fuer diese abgeschlossene "
            "Wirtelprimpf-Geschichte aus. Gib nur den Titel aus, ohne Markdown, ohne Anfuehrungszeichen, "
            "ohne Erklaerung. Der Titel soll neugierig machen und zur fertigen Geschichte passen.\n\n"
            f"Geschichte:\n{excerpt}"
        ),
    )
    return clean_story_title(_extract_text_response(response))


def add_story_title_if_missing(client: OpenAI, *, model: str, story_document: str) -> str:
    if story_document_has_title(story_document):
        return story_document
    title = generate_story_title(client, model=model, story_document=story_document)
    return f"# {title}\n\n{story_document.lstrip()}"


def build_story_image_prompt(story_part: str, story_config: str) -> str:
    prompt = (
        "Generiere ein Bild zu diesem Teil der fortlaufenden Wirtelprimpf-Geschichte.\n"
        "Nutze dieselben Regeln wie fuer den Textteil, aber formuliere das Ergebnis als sichtbare Bildszene.\n"
        "Kein langer lesbarer Text im Bild, keine Wasserzeichen.\n\n"
        "Regeln:\n"
        f"{story_config}\n\n"
        "Geschichtsteil:\n"
        f"{story_part}"
    )
    if len(prompt) > 6000:
        prompt = prompt[:5900].rstrip() + "\n\n[Geschichtsteil fuer Bildprompt gekuerzt.]"
    return validate_prompt(prompt)


def build_story_plans(config: Config, now: datetime, client: OpenAI | None, *, dry_run: bool) -> list[GenerationPlan]:
    story_config, story_image_config = build_story_generation_configs(config.story_prompt_config_path)
    story_state, story_document_path, closing_instruction = prepare_story_state_for_plan(config, dry_run=dry_run)
    recent_entries = load_recent_story_entries(story_document_path)
    if dry_run:
        story_part = (
            "DRY-RUN: Hier wuerde der naechste Teil der fortlaufenden Geschichte stehen. "
            "Der echte Lauf nutzt die letzten Eintraege und die zufaellig gezogenen Regeln aus der zweiten Markdown-Konfig."
        )
        if closing_instruction:
            story_part = f"{story_part}\n\n{closing_instruction}"
    else:
        if client is None:
            raise RuntimeError("OpenAI client is required for story generation")
        story_part = generate_story_part(
            client,
            model=config.story_model,
            story_config=story_config,
            recent_entries=recent_entries,
            closing_instruction=closing_instruction,
        )
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    story_entry = f"## {timestamp}\n\n{story_part.strip()}\n"
    title_after_success = story_state.closing_remaining == 1
    return [
        GenerationPlan(
            prompt=build_story_image_prompt(story_part, story_image_config),
            kind=OPERANDI_STORY,
            story_part=story_part,
            story_entry_markdown=story_entry,
            story_document_append="\n" + story_entry,
            story_document_path=story_document_path,
            story_state_after_success=story_state_after_success(story_state),
            story_title_after_success=title_after_success,
        )
    ]


def build_generation_plans(config: Config, now: datetime, client: OpenAI | None, *, dry_run: bool) -> list[GenerationPlan]:
    plans: list[GenerationPlan] = []
    if operandi_includes(config, OPERANDI_CLASSIC):
        plans.extend(build_classic_plans(config.prompt_config_path, now))
    if operandi_includes(config, OPERANDI_STORY):
        plans.extend(build_story_plans(config, now, client, dry_run=dry_run))
    if not plans:
        raise ValueError(f"No generation plans for operandi={config.operandi!r}")
    return plans


def is_retryable_generation_error(exc: Exception) -> bool:
    if isinstance(exc, (TimeoutError, OSError)):
        return True

    message = str(exc).lower()
    return (
        "timeout" in message
        or "rate limit" in message
        or "temporarily" in message
        or "connection" in message
        or "429" in message
    )


def generate_image_with_retries(client: OpenAI, request: dict[str, object]) -> str:
    last_error: Exception | None = None
    flex_fallback_used = False
    for attempt in range(1, GENERATION_RETRIES + 1):
        try:
            response = client.images.generate(**request)
            image_record = response.data[0]
            image_b64 = image_record.b64_json
            if image_b64 is None:
                raise RuntimeError("OpenAI response did not include base64 image data")
            return image_b64
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if not flex_fallback_used and request_uses_flex_service_tier(request) and is_service_tier_unsupported_error(exc):
                print("Flex service_tier was not accepted for this image request; retrying without Flex.", file=sys.stderr)
                request = request_without_service_tier(request)
                flex_fallback_used = True
                continue
            if not is_retryable_generation_error(exc) or attempt == GENERATION_RETRIES:
                break
            delay = GENERATION_RETRY_BASE_SECONDS * attempt
            time.sleep(delay)
    assert last_error is not None
    raise last_error


def request_uses_flex_service_tier(request: dict[str, object]) -> bool:
    extra_body = request.get("extra_body")
    return isinstance(extra_body, dict) and extra_body.get("service_tier") == "flex"


def request_without_service_tier(request: dict[str, object]) -> dict[str, object]:
    cleaned = dict(request)
    extra_body = cleaned.get("extra_body")
    if isinstance(extra_body, dict):
        cleaned_extra_body = dict(extra_body)
        cleaned_extra_body.pop("service_tier", None)
        if cleaned_extra_body:
            cleaned["extra_body"] = cleaned_extra_body
        else:
            cleaned.pop("extra_body", None)
    return cleaned


def is_service_tier_unsupported_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "service_tier" in message and (
        "unknown parameter" in message
        or "unsupported" in message
        or "not supported" in message
        or "invalid_request_error" in message
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Wirtelprimpf images.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    parser.add_argument("--check-config", action="store_true", help="Validate config and prompt config, no API call.")
    parser.add_argument(
        "--status",
        action="store_true",
        help="Emit machine-readable runtime status and configuration checks without making API calls.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate prompts and print them, but do not call OpenAI API or publish to git.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable status output.")
    return parser.parse_args()


def emit_summary(
    summary: RunSummary,
    args: argparse.Namespace,
    *,
    compact: bool = True,
    mode: str = MODE_RUN,
    details: dict[str, object] | None = None,
) -> None:
    if args.json:
        ok = summary.exit_code == 0
        version = VERSION
        if isinstance(details, dict) and isinstance(details.get("version"), str):
            version = details["version"]
        payload = build_status_envelope(
            ok=ok,
            version=version,
            mode=mode,
            status=STATUS_OK if ok else STATUS_ERROR,
            exit_code=summary.exit_code,
            details=details,
            summary={
                "success": summary.success,
                "failed": summary.failed,
                "skipped": summary.skipped,
                "prompts": summary.prompts,
                "total": summary.total,
            },
        )
        print(format_json(payload, compact=compact))


def emit_status(payload: dict[str, object], *, as_json: bool) -> int:
    if as_json:
        status = bool(payload.get("ok"))
        base = dict(payload)
        base.setdefault("ok", status)
        base.setdefault("version", VERSION)
        base.setdefault("timestamp", build_status_timestamp())
        base.setdefault("status", STATUS_OK if status else STATUS_ERROR)
        base.setdefault("exit_code", 0 if status else 1)
        base["mode"] = validate_mode(str(base.get("mode", MODE_STATUS)))
        payload = build_status_envelope(
            ok=bool(base["ok"]),
            status=str(base["status"]),
            mode=str(base["mode"]),
            exit_code=int(base["exit_code"]),
            version=str(base["version"]),
            checks=list(base.get("checks")) if isinstance(base.get("checks"), list) else None,
            details=base.get("details") if isinstance(base.get("details"), dict) else None,
            message=base.get("message") if isinstance(base.get("message"), str) else None,
        )
        print(format_json(payload, compact=True))
        return 0 if status else 1

    print(f"wirtelprimpf_generator.py status: {payload.get('status', STATUS_ERROR)}")
    print(f"mode: {payload.get('mode', MODE_STATUS)}")
    print(f"version: {payload.get('version', VERSION)}")
    print(f"timestamp: {payload.get('timestamp', build_status_timestamp())}")
    print(f"exit_code: {payload.get('exit_code', 0)}")
    for key, value in payload.items():
        if key in {"ok", "status", "version", "timestamp", "exit_code"}:
            continue
        print(f"{key}: {value}")
    return 0 if bool(payload.get("ok")) else 1


def status_report(config: Config | None = None) -> dict[str, object]:
    timestamp = build_status_timestamp()
    report = {
        "ok": True,
        "version": VERSION,
        "timestamp": timestamp,
        "mode": MODE_STATUS,
        "status": STATUS_OK,
        "exit_code": 0,
        "checks": [],
        "details": {
            "git_available": bool(_resolve_secure_executable_cached("git", required=False)),
            "gh_available": bool(_resolve_secure_executable_cached("gh", required=False)),
            "openai_key_present": bool(env("OPENAI_API_KEY")),
        },
    }
    checks = report["checks"]

    if config is None:
        checks.append({"name": "load_config", "ok": False, "message": "Configuration loading failed"})
        return report

    report["details"].update(
        {
            "operandi": config.operandi,
            "working_dir": str(config.working_dir),
            "semver_base": VERSION,
            "publish_push_interval_patches": PUBLISH_PUSH_INTERVAL_PATCHES,
            "publish_release_push_interval": PUBLISH_RELEASE_PUSH_INTERVAL,
        }
    )

    prompt_config_paths = [config.prompt_config_path]
    if operandi_includes(config, OPERANDI_STORY):
        prompt_config_paths.append(config.story_prompt_config_path)

    for prompt_config in prompt_config_paths:
        checks.append({"name": "prompt_config_file", "ok": prompt_config.exists(), "path": str(prompt_config)})
        if not prompt_config.exists():
            report["ok"] = False
            report["status"] = STATUS_ERROR
            report["exit_code"] = 1
            checks.append({"name": "prompt_config_parse", "ok": False, "message": "Prompt config file missing"})
            return report

    try:
        plans = build_generation_plans(config, datetime.now(), None, dry_run=True)
    except Exception as exc:
        report["ok"] = False
        report["status"] = STATUS_ERROR
        report["exit_code"] = 1
        checks.append({"name": "prompt_config_parse", "ok": False, "message": str(exc)})
    else:
        checks.append(
            {
                "name": "prompt_config_parse",
                "ok": True,
                "prompt_count": len(plans),
            }
        )
        local_outdir_exists = config.local_outdir.exists()
        if local_outdir_exists:
            is_dir = config.local_outdir.is_dir()
            writable = os.access(config.local_outdir, os.W_OK | os.X_OK) if is_dir else False
            checks.append(
                {
                    "name": "local_outdir",
                    "ok": is_dir and writable,
                    "path": str(config.local_outdir),
                    "is_dir": is_dir,
                    "writable": writable,
                }
            )
            if not (is_dir and writable):
                report["ok"] = False
                report["status"] = STATUS_ERROR
                report["exit_code"] = 1
        else:
            parent = config.local_outdir.parent
            parent_is_dir = parent.is_dir()
            parent_writable = parent_is_dir and os.access(parent, os.W_OK | os.X_OK)
            checks.append(
                {
                    "name": "local_outdir",
                    "ok": parent_is_dir and parent_writable,
                    "path": str(config.local_outdir),
                    "parent": str(parent),
                    "parent_is_dir": parent_is_dir,
                    "writable": parent_writable,
                }
            )
            if not parent_is_dir or not parent_writable:
                report["ok"] = False
                report["status"] = STATUS_ERROR
                report["exit_code"] = 1

        working_dir_exists = config.working_dir.exists()
        if working_dir_exists:
            working_is_dir = config.working_dir.is_dir()
            working_writable = os.access(config.working_dir, os.W_OK | os.X_OK) if working_is_dir else False
            checks.append(
                {
                    "name": "working_dir",
                    "ok": working_is_dir and working_writable,
                    "path": str(config.working_dir),
                    "is_dir": working_is_dir,
                    "writable": working_writable,
                }
            )
            if not (working_is_dir and working_writable):
                report["ok"] = False
                report["status"] = STATUS_ERROR
                report["exit_code"] = 1
        else:
            working_parent = config.working_dir.parent
            working_parent_is_dir = working_parent.is_dir()
            working_parent_writable = working_parent_is_dir and os.access(working_parent, os.W_OK | os.X_OK)
            local_outdir_creatable = (
                working_parent == config.local_outdir
                and (
                    (config.local_outdir.is_dir() and os.access(config.local_outdir, os.W_OK | os.X_OK))
                    or (
                        config.local_outdir.parent.is_dir()
                        and os.access(config.local_outdir.parent, os.W_OK | os.X_OK)
                    )
                )
            )
            working_parent_ok = working_parent_writable or local_outdir_creatable
            checks.append(
                {
                    "name": "working_dir",
                    "ok": working_parent_ok,
                    "path": str(config.working_dir),
                    "parent": str(working_parent),
                    "parent_is_dir": working_parent_is_dir,
                    "writable": working_parent_writable,
                    "parent_creatable_via_local_outdir": local_outdir_creatable,
                }
            )
            if not working_parent_ok:
                report["ok"] = False
                report["status"] = STATUS_ERROR
                report["exit_code"] = 1

    if config.repo_path is None:
        checks.append({"name": "repo", "ok": True, "enabled": False})
    else:
        repo_checks = {"name": "repo", "ok": True, "path": str(config.repo_path), "slug": config.repo_slug}
        if config.repo_path.is_symlink():
            repo_checks["ok"] = False
            repo_checks["message"] = "Configured repo path must not be a symlink"
            report["ok"] = False
            report["status"] = STATUS_ERROR
            report["exit_code"] = 1
        if config.repo_path.exists():
            if not (config.repo_path / ".git").is_dir():
                repo_checks["ok"] = False
                repo_checks["message"] = "Configured repo path is not a git repository"
                report["ok"] = False
                report["status"] = STATUS_ERROR
                report["exit_code"] = 1
        elif not config.repo_slug:
            repo_checks["ok"] = False
            repo_checks["message"] = "Repo path does not exist and WIRTELPRIMPF_REPO_SLUG is not configured"
            report["ok"] = False
            report["status"] = STATUS_ERROR
            report["exit_code"] = 1
        elif not _resolve_secure_executable_cached("gh", required=False):
            repo_checks["ok"] = False
            repo_checks["message"] = "gh CLI is required to auto-clone missing repo path"
            report["ok"] = False
            report["status"] = STATUS_ERROR
            report["exit_code"] = 1
        checks.append(repo_checks)
    if config.repo_path is not None and repo_checks.get("ok", True):
        try:
            publish_state = read_publish_state(publish_state_path(config.repo_path))
            major_version, minor_version, patch_version = _derive_version_numbers(
                publish_state.patch_count,
                semver_base_patch_count=publish_state.semver_base_patch_count,
            )
        except Exception as exc:
            report["ok"] = False
            report["status"] = STATUS_ERROR
            report["exit_code"] = 1
            checks.append({"name": "publish_state", "ok": False, "message": str(exc)})
            report["checks"] = checks
        else:
            details = dict(report["details"])
            details.update(
                {
                    "major_version": major_version,
                    "minor_version": minor_version,
                    "patch_count": publish_state.patch_count,
                    "patch_version": patch_version,
                    "publish_push_count": publish_state.publish_push_count,
                    "semver_base": publish_state.semver_base,
                    "semver_base_patch_count": publish_state.semver_base_patch_count,
                    "semver_patch_offset": publish_state.patch_count - publish_state.semver_base_patch_count,
                }
            )
            report["version"] = f"{major_version}.{minor_version}.{patch_version}{VERSION_SUFFIX}"
            report["details"] = details

    checks.append(
        {
            "name": "openai_key",
            "ok": bool(env("OPENAI_API_KEY")),
            "required": False,
        }
    )

    return report


def publish_state_summary(config: Config) -> dict[str, object] | None:
    if config.repo_path is None:
        return None
    try:
        publish_state = read_publish_state(publish_state_path(config.repo_path))
    except Exception as exc:  # pragma: no cover - defensive path
        return {"publish_state_error": f"Failed to read publish state: {exc}"}

    major_version, minor_version, patch_version = _derive_version_numbers(
        publish_state.patch_count,
        semver_base_patch_count=publish_state.semver_base_patch_count,
    )
    patches_into_publish_window = publish_state.patch_count % PUBLISH_PUSH_INTERVAL_PATCHES
    patches_until_publish = (
        PUBLISH_PUSH_INTERVAL_PATCHES
        if patches_into_publish_window == 0
        else PUBLISH_PUSH_INTERVAL_PATCHES - patches_into_publish_window
    )
    publish_pushes_into_release_window = publish_state.publish_push_count % PUBLISH_RELEASE_PUSH_INTERVAL
    publish_pushes_until_release = (
        PUBLISH_RELEASE_PUSH_INTERVAL
        if publish_pushes_into_release_window == 0
        else PUBLISH_RELEASE_PUSH_INTERVAL - publish_pushes_into_release_window
    )
    release_ready = (
        publish_state.publish_push_count > 0 and publish_pushes_into_release_window == 0
    )
    return {
        "patch_version": patch_version,
        "minor_version": minor_version,
        "major_version": major_version,
        "patch_count": publish_state.patch_count,
        "version": f"{major_version}.{minor_version}.{patch_version}{VERSION_SUFFIX}",
        "publish_push_count": publish_state.publish_push_count,
        "semver_base": publish_state.semver_base,
        "semver_base_patch_count": publish_state.semver_base_patch_count,
        "semver_patch_offset": publish_state.patch_count - publish_state.semver_base_patch_count,
        "publish_push_interval_patches": PUBLISH_PUSH_INTERVAL_PATCHES,
        "publish_release_push_interval": PUBLISH_RELEASE_PUSH_INTERVAL,
        "patches_until_next_publish": patches_until_publish,
        "publish_pushes_until_release": publish_pushes_until_release,
        "release_ready": release_ready,
    }


def _die(message: str, *, exit_code: int = 1) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(exit_code)


def emit_unexpected_failure(message: str, args: argparse.Namespace, runtime_mode: str) -> None:
    if args.json:
        payload = build_status_envelope(
            ok=False,
            mode=runtime_mode,
            status=STATUS_ERROR,
            exit_code=1,
            message=message,
        )
        print(format_json(payload, compact=True))
        raise SystemExit(1)
    _die(message)


def main() -> None:
    args = parse_args()
    runtime_mode = MODE_RUN
    if args.check_config:
        runtime_mode = MODE_CHECK_CONFIG
    elif args.dry_run:
        runtime_mode = MODE_DRY_RUN

    if args.status:
        try:
            cfg = load_config()
        except Exception as exc:
            payload = status_report(None)
            payload["checks"].append({"name": "load_config", "ok": False, "message": str(exc)})
            _code = emit_status(payload, as_json=args.json)
        else:
            payload = status_report(cfg)
            if args.json:
                payload = dict(payload)
                if not payload.get("ok"):
                    payload["message"] = payload.get("message", "status report validation failed")
            _code = emit_status(payload, as_json=args.json)
        raise SystemExit(_code)

    if not args.json:
        emit_mode_line(runtime_mode)

    try:
        if not os.environ.get("OPENAI_API_KEY") and not args.check_config and not args.dry_run:
            if args.json:
                emit_unexpected_failure("OPENAI_API_KEY environment variable is required", args, runtime_mode)
            _die("OPENAI_API_KEY environment variable is required")

        config = load_config()
        if not config.prompt_config_path.exists():
            if args.json:
                emit_unexpected_failure(
                    f"Prompt config file not found: {config.prompt_config_path}",
                    args,
                    runtime_mode,
                )
            _die(f"Prompt config file not found: {config.prompt_config_path}")
        if operandi_includes(config, OPERANDI_STORY) and not config.story_prompt_config_path.exists():
            if args.json:
                emit_unexpected_failure(
                    f"Story prompt config file not found: {config.story_prompt_config_path}",
                    args,
                    runtime_mode,
                )
            _die(f"Story prompt config file not found: {config.story_prompt_config_path}")

        try:
            plans = build_generation_plans(config, datetime.now(), None, dry_run=True)
        except Exception as exc:
            runtime_version = resolve_runtime_version(
                patch_count=(
                    read_publish_state(publish_state_path(config.repo_path)).patch_count
                    if config.repo_path
                    else 0
                ),
            )
            if args.check_config and args.json:
                print(
                    format_json(
                        build_status_envelope(
                            ok=False,
                            mode=MODE_CHECK_CONFIG,
                            status=STATUS_ERROR,
                            exit_code=1,
                            version=runtime_version,
                            check_config=True,
                            message=f"Prompt config validation failed: {exc}",
                        ),
                        compact=True,
                    )
                )
                raise SystemExit(1)
            if args.json:
                emit_unexpected_failure(
                    f"Prompt config validation failed: {exc}",
                    args,
                    runtime_mode,
                )
            _die(f"Prompt config validation failed: {exc}")

        total_prompts = len(plans)

        if args.check_config:
            check_config_details = publish_state_summary(config)
            current_version = (
                check_config_details.get("version") if isinstance(check_config_details, dict) else None
            )
            publish_state_error = (
                isinstance(check_config_details, dict)
                and isinstance(check_config_details.get("publish_state_error"), str)
            )
            if publish_state_error:
                error_message = check_config_details["publish_state_error"]
                if args.json:
                    print(
                        format_json(
                            build_status_envelope(
                                ok=False,
                                mode=MODE_CHECK_CONFIG,
                                status=STATUS_ERROR,
                                exit_code=1,
                                version=current_version or VERSION,
                                check_config=True,
                                message=error_message,
                                details=check_config_details,
                            ),
                            compact=True,
                        )
                    )
                    raise SystemExit(1)
                _die(f"Invalid publish state: {error_message}")

            if not isinstance(current_version, str):
                current_version = resolve_runtime_version(
                    patch_count=0,
                )
            if args.json:
                print(
                    format_json(
                        build_status_envelope(
                            ok=True,
                            mode=MODE_CHECK_CONFIG,
                            status=STATUS_OK,
                            exit_code=0,
                            version=current_version,
                            check_config=True,
                            details=check_config_details,
                            local_outdir=str(config.local_outdir),
                            prompt_count=len(plans),
                            model=config.image_model,
                            image_size=config.image_size,
                            output_resolution=config.output_resolution,
                            repo_path=str(config.repo_path) if config.repo_path else None,
                        ),
                        compact=True,
                    )
                )
                return
            print("Prompt configuration is valid.")
            print(f"Resolved config: local_outdir={config.local_outdir}")
            print(f"working_dir={config.working_dir}")
            print(f"model={config.image_model} size={config.image_size} output_resolution={config.output_resolution}")
            print(f"operandi={config.operandi}")
            print(f"repo_path={config.repo_path or '<disabled>'}")
            print(f"prompts={total_prompts}")
            print(f"exit_code: 0")
            return

        ensure_output_directory(config.local_outdir)
        config.local_outdir.mkdir(parents=True, exist_ok=True)
        ensure_private_output_directory(config.working_dir, env_name="WIRTELPRIMPF_WORKING_DIR")
        try:
            repo_outdir = ensure_repo(config)
        except Exception as exc:
            if args.json:
                emit_unexpected_failure(f"Failed to prepare repository: {exc}", args, runtime_mode)
            _die(f"Failed to prepare repository: {exc}")
        summary = RunSummary(total=len(plans))
        output_resolution_size = parse_resolution(config.output_resolution)

        if args.dry_run:
            fallback_version = resolve_runtime_version(
                patch_count=0,
            )
            dry_run_details = publish_state_summary(config)
            if (
                isinstance(dry_run_details, dict)
                and isinstance(dry_run_details.get("publish_state_error"), str)
            ):
                error_message = dry_run_details["publish_state_error"]
                if args.json:
                    print(
                        format_json(
                            build_status_envelope(
                                ok=False,
                                mode=MODE_DRY_RUN,
                                status=STATUS_ERROR,
                                exit_code=1,
                                version=fallback_version,
                                details=dry_run_details,
                                message=f"Invalid publish state: {error_message}",
                            ),
                            compact=True,
                        )
                    )
                    raise SystemExit(1)
                _die(f"Invalid publish state: {error_message}")
            current_version = (
                dry_run_details.get("version") if isinstance(dry_run_details, dict) else None
            )
            if current_version is None:
                current_version = fallback_version

            for index, plan in enumerate(plans, start=1):
                if args.json:
                    print(
                        format_json(
                            build_status_envelope(
                                ok=True,
                                mode=MODE_DRY_RUN,
                                status=STATUS_OK,
                                exit_code=0,
                                version=current_version or fallback_version,
                                details=dry_run_details,
                                type="dry_run",
                                index=index,
                                total=total_prompts,
                                prompt_preview=plan.prompt[:140],
                            ),
                            compact=True,
                        )
                    )
                else:
                    print(f"[DRY-RUN {index}/{total_prompts}] {plan.prompt[:140]}...")
                    if plan.story_entry_markdown:
                        print(plan.story_entry_markdown[:220] + "...")
                summary.skipped += 1
                summary.prompts += 1
            summary.exit_code = 0
            emit_summary(summary, args, compact=True, mode=MODE_DRY_RUN, details=dry_run_details)
            return

        client = OpenAI()
        if operandi_includes(config, OPERANDI_STORY):
            plans = build_generation_plans(config, datetime.now(), client, dry_run=False)
            total_prompts = len(plans)
            summary.total = len(plans)

        per_kind_counts: dict[str, int] = {}
        for index, plan in enumerate(plans, start=1):
            timestamp = build_timestamp()
            per_kind_counts[plan.kind] = per_kind_counts.get(plan.kind, 0) + 1
            kind_index = per_kind_counts[plan.kind]
            suffix = f"_{plan.kind}-{kind_index:02d}" if len(plans) > 1 else ""
            stem = f"wirtelprimpf_{timestamp}{suffix}"
            local_png = config.local_outdir / f"{stem}.png"
            local_prompt = config.local_outdir / f"{stem}.txt"
            local_story = config.local_outdir / f"{stem}.md" if plan.story_entry_markdown else None

            request: dict[str, object] = {
                "model": config.image_model,
                "prompt": plan.prompt,
                "size": config.image_size,
            }
            if config.flex_processing_mode:
                request["extra_body"] = {"service_tier": config.flex_processing_mode}

            try:
                image_b64 = generate_image_with_retries(client, request)
            except Exception as exc:
                print(f"Generation failed for {stem}: {exc}", file=sys.stderr)
                summary.failed += 1
                summary.prompts += 1
                summary.exit_code = 2
                continue

            if image_b64 is None:
                print(f"Generation failed for {stem}: no base64 image data", file=sys.stderr)
                summary.failed += 1
                summary.prompts += 1
                summary.exit_code = 2
                continue

            try:
                write_bytes_atomically(local_png, decode_image_bytes(image_b64))
                resize_cover(local_png, output_resolution_size)
                write_text_atomically(local_prompt, plan.prompt)
                if local_story is not None and plan.story_entry_markdown is not None:
                    write_text_atomically(local_story, plan.story_entry_markdown)
                if plan.story_document_append:
                    story_document_path = plan.story_document_path or config.story_document_path
                    existing_story_document = ""
                    if story_document_path.exists():
                        if story_document_path.is_symlink() or not story_document_path.is_file():
                            raise RuntimeError(f"Story document must be a regular non-symlink file: {story_document_path}")
                        existing_story_document = story_document_path.read_text(encoding="utf-8")
                    elif not story_document_path.parent.exists():
                        story_document_path.parent.mkdir(parents=True, exist_ok=True)
                    updated_story_document = existing_story_document.rstrip() + "\n" + plan.story_document_append.lstrip()
                    if plan.story_title_after_success:
                        updated_story_document = add_story_title_if_missing(
                            client,
                            model=config.story_model,
                            story_document=updated_story_document,
                        )
                    write_text_atomically(story_document_path, updated_story_document)
                    if plan.story_state_after_success is not None:
                        write_story_state(config.story_state_path, plan.story_state_after_success)
                rotate_working_outputs(
                    config,
                    local_png,
                    local_prompt,
                    local_story,
                    plan.story_document_path if plan.story_document_append else None,
                )
            except Exception as exc:
                print(f"Write/transform failed for {stem}: {exc}", file=sys.stderr)
                summary.failed += 1
                summary.prompts += 1
                summary.exit_code = 2
                continue
            summary.success += 1
            summary.prompts += 1
            print(f"Local image: {local_png}")
            print(f"Local prompt: {local_prompt}")
            if local_story is not None:
                print(f"Local story: {local_story}")
            if plan.story_document_append:
                print(f"Story document: {plan.story_document_path or config.story_document_path}")
            print(f"Working directory: {config.working_dir}")

            if repo_outdir is None:
                continue

            repo_png = repo_outdir / local_png.name
            repo_prompt = repo_outdir / local_prompt.name
            repo_paths = [repo_png, repo_prompt]
            try:
                shutil.copy2(local_png, repo_png)
                shutil.copy2(local_prompt, repo_prompt)
                if local_story is not None:
                    repo_story = repo_outdir / local_story.name
                    shutil.copy2(local_story, repo_story)
                    repo_paths.append(repo_story)
                if plan.story_document_append:
                    story_document_path = plan.story_document_path or config.story_document_path
                    repo_story_document = repo_outdir / story_document_path.name
                    shutil.copy2(story_document_path, repo_story_document)
                    repo_paths.append(repo_story_document)
                repo_paths.extend(
                    sync_repo_working_outputs(
                        repo_outdir,
                        local_png,
                        local_prompt,
                        local_story,
                        plan.story_document_path if plan.story_document_append else active_story_document_path(config),
                    )
                )
                commit_and_push(config, repo_paths, stem)
                print(f"Repository image: {repo_png}")
                print(f"Repository prompt: {repo_prompt}")
            except Exception as exc:
                print(f"Repository publish failed for {stem}: {exc}", file=sys.stderr)
                summary.failed += 1
                summary.exit_code = 2
                continue

        publish_details = publish_state_summary(config)
        if (
            isinstance(publish_details, dict)
            and isinstance(publish_details.get("publish_state_error"), str)
            and summary.exit_code == 0
        ):
            summary.exit_code = 1
        if summary.exit_code:
            if args.json:
                emit_summary(summary, args, compact=True, mode=MODE_RUN, details=publish_details)
                raise SystemExit(summary.exit_code)
            if not args.json:
                print(f"Completed with {summary.failed} failure(s)", file=sys.stderr)
            emit_summary(summary, args, compact=True, mode=MODE_RUN, details=publish_details)
            _die(f"Completed with {summary.failed} failure(s)", exit_code=summary.exit_code)

        emit_summary(summary, args, mode=MODE_RUN, details=publish_details)
        return

    except Exception as exc:
        emit_unexpected_failure(f"Unhandled failure in mode {runtime_mode}: {exc}", args, runtime_mode)


if __name__ == "__main__":
    main()
