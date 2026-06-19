#!/usr/bin/env python3
"""Regression tests for the generator's Git object-store fallback."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = ROOT / "Sourcecode" / "wirtelprimpf_generator.py"


def load_generator():
    spec = importlib.util.spec_from_file_location("wirtelprimpf_generator_git_fallback", GENERATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load generator module from {GENERATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class GitObjectFallbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generator = load_generator()

    def test_detects_git_object_permission_failure(self):
        exc = RuntimeError(
            "Command failed: git commit: error: insufficient permission for adding an object "
            "to repository database .git/objects\nerror: Error building trees"
        )

        self.assertTrue(self.generator._git_object_permission_failure(exc))

    def test_registers_fallback_object_store_idempotently(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "repo"
            objects = repo / ".git" / "objects"
            (objects / "info").mkdir(parents=True)

            first = self.generator._git_object_fallback_env(repo)
            second = self.generator._git_object_fallback_env(repo)

            fallback = repo / ".git" / self.generator.GIT_FALLBACK_OBJECT_DIR
            alternates = objects / "info" / "alternates"
            lines = alternates.read_text(encoding="utf-8").splitlines()

        self.assertEqual(first, second)
        self.assertEqual(lines, [str(fallback.resolve())])
        self.assertEqual(first["GIT_OBJECT_DIRECTORY"], str(fallback.resolve()))
        self.assertIn(str(objects.resolve()), first["GIT_ALTERNATE_OBJECT_DIRECTORIES"])

    def test_commit_and_push_uses_pathspec_for_generator_files_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "repo"
            subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, stdout=subprocess.PIPE)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
            (repo / "Wirtelprimpf").mkdir()
            (repo / "Wirtelprimpf" / ".gitkeep").write_text("", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, check=True, stdout=subprocess.PIPE)

            unrelated = repo / "unrelated.txt"
            unrelated.write_text("foreign staged change\n", encoding="utf-8")
            subprocess.run(["git", "add", "unrelated.txt"], cwd=repo, check=True)

            generated = repo / "Wirtelprimpf" / "generated.txt"
            generated.write_text("generated\n", encoding="utf-8")
            config = self.generator.Config(
                local_outdir=repo,
                working_dir=repo / "working",
                repo_path=repo,
                repo_slug=None,
                repo_subdir="Wirtelprimpf",
                repo_branch="main",
                image_model="gpt-image-2",
                image_size="1536x1024",
                output_resolution="2k",
                flex_processing_mode=None,
                operandi=self.generator.OPERANDI_STORY,
                prompt_config_path=repo / "prompt.md",
                story_prompt_config_path=repo / "story_prompt.md",
                story_model="gpt-5-mini",
                story_document_path=repo / "story.md",
                story_state_path=repo / "story_state.json",
                story_finish_requested=False,
                story_finish_parts_min=3,
                story_finish_parts_max=5,
                commit_author_name="Bot",
                commit_author_email="bot@example.invalid",
            )
            old_path = os.environ.get("PATH")
            os.environ["PATH"] = "/usr/local/bin:/usr/bin:/bin"
            try:
                self.generator.commit_and_push(config, [generated], "generated")
            finally:
                if old_path is None:
                    os.environ.pop("PATH", None)
                else:
                    os.environ["PATH"] = old_path

            committed_files = subprocess.run(
                ["git", "show", "--name-only", "--pretty=format:", "HEAD"],
                cwd=repo,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            ).stdout.splitlines()
            staged_status = subprocess.run(
                ["git", "status", "--porcelain", "--", "unrelated.txt"],
                cwd=repo,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            ).stdout.strip()

        self.assertIn("Wirtelprimpf/generated.txt", committed_files)
        self.assertNotIn("unrelated.txt", committed_files)
        self.assertEqual(staged_status, "A  unrelated.txt")


if __name__ == "__main__":
    unittest.main()
