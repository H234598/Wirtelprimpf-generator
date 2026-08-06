from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from wirtelprimpf_platform.github_provision import GitHubProvisioner


class RecordingProvisioner(GitHubProvisioner):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.commands: list[list[str]] = []

    def _run(self, command, *, cwd=None, input_text=None, check=True):
        del cwd, input_text, check
        self.commands.append(command)
        if command[:3] == ["git", "status", "--porcelain"]:
            stdout = "?? .gitignore\n"
        elif command[:2] == ["git", "rev-parse"]:
            stdout = f"{'a' * 40}\n"
        else:
            stdout = ""
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")


class GitHubProvisionerTests(unittest.TestCase):
    def test_new_archive_ignores_images_but_keeps_publication_text(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            generator_root = root / "generator"
            archive_root = root / "archives"
            checkout = archive_root / "Wirtelprimpf-0002"
            (generator_root / "web").mkdir(parents=True)
            (generator_root / "web/package.json").write_text("{}\n", encoding="utf-8")
            (generator_root / "LICENSE").write_text("license\n", encoding="utf-8")
            checkout.mkdir(parents=True)
            subprocess.run(["git", "init", "--quiet"], cwd=checkout, check=True)
            provisioner = RecordingProvisioner(
                owner="H234598",
                generator_root=generator_root,
                archive_root=archive_root,
                factory_ref="b" * 40,
            )

            revision = provisioner.initialize_archive(
                "Wirtelprimpf-0002",
                archive_index=2,
                domain="wirtelprimpf.telacore.org",
            )

            ignore = (checkout / ".gitignore").read_text(encoding="utf-8")
            for suffix in ("png", "jpg", "jpeg", "webp", "gif", "avif"):
                self.assertIn(f"/Wirtelprimpf/*.{suffix}", ignore)
                self.assertIn(f"/Wirtelprimpf/**/*.{suffix}", ignore)
            self.assertNotIn("*.md", ignore)
            self.assertNotIn("*.txt", ignore)
            self.assertEqual(revision, "a" * 40)
            add = next(command for command in provisioner.commands if command[:2] == ["git", "add"])
            self.assertIn(".gitignore", add)
            (checkout / "Wirtelprimpf/working").mkdir(parents=True)
            (checkout / "Wirtelprimpf/current.png").touch()
            (checkout / "Wirtelprimpf/working/latest.webp").touch()
            (checkout / "Wirtelprimpf/story.md").touch()
            for path in ("Wirtelprimpf/current.png", "Wirtelprimpf/working/latest.webp"):
                ignored = subprocess.run(
                    ["git", "check-ignore", "--quiet", "--no-index", path],
                    cwd=checkout,
                    check=False,
                )
                self.assertEqual(ignored.returncode, 0, path)
            public_text = subprocess.run(
                ["git", "check-ignore", "--quiet", "--no-index", "Wirtelprimpf/story.md"],
                cwd=checkout,
                check=False,
            )
            self.assertEqual(public_text.returncode, 1)
            manifest = json.loads((checkout / "archive-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["story_start"], 51)
            self.assertEqual(manifest["story_end"], 100)
            self.assertEqual(manifest["book_start"], 6)
            self.assertEqual(manifest["book_end"], 10)
            self.assertEqual(manifest["stories_per_book"], 10)
            readme = (checkout / "README.md").read_text(encoding="utf-8")
            self.assertIn("Storys 51 bis 100", readme)
            self.assertIn("Bücher 6 bis 10", readme)
            self.assertIn("Zentrale Website: <https://wirtelprimpf.telacore.org>", readme)
            self.assertIn("Repository: <https://github.com/H234598/Wirtelprimpf-0002>", readme)
            self.assertFalse((checkout / ".github/workflows/pages.yml").exists())


if __name__ == "__main__":
    unittest.main()
