#!/usr/bin/env python3
"""Build a small, deterministic EPUB from a Wirtelprimpf story Markdown file."""

from __future__ import annotations

import argparse
import html
import re
import sys
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path


EPUB_MIME = "application/epub+zip"
_CHAPTER_RE = re.compile(r"^## (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s*$", re.MULTILINE)
_INVALID_XML = re.compile(r"[^\x09\x0A\x0D\x20-\uD7FF\uE000-\uFFFD]")


@dataclass(frozen=True)
class Chapter:
    timestamp: str
    paragraphs: tuple[str, ...]


def _clean_text(value: str) -> str:
    return _INVALID_XML.sub("", value.replace("\r\n", "\n").replace("\r", "\n"))


def _escape(value: str) -> str:
    return html.escape(_clean_text(value), quote=False)


def _title_and_body(markdown: str, volume: int, title: str | None) -> tuple[str, str]:
    text = _clean_text(markdown).strip() + "\n"
    if title:
        return title.strip(), text
    match = re.match(r"^#\s+(.+?)\s*\n", text)
    if match:
        return match.group(1), text[match.end():]
    return f"Wirtelprimpf \u00b7 Story {volume}", text


def parse_story(markdown: str, volume: int, title: str | None = None) -> tuple[str, tuple[Chapter, ...]]:
    if not isinstance(volume, int) or volume < 1:
        raise ValueError("volume must be a positive integer")
    story_title, body = _title_and_body(markdown, volume, title)
    matches = list(_CHAPTER_RE.finditer(body))
    if not matches:
        raise ValueError("story Markdown contains no timestamped ## chapters")

    chapters: list[Chapter] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        raw_content = body[match.end():end].strip()
        paragraphs = tuple(
            " ".join(line.strip() for line in block.splitlines() if line.strip())
            for block in re.split(r"\n\s*\n", raw_content)
            if block.strip()
        )
        chapters.append(Chapter(match.group(1), paragraphs))
    return story_title.strip(), tuple(chapters)


def _chapter_xhtml(title: str, chapter: Chapter) -> str:
    paragraphs = "\n".join(f"    <p>{_escape(paragraph)}</p>" for paragraph in chapter.paragraphs)
    return f'''<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="de" xml:lang="de">
  <head>
    <title>{_escape(title)} - {_escape(chapter.timestamp)}</title>
    <link rel="stylesheet" type="text/css" href="styles.css" />
  </head>
  <body>
    <main epub:type="bodymatter">
      <h1>{_escape(chapter.timestamp)}</h1>
{paragraphs}
    </main>
  </body>
</html>
'''


def _nav_xhtml(title: str, chapters: tuple[Chapter, ...]) -> str:
    items = "\n".join(
        f'        <li><a href="chapter-{index:03d}.xhtml">{_escape(chapter.timestamp)}</a></li>'
        for index, chapter in enumerate(chapters, start=1)
    )
    return f'''<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="de" xml:lang="de">
  <head><title>{_escape(title)} - Inhaltsverzeichnis</title></head>
  <body>
    <nav epub:type="toc" id="toc" role="doc-toc">
      <h1>{_escape(title)}</h1>
      <ol>
{items}
      </ol>
    </nav>
  </body>
</html>
'''


def _package_opf(title: str, volume: int, chapters: tuple[Chapter, ...]) -> str:
    chapter_manifest = "\n".join(
        f'    <item id="chapter-{index:03d}" href="chapter-{index:03d}.xhtml" media-type="application/xhtml+xml" />'
        for index in range(1, len(chapters) + 1)
    )
    spine = "\n".join(
        f'    <itemref idref="chapter-{index:03d}" />'
        for index in range(1, len(chapters) + 1)
    )
    return f'''<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="book-id" version="3.0" xml:lang="de">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="book-id">urn:wirtelprimpf:story:{volume}</dc:identifier>
    <dc:title>{_escape(title)}</dc:title>
    <dc:language>de</dc:language>
    <meta property="dcterms:modified">2000-01-01T00:00:00Z</meta>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav" />
    <item id="styles" href="styles.css" media-type="text/css" />
{chapter_manifest}
  </manifest>
  <spine>
{spine}
  </spine>
</package>
'''


def _write_entry(archive: zipfile.ZipFile, name: str, content: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=(2000, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.external_attr = 0o644 << 16
    info.compress_type = zipfile.ZIP_STORED
    archive.writestr(info, content)


def build_epub_bytes(markdown: str, volume: int, title: str | None = None) -> bytes:
    story_title, chapters = parse_story(markdown, volume, title)
    entries: list[tuple[str, bytes]] = [
        ("mimetype", EPUB_MIME.encode("ascii")),
        (
            "META-INF/container.xml",
            b'''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/package.opf" media-type="application/oebps-package+xml" />
  </rootfiles>
</container>
''',
        ),
        ("OEBPS/package.opf", _package_opf(story_title, volume, chapters).encode("utf-8")),
        ("OEBPS/nav.xhtml", _nav_xhtml(story_title, chapters).encode("utf-8")),
        (
            "OEBPS/styles.css",
            b"body { font-family: serif; line-height: 1.55; margin: 5%; }\n"
            b"h1 { font-size: 1.4em; }\n",
        ),
    ]
    entries.extend(
        (
            f"OEBPS/chapter-{index:03d}.xhtml",
            _chapter_xhtml(story_title, chapter).encode("utf-8"),
        )
        for index, chapter in enumerate(chapters, start=1)
    )
    output = BytesIO()
    with zipfile.ZipFile(output, "w", allowZip64=False) as archive:
        for name, content in entries:
            _write_entry(archive, name, content)
    return output.getvalue()


def build_epub(source: Path, output: Path, volume: int, title: str | None = None) -> int:
    data = source.read_text(encoding="utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(build_epub_bytes(data, volume, title))
    return output.stat().st_size


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--story", type=Path, required=True, help="story Markdown source")
    parser.add_argument("--volume", type=int, required=True, help="positive story volume number")
    parser.add_argument("--output", type=Path, required=True, help="EPUB output path")
    parser.add_argument("--title", help="override the title derived from the Markdown")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        size = build_epub(args.story, args.output, args.volume, args.title)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(f"build_epub: {error}", file=sys.stderr)
        return 2
    print(f"{args.output} ({size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
