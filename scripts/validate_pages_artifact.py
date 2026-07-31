#!/usr/bin/env python3
"""Fail-closed validator for Wirtelprimpf GitHub Pages artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

MAX_ARTIFACT_BYTES = 850 * 1024 * 1024
MAX_SINGLE_FILE_BYTES = 12 * 1024 * 1024
REQUIRED_PATHS = ("index.html", "404.html", "robots.txt", "sitemap.xml", "feed.xml")
TEXT_SUFFIXES = {".html", ".css", ".js", ".json", ".xml", ".txt", ".svg", ".map"}
SECRET_PATTERNS = (
    re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"(?:CLOUDFLARE_API_TOKEN|OPENAI_API_KEY|GH_TOKEN)\s*[:=]\s*['\"]?[A-Za-z0-9._-]{12,}"),
)
LOCAL_PATH_PATTERNS = (
    re.compile(r"/(?:home|root)/[A-Za-z0-9._/-]+"),
    re.compile(r"[A-Za-z]:\\Users\\", re.IGNORECASE),
)


class ArtifactError(RuntimeError):
    """The Pages tree violates a publication safety contract."""


@dataclass(frozen=True, slots=True)
class ArtifactReport:
    root: str
    file_count: int
    total_bytes: int
    html_count: int
    internal_links_checked: int
    tree_sha256: str


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.canonicals: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag in {"a", "link", "script", "img", "source"}:
            for key in ("href", "src"):
                if values.get(key):
                    self.links.append(values[key] or "")
        if tag == "link" and values.get("rel", "").lower() == "canonical" and values.get("href"):
            self.canonicals.append(values["href"] or "")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _internal_target(root: Path, source: Path, raw_link: str) -> Path | None:
    if not raw_link or raw_link.startswith(("#", "mailto:", "tel:", "data:")):
        return None
    parsed = urlsplit(raw_link)
    if parsed.scheme or parsed.netloc:
        return None
    decoded = unquote(parsed.path)
    if not decoded:
        return None
    pure = PurePosixPath(decoded)
    if ".." in pure.parts:
        raise ArtifactError(f"internal link contains traversal in {source.relative_to(root)}: {raw_link}")
    candidate = root.joinpath(*pure.parts[1:]) if decoded.startswith("/") else source.parent.joinpath(*pure.parts)
    if decoded.endswith("/"):
        candidate /= "index.html"
    elif not candidate.suffix:
        directory_index = candidate / "index.html"
        if directory_index.exists():
            candidate = directory_index
    try:
        candidate.resolve(strict=False).relative_to(root)
    except ValueError as exc:
        raise ArtifactError(f"internal link escaped artifact: {raw_link}") from exc
    return candidate


def validate_artifact(root: Path, *, expected_domain: str) -> ArtifactReport:
    artifact = Path(root)
    if artifact.is_symlink() or not artifact.is_dir():
        raise ArtifactError(f"artifact root must be a non-symlink directory: {artifact}")
    artifact = artifact.resolve()
    if not re.fullmatch(r"[a-z0-9-]+(?:\.[a-z0-9-]+)+", expected_domain):
        raise ArtifactError(f"invalid expected domain: {expected_domain!r}")
    for required in REQUIRED_PATHS:
        if not (artifact / required).is_file():
            raise ArtifactError(f"required Pages file is missing: {required}")

    files: list[Path] = []
    for directory, names, filenames in os.walk(artifact, followlinks=False):
        current = Path(directory)
        for name in names:
            candidate = current / name
            if candidate.is_symlink():
                raise ArtifactError(f"artifact contains symlink directory: {candidate.relative_to(artifact)}")
        for name in filenames:
            candidate = current / name
            if candidate.is_symlink():
                raise ArtifactError(f"artifact contains symlink: {candidate.relative_to(artifact)}")
            if not candidate.is_file():
                raise ArtifactError(f"artifact contains non-regular file: {candidate.relative_to(artifact)}")
            files.append(candidate)
    files.sort(key=lambda path: path.relative_to(artifact).as_posix())

    total = 0
    html_count = 0
    internal_links = 0
    tree = hashlib.sha256()
    for path in files:
        relative = path.relative_to(artifact).as_posix()
        size = path.stat().st_size
        if size > MAX_SINGLE_FILE_BYTES:
            raise ArtifactError(f"single-file budget exceeded: {relative} ({size} bytes)")
        total += size
        if total > MAX_ARTIFACT_BYTES:
            raise ArtifactError(f"artifact budget exceeded: {total} bytes")
        digest = _sha256(path)
        tree.update(
            relative.encode("utf-8")
            + b"\0"
            + str(size).encode("ascii")
            + b"\0"
            + digest.encode("ascii")
            + b"\n"
        )
        if path.suffix == ".map":
            raise ArtifactError(f"source map must not be published: {relative}")
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ArtifactError(f"text artifact is not UTF-8: {relative}") from exc
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                raise ArtifactError(f"secret-like material found in artifact: {relative}")
        for pattern in LOCAL_PATH_PATTERNS:
            if pattern.search(text):
                raise ArtifactError(f"local absolute path found in artifact: {relative}")
        if path.suffix.lower() != ".html":
            continue
        html_count += 1
        parser = _Links()
        parser.feed(text)
        if path.name == "index.html":
            expected_prefix = f"https://{expected_domain}/"
            if len(parser.canonicals) != 1 or not parser.canonicals[0].startswith(expected_prefix):
                raise ArtifactError(f"canonical domain mismatch in {relative}: {parser.canonicals}")
        for link in parser.links:
            target = _internal_target(artifact, path, link)
            if target is None:
                continue
            internal_links += 1
            if not target.is_file():
                raise ArtifactError(f"broken internal link in {relative}: {link}")

    return ArtifactReport(
        root=str(artifact),
        file_count=len(files),
        total_bytes=total,
        html_count=html_count,
        internal_links_checked=internal_links,
        tree_sha256=tree.hexdigest(),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--expected-domain", required=True)
    args = parser.parse_args()
    try:
        report = validate_artifact(args.root, expected_domain=args.expected_domain)
    except ArtifactError as exc:
        parser.exit(2, f"Pages artifact rejected: {exc}\n")
    print(json.dumps(asdict(report), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
