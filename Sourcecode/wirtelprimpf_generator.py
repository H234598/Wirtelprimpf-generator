#!/usr/bin/env python3
"""Generate Wirtelprimpf-style cat images and optionally publish them to Git."""

from __future__ import annotations

import base64
import binascii
import argparse
import json
import os
import random
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

from openai import OpenAI
from PIL import Image

FLEX_PROCESSING_DEFAULT: str = "high"
FLEX_PROCESSING_MODES = frozenset({FLEX_PROCESSING_DEFAULT, "low"})
FLEX_PROCESSING_ENABLED_VALUES = {"1", "true", "yes", "on", "enabled", "enable"}
FLEX_PROCESSING_DISABLED_VALUES = {"0", "false", "no", "off", "disabled", "disable"}
IMAGE_SIZE_PATTERN: Final = r"^\d+x\d+$"
RESOLUTION_MAX_DIM: Final = 8192
IMAGE_PAYLOAD_MAX_BYTES: Final = 80 * 1024 * 1024
GIT_TIMEOUT_SECONDS: Final = 120
GENERATION_RETRIES: Final = 3
GENERATION_RETRY_BASE_SECONDS: Final = 2
VERSION: Final = "0.5.6-hardening"
STATUS_OK: Final = "ok"
STATUS_ERROR: Final = "error"


@dataclass
class RunSummary:
    success: int = 0
    failed: int = 0
    skipped: int = 0
    prompts: int = 0
    total: int = 0
    exit_code: int = 0


def format_json(value: object, *, indent: int = 2) -> str:
    return json.dumps(value, indent=indent, ensure_ascii=False)


def env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value


@dataclass(frozen=True)
class Config:
    local_outdir: Path
    repo_path: Path | None
    repo_slug: str | None
    repo_subdir: str
    repo_branch: str
    image_model: str
    image_size: str
    output_resolution: str
    flex_processing_mode: str | None
    prompt_config_path: Path
    commit_author_name: str
    commit_author_email: str


def load_config() -> Config:
    default_outdir = Path.home() / "Pictures" / "Wirtelprimpf"
    config_home = Path(env("XDG_CONFIG_HOME", str(Path.home() / ".config")) or str(Path.home() / ".config"))
    default_prompt_config = config_home / "wirtelprimpf" / "prompt_config.json"
    repo_path = env("WIRTELPRIMPF_REPO_PATH")

    return Config(
        local_outdir=Path(env("WIRTELPRIMPF_LOCAL_OUTDIR", str(default_outdir))).expanduser(),
        repo_path=Path(repo_path).expanduser() if repo_path else None,
        repo_slug=env("WIRTELPRIMPF_REPO_SLUG"),
        repo_subdir=env("WIRTELPRIMPF_REPO_SUBDIR", "Wirtelprimpf") or "Wirtelprimpf",
        repo_branch=env("WIRTELPRIMPF_REPO_BRANCH", "main") or "main",
        image_model=env("WIRTELPRIMPF_IMAGE_MODEL", "gpt-image-2") or "gpt-image-2",
        image_size=parse_image_size(env("WIRTELPRIMPF_IMAGE_SIZE", "1536x1024") or "1536x1024"),
        output_resolution=parse_output_resolution(env("WIRTELPRIMPF_OUTPUT_RESOLUTION", "2k") or "2k"),
        flex_processing_mode=parse_flex_processing(),
        prompt_config_path=Path(
            env("WIRTELPRIMPF_PROMPT_CONFIG", str(default_prompt_config)) or str(default_prompt_config)
        ).expanduser(),
        commit_author_name=env("WIRTELPRIMPF_GIT_AUTHOR_NAME", "Wirtelprimpf Bot") or "Wirtelprimpf Bot",
        commit_author_email=env("WIRTELPRIMPF_GIT_AUTHOR_EMAIL", "wirtelprimpf@example.invalid")
        or "wirtelprimpf@example.invalid",
    )


