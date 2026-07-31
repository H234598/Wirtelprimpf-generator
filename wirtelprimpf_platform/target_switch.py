"""Verified catalog publication and atomic generator target switching."""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import uuid
from collections.abc import Callable
from pathlib import Path

from .naming import archive_name


class TargetSwitchError(RuntimeError):
    """The active generator target could not be changed without ambiguity."""


def _validate_archive(repository: str) -> str:
    match = re.fullmatch(r"Wirtelprimpf-(\d{4})", repository)
    if match is None or archive_name(int(match.group(1))) != repository:
        raise TargetSwitchError(f"invalid archive repository: {repository!r}")
    return repository


class GitCatalogPublisher:
    """Commit and normally push exactly the verified publication catalog."""

    def __init__(
        self,
        *,
        generator_root: Path,
        catalog_path: Path,
        branch: str = "main",
        timeout_seconds: int = 180,
    ) -> None:
        root = Path(generator_root)
        catalog = Path(catalog_path)
        if root.is_symlink() or catalog.is_symlink():
            raise TargetSwitchError("generator root and catalog must not be symlinks")
        if not (root / ".git").is_dir():
            raise TargetSwitchError(f"generator root is not a Git checkout: {root}")
        self.generator_root = root.resolve()
        try:
            self.catalog_relative = catalog.resolve().relative_to(self.generator_root)
        except ValueError as exc:
            raise TargetSwitchError("publication catalog must be inside generator checkout") from exc
        if self.catalog_relative.as_posix() != "data/publication-catalog.json":
            raise TargetSwitchError(
                f"unexpected publication catalog path: {self.catalog_relative.as_posix()}"
            )
        if not re.fullmatch(r"[A-Za-z0-9._/-]+", branch) or ".." in branch:
            raise TargetSwitchError(f"invalid Git branch: {branch!r}")
        self.branch = branch
        self.timeout_seconds = timeout_seconds

    def _run(self, command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        try:
            result = subprocess.run(
                command,
                cwd=self.generator_root,
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise TargetSwitchError(f"cannot execute {command[0]} {command[1:2]}") from exc
        if check and result.returncode != 0:
            raise TargetSwitchError(
                f"command failed ({result.returncode}): {command[0]} {command[1:2]}: {result.stderr.strip()}"
            )
        return result

    def publish(self, repository: str) -> str:
        repository = _validate_archive(repository)
        if not (self.generator_root / self.catalog_relative).is_file():
            raise TargetSwitchError("publication catalog is missing")
        status = self._run(["git", "status", "--porcelain=v1", "--untracked-files=all"]).stdout.splitlines()
        expected = self.catalog_relative.as_posix()
        foreign = [line for line in status if line[3:] != expected]
        if foreign:
            raise TargetSwitchError(
                f"generator checkout has changes outside publication catalog; refusing target switch: {foreign}"
            )
        self._run(["git", "diff", "--check", "--", expected])
        self._run(["git", "add", "--", expected])
        staged = self._run(["git", "diff", "--cached", "--quiet", "--", expected], check=False)
        if staged.returncode not in {0, 1}:
            raise TargetSwitchError("cannot determine staged publication-catalog state")
        if staged.returncode == 1:
            self._run(
                [
                    "git",
                    "-c",
                    "user.name=Wirtelprimpf Bot",
                    "-c",
                    "user.email=wirtelprimpf@example.invalid",
                    "commit",
                    "-m",
                    f"chore: activate {repository} in publication catalog",
                    "--",
                    expected,
                ]
            )
        revision = self._run(["git", "rev-parse", "HEAD"]).stdout.strip()
        if not re.fullmatch(r"[0-9a-f]{40}", revision):
            raise TargetSwitchError("local generator revision is invalid")
        self._run(["git", "push", "origin", self.branch])
        remote = self._run(["git", "ls-remote", "--exit-code", "origin", f"refs/heads/{self.branch}"]).stdout
        fields = remote.strip().split()
        if len(fields) != 2 or fields[0] != revision:
            raise TargetSwitchError("remote generator revision does not match catalog commit")
        return revision


class GeneratorTargetSwitcher:
    """Publish the catalog, then atomically point the next timer run at its archive."""

    def __init__(
        self,
        *,
        settings_path: Path,
        archive_root: Path,
        owner: str,
        publish_catalog: Callable[[str], object],
    ) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", owner):
            raise TargetSwitchError(f"invalid GitHub owner: {owner!r}")
        self.settings_path = Path(settings_path)
        self.archive_root = Path(archive_root)
        self.owner = owner
        self.publish_catalog = publish_catalog

    def _switch_settings(self, repository: str) -> None:
        path = self.settings_path
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise TargetSwitchError(f"settings path must be a regular non-symlink file: {path}")
        try:
            lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
        except (OSError, UnicodeError) as exc:
            raise TargetSwitchError(f"cannot read generator settings: {path}") from exc
        updates = {
            "WIRTELPRIMPF_REPO_PATH": str(self.archive_root / repository),
            "WIRTELPRIMPF_REPO_SLUG": f"{self.owner}/{repository}",
        }
        seen: set[str] = set()
        rendered: list[str] = []
        for line in lines:
            if "=" not in line or line.lstrip().startswith("#"):
                rendered.append(line)
                continue
            key = line.split("=", 1)[0].strip()
            if key not in updates:
                rendered.append(line)
                continue
            if key in seen:
                raise TargetSwitchError(f"duplicate target setting: {key}")
            seen.add(key)
            rendered.append(f"{key}={shlex.quote(updates[key])}")
        for key in sorted(set(updates) - seen):
            rendered.append(f"{key}={shlex.quote(updates[key])}")
        encoded = "\n".join(rendered).rstrip() + "\n"

        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(path.parent, 0o700)
        part = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.part")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(part, flags, 0o600)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(part, path)
            os.chmod(path, 0o600)
        finally:
            part.unlink(missing_ok=True)

    def switch_target(self, repository: str) -> None:
        repository = _validate_archive(repository)
        # Publishing first ensures the central hub never points at a local-only
        # target. A publish failure leaves the private settings byte-identical.
        self.publish_catalog(repository)
        self._switch_settings(repository)
