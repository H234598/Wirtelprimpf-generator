from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from wirtelprimpf_platform.catalog import CatalogStore
from wirtelprimpf_platform.cloudflare_dns import CloudflareDNS, DNSConflictError
from wirtelprimpf_platform.provision import ProvisionPending, RotationOrchestrator
from wirtelprimpf_platform.state import PlatformState, RotationPhase, StateStore, complete_volume


class FakeGitHub:
    def __init__(self) -> None:
        self.operations: list[tuple[str, str]] = []
        self.repositories: dict[str, int] = {}
        self.fail_initialize_once = False
        self.pages_ready = True

    def reserve_repository(self, repository: str, *, transaction_id: str) -> None:
        self.operations.append(("reserve", repository))
        del transaction_id

    def ensure_repository(self, repository: str, *, transaction_id: str) -> int:
        self.operations.append(("create", repository))
        del transaction_id
        return self.repositories.setdefault(repository, 10_000 + len(self.repositories))

    def ensure_local_checkout(self, repository: str) -> str:
        self.operations.append(("clone", repository))
        return "a" * 40

    def initialize_archive(self, repository: str, *, archive_index: int, domain: str) -> str:
        self.operations.append(("initialize", repository))
        del archive_index, domain
        if self.fail_initialize_once:
            self.fail_initialize_once = False
            raise RuntimeError("injected initialization failure")
        return "b" * 40

    def ensure_pages(self, repository: str, *, domain: str) -> None:
        self.operations.append(("pages", repository))
        del domain

    def verify_pages_and_enable_https(self, repository: str, *, domain: str) -> bool:
        self.operations.append(("verify", repository))
        del domain
        return self.pages_ready


class FakeDNS:
    def __init__(self) -> None:
        self.operations: list[tuple[str, str]] = []

    def ensure_cname(self, name: str, target: str, *, comment: str) -> None:
        del comment
        self.operations.append((name, target))


class FakeTargetSwitcher:
    def __init__(self) -> None:
        self.repositories: list[str] = []
        self.fail_once = False

    def switch_target(self, repository: str) -> None:
        self.repositories.append(repository)
        if self.fail_once:
            self.fail_once = False
            raise RuntimeError("injected target-switch failure")


class RotationOrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.state_store = StateStore(root / "private" / "platform-state.json")
        self.catalog_store = CatalogStore(root / "publication-catalog.json")
        self.github = FakeGitHub()
        self.dns = FakeDNS()
        self.switcher = FakeTargetSwitcher()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def orchestrator(self) -> RotationOrchestrator:
        return RotationOrchestrator(
            owner="H234598",
            pages_target="h234598.github.io",
            state_store=self.state_store,
            catalog_store=self.catalog_store,
            github=self.github,
            dns=self.dns,
            target_switcher=self.switcher,
        )

    def stage_boundary(self) -> PlatformState:
        state = complete_volume(
            PlatformState(completed_volumes=49, current_volume=50, active_archive_index=1),
            50,
            transaction_id="rotation-0001-0002",
        )
        self.state_store.save(state)
        return state

    def test_no_remote_is_created_before_a_full_fifty_volume_boundary(self) -> None:
        self.state_store.save(PlatformState())

        result = self.orchestrator().run()

        self.assertEqual(result, PlatformState())
        self.assertEqual(self.github.operations, [])
        self.assertEqual(self.dns.operations, [])

    def test_rotation_runs_all_phases_and_only_then_switches_active_repository(self) -> None:
        self.stage_boundary()

        result = self.orchestrator().run()

        self.assertEqual(result.active_repository, "Wirtelprimpf-0002")
        self.assertIsNone(result.rotation)
        self.assertEqual([name for name, _ in self.github.operations], [
            "reserve", "create", "clone", "initialize", "pages", "verify"
        ])
        self.assertEqual(self.dns.operations, [
            ("wirtelprimpf-0002.telacore.org", "h234598.github.io")
        ])
        self.assertEqual(self.switcher.repositories, ["Wirtelprimpf-0002"])
        catalog = self.catalog_store.load()
        entry = catalog.entry(2)
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertTrue(entry.verified)
        self.assertEqual(entry.volume_start, 51)
        self.assertEqual(entry.volume_end, 100)
        self.assertEqual(catalog.active_archive_index, 2)

    def test_interruption_resumes_after_last_persisted_phase_without_recreating_remote(self) -> None:
        self.stage_boundary()
        self.github.fail_initialize_once = True

        with self.assertRaisesRegex(RuntimeError, "injected"):
            self.orchestrator().run()

        interrupted = self.state_store.load()
        assert interrupted.rotation is not None
        self.assertEqual(interrupted.rotation.phase, RotationPhase.LOCAL_CLONE_READY)
        self.assertEqual([name for name, _ in self.github.operations].count("create"), 1)

        completed = self.orchestrator().run()

        self.assertIsNone(completed.rotation)
        self.assertEqual([name for name, _ in self.github.operations].count("create"), 1)
        self.assertEqual([name for name, _ in self.github.operations].count("clone"), 1)

    def test_target_switch_failure_is_restartable_after_catalog_persistence(self) -> None:
        self.stage_boundary()
        self.switcher.fail_once = True

        with self.assertRaisesRegex(RuntimeError, "target-switch failure"):
            self.orchestrator().run()

        interrupted = self.state_store.load()
        assert interrupted.rotation is not None
        self.assertEqual(interrupted.rotation.phase, RotationPhase.CATALOG_UPDATED)
        self.assertEqual(self.switcher.repositories, ["Wirtelprimpf-0002"])

        completed = self.orchestrator().run()

        self.assertIsNone(completed.rotation)
        self.assertEqual(self.switcher.repositories, ["Wirtelprimpf-0002", "Wirtelprimpf-0002"])

    def test_unready_pages_stays_blocked_and_resumes_at_verification(self) -> None:
        self.stage_boundary()
        self.github.pages_ready = False

        with self.assertRaises(ProvisionPending):
            self.orchestrator().run()

        pending = self.state_store.load()
        assert pending.rotation is not None
        self.assertEqual(pending.rotation.phase, RotationPhase.DNS_CREATED)
        self.assertTrue(pending.generation_blocked)

        self.github.pages_ready = True
        completed = self.orchestrator().run()
        self.assertIsNone(completed.rotation)
        self.assertEqual([name for name, _ in self.github.operations].count("create"), 1)