def run(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            check=True,
            text=True,
            capture_output=True,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Command timed out after {GIT_TIMEOUT_SECONDS}s: {' '.join(command)}") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        message = f"Command failed: {' '.join(command)}"
        if stderr:
            message = f"{message}: {stderr}"
        raise RuntimeError(message) from exc


def ensure_repo(config: Config) -> Path | None:
    if config.repo_path is None:
        return None

    if (config.repo_path / ".git").is_dir():
        run(["git", "fetch", "origin", config.repo_branch], cwd=config.repo_path)
        run(["git", "checkout", config.repo_branch], cwd=config.repo_path)
        run(["git", "pull", "--ff-only", "origin", config.repo_branch], cwd=config.repo_path)
    else:
        if not config.repo_slug:
            raise RuntimeError("WIRTELPRIMPF_REPO_PATH is not a Git checkout and WIRTELPRIMPF_REPO_SLUG is unset")
        if not shutil.which("gh"):
            raise RuntimeError("gh is required to clone WIRTELPRIMPF_REPO_SLUG")

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

    relative_paths = [str(path.relative_to(config.repo_path)) for path in paths]
    run(["git", "add", *relative_paths], cwd=config.repo_path)
    status = run(["git", "status", "--porcelain", "--", *relative_paths], cwd=config.repo_path)
    if not status.stdout.strip():
        return

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
    run(["git", "push", "origin", config.repo_branch], cwd=config.repo_path)


def parse_resolution(value: str) -> tuple[int, int] | None:
    normalized = value.strip().lower()
    aliases: dict[str, tuple[int, int] | None] = {
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
    if normalized in aliases:
        return aliases[normalized]

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
    if not raw or not re.match(IMAGE_SIZE_PATTERN, raw):
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
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(payload)
    tmp.replace(path)


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

    raise ValueError(
        "Invalid WIRTELPRIMPF_FLEX_PROCESSING value. "
        "Use on/off, true/false, yes/no, 1/0, enabled/disabled, or a concrete mode (low|high)."
    )


def bullet_list(values: list[str]) -> str:
    return "\n".join(f"- {value}" for value in values)


def load_prompt_config(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError("Prompt config must be a JSON object")
    return data


def build_prompt(data: dict[str, object]) -> str:
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
    if is_birthday_run(now, birthday):
        return build_birthday_prompts(now, birthday)
    return [build_prompt(data)]


def is_retryable_generation_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        isinstance(exc, (TimeoutError, OSError))
        or "timeout" in message
        or "rate limit" in message
        or "temporarily" in message
        or "connection" in message
        or "429" in message
    )


def generate_image_with_retries(client: OpenAI, request: dict[str, object]) -> str:
    last_error: Exception | None = None
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
            if not is_retryable_generation_error(exc) or attempt == GENERATION_RETRIES:
                break
            delay = GENERATION_RETRY_BASE_SECONDS * attempt
            time.sleep(delay)
    assert last_error is not None
    raise last_error


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


def emit_summary(summary: RunSummary, args: argparse.Namespace) -> None:
    if args.json:
        ok = summary.exit_code == 0
        print(
            format_json(
                {
                    "ok": ok,
                    "version": VERSION,
                    "timestamp": build_status_timestamp(),
                    "status": STATUS_OK if ok else STATUS_ERROR,
                    "exit_code": summary.exit_code,
                    "summary": {
                        "success": summary.success,
                        "failed": summary.failed,
                        "skipped": summary.skipped,
                        "prompts": summary.prompts,
                        "total": summary.total,
                        "exit_code": summary.exit_code,
                    },
                }
            )
        )


def emit_status(payload: dict[str, object], *, as_json: bool) -> int:
    if as_json:
        status = bool(payload.get("ok"))
        payload = dict(payload)
        payload.setdefault("timestamp", build_status_timestamp())
        payload.setdefault("status", STATUS_OK if status else STATUS_ERROR)
        payload.setdefault("version", VERSION)
        payload.setdefault("ok", status)
        payload.setdefault("exit_code", 0 if status else 1)
        print(format_json(payload))
        return 0 if status else 1

    print(f"wirtelprimpf_generator.py status: {payload.get('status', STATUS_ERROR)}")
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
        "status": STATUS_OK,
        "exit_code": 0,
        "checks": [],
        "details": {
            "git_available": bool(shutil.which("git")),
            "gh_available": bool(shutil.which("gh")),
            "openai_key_present": bool(env("OPENAI_API_KEY")),
        },
    }
    checks = report["checks"]

    if config is None:
        checks.append({"name": "load_config", "ok": False, "message": "Configuration loading failed"})
        report["ok"] = False
        report["status"] = STATUS_ERROR
        report["exit_code"] = 1
        return report

    prompt_config = config.prompt_config_path
    checks.append({"name": "prompt_config_file", "ok": prompt_config.exists(), "path": str(prompt_config)})
    if not prompt_config.exists():
        report["ok"] = False
        report["status"] = STATUS_ERROR
        report["exit_code"] = 1
        checks.append({"name": "prompt_config_parse", "ok": False, "message": "Prompt config file missing"})
        return report

    try:
        prompts = build_prompts(prompt_config, datetime.now())
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
                "prompt_count": len(prompts),
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

    if config.repo_path is None:
        checks.append({"name": "repo", "ok": True, "enabled": False})
    else:
        repo_checks = {"name": "repo", "ok": True, "path": str(config.repo_path), "slug": config.repo_slug}
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
        elif not shutil.which("gh"):
            repo_checks["ok"] = False
            repo_checks["message"] = "gh CLI is required to auto-clone missing repo path"
            report["ok"] = False
            report["status"] = STATUS_ERROR
            report["exit_code"] = 1
        checks.append(repo_checks)

    if not env("OPENAI_API_KEY"):
        checks.append({"name": "openai_key", "ok": False, "message": "OPENAI_API_KEY not set"})
        report["ok"] = False
        report["status"] = STATUS_ERROR
        report["exit_code"] = 1

    return report


def _die(message: str, *, exit_code: int = 1) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(exit_code)


def main() -> None:
    args = parse_args()

    if args.status:
        try:
            cfg = load_config()
        except Exception as exc:
            payload = status_report(None)
            payload["checks"].append({"name": "load_config", "ok": False, "message": str(exc)})
            _code = emit_status(payload, as_json=args.json)
        else:
            _code = emit_status(status_report(cfg), as_json=args.json)
        raise SystemExit(_code)

    if not os.environ.get("OPENAI_API_KEY") and not args.check_config and not args.dry_run:
        _die("OPENAI_API_KEY environment variable is required")

    config = load_config()
    if not config.prompt_config_path.exists():
        _die(f"Prompt config file not found: {config.prompt_config_path}")

    try:
        prompts = build_prompts(config.prompt_config_path, datetime.now())
    except Exception as exc:
        if args.check_config and args.json:
            print(
                format_json(
                    {
                        "ok": False,
                        "version": VERSION,
                        "timestamp": build_status_timestamp(),
                        "status": STATUS_ERROR,
                        "exit_code": 1,
                        "check_config": True,
                        "message": f"Prompt config validation failed: {exc}",
                    }
                )
            )
            raise SystemExit(1)
        _die(f"Prompt config validation failed: {exc}")

    if args.check_config:
        if args.json:
            print(
                format_json(
                    {
                        "ok": True,
                        "version": VERSION,
                        "timestamp": build_status_timestamp(),
                        "status": STATUS_OK,
                        "exit_code": 0,
                        "check_config": True,
                        "local_outdir": str(config.local_outdir),
                        "prompt_count": len(prompts),
                        "model": config.image_model,
                        "image_size": config.image_size,
                        "output_resolution": config.output_resolution,
                        "repo_path": str(config.repo_path) if config.repo_path else None,
                    }
                )
            )
            return
        print("Prompt configuration is valid.")
        print(f"Resolved config: local_outdir={config.local_outdir}")
        print(f"model={config.image_model} size={config.image_size} output_resolution={config.output_resolution}")
        print(f"repo_path={config.repo_path or '<disabled>'}")
        print(f"prompts={len(prompts)}")
        return

    if not config.local_outdir.is_dir() and config.local_outdir.exists():
        _die(f"WIRTELPRIMPF_LOCAL_OUTDIR is not a directory: {config.local_outdir}")

    config.local_outdir.mkdir(parents=True, exist_ok=True)
    repo_outdir = ensure_repo(config)
    summary = RunSummary(total=len(prompts))

    if args.dry_run:
        for index, prompt in enumerate(prompts, start=1):
            if args.json:
                print(
                    format_json(
                        {
                            "ok": True,
                            "version": VERSION,
                            "timestamp": build_status_timestamp(),
                            "status": STATUS_OK,
                            "exit_code": 0,
                            "type": "dry_run",
                            "index": index,
                            "total": len(prompts),
                            "prompt_preview": prompt[:140],
                        }
                    )
                )
            else:
                print(f"[DRY-RUN {index}/{len(prompts)}] {prompt[:140]}...")
            summary.skipped += 1
        summary.exit_code = 0
        emit_summary(summary, args)
        return

    client = OpenAI()
    for index, prompt in enumerate(prompts, start=1):
        timestamp = build_timestamp()
        suffix = f"_geburtstag-{index:02d}" if len(prompts) > 1 else ""
        stem = f"wirtelprimpf_{timestamp}{suffix}"
        local_png = config.local_outdir / f"{stem}.png"
        local_prompt = config.local_outdir / f"{stem}.txt"

        request: dict[str, object] = {
            "model": config.image_model,
            "prompt": prompt,
            "size": config.image_size,
        }
        if config.flex_processing_mode:
            request["processing"] = config.flex_processing_mode

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
            resize_cover(local_png, parse_resolution(config.output_resolution))
            local_prompt.write_text(prompt, encoding="utf-8")
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

        if repo_outdir is None:
            continue

        repo_png = repo_outdir / local_png.name
        repo_prompt = repo_outdir / local_prompt.name
        try:
            shutil.copy2(local_png, repo_png)
            shutil.copy2(local_prompt, repo_prompt)
            commit_and_push(config, [repo_png, repo_prompt], stem)
            print(f"Repository image: {repo_png}")
            print(f"Repository prompt: {repo_prompt}")
        except Exception as exc:
            print(f"Repository publish failed for {stem}: {exc}", file=sys.stderr)
            summary.failed += 1
            summary.exit_code = 2
            continue

    if summary.exit_code:
        if not args.json:
            print(f"Completed with {summary.failed} failure(s)", file=sys.stderr)
        emit_summary(summary, args)
        _die(f"Completed with {summary.failed} failure(s)", exit_code=summary.exit_code)

    emit_summary(summary, args)
    return


if __name__ == "__main__":
    main()
