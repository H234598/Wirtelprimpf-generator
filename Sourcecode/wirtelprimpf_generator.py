#!/usr/bin/env python3
"""Generate Wirtelprimpf-style cat images and optionally publish them to Git."""

from __future__ import annotations

import base64
import json
import os
import random
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from openai import OpenAI
from PIL import Image


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
        image_size=env("WIRTELPRIMPF_IMAGE_SIZE", "1536x1024") or "1536x1024",
        output_resolution=env("WIRTELPRIMPF_OUTPUT_RESOLUTION", "2k") or "2k",
        prompt_config_path=Path(
            env("WIRTELPRIMPF_PROMPT_CONFIG", str(default_prompt_config)) or str(default_prompt_config)
        ).expanduser(),
        commit_author_name=env("WIRTELPRIMPF_GIT_AUTHOR_NAME", "Wirtelprimpf Bot") or "Wirtelprimpf Bot",
        commit_author_email=env("WIRTELPRIMPF_GIT_AUTHOR_EMAIL", "wirtelprimpf@example.invalid")
        or "wirtelprimpf@example.invalid",
    )


def run(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, check=True, text=True, capture_output=True)


def ensure_repo(config: Config) -> Path | None:
    if config.repo_path is None:
        return None

    if (config.repo_path / ".git").exists():
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

    repo_outdir = config.repo_path / config.repo_subdir
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

    try:
        width, height = normalized.split("x", 1)
        return int(width), int(height)
    except ValueError as exc:
        raise ValueError(f"Invalid WIRTELPRIMPF_OUTPUT_RESOLUTION: {value!r}") from exc


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
    return template.format(**values).strip()


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
    return prompts


def build_prompts(config_path: Path, now: datetime) -> list[str]:
    data = load_prompt_config(config_path)
    birthday = birthday_config(data)
    if is_birthday_run(now, birthday):
        return build_birthday_prompts(now, birthday)
    return [build_prompt(data)]


def main() -> None:
    config = load_config()
    config.local_outdir.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    prompts = build_prompts(config.prompt_config_path, now)
    client = OpenAI()
    repo_outdir = ensure_repo(config)

    for index, prompt in enumerate(prompts, start=1):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        suffix = f"_geburtstag-{index:02d}" if len(prompts) > 1 else ""
        stem = f"wirtelprimpf_{timestamp}{suffix}"
        local_png = config.local_outdir / f"{stem}.png"
        local_prompt = config.local_outdir / f"{stem}.txt"

        response = client.images.generate(
            model=config.image_model,
            prompt=prompt,
            size=config.image_size,
        )

        local_png.write_bytes(base64.b64decode(response.data[0].b64_json))
        resize_cover(local_png, parse_resolution(config.output_resolution))
        local_prompt.write_text(prompt, encoding="utf-8")
        print(f"Local image: {local_png}")
        print(f"Local prompt: {local_prompt}")

        if repo_outdir is None:
            continue

        repo_png = repo_outdir / local_png.name
        repo_prompt = repo_outdir / local_prompt.name
        shutil.copy2(local_png, repo_png)
        shutil.copy2(local_prompt, repo_prompt)
        commit_and_push(config, [repo_png, repo_prompt], stem)
        print(f"Repository image: {repo_png}")
        print(f"Repository prompt: {repo_prompt}")


if __name__ == "__main__":
    main()
