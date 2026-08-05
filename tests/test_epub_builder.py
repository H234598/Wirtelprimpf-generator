from __future__ import annotations

import sys
import unittest
import zipfile
from io import BytesIO
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_epub import build_epub_bytes, parse_story  # noqa: E402


SAMPLE = """# Eine Teststory

## 2026-08-06 12:34:56

Ein Absatz mit <tag> und & Zeichen.

Ein zweiter Absatz.

## 2026-08-06 13:35:57

Der nächste Teil.
"""


class EpubBuilderTests(unittest.TestCase):
    def test_build_is_deterministic_and_starts_with_stored_mimetype(self) -> None:
        first = build_epub_bytes(SAMPLE, 7)
        second = build_epub_bytes(SAMPLE, 7)
        self.assertEqual(first, second)
        with zipfile.ZipFile(BytesIO(first)) as archive:
            infos = archive.infolist()
            self.assertEqual(infos[0].filename, "mimetype")
            self.assertEqual(infos[0].compress_type, zipfile.ZIP_STORED)
            self.assertEqual(archive.read("mimetype"), b"application/epub+zip")

    def test_package_navigation_and_chapter_content_are_complete(self) -> None:
        data = build_epub_bytes(SAMPLE, 7)
        with zipfile.ZipFile(BytesIO(data)) as archive:
            names = archive.namelist()
            self.assertEqual(names[0], "mimetype")
            self.assertIn("META-INF/container.xml", names)
            self.assertIn("OEBPS/package.opf", names)
            self.assertIn("OEBPS/nav.xhtml", names)
            self.assertIn("OEBPS/chapter-001.xhtml", names)
            self.assertIn("OEBPS/chapter-002.xhtml", names)
            chapter = archive.read("OEBPS/chapter-001.xhtml").decode("utf-8")
            self.assertIn("&lt;tag&gt; und &amp; Zeichen.", chapter)
            self.assertNotIn("<tag>", chapter)
            navigation = archive.read("OEBPS/nav.xhtml").decode("utf-8")
            self.assertIn('href="chapter-002.xhtml"', navigation)
            package = archive.read("OEBPS/package.opf").decode("utf-8")
            self.assertIn("urn:wirtelprimpf:story:7", package)
            self.assertIn("Eine Teststory", package)

    def test_title_fallback_and_invalid_sources_fail_closed(self) -> None:
        title, chapters = parse_story("## 2026-08-06 12:34:56\n\nText", 3)
        self.assertEqual(title, "Wirtelprimpf · Story 3")
        self.assertEqual(len(chapters), 1)
        empty = build_epub_bytes(
            "# Leer\n\n## 2026-08-06 12:34:56\n\n## 2026-08-06 13:35:57\n\nText",
            3,
        )
        with zipfile.ZipFile(BytesIO(empty)) as archive:
            self.assertIn("OEBPS/chapter-001.xhtml", archive.namelist())
            self.assertIn("OEBPS/chapter-002.xhtml", archive.namelist())
            self.assertNotIn("<p>", archive.read("OEBPS/chapter-001.xhtml").decode("utf-8"))
        with self.assertRaisesRegex(ValueError, "no timestamped"):
            build_epub_bytes("# Ohne Kapitel\n\nText", 3)
        with self.assertRaisesRegex(ValueError, "positive integer"):
            build_epub_bytes(SAMPLE, 0)


if __name__ == "__main__":
    unittest.main()
