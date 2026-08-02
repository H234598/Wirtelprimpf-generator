from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

if __package__:
    from ._settings_fixtures import snapshot_for_test
else:
    from _settings_fixtures import snapshot_for_test

from wirtelprimpf_platform.catalog import CatalogEntry, CatalogStore, PublicationCatalog
from wirtelprimpf_platform.naming import STORIES_PER_BOOK
from wirtelprimpf_platform.operational_status import OperationalStatusCollector, StatusPaths
from wirtelprimpf_platform.settings import SettingsPaths
from wirtelprimpf_platform.state import PlatformState, StateStore
from wirtelprimpf_platform.systemd_user import TimerConfiguration, TimerObservation


def active_timer() -> TimerObservation:
    return TimerObservation.from_configuration(
        TimerConfiguration(True, 120, 120, True),
        active=True,
    )


class OperationalStatusTests(unittest.TestCase):
    def test_unexpected_invalid_state_reader_result_degrades_only_the_story_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = StatusPaths.for_root(Path(temporary))
            paths.platform_state.parent.mkdir(parents=True, exist_ok=True)
            paths.platform_state.touch(mode=0o600)
            invalid_state = SimpleNamespace(
                completed_volumes=0,
                current_volume=object(),
                active_archive_index=1,
                active_repository="Wirtelprimpf-0001",
                generation_blocked=False,
                rotation=None,
            )
            snapshot = snapshot_for_test(revision="b" * 64, settings={})
            collector = OperationalStatusCollector(
                paths=paths,
                snapshot_reader=lambda: snapshot,
                timer_reader=active_timer,
                service_reader=lambda: {
                    "active_state": "inactive",
                    "result": "success",
                    "exec_main_status": 0,
                },
                clock=lambda: datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
            )
            with patch(
                "wirtelprimpf_platform.operational_status.StateStore",
                return_value=SimpleNamespace(load=lambda: invalid_state),
            ):
                status = collector.collect()

        self.assertEqual(status["health"], "degraded")
        self.assertEqual(status["configuration"]["state"], "valid")
        self.assertEqual(status["story"]["state"], "unknown")
        self.assertIsNone(status["story"]["current_volume"])
        self.assertEqual(
            status["errors"],
            [{"source": "platform_state", "message": "local source unavailable"}],
        )

    def test_malformed_current_volume_json_is_already_redacted_and_degraded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = StatusPaths.for_root(Path(temporary))
            paths.platform_state.parent.mkdir(parents=True, exist_ok=True)
            paths.platform_state.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "completed_volumes": 0,
                        "current_volume": "not an integer",
                        "active_archive_index": 1,
                        "rotation": None,
                    }
                ),
                encoding="utf-8",
            )
            paths.platform_state.chmod(0o600)
            snapshot = snapshot_for_test(revision="b" * 64, settings={})
            status = OperationalStatusCollector(
                paths=paths,
                snapshot_reader=lambda: snapshot,
                timer_reader=active_timer,
                service_reader=lambda: {
                    "active_state": "inactive",
                    "result": "success",
                    "exec_main_status": 0,
                },
                clock=lambda: datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
            ).collect()

        self.assertEqual(status["health"], "degraded")
        self.assertEqual(status["story"]["state"], "unknown")
        self.assertEqual(
            status["errors"],
            [{"source": "platform_state", "message": "local source unavailable"}],
        )

    def test_configuration_status_paths_are_owned_by_settings_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            status_paths = StatusPaths.for_home(root)
            settings_paths = SettingsPaths.for_home(root)
        self.assertEqual(status_paths.platform_state, settings_paths.platform_state)
        self.assertEqual(status_paths.settings_state, settings_paths.state_file)

    def test_local_state_builds_real_story_book_archive_and_timer_status(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = StatusPaths.for_root(root)
            StateStore(paths.platform_state).save(
                PlatformState(completed_volumes=1, current_volume=2, active_archive_index=1)
            )
            paths.hub_source.parent.mkdir(parents=True, exist_ok=True)
            paths.hub_source.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "current_volume": 2,
                        "repository": "Wirtelprimpf-0001",
                        "revision": "a" * 40,
                        "story_path": "Wirtelprimpf/Wirtelprimpf_Story_II.md",
                    }
                ),
                encoding="utf-8",
            )
            snapshot = snapshot_for_test(
                revision="b" * 64,
                settings={"repo_path": str(root / "archive")},
            )
            collector = OperationalStatusCollector(
                paths=paths,
                snapshot_reader=lambda: snapshot,
                timer_reader=active_timer,
                service_reader=lambda: {
                    "active_state": "inactive",
                    "result": "success",
                    "exec_main_status": 0,
                },
                clock=lambda: datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
            )
            status = collector.collect()
        self.assertEqual(status["health"], "ok")
        self.assertEqual(status["story"]["current_volume"], 2)
        self.assertEqual(status["story"]["book"], 1)
        self.assertEqual(status["story"]["story_in_book"], 2)
        self.assertEqual(status["story"]["stories_per_book"], STORIES_PER_BOOK)
        self.assertEqual(status["archive"]["repository"], "Wirtelprimpf-0001")
        self.assertEqual(status["timer"]["interval_minutes"], 120)

    def test_hub_repository_mismatch_is_visible_before_the_hub_value_wins(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = StatusPaths.for_root(root)
            StateStore(paths.platform_state).save(PlatformState(active_archive_index=1))
            paths.hub_source.parent.mkdir(parents=True, exist_ok=True)
            paths.hub_source.write_text(
                json.dumps(
                    {
                        "repository": "Wirtelprimpf-0002",
                        "revision": "a" * 40,
                    }
                ),
                encoding="utf-8",
            )
            snapshot = snapshot_for_test(revision="b" * 64, settings={})
            status = OperationalStatusCollector(
                paths=paths,
                snapshot_reader=lambda: snapshot,
                timer_reader=active_timer,
                service_reader=lambda: {"active_state": "inactive"},
            ).collect()

        self.assertEqual(status["archive"]["repository"], "Wirtelprimpf-0002")
        self.assertIn("hub_archive_repository_mismatch", status["warnings"])

    def test_one_broken_local_source_is_degraded_and_explicitly_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = StatusPaths.for_root(root)
            paths.platform_state.parent.mkdir(parents=True, exist_ok=True)
            paths.platform_state.write_text("{broken", encoding="utf-8")
            snapshot = snapshot_for_test(revision="b" * 64, settings={})
            collector = OperationalStatusCollector(
                paths=paths,
                snapshot_reader=lambda: snapshot,
                timer_reader=active_timer,
                service_reader=lambda: {
                    "active_state": "inactive",
                    "result": "success",
                    "exec_main_status": 0,
                },
                clock=lambda: datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
            )
            status = collector.collect()
        self.assertEqual(status["health"], "degraded")
        self.assertIsNone(status["story"]["current_volume"])
        self.assertEqual(status["story"]["state"], "unknown")
        self.assertNotIn("token", json.dumps(status).lower())

    def test_missing_platform_state_is_degraded_and_does_not_invent_story_one(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = StatusPaths.for_root(Path(temporary))
            snapshot = snapshot_for_test(revision="b" * 64, settings={})
            status = OperationalStatusCollector(
                paths=paths,
                snapshot_reader=lambda: snapshot,
                timer_reader=active_timer,
                service_reader=lambda: {
                    "active_state": "inactive",
                    "result": "success",
                    "exec_main_status": 0,
                },
                clock=lambda: datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
            ).collect()
        self.assertEqual(status["health"], "degraded")
        self.assertEqual(status["story"]["state"], "unknown")
        self.assertIsNone(status["story"]["current_volume"])
        self.assertIn(
            {"source": "platform_state", "message": "local source unavailable"},
            status["errors"],
        )

    def test_configuration_freshness_uses_revision_signal_mtime(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = StatusPaths.for_root(Path(temporary))
            StateStore(paths.platform_state).save(PlatformState())
            paths.settings_state.parent.mkdir(parents=True, exist_ok=True)
            paths.settings_state.write_text(
                json.dumps({"schema_version": "2.0.0", "revision": "b" * 64}) + "\n",
                encoding="utf-8",
            )
            observed_timestamp = datetime(2026, 8, 1, 11, 58, tzinfo=UTC).timestamp()
            os.utime(paths.settings_state, (observed_timestamp, observed_timestamp))
            snapshot = snapshot_for_test(revision="b" * 64, settings={})
            status = OperationalStatusCollector(
                paths=paths,
                snapshot_reader=lambda: snapshot,
                timer_reader=active_timer,
                service_reader=lambda: {
                    "active_state": "inactive",
                    "result": "success",
                    "exec_main_status": 0,
                },
                clock=lambda: datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
            ).collect()
        self.assertEqual(status["configuration"]["observed_at"], "2026-08-01T11:58:00Z")
        self.assertEqual(status["configuration"]["state"], "valid")

    def test_revision_signal_mismatch_is_copied_into_final_configuration_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = StatusPaths.for_root(Path(temporary))
            StateStore(paths.platform_state).save(PlatformState())
            paths.settings_state.parent.mkdir(parents=True, exist_ok=True)
            paths.settings_state.write_text(
                json.dumps({"schema_version": "2.0.0", "revision": "c" * 64}) + "\n",
                encoding="utf-8",
            )
            snapshot = snapshot_for_test(revision="b" * 64, settings={})
            status = OperationalStatusCollector(
                paths=paths,
                snapshot_reader=lambda: snapshot,
                timer_reader=active_timer,
                service_reader=lambda: {"active_state": "inactive"},
            ).collect()

        self.assertEqual(status["configuration"]["state"], "drift")
        self.assertIn("revision_signal_mismatch", status["configuration"]["drift"])
        self.assertIn("revision_signal_mismatch", status["warnings"])

    def test_story_property_failure_is_redacted_inside_the_source_boundary(self) -> None:
        class InvalidState:
            current_volume = 1

            @property
            def generation_blocked(self):
                raise RuntimeError("OPENAI_API_KEY=must-never-escape")

        with tempfile.TemporaryDirectory() as temporary:
            paths = StatusPaths.for_root(Path(temporary))
            paths.platform_state.parent.mkdir(parents=True, exist_ok=True)
            paths.platform_state.touch(mode=0o600)
            snapshot = snapshot_for_test(revision="b" * 64, settings={})
            collector = OperationalStatusCollector(
                paths=paths,
                snapshot_reader=lambda: snapshot,
                timer_reader=active_timer,
                service_reader=lambda: {"active_state": "inactive"},
            )
            with patch(
                "wirtelprimpf_platform.operational_status.StateStore",
                return_value=SimpleNamespace(load=lambda: InvalidState()),
            ):
                status = collector.collect()

        self.assertEqual(status["story"]["state"], "unknown")
        self.assertIn(
            {"source": "platform_state", "message": "local source unavailable"},
            status["errors"],
        )
        self.assertNotIn("must-never-escape", json.dumps(status))

    def test_malformed_release_tag_degrades_instead_of_winning_lexically(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = StatusPaths.for_root(Path(temporary))
            StateStore(paths.platform_state).save(PlatformState())
            paths.media_manifest.parent.mkdir(parents=True, exist_ok=True)
            paths.media_manifest.write_text(
                json.dumps(
                    {
                        "media": [
                            {"release_tag": "archive-0001-media-0002"},
                            {"release_tag": "zzz-not-a-release"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            snapshot = snapshot_for_test(revision="b" * 64, settings={})
            status = OperationalStatusCollector(
                paths=paths,
                snapshot_reader=lambda: snapshot,
                timer_reader=active_timer,
                service_reader=lambda: {"active_state": "inactive"},
            ).collect()

        self.assertEqual(status["publication"]["release"]["state"], "unknown")
        self.assertIn(
            {"source": "media_manifest", "message": "local source unavailable"},
            status["errors"],
        )

    def test_hub_derived_value_failure_is_redacted_inside_the_source_boundary(self) -> None:
        class InvalidHub(dict):
            def get(self, *_args, **_kwargs):
                raise RuntimeError("GH_TOKEN=must-never-escape")

        with tempfile.TemporaryDirectory() as temporary:
            paths = StatusPaths.for_root(Path(temporary))
            StateStore(paths.platform_state).save(PlatformState())
            paths.hub_source.parent.mkdir(parents=True, exist_ok=True)
            paths.hub_source.touch()
            snapshot = snapshot_for_test(revision="b" * 64, settings={})
            collector = OperationalStatusCollector(
                paths=paths,
                snapshot_reader=lambda: snapshot,
                timer_reader=active_timer,
                service_reader=lambda: {"active_state": "inactive"},
            )
            with patch(
                "wirtelprimpf_platform.operational_status._read_json_object",
                return_value=InvalidHub(),
            ):
                status = collector.collect()

        self.assertEqual(status["publication"]["hub"]["state"], "unknown")
        self.assertIn(
            {"source": "hub", "message": "local source unavailable"},
            status["errors"],
        )
        self.assertNotIn("must-never-escape", json.dumps(status))

    def test_catalog_derived_value_failure_is_redacted_inside_the_source_boundary(self) -> None:
        class InvalidCatalog:
            active_archive_index = 1

            def entry(self, _archive_index: int):
                raise RuntimeError("CLOUDFLARE_API_TOKEN=must-never-escape")

        with tempfile.TemporaryDirectory() as temporary:
            paths = StatusPaths.for_root(Path(temporary))
            StateStore(paths.platform_state).save(PlatformState())
            paths.publication_catalog.parent.mkdir(parents=True, exist_ok=True)
            paths.publication_catalog.touch()
            snapshot = snapshot_for_test(revision="b" * 64, settings={})
            collector = OperationalStatusCollector(
                paths=paths,
                snapshot_reader=lambda: snapshot,
                timer_reader=active_timer,
                service_reader=lambda: {"active_state": "inactive"},
            )
            with patch(
                "wirtelprimpf_platform.operational_status.CatalogStore",
                return_value=SimpleNamespace(load=lambda: InvalidCatalog()),
            ):
                status = collector.collect()

        self.assertEqual(status["publication"]["pages"]["state"], "unknown")
        self.assertEqual(status["publication"]["dns"]["state"], "unknown")
        self.assertIn(
            {"source": "publication_catalog", "message": "local source unavailable"},
            status["errors"],
        )
        self.assertNotIn("must-never-escape", json.dumps(status))

    def test_collector_never_invokes_network_clients(self) -> None:
        forbidden = {"curl", "wget", "gh", "wrangler"}
        commands: list[list[str]] = []
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = StatusPaths.for_root(root)
            StateStore(paths.platform_state).save(PlatformState())
            repository = root / "archive"
            repository.mkdir()
            snapshot = snapshot_for_test(
                revision="b" * 64,
                settings={"repo_path": str(repository)},
            )
            collector = OperationalStatusCollector(
                paths=paths,
                snapshot_reader=lambda: snapshot,
                timer_reader=active_timer,
                service_reader=lambda: {
                    "active_state": "inactive",
                    "result": "success",
                    "exec_main_status": 0,
                },
                local_runner=lambda command, timeout: (
                    commands.append(command)
                    or subprocess.CompletedProcess(command, 0, f"{'a' * 40}\n", "")
                ),
                clock=lambda: datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
            )
            collector.collect()
        self.assertTrue(commands)
        self.assertTrue(all(command[0] not in forbidden for command in commands))

    def test_service_timeout_is_redacted_and_degraded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = StatusPaths.for_root(Path(temporary))
            StateStore(paths.platform_state).save(PlatformState())
            snapshot = snapshot_for_test(revision="b" * 64, settings={})

            def timed_out():
                raise subprocess.TimeoutExpired(["systemctl", "--user", "show"], 2)

            collector = OperationalStatusCollector(
                paths=paths,
                snapshot_reader=lambda: snapshot,
                timer_reader=active_timer,
                service_reader=timed_out,
                clock=lambda: datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
            )
            status = collector.collect()
        self.assertEqual(status["health"], "degraded")
        self.assertEqual(status["generator"]["active_state"], "unknown")
        self.assertEqual(
            status["errors"],
            [{"source": "generator_service", "message": "local source unavailable"}],
        )

    def test_verified_catalog_populates_persisted_pages_and_dns_observations(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = StatusPaths.for_root(Path(temporary))
            StateStore(paths.platform_state).save(PlatformState())
            entry = CatalogEntry.for_archive(
                1,
                owner="H234598",
                active=True,
                sealed=False,
                verified=True,
                revision="a" * 40,
            )
            CatalogStore(paths.publication_catalog).save(
                PublicationCatalog(active_archive_index=1, archives=(entry,))
            )
            snapshot = snapshot_for_test(revision="b" * 64, settings={})
            status = OperationalStatusCollector(
                paths=paths,
                snapshot_reader=lambda: snapshot,
                timer_reader=active_timer,
                service_reader=lambda: {
                    "active_state": "inactive",
                    "result": "success",
                    "exec_main_status": 0,
                },
                clock=lambda: datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
            ).collect()
        self.assertEqual(status["publication"]["pages"]["state"], "verified")
        self.assertEqual(
            status["publication"]["pages"]["value"],
            "https://wirtelprimpf-0001.telacore.org",
        )
        self.assertEqual(status["publication"]["dns"]["value"], "wirtelprimpf-0001.telacore.org")


if __name__ == "__main__":
    unittest.main()
