"""Exact current-story source selection and hub Pages workflow dispatch."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .naming import archive_target_for_volume

HUB_SOURCE_SCHEMA = "1.0.0"
STORY_FILE = re.compile(r"^Wirtelprimpf_Story_([IVXLCDM]+)\.md$")


def _roman(value: int) -> str:
    if value < 1 or value > 9_999:
        raise RuntimeError("story volume is outside the supported Roman numeral range")
    parts: list[str] = []
    remaining = value
    for number, symbol in (
        (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
        (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
        (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
    ):
        count, remaining = divmod(remaining, number)
        parts.append(symbol * count)
    return "".join(parts)


def _roman_to_integer(value: str) -> int:
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    if not value or any(character not in values for character in value):
        raise RuntimeError(f"invalid Roman story volume: {value!r}")
    result = 0
    previous = 0
    for character in reversed(value):
        current = values[character]
        result += -current if current < previous else current
        previous = max(previous, current)
    return result


@dataclass(frozen=True, slots=True)
class HubSource:
    external: bool
    repository: str
    revision: str | None
    current_volume: int
    story_file: Path
    story_files: tuple[Path, ...]
    media_manifest: Path


@dataclass(frozen=True, slots=True)
class HubDispatchRequest:
    archive_repository: str
    archive_revision: str
    current_volume: int

    def __post_init__(self) -> None:
        _validate_source(self.archive_repository, self.current_volume)
        if not re.fullmatch(r"[0-9a-f]{40}", self.archive_revision):
            raise RuntimeError("archive revision must be a full lower-case Git commit SHA")


def _validate_source(repository: str, current_volume: int) -> tuple[str, str]:
    target = archive_target_for_volume(current_volume)
    if repository != target.repository:
        raise RuntimeError(
            f"hub repository {repository!r} does not match current volume {current_volume} ({target.repository})"
        )
    story_path = f"Wirtelprimpf/Wirtelprimpf_Story_{_roman(current_volume)}.md"
    return target.repository, story_path


def _published_story_files(root: Path, current_volume: int) -> tuple[Path, ...]:
    story_root = root / "Wirtelprimpf"
    if story_root.is_symlink() or not story_root.is_dir():
        raise RuntimeError("exact archive story directory is missing or unsafe")
    archive_start = ((current_volume - 1) // 50) * 50 + 1
    found: dict[int, Path] = {}
    for path in sorted(story_root.iterdir(), key=lambda item: item.name.casefold()):
        match = STORY_FILE.fullmatch(path.name)
        if not match:
            continue
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"exact archive story file is missing or unsafe: {path.name}")
        volume = _roman_to_integer(match.group(1))
        if archive_start <= volume <= current_volume:
            if volume in found:
                raise RuntimeError(f"duplicate exact archive story volume: {volume}")
            found[volume] = path
    expected = story_root / f"Wirtelprimpf_Story_{_roman(current_volume)}.md"
    if current_volume not in found or found[current_volume] != expected:
        raise RuntimeError(f"exact current story is missing: {expected}")
    return tuple(found[volume] for volume in sorted(found))


def resolve_hub_source(
    data_root: Path,
    *,
    repository: str | None = None,
    revision: str | None = None,
    current_volume: int | None = None,
    external_root: Path | None = None,
) -> HubSource:
    """Resolve either committed fallback data or one exact archive commit."""
    data_root = Path(data_root)
    supplied = (repository is not None, revision is not None, current_volume is not None)
    if any(supplied) and not all(supplied):
        raise RuntimeError("external hub source requires repository, revision, and current volume together")
    if all(supplied):
        assert repository is not None and revision is not None and current_volume is not None
        if not re.fullmatch(r"[0-9a-f]{40}", revision):
            raise RuntimeError("archive_ref must be a full lower-case Git commit SHA")
        if external_root is None:
            raise RuntimeError("external archive checkout root is required")
        canonical_repository, story_path = _validate_source(repository, current_volume)
        root = Path(external_root)
        story_files = _published_story_files(root, current_volume)
        return HubSource(
            external=True,
            repository=canonical_repository,
            revision=revision,
            current_volume=current_volume,
            story_file=root / story_path,
            story_files=story_files,
            media_manifest=root / "media-manifest.json",
        )

    source_path = data_root / "hub-source.json"
    story_file = data_root / "current-story.md"
    if source_path.is_symlink() or story_file.is_symlink():
        raise RuntimeError("committed hub source files must not be symlinks")
    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read committed hub source: {source_path}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != HUB_SOURCE_SCHEMA:
        raise RuntimeError("unsupported committed hub source schema")
    fallback_repository = payload.get("repository")
    fallback_volume = payload.get("current_volume")
    if not isinstance(fallback_repository, str):
        raise RuntimeError("committed hub repository is invalid")
    if not isinstance(fallback_volume, int) or isinstance(fallback_volume, bool):
        raise RuntimeError("committed hub volume is invalid")
    canonical_repository, expected_story_path = _validate_source(fallback_repository, fallback_volume)
    if payload.get("story_path") != expected_story_path:
        raise RuntimeError("committed hub story path is not canonical")
    if not story_file.is_file():
        raise RuntimeError(f"committed current story is missing: {story_file}")
    fallback_revision = payload.get("revision")
    if fallback_revision is not None and not re.fullmatch(r"[0-9a-f]{40}", str(fallback_revision)):
        raise RuntimeError("committed hub archive revision is invalid")
    return HubSource(
        external=False,
        repository=canonical_repository,
        revision=str(fallback_revision) if fallback_revision is not None else None,
        current_volume=fallback_volume,
        story_file=story_file,
        story_files=(story_file,),
        media_manifest=data_root / "media-manifest.json",
    )


def _default_runner(command: list[str]) -> None:
    try:
        result = subprocess.run(
            command,
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError("cannot execute GitHub hub workflow dispatch") from exc
    if result.returncode != 0:
        raise RuntimeError(f"GitHub hub workflow dispatch failed: {result.stderr.strip()}")


class GitHubHubDispatcher:
    def __init__(
        self,
        *,
        owner: str,
        runner: Callable[[list[str]], None] = _default_runner,
    ) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", owner):
            raise ValueError(f"invalid GitHub owner: {owner!r}")
        self.owner = owner
        self.runner = runner

    def dispatch(
        self,
        *,
        archive_repository: str,
        archive_revision: str,
        current_volume: int,
    ) -> None:
        canonical_repository, _ = _validate_source(archive_repository, current_volume)
        if not re.fullmatch(r"[0-9a-f]{40}", archive_revision):
            raise RuntimeError("archive revision must be a full lower-case Git commit SHA")
        self.runner(
            [
                "gh", "workflow", "run", "hub-pages.yml",
                "--repo", f"{self.owner}/Wirtelprimpf-generator",
                "--ref", "main",
                "-f", f"active_repository={canonical_repository}",
                "-f", f"archive_ref={archive_revision}",
                "-f", f"current_volume={current_volume}",
            ]
        )


class HubDispatchOutbox:
    """Private one-item outbox; duplicate workflow dispatch is safe after a crash."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def load(self) -> HubDispatchRequest | None:
        if self.path.is_symlink():
            raise RuntimeError(f"hub dispatch outbox must not be a symlink: {self.path}")
        if not self.path.exists():
            return None
        if not self.path.is_file():
            raise RuntimeError(f"hub dispatch outbox must be a regular file: {self.path}")
        mode = stat.S_IMODE(self.path.stat().st_mode)
        if mode & 0o077:
            raise RuntimeError(f"hub dispatch outbox permissions are too broad: {mode:04o}")
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or payload.get("schema_version") != HUB_SOURCE_SCHEMA:
                raise RuntimeError("unsupported hub dispatch outbox schema")
            return HubDispatchRequest(
                archive_repository=payload["archive_repository"],
                archive_revision=payload["archive_revision"],
                current_volume=payload["current_volume"],
            )
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(f"cannot read hub dispatch outbox: {self.path}") from exc

    def stage(self, request: HubDispatchRequest) -> None:
        existing = self.load()
        if existing is not None:
            if existing == request:
                return
            if (
                existing.archive_repository != request.archive_repository
                or existing.current_volume != request.current_volume
            ):
                raise RuntimeError("a different hub Pages dispatch is already pending")
        if self.path.parent.is_symlink():
            raise RuntimeError(f"hub dispatch outbox parent must not be a symlink: {self.path.parent}")
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.path.parent, 0o700)
        payload = {
            "schema_version": HUB_SOURCE_SCHEMA,
            "archive_repository": request.archive_repository,
            "archive_revision": request.archive_revision,
            "current_volume": request.current_volume,
        }
        encoded = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        part = self.path.with_name(f".{self.path.name}.{os.getpid()}.{uuid.uuid4().hex}.part")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(part, flags, 0o600)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(part, self.path)
            os.chmod(self.path, 0o600)
        finally:
            part.unlink(missing_ok=True)

    def dispatch_pending(self, dispatcher: GitHubHubDispatcher) -> bool:
        request = self.load()
        if request is None:
            return False
        dispatcher.dispatch(
            archive_repository=request.archive_repository,
            archive_revision=request.archive_revision,
            current_volume=request.current_volume,
        )
        if self.path.is_symlink():
            raise RuntimeError("hub dispatch outbox became a symlink before completion")
        self.path.unlink()
        return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m wirtelprimpf_platform.hub")
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--external-root", type=Path, required=True)
    parser.add_argument("--repository")
    parser.add_argument("--revision")
    parser.add_argument("--current-volume", type=int)
    parser.add_argument("--github-output", type=Path, default=Path(os.environ.get("GITHUB_OUTPUT", "")))
    args = parser.parse_args(argv)
    source = resolve_hub_source(
        args.data_root,
        repository=args.repository or None,
        revision=args.revision or None,
        current_volume=args.current_volume,
        external_root=args.external_root,
    )
    if not str(args.github_output):
        raise RuntimeError("GITHUB_OUTPUT is required")
    values = {
        "external": "true" if source.external else "false",
        "repository": source.repository,
        "revision": source.revision or "",
        "current_volume": str(source.current_volume),
        "story_file": str(source.story_file),
        "story_files": json.dumps([str(path) for path in source.story_files], separators=(",", ":")),
        "media_manifest": str(source.media_manifest),
    }
    with args.github_output.open("a", encoding="utf-8", newline="\n") as handle:
        for key, value in values.items():
            if "\n" in value or "\r" in value:
                raise RuntimeError(f"invalid multiline GitHub output: {key}")
            handle.write(f"{key}={value}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
