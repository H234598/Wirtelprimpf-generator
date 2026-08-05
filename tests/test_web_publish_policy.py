from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = ROOT / "Sourcecode" / "wirtelprimpf_generator.py"


def load_generator():
    spec = importlib.util.spec_from_file_location("wirtelprimpf_generator_publish_policy", GENERATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load generator module from {GENERATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class WebPublishPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.generator = load_generator()

    def config(self, root: Path):
        return self.generator.Config(
            local_outdir=root / "out",
            working_dir=root / "working",
            repo_path=root / "repo",
            repo_slug=None,
            repo_subdir="Wirtelprimpf",
            repo_branch="main",
            image_model="gpt-image-2",
            image_size="1536x1024",
            output_resolution="2k",
            flex_processing_mode=None,
            operandi=self.generator.OPERANDI_STORY,
            prompt_config_path=root / "prompt.md",
            story_prompt_config_path=root / "story-prompt.md",
            story_model="gpt-5-mini",
            story_document_path=root / "story.md",
            story_state_path=root / "story-state.json",
            story_finish_requested=False,
            story_finish_parts_min=3,
            story_finish_parts_max=5,
            commit_author_name="Bot",
            commit_author_email="bot@example.invalid",
            publish_immediately=True,
        )

    def test_intervals_are_explicit_and_publish_is_path_scoped(self) -> None:
        self.assertEqual(self.generator.PUBLISH_PUSH_INTERVAL_PATCHES, 100)
        self.assertEqual(self.generator.PUBLISH_RELEASE_PUSH_INTERVAL, 10)
        source = (ROOT / "Sourcecode" / "wirtelprimpf_generator.py").read_text(encoding="utf-8")
        self.assertIn('git", "add", *relative_paths', source)
        self.assertIn('git", "status", "--porcelain", "--", *relative_paths', source)
        self.assertIn("_exclusive_story_state_lock", source)

    def test_push_failure_keeps_the_local_commit_and_records_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = self.config(root)
            config.repo_path.mkdir()
            subprocess.run(["git", "init", "-b", "main", str(config.repo_path)], check=True, stdout=subprocess.PIPE)
            generated = config.repo_path / "Wirtelprimpf" / "part.md"
            generated.parent.mkdir()
            generated.write_text("published\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "commit recorded but push failed"):
                self.generator.commit_and_push(config, [generated], "part")
            head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=config.repo_path, check=True, text=True, stdout=subprocess.PIPE).stdout.strip()
            self.assertEqual(len(head), 40)
            state = json.loads((config.repo_path / ".git" / self.generator.PUBLISH_STATE_FILE).read_text(encoding="utf-8"))
            self.assertEqual(state["patch_count"], 1)


if __name__ == "__main__":
    unittest.main()
