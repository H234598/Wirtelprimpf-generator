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

BIRTHDAY_BASE_YEAR = 2026
BIRTHDAY_BASE_AGE = 15


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


def load_prompt_config(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError("Prompt config must be a JSON object")
    return data


def build_prompt(config_path: Path) -> str:
    data = load_prompt_config(config_path)
    template = data.get("template")
    if not isinstance(template, str) or not template.strip():
        raise ValueError("Prompt config key 'template' must be a non-empty string")

    values = {
        "setting": random.choice(require_list(data, "settings")),
        "action": random.choice(require_list(data, "actions")),
        "joke": random.choice(require_list(data, "jokes")),
        "mood": random.choice(require_list(data, "moods")),
        "style": random.choice(require_list(data, "styles")),
    }
    return template.format(**values).strip()


def birthday_age(now: datetime) -> int:
    return BIRTHDAY_BASE_AGE + (now.year - BIRTHDAY_BASE_YEAR)


def is_birthday_run(now: datetime) -> bool:
    force = os.environ.get("WIRTELPRIMPF_FORCE_BIRTHDAY", "").strip().lower()
    if force in {"1", "true", "yes", "ja"}:
        return True
    return now.month == 5 and now.day == 22 and now.hour == 0


def build_birthday_prompts(now: datetime) -> list[str]:
    age = birthday_age(now)
    shared_rules = f"""Erzeuge ein einzelnes hochwertiges Bild im Wirtelprimpf-Stil.

Zwingende Bildregeln:
- Genau zwei Hauskatzen: eine kleinere weisse weibliche Katze und eine groessere schwarze maennliche Katze.
- Beide haben gruene Augen, mittellanges Fell und sind klar sichtbar.
- Heute feiern sie ihren {age}. Geburtstag; die Zahl {age} muss als Geburtstagssignal erkennbar sein.
- Ausgelassene Stimmung, aber nicht platt, nicht slapstickhaft, kein Klamauk.
- Offene Muender wirken unsexy: hoechstens dezent, nie dominant.
- Eine kleine Maus feiert sichtbar mit.
- Eine kleine feiernde comichafte Karotte ist sichtbar und charmant absurd.
- Ein leicht erkennbarer Hase ist im Bild versteckt und feiert mit; versteckt, aber beim genaueren Hinsehen eindeutig.
- Der Mond muss sichtbar sein, stilistisch passend, eher rechts oben im Bild.
- Viele Geschenke im Vordergrund; die Geschenke sind wichtiger und praesenter als das Armageddon.
- Der Humor soll subtil sein und auf den zweiten oder dritten Blick funktionieren: doppelte und dreifache Bedeutungen, visuelle Wortspiele, leise Ironie, keine offensichtlichen Schilderwitze.
- Falls Text vorkommt, dann nur winzig und als Hintergrunddetail.
- Keine Katze sitzt in einer Kiste, keinem Regal, keinem Schrank, keinem Topf, keiner Nische.
- Die weisse Katze darf nicht uebertrieben suess, kawaii oder puppenhaft wirken.
- Die schwarze Katze soll groesser, ruhig, wuerdevoll und etwas keck wirken."""

    return [
        f"""{shared_rules}

Szene:
Die beiden Wirtelprimpfe feiern vor einer antiken Stadt, die im Armageddon vergeht, eine Geburtstagsparty. Im Hintergrund gehen Tempel, Saeulen, Aquaedukte und Sternwarten dramatisch unter, aber der Vordergrund bleibt eine elegante, vielschichtige Partylandschaft voller Geschenke, Schleifen, seltsam bedeutungsvoller kleiner Objekte und feiner visueller Witze. Die Apokalypse ist Kulisse, nicht Hauptdarsteller.

Stil:
Realistisch-painterly, edel, detailreich, warmes Festlicht gegen kosmisches Katastrophenlicht, klassisch komponiert, humorvolle Feinheiten in jeder Bildecke.""",
        f"""{shared_rules}

Szene:
Vor einem verwandten, aber eigenstaendigen Hintergrund deiner Wahl: eine halb versunkene antike Hafenstadt unter Sternen, ein zerbrochenes Observatorium, ein Festplatz zwischen Ruinen und leuchtenden Himmelszeichen. Es soll sich wie dieselbe Geburtstagsnacht anfuehlen, aber nicht wie eine Wiederholung. Die Party, die Geschenke und die feinen Nebenbedeutungen dominieren; das Armageddon bleibt elegant im Hintergrund.

Stil:
Hochwertiger westlicher Comic-Painterly-Mix, kein Manga, kein Superheldenlook; dicht komponiert, witzig, festlich, mit vielen kleinen Details, die erst beim zweiten Hinschauen Sinn ergeben.""",
    ]


def build_prompts(config_path: Path, now: datetime) -> list[str]:
    if is_birthday_run(now):
        return build_birthday_prompts(now)
    return [build_prompt(config_path)]


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
