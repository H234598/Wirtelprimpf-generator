from __future__ import annotations

import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from wirtelprimpf_platform.media import (
    MediaError,
    build_media_inventory,
    build_release_plan,
    materialize_release_plan,
    publish_release_plan,
)


def png_bytes(width: int, height: int, color: tuple[int, int, int]) -> bytes:
    stream = io.BytesIO()
    Image.new("RGB", (width, height), color).save(stream, format="PNG")
    return stream.getvalue()


class MemoryReleaseBackend:
    def __init__(self) -> None:
        self.releases: dict[str, dict[str, bytes]] = {}
        self.uploads: list[tuple[str, str]] = []
        self.downloads: list[tuple[str, str]] = []

    def ensure_release(self, tag: str, *, title: str, notes: str) -> None:
        del title, notes
        self.releases.setdefault(tag, {})

    def asset_names(self, tag: str) -> set[str]:
        return set(self.releases.get(tag, {}))

    def upload_asset(self, tag: str, path: Path) -> None:
        self.releases.setdefault(tag, {})[path.name] = path.read_bytes()
        self.uploads.append((tag, path.name))

    def download_asset(self, tag: str, asset_name: str, destination: Path) -> None:
        self.downloads.append((tag, asset_name))
        destination.write_bytes(self.releases[tag][asset_name])


class MediaReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "Wirtelprimpf"
        self.source.mkdir()
        fixtures = (
            ("wirtelprimpf_2026-01-01_12-00-00-000001_story-01", (80, 40), (240, 100, 90)),
            ("wirtelprimpf_2026-01-02_12-00-00-000002_geburtstag-01", (90, 60), (90, 180, 130)),
            ("historisch-ohne-paarung", (70, 70), (100, 120, 210)),
        )
        for stem, size, color in fixtures:
            (self.source / f"{stem}.png").write_bytes(png_bytes(*size, color))
        (self.source / "wirtelprimpf_2026-01-01_12-00-00-000001_story-01.md").write_text(
            "## 2026-01-01 12:00:00\n\nStory.\n", encoding="utf-8"
        )
        (self.source / "wirtelprimpf_2026-01-01_12-00-00-000001_story-01.txt").write_text(
            "Prompt.\n", encoding="utf-8"
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_inventory_is_deterministic_and_classifies_without_inventing_relations(self) -> None:
        first = build_media_inventory(self.source, archive_index=1)
        second = build_media_inventory(self.source, archive_index=1)

        self.assertEqual(first, second)
        self.assertEqual(len(first.records), 3)
        by_path = {record.source_path: record for record in first.records}
        story = by_path["wirtelprimpf_2026-01-01_12-00-00-000001_story-01.png"]
        birthday = by_path["wirtelprimpf_2026-01-02_12-00-00-000002_geburtstag-01.png"]
        legacy = by_path["historisch-ohne-paarung.png"]
        self.assertEqual(story.kind, "story")
        self.assertEqual(story.story_part_path, story.source_path.removesuffix(".png") + ".md")
        self.assertEqual(birthday.kind, "classic")
        self.assertEqual(legacy.kind, "legacy")
        self.assertIsNone(legacy.story_part_path)
        self.assertEqual(story.sha256, hashlib.sha256((self.source / story.source_path).read_bytes()).hexdigest())

    def test_release_plan_shards_below_asset_limit_and_uses_hash_bound_urls(self) -> None:
        inventory = build_media_inventory(self.source, archive_index=1)
        plan = build_release_plan(
            inventory,
            owner="H234598",
            repository="Wirtelprimpf-0001",
            max_originals_per_shard=2,
        )

        self.assertEqual([shard.tag for shard in plan.shards], [
            "archive-0001-media-0001",
            "archive-0001-media-0002",
        ])
        self.assertEqual([len(shard.records) for shard in plan.shards], [2, 1])
        for shard in plan.shards:
            self.assertLess(len(shard.assets), 1_000)
            for record in shard.records:
                self.assertIn(record.sha256[:16], record.original_asset_name)
                self.assertIn(f"/releases/download/{shard.tag}/", record.original_url)
                self.assertEqual({variant.width for variant in record.variants}, {640, 1280})

    def test_materialization_strips_metadata_and_publisher_reverifies_every_download(self) -> None:
        inventory = build_media_inventory(self.source, archive_index=1)
        plan = build_release_plan(
            inventory,
            owner="H234598",
            repository="Wirtelprimpf-0001",
            max_originals_per_shard=2,
        )
        prepared = materialize_release_plan(plan, source_root=self.source, staging_root=self.root / "staging")
        backend = MemoryReleaseBackend()

        report = publish_release_plan(prepared, backend=backend)

        self.assertEqual(report.expected_assets, report.uploaded_assets)
        self.assertEqual(report.expected_assets, report.verified_assets)
        self.assertEqual(len(backend.downloads), report.expected_assets)
        manifest = json.loads(prepared.manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["archive_repository"], "Wirtelprimpf-0001")
        self.assertEqual(len(manifest["media"]), 3)
        self.assertTrue(all(shard["open"] is False for shard in manifest["shards"]))
        self.assertEqual([shard["record_count"] for shard in manifest["shards"]], [2, 1])
        for shard in prepared.shards:
            self.assertTrue(shard.bundle_path.is_file())
            self.assertLess(shard.asset_count, 1_000)

    def test_existing_hash_mismatch_is_fail_closed_and_never_overwritten(self) -> None:
        inventory = build_media_inventory(self.source, archive_index=1)
        plan = build_release_plan(
            inventory,
            owner="H234598",
            repository="Wirtelprimpf-0001",
            max_originals_per_shard=2,
        )
        prepared = materialize_release_plan(plan, source_root=self.source, staging_root=self.root / "staging")
        backend = MemoryReleaseBackend()
        first = prepared.shards[0]
        backend.ensure_release(first.tag, title="", notes="")
        first_asset = first.asset_paths[0]
        backend.releases[first.tag][first_asset.name] = b"corrupt remote object"

        with self.assertRaisesRegex(MediaError, "hash mismatch"):
            publish_release_plan(prepared, backend=backend)

        self.assertEqual(backend.releases[first.tag][first_asset.name], b"corrupt remote object")
        self.assertNotIn((first.tag, first_asset.name), backend.uploads)

    def test_modified_source_after_inventory_is_rejected_before_staging(self) -> None:
        inventory = build_media_inventory(self.source, archive_index=1)
        plan = build_release_plan(
            inventory,
            owner="H234598",
            repository="Wirtelprimpf-0001",
        )
        changed = self.source / plan.shards[0].records[0].source_path
        changed.write_bytes(png_bytes(10, 10, (0, 0, 0)))

        with self.assertRaisesRegex(MediaError, "changed after inventory"):
            materialize_release_plan(plan, source_root=self.source, staging_root=self.root / "staging")

    def test_source_symlink_is_rejected(self) -> None:
        if not hasattr(Path, "symlink_to"):
            self.skipTest("symlinks unavailable")
        outside = self.root / "outside.png"
        outside.write_bytes(png_bytes(10, 10, (1, 2, 3)))
        (self.source / "escape.png").symlink_to(outside)

        with self.assertRaisesRegex(MediaError, "symlink"):
            build_media_inventory(self.source, archive_index=1)


if __name__ == "__main__":
    unittest.main()
