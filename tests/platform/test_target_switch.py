from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from wirtelprimpf_platform.target_switch import GeneratorTargetSwitcher, GitCatalogPublisher


class TargetSwitchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_catalog_is_published_before_private_settings_switch_and_secret_is_preserved(self) -> None:
        settings = self.root / "private" / "openai.env"
        settings.parent.mkdir(mode=0o700)
        settings.write_text(
            "# keep this comment\n"
            "OPENAI_API_KEY=do-not-return-or-change\n"
            "WIRTELPRIMPF_REPO_PATH=/old/archive\n"
            "WIRTELPRIMPF_REPO_SLUG=H234598/Wirtelprimpf-0001\n",
            encoding="utf-8",
        )
        os.chmod(settings, 0o600)
        events: list[str] = []

        switcher = GeneratorTargetSwitcher(
            settings_path=settings,
            archive_root=self.root / "archives",
            owner="H234598",
            publish_catalog=lambda repository: events.append(f"catalog:{repository}"),
        )
        switcher.switch_target("Wirtelprimpf-0002")

        raw = settings.read_text(encoding="utf-8")
        self.assertEqual(events, ["catalog:Wirtelprimpf-0002"])
        self.assertIn("OPENAI_API_KEY=do-not-return-or-change", raw)
        self.assertIn(f"WIRTELPRIMPF_REPO_PATH={self.root / 'archives/Wirtelprimpf-0002'}", raw)
        self.assertIn("WIRTELPRIMPF_REPO_SLUG=H234598/Wirtelprimpf-0002", raw)
        self.assertEqual(settings.stat().st_mode & 0o777, 0o600)
        self.assertFalse(list(settings.parent.glob("*.part")))

    def test_settings_are_byte_identical_when_catalog_publish_fails(self) -> None:
        settings = self.root / "settings.env"
        settings.write_text("OPENAI_API_KEY=unchanged\n", encoding="utf-8")
        before = settings.read_bytes()
        switcher = GeneratorTargetSwitcher(
            settings_path=settings,
            archive_root=self.root / "archives",
            owner="H234598",
            publish_catalog=lambda repository: (_ for _ in ()).throw(RuntimeError(repository)),
        )

        with self.assertRaises(RuntimeError):
            switcher.switch_target("Wirtelprimpf-0002")

        self.assertEqual(settings.read_bytes(), before)

    def test_catalog_publisher_commits_only_catalog_and_pushes_main(self) -> None:
        bare = self.root / "remote.git"
        repository = self.root / "generator"
        subprocess.run(["git", "init", "--bare", str(bare)], check=True, stdout=subprocess.PIPE)
        subprocess.run(["git", "init", "-b", "main", str(repository)], check=True, stdout=subprocess.PIPE)
        subprocess.run(["git", "remote", "add", "origin", str(bare)], cwd=repository, check=True)
        catalog = repository / "data" / "publication-catalog.json"
        catalog.parent.mkdir()
        catalog.write_text('{"archives":[]}\n', encoding="utf-8")
        subprocess.run(["git", "add", "data/publication-catalog.json"], cwd=repository, check=True)
        subprocess.run(
            ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "initial"],
            cwd=repository,
            check=True,
            stdout=subprocess.PIPE,
        )
        subprocess.run(["git", "push", "-u", "origin", "main"], cwd=repository, check=True, stdout=subprocess.PIPE)
        catalog.write_text('{"archives":[{"archive_index":2}]}\n', encoding="utf-8")

        revision = GitCatalogPublisher(
            generator_root=repository,
            catalog_path=catalog,
        ).publish("Wirtelprimpf-0002")

        remote_revision = subprocess.run(
            ["git", "rev-parse", "refs/heads/main"],
            cwd=bare,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout.strip()
        changed = subprocess.run(
            ["git", "show", "--name-only", "--pretty=format:", revision],
            cwd=repository,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout.splitlines()
        self.assertEqual(revision, remote_revision)
        self.assertEqual(changed, ["data/publication-catalog.json"])


if __name__ == "__main__":
    unittest.main()
