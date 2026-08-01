"""Concrete GitHub backend for idempotent publication-archive provisioning."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .naming import ARCHIVE_CAPACITY, STORIES_PER_BOOK, archive_domain, archive_name

ARCHIVE_GITIGNORE = """# Lokale Laufzeit- und Migrationsartefakte.
__pycache__/
*.py[cod]
.DS_Store
*.part
*.tmp
/release-staging/
/migration-work/

# Binäre Publikationsmedien gehören ausschließlich in verifizierte Releases.
/Wirtelprimpf/*.png
/Wirtelprimpf/**/*.png
/Wirtelprimpf/*.jpg
/Wirtelprimpf/**/*.jpg
/Wirtelprimpf/*.jpeg
/Wirtelprimpf/**/*.jpeg
/Wirtelprimpf/*.webp
/Wirtelprimpf/**/*.webp
/Wirtelprimpf/*.gif
/Wirtelprimpf/**/*.gif
/Wirtelprimpf/*.avif
/Wirtelprimpf/**/*.avif
"""


class GitHubProvisionError(RuntimeError):
    """A GitHub archive provisioning step cannot be completed safely."""


def _atomic_text(path: Path, text: str, *, mode: int = 0o644) -> None:
    if path.is_symlink():
        raise GitHubProvisionError(f"refusing to replace symlink: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(f".{path.name}.{os.getpid()}.part")
    try:
        descriptor = os.open(part, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(part, path)
        os.chmod(path, mode)
    finally:
        part.unlink(missing_ok=True)


class GitHubProvisioner:
    def __init__(
        self,
        *,
        owner: str,
        generator_root: Path,
        archive_root: Path,
        factory_ref: str,
        timeout_seconds: int = 300,
    ) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", owner):
            raise ValueError("invalid GitHub owner")
        if not re.fullmatch(r"[0-9a-f]{40}", factory_ref):
            raise ValueError("factory_ref must be a full 40-character commit SHA")
        self.owner = owner
        self.generator_root = Path(generator_root).resolve()
        self.archive_root = Path(archive_root).resolve()
        self.factory_ref = factory_ref
        self.timeout_seconds = timeout_seconds
        if not (self.generator_root / "web/package.json").is_file():
            raise ValueError(f"generator root lacks the Pages factory: {self.generator_root}")

    def _run(
        self,
        command: list[str],
        *,
        cwd: Path | None = None,
        input_text: str | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                input=input_text,
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise GitHubProvisionError(f"command failed to execute: {command[0]} {command[1:2]}") from exc
        if check and result.returncode != 0:
            raise GitHubProvisionError(
                f"command failed ({result.returncode}): {command[0]} {command[1:2]}: {result.stderr.strip()}"
            )
        return result

    def _slug(self, repository: str) -> str:
        if not re.fullmatch(r"Wirtelprimpf-\d{4}", repository):
            raise ValueError(f"invalid archive repository: {repository!r}")
        return f"{self.owner}/{repository}"

    def _view(self, repository: str) -> dict[str, Any] | None:
        result = self._run(
            [
                "gh",
                "repo",
                "view",
                self._slug(repository),
                "--json",
                "databaseId,name,description,isPrivate,defaultBranchRef,url",
            ],
            check=False,
        )
        if result.returncode != 0:
            stderr = result.stderr.lower()
            if "not found" in stderr or "could not resolve" in stderr or "graphql: could not resolve" in stderr:
                return None
            raise GitHubProvisionError(f"cannot inspect repository {self._slug(repository)}: {result.stderr.strip()}")
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise GitHubProvisionError(f"invalid repository metadata for {repository}") from exc
        return payload if isinstance(payload, dict) else None

    @staticmethod
    def _marker(transaction_id: str) -> str:
        return f"Wirtelprimpf publication archive; provision-transaction={transaction_id}"

    def reserve_repository(self, repository: str, *, transaction_id: str) -> None:
        existing = self._view(repository)
        if existing is None:
            return
        if existing.get("description") == self._marker(transaction_id) and existing.get("isPrivate") is False:
            return
        raise GitHubProvisionError(
            f"repository {self._slug(repository)} already exists without this transaction marker; refusing reuse"
        )

    def ensure_repository(self, repository: str, *, transaction_id: str) -> int:
        existing = self._view(repository)
        marker = self._marker(transaction_id)
        if existing is None:
            self._run(
                [
                    "gh",
                    "repo",
                    "create",
                    self._slug(repository),
                    "--public",
                    "--add-readme",
                    "--description",
                    marker,
                    "--disable-wiki",
                ]
            )
            existing = self._view(repository)
        if existing is None or existing.get("description") != marker or existing.get("isPrivate") is not False:
            raise GitHubProvisionError(f"repository creation cannot be verified: {self._slug(repository)}")
        database_id = existing.get("databaseId")
        if not isinstance(database_id, int):
            raise GitHubProvisionError(f"repository has no numeric database ID: {self._slug(repository)}")
        return database_id

    def _checkout_path(self, repository: str) -> Path:
        path = self.archive_root / repository
        if path.is_symlink():
            raise GitHubProvisionError(f"archive checkout path must not be a symlink: {path}")
        return path

    def ensure_local_checkout(self, repository: str) -> str:
        path = self._checkout_path(repository)
        self.archive_root.mkdir(parents=True, exist_ok=True)
        if (path / ".git").is_dir():
            status = self._run(["git", "status", "--porcelain"], cwd=path)
            if status.stdout.strip():
                raise GitHubProvisionError(f"archive checkout is dirty: {path}")
            self._run(["git", "fetch", "--prune", "origin"], cwd=path)
            self._run(["git", "switch", "main"], cwd=path)
            self._run(["git", "pull", "--ff-only", "origin", "main"], cwd=path)
        else:
            if path.exists() and any(path.iterdir()):
                raise GitHubProvisionError(f"archive checkout target is non-empty: {path}")
            self._run(["gh", "repo", "clone", self._slug(repository), str(path)])
        revision = self._run(["git", "rev-parse", "HEAD"], cwd=path).stdout.strip()
        if not re.fullmatch(r"[0-9a-f]{40}", revision):
            raise GitHubProvisionError(f"cannot verify archive checkout revision: {path}")
        return revision

    def initialize_archive(self, repository: str, *, archive_index: int, domain: str) -> str:
        if repository != archive_name(archive_index) or domain != archive_domain(archive_index):
            raise GitHubProvisionError("archive initialization violates naming/domain contract")
        path = self._checkout_path(repository)
        if not (path / ".git").is_dir():
            raise GitHubProvisionError(f"archive checkout is missing: {path}")
        volume_start = ((archive_index - 1) * ARCHIVE_CAPACITY) + 1
        volume_end = volume_start + ARCHIVE_CAPACITY - 1
        book_start = ((volume_start - 1) // STORIES_PER_BOOK) + 1
        book_end = ((volume_end - 1) // STORIES_PER_BOOK) + 1
        archive_manifest = {
            "archive_index": archive_index,
            "book_end": book_end,
            "book_start": book_start,
            "domain": domain,
            "repository": repository,
            "schema_version": "1.0.0",
            "status": "active",
            "stories_per_book": STORIES_PER_BOOK,
            "story_end": volume_end,
            "story_start": volume_start,
            "volume_end": volume_end,
            "volume_start": volume_start,
        }
        media_manifest = {
            "archive_index": archive_index,
            "archive_repository": repository,
            "media": [],
            "media_count": 0,
            "schema_version": "1.0.0",
            "shards": [],
        }
        workflow = f'''name: Publish Wirtelprimpf archive Pages

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  publish:
    uses: {self.owner}/Wirtelprimpf-generator/.github/workflows/archive-pages.yml@{self.factory_ref}
    with:
      archive_index: "{archive_index}"
      custom_domain: "{domain}"
      factory_ref: "{self.factory_ref}"
'''
        readme = f"""# {repository}

