from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = ROOT / "Sourcecode" / "wirtelprimpf_generator.py"


def load_generator():
    spec = importlib.util.spec_from_file_location("wirtelprimpf_generator_release_test", GENERATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load generator module from {GENERATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class MemoryBackend:
    def __init__(self) -> None:
        self.assets: dict[str, dict[str, bytes]] = {}

    def ensure_release(self, tag: str, *, title: str, notes: str) -> None:
        del title, notes
        self.assets.setdefault(tag, {})

    def asset_names(self, tag: str) -> set[str]:
        return set(self.assets.get(tag, {}))

    def upload_asset(self, tag: str, path: Path) -> None:
        self.assets[tag][path.name] = path.read_bytes()

    def download_asset(self, tag: str, asset_name: str, destination: Path) -> None:
        destination.write_bytes(self.assets[tag][asset_name])


class ReleasePublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.generator = load_generator()

    def config(self, root: Path):
        repository = root / "Wirtelprimpf-0001"
        repository.mkdir()
        return self.generator.Config(
            local_outdir=root / "out",
            working_dir=root / "working",
            repo_path=repository,
            repo_slug="H234598/Wirtelprimpf-0001",
            repo_subdir="Wirtelprimpf",
            repo_branch="main",
            image_model="gpt-image-2",
            image_size="1536x1024",
            output_resolution="2k",
            flex_processing_mode=None,
            operandi=self.generator.OPERANDI_STORY,
            prompt_config_path=root / "prompt.md",
            story_prompt_config_path=root / "story_prompt.md",
            story_model="gpt-5-mini",
            story_document_path=root / "Wirtelprimpf_Story_I.md",
            story_state_path=root / "story_state.json",
            story_finish_requested=False,
            story_finish_parts_min=3,
            story_finish_parts_max=5,
            commit_author_name="Bot",
            commit_author_email="bot@example.invalid",
            media_mode="release",
            github_owner="H234598",
            media_staging_path=root / "staging",
            publish_immediately=True,
        )

    def test_release_mode_publishes_five_assets_and_only_writes_manifest_to_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = self.config(root)
            image = root / "out" / "wirtelprimpf_2026-07-31_23-00-00-000001.png"
            image.parent.mkdir()
            Image.new("RGB", (1280, 720), (90, 140, 180)).save(image)
            backend = MemoryBackend()

            record, manifest = self.generator.publish_release_image(
                config,
                image,
                source_path=f"Wirtelprimpf/{image.name}",
                kind="story",
                prompt_path=f"Wirtelprimpf/{image.stem}.txt",
                story_part_path=f"Wirtelprimpf/{image.stem}.md",
                story_volume=2,
                backend=backend,
            )

            self.assertEqual(record["release_tag"], "archive-0001-media-0001")
            self.assertEqual(sum(len(assets) for assets in backend.assets.values()), 5)
            self.assertEqual(manifest, config.repo_path / "media-manifest.json")
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(payload["media_count"], 1)
            self.assertFalse(list(config.repo_path.rglob("*.png")))

    def test_release_mode_rejects_repository_that_does_not_match_story_band(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = self.config(root)
            image = root / "image.png"
            Image.new("RGB", (64, 64), (10, 20, 30)).save(image)

            with self.assertRaisesRegex(RuntimeError, "archive target mismatch"):
                self.generator.publish_release_image(
                    config,
                    image,
                    source_path="Wirtelprimpf/image.png",
                    kind="story",
                    story_volume=51,
                    backend=MemoryBackend(),
                )

    def test_publish_immediately_pushes_the_exact_generated_path_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = self.config(root)
            bare = root / "remote.git"
            subprocess.run(["git", "init", "--bare", str(bare)], check=True, stdout=subprocess.PIPE)
            subprocess.run(["git", "init", "-b", "main"], cwd=config.repo_path, check=True, stdout=subprocess.PIPE)
            subprocess.run(["git", "remote", "add", "origin", str(bare)], cwd=config.repo_path, check=True)
            generated = config.repo_path / "Wirtelprimpf" / "part.md"
            generated.parent.mkdir()
            generated.write_text("published\n", encoding="utf-8")

            revision = self.generator.commit_and_push(config, [generated], "part")
            remote_revision = subprocess.run(
                ["git", "rev-parse", "refs/heads/main"],
                cwd=bare,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            ).stdout.strip()

            self.assertEqual(revision, remote_revision)


if __name__ == "__main__":
    unittest.main()
