from __future__ import annotations

import json
import os
import signal
import subprocess
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_PLAN = ROOT / "docs/superpowers/plans/2026-08-01-public-site-copy-and-rollout.md"


def _code_block_after(document: str, marker: str) -> str:
    marker_offset = document.index(marker)
    fence_offset = document.index("```bash\n", marker_offset) + len("```bash\n")
    fence_end = document.index("\n```", fence_offset)
    return document[fence_offset:fence_end]


def _marked_block(script: str, marker: str) -> str:
    start_marker = f"# BEGIN {marker}"
    end_marker = f"# END {marker}"
    start = script.index(start_marker) + len(start_marker)
    end = script.index(end_marker, start)
    return script[start:end].strip()


def _shell_function(script: str, name: str) -> str:
    start_marker = f"{name}() {{\n"
    start = script.index(start_marker)
    end = script.index("\n}\n", start) + len("\n}")
    return script[start:end]


def _quoted_heredoc(script: str, marker: str) -> tuple[str, str]:
    opener = f"<<'{marker}'"
    opener_offset = script.index(opener) + len(opener)
    body_offset = script.index("\n", opener_offset) + 1
    body_end = script.index(f"\n{marker}", body_offset)
    return script[:body_offset], script[body_offset:body_end]


class RolloutPlanContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = PUBLIC_PLAN.read_text(encoding="utf-8")
        cls.task3_step1 = _code_block_after(
            cls.document,
            "**Step 1: Run the complete local matrix from a clean branch**",
        )
        cls.task3_step2 = _code_block_after(
            cls.document,
            "**Step 2: Perform a fresh spec and security diff review**",
        )
        cls.task3_step3 = _code_block_after(
            cls.document,
            "**Step 3: Incorporate newly arrived user commits, rerun, and push without force**",
        )
        cls.task3_step4 = _code_block_after(
            cls.document,
            "**Step 4: Open the pull request and wait for all checks**",
        )
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
        task5_offset = cls.document.index("### Task 5:")
        cls.task5_step1 = _code_block_after(
            cls.document[task5_offset:],
            "**Step 1: Verify the archive checkout and remote are clean/current**",
        )
        cls.task5_step3 = _code_block_after(
            cls.document[task5_offset:],
            "**Step 3: Replace both old pins",
        )
        cls.task5_step4 = _code_block_after(
            cls.document[task5_offset:],
            "**Step 4: Validate the two pins and exact diff**",
        )
        cls.task5_step5 = _code_block_after(
            cls.document[task5_offset:],
            "**Step 5: Commit the isolated archive pin and open its pull request**",
        )

    def _make_merge_fixture(self, tmp: str) -> dict[str, str]:
        repo = Path(tmp) / "merge-source"
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.name", "Fixture"], check=True)
        subprocess.run(
            ["git", "-C", str(repo), "config", "user.email", "fixture@example.invalid"],
            check=True,
        )
        (repo / "story").write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "story"], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "base"], check=True)
        base = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        (repo / "story").write_text("reviewed head\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "-am", "reviewed"], check=True)
        head = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        head_tree = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", f"{head}^{{tree}}"],
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        merge_date = subprocess.run(
            ["git", "-C", str(repo), "show", "-s", "--format=%cI", head],
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        message = "Merge pull request #17 from feature/reviewed"
        merge_env = os.environ.copy()
        merge_env.update(
            {
                "GIT_AUTHOR_NAME": "H234598",
                "GIT_AUTHOR_EMAIL": "54270221+H234598@users.noreply.github.com",
                "GIT_AUTHOR_DATE": merge_date,
                "GIT_COMMITTER_NAME": "H234598",
                "GIT_COMMITTER_EMAIL": "54270221+H234598@users.noreply.github.com",
                "GIT_COMMITTER_DATE": merge_date,
            }
        )

        def commit_tree(tree: str) -> str:
            return subprocess.run(
                ["git", "-C", str(repo), "commit-tree", tree, "-p", base, "-p", head],
                input=f"{message}\n",
                text=True,
                capture_output=True,
                check=True,
                env=merge_env,
            ).stdout.strip()

        expected_merge = commit_tree(head_tree)
        malicious_blob = subprocess.run(
            ["git", "-C", str(repo), "hash-object", "-w", "--stdin"],
            input="unreviewed payload\n",
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        malicious_tree = subprocess.run(
            ["git", "-C", str(repo), "mktree"],
            input=f"100644 blob {malicious_blob}\tunreviewed\n",
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        malicious_merge = commit_tree(malicious_tree)
        return {
            "repo": str(repo),
            "base": base,
            "head": head,
            "head_tree": head_tree,
            "merge_date": merge_date,
            "message": message,
            "expected_merge": expected_merge,
            "malicious_tree": malicious_tree,
            "malicious_merge": malicious_merge,
        }

    @staticmethod
    def _receipt_for_fixture(fixture: dict[str, str]) -> dict[str, object]:
        return {
            "version": 2,
            "state": "planned",
            "actor_login": "H234598",
            "actor_id": 54270221,
            "repository_id": "R_kgDOTpr2BA",
            "repository": "H234598/Wirtelprimpf-generator",
            "canonical_origin": "https://github.com/H234598/Wirtelprimpf-generator.git",
            "pr_number": 17,
            "head_ref": "feature/reviewed",
            "expected_head": fixture["head"],
            "base_before": fixture["base"],
            "head_tree": fixture["head_tree"],
            "merge_date": fixture["merge_date"],
            "merge_message": fixture["message"],
            "merge_sha": fixture["expected_merge"],
        }

    def test_task3_uses_an_exact_base_lease_cas_and_verifies_the_indirect_merge(self) -> None:
        normalized = " ".join(self.task3_merge.split())
        self.assertNotIn("gh pr merge", normalized)
        self.assertIn("commit-tree", normalized)
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

    def test_task5_archive_operations_are_inside_literal_teladi_fences(self) -> None:
        archive_path = "/home/teladi/.local/share/wirtelprimpf/archives/Wirtelprimpf-0001"
        for name, script, marker in (
            ("step1", self.task5_step1, "TASK5_STEP1_TELADI"),
            ("step3", self.task5_step3, "TASK5_STEP3_TELADI"),
            ("step4", self.task5_step4, "TASK5_STEP4_TELADI"),
            ("step5", self.task5_step5, "TASK5_STEP5_TELADI"),
        ):
            with self.subTest(name=name):
                outer, child = _quoted_heredoc(script, marker)
                normalized_outer = " ".join(outer.split())
                self.assertIn("test \"$(id -u)\" = 0", outer)
                self.assertIn(
                    "/usr/sbin/runuser -u teladi -- /usr/bin/env -i",
                    normalized_outer,
                )
                self.assertIn("HOME=/home/teladi", normalized_outer)
                self.assertIn('test "$(id -u)" = 1000', child)
                self.assertIn('test "$(id -g)" = 1000', child)
                self.assertIn(archive_path, child)
                root_shell = script.replace(child, "", 1)
                self.assertNotIn(archive_path, root_shell)
                self.assertNotIn("$archive_checkout", root_shell)

        self.assertIn("os.replace(part, workflow)", self.task5_step3)
        self.assertIn("workflow.lstat()", self.task5_step3)
        self.assertIn("st.st_uid == 1000 and st.st_gid == 1000", self.task5_step3)
        self.assertIn("if old_count != 2", self.task5_step3)
        self.assertIn("if new_count != 2", self.task5_step3)

    def test_task5_literal_fence_executes_as_teladi_without_root_expansion(self) -> None:
        if os.geteuid() != 0 or not Path("/usr/sbin/runuser").is_file():
            self.skipTest("the real Task-5 runuser probe requires root and /usr/sbin/runuser")
        try:
            teladi_ids = subprocess.run(
                ["id", "-u", "teladi"],
                text=True,
                capture_output=True,
                check=True,
            ).stdout.strip(), subprocess.run(
                ["id", "-g", "teladi"],
                text=True,
                capture_output=True,
                check=True,
            ).stdout.strip()
        except subprocess.CalledProcessError:
            self.skipTest("the real Task-5 runuser probe requires the teladi account")
        if teladi_ids != ("1000", "1000"):
            self.skipTest("the Task-5 contract pins teladi to UID/GID 1000")

        prefix, _child = _quoted_heredoc(self.task5_step1, "TASK5_STEP1_TELADI")
        probe = (
            "root_only=ROOT_MUST_NOT_EXPAND_THIS\n"
            f"{prefix}"
            "set -Eeuo pipefail\n"
            'test "$(id -u)" = 1000\n'
            'test "$(id -g)" = 1000\n'
            'test "${root_only-unexpanded}" = unexpanded\n'
            'printf "%s:%s:%s\\n" "$(id -u)" "$(id -g)" "${root_only-unexpanded}"\n'
            "TASK5_STEP1_TELADI\n"
        )
        result = subprocess.run(
            ["bash"],
            input=probe,
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "1000:1000:unexpanded\n")
        self.assertNotIn("ROOT_MUST_NOT_EXPAND_THIS", result.stdout + result.stderr)

    def test_task5_workflow_rewriter_executes_as_teladi_and_changes_only_two_pins(self) -> None:
        if os.geteuid() != 0 or not Path("/usr/sbin/runuser").is_file():
            self.skipTest("the real Task-5 workflow rewrite probe requires root and runuser")
        try:
            teladi_uid = int(
                subprocess.run(
                    ["id", "-u", "teladi"],
                    text=True,
                    capture_output=True,
                    check=True,
                ).stdout
            )
            teladi_gid = int(
                subprocess.run(
                    ["id", "-g", "teladi"],
                    text=True,
                    capture_output=True,
                    check=True,
                ).stdout
            )
        except subprocess.CalledProcessError:
            self.skipTest("the real Task-5 workflow rewrite probe requires the teladi account")
        if (teladi_uid, teladi_gid) != (1000, 1000):
            self.skipTest("the Task-5 contract pins teladi to UID/GID 1000")

        _prefix, rewrite = _quoted_heredoc(self.task5_step3, "TASK5_REWRITE_PY")
        old_sha = "1" * 40
        new_sha = "2" * 40
        original = (
            "jobs:\n"
            "  publish:\n"
            "    uses: H234598/Wirtelprimpf-generator/.github/workflows/"
            f"archive-pages.yml@{old_sha}\n"
            "    with:\n"
            f'      factory_ref: "{old_sha}"\n'
        )
        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-task5-rewrite-") as tmp:
            root = Path(tmp)
            os.chown(root, teladi_uid, teladi_gid)
            root.chmod(0o700)
            workflow = root / "pages.yml"
            workflow.write_text(original, encoding="utf-8")
            os.chown(workflow, teladi_uid, teladi_gid)
            workflow.chmod(0o644)
            result = subprocess.run(
                [
                    "/usr/sbin/runuser",
                    "-u",
                    "teladi",
                    "--",
                    "/usr/bin/env",
                    "-i",
                    "HOME=/home/teladi",
                    "PATH=/usr/local/bin:/usr/bin:/bin",
                    "/usr/bin/python3",
                    "-",
                    str(workflow),
                    new_sha,
                ],
                input=rewrite,
                text=True,
                capture_output=True,
                check=False,
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            updated = workflow.read_text(encoding="utf-8")
            metadata = workflow.stat()
        self.assertEqual(updated.count(new_sha), 2)
        self.assertNotIn(old_sha, updated)
        self.assertEqual(metadata.st_uid, teladi_uid)
        self.assertEqual(metadata.st_gid, teladi_gid)
        self.assertEqual(metadata.st_mode & 0o777, 0o644)

    def test_task3_runs_git_as_teladi_with_ephemeral_authenticated_credentials(self) -> None:
        normalized = " ".join(self.task3_merge.split())
        self.assertIn("test \"$(id -u)\" = 0", self.task3_merge)
        self.assertIn("runuser -u teladi -- /usr/bin/env -i", normalized)
        self.assertIn("HOME=/home/teladi", normalized)
        self.assertIn("USER=teladi", normalized)
        self.assertIn("LOGNAME=teladi", normalized)
        self.assertNotIn('GH_TOKEN="$task3_ephemeral_token" \\', self.task3_merge)
        self.assertIn('"/user"', self.task3_merge)
        self.assertIn("credential.helper=", self.task3_merge)
        self.assertIn("!/usr/bin/gh auth git-credential", self.task3_merge)
        self.assertIn("core.hooksPath=/dev/null", self.task3_merge)
        self.assertNotIn("gh auth setup-git", self.task3_merge)
        self.assertNotIn("safe.directory", self.task3_merge)

    def test_task3_steps_one_through_three_enter_clean_teladi_context(self) -> None:
        for name, script in (
            ("step1", self.task3_step1),
            ("step2", self.task3_step2),
            ("step3", self.task3_step3),
        ):
            with self.subTest(name=name):
                normalized = " ".join(script.split())
                self.assertIn("/usr/sbin/runuser -u teladi -- /usr/bin/env -i", normalized)
                self.assertIn('test "$(id -u)" = 1000', script)
                self.assertIn('test "$(id -g)" = 1000', script)

    def test_step1_profile_builds_and_validators_stay_inside_teladi_fence(self) -> None:
        section_start = self.document.index(
            "**Step 1: Run the complete local matrix from a clean branch**",
        )
        section_end = self.document.index(
            "**Step 2: Perform a fresh spec and security diff review**",
            section_start,
        )
        step1_section = self.document[section_start:section_end]
        normalized = " ".join(self.task3_step1.replace("\\\n", "").split())
        hub_build = (
            'WIRTELPRIMPF_DATA_ROOT="$PWD/web/fixtures/site" '
            'WIRTELPRIMPF_MEDIA_MANIFEST="$PWD/data/media-manifest.json" '
            "WIRTELPRIMPF_SITE_PROFILE=hub "
            "WIRTELPRIMPF_SITE_URL=https://wirtelprimpf.telacore.org "
            "npm --prefix web run build"
        )
        hub_validate = (
            "python3 scripts/validate_pages_artifact.py web/dist "
            "--expected-domain wirtelprimpf.telacore.org"
        )
        archive_build = (
            'WIRTELPRIMPF_DATA_ROOT="$PWD/web/fixtures/site" '
            'WIRTELPRIMPF_MEDIA_MANIFEST="$PWD/data/media-manifest.json" '
            "WIRTELPRIMPF_SITE_PROFILE=archive "
            "WIRTELPRIMPF_SITE_URL=https://wirtelprimpf-0001.telacore.org "
            "npm --prefix web run build"
        )
        archive_validate = (
            "python3 scripts/validate_pages_artifact.py web/dist "
            "--expected-domain wirtelprimpf-0001.telacore.org"
        )
        for command in (hub_build, hub_validate, archive_build, archive_validate):
            self.assertIn(command, normalized)
        ordered = (
            normalized.index("/usr/sbin/runuser -u teladi -- /usr/bin/env -i"),
            normalized.index('test "$(id -u)" = 1000'),
            normalized.index('test "$(id -g)" = 1000'),
            normalized.index(hub_build),
            normalized.index(hub_validate),
            normalized.index(archive_build),
            normalized.index(archive_validate),
            normalized.rindex("TASK3_STEP1_TELADI"),
        )
        self.assertEqual(ordered, tuple(sorted(ordered)))
        self.assertEqual(normalized.count("npm --prefix web run build"), 2)
        self.assertNotIn("Then repeat the two profile builds", step1_section)

    def test_step3_actual_prewrite_gate_precedes_the_first_fetch(self) -> None:
        script = self.task3_step3
        self.assertIn("# BEGIN TASK3_STEP3_PREWRITE_GATE", script)
        gate = _marked_block(script, "TASK3_STEP3_PREWRITE_GATE")
        required_calls = (
            'generator_head="$(/usr/bin/git branch --show-current)"',
            'assert_task3_feature_branch "$generator_head"',
            "assert_canonical_origin",
            "require_task3_auth",
            "require_canonical_repository",
        )
        for call in required_calls:
            self.assertIn(call, gate)
        positions = tuple(gate.index(call) for call in required_calls)
        self.assertEqual(positions, tuple(sorted(positions)))
        gate_end = script.index("# END TASK3_STEP3_PREWRITE_GATE")
        fetch = script.index('git_remote fetch "$canonical_origin"')
        merge = script.index("core.hooksPath=/dev/null merge")
        push = script.index('git_remote push "$canonical_origin"')
        self.assertLess(gate_end, fetch)
        self.assertLess(fetch, merge)
        self.assertLess(merge, push)
        self.assertLess(script.index("set +x"), script.index("${GH_TOKEN"))

    def test_step3_branch_predicate_rejects_main_and_accepts_a_feature(self) -> None:
        self.assertIn("# BEGIN TASK3_FEATURE_BRANCH_PREDICATE", self.task3_step3)
        predicate = _marked_block(self.task3_step3, "TASK3_FEATURE_BRANCH_PREDICATE")
        script = f"set -Eeuo pipefail\n{predicate}\nassert_task3_feature_branch \"$1\"\n"
        accepted = subprocess.run(
            ["bash", "-c", script, "branch-test", "feature/reviewed"],
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
        rejected = subprocess.run(
            ["bash", "-c", script, "branch-test", "main"],
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertNotEqual(rejected.returncode, 0)

    def test_task3_identity_predicates_pin_actor_and_repository(self) -> None:
        valid_actor = json.dumps({"login": "H234598", "id": 54270221})
        valid_repository = json.dumps(
            {
                "id": "R_kgDOTpr2BA",
                "nameWithOwner": "H234598/Wirtelprimpf-generator",
            },
        )
        invalid_pairs = (
            (json.dumps({"login": "H234598", "id": 1}), valid_repository),
            (json.dumps({"id": 54270221}), valid_repository),
            (
                valid_actor,
                json.dumps(
                    {
                        "id": "R_DYNAMIC_REPLACEMENT",
                        "nameWithOwner": "H234598/Wirtelprimpf-generator",
                    },
                ),
            ),
            (
                valid_actor,
                json.dumps({"nameWithOwner": "H234598/Wirtelprimpf-generator"}),
            ),
            (
                valid_actor,
                json.dumps(
                    {
                        "id": "R_kgDOTpr2BA",
                        "nameWithOwner": "H234598/replacement",
                    },
                ),
            ),
        )
        for name, plan_script in (
            ("step3", self.task3_step3),
            ("step4", self.task3_step4),
            ("step5", self.task3_merge),
        ):
            has_marker = "# BEGIN TASK3_IDENTITY_PREDICATES" in plan_script
            with self.subTest(name=name, case="marker"):
                self.assertTrue(has_marker)
            if not has_marker:
                continue
            predicates = _marked_block(plan_script, "TASK3_IDENTITY_PREDICATES")
            actor_gate = _shell_function(plan_script, "require_task3_auth")
            repository_gate = _shell_function(
                plan_script,
                "require_canonical_repository",
            )
            script = (
                f"set -Eeuo pipefail\n{predicates}\n{actor_gate}\n{repository_gate}\n"
                'actor_json=$1\nrepository_json=$2\n'
                "task3_gh() {\n"
                '  if [[ "$1" == api && "$2" == /user ]]; then\n'
                '    printf \'%s\\n\' "$actor_json"\n'
                '  elif [[ "$1" == repo && "$2" == view ]]; then\n'
                '    test "$3" = H234598/Wirtelprimpf-generator\n'
                '    test "$4" = --json\n'
                '    test "$5" = id,nameWithOwner\n'
                '    printf \'%s\\n\' "$repository_json"\n'
                "  else\n"
                "    return 90\n"
                "  fi\n"
                "}\n"
                "require_task3_auth\n"
                "require_canonical_repository\n"
            )
            accepted = subprocess.run(
                ["bash", "-c", script, "identity-test", valid_actor, valid_repository],
                text=True,
                capture_output=True,
                check=False,
                timeout=10,
            )
            with self.subTest(name=name, case="valid"):
                self.assertEqual(accepted.returncode, 0, accepted.stderr)
            for case, (actor_json, repository_json) in enumerate(invalid_pairs):
                rejected = subprocess.run(
                    [
                        "bash",
                        "-c",
                        script,
                        "identity-test",
                        actor_json,
                        repository_json,
                    ],
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=10,
                )
                with self.subTest(name=name, case=case):
                    self.assertNotEqual(rejected.returncode, 0)
        placeholder_id = "R_" + "TEST_CANONICAL"
        self.assertNotIn(placeholder_id, self.document)
        self.assertNotIn(placeholder_id, Path(__file__).read_text(encoding="utf-8"))

    def test_steps_four_and_five_execute_the_fixed_repository_gate(self) -> None:
        for name, script, marker, first_post_gate_operation in (
            (
                "step4",
                self.task3_step4,
                "TASK3_STEP4_IDENTITY_GATE",
                'generator_head="$(/usr/bin/git branch --show-current)"',
            ),
            (
                "step5",
                self.task3_merge,
                "TASK3_STEP5_IDENTITY_GATE",
                "receipt_state=absent",
            ),
        ):
            with self.subTest(name=name):
                self.assertIn(f"# BEGIN {marker}", script)
                gate = _marked_block(script, marker)
                self.assertIn("require_task3_auth", gate)
                self.assertIn("require_canonical_repository", gate)
                self.assertLess(
                    script.index(f"# END {marker}"),
                    script.index(first_post_gate_operation),
                )

    def test_normative_fd_relay_keeps_token_out_of_argv_and_long_environment(self) -> None:
        self.assertIn("# BEGIN TASK3_FD_TOKEN_CALL", self.task3_merge)
        token_call = _marked_block(self.task3_merge, "TASK3_FD_TOKEN_CALL")
        token = b"FD_RELAY_SENTINEL_NOT_A_SECRET\0"
        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-fd-contract-") as tmp:
            probe = Path(tmp) / "probe"
            probe.write_text(
                "#!/bin/bash\n"
                "set -Eeuo pipefail\n"
                "test \"${GH_TOKEN:-}\" = FD_RELAY_SENTINEL_NOT_A_SECRET\n"
                "! tr '\\\\0' '\\\\n' </proc/self/cmdline | grep -Fq \"$GH_TOKEN\"\n"
                "! tr '\\\\0' '\\\\n' </proc/$PPID/cmdline | grep -Fq \"$GH_TOKEN\"\n"
                "printf 'probe-ok\\n'\n",
                encoding="utf-8",
            )
            probe.chmod(0o700)
            read_fd, write_fd = os.pipe()
            try:
                os.write(write_fd, token)
                os.close(write_fd)
                write_fd = -1
                script = f"""
set -Eeuo pipefail
set +x
{token_call}
relay_fd=$1
task3_ephemeral_token=
IFS= read -r -d '' task3_ephemeral_token <&"$relay_fd"
exec {{relay_fd}}<&-
test -z "${{GH_TOKEN+x}}"
! tr '\\0' '\\n' </proc/self/environ | grep -Fq "$task3_ephemeral_token"
! /usr/bin/env | grep -q '^GH_TOKEN='
task3_token_call "$2"
"""
                result = subprocess.run(
                    ["bash", "-x", "-c", script, "task3-fd-test", str(read_fd), str(probe)],
                    pass_fds=(read_fd,),
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=10,
                    env={"HOME": "/home/teladi", "PATH": "/usr/bin:/bin"},
                )
            finally:
                if write_fd >= 0:
                    os.close(write_fd)
                os.close(read_fd)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "probe-ok\n")
            self.assertNotIn("FD_RELAY_SENTINEL_NOT_A_SECRET", result.stderr)

    def test_short_token_children_disable_every_askpass_environment(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-token-env-") as tmp:
            probe = Path(tmp) / "probe"
            probe.write_text(
                "#!/bin/bash\n"
                "set -Eeuo pipefail\n"
                'test "$GIT_TERMINAL_PROMPT" = 0\n'
                'test "$GIT_ASKPASS" = /bin/false\n'
                'test "$SSH_ASKPASS" = /bin/false\n'
                'test "$GH_TOKEN" = SHORT_CHILD_SENTINEL_NOT_A_SECRET\n',
                encoding="utf-8",
            )
            probe.chmod(0o700)
            for name, plan_script in (
                ("step3", self.task3_step3),
                ("step4", self.task3_step4),
                ("step5", self.task3_merge),
            ):
                token_call = _shell_function(plan_script, "task3_token_call")
                script = f"""
set -Eeuo pipefail
{token_call}
task3_ephemeral_token=SHORT_CHILD_SENTINEL_NOT_A_SECRET
task3_token_call "$1"
"""
                result = subprocess.run(
                    ["bash", "-c", script, "token-env-test", str(probe)],
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=10,
                    env={"HOME": "/home/teladi", "PATH": "/usr/bin:/bin"},
                )
                with self.subTest(name=name):
                    self.assertEqual(result.returncode, 0, result.stderr)

    def test_normative_origin_predicate_rejects_every_extra_url(self) -> None:
        self.assertIn("# BEGIN TASK3_CANONICAL_ORIGIN", self.task3_merge)
        predicate = _marked_block(self.task3_merge, "TASK3_CANONICAL_ORIGIN")
        canonical = "https://github.com/H234598/Wirtelprimpf-generator.git"
        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-origin-contract-") as tmp:
            repo = Path(tmp) / "repo"
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", canonical], check=True)
            check_script = f"set -Eeuo pipefail\n{predicate}\ncanonical_origin=$1\nassert_canonical_origin origin\n"
            accepted = subprocess.run(
                ["bash", "-c", check_script, "origin-test", canonical],
                cwd=repo,
                text=True,
                capture_output=True,
                check=False,
                timeout=10,
            )
            self.assertEqual(accepted.returncode, 0, accepted.stderr)

            subprocess.run(
                ["git", "-C", str(repo), "remote", "set-url", "--add", "--push", "origin", canonical],
                check=True,
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo),
                    "remote",
                    "set-url",
                    "--add",
                    "--push",
                    "origin",
                    "https://example.invalid/second.git",
                ],
                check=True,
            )
            rejected = subprocess.run(
                ["bash", "-c", check_script, "origin-test", canonical],
                cwd=repo,
                text=True,
                capture_output=True,
                check=False,
                timeout=10,
            )
            self.assertNotEqual(rejected.returncode, 0)

    def test_normative_git_remote_disables_a_real_pre_push_hook(self) -> None:
        self.assertIn("# BEGIN TASK3_FD_TOKEN_CALL", self.task3_merge)
        self.assertIn("# BEGIN TASK3_GIT_REMOTE", self.task3_merge)
        token_call = _marked_block(self.task3_merge, "TASK3_FD_TOKEN_CALL")
        git_remote = _marked_block(self.task3_merge, "TASK3_GIT_REMOTE")
        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-hook-contract-") as tmp:
            source = Path(tmp) / "source"
            remote = Path(tmp) / "remote.git"
            leak = Path(tmp) / "hook-leak"
            subprocess.run(["git", "init", "-q", str(source)], check=True)
            subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
            subprocess.run(["git", "-C", str(source), "config", "user.name", "Contract Test"], check=True)
            subprocess.run(["git", "-C", str(source), "config", "user.email", "contract@example.invalid"], check=True)
            (source / "tracked").write_text("reviewed\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(source), "add", "tracked"], check=True)
            subprocess.run(["git", "-C", str(source), "commit", "-q", "-m", "reviewed"], check=True)
            hook = source / ".git/hooks/pre-push"
            hook.write_text(
                f"#!/bin/sh\nprintf '%s' \"${{GH_TOKEN:-missing}}\" >'{leak}'\nexit 91\n",
                encoding="utf-8",
            )
            hook.chmod(0o700)
            read_fd, write_fd = os.pipe()
            try:
                os.write(write_fd, b"HOOK_SENTINEL_NOT_A_SECRET\0")
                os.close(write_fd)
                write_fd = -1
                script = f"""
set -Eeuo pipefail
{token_call}
{git_remote}
canonical_origin=https://github.com/H234598/Wirtelprimpf-generator.git
relay_fd=$1
task3_ephemeral_token=
IFS= read -r -d '' task3_ephemeral_token <&"$relay_fd"
exec {{relay_fd}}<&-
git_remote -C "$2" push "$3" HEAD:refs/heads/main
"""
                result = subprocess.run(
                    ["bash", "-c", script, "hook-test", str(read_fd), str(source), str(remote)],
                    pass_fds=(read_fd,),
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=10,
                    env={"HOME": "/home/teladi", "PATH": "/usr/bin:/bin"},
                )
            finally:
                if write_fd >= 0:
                    os.close(write_fd)
                os.close(read_fd)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(leak.exists(), "the real pre-push hook observed the tokenized Git process")
            remote_head = subprocess.run(
                ["git", "-C", str(remote), "rev-parse", "refs/heads/main"],
                text=True,
                capture_output=True,
                check=True,
            ).stdout.strip()
            local_head = subprocess.run(
                ["git", "-C", str(source), "rev-parse", "HEAD"],
                text=True,
                capture_output=True,
                check=True,
            ).stdout.strip()
            self.assertEqual(remote_head, local_head)

    def test_git_remote_clears_url_specific_authorization_extraheader(self) -> None:
        received_paths: list[str] = []
        received_authorizations: list[str] = []

        class HeaderProbeHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                received_paths.append(self.path)
                received_authorizations.extend(self.headers.get_all("Authorization") or [])
                self.send_response(403)
                self.end_headers()

            def log_message(self, format: str, *args: object) -> None:
                del format, args

        server = ThreadingHTTPServer(("127.0.0.1", 0), HeaderProbeHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        remote_url = f"http://{host}:{port}/repository.git"
        sentinel = "EXTRAHEADER_SENTINEL_NOT_A_SECRET"
        try:
            with tempfile.TemporaryDirectory(prefix="wirtelprimpf-extraheader-") as tmp:
                for name, plan_script in (
                    ("step3", self.task3_step3),
                    ("step5", self.task3_merge),
                ):
                    repo = Path(tmp) / name
                    subprocess.run(["git", "init", "-q", str(repo)], check=True)
                    subprocess.run(
                        [
                            "git",
                            "-C",
                            str(repo),
                            "config",
                            f"http.{remote_url}.extraHeader",
                            f"Authorization: Basic {sentinel}",
                        ],
                        check=True,
                    )
                    git_remote = _shell_function(plan_script, "git_remote")
                    script = f"""
set -Eeuo pipefail
{git_remote}
canonical_origin=$2
task3_token_call() {{
  /usr/bin/env -i \
    HOME=/home/teladi \
    PATH=/usr/bin:/bin \
    GH_TOKEN=EXTRAHEADER_CHILD_TOKEN_NOT_A_SECRET \
    GIT_TERMINAL_PROMPT=0 \
    "$@"
}}
if git_remote -C "$1" ls-remote "$2"; then
  exit 91
fi
"""
                    result = subprocess.run(
                        ["bash", "-c", script, "extraheader-test", str(repo), remote_url],
                        text=True,
                        capture_output=True,
                        check=False,
                        timeout=10,
                        env={"HOME": "/home/teladi", "PATH": "/usr/bin:/bin"},
                    )
                    with self.subTest(name=name):
                        self.assertEqual(result.returncode, 0, result.stderr)
            self.assertGreaterEqual(len(received_paths), 2)
            self.assertFalse(
                any(sentinel in value for value in received_authorizations),
                received_authorizations,
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_git_remote_neutralizes_configured_askpass_after_helper_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-askpass-") as tmp:
            root = Path(tmp)
            askpass = root / "askpass"
            askpass.write_text(
                "#!/bin/bash\n"
                "set -Eeuo pipefail\n"
                'printf "%s" "${GH_TOKEN:-missing}" >"$ASKPASS_LEAK_PATH"\n'
                "printf 'credential-from-forbidden-askpass\\n'\n",
                encoding="utf-8",
            )
            askpass.chmod(0o700)
            for name, plan_script in (
                ("step3", self.task3_step3),
                ("step5", self.task3_merge),
            ):
                repo = root / f"repo-{name}"
                leak = root / f"askpass-leak-{name}"
                subprocess.run(["git", "init", "-q", str(repo)], check=True)
                subprocess.run(
                    ["git", "-C", str(repo), "config", "core.askPass", str(askpass)],
                    check=True,
                )
                git_remote = _shell_function(plan_script, "git_remote")
                script = f"""
set -Eeuo pipefail
{git_remote}
askpass_leak_path=$2
task3_token_call() {{
  /usr/bin/env -i \
    HOME=/home/teladi \
    PATH=/usr/bin:/bin \
    GH_TOKEN=ASKPASS_CHILD_TOKEN_NOT_A_SECRET \
    GIT_TERMINAL_PROMPT=0 \
    ASKPASS_LEAK_PATH="$askpass_leak_path" \
    "$@"
}}
if printf 'protocol=https\\nhost=example.invalid\\n\\n' | \
  git_remote -C "$1" \
    -c credential.helper= \
    -c 'credential.helper=!/bin/false' \
    credential fill >/dev/null 2>&1; then
  exit 92
fi
test ! -e "$2"
"""
                result = subprocess.run(
                    ["bash", "-c", script, "askpass-test", str(repo), str(leak)],
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=10,
                    env={"HOME": "/home/teladi", "PATH": "/usr/bin:/bin"},
                )
                with self.subTest(name=name):
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertFalse(leak.exists())

    def test_normative_merge_derivation_matches_the_reviewed_tree_and_exact_oid(self) -> None:
        self.assertIn("# BEGIN TASK3_DERIVE_MERGE", self.task3_merge)
        derive_merge = _marked_block(self.task3_merge, "TASK3_DERIVE_MERGE")
        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-derive-contract-") as tmp:
            fixture = self._make_merge_fixture(tmp)
            script = f"""
set -Eeuo pipefail
{derive_merge}
generator_pr_number=17
generator_head=feature/reviewed
generator_expected_head=$1
generator_base_before=$2
derive_task3_merge
printf '%s\\n' "$generator_head_tree" "$generator_merge_date" \\
  "$generator_merge_message" "$generator_merge_sha"
"""
            result = subprocess.run(
                ["bash", "-c", script, "derive-test", fixture["head"], fixture["base"]],
                cwd=fixture["repo"],
                text=True,
                capture_output=True,
                check=False,
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                result.stdout.splitlines(),
                [
                    fixture["head_tree"],
                    fixture["merge_date"],
                    fixture["message"],
                    fixture["expected_merge"],
                ],
            )

    def test_normative_receipt_rejects_extra_malformed_stale_and_forged_content(self) -> None:
        self.assertIn("# BEGIN TASK3_DERIVE_MERGE", self.task3_merge)
        self.assertIn("# BEGIN TASK3_VALIDATE_RECEIPT", self.task3_merge)
        derive_merge = _marked_block(self.task3_merge, "TASK3_DERIVE_MERGE")
        validate_receipt = _marked_block(self.task3_merge, "TASK3_VALIDATE_RECEIPT")
        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-receipt-contract-") as tmp:
            fixture = self._make_merge_fixture(tmp)
            valid_receipt = self._receipt_for_fixture(fixture)
            validation_script = f"""
set -Eeuo pipefail
{derive_merge}
{validate_receipt}
receipt_file=$1
task3_actor_login=H234598
task3_actor_id=54270221
canonical_repo_id=R_kgDOTpr2BA
canonical_repository=H234598/Wirtelprimpf-generator
canonical_origin=https://github.com/H234598/Wirtelprimpf-generator.git
generator_head=feature/reviewed
generator_expected_head=$2
load_task3_receipt
generator_pr_number=$receipt_pr_number
generator_base_before=$receipt_base_before
derive_task3_merge
validate_task3_receipt_derivation
"""

            def validate(name: str, content: str) -> subprocess.CompletedProcess[str]:
                receipt_path = Path(tmp) / f"{name}.json"
                receipt_path.write_text(content, encoding="utf-8")
                receipt_path.chmod(0o600)
                return subprocess.run(
                    ["bash", "-c", validation_script, "receipt-test", str(receipt_path), fixture["head"]],
                    cwd=fixture["repo"],
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=10,
                )

            accepted = validate("valid", json.dumps(valid_receipt, sort_keys=True))
            self.assertEqual(accepted.returncode, 0, accepted.stderr)

            extra = dict(valid_receipt)
            extra["attacker_note"] = "schema extension must not be ignored"
            stale = dict(valid_receipt)
            stale["expected_head"] = fixture["base"]
            forged = dict(valid_receipt)
            forged["head_tree"] = fixture["malicious_tree"]
            forged["merge_sha"] = fixture["malicious_merge"]
            replacement_repository = dict(valid_receipt)
            replacement_repository["repository_id"] = "R_DYNAMIC_REPLACEMENT"
            rejected_cases = {
                "extra": json.dumps(extra, sort_keys=True),
                "malformed": "{",
                "stale": json.dumps(stale, sort_keys=True),
                "forged": json.dumps(forged, sort_keys=True),
                "replacement_repository": json.dumps(
                    replacement_repository,
                    sort_keys=True,
                ),
            }
            for name, content in rejected_cases.items():
                with self.subTest(name=name):
                    rejected = validate(name, content)
                    self.assertNotEqual(rejected.returncode, 0)

    def test_normative_receipt_writer_cleans_private_temp_after_atomic_replace_failure(self) -> None:
        self.assertIn("# BEGIN TASK3_RECEIPT_IO", self.task3_merge)
        receipt_io = _marked_block(self.task3_merge, "TASK3_RECEIPT_IO")
        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-receipt-io-") as tmp:
            fixture = self._make_merge_fixture(tmp)
            receipt_parent = Path(tmp) / "state"
            receipt_dir = receipt_parent / "task3-merge"
            receipt_parent.mkdir(mode=0o700)
            receipt_parent.chmod(0o700)
            receipt_dir.mkdir(mode=0o700)
            receipt_dir.chmod(0o700)
            occupied_destination = receipt_dir / "occupied-destination"
            occupied_destination.mkdir(mode=0o700)
            script = f"""
set -Eeuo pipefail
{receipt_io}
receipt_parent=$1
receipt_dir=$2
receipt_file=$3
receipt_state=absent
task3_actor_login=H234598
task3_actor_id=54270221
canonical_repo_id=R_kgDOTpr2BA
canonical_repository=H234598/Wirtelprimpf-generator
canonical_origin=https://github.com/H234598/Wirtelprimpf-generator.git
generator_pr_number=17
generator_head=feature/reviewed
generator_expected_head=$4
generator_base_before=$5
generator_head_tree=$6
generator_merge_date=$7
generator_merge_message='Merge pull request #17 from feature/reviewed'
generator_merge_sha=$8
write_task3_receipt planned
"""
            failed = subprocess.run(
                [
                    "bash",
                    "-c",
                    script,
                    "receipt-io-test",
                    str(receipt_parent),
                    str(receipt_dir),
                    str(occupied_destination),
                    fixture["head"],
                    fixture["base"],
                    fixture["head_tree"],
                    fixture["merge_date"],
                    fixture["expected_merge"],
                ],
                cwd=fixture["repo"],
                text=True,
                capture_output=True,
                check=False,
                timeout=10,
            )
            self.assertNotEqual(failed.returncode, 0)
            self.assertEqual(list(receipt_dir.glob(".generator-main-receipt.*")), [])

    def test_normative_remote_state_classifier_never_repushes_a_committed_merge(self) -> None:
        self.assertIn("# BEGIN TASK3_REMOTE_STATE", self.task3_merge)
        classifier = _marked_block(self.task3_merge, "TASK3_REMOTE_STATE")
        base = "1" * 40
        head = "2" * 40
        merge = "3" * 40
        script = f"""
set -Eeuo pipefail
{classifier}
classify_task3_remote_action "$1" "$2" "$3" "$4" "$5" "$6"
"""

        def classify(state: str, remote_main: str, remote_head: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                [
                    "bash",
                    "-c",
                    script,
                    "remote-state-test",
                    state,
                    remote_main,
                    remote_head,
                    base,
                    merge,
                    head,
                ],
                text=True,
                capture_output=True,
                check=False,
                timeout=10,
            )

        cases = {
            ("planned", base, head): "push\n",
            ("planned", merge, ""): "reconcile\n",
            ("remote_committed", merge, ""): "observe\n",
            ("verified", merge, ""): "observe\n",
        }
        for inputs, expected in cases.items():
            with self.subTest(inputs=inputs):
                result = classify(*inputs)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, expected)
        for inputs in (
            ("planned", "4" * 40, head),
            ("remote_committed", base, head),
            ("verified", merge, head),
            ("unknown", merge, ""),
        ):
            with self.subTest(rejected=inputs):
                result = classify(*inputs)
                self.assertNotEqual(result.returncode, 0)

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
        self.assertIn("git remote get-url --push --all origin", self.task3_merge)
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
        rollback = _marked_block(self.deployment, "TASK4_ROLLBACK_DEPLOYMENT")
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

    def test_actual_normative_rollback_survives_second_signal_and_releases_lock(self) -> None:
        self.assertIn("# BEGIN TASK4_ROLLBACK_DEPLOYMENT", self.deployment)
        rollback = _marked_block(self.deployment, "TASK4_ROLLBACK_DEPLOYMENT")
        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-rollback-contract-") as tmp:
            armed = Path(tmp) / "armed"
            recovery_ready = Path(tmp) / "recovery-ready"
            recovery_release = Path(tmp) / "recovery-release"
            release_proof = Path(tmp) / "release-proof"
            script = f"""
set -Eeuo pipefail
{rollback}
armed_path=$1
recovery_ready_path=$2
recovery_release_path=$3
release_proof_path=$4
deployment_complete=0
software_commit_complete=0
backup_complete=0
settings_lock_held=0
target_sha=2222222222222222222222222222222222222222
runtime_sha_before=1111111111111111111111111111111111111111
runtime_branch_before=main
runtime=/nonexistent/runtime
deploy_backup=/nonexistent/backup
timer_enabled_before=disabled
timer_active_before=inactive
admin_active_before=inactive
applet_running_before=0
runtime_timer_masked=0
runtime_service_masked=0

quiesce_generator() {{ return 0; }}
acquire_settings_lock_bounded() {{
  settings_lock_held=1
  : >"$recovery_ready_path"
  while [[ ! -e "$recovery_release_path" ]]; do sleep 0.01; done
}}
release_settings_lock() {{
  settings_lock_held=0
  : >"$release_proof_path"
}}
fail_closed_runtime() {{ return 0; }}
restore_timer_enablement_stopped() {{ return 0; }}
restore_timer_activity() {{ return 0; }}
unmask_timer_runtime_stopped() {{ return 0; }}
unmask_generator_runtime() {{ return 0; }}
git_runtime() {{
  if [[ "$1" == rev-parse && "$2" == refs/heads/main ]]; then
    printf '%s\\n' "$runtime_sha_before"
  elif [[ "$1" == rev-parse && "$2" == HEAD ]]; then
    printf '%s\\n' "$runtime_sha_before"
  else
    return 0
  fi
}}
systemctl() {{
  case "$*" in
    '--user is-enabled wirtelprimpf.timer') printf 'disabled\\n' ;;
    '--user is-enabled wirtelprimpf.service') printf 'static\\n' ;;
    '--user is-active wirtelprimpf-admin.service') printf 'inactive\\n' ;;
    *) return 0 ;;
  esac
}}
timeout() {{ return 0; }}
cmp() {{ return 0; }}
diff() {{ return 0; }}
gdbus() {{ printf '(@as [],)\\n'; }}

trap 'rollback_deployment $?' EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
: >"$armed_path"
while :; do sleep 0.01; done
"""
            process = subprocess.Popen(
                [
                    "bash",
                    "-c",
                    script,
                    "rollback-test",
                    str(armed),
                    str(recovery_ready),
                    str(recovery_release),
                    str(release_proof),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={"HOME": "/home/teladi", "PATH": "/usr/bin:/bin"},
            )
            deadline = time.monotonic() + 5
            while not armed.exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertTrue(armed.exists(), "normative rollback probe did not arm")
            process.send_signal(signal.SIGTERM)
            while not recovery_ready.exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertTrue(recovery_ready.exists(), "normative rollback did not enter recovery")
            process.send_signal(signal.SIGHUP)
            time.sleep(0.05)
            self.assertIsNone(process.poll(), "second signal interrupted normative recovery")
            recovery_release.touch()
            stdout, stderr = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 143, stderr)
            self.assertEqual(stdout, "")
            self.assertTrue(release_proof.exists(), "normative rollback did not release its lock")

    def test_normative_deployment_and_harness_are_valid_bash(self) -> None:
        for name, script in (
            ("task3_step3", self.task3_step3),
            ("task3_step4", self.task3_step4),
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
