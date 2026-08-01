from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_PLAN = ROOT / "docs/superpowers/plans/2026-08-01-public-site-copy-and-rollout.md"


def _code_block_after(document: str, marker: str) -> str:
    marker_offset = document.index(marker)
    fence_offset = document.index("```bash\n", marker_offset) + len("```bash\n")
    fence_end = document.index("\n```", fence_offset)
    return document[fence_offset:fence_end]


class RolloutPlanContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = PUBLIC_PLAN.read_text(encoding="utf-8")
        cls.task3_merge = _code_block_after(
            cls.document,
            "**Step 5: Merge through GitHub and record the immutable generator SHA**",
        )
        cls.smoke_api = _code_block_after(
            cls.document,
            "**Step 5: Verify APIs, security headers, model choices, and local status**",
        )
        cls.smoke_sync = _code_block_after(
            cls.document,
            "**Step 6: Perform a fully automated reversible HTTP/CLI live-sync and conflict smoke**",
        )
        cls.deployment = _code_block_after(
            cls.document,
            "**Step 9: Execute Steps 1–8 through one guarded deployment transaction**",
        )
        cls.harness = _code_block_after(
            cls.document,
            "**Step 10: Syntax-check and failure-inject the restore semantics in isolation**",
        )

    def test_task3_uses_an_exact_base_lease_cas_and_verifies_the_indirect_merge(self) -> None:
        normalized = " ".join(self.task3_merge.split())
        self.assertNotIn("gh pr merge", normalized)
        self.assertIn("git commit-tree", normalized)
        self.assertIn(
            "--force-with-lease=refs/heads/main:$generator_base_before",
            normalized,
        )
        self.assertIn("git push --atomic", normalized)
        self.assertIn(
            "--force-with-lease=refs/heads/$generator_head:$generator_expected_head",
            normalized,
        )
        self.assertIn('\":refs/heads/$generator_head\"', normalized)
        self.assertIn("rulesets", normalized)
        self.assertIn("branch_protection", normalized)
        self.assertIn("required_linear_history", normalized)
        self.assertIn("/tmp/wirtelprimpf-merge-policy.", normalized)
        self.assertIn("indirect-merges", self.document)
        self.assertIn(".state == \"MERGED\"", self.task3_merge)
        self.assertIn(".mergeCommit.oid", self.task3_merge)

    def test_step9_contains_the_exact_smokes_and_orders_marker_producer_before_consumer(self) -> None:
        self.assertIn(self.smoke_api, self.deployment)
        self.assertIn(self.smoke_sync, self.deployment)
        self.assertNotIn("Execute the exact Step-5", self.deployment)
        producer = self.deployment.index("marker_path.write_text")
        consumer = self.deployment.index(
            "smoke_owned_revision=\"$(jq -er '.revision' "
            '"$deploy_backup/smoke-owned-revision.json")"'
        )
        self.assertLess(producer, consumer)

    def test_erratum_keeps_runtime_old_until_the_guarded_task4_cas(self) -> None:
        self.assertIn(
            "Task 3 verändert den Runtime-Checkout nicht",
            self.document,
        )
        self.assertIn('test "$runtime_sha_before" != "$target_sha"', self.deployment)
        self.assertIn(
            "Erst nach dem Task-4-CAS",
            self.document,
        )

    def test_step10_contains_real_signal_and_lease_race_injections(self) -> None:
        self.assertIn('kill -TERM "$recovery_pid"', self.harness)
        self.assertIn('kill -HUP "$recovery_pid"', self.harness)
        self.assertIn("lease-race", self.harness)
        self.assertIn("masked-runtime", self.harness)
        self.assertIn("timer-persistent-enablement", self.harness)

    def test_normative_deployment_and_harness_are_valid_bash(self) -> None:
        for name, script in (
            ("task3_merge", self.task3_merge),
            ("deployment", self.deployment),
            ("harness", self.harness),
        ):
            with self.subTest(name=name):
                result = subprocess.run(
                    ["bash", "-n"],
                    input=script,
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=10,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_make_check_runs_the_rollout_contract(self) -> None:
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn(
            "$(PYTHON) -m unittest tests.test_rollout_plan_contract",
            makefile,
        )

    def test_disposable_step10_harness_executes_successfully(self) -> None:
        result = subprocess.run(
            ["bash"],
            input=self.harness,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
