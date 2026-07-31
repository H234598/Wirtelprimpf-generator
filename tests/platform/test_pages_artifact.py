from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.validate_pages_artifact import ArtifactError, validate_artifact


class PagesArtifactTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "bilder").mkdir()
        (self.root / "index.html").write_text(
            '<!doctype html><html><head><link rel="canonical" href="https://wirtelprimpf.telacore.org/"></head>'
            '<body><a href="/bilder/">Bilder</a></body></html>',
            encoding="utf-8",
        )
        (self.root / "bilder" / "index.html").write_text(
            '<!doctype html><html><head><link rel="canonical" href="https://wirtelprimpf.telacore.org/bilder/">'
            '</head><body><a href="/">Start</a></body></html>',
            encoding="utf-8",
        )
        for name, content in (
            ("404.html", "<!doctype html><title>404</title>"),
            ("robots.txt", "User-agent: *\n"),
            ("sitemap.xml", "<?xml version=\"1.0\"?><urlset></urlset>"),
            ("feed.xml", "<?xml version=\"1.0\"?><feed></feed>"),
        ):
            (self.root / name).write_text(content, encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_valid_artifact_passes_with_deterministic_tree_hash(self) -> None:
        first = validate_artifact(self.root, expected_domain="wirtelprimpf.telacore.org")
        second = validate_artifact(self.root, expected_domain="wirtelprimpf.telacore.org")
        self.assertEqual(first.tree_sha256, second.tree_sha256)
        self.assertEqual(first.file_count, 6)

    def test_secret_and_local_absolute_path_are_blocking(self) -> None:
        (self.root / "leak.js").write_text(
            'const key="sk-proj-abcdefghijklmnopqrstuv"; const path="/home/teladi/private";',
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ArtifactError, "secret-like|local absolute"):
            validate_artifact(self.root, expected_domain="wirtelprimpf.telacore.org")

    def test_broken_internal_link_is_blocking(self) -> None:
        path = self.root / "index.html"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "</body>",
                '<a href="/nicht-da/">kaputt</a></body>',
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ArtifactError, "broken internal link"):
            validate_artifact(self.root, expected_domain="wirtelprimpf.telacore.org")

    def test_wrong_canonical_domain_is_blocking(self) -> None:
        path = self.root / "index.html"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "wirtelprimpf.telacore.org",
                "wrong.invalid",
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ArtifactError, "canonical"):
            validate_artifact(self.root, expected_domain="wirtelprimpf.telacore.org")

    def test_symlink_is_blocking(self) -> None:
        outside = Path(self.temp.name).parent / "outside-pages-file"
        outside.write_text("outside", encoding="utf-8")
        try:
            (self.root / "escape").symlink_to(outside)
            with self.assertRaisesRegex(ArtifactError, "symlink"):
                validate_artifact(self.root, expected_domain="wirtelprimpf.telacore.org")
        finally:
            outside.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
