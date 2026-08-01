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
        self.assertIn("git_remote push --atomic", normalized)
        self.assertIn(
            "--force-with-lease=refs/heads/$generator_head:$generator_expected_head",
            normalized,
        )
        self.assertIn('\":refs/heads/$generator_head\"', normalized)
        self.assertIn("rulesets", normalized)
        self.assertIn("branch_protection", normalized)
        self.assertIn("/tmp/wirtelprimpf-merge-policy.", normalized)
        self.assertIn("indirect-merges", self.document)
        self.assertIn("== MERGED", self.task3_merge)
        self.assertIn(".mergeCommit.oid", self.task3_merge)

    def test_task3_runs_git_as_teladi_with_ephemeral_authenticated_credentials(self) -> None:
        normalized = " ".join(self.task3_merge.split())
        self.assertIn("test \"$(id -u)\" = 0", self.task3_merge)
        self.assertIn("runuser -u teladi -- env -i", normalized)
        self.assertIn("HOME=/home/teladi", normalized)
        self.assertIn("USER=teladi", normalized)
        self.assertIn("LOGNAME=teladi", normalized)
        self.assertIn("GH_TOKEN=\"$task3_ephemeral_token\"", normalized)
        self.assertIn('"/user"', self.task3_merge)
        self.assertIn("credential.helper=", self.task3_merge)
        self.assertIn("!/usr/bin/gh auth git-credential", self.task3_merge)
        self.assertNotIn("gh auth setup-git", self.task3_merge)
        self.assertNotIn("safe.directory", self.task3_merge)
        self.assertLess(
            self.task3_merge.index('"/user"'),
            self.task3_merge.index("git commit-tree"),
        )

    def test_task3_policy_and_pr_identity_gates_are_strictly_fail_closed(self) -> None:
        self.assertIn('type == "array" and length == 0', self.task3_merge)
        self.assertNotIn("blocking_rules=", self.task3_merge)
        self.assertIn("classic_protection_status", self.task3_merge)
        self.assertIn('test "$classic_protection_status" = 404', self.task3_merge)
        self.assertIn("headRefName", self.task3_merge)
        self.assertIn("isCrossRepository", self.task3_merge)
        self.assertIn("headRepository", self.task3_merge)
        self.assertIn("nameWithOwner", self.task3_merge)
        self.assertIn(
            "canonical_origin=https://github.com/H234598/Wirtelprimpf-generator.git",
            self.task3_merge,
        )
        self.assertIn("git remote get-url --push origin", self.task3_merge)
        self.assertIn(
            'generator_merge_message="Merge pull request #${generator_pr_number} from ${generator_head}"',
            self.task3_merge,
        )
        self.assertEqual(self.task3_merge.count("git branch --show-current"), 1)

    def test_step4_rechecks_the_exact_same_repository_pr_head(self) -> None:
        task3_start = self.document.index("### Task 3:")
        step4_start = self.document.index("**Step 4: Open the pull request", task3_start)
        step5_start = self.document.index("**Step 5: Merge through GitHub", step4_start)
        step4 = self.document[step4_start:step5_start]
        self.assertIn("headRefName", step4)
        self.assertIn("isCrossRepository", step4)
        self.assertIn("headRepository", step4)
        self.assertIn("nameWithOwner", step4)
        self.assertIn('"/user"', step4)

    def test_task3_has_a_durable_idempotent_remote_commit_receipt(self) -> None:
        for state in ("planned", "remote_committed", "verified"):
            self.assertIn(state, self.task3_merge)
        self.assertIn("write_task3_receipt", self.task3_merge)
        self.assertIn("receipt_parent=/home/teladi/.local/state/wirtelprimpf", self.task3_merge)
        self.assertLess(
            self.task3_merge.index('realpath -e -- "$receipt_parent"'),
            self.task3_merge.index('install -d -m0700 "$receipt_dir"'),
        )
        self.assertIn("task3_remote_committed=1", self.task3_merge)
        self.assertIn("task3_push_started=1", self.task3_merge)
        self.assertIn("REMOTE COMMIT COMPLETE; VERIFICATION PENDING", self.task3_merge)
        self.assertIn("PUSH OUTCOME REQUIRES RECEIPT RECONCILIATION", self.task3_merge)
        self.assertIn("planned_remote_committed", self.task3_merge)
        self.assertLess(
            self.task3_merge.index("task3_push_started=1"),
            self.task3_merge.index("git_remote push --atomic"),
        )
        self.assertLess(
            self.task3_merge.index("git_remote push --atomic"),
            self.task3_merge.index("task3_remote_committed=1"),
        )
        self.assertLess(
            self.task3_merge.index("task3_remote_committed=1"),
            self.task3_merge.index("write_task3_receipt remote_committed"),
        )

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
        self.assertIn("after-push-before-receipt", self.harness)
        self.assertIn("planned-remote-committed-reconciled", self.harness)
        self.assertIn("remote-committed-api-failure", self.harness)
        self.assertIn("verified-without-second-push", self.harness)

    def test_normative_step9_rollback_prolog_masks_signals_before_recovery(self) -> None:
        function_start = self.deployment.index("rollback_deployment() {")
        function_end = self.deployment.index("\n}\n\ntrap 'rollback_deployment", function_start)
        rollback = self.deployment[function_start:function_end]
        disarm = rollback.index("trap - EXIT")
        mask = rollback.index("trap '' HUP INT TERM")
        recovery = rollback.index("set +e")
        acquire = rollback.index("acquire_settings_lock_bounded")
        release = rollback.rindex("release_settings_lock")
        final_exit = rollback.rindex('exit "$final_status"')
        self.assertLess(disarm, mask)
        self.assertLess(mask, recovery)
        self.assertLess(recovery, acquire)
        self.assertLess(acquire, release)
        self.assertLess(release, final_exit)
        self.assertNotIn("trap - EXIT HUP INT TERM", rollback)

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