class FakeCloudflareTransport:
    def __init__(self, records: list[dict] | None = None) -> None:
        self.records = list(records or [])
        self.calls: list[tuple[str, str, dict | None]] = []

    def request(self, method: str, path: str, payload: dict | None = None) -> dict:
        self.calls.append((method, path, payload))
        if method == "GET":
            return {"success": True, "result": self.records, "result_info": {"total_pages": 1}}
        if method == "POST":
            assert payload is not None
            record = {"id": "new-record", **payload}
            self.records.append(record)
            return {"success": True, "result": record}
        raise AssertionError(f"unexpected request: {method} {path}")


class CloudflareDNSTests(unittest.TestCase):
    def client(self, transport: FakeCloudflareTransport) -> CloudflareDNS:
        return CloudflareDNS(
            zone_id="a" * 32,
            zone_name="telacore.org",
            transport=transport,
        )

    def test_missing_record_is_created_dns_only_with_exact_target(self) -> None:
        transport = FakeCloudflareTransport()

        self.client(transport).ensure_cname(
            "wirtelprimpf-0001.telacore.org",
            "h234598.github.io",
            comment="Managed by Wirtelprimpf-generator transaction migration-0001",
        )

        posts = [call for call in transport.calls if call[0] == "POST"]
        self.assertEqual(len(posts), 1)
        payload = posts[0][2]
        assert payload is not None
        self.assertEqual(payload["type"], "CNAME")
        self.assertEqual(payload["content"], "h234598.github.io")
        self.assertFalse(payload["proxied"])
        self.assertEqual(payload["ttl"], 1)

    def test_identical_dns_only_cname_is_idempotently_reused(self) -> None:
        transport = FakeCloudflareTransport([
            {
                "id": "existing",
                "type": "CNAME",
                "name": "wirtelprimpf-0001.telacore.org",
                "content": "H234598.github.io.",
                "proxied": False,
            }
        ])

        self.client(transport).ensure_cname(
            "wirtelprimpf-0001.telacore.org",
            "h234598.github.io",
            comment="managed",
        )

        self.assertFalse(any(call[0] == "POST" for call in transport.calls))

    def test_conflicting_record_is_never_updated_or_deleted(self) -> None:
        transport = FakeCloudflareTransport([
            {
                "id": "foreign",
                "type": "A",
                "name": "wirtelprimpf-0001.telacore.org",
                "content": "192.0.2.10",
                "proxied": True,
            }
        ])

        with self.assertRaisesRegex(DNSConflictError, "refusing"):
            self.client(transport).ensure_cname(
                "wirtelprimpf-0001.telacore.org",
                "h234598.github.io",
                comment="managed",
            )

        self.assertEqual([method for method, _, _ in transport.calls], ["GET"])


if __name__ == "__main__":
    unittest.main()
