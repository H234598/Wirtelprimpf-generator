from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from wirtelprimpf_platform.media_cache import MediaDerivativeCache, media_cache_key


def make_derivative(target: Path) -> tuple[str, int, int, int]:
    Image.new("RGB", (640, 360), (70, 120, 180)).save(target, format="WEBP", quality=82, method=6, exif=b"")
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    return digest, target.stat().st_size, 640, 360


class MediaCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_persistent_cache_reuses_an_unchanged_derivative(self) -> None:
        cache_root = self.root / "cache"
        first_target = self.root / "first.webp"
        first_cache = MediaDerivativeCache(cache_root, tool_version="pillow-test", writable=True)
        first = first_cache.materialize(
            original_sha256="a" * 64,
            target_width=640,
            target=first_target,
            producer=make_derivative,
        )
        self.assertEqual(first_cache.report()["cache_hit_rate"], 0.0)

        second_target = self.root / "second.webp"
        second_cache = MediaDerivativeCache(cache_root, tool_version="pillow-test", writable=True)

        def must_not_rebuild(target: Path) -> tuple[str, int, int, int]:
            raise AssertionError(f"cache miss unexpectedly rebuilt {target}")

        second = second_cache.materialize(
            original_sha256="a" * 64,
            target_width=640,
            target=second_target,
            producer=must_not_rebuild,
        )
        self.assertEqual(first, second)
        self.assertEqual(first_target.read_bytes(), second_target.read_bytes())
        self.assertEqual(second_cache.report()["cache_hit_rate"], 1.0)
        self.assertEqual(len([path for path in cache_root.iterdir() if path.is_dir()]), 1)

    def test_transform_config_change_gets_a_new_cache_entry(self) -> None:
        cache_root = self.root / "cache"
        first = MediaDerivativeCache(cache_root, tool_version="pillow-test", writable=True)
        first.materialize(
            original_sha256="b" * 64,
            target_width=640,
            target=self.root / "first.webp",
            producer=make_derivative,
        )
        changed = MediaDerivativeCache(
            cache_root,
            tool_version="pillow-test",
            transform_config_version="media-transform-v2",
            writable=True,
        )
        changed.materialize(
            original_sha256="b" * 64,
            target_width=640,
            target=self.root / "changed.webp",
            producer=make_derivative,
        )
        self.assertEqual(changed.report()["misses"], 1)
        self.assertNotEqual(
            media_cache_key("b" * 64, "pillow-test", "media-transform-v1", "webp", 640),
            media_cache_key("b" * 64, "pillow-test", "media-transform-v2", "webp", 640),
        )

    def test_corrupt_entry_is_rebuilt_and_read_only_cache_never_writes(self) -> None:
        cache_root = self.root / "cache"
        writable = MediaDerivativeCache(cache_root, tool_version="pillow-test", writable=True)
        writable.materialize(
            original_sha256="c" * 64,
            target_width=640,
            target=self.root / "first.webp",
            producer=make_derivative,
        )
        entry = next(path for path in cache_root.iterdir() if path.is_dir())
        (entry / "derivative.webp").write_bytes(b"corrupt")

        rebuilt = MediaDerivativeCache(cache_root, tool_version="pillow-test", writable=True)
        rebuilt.materialize(
            original_sha256="c" * 64,
            target_width=640,
            target=self.root / "rebuilt.webp",
            producer=make_derivative,
        )
        self.assertEqual(rebuilt.report()["hits"], 0)
        self.assertEqual(rebuilt.report()["misses"], 1)

        read_only_root = self.root / "read-only-cache"
        read_only = MediaDerivativeCache(read_only_root, tool_version="pillow-test", writable=False)
        read_only.materialize(
            original_sha256="d" * 64,
            target_width=640,
            target=self.root / "read-only.webp",
            producer=make_derivative,
        )
        self.assertFalse(read_only_root.exists())
        self.assertEqual(read_only.report()["cache_hit_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()
