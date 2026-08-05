from __future__ import annotations

import copy
import json
import stat
import tempfile
import unittest
from pathlib import Path

from wirtelprimpf_platform.cloudflare_snapshot import (
    SNAPSHOT_VERSION,
    CloudflareSnapshotError,
    read_snapshot,
    write_snapshot,
)


def snapshot() -> dict:
    return {
        "schema_version": SNAPSHOT_VERSION,
        "captured_at": "2026-08-05T07:00:00Z",
        "zone": "telacore.org",
        "ruleset": {
            "id": "ruleset-1",
            "version": 15,
            "security_rule_hash": "a" * 64,
            "rules": [{"ref": "security", "action": "rewrite"}],
        },
        "dns_records": [{"id": "record-1", "name": "example.telacore.org", "type": "A"}],
        "quota": {"used": 52, "limit": 1000},
        "alias_dns_answers": {"wirtelprimpf-story.telacore.org": []},
    }


class CloudflareSnapshotTests(unittest.TestCase):
    def test_roundtrip_is_canonical_private_and_hash_stable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "private" / "cloudflare.json"
            first_hash = write_snapshot(path, snapshot())
            loaded, second_hash = read_snapshot(path)
            self.assertEqual(first_hash, second_hash)
            self.assertEqual(loaded, snapshot())
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)
            self.assertEqual(path.read_bytes(), path.read_bytes())

    def test_key_order_does_not_change_canonical_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            first = Path(temporary) / "first.json"
            second = Path(temporary) / "second.json"
            original = snapshot()
            reordered = json.loads(json.dumps(original))
            reordered["ruleset"] = {key: reordered["ruleset"][key] for key in reversed(tuple(reordered["ruleset"]))}
            self.assertEqual(write_snapshot(first, original), write_snapshot(second, reordered))
            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_credentials_are_rejected_before_any_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "private" / "cloudflare.json"
            for field, value in (("api_token", "not-written"), ("authorization_header", "Bearer x")):
                invalid = copy.deepcopy(snapshot())
                invalid["ruleset"][field] = value
                with self.subTest(field=field), self.assertRaises(CloudflareSnapshotError):
                    write_snapshot(path, invalid)
            self.assertFalse(path.exists())

    def test_invalid_snapshot_and_symlinked_paths_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            invalid = copy.deepcopy(snapshot())
            invalid["quota"] = {"used": 1001, "limit": 1000}
            with self.assertRaises(CloudflareSnapshotError):
                write_snapshot(root / "invalid.json", invalid)

            target = root / "target.json"
            target.write_text("outside", encoding="utf-8")
            linked = root / "linked.json"
            linked.symlink_to(target)
            with self.assertRaises(CloudflareSnapshotError):
                write_snapshot(linked, snapshot())
            self.assertEqual(target.read_text(encoding="utf-8"), "outside")

    def test_missing_or_malformed_snapshot_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "snapshot.json"
            path.write_text("not-json", encoding="utf-8")
            with self.assertRaises(CloudflareSnapshotError):
                read_snapshot(path)

    def test_snapshot_with_open_permissions_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "snapshot.json"
            write_snapshot(path, snapshot())
            path.chmod(0o640)
            with self.assertRaises(CloudflareSnapshotError):
                read_snapshot(path)


if __name__ == "__main__":
    unittest.main()
