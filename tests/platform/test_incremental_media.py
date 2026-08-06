from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from wirtelprimpf_platform.incremental_media import IncrementalMediaPublisher


class MemoryBackend:
    def __init__(self) -> None:
        self.assets: dict[str, dict[str, bytes]] = {}
        self.upload_count = 0

    def ensure_release(self, tag: str, *, title: str, notes: str) -> None:
        del title, notes
        self.assets.setdefault(tag, {})

    def asset_names(self, tag: str) -> set[str]:
        return set(self.assets.get(tag, {}))

    def upload_asset(self, tag: str, path: Path) -> None:
        self.assets[tag][path.name] = path.read_bytes()
        self.upload_count += 1

    def download_asset(self, tag: str, asset_name: str, destination: Path) -> None:
        destination.write_bytes(self.assets[tag][asset_name])


def write_png(path: Path) -> None:
    Image.new("RGB", (1280, 720), (210, 130, 75)).save(path, format="PNG")


class IncrementalMediaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.image = self.root / "wirtelprimpf_2026-07-31_23-00-00-000001_story-01.png"
        write_png(self.image)
        self.manifest = self.root / "archive" / "media-manifest.json"
        self.backend = MemoryBackend()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def publisher(self, *, max_records_per_shard: int = 199) -> IncrementalMediaPublisher:
        return IncrementalMediaPublisher(
            owner="H234598",
            repository="Wirtelprimpf-0001",
            archive_index=1,
            manifest_path=self.manifest,
            staging_root=self.root / "staging",
            backend=self.backend,
            max_records_per_shard=max_records_per_shard,
        )

    def test_new_image_is_published_as_original_three_derivatives_and_immutable_record_manifest(self) -> None:
        record = self.publisher().publish(
            self.image,
            source_path=f"Wirtelprimpf/{self.image.name}",
            kind="story",
            prompt_path=f"Wirtelprimpf/{self.image.stem}.txt",
            story_part_path=f"Wirtelprimpf/{self.image.stem}.md",
        )

        self.assertEqual(record["release_tag"], "archive-0001-media-0001")
        self.assertEqual(self.backend.upload_count, 5)
        self.assertEqual(len(self.backend.assets[record["release_tag"]]), 5)
        payload = json.loads(self.manifest.read_text(encoding="utf-8"))
        self.assertEqual(payload["media_count"], 1)
        self.assertEqual(payload["media"], [record])
        self.assertTrue(payload["shards"][0]["open"])
        self.assertEqual(payload["shards"][0]["record_count"], 1)

    def test_rerun_is_idempotent_and_does_not_upload_or_duplicate(self) -> None:
        first = self.publisher().publish(
            self.image,
            source_path=f"Wirtelprimpf/{self.image.name}",
            kind="story",
        )
        uploads = self.backend.upload_count

        second = self.publisher().publish(
            self.image,
            source_path=f"Wirtelprimpf/{self.image.name}",
            kind="story",
        )

        self.assertEqual(first, second)
        self.assertEqual(self.backend.upload_count, uploads)
        self.assertEqual(json.loads(self.manifest.read_text(encoding="utf-8"))["media_count"], 1)

    def test_unknown_test_image_is_published_and_retained(self) -> None:
        record = self.publisher().publish(
            self.image,
            source_path=f"Wirtelprimp/{self.image.name}",
            kind="unknown",
        )

        self.assertEqual(record["kind"], "unknown")
        self.assertEqual(json.loads(self.manifest.read_text(encoding="utf-8"))["media_count"], 1)

    def test_open_shard_rolls_over_before_asset_limit(self) -> None:
        first = self.publisher(max_records_per_shard=1).publish(
            self.image,
            source_path=f"Wirtelprimpf/{self.image.name}",
            kind="story",
        )
        second_image = self.root / "wirtelprimpf_2026-08-01_01-00-00-000001.png"
        write_png(second_image)

        second = self.publisher(max_records_per_shard=1).publish(
            second_image,
            source_path=f"Wirtelprimpf/{second_image.name}",
            kind="classic",
        )

        self.assertEqual(first["release_tag"], "archive-0001-media-0001")
        self.assertEqual(second["release_tag"], "archive-0001-media-0002")
        payload = json.loads(self.manifest.read_text(encoding="utf-8"))
        self.assertFalse(payload["shards"][0]["open"])
        self.assertTrue(payload["shards"][1]["open"])

    def test_preexisting_sealed_migration_shards_are_never_mutated(self) -> None:
        self.manifest.parent.mkdir(parents=True)
        self.manifest.write_text(json.dumps({
            "schema_version": "1.0.0",
            "archive_index": 1,
            "archive_repository": "Wirtelprimpf-0001",
            "media_count": 0,
            "media": [],
            "shards": [{"index": 1, "tag": "archive-0001-media-0001", "open": False, "record_count": 0}],
        }), encoding="utf-8")

        record = self.publisher().publish(
            self.image,
            source_path=f"Wirtelprimpf/{self.image.name}",
            kind="story",
        )

        self.assertEqual(record["release_tag"], "archive-0001-media-0002")


if __name__ == "__main__":
    unittest.main()
