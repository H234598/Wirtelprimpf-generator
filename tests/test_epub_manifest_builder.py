from __future__ import annotations

import json
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_epub import build_epub_bytes  # noqa: E402
from build_epub_manifest import EpubManifestError, build_manifest  # noqa: E402


STORY = "## 2026-08-06 12:34:56\n\nEin gepruefter Teil.\n"


class EpubManifestBuilderTests(unittest.TestCase):
    def test_manifest_requires_matching_verified_release_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "story-0001.epub"
            source.write_bytes(build_epub_bytes(STORY, 1))
            inventory = root / "inventory.json"
            inventory.write_text(json.dumps({"schema_version": "1.0.0", "assets": []}), encoding="utf-8")
            with self.assertRaisesRegex(EpubManifestError, "missing verified"):
                build_manifest(
                    [(1, source)],
                    owner="H234598",
                    repository="Wirtelprimpf-0001",
                    release_tag="archive-0001-epub-0001",
                    inventory_path=inventory,
                )

    def test_manifest_is_deterministic_and_keeps_local_files_inside_data_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data_root = root / "data"
            data_root.mkdir()
            source = data_root / "story-0001.epub"
            source.write_bytes(build_epub_bytes(STORY, 1))
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            inventory = root / "inventory.json"
            inventory.write_text(json.dumps({
                "schema_version": "1.0.0",
                "assets": [{
                    "asset_name": source.name,
                    "header_verified": True,
                    "mime_type": "application/epub+zip",
                    "release_asset_verified": True,
                    "release_tag": "archive-0001-epub-0001",
                    "sha256": digest,
                    "size_bytes": source.stat().st_size,
                }],
            }), encoding="utf-8")
            first = build_manifest(
                [(1, source)], owner="H234598", repository="Wirtelprimpf-0001",
                release_tag="archive-0001-epub-0001", inventory_path=inventory, data_root=data_root,
            )
            second = build_manifest(
                [(1, source)], owner="H234598", repository="Wirtelprimpf-0001",
                release_tag="archive-0001-epub-0001", inventory_path=inventory, data_root=data_root,
            )
            self.assertEqual(first, second)
            item = first["downloads"][0]
            self.assertEqual(item["local_path"], source.name)
            self.assertTrue(item["url"].endswith("/archive-0001-epub-0001/story-0001.epub"))

    def test_manifest_rejects_changed_local_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "story-0001.epub"
            source.write_bytes(build_epub_bytes(STORY, 1))
            inventory = root / "inventory.json"
            inventory.write_text(json.dumps({
                "schema_version": "1.0.0",
                "assets": [{
                    "asset_name": source.name,
                    "header_verified": True,
                    "mime_type": "application/epub+zip",
                    "release_asset_verified": True,
                    "release_tag": "archive-0001-epub-0001",
                    "sha256": "0" * 64,
                    "size_bytes": source.stat().st_size,
                }],
            }), encoding="utf-8")
            with self.assertRaisesRegex(EpubManifestError, "differs"):
                build_manifest(
                    [(1, source)], owner="H234598", repository="Wirtelprimpf-0001",
                    release_tag="archive-0001-epub-0001", inventory_path=inventory,
                )


if __name__ == "__main__":
    unittest.main()
