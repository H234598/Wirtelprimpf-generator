#!/usr/bin/env python3
"""Generate Wirtelprimpf-style cat images and optionally publish them to Git."""

from __future__ import annotations

import base64
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
    commit_author_name: str
    commit_author_email: str


def load_config() -> Config:
    default_outdir = Path.home() / "Pictures" / "Wirtelprimpf"
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


SETTINGS = [
    "alte alpine Wetterstation bei Sonnenaufgang",
    "verlassene Druckerei mit warmem Staublicht",
    "Kartographenzimmer voller riesiger Landkarten",
    "Opernhaus waehrend einer leeren Probe",
    "Baeckerei am fruehen Morgen, Mehl auf dem Boden",
    "Bibliothek eines exzentrischen Astronomen",
    "Gewaechshaus nach einem Regenschauer",
    "Bahnhofsvorsteherbuero in den Bergen",
    "Uhrenmacherwerkstatt mit viel Messing und Staub",
    "alter Lesesaal mit Kamin und einem einzigen offenen Fenster",
    "Museumsmagazin voller falsch beschrifteter Artefakte",
    "Fischmarkt kurz vor Oeffnung, noch fast menschenleer",
    "Dachboden eines Naturkundemuseums",
    "Schreibstube eines absurden Ministeriums",
    "Kueche eines alten Gasthauses kurz vor dem Mittag",
]

ACTIONS = [
    "die weisse Katze laeuft wachsam durchs Bild, die schwarze Katze schlaeft breit und zufrieden",
    "die weisse Katze untersucht etwas, die schwarze Katze liegt faul daneben",
    "beide Katzen laufen ruhig durch die Szene, als haetten sie einen wichtigen Termin",
    "die weisse Katze frisst etwas Unverdaechtiges, die schwarze Katze beobachtet sie streng",
    "die schwarze Katze schlaeft, waehrend die weisse Katze so tut, als sei alles unter Kontrolle",
    "beide Katzen sitzen nicht irgendwo drin, sondern befinden sich sichtbar frei im Raum",
    "die weisse Katze spielt mit einem kleinen Gegenstand, die schwarze Katze ignoriert das demonstrativ",
    "die schwarze Katze liegt lang ausgestreckt auf dem Boden, die weisse Katze geht vorbei",
]

JOKES = [
    "subtiler Humor auf den zweiten Blick",
    "ein kleines Schild mit trockenem deutschen Unsinn im Hintergrund",
    "nichts Slapstickhaftes, eher feiner visueller Witz",
    "eine winzige absurde buerokratische Notiz irgendwo im Bild",
    "ein Gegenstand ist offensichtlich fehl am Platz, aber niemand kommentiert es",
    "die Szene wirkt serioes, bis man ein kleines Detail bemerkt",
]


def build_prompt() -> str:
    setting = random.choice(SETTINGS)
    action = random.choice(ACTIONS)
    joke = random.choice(JOKES)

    return f"""
Erzeuge ein einzelnes hochwertiges Bild im Wirtelprimpf-Stil.

Zwingende Bildregeln:
- Genau zwei normale, nicht-anthropomorphe Hauskatzen.
- Eine kleinere weisse weibliche Katze.
- Eine groessere schwarze maennliche Katze.
- Beide haben gruene Augen.
- Beide haben mittellanges Fell.
- Die Katzen sind echte Tiere, keine Menschen, keine Kleidung, keine vermenschlichten Posen.
- Keine Katze sitzt in einer Kiste, keinem Regal, keinem Schrank, keinem Topf, keiner Nische.
- Die weisse Katze darf nicht uebertrieben suess, kawaii oder puppenhaft wirken.
- Die schwarze Katze soll groesser, ruhig, wuerdevoll und etwas keck wirken.
- Beide Katzen muessen klar sichtbar sein.

Szene:
{setting}.

Handlung:
{action}.

Stimmung:
Realistisch-painterly, edel, detailreich, warmes natuerliches Licht, klassisch komponiert.
Die Szene soll wie eine kleine Geschichte wirken.
{joke}.
Keine Textlastigkeit; falls Text vorkommt, nur als kleines Hintergrunddetail.
Jedes Bild soll ein komplett neues Setting haben und nicht wie das vorherige wirken.
""".strip()


def main() -> None:
    config = load_config()
    config.local_outdir.mkdir(parents=True, exist_ok=True)

    prompt = build_prompt()
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    stem = f"wirtelprimpf_{timestamp}"
    local_png = config.local_outdir / f"{stem}.png"
    local_prompt = config.local_outdir / f"{stem}.txt"

    response = OpenAI().images.generate(
        model=config.image_model,
        prompt=prompt,
        size=config.image_size,
    )

    local_png.write_bytes(base64.b64decode(response.data[0].b64_json))
    resize_cover(local_png, parse_resolution(config.output_resolution))
    local_prompt.write_text(prompt, encoding="utf-8")
    print(f"Local image: {local_png}")
    print(f"Local prompt: {local_prompt}")

    repo_outdir = ensure_repo(config)
    if repo_outdir is None:
        return

    repo_png = repo_outdir / local_png.name
    repo_prompt = repo_outdir / local_prompt.name
    shutil.copy2(local_png, repo_png)
    shutil.copy2(local_prompt, repo_prompt)
    commit_and_push(config, [repo_png, repo_prompt], stem)
    print(f"Repository image: {repo_png}")
    print(f"Repository prompt: {repo_prompt}")


if __name__ == "__main__":
    main()
