from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from wirtelprimpf_platform.hub import (
    GitHubHubDispatcher,
    HubDispatchOutbox,
    HubDispatchRequest,
    resolve_hub_source,
)


ROOT = Path(__file__).resolve().parents[2]


class HubSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "current-story.md").write_text("# Current\n", encoding="utf-8")
        (self.root / "hub-source.json").write_text(json.dumps({
            "schema_version": "1.0.0",
            "repository": "Wirtelprimpf-0001",
            "current_volume": 2,
            "story_path": "Wirtelprimpf/Wirtelprimpf_Story_II.md",
        }), encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_committed_fallback_uses_local_current_story(self) -> None:
        source = resolve_hub_source(self.root)

        self.assertFalse(source.external)
        self.assertEqual(source.repository, "Wirtelprimpf-0001")
        self.assertEqual(source.current_volume, 2)
        self.assertEqual(source.story_file, self.root / "current-story.md")

    def test_dispatch_source_is_exact_ref_and_derives_canonical_roman_story_path(self) -> None:
        source = resolve_hub_source(
            self.root,
            repository="Wirtelprimpf-0002",
            revision="a" * 40,
            current_volume=51,
            external_root=self.root / "external",
        )

        self.assertTrue(source.external)
        self.assertEqual(source.story_file, self.root / "external/Wirtelprimpf/Wirtelprimpf_Story_LI.md")
        self.assertEqual(source.media_manifest, self.root / "external/media-manifest.json")

    def test_dispatch_source_rejects_repository_volume_mismatch(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "does not match"):
            resolve_hub_source(
                self.root,
                repository="Wirtelprimpf-0001",
                revision="b" * 40,
                current_volume=51,
                external_root=self.root / "external",
            )

    def test_pages_workflow_allows_only_exact_dispatches(self) -> None:
        workflow = (ROOT / ".github/workflows/hub-pages.yml").read_text(encoding="utf-8")
        triggers = workflow.split("on:\n", 1)[1].split("\npermissions:\n", 1)[0]

        trigger_names = [
            next(name for name in match.groups() if name is not None)
            for match in re.finditer(
                r'''^  (?:"([^"]+)"|'([^']+)'|([A-Za-z_][A-Za-z0-9_-]*))\s*:''',
                triggers,
                re.MULTILINE,
            )
        ]
        self.assertEqual(trigger_names, ["workflow_dispatch"])
        for name in ("active_repository", "archive_ref", "current_volume"):
            match = re.search(rf"^      {name}:\n(?P<body>(?:        .*\n)+)", triggers, re.MULTILINE)
            self.assertIsNotNone(match, name)
            assert match is not None
            self.assertIn("        required: true\n", match.group("body"), name)

    def test_dispatcher_sends_only_validated_exact_inputs(self) -> None:
        calls: list[list[str]] = []

        def runner(command: list[str]) -> None:
            calls.append(command)

        GitHubHubDispatcher(owner="H234598", runner=runner).dispatch(
            archive_repository="Wirtelprimpf-0001",
            archive_revision="c" * 40,
            current_volume=2,
        )

        self.assertEqual(len(calls), 1)
        command = calls[0]
        self.assertEqual(command[:6], [
            "gh", "workflow", "run", "hub-pages.yml", "--repo", "H234598/Wirtelprimpf-generator"
        ])
        self.assertIn("active_repository=Wirtelprimpf-0001", command)
        self.assertIn(f"archive_ref={'c' * 40}", command)
        self.assertIn("current_volume=2", command)

    def test_dispatch_outbox_is_private_restart_safe_and_clears_only_after_success(self) -> None:
        path = self.root / "private" / "hub-dispatch.json"
        outbox = HubDispatchOutbox(path)
        request = HubDispatchRequest(
            archive_repository="Wirtelprimpf-0001",
            archive_revision="d" * 40,
            current_volume=2,
        )
        outbox.stage(request)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)

        with self.assertRaisesRegex(RuntimeError, "dispatch failed"):
            outbox.dispatch_pending(
                GitHubHubDispatcher(
                    owner="H234598",
                    runner=lambda command: (_ for _ in ()).throw(RuntimeError("dispatch failed")),
                )
            )
        self.assertEqual(outbox.load(), request)

        calls: list[list[str]] = []
        self.assertTrue(outbox.dispatch_pending(GitHubHubDispatcher(owner="H234598", runner=calls.append)))
        self.assertFalse(path.exists())
        self.assertEqual(len(calls), 1)

    def test_outbox_coalesces_a_newer_revision_for_the_same_story_volume(self) -> None:
        outbox = HubDispatchOutbox(self.root / "private" / "hub-dispatch.json")
        first = HubDispatchRequest("Wirtelprimpf-0001", "e" * 40, 2)
        latest = HubDispatchRequest("Wirtelprimpf-0001", "f" * 40, 2)

        outbox.stage(first)
        outbox.stage(latest)

        self.assertEqual(outbox.load(), latest)


if __name__ == "__main__":
    unittest.main()
