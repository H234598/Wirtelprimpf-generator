from __future__ import annotations

import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from PIL import Image

from wirtelprimpf_platform.media import (
    GitHubReleaseBackend,
    DERIVATIVE_WIDTHS,
    MAX_SOURCE_BYTES,
    MAX_SOURCE_PIXELS,
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

    def test_timestamp_image_with_an_exact_markdown_sidecar_is_story_media(self) -> None:
        stem = "wirtelprimpf_2026-01-03_12-00-00-000003"
        (self.source / f"{stem}.png").write_bytes(png_bytes(100, 50, (40, 60, 80)))
        (self.source / f"{stem}.md").write_text("## 2026-01-03 12:00:00\n\nStory.\n", encoding="utf-8")

        inventory = build_media_inventory(self.source, archive_index=1)
        record = next(item for item in inventory.records if item.source_path == f"{stem}.png")

        self.assertEqual(record.kind, "story")
        self.assertEqual(record.story_part_path, f"{stem}.md")

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

    def test_exif_orientation_is_applied_and_private_metadata_is_removed(self) -> None:
        image_path = self.source / "wirtelprimpf_2026-01-04_12-00-00-000004_gps.jpg"
        image = Image.new("RGB", (20, 10), (30, 80, 140))
        exif = image.getexif()
        exif[274] = 6
        exif[34853] = {1: "N", 2: (51, 30, 0), 3: "E", 4: (7, 0, 0)}
        image.save(image_path, format="JPEG", exif=exif.tobytes())

        inventory = build_media_inventory(self.source, archive_index=1)
        record = next(item for item in inventory.records if item.source_path == image_path.name)
        self.assertEqual((record.width, record.height), (10, 20))
        plan = build_release_plan(inventory, owner="H234598", repository="Wirtelprimpf-0001")
        prepared = materialize_release_plan(plan, source_root=self.source, staging_root=self.root / "oriented-staging")
        prepared_record = next(item for shard in prepared.shards for item in shard.records if item.source_path == image_path.name)
        self.assertEqual(tuple(item.width for item in prepared_record.variants), DERIVATIVE_WIDTHS)

        variant_path = next(
            path
            for shard in prepared.shards
            for path in shard.asset_paths
            if path.name == prepared_record.variants[0].asset_name
        )
        with Image.open(variant_path) as derivative:
            self.assertEqual(derivative.size, (10, 20))
            self.assertEqual(len(derivative.getexif()), 0)
            self.assertNotIn("exif", derivative.info)
            self.assertNotIn("icc_profile", derivative.info)

    def test_truncated_image_is_rejected_without_an_absolute_path(self) -> None:
        truncated = self.source / "truncated.png"
        truncated.write_bytes(png_bytes(20, 20, (10, 20, 30))[:-12])

        with self.assertRaisesRegex(MediaError, "invalid image") as context:
            build_media_inventory(self.source, archive_index=1)

        self.assertNotIn(str(self.source), str(context.exception))
        self.assertIn("truncated.png", str(context.exception))

    def test_materialization_cache_hits_all_derivatives_on_unchanged_rerun(self) -> None:
        inventory = build_media_inventory(self.source, archive_index=1)
        plan = build_release_plan(
            inventory,
            owner="H234598",
            repository="Wirtelprimpf-0001",
            max_originals_per_shard=2,
        )
        first = materialize_release_plan(
            plan,
            source_root=self.source,
            staging_root=self.root / "staging-first",
            cache_root=self.root / "cache",
        )
        second = materialize_release_plan(
            plan,
            source_root=self.source,
            staging_root=self.root / "staging-second",
            cache_root=self.root / "cache",
        )

        self.assertEqual(first.cache_report["misses"], 6)
        self.assertEqual(second.cache_report["hits"], 6)
        self.assertEqual(second.cache_report["cache_hit_rate"], 1.0)
        self.assertEqual(
            [path.read_bytes() for shard in first.shards for path in shard.asset_paths],
            [path.read_bytes() for shard in second.shards for path in shard.asset_paths],
        )

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

    def test_github_backend_retries_transient_public_404_after_upload(self) -> None:
        destination = self.root / "downloaded.webp"
        attempts = 0
        transient_error = HTTPError(
            "https://example.invalid/asset.webp",
            404,
            "Not Found",
            hdrs=None,
            fp=io.BytesIO(),
        )

        def eventually_visible(request, *, timeout):
            nonlocal attempts
            del timeout
            attempts += 1
            if attempts == 1:
                transient_error.filename = request.full_url
                raise transient_error
            return io.BytesIO(b"public release asset")

        backend = GitHubReleaseBackend("H234598", "Wirtelprimpf-0001")
        failure = None
        with (
            patch("wirtelprimpf_platform.media.urlopen", side_effect=eventually_visible),
            patch("wirtelprimpf_platform.media.PUBLIC_DOWNLOAD_RETRY_DELAYS_SECONDS", (0.0,)),
        ):
            try:
                backend.download_asset("archive-0001-media-0001", "asset.webp", destination)
            except MediaError as exc:
                failure = exc

        self.assertIsNone(failure)
        self.assertEqual(destination.read_bytes(), b"public release asset")
        self.assertEqual(attempts, 2)
        self.assertTrue(transient_error.fp.closed)

    def test_github_backend_reconnects_after_a_stalled_public_read(self) -> None:
        destination = self.root / "downloaded.webp"
        observed_timeouts: list[float] = []

        def timeout_then_visible(request, *, timeout):
            del request
            observed_timeouts.append(timeout)
            if len(observed_timeouts) == 1:
                raise TimeoutError("public connection stopped delivering bytes")
            return io.BytesIO(b"public release asset")

        backend = GitHubReleaseBackend(
            "H234598",
            "Wirtelprimpf-0001",
            public_download_timeout_seconds=23.0,
        )
        failure = None
        with (
            patch("wirtelprimpf_platform.media.urlopen", side_effect=timeout_then_visible),
            patch("wirtelprimpf_platform.media.PUBLIC_DOWNLOAD_RETRY_DELAYS_SECONDS", (0.0,)),
        ):
            try:
                backend.download_asset("archive-0001-media-0001", "asset.webp", destination)
            except MediaError as exc:
                failure = exc

        self.assertIsNone(failure)
        self.assertEqual(destination.read_bytes(), b"public release asset")
        self.assertEqual(observed_timeouts, [23.0, 23.0])

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

    def test_working_image_symlink_is_ignored_without_weakening_source_symlink_rejection(self) -> None:
        working = self.source / "working"
        working.mkdir()
        latest = working / "latest.png"
        latest.symlink_to(self.source / "historisch-ohne-paarung.png")

        inventory = build_media_inventory(self.source, archive_index=1)

        self.assertEqual(len(inventory.records), 3)
        self.assertEqual(inventory.ignored_working_paths, ("working/latest.png",))

    def test_source_symlink_is_rejected(self) -> None:
        if not hasattr(Path, "symlink_to"):
            self.skipTest("symlinks unavailable")
        outside = self.root / "outside.png"
        outside.write_bytes(png_bytes(10, 10, (1, 2, 3)))
        (self.source / "escape.png").symlink_to(outside)

        with self.assertRaisesRegex(MediaError, "symlink"):
            build_media_inventory(self.source, archive_index=1)

    def test_lfs_pointer_is_rejected_before_image_decode(self) -> None:
        pointer = self.source / "pointer.png"
        pointer.write_text(
            "version https://git-lfs.github.com/spec/v1\noid sha256:" + "a" * 64 + "\nsize 123\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(MediaError, "LFS pointer"):
            build_media_inventory(self.source, archive_index=1)

    def test_source_byte_and_pixel_limits_are_fail_closed(self) -> None:
        self.assertEqual(MAX_SOURCE_BYTES, 25 * 1024 * 1024)
        self.assertEqual(MAX_SOURCE_PIXELS, 50_000_000)
        with patch("wirtelprimpf_platform.media.MAX_SOURCE_BYTES", 1):
            with self.assertRaisesRegex(MediaError, "byte limit"):
                build_media_inventory(self.source, archive_index=1)
        with patch("wirtelprimpf_platform.media.MAX_SOURCE_PIXELS", 1):
            with self.assertRaisesRegex(MediaError, "pixel limit"):
                build_media_inventory(self.source, archive_index=1)


if __name__ == "__main__":
    unittest.main()