Publikationsarchiv für die globalen Wirtelprimpf-Storys {volume_start} bis {volume_end}
beziehungsweise die Bücher {book_start} bis {book_end}. Je zehn vollständig abgeschlossene Storys bilden ein Buch.

- Website: <https://{domain}>
- Zentrale: <https://wirtelprimpf.telacore.org>
- Generator und Seitenfabrik: <https://github.com/{self.owner}/Wirtelprimpf-generator>

Dieses Repository enthält Publikationsdaten und Manifeste. Ausführbarer Generator-, Applet-, Admin- und
Webquellcode wird ausschließlich im Generatorrepository gepflegt. Originalbilder liegen in hashverifizierten
GitHub Releases; `main` enthält kleine, reviewbare Verweise und Storytexte.
"""
        _atomic_text(path / "README.md", readme)
        _atomic_text(
            path / "archive-manifest.json",
            json.dumps(archive_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )
        _atomic_text(
            path / "media-manifest.json",
            json.dumps(media_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )
        _atomic_text(path / ".gitignore", ARCHIVE_GITIGNORE)
        _atomic_text(path / ".github/workflows/pages.yml", workflow)
        _atomic_text(path / ".nojekyll", "")
        source_license = self.generator_root / "LICENSE"
        if source_license.is_file() and not (path / "LICENSE").exists():
            shutil.copyfile(source_license, path / "LICENSE")
        tracked = [
            "README.md",
            "LICENSE",
            "archive-manifest.json",
            "media-manifest.json",
            ".gitignore",
            ".github/workflows/pages.yml",
            ".nojekyll",
        ]
        self._run(["git", "add", "--", *tracked], cwd=path)
        status = self._run(["git", "status", "--porcelain", "--", *tracked], cwd=path)
        if status.stdout.strip():
            self._run(
                [
                    "git",
                    "-c",
                    "user.name=Wirtelprimpf Bot",
                    "-c",
                    "user.email=wirtelprimpf@example.invalid",
                    "commit",
                    "-m",
                    f"feat: initialize publication archive {archive_index:04d}",
                    "--",
                    *tracked,
                ],
                cwd=path,
            )
            self._run(["git", "push", "origin", "main"], cwd=path)
        revision = self._run(["git", "rev-parse", "HEAD"], cwd=path).stdout.strip()
        if not re.fullmatch(r"[0-9a-f]{40}", revision):
            raise GitHubProvisionError("archive initialization revision is invalid")
        return revision

    def _api(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        command = ["gh", "api", "--method", method, path]
        input_text = None
        if payload is not None:
            command.extend(["--input", "-"])
            input_text = json.dumps(payload, separators=(",", ":"))
        return self._run(command, input_text=input_text, check=check)

    def ensure_pages(self, repository: str, *, domain: str) -> None:
        if domain != archive_domain(int(repository.rsplit("-", 1)[-1])):
            raise GitHubProvisionError("Pages domain violates archive contract")
        endpoint = f"repos/{self._slug(repository)}/pages"
        current = self._api("GET", endpoint, check=False)
        if current.returncode != 0:
            created = self._api("POST", endpoint, {"build_type": "workflow"}, check=False)
            if created.returncode != 0:
                raise GitHubProvisionError(f"cannot create Pages site for {repository}: {created.stderr.strip()}")
        updated = self._api("PUT", endpoint, {"build_type": "workflow", "cname": domain}, check=False)
        if updated.returncode != 0:
            raise GitHubProvisionError(f"cannot configure Pages domain for {repository}: {updated.stderr.strip()}")

    def verify_pages_and_enable_https(self, repository: str, *, domain: str) -> bool:
        endpoint = f"repos/{self._slug(repository)}/pages"
        result = self._api("GET", endpoint, check=False)
        if result.returncode != 0:
            return False
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            return False
        if payload.get("cname") != domain or payload.get("protected_domain_state") != "verified":
            return False
        if payload.get("status") not in {"built", None}:
            return False
        request = Request(f"https://{domain}/", headers={"User-Agent": "Wirtelprimpf-generator/1.0"})
        try:
            with urlopen(request, timeout=30) as response:
                if response.status != 200:
                    return False
        except (HTTPError, URLError, OSError):
            return False
        if payload.get("https_enforced") is not True:
            update = self._api("PUT", endpoint, {"https_enforced": True}, check=False)
            if update.returncode != 0:
                return False
        verified = self._api("GET", endpoint, check=False)
        if verified.returncode != 0:
            return False
        try:
            return json.loads(verified.stdout).get("https_enforced") is True
        except json.JSONDecodeError:
            return False
