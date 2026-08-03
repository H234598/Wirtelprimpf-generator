from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import shlex
import signal
import socket
import subprocess
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_PLAN = ROOT / "docs/superpowers/plans/2026-08-01-public-site-copy-and-rollout.md"
PR4_REOPEN_EVIDENCE = (
    ROOT / "docs/superpowers/evidence/2026-08-02-pr4-reopen-422.json"
)
_FIXTURE_GIT_ENV = {
    "HOME": "/home/teladi",
    "USER": "teladi",
    "LOGNAME": "teladi",
    "PATH": "/usr/bin:/bin",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_ASKPASS": "/bin/false",
    "SSH_ASKPASS": "/bin/false",
}
_FIXTURE_GIT_CONFIG = (
    "-c",
    "core.hooksPath=/dev/null",
    "-c",
    "core.fsmonitor=false",
    "-c",
    "credential.helper=",
    "-c",
    "commit.gpgSign=false",
    "-c",
    "tag.gpgSign=false",
    "-c",
    "protocol.ext.allow=never",
    "-c",
    "protocol.file.allow=always",
)
_FIXTURE_IDENTITY_ENV = frozenset(
    {
        "GIT_AUTHOR_NAME",
        "GIT_AUTHOR_EMAIL",
        "GIT_AUTHOR_DATE",
        "GIT_COMMITTER_NAME",
        "GIT_COMMITTER_EMAIL",
        "GIT_COMMITTER_DATE",
    }
)


def _fixture_git(
    arguments: list[str],
    *,
    extra_env: dict[str, str] | None = None,
    timeout: float = 15,
    **kwargs: object,
) -> subprocess.CompletedProcess[str]:
    forbidden = {"env", "executable", "shell"}.intersection(kwargs)
    if forbidden:
        raise TypeError(f"fixture Git controls {', '.join(sorted(forbidden))}")
    if timeout <= 0 or timeout > 15:
        raise ValueError("fixture Git timeout must be in (0, 15] seconds")
    environment = dict(_FIXTURE_GIT_ENV)
    if extra_env:
        unexpected = set(extra_env).difference(_FIXTURE_IDENTITY_ENV)
        if unexpected:
            raise ValueError("fixture Git received a non-identity environment key")
        environment.update(extra_env)
    return subprocess.run(  # nosec B603 -- fixed Git binary and isolated argv/env
        ["/usr/bin/git", *_FIXTURE_GIT_CONFIG, *arguments],
        env=environment,
        timeout=timeout,
        **kwargs,
    )  # type: ignore[return-value]


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


def _ownership_test_owner_pairs(
) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int]]:
    source = (os.geteuid(), os.getegid())
    if source == (0, 0):
        return source, (1000, 1000), (1, 1)
    alternate_groups = sorted(set(os.getgroups()).difference({source[1]}))
    if len(alternate_groups) < 2:
        raise unittest.SkipTest(
            "two supplementary groups are required for the ownership test"
        )
    return (
        source,
        (source[0], alternate_groups[0]),
        (source[0], alternate_groups[1]),
    )


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
        cls.ownership_gate = _code_block_after(
            cls.document,
            "#### Verbindliches Ownership-Gate vor jedem Runtime-Gitlauf",
        )
        cls.task1_commit = _code_block_after(
            cls.document,
            "**Step 5: Commit the independently reviewable copy change**",
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
            "**Step 9: Execute Steps 1\u20138 through one guarded deployment transaction**",
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
        cls.task5_step2 = _code_block_after(
            cls.document[task5_offset:],
            "**Step 2: Resolve and validate the immutable factory SHA**",
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
        cls.task5_step6 = _code_block_after(
            cls.document[task5_offset:],
            "**Step 6: Merge and watch the exact archive Pages run**",
        )
        task6_offset = cls.document.index("### Task 6:")
        cls.task6_step1 = _code_block_after(
            cls.document[task6_offset:],
            "**Step 1: Dispatch the hub with the exact active archive commit**",
        )

    def test_task1_commit_starts_clean_and_stages_exactly_the_declared_paths(self) -> None:
        expected_paths = (
            "web/tests/copy-contract.test.ts",
            "web/src/layouts/BaseLayout.astro",
            "web/src/pages/index.astro",
            "web/src/components/MediaCard.astro",
            "web/src/pages/projekt/status.astro",
        )
        self.assertIn("git diff --cached --quiet", self.task1_commit)
        self.assertIn("expected_task1_paths=(", self.task1_commit)
        self.assertIn("git diff --cached --name-only", self.task1_commit)
        self.assertIn("cmp --silent", self.task1_commit)
        self.assertIn('git add -- "${expected_task1_paths[@]}"', self.task1_commit)
        for path in expected_paths:
            self.assertEqual(self.task1_commit.count(path), 1, path)

    def _make_merge_fixture(self, tmp: str) -> dict[str, str]:
        repo = Path(tmp) / "merge-source"
        _fixture_git(["init", "-q", str(repo)], check=True)
        _fixture_git(["-C", str(repo), "config", "user.name", "Fixture"], check=True)
        _fixture_git(
            ["-C", str(repo), "config", "user.email", "fixture@example.invalid"],
            check=True,
        )
        (repo / "story").write_text("base\n", encoding="utf-8")
        _fixture_git(["-C", str(repo), "add", "story"], check=True)
        _fixture_git(["-C", str(repo), "commit", "-q", "-m", "base"], check=True)
        base = _fixture_git(
            ["-C", str(repo), "rev-parse", "HEAD"],
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        (repo / "story").write_text("reviewed head\n", encoding="utf-8")
        _fixture_git(["-C", str(repo), "commit", "-q", "-am", "reviewed"], check=True)
        head = _fixture_git(
            ["-C", str(repo), "rev-parse", "HEAD"],
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        head_tree = _fixture_git(
            ["-C", str(repo), "rev-parse", f"{head}^{{tree}}"],
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        merge_date = _fixture_git(
            ["-C", str(repo), "show", "-s", "--format=%cI", head],
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        message = "Merge pull request #17 from feature/reviewed"
        merge_env = {
            "GIT_AUTHOR_NAME": "H234598",
            "GIT_AUTHOR_EMAIL": "54270221+H234598@users.noreply.github.com",
            "GIT_AUTHOR_DATE": merge_date,
            "GIT_COMMITTER_NAME": "H234598",
            "GIT_COMMITTER_EMAIL": "54270221+H234598@users.noreply.github.com",
            "GIT_COMMITTER_DATE": merge_date,
        }

        def commit_tree(tree: str) -> str:
            return _fixture_git(
                ["-C", str(repo), "commit-tree", tree, "-p", base, "-p", head],
                input=f"{message}\n",
                text=True,
                capture_output=True,
                check=True,
                extra_env=merge_env,
            ).stdout.strip()

        expected_merge = commit_tree(head_tree)
        malicious_blob = _fixture_git(
            ["-C", str(repo), "hash-object", "-w", "--stdin"],
            input="unreviewed payload\n",
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        malicious_tree = _fixture_git(
            ["-C", str(repo), "mktree"],
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
            "version": 3,
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
            "review_id": 8142270,
            "review_author_login": "coderabbitai[bot]",
            "review_author_id": 136622811,
            "review_commit": fixture["head"],
            "review_state": "APPROVED",
        }

    @staticmethod
    def _pr4_closed_binding(
        receipt_state: str = "remote_committed",
        remote_feature: str | None = None,
    ) -> dict[str, object]:
        historical_reopen = json.loads(PR4_REOPEN_EVIDENCE.read_text(encoding="utf-8"))
        base = "b00d824adee47341e3251bc18e09239fde1c5939"
        head = "5aab1907b9af73fe6d8ef56e49beb7a527877e19"
        tree = "967a0b41f6525de79dfc91e1b52dd8ca3dc85ac8"
        merge = "274b25c9e1f9ea97d3b060997ed5c425d2b30e9f"
        if remote_feature is None:
            remote_feature = head
        return {
            "version": 1,
            "actor": {"login": "H234598", "id": 54270221},
            "repository": {
                "id": "R_kgDOTpr2BA",
                "name_with_owner": "H234598/Wirtelprimpf-generator",
                "canonical_origin": (
                    "https://github.com/H234598/Wirtelprimpf-generator.git"
                ),
            },
            "receipt": {
                "version": 3,
                "state": receipt_state,
                "pr_number": 4,
                "head_ref": "agent/transactional-settings-live-sync-status",
                "base_before": base,
                "expected_head": head,
                "head_tree": tree,
                "merge_sha": merge,
            },
            "refs": {"main": merge, "feature": remote_feature},
            "graphql_pr": {
                "number": 4,
                "state": "CLOSED",
                "merged": False,
                "merge_commit": None,
                "viewer_can_reopen": False,
                "base_ref": "main",
                "head_ref": "agent/transactional-settings-live-sync-status",
                "head_oid": head,
                "is_draft": False,
                "is_cross_repository": False,
                "head_repository_id": "R_kgDOTpr2BA",
                "head_repository": "H234598/Wirtelprimpf-generator",
                "head_owner": "H234598",
                "review_decision": "APPROVED",
            },
            "rest_pr": {
                "number": 4,
                "state": "closed",
                "merged": False,
                "merge_commit_sha": "01df605da0cd39f5bbcddfd2ebc9837d74f3f375",
                "base_ref": "main",
                "base_sha": base,
                "head_ref": "agent/transactional-settings-live-sync-status",
                "head_sha": head,
                "base_repository_node_id": "R_kgDOTpr2BA",
                "base_repository": "H234598/Wirtelprimpf-generator",
                "head_repository_node_id": "R_kgDOTpr2BA",
                "head_repository": "H234598/Wirtelprimpf-generator",
                "author_login": "H234598",
                "author_id": 54270221,
                "mergeable": True,
                "mergeable_state": "clean",
            },
            "timeline": [
                {
                    "event": "closed",
                    "actor_login": "H234598",
                    "actor_id": 54270221,
                    "created_at": "2026-08-02T11:08:29Z",
                },
                {
                    "event": "head_ref_deleted",
                    "actor_login": "H234598",
                    "actor_id": 54270221,
                    "created_at": "2026-08-02T11:08:29Z",
                },
                {
                    "event": "head_ref_restored",
                    "actor_login": "H234598",
                    "actor_id": 54270221,
                    "created_at": "2026-08-02T11:14:21Z",
                },
            ],
            "compare": {
                "status": "ahead",
                "ahead_by": 1,
                "behind_by": 0,
                "total_commits": 1,
                "merge_base": head,
                "base_commit": head,
                "commits": [merge],
                "files_count": 0,
            },
            "commit": {
                "sha": merge,
                "tree": tree,
                "parents": [base, head],
                "author_name": "H234598",
                "author_email": "54270221+H234598@users.noreply.github.com",
                "author_date": "2026-08-02T11:00:40Z",
                "committer_name": "H234598",
                "committer_email": "54270221+H234598@users.noreply.github.com",
                "committer_date": "2026-08-02T11:00:40Z",
                "message": (
                    "Merge pull request #4 from "
                    "agent/transactional-settings-live-sync-status"
                ),
            },
            "review": {
                "id": 4838199265,
                "author_login": "coderabbitai[bot]",
                "author_id": 136622811,
                "author_node_id": "BOT_kgDOCCSy2w",
                "author_url": "https://github.com/apps/coderabbitai",
                "commit": head,
                "state": "APPROVED",
                "unresolved_threads": 0,
            },
            "historical_reopen": historical_reopen,
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

        self.assertIn(
            "os.replace(part_name, workflow_name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)",
            self.task5_step3,
        )
        self.assertIn("parent_fd = os.open(", self.task5_step3)
        self.assertIn("root_fd = os.open(", self.task5_step3)
        self.assertIn('github_fd = os.open(', self.task5_step3)
        self.assertIn('".github"', self.task5_step3)
        self.assertIn("dir_fd=parent_fd", self.task5_step3)
        self.assertIn("follow_symlinks=False", self.task5_step3)
        self.assertIn("parent_identity", self.task5_step3)
        self.assertIn("target_identity", self.task5_step3)
        self.assertIn("st.st_uid == 1000 and st.st_gid == 1000", self.task5_step3)
        self.assertIn("if old_count != 2", self.task5_step3)
        self.assertIn("if new_count != 2", self.task5_step3)

    def test_task5_literal_fence_executes_as_teladi_without_root_expansion(self) -> None:
        if os.geteuid() != 0 or not Path("/usr/sbin/runuser").is_file():
            self.skipTest("the real Task-5 runuser probe requires root and /usr/sbin/runuser")
        try:
            teladi_ids = subprocess.run(  # nosec B603 -- fixed root probe argv
                ["/usr/bin/id", "-u", "teladi"],
                text=True,
                capture_output=True,
                check=True,
            ).stdout.strip(), subprocess.run(  # nosec B603 -- fixed root probe argv
                ["/usr/bin/id", "-g", "teladi"],
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
        result = subprocess.run(  # nosec B603 -- fixed shell and generated local probe
            ["/bin/bash"],
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
        teladi_uid = 1000
        teladi_gid = 1000
        if os.geteuid() == teladi_uid and os.getegid() == teladi_gid:
            command_prefix = [
                "/usr/bin/env",
                "-i",
                "HOME=/home/teladi",
                "PATH=/usr/local/bin:/usr/bin:/bin",
                "/usr/bin/python3",
            ]
        elif os.geteuid() == 0 and Path("/usr/sbin/runuser").is_file():
            command_prefix = [
                "/usr/sbin/runuser",
                "-u",
                "teladi",
                "--",
                "/usr/bin/env",
                "-i",
                "HOME=/home/teladi",
                "PATH=/usr/local/bin:/usr/bin:/bin",
                "/usr/bin/python3",
            ]
        else:
            self.skipTest("the Task-5 workflow rewrite probe requires teladi or root/runuser")
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
            root.chmod(0o700)
            archive = root / "archive"
            workflow = archive / ".github/workflows/pages.yml"
            workflow.parent.mkdir(parents=True, mode=0o700)
            workflow.write_text(original, encoding="utf-8")
            if os.geteuid() == 0:
                for path in (root, archive, archive / ".github", workflow.parent, workflow):
                    os.chown(path, teladi_uid, teladi_gid)
            workflow.chmod(0o644)
            result = subprocess.run(  # nosec B603 -- fixed runuser/python argv
                [*command_prefix, "-", str(workflow), new_sha],
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

    def test_task5_workflow_rewriter_rejects_github_symlink_and_parent_swap(self) -> None:
        if (os.geteuid(), os.getegid()) != (1000, 1000):
            self.skipTest("the attack probe runs directly as teladi")
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

        def execute(script: str, workflow: Path) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                [
                    "/usr/bin/env",
                    "-i",
                    "HOME=/home/teladi",
                    "PATH=/usr/local/bin:/usr/bin:/bin",
                    "/usr/bin/python3",
                    "-",
                    str(workflow),
                    new_sha,
                ],
                input=script,
                text=True,
                capture_output=True,
                check=False,
                timeout=10,
            )

        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-task5-symlink-") as tmp:
            root = Path(tmp)
            archive = root / "archive"
            archive.mkdir()
            external = root / "external-github/workflows"
            external.mkdir(parents=True)
            workflow = external / "pages.yml"
            workflow.write_text(original, encoding="utf-8")
            workflow.chmod(0o644)
            (archive / ".github").symlink_to(external.parent, target_is_directory=True)

            result = execute(rewrite, archive / ".github/workflows/pages.yml")

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(workflow.read_text(encoding="utf-8"), original)
            self.assertEqual(list(external.glob(".*.part")), [])

        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-task5-parent-swap-") as tmp:
            archive = Path(tmp) / "archive"
            original_parent = archive / ".github/workflows"
            replacement_parent = archive / ".github-replacement/workflows"
            original_parent.mkdir(parents=True)
            replacement_parent.mkdir(parents=True)
            workflow = original_parent / "pages.yml"
            replacement = replacement_parent / "pages.yml"
            workflow.write_text(original, encoding="utf-8")
            replacement.write_text(original, encoding="utf-8")
            workflow.chmod(0o644)
            replacement.chmod(0o644)
            needle = "    current_root = os.stat(archive_root, follow_symlinks=False)\n"
            self.assertIn(needle, rewrite)
            injected = rewrite.replace(
                needle,
                "    os.rename(archive_root / '.github', archive_root / '.github-original')\n"
                "    os.rename(archive_root / '.github-replacement', archive_root / '.github')\n"
                + needle,
                1,
            )

            result = execute(injected, workflow)

            self.assertNotEqual(result.returncode, 0)
            moved_original = archive / ".github-original/workflows/pages.yml"
            self.assertEqual(moved_original.read_text(encoding="utf-8"), original)
            self.assertEqual(
                (archive / ".github/workflows/pages.yml").read_text(encoding="utf-8"),
                original,
            )
            self.assertEqual(list(moved_original.parent.glob(".*.part")), [])

    def test_runtime_git_fetch_and_switch_share_the_hardened_local_config_boundary(self) -> None:
        guard = _marked_block(self.deployment, "TASK4_RUNTIME_GIT_GUARD")
        runtime_git = _shell_function(self.deployment, "git_runtime")
        runtime_fetch = _shell_function(self.deployment, "git_runtime_fetch_bounded")
        for script in (guard, runtime_git, runtime_fetch):
            self.assertIn("GIT_CONFIG_NOSYSTEM=1", script)
            self.assertIn("GIT_CONFIG_GLOBAL=/dev/null", script)
        self.assertIn("assert_safe_runtime_git_config", runtime_git)
        self.assertIn("switch)", runtime_git)
        self.assertIn("core.hooksPath=/dev/null", runtime_git)
        self.assertIn("core.fsmonitor=false", runtime_git)
        self.assertIn("protocol.ext.allow=never", runtime_git)
        self.assertIn('fetch "$runtime_canonical_origin"', runtime_fetch)
        self.assertIn("refs/heads/main:refs/remotes/origin/main", runtime_fetch)
        self.assertNotIn("fetch origin main", runtime_fetch)

    def test_runtime_git_local_config_is_exactly_allowlisted_for_checkout(self) -> None:
        guard = _marked_block(self.deployment, "TASK4_RUNTIME_GIT_GUARD")
        hostile_entries = (
            ("filter.attack.smudge", "/bin/false"),
            ("core.attributesFile", "/tmp/hostile-attributes"),  # nosec B108
            ("core.worktree", "/tmp/hostile-worktree"),  # nosec B108
            ("diff.attack.command", "/bin/false"),
            ("merge.attack.driver", "/bin/false"),
        )
        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-runtime-config-") as tmp:
            repository = Path(tmp) / "runtime"
            _fixture_git(
                ["init", "-q", "-b", "main", str(repository)],
                check=True,
                timeout=10,
            )
            _fixture_git(
                [
                    "-C",
                    str(repository),
                    "remote",
                    "add",
                    "origin",
                    "https://github.com/H234598/Wirtelprimpf-generator.git",
                ],
                check=True,
                timeout=10,
            )
            _fixture_git(
                [
                    "-C",
                    str(repository),
                    "config",
                    "--local",
                    "core.repositoryformatversion",
                    "1",
                ],
                check=True,
                timeout=10,
            )
            _fixture_git(
                [
                    "-C",
                    str(repository),
                    "config",
                    "--local",
                    "remote.origin.fetch",
                    "+refs/heads/main:refs/remotes/origin/main",
                ],
                check=True,
                timeout=10,
            )
            for key, value in (
                ("branch.main.remote", "origin"),
                ("branch.main.merge", "refs/heads/main"),
                ("branch.agent/transactional-settings-live-sync-status.remote", "origin"),
                (
                    "branch.agent/transactional-settings-live-sync-status.merge",
                    "refs/heads/agent/transactional-settings-live-sync-status",
                ),
            ):
                _fixture_git(
                    ["-C", str(repository), "config", "--local", key, value],
                    check=True,
                    timeout=10,
                )
            script = (
                "set -Eeuo pipefail\n"
                f"runtime={repository!s}\n"
                "runtime_canonical_origin=https://github.com/H234598/Wirtelprimpf-generator.git\n"
                f"{guard}\n"
                "assert_safe_runtime_git_config\n"
            )
            accepted = subprocess.run(
                ["/bin/bash", "-c", script],
                text=True,
                capture_output=True,
                check=False,
                timeout=10,
                env={"HOME": "/home/teladi", "PATH": "/usr/bin:/bin"},
            )
            self.assertEqual(accepted.returncode, 0, accepted.stderr)
            for key, value in hostile_entries:
                _fixture_git(
                    ["-C", str(repository), "config", "--local", key, value],
                    check=True,
                    timeout=10,
                )
                rejected = subprocess.run(
                    ["/bin/bash", "-c", script],
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=10,
                    env={"HOME": "/home/teladi", "PATH": "/usr/bin:/bin"},
                )
                with self.subTest(key=key):
                    self.assertNotEqual(rejected.returncode, 0)
                _fixture_git(
                    [
                        "-C",
                        str(repository),
                        "config",
                        "--local",
                        "--unset-all",
                        key,
                    ],
                    check=True,
                    timeout=10,
                )

    def test_task6_binds_probe_dispatch_selection_and_watch_to_exact_inputs(self) -> None:
        step = self.task6_step1
        normalized = " ".join(step.split())
        self.assertIn("set -Eeuo pipefail", step)
        self.assertIn("test \"$(id -u)\" = 0", step)
        self.assertIn("/usr/sbin/runuser -u teladi -- /usr/bin/env -i", normalized)
        self.assertIn("DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus", normalized)
        self.assertIn("XDG_RUNTIME_DIR=/run/user/1000", normalized)
        local_prefix, local_probe = _quoted_heredoc(step, "TASK6_LOCAL_PROBE")
        del local_prefix
        self.assertNotIn("GH_TOKEN", local_probe)
        self.assertNotIn("GITHUB_TOKEN", local_probe)
        self.assertIn("refs/heads/main", local_probe)
        self.assertIn("refs/remotes/origin/main", local_probe)
        self.assertIn("task6_token_call", step)
        self.assertIn("set +x", step)
        self.assertIn(".login == \"H234598\"", step)
        self.assertIn(".id == 54270221", step)
        self.assertIn(".id == \"R_kgDOTpr2BA\"", step)
        self.assertIn(
            "repos/H234598/Wirtelprimpf-generator/actions/workflows/"
            "hub-pages.yml/dispatches",
            step,
        )
        self.assertIn("X-GitHub-Api-Version: 2026-03-10", step)
        self.assertIn('"return_run_details": true', step)
        self.assertIn('"ref": "main"', step)
        self.assertIn('"active_repository": $active_repository', step)
        self.assertIn('"archive_ref": $archive_main_sha', step)
        self.assertIn('"current_volume": $current_volume', step)
        self.assertNotIn("workflow run hub-pages.yml", step)
        self.assertNotIn("run list", step)
        self.assertNotIn("dispatch_started_at", step)
        self.assertIn("workflow_run_id", step)
        for field in (
            "head_sha",
            "head_branch",
            "event",
            "display_title",
            "repository",
            "workflow_url",
        ):
            self.assertIn(field, step)
        self.assertIn("expected_display_title", step)
        self.assertIn("verify_hub_run_identity", step)
        self.assertLess(step.rindex("verify_hub_run_identity"), step.index("run watch"))

    def test_token_children_isolate_system_and_global_git_configuration(self) -> None:
        task5_child = _quoted_heredoc(self.task5_step5, "TASK5_STEP5_TELADI")[1]
        cases = (
            ("task3-step3", self.task3_step3, "task3_token_call", "task3_ephemeral_token"),
            ("task3-step5", self.task3_merge, "task3_token_call", "task3_ephemeral_token"),
            ("task5-root", self.task5_step5, "task5_token_call", "task5_ephemeral_token"),
            ("task5-teladi", task5_child, "task5_token_call", "task5_ephemeral_token"),
        )
        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-git-config-env-") as tmp:
            probe = Path(tmp) / "probe"
            probe.write_text(
                "#!/bin/bash\n"
                "set -Eeuo pipefail\n"
                'test "$GIT_CONFIG_NOSYSTEM" = 1\n'
                'test "$GIT_CONFIG_GLOBAL" = /dev/null\n'
                'test "$GIT_TERMINAL_PROMPT" = 0\n'
                'test "$GIT_ASKPASS" = /bin/false\n'
                'test "$SSH_ASKPASS" = /bin/false\n',
                encoding="utf-8",
            )
            probe.chmod(0o700)
            for name, plan_script, function_name, token_name in cases:
                token_call = _shell_function(plan_script, function_name)
                script = f"""
set -Eeuo pipefail
{token_call}
{token_name}=CONFIG_ISOLATION_SENTINEL_NOT_A_SECRET
{function_name} "$1"
"""
                result = subprocess.run(  # nosec B603 -- fixed local shell/probe argv
                    ["/bin/bash", "-c", script, "git-config-env-test", str(probe)],
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=10,
                    env={
                        "HOME": "/home/teladi",
                        "PATH": "/usr/bin:/bin",
                        "GIT_CONFIG_SYSTEM": str(Path(tmp) / "hostile-system"),
                        "GIT_CONFIG_GLOBAL": str(Path(tmp) / "hostile-global"),
                    },
                )
                with self.subTest(name=name):
                    self.assertEqual(result.returncode, 0, result.stderr)

    def test_effective_local_git_config_guard_rejects_every_routing_or_exec_vector(self) -> None:
        marker = "# BEGIN TASK3_GIT_CONFIG_GUARD"
        self.assertIn(marker, self.task3_merge)
        guard = _marked_block(self.task3_merge, "TASK3_GIT_CONFIG_GUARD")
        hostile_entries = (
            ("include.path", "/tmp/hostile-config"),  # nosec B108 -- not a tempfile sink
            ("includeIf.onbranch:main.path", "/tmp/hostile-config"),  # nosec B108 -- not a tempfile sink
            ("url.https://foreign.invalid/.insteadOf", "https://github.com/"),
            ("url.ssh://foreign.invalid/.pushInsteadOf", "https://github.com/"),
            ("http.https://github.com/.extraHeader", "Authorization: forbidden"),
            ("protocol.ext.allow", "always"),
            ("core.sshCommand", "/tmp/forbidden-command"),  # nosec B108 -- not a tempfile sink
            ("core.gitProxy", "/tmp/forbidden-command"),  # nosec B108 -- not a tempfile sink
            ("core.fsmonitor", "/tmp/forbidden-command"),  # nosec B108 -- not a tempfile sink
            ("http.proxy", "http://127.0.0.1:9"),
            ("http.sslVerify", "false"),
            ("http.sslCAInfo", "/tmp/forbidden-ca"),  # nosec B108 -- not a tempfile sink
            ("http.curloptResolve", "github.com:443:127.0.0.1"),
            ("remote.origin.proxy", "http://127.0.0.1:9"),
            ("credential.https://github.com.helper", "/tmp/forbidden-helper"),  # nosec B108 -- not a tempfile sink
        )
        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-local-config-guard-") as tmp:
            repo = Path(tmp) / "repo"
            _fixture_git(
                ["init", "-q", str(repo)],
                check=True,
            )
            script = f"set -Eeuo pipefail\n{guard}\nassert_safe_local_git_config \"$1\"\n"
            accepted = subprocess.run(  # nosec B603 -- fixed local shell argv
                ["/bin/bash", "-c", script, "local-config-test", str(repo)],
                text=True,
                capture_output=True,
                check=False,
                timeout=10,
            )
            self.assertEqual(accepted.returncode, 0, accepted.stderr)
            for key, value in hostile_entries:
                _fixture_git(
                    ["-C", str(repo), "config", "--local", key, value],
                    check=True,
                )
                rejected = subprocess.run(  # nosec B603 -- fixed local shell argv
                    ["/bin/bash", "-c", script, "local-config-test", str(repo)],
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=10,
                )
                with self.subTest(key=key):
                    self.assertNotEqual(rejected.returncode, 0)
                _fixture_git(
                    ["-C", str(repo), "config", "--local", "--unset-all", key],
                    check=True,
                )

    def test_every_git_config_guard_redacts_secret_bearing_key_names(self) -> None:
        sentinel = "guard_secret_sentinel_6fdb8a15"
        cases = (
            ("task3-step3", self.task3_step3, "TASK3_GIT_CONFIG_GUARD"),
            ("task3-step5", self.task3_merge, "TASK3_GIT_CONFIG_GUARD"),
            ("task5-step1", self.task5_step1, "TASK5_GIT_CONFIG_GUARD"),
            ("task5-step2", self.task5_step2, "TASK5_GIT_CONFIG_GUARD"),
            ("task5-step3", self.task5_step3, "TASK5_GIT_CONFIG_GUARD"),
            ("task5-step4", self.task5_step4, "TASK5_GIT_CONFIG_GUARD"),
            ("task5-step5", self.task5_step5, "TASK5_GIT_CONFIG_GUARD"),
            ("task5-step6", self.task5_step6, "TASK5_GIT_CONFIG_GUARD"),
        )
        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-redacted-git-guard-") as tmp:
            for name, plan_script, marker in cases:
                repo = Path(tmp) / name
                _fixture_git(
                    ["init", "-q", str(repo)],
                    check=True,
                )
                secret_key = f"url.https://{sentinel}@foreign.invalid/.insteadOf"
                _fixture_git(
                    [
                        "-C",
                        str(repo),
                        "config",
                        "--local",
                        secret_key,
                        "https://github.com/",
                    ],
                    check=True,
                )
                guard = _marked_block(plan_script, marker)
                result = subprocess.run(  # nosec B603 -- fixed local shell argv
                    [
                        "/bin/bash",
                        "-c",
                        f"set -Eeuo pipefail\n{guard}\nassert_safe_local_git_config \"$1\"\n",
                        "redacted-git-guard-test",
                        str(repo),
                    ],
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=10,
                )
                with self.subTest(name=name):
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn(sentinel, result.stdout)
                    self.assertNotIn(sentinel, result.stderr)

    def test_every_network_git_wrapper_uses_system_trust_without_empty_ca_overrides(self) -> None:
        cases = (
            ("task3-step3", self.task3_step3, "git_remote", "TASK3_GIT_CONFIG_GUARD"),
            ("task3-step5", self.task3_merge, "git_remote", "TASK3_GIT_CONFIG_GUARD"),
            ("task5-step1", self.task5_step1, "task5_git_remote", "TASK5_GIT_CONFIG_GUARD"),
            ("task5-step2", self.task5_step2, "task5_git_remote", "TASK5_GIT_CONFIG_GUARD"),
            ("task5-step3", self.task5_step3, "task5_git_remote", "TASK5_GIT_CONFIG_GUARD"),
            ("task5-step4", self.task5_step4, "task5_git_remote", "TASK5_GIT_CONFIG_GUARD"),
            ("task5-step5", self.task5_step5, "task5_git_remote", "TASK5_GIT_CONFIG_GUARD"),
            ("task5-step6", self.task5_step6, "task5_git_remote", "TASK5_GIT_CONFIG_GUARD"),
        )
        for name, script, function_name, guard_marker in cases:
            wrapper = _shell_function(script, function_name)
            normalized_wrapper = " ".join(wrapper.split())
            with self.subTest(name=name):
                self.assertIn(guard_marker, script)
                self.assertIn("GIT_CONFIG_NOSYSTEM=1", script)
                self.assertIn("GIT_CONFIG_GLOBAL=/dev/null", script)
                self.assertIn("-c http.sslVerify=true", normalized_wrapper)
                self.assertNotIn("-c http.sslCAInfo=", normalized_wrapper)
                self.assertNotIn("-c http.sslCAPath=", normalized_wrapper)
                self.assertRegex(
                    script,
                    r"https://github\.com/H234598/Wirtelprimpf-(?:generator|0001)\.git",
                )

    def test_task5_has_no_raw_network_git_and_uses_only_canonical_literal_urls(self) -> None:
        for name, script in (
            ("step1", self.task5_step1),
            ("step2", self.task5_step2),
            ("step3", self.task5_step3),
            ("step4", self.task5_step4),
            ("step5", self.task5_step5),
            ("step6", self.task5_step6),
        ):
            with self.subTest(name=name):
                self.assertIn("TASK5_GIT_CONFIG_GUARD", script)
                self.assertNotRegex(
                    " ".join(script.split()),
                    r"/usr/bin/git\b(?:(?!task5_git_remote).){0,180}\b(?:fetch|pull|ls-remote|push)\b",
                )
                self.assertNotIn("ls-remote origin", script)
        self.assertIn('task5_git_remote fetch "$canonical_origin"', self.task5_step1)
        self.assertIn('task5_git_remote ls-remote "$canonical_origin"', self.task5_step2)
        self.assertIn('task5_git_remote push', self.task5_step5)

    def test_task3_current_head_review_gate_is_paginated_and_fail_closed(self) -> None:
        self.assertIn("# BEGIN TASK3_REVIEW_GATE", self.task3_merge)
        review_gate = _marked_block(self.task3_merge, "TASK3_REVIEW_GATE")
        pr_identity = _shell_function(self.task3_merge, "assert_pr_identity")
        head = "2" * 40
        base_overview = {
            "state": "OPEN",
            "headRefName": "feature/reviewed",
            "headRefOid": head,
            "baseRefName": "main",
            "isDraft": False,
            "isCrossRepository": False,
            "headRepository": {
                "id": "R_kgDOTpr2BA",
                "nameWithOwner": "H234598/Wirtelprimpf-generator",
            },
            "headRepositoryOwner": {"login": "H234598"},
            "reviewDecision": "APPROVED",
        }
        actor = {"login": "coderabbitai[bot]", "id": 136622811}

        def page(nodes: list[dict[str, object]], *, more: bool = False, cursor: str | None = None):
            return {
                "nodes": nodes,
                "pageInfo": {"hasNextPage": more, "endCursor": cursor},
            }

        approved_review = {
            "databaseId": 4837973683,
            "state": "APPROVED",
            "author": {
                "__typename": "Bot",
                "login": "coderabbitai",
                "databaseId": 136622811,
                "id": "BOT_kgDOCCSy2w",
                "url": "https://github.com/apps/coderabbitai",
            },
            "commit": {"oid": head},
        }

        reviews_page_function = _shell_function(review_gate, "fetch_task3_reviews_page")
        author_selection = re.search(
            r"author\{(?P<actor>[^{}]*?)\.\.\. on Bot\{(?P<bot>[^{}]+)\}\}",
            reviews_page_function,
        )
        self.assertIsNotNone(author_selection)
        assert author_selection is not None
        self.assertEqual(author_selection.group("actor").split(), ["__typename", "login"])
        self.assertEqual(
            author_selection.group("bot").split(), ["id", "databaseId", "url"]
        )
        self.assertEqual(reviews_page_function.count("author{"), 1)
        self.assertIn("__typename", review_gate)
        self.assertIn("databaseId", review_gate)
        self.assertIn("BOT_kgDOCCSy2w", review_gate)
        self.assertIn("https://github.com/apps/coderabbitai", review_gate)

        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-review-gate-") as tmp:
            fixture_dir = Path(tmp)
            script = f"""
set -Eeuo pipefail
{pr_identity}
{review_gate}
fixture_dir=$1
fetch_task3_review_overview() {{ /bin/cat "$fixture_dir/overview.json"; }}
fetch_task3_coderabbit_actor() {{ /bin/cat "$fixture_dir/actor.json"; }}
fetch_task3_review_threads_page() {{
  case "${{1:-}}" in
    '') /bin/cat "$fixture_dir/threads-root.json" ;;
    T1) /bin/cat "$fixture_dir/threads-T1.json" ;;
    *) return 91 ;;
  esac
}}
fetch_task3_reviews_page() {{
  case "${{1:-}}" in
    '') /bin/cat "$fixture_dir/reviews-root.json" ;;
    R1) /bin/cat "$fixture_dir/reviews-R1.json" ;;
    *) return 92 ;;
  esac
}}
generator_pr_number=17
generator_head=feature/reviewed
generator_expected_head=$2
canonical_repo_id=R_kgDOTpr2BA
canonical_repository=H234598/Wirtelprimpf-generator
assert_task3_current_review "$3"
printf '%s:%s:%s:%s:%s\n' "$generator_review_id" \
  "$generator_review_author_login" "$generator_review_author_id" \
  "$generator_review_commit" "$generator_review_state"
"""

            def execute(
                *,
                overview: dict[str, object] | None = None,
                actor_override: dict[str, object] | None = None,
                threads: dict[str, object] | None = None,
                reviews: dict[str, object] | None = None,
                threads_second: dict[str, object] | None = None,
                reviews_second: dict[str, object] | None = None,
                required_pr_state: str = "OPEN",
            ) -> subprocess.CompletedProcess[str]:
                payloads = {
                    "overview.json": overview or base_overview,
                    "actor.json": actor_override or actor,
                    "threads-root.json": threads or page([{"isResolved": True}]),
                    "threads-T1.json": threads_second or page([]),
                    "reviews-root.json": reviews or page([approved_review]),
                    "reviews-R1.json": reviews_second or page([]),
                }
                for filename, payload in payloads.items():
                    (fixture_dir / filename).write_text(json.dumps(payload), encoding="utf-8")
                return subprocess.run(  # nosec B603 -- fixed local shell and fixture argv
                    [
                        "/bin/bash",
                        "-c",
                        script,
                        "review-gate-test",
                        str(fixture_dir),
                        head,
                        required_pr_state,
                    ],
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=10,
                )

            accepted = execute(
                threads=page([{"isResolved": True}], more=True, cursor="T1"),
                reviews=page(
                    [
                        {
                            "databaseId": 1,
                            "state": "COMMENTED",
                            "author": {
                                "__typename": "User",
                                "login": "human",
                            },
                            "commit": {"oid": head},
                        }
                    ],
                    more=True,
                    cursor="R1",
                ),
                reviews_second=page([approved_review]),
            )
            self.assertEqual(accepted.returncode, 0, accepted.stderr)
            self.assertEqual(
                accepted.stdout,
                f"4837973683:coderabbitai[bot]:136622811:{head}:APPROVED\n",
            )

            closed = execute(
                overview=dict(base_overview, state="CLOSED"),
                required_pr_state="CLOSED",
            )
            self.assertEqual(closed.returncode, 0, closed.stderr)
            self.assertEqual(
                closed.stdout,
                f"4837973683:coderabbitai[bot]:136622811:{head}:APPROVED\n",
            )

            drifted = dict(base_overview, headRefOid="3" * 40)
            changed = dict(base_overview, reviewDecision="CHANGES_REQUESTED")
            stale_review = dict(approved_review, commit={"oid": "3" * 40})
            duplicate_reviews = page(
                [approved_review, dict(approved_review, databaseId=4837973684)]
            )
            foreign_bot = copy.deepcopy(approved_review)
            foreign_bot["author"]["databaseId"] = 999999999
            same_named_user = copy.deepcopy(approved_review)
            same_named_user["author"]["__typename"] = "User"
            wrong_node = copy.deepcopy(approved_review)
            wrong_node["author"]["id"] = "BOT_foreign"
            wrong_url = copy.deepcopy(approved_review)
            wrong_url["author"]["url"] = "https://github.com/apps/foreign"
            rejected_cases = {
                "head-drift": {"overview": drifted},
                "changes-requested": {"overview": changed},
                "unresolved": {"threads": page([{"isResolved": False}])},
                "stale-review": {"reviews": page([stale_review])},
                "ambiguous-review": {"reviews": duplicate_reviews},
                "broken-pagination": {
                    "threads": page([{"isResolved": True}], more=True, cursor=None)
                },
                "foreign-rest-actor": {
                    "actor_override": {
                        "login": "coderabbitai[bot]",
                        "id": 999999999,
                    }
                },
                "foreign-rest-login": {
                    "actor_override": {
                        "login": "coderabbitai",
                        "id": 136622811,
                    }
                },
                "foreign-graphql-bot": {"reviews": page([foreign_bot])},
                "same-named-user": {"reviews": page([same_named_user])},
                "wrong-bot-node": {"reviews": page([wrong_node])},
                "wrong-app-url": {"reviews": page([wrong_url])},
            }
            for name, kwargs in rejected_cases.items():
                with self.subTest(name=name):
                    self.assertNotEqual(execute(**kwargs).returncode, 0)

    def test_task3_review_gate_precedes_receipt_and_atomic_push_and_receipt_is_v3(self) -> None:
        planned = self.task3_merge.index("write_task3_receipt planned")
        retry = self.task3_merge.index(
            'else\n  case "$generator_pr_state" in OPEN|MERGED)'
        )
        remote_classification = self.task3_merge.index("\nremote_main_sha=", retry)
        retry_branch = self.task3_merge[retry:remote_classification]
        push_case = self.task3_merge.index("\n  push)", remote_classification)
        push = self.task3_merge.index("git_remote push --atomic", push_case)
        push_preamble = self.task3_merge[push_case:push]
        self.assertGreaterEqual(
            self.task3_merge[:planned].count("assert_task3_current_review"),
            1,
        )
        self.assertNotIn("assert_task3_current_review", retry_branch)
        for field in (
            "id",
            "author_login",
            "author_id",
            "commit",
            "state",
        ):
            hydration = (
                f'generator_review_{field}="$receipt_review_{field}"'
            )
            self.assertIn(hydration, retry_branch)
            self.assertLess(
                retry_branch.index(hydration),
                retry_branch.index("derive_task3_merge"),
            )
        self.assertLess(
            retry_branch.index("derive_task3_merge"),
            retry_branch.index("validate_task3_receipt_derivation"),
        )
        self.assertEqual(push_preamble.count("assert_task3_current_review"), 1)
        self.assertLess(
            push_preamble.index("assert_task3_current_review"),
            push_preamble.index("validate_task3_receipt_derivation"),
        )
        self.assertIn(".version == 3", self.task3_merge)
        for field in (
            "review_id",
            "review_author_login",
            "review_author_id",
            "review_commit",
            "review_state",
        ):
            self.assertIn(field, self.task3_merge)

    def test_all_normative_pr_views_have_an_explicit_pr_argument(self) -> None:
        self.assertNotRegex(
            self.document,
            r"\btask[35]_gh pr view(?:[ \t]+|[ \t]*\\\n[ \t]*)--repo\b",
        )
        discovery_start = self.task3_merge.index("receipt_state=absent")
        discovery_end = self.task3_merge.index(
            '\nif [[ "$receipt_state" == absent ]]; then',
            discovery_start,
        )
        discovery = self.task3_merge[discovery_start:discovery_end]
        list_call = discovery.index("task3_gh pr list")
        numbered_view = discovery.index(
            'task3_gh pr view "$generator_pr_number"',
        )
        identity_gate = discovery.index(
            'assert_pr_identity "$generator_merge_gate"',
        )
        self.assertIn(
            '--state open --base main --head "$generator_head" --limit 2',
            discovery,
        )
        self.assertLess(list_call, numbered_view)
        self.assertLess(numbered_view, identity_gate)

    def test_absent_receipt_discovers_one_exact_open_pr_before_numbered_view(self) -> None:
        assert_pr_identity = _shell_function(self.task3_merge, "assert_pr_identity")
        discovery_start = self.task3_merge.index("receipt_state=absent")
        discovery_end = self.task3_merge.index(
            '\nif [[ "$receipt_state" == absent ]]; then',
            discovery_start,
        )
        discovery = self.task3_merge[discovery_start:discovery_end]
        script = (
            "set -Eeuo pipefail\n"
            + assert_pr_identity
            + r'''

candidate_json() {
  /usr/bin/jq -cn --arg oid "$1" '{
    number: 17,
    state: "OPEN",
    headRefName: "feature/reviewed",
    headRefOid: $oid,
    baseRefName: "main",
    isDraft: false,
    isCrossRepository: false,
    headRepository: {
      id: "R_kgDOTpr2BA",
      nameWithOwner: "H234598/Wirtelprimpf-generator"
    },
    headRepositoryOwner: {login: "H234598"},
    mergeCommit: null
  }'
}

task3_gh() {
  test "$1" = pr
  local operation="$2"
  shift 2
  case "$operation" in
    list)
      local list_fields=number,state,headRefName,headRefOid,baseRefName,isDraft
      list_fields+=,isCrossRepository,headRepository,headRepositoryOwner
      local -a expected_list=(
        --repo "$canonical_repository"
        --state open --base main --head "$generator_head" --limit 2
        --json "$list_fields"
      )
      local -a actual_list=("$@")
      test "${#actual_list[@]}" = "${#expected_list[@]}"
      local index
      for index in "${!expected_list[@]}"; do
        test "${actual_list[$index]}" = "${expected_list[$index]}"
      done
      local candidate
      case "$scenario" in
        exact)
          candidate="$(candidate_json "$generator_expected_head")"
          printf '[%s]\n' "$candidate"
          ;;
        zero)
          printf '[]\n'
          ;;
        multiple)
          candidate="$(candidate_json "$generator_expected_head")"
          printf '[%s,%s]\n' "$candidate" "$candidate"
          ;;
        wrong-head)
          candidate="$(candidate_json '3333333333333333333333333333333333333333')"
          printf '[%s]\n' "$candidate"
          ;;
        *) return 90 ;;
      esac
      ;;
    view)
      if (( $# == 0 )) || [[ "$1" == --* ]]; then
        printf 'argument required when using the --repo flag\n' >&2
        return 2
      fi
      test "$1" = 17
      shift
      local view_fields=state,headRefName,headRefOid,baseRefName,isDraft
      view_fields+=,isCrossRepository,headRepository,headRepositoryOwner,mergeCommit
      local -a expected_view=(
        --repo "$canonical_repository"
        --json "$view_fields"
      )
      local -a actual_view=("$@")
      test "${#actual_view[@]}" = "${#expected_view[@]}"
      for index in "${!expected_view[@]}"; do
        test "${actual_view[$index]}" = "${expected_view[$index]}"
      done
      candidate_json "$generator_expected_head"
      ;;
    *) return 91 ;;
  esac
}

receipt_file=$1
receipt_dir=$2
scenario=$3
canonical_repository=H234598/Wirtelprimpf-generator
canonical_repo_id=R_kgDOTpr2BA
generator_head=feature/reviewed
generator_expected_head=2222222222222222222222222222222222222222
'''
            + discovery
            + r'''
printf '%s:%s\n' "$generator_pr_number" "$generator_pr_state"
'''
        )

        def execute(scenario: str) -> subprocess.CompletedProcess[str]:
            with tempfile.TemporaryDirectory(prefix="wirtelprimpf-pr-discovery-") as tmp:
                receipt = Path(tmp) / "absent.json"
                result = subprocess.run(  # nosec B603 -- fixed shell and controlled local fixture argv
                    ["/bin/bash", "-c", script, "pr-discovery-test", str(receipt), tmp, scenario],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=10,
                )
                self.assertFalse(receipt.exists())
                return result

        exact = execute("exact")
        self.assertEqual(exact.returncode, 0, exact.stderr)
        self.assertEqual(exact.stdout, "17:OPEN\n")
        for scenario in ("zero", "multiple", "wrong-head"):
            with self.subTest(scenario=scenario):
                rejected = execute(scenario)
                self.assertNotEqual(rejected.returncode, 0)
                self.assertNotIn(
                    "argument required when using the --repo flag",
                    rejected.stderr,
                )

    def test_task5_accepts_only_the_verified_task3_v3_receipt_sha(self) -> None:
        self.assertIn("# BEGIN TASK5_FACTORY_RECEIPT", self.task5_step2)
        receipt_guard = _marked_block(self.task5_step2, "TASK5_FACTORY_RECEIPT")
        production_metadata_guard = (
            'test "$(stat -c \'%u:%g:%a\' "$receipt_file")" = 1000:1000:600'
        )
        self.assertEqual(receipt_guard.count(production_metadata_guard), 1)
        fixture_receipt_guard = receipt_guard
        fixture_identity = (os.geteuid(), os.getegid())
        if os.geteuid() != 0 and fixture_identity != (1000, 1000):
            fixture_metadata_guard = production_metadata_guard.replace(
                "1000:1000:600",
                f"{fixture_identity[0]}:{fixture_identity[1]}:600",
            )
            fixture_receipt_guard = receipt_guard.replace(
                production_metadata_guard,
                fixture_metadata_guard,
                1,
            )
            self.assertNotIn(production_metadata_guard, fixture_receipt_guard)
        head = "2" * 40
        merge = "3" * 40
        valid = {
            "version": 3,
            "state": "verified",
            "actor_login": "H234598",
            "actor_id": 54270221,
            "repository_id": "R_kgDOTpr2BA",
            "repository": "H234598/Wirtelprimpf-generator",
            "canonical_origin": "https://github.com/H234598/Wirtelprimpf-generator.git",
            "pr_number": 17,
            "head_ref": "feature/reviewed",
            "expected_head": head,
            "base_before": "1" * 40,
            "head_tree": "4" * 40,
            "merge_date": "2026-08-02T00:00:00+00:00",
            "merge_message": "Merge pull request #17 from feature/reviewed",
            "merge_sha": merge,
            "review_id": 8142270,
            "review_author_login": "coderabbitai[bot]",
            "review_author_id": 136622811,
            "review_commit": head,
            "review_state": "APPROVED",
        }
        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-task5-receipt-") as tmp:
            receipt = Path(tmp) / "receipt.json"
            script = f"""
set -Eeuo pipefail
{fixture_receipt_guard}
receipt_file=$1
load_verified_task3_factory_sha
"""

            def validate(name: str, payload: dict[str, object]) -> subprocess.CompletedProcess[str]:
                receipt.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
                receipt.chmod(0o600)
                if os.geteuid() == 0:
                    os.chown(receipt, 1000, 1000)
                return subprocess.run(  # nosec B603 -- fixed local shell and fixture argv
                    ["/bin/bash", "-c", script, f"task5-receipt-{name}", str(receipt)],
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=10,
                )

            accepted = validate("valid", valid)
            self.assertEqual(accepted.returncode, 0, accepted.stderr)
            self.assertEqual(accepted.stdout, f"{merge}\n")
            invalid_cases = {
                "planned": dict(valid, state="planned"),
                "stale-review": dict(valid, review_commit="5" * 40),
                "wrong-review": dict(valid, review_state="CHANGES_REQUESTED"),
                "extra": {**valid, "unexpected": True},
            }
            for name, payload in invalid_cases.items():
                with self.subTest(name=name):
                    self.assertNotEqual(validate(name, payload).returncode, 0)

    def test_every_task5_step_rebinds_receipt_sha_and_merge_uses_exact_head_cas(self) -> None:
        for name, script in (
            ("step1", self.task5_step1),
            ("step2", self.task5_step2),
            ("step3", self.task5_step3),
            ("step4", self.task5_step4),
            ("step5", self.task5_step5),
            ("step6", self.task5_step6),
        ):
            with self.subTest(name=name):
                self.assertIn("load_verified_task3_factory_sha", script)
                self.assertIn("generator_factory_sha", script)
        self.assertIn("canonical_archive_repo_id=", self.task5_step5)
        self.assertIn("canonical_archive_repo_id=", self.task5_step6)
        self.assertIn("task5_gh pr merge", self.task5_step6)
        self.assertIn('--match-head-commit "$archive_head_sha"', self.task5_step6)
        self.assertIn("TASK5_STEP6_TELADI", self.task5_step6)
        self.assertIn("task5_token_call", self.task5_step6)

    def test_task5_step6_content_gate_uses_ubuntu_runner_baseline_tools(self) -> None:
        gate = _marked_block(self.task5_step6, "TASK5_STEP6_ARCHIVE_CONTENT_GATE")
        self.assertNotIn("/usr/bin/rg", gate)
        self.assertIn("/usr/bin/grep", gate)

    def test_task5_step6_archive_candidate_gate_enforces_exact_diff_and_pins(self) -> None:
        marker = "TASK5_STEP6_ARCHIVE_CONTENT_GATE"
        self.assertIn(f"# BEGIN {marker}", self.task5_step6)
        gate = _marked_block(self.task5_step6, marker)
        old_sha = "1" * 40
        factory_sha = "2" * 40

        def exercise(
            workflow: str,
            *,
            extra_file: bool = False,
            base_has_pr_trigger: bool = False,
        ) -> subprocess.CompletedProcess[str]:
            with tempfile.TemporaryDirectory(prefix="wirtelprimpf-step6-candidate-") as tmp:
                repo = Path(tmp) / "archive"
                _fixture_git(
                    ["init", "-q", str(repo)],
                    check=True,
                )
                _fixture_git(
                    ["-C", str(repo), "config", "user.name", "Contract Test"],
                    check=True,
                )
                _fixture_git(
                    ["-C", str(repo), "config", "user.email", "contract@example.invalid"],
                    check=True,
                )
                workflow_path = repo / ".github" / "workflows" / "pages.yml"
                workflow_path.parent.mkdir(parents=True)
                workflow_path.write_text(
                    "on:\n  push:\n"
                    + ("  pull_request:\n" if base_has_pr_trigger else "")
                    + "jobs:\n  publish:\n"
                    "    uses: H234598/Wirtelprimpf-generator/.github/workflows/"
                    f"archive-pages.yml@{old_sha}\n"
                    "    with:\n"
                    f'      factory_ref: "{old_sha}"\n',
                    encoding="utf-8",
                )
                _fixture_git(["-C", str(repo), "add", "."], check=True)
                _fixture_git(
                    ["-C", str(repo), "commit", "-q", "-m", "base"],
                    check=True,
                )
                base = _fixture_git(
                    ["-C", str(repo), "rev-parse", "HEAD"],
                    text=True,
                    capture_output=True,
                    check=True,
                ).stdout.strip()
                workflow_path.write_text(workflow, encoding="utf-8")
                if extra_file:
                    (repo / "unexpected").write_text("unexpected\n", encoding="utf-8")
                _fixture_git(["-C", str(repo), "add", "."], check=True)
                _fixture_git(
                    ["-C", str(repo), "commit", "-q", "-m", "candidate"],
                    check=True,
                )
                head = _fixture_git(
                    ["-C", str(repo), "rev-parse", "HEAD"],
                    text=True,
                    capture_output=True,
                    check=True,
                ).stdout.strip()
                script = f"set -Eeuo pipefail\n{gate}\nassert_task5_archive_candidate \"$1\" \"$2\" \"$3\" \"$4\"\n"
                return subprocess.run(  # nosec B603 -- fixed local shell and fixture argv
                    [
                        "/bin/bash",
                        "-c",
                        script,
                        "step6-candidate-test",
                        str(repo),
                        base,
                        head,
                        factory_sha,
                    ],
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=10,
                )

        valid = (
            "on:\n  push:\n"
            "jobs:\n  publish:\n"
            "    uses: H234598/Wirtelprimpf-generator/.github/workflows/"
            f"archive-pages.yml@{factory_sha}\n"
            "    with:\n"
            f'      factory_ref: "{factory_sha}"\n'
        )
        accepted = exercise(valid)
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertEqual(accepted.stdout, "0\n")

        with_pr_trigger = valid.replace("  push:\n", "  push:\n  pull_request:\n")
        accepted_with_pr = exercise(with_pr_trigger, base_has_pr_trigger=True)
        self.assertEqual(accepted_with_pr.returncode, 0, accepted_with_pr.stderr)
        self.assertEqual(accepted_with_pr.stdout, "1\n")

        wrong_pin = valid.replace(f'factory_ref: "{factory_sha}"', f'factory_ref: "{"3" * 40}"')
        extra_sha = valid + f"# {'4' * 40}\n"
        for name, workflow, extra_file in (
            ("wrong-pin", wrong_pin, False),
            ("extra-sha", extra_sha, False),
            ("extra-file", valid, True),
        ):
            with self.subTest(name=name):
                self.assertNotEqual(exercise(workflow, extra_file=extra_file).returncode, 0)

    def test_task5_step6_revalidates_immediately_and_observes_remote_merge_before_pages(self) -> None:
        merge_index = self.task5_step6.index("task5_gh pr merge")
        pages_index = self.task5_step6.index('archive_run_id=""')
        premerge = self.task5_step6[:merge_index]
        postmerge = self.task5_step6[merge_index:pages_index]
        self.assertGreaterEqual(premerge.count("load_verified_task3_factory_sha"), 2)
        self.assertIn("TASK5_STEP6_FINAL_PREMERGE", premerge)
        self.assertIn("assert_task5_archive_candidate", premerge)
        self.assertIn("statusCheckRollup", premerge)
        self.assertIn('test "$archive_has_pr_trigger" = 0', premerge)
        self.assertIn("headRepository", premerge)
        self.assertIn(".files[].path", premerge)
        self.assertIn('.state == "MERGED"', postmerge)
        self.assertIn("mergeCommit", postmerge)
        self.assertIn("git/ref/heads/main", postmerge)
        self.assertIn("git/matching-refs/heads/chore/pin-transactional-site-factory", postmerge)
        self.assertIn("task5_postmerge_local_main", postmerge)
        self.assertIn("refs/heads/main:refs/remotes/origin/main", postmerge)
        self.assertIn("'refs/heads/main^{commit}'", postmerge)
        self.assertIn("'refs/remotes/origin/main^{commit}'", postmerge)
        self.assertIn('test "$local_main" = "$merged_sha"', postmerge)
        self.assertIn('test "$remote_main" = "$merged_sha"', postmerge)
        self.assertIn("switch main", postmerge)

    def test_task5_postmerge_git_config_is_exactly_allowlisted(self) -> None:
        postmerge_child = _quoted_heredoc(
            self.task5_step6, "TASK5_POSTMERGE_TELADI"
        )[1]
        guard = _marked_block(postmerge_child, "TASK5_POSTMERGE_GIT_GUARD")
        hostile_entries = (
            ("filter.attack.smudge", "/bin/false"),
            ("core.attributesFile", "/tmp/hostile-attributes"),  # nosec B108
            ("core.worktree", "/tmp/hostile-worktree"),  # nosec B108
            ("diff.attack.command", "/bin/false"),
            ("merge.attack.driver", "/bin/false"),
        )
        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-postmerge-config-") as tmp:
            repository = Path(tmp) / "archive"
            canonical = "https://github.com/H234598/Wirtelprimpf-0001.git"
            _fixture_git(["init", "-q", "-b", "main", str(repository)], check=True)
            _fixture_git(
                ["-C", str(repository), "remote", "add", "origin", canonical],
                check=True,
            )
            _fixture_git(
                [
                    "-C",
                    str(repository),
                    "config",
                    "--local",
                    "remote.origin.fetch",
                    "+refs/heads/main:refs/remotes/origin/main",
                ],
                check=True,
            )
            for key, value in (
                ("branch.main.remote", "origin"),
                ("branch.main.merge", "refs/heads/main"),
            ):
                _fixture_git(
                    ["-C", str(repository), "config", "--local", key, value],
                    check=True,
                )
            script = (
                "set -Eeuo pipefail\n"
                f"archive_checkout={repository!s}\n"
                f"canonical_origin={canonical}\n"
                f"{guard}\n"
                "assert_safe_task5_postmerge_config\n"
            )
            accepted = subprocess.run(
                ["/bin/bash", "-c", script],
                text=True,
                capture_output=True,
                check=False,
                timeout=10,
                env={"HOME": "/home/teladi", "PATH": "/usr/bin:/bin"},
            )
            self.assertEqual(accepted.returncode, 0, accepted.stderr)
            for key, value in hostile_entries:
                _fixture_git(
                    ["-C", str(repository), "config", "--local", key, value],
                    check=True,
                )
                rejected = subprocess.run(
                    ["/bin/bash", "-c", script],
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=10,
                    env={"HOME": "/home/teladi", "PATH": "/usr/bin:/bin"},
                )
                with self.subTest(key=key):
                    self.assertNotEqual(rejected.returncode, 0)
                _fixture_git(
                    ["-C", str(repository), "config", "--local", "--unset-all", key],
                    check=True,
                )

    def test_task3_expected_text_has_no_normative_v2_receipt(self) -> None:
        task3_expected_start = self.document.index(
            "Expected: GitHub main contains the deterministic two-parent merge",
        )
        task3_expected_end = self.document.index(
            "#### Verbindliches Execution-Context-Erratum für Task 3 Step 5",
            task3_expected_start,
        )
        task3_expected = self.document[task3_expected_start:task3_expected_end]
        self.assertIn("private atomic v3 receipt", task3_expected)
        self.assertNotIn("private atomic v2 receipt", task3_expected)

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
            poisoned_global = Path(tmp) / "poisoned-global.gitconfig"
            poisoned_global.write_text(
                '[url "https://attacker.invalid/"]\n'
                "\tinsteadOf = https://github.com/\n",
                encoding="utf-8",
            )
            poisoned_probe_env = dict(_FIXTURE_GIT_ENV)
            poisoned_probe_env["GIT_CONFIG_GLOBAL"] = str(poisoned_global)
            _fixture_git(["init", "-q", str(repo)], check=True)
            _fixture_git(["-C", str(repo), "remote", "add", "origin", canonical], check=True)
            check_script = f"set -Eeuo pipefail\n{predicate}\ncanonical_origin=$1\nassert_canonical_origin origin\n"
            accepted = subprocess.run(
                ["/bin/bash", "-c", check_script, "origin-test", canonical],
                cwd=repo,
                text=True,
                capture_output=True,
                check=False,
                timeout=10,
                env=poisoned_probe_env,
            )
            self.assertEqual(accepted.returncode, 0, accepted.stderr)

            _fixture_git(
                ["-C", str(repo), "remote", "set-url", "--add", "--push", "origin", canonical],
                check=True,
            )
            _fixture_git(
                [
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
                ["/bin/bash", "-c", check_script, "origin-test", canonical],
                cwd=repo,
                text=True,
                capture_output=True,
                check=False,
                timeout=10,
                env=poisoned_probe_env,
            )
            self.assertNotEqual(rejected.returncode, 0)

    def test_normative_git_remote_disables_a_real_pre_push_hook(self) -> None:
        self.assertIn("# BEGIN TASK3_FD_TOKEN_CALL", self.task3_merge)
        self.assertIn("# BEGIN TASK3_GIT_REMOTE", self.task3_merge)
        git_remote = _marked_block(self.task3_merge, "TASK3_GIT_REMOTE")
        self.assertIn("-c core.hooksPath=/dev/null", git_remote)
        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-hook-contract-") as tmp:
            source = Path(tmp) / "source"
            remote = Path(tmp) / "remote.git"
            leak = Path(tmp) / "hook-leak"
            _fixture_git(["init", "-q", str(source)], check=True)
            _fixture_git(["init", "-q", "--bare", str(remote)], check=True)
            _fixture_git(["-C", str(source), "config", "user.name", "Contract Test"], check=True)
            _fixture_git(
                ["-C", str(source), "config", "user.email", "contract@example.invalid"],
                check=True,
            )
            (source / "tracked").write_text("reviewed\n", encoding="utf-8")
            _fixture_git(["-C", str(source), "add", "tracked"], check=True)
            _fixture_git(
                ["-C", str(source), "commit", "-q", "-m", "reviewed"], check=True
            )
            hook = source / ".git/hooks/pre-push"
            hook.write_text(
                f"#!/bin/sh\nprintf '%s' \"${{GH_TOKEN:-missing}}\" >'{leak}'\nexit 91\n",
                encoding="utf-8",
            )
            hook.chmod(0o700)
            result = _fixture_git(
                [
                    "-C",
                    str(source),
                    "push",
                    str(remote),
                    "HEAD:refs/heads/main",
                ],
                text=True,
                capture_output=True,
                check=False,
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(leak.exists(), "the real pre-push hook observed the tokenized Git process")
            remote_head = _fixture_git(
                ["-C", str(remote), "rev-parse", "refs/heads/main"],
                text=True,
                capture_output=True,
                check=True,
            ).stdout.strip()
            local_head = _fixture_git(
                ["-C", str(source), "rev-parse", "HEAD"],
                text=True,
                capture_output=True,
                check=True,
            ).stdout.strip()
            self.assertEqual(remote_head, local_head)

    def test_git_remote_rejects_url_specific_authorization_extraheader(self) -> None:
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
                    _fixture_git(["init", "-q", str(repo)], check=True)
                    _fixture_git(
                        [
                            "-C",
                            str(repo),
                            "config",
                            f"http.{remote_url}.extraHeader",
                            f"Authorization: Basic {sentinel}",
                        ],
                        check=True,
                    )
                    git_remote = _shell_function(plan_script, "git_remote")
                    git_config_guard = _marked_block(
                        plan_script,
                        "TASK3_GIT_CONFIG_GUARD",
                    )
                    script = f"""
set -Eeuo pipefail
{git_config_guard}
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
cd "$1"
if git_remote ls-remote "$2"; then
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
            self.assertEqual(received_paths, [])
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
                _fixture_git(["init", "-q", str(repo)], check=True)
                _fixture_git(
                    ["-C", str(repo), "config", "core.askPass", str(askpass)],
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
generator_review_id=8142270
generator_review_author_login='coderabbitai[bot]'
generator_review_author_id=136622811
generator_review_commit=$generator_expected_head
generator_review_state=APPROVED
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
generator_review_id=8142270
generator_review_author_login='coderabbitai[bot]'
generator_review_author_id=136622811
generator_review_commit=$4
generator_review_state=APPROVED
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

    def test_existing_receipt_reconcile_and_observe_do_not_refetch_live_review(self) -> None:
        derive_merge = _marked_block(self.task3_merge, "TASK3_DERIVE_MERGE")
        validate_receipt = _marked_block(self.task3_merge, "TASK3_VALIDATE_RECEIPT")
        classifier = _marked_block(self.task3_merge, "TASK3_REMOTE_STATE")
        retry_start = self.task3_merge.index(
            'else\n  case "$generator_pr_state" in OPEN|MERGED)'
        ) + len("else\n")
        retry_end = self.task3_merge.index("\nfi\n\nremote_main_sha=", retry_start)
        retry_branch = self.task3_merge[retry_start:retry_end]
        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-reconcile-contract-") as tmp:
            fixture = self._make_merge_fixture(tmp)
            script = f"""
set -Eeuo pipefail
{derive_merge}
{validate_receipt}
{classifier}
receipt_file=$1
task3_actor_login=H234598
task3_actor_id=54270221
canonical_repo_id=R_kgDOTpr2BA
canonical_repository=H234598/Wirtelprimpf-generator
canonical_origin=https://github.com/H234598/Wirtelprimpf-generator.git
generator_head=feature/reviewed
generator_expected_head=$2
generator_pr_state=MERGED
live_review_decision=$3
remote_main=$4
remote_head=$5
assert_task3_current_review() {{
  printf 'unexpected live review fetch: %s\\n' "$live_review_decision" >&2
  return 97
}}
load_task3_receipt
generator_pr_number=$receipt_pr_number
generator_base_before=$receipt_base_before
{retry_branch}
classify_task3_remote_action \
  "$receipt_state" "$remote_main" "$remote_head" \
  "$generator_base_before" "$generator_merge_sha" \
  "$generator_expected_head"
"""
            self.assertIn(
                "printf 'unexpected live review fetch: %s\\n'",
                script,
            )

            def execute(
                state: str,
                live_review_decision: str,
                remote_main: str,
                remote_head: str,
            ) -> subprocess.CompletedProcess[str]:
                receipt = self._receipt_for_fixture(fixture)
                receipt["state"] = state
                receipt_path = Path(tmp) / f"receipt-{state}.json"
                receipt_path.write_text(
                    json.dumps(receipt, sort_keys=True),
                    encoding="utf-8",
                )
                receipt_path.chmod(0o600)
                return subprocess.run(  # nosec B603 -- fixed shell and controlled local fixture argv
                    [
                        "/bin/bash",
                        "-c",
                        script,
                        "receipt-reconcile-test",
                        str(receipt_path),
                        fixture["head"],
                        live_review_decision,
                        remote_main,
                        remote_head,
                    ],
                    cwd=fixture["repo"],
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=10,
                )

            reconcile = execute("planned", "null", fixture["expected_merge"], "")
            self.assertEqual(reconcile.returncode, 0, reconcile.stderr)
            self.assertEqual(reconcile.stdout, "reconcile\n")

            observe = execute(
                "remote_committed",
                "CHANGES_REQUESTED",
                fixture["expected_merge"],
                "",
            )
            self.assertEqual(observe.returncode, 0, observe.stderr)
            self.assertEqual(observe.stdout, "observe\n")

            unknown = execute("planned", "null", fixture["base"], "")
            self.assertNotEqual(unknown.returncode, 0)
            self.assertNotIn("unexpected live review fetch", unknown.stderr)

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

    def test_pr4_reopen_rejection_is_machine_bound_and_never_replayed(self) -> None:
        evidence = json.loads(PR4_REOPEN_EVIDENCE.read_text(encoding="utf-8"))
        self.assertEqual(
            evidence,
            {
                "schema": "wirtelprimpf-pr4-reopen-rejection/v1",
                "attempt_count": 1,
                "request": {
                    "method": "PATCH",
                    "path": "/repos/H234598/Wirtelprimpf-generator/pulls/4",
                    "body": {"state": "open"},
                },
                "response": {
                    "status": 422,
                    "error": {
                        "resource": "PullRequest",
                        "code": "custom",
                        "field": "state",
                        "message": (
                            "state cannot be changed. These commits are already merged."
                        ),
                    },
                },
                "binding": {
                    "actor_login": "H234598",
                    "actor_id": 54270221,
                    "repository_id": "R_kgDOTpr2BA",
                    "repository": "H234598/Wirtelprimpf-generator",
                    "pr_number": 4,
                    "receipt_version": 3,
                    "receipt_state": "remote_committed",
                    "base_before": "b00d824adee47341e3251bc18e09239fde1c5939",
                    "expected_head": "5aab1907b9af73fe6d8ef56e49beb7a527877e19",
                    "head_tree": "967a0b41f6525de79dfc91e1b52dd8ca3dc85ac8",
                    "merge_sha": "274b25c9e1f9ea97d3b060997ed5c425d2b30e9f",
                    "merge_parents": [
                        "b00d824adee47341e3251bc18e09239fde1c5939",
                        "5aab1907b9af73fe6d8ef56e49beb7a527877e19",
                    ],
                    "review_id": 4838199265,
                    "review_author_id": 136622811,
                    "review_commit": "5aab1907b9af73fe6d8ef56e49beb7a527877e19",
                    "review_state": "APPROVED",
                },
            },
        )
        recovery = _marked_block(self.task3_merge, "TASK3_PR4_CLOSED_RECOVERY")
        normalized = " ".join(recovery.split())
        self.assertNotIn("--method PATCH", normalized)
        self.assertNotIn("-X PATCH", normalized)
        self.assertNotIn("state=open", normalized)
        self.assertIn("attempt_count == 1", recovery)
        self.assertIn("task3_git_probe hash-object", recovery)
        evidence_blob = _fixture_git(
            ["hash-object", "--", str(PR4_REOPEN_EVIDENCE)],
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        self.assertEqual(evidence_blob, "769dac62c3d3fa734945de5e83af4444fad1b9b3")
        self.assertIn(f"PR4_REOPEN_EVIDENCE_BLOB={evidence_blob}", recovery)

    def test_pr4_closed_recovery_classifier_is_exact_and_never_returns_push(self) -> None:
        recovery = _marked_block(self.task3_merge, "TASK3_PR4_CLOSED_RECOVERY")
        classifier = _shell_function(
            recovery,
            "classify_task3_pr4_closed_action",
        )
        validator = _shell_function(
            recovery,
            "assert_task3_pr4_closed_binding",
        )
        base = "b00d824adee47341e3251bc18e09239fde1c5939"
        head = "5aab1907b9af73fe6d8ef56e49beb7a527877e19"
        merge = "274b25c9e1f9ea97d3b060997ed5c425d2b30e9f"
        script = f"""
set -Eeuo pipefail
{validator}
{classifier}
classify_task3_pr4_closed_action "$1" "$2" "$3" "$4"
"""

        def classify(
            state: str,
            remote_main: str,
            remote_head: str,
            binding: dict[str, object],
        ) -> subprocess.CompletedProcess[str]:
            return subprocess.run(  # nosec B603 -- fixed local shell and JSON fixture
                [
                    "/bin/bash",
                    "-c",
                    script,
                    "pr4-closed-state-test",
                    state,
                    remote_main,
                    remote_head,
                    json.dumps(binding, separators=(",", ":")),
                ],
                text=True,
                capture_output=True,
                check=False,
                timeout=10,
            )

        accepted = (
            (
                "remote_committed",
                merge,
                head,
                self._pr4_closed_binding(),
                "closed-verify-cleanup\n",
            ),
            (
                "verified",
                merge,
                head,
                self._pr4_closed_binding("verified"),
                "closed-cleanup\n",
            ),
            (
                "verified",
                merge,
                "",
                self._pr4_closed_binding("verified", ""),
                "closed-observe\n",
            ),
        )
        for state, remote_main, remote_head, binding, expected in accepted:
            with self.subTest(accepted=(state, remote_main, remote_head)):
                result = classify(state, remote_main, remote_head, binding)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, expected)
                self.assertNotIn("push", result.stdout)

        rejected_inputs = (
            ("planned", merge, head, self._pr4_closed_binding()),
            (
                "remote_committed",
                merge,
                "",
                self._pr4_closed_binding("remote_committed", ""),
            ),
            ("remote_committed", base, head, self._pr4_closed_binding()),
            ("verified", merge, "4" * 40, self._pr4_closed_binding("verified")),
        )
        for state, remote_main, remote_head, binding in rejected_inputs:
            with self.subTest(rejected=(state, remote_main, remote_head)):
                result = classify(state, remote_main, remote_head, binding)
                self.assertNotEqual(result.returncode, 0)

        drift_cases: dict[str, tuple[str, object]] = {
            "actor-id": ("actor.id", 7),
            "repo-id": ("repository.id", "R_foreign"),
            "receipt-version": ("receipt.version", 4),
            "pr-number": ("receipt.pr_number", 5),
            "base": ("receipt.base_before", "1" * 40),
            "head": ("receipt.expected_head", "2" * 40),
            "tree": ("receipt.head_tree", "3" * 40),
            "merge": ("receipt.merge_sha", "4" * 40),
            "graphql-state": ("graphql_pr.state", "MERGED"),
            "graphql-merged": ("graphql_pr.merged", True),
            "reopen": ("graphql_pr.viewer_can_reopen", True),
            "rest-mergeable": ("rest_pr.mergeable", False),
            "timeline": ("timeline.0.created_at", "2026-08-02T11:08:30Z"),
            "compare": ("compare.ahead_by", 2),
            "parent": ("commit.parents.0", "5" * 40),
            "review": ("review.id", 1),
            "historical-status": ("historical_reopen.response.status", 200),
        }
        for name, (path, value) in drift_cases.items():
            binding = self._pr4_closed_binding()
            cursor: object = binding
            parts = path.split(".")
            for part in parts[:-1]:
                if isinstance(cursor, list):
                    cursor = cursor[int(part)]
                else:
                    assert isinstance(cursor, dict)
                    cursor = cursor[part]
            if isinstance(cursor, list):
                cursor[int(parts[-1])] = value
            else:
                assert isinstance(cursor, dict)
                cursor[parts[-1]] = value
            with self.subTest(drift=name):
                result = classify("remote_committed", merge, head, binding)
                self.assertNotEqual(result.returncode, 0)

    def test_pr4_cleanup_has_only_an_exact_feature_lease_after_all_live_gates(self) -> None:
        recovery = _marked_block(self.task3_merge, "TASK3_PR4_CLOSED_RECOVERY")
        deletion = _marked_block(recovery, "TASK3_PR4_FEATURE_REF_DELETE")
        normalized_delete = " ".join(deletion.split())
        self.assertEqual(deletion.count("git_remote push"), 1)
        self.assertIn(
            "--force-with-lease=refs/heads/$generator_head:$generator_expected_head",
            normalized_delete,
        )
        self.assertIn('\":refs/heads/$generator_head\"', normalized_delete)
        self.assertNotIn("refs/heads/main:", normalized_delete)
        self.assertNotIn("$generator_merge_sha:refs/heads/main", normalized_delete)
        self.assertNotIn("--atomic", normalized_delete)
        delete_offset = recovery.index("# BEGIN TASK3_PR4_FEATURE_REF_DELETE")
        gated = recovery[:delete_offset]
        for required_gate in (
            "require_task3_auth",
            "require_canonical_repository",
            "assert_task3_current_review CLOSED",
            "assert_task3_pr4_closed_binding",
            "assert_task3_pr4_timeline",
            "assert_task3_pr4_compare",
            "assert_task3_pr4_merge_object",
            "write_task3_receipt verified",
        ):
            self.assertIn(required_gate, gated)
        self.assertLess(
            gated.index("assert_task3_current_review CLOSED"),
            gated.index("write_task3_receipt verified"),
        )
        self.assertIn("closed-verify-cleanup", recovery)
        self.assertIn("closed-cleanup", recovery)
        self.assertIn("closed-observe", recovery)

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
        self.assertIn(
            "task3_git_probe remote get-url --push --all origin",
            self.task3_merge,
        )
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
        atomic_push = self.task3_merge.index("git_remote push --atomic")
        committed_after_push = self.task3_merge.index(
            "task3_remote_committed=1",
            atomic_push,
        )
        remote_receipt_after_push = self.task3_merge.index(
            "write_task3_receipt remote_committed",
            committed_after_push,
        )
        self.assertLess(
            self.task3_merge.index("task3_push_started=1"),
            atomic_push,
        )
        self.assertLess(atomic_push, committed_after_push)
        self.assertLess(committed_after_push, remote_receipt_after_push)

    def test_step9_contains_the_exact_smokes_and_orders_marker_producer_before_consumer(self) -> None:
        self.assertIn(self.smoke_api, self.deployment)
        self.assertIn(self.smoke_sync, self.deployment)
        self.assertNotIn("Execute the exact Step-5", self.deployment)
        admin_start = self.deployment.index(
            "systemctl --user start wirtelprimpf-admin.service"
        )
        readiness = self.deployment.index("\nwait_admin_ready_loopback 8765\n")
        first_settings_smoke = self.deployment.index(self.smoke_api)
        self.assertEqual(self.deployment.count("\nwait_admin_ready_loopback 8765\n"), 1)
        self.assertLess(admin_start, readiness)
        self.assertLess(readiness, first_settings_smoke)
        producer = self.deployment.index("marker_path.write_text")
        consumer = self.deployment.index(
            "smoke_owned_revision=\"$(jq -er '.revision' "
            '"$deploy_backup/smoke-owned-revision.json")"'
        )
        self.assertLess(producer, consumer)

    def test_admin_readiness_gate_waits_for_a_delayed_loopback_listener(self) -> None:
        self.assertIn("wait_admin_ready_loopback() {\n", self.deployment)
        readiness = _shell_function(self.deployment, "wait_admin_ready_loopback")
        self.assertEqual(
            readiness.count('"http://127.0.0.1:${port}/api/status"'),
            1,
        )
        self.assertNotIn("--retry", readiness)
        received_paths: list[str] = []
        server_holder: list[ThreadingHTTPServer] = []
        server_error: list[BaseException] = []
        server_started = threading.Event()

        class DelayedReadinessHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                received_paths.append(self.path)
                if self.path != "/api/status":
                    self.send_response(404)
                    self.end_headers()
                    return
                body = b"{}"
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: object) -> None:
                del format, args

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as candidate:
            candidate.bind(("127.0.0.1", 0))
            port = candidate.getsockname()[1]

        def delayed_server() -> None:
            time.sleep(0.25)
            try:
                server = ThreadingHTTPServer(
                    ("127.0.0.1", port),
                    DelayedReadinessHandler,
                )
                server_holder.append(server)
                server_started.set()
                server.serve_forever()
            except BaseException as error:  # pragma: no cover - diagnostic path
                server_error.append(error)
                server_started.set()

        thread = threading.Thread(target=delayed_server, daemon=True)
        thread.start()
        script = f"""
set -Eeuo pipefail
{readiness}
systemctl() {{
  case "$*" in
    '--user show wirtelprimpf-admin.service -p ActiveState --value')
      printf 'active\n'
      ;;
    '--user show wirtelprimpf-admin.service -p SubState --value')
      printf 'running\n'
      ;;
    '--user show wirtelprimpf-admin.service -p InvocationID --value')
      printf '11111111111111111111111111111111\n'
      ;;
    *) return 97 ;;
  esac
}}
wait_admin_ready_loopback "$1"
"""
        started = time.monotonic()
        try:
            result = subprocess.run(  # nosec B603 -- exact helper and real loopback server
                ["/bin/bash", "-c", script, "admin-readiness-delayed", str(port)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
                timeout=8,
                env={"HOME": "/home/teladi", "PATH": "/usr/bin:/bin"},
            )
            elapsed = time.monotonic() - started
        finally:
            server_started.wait(timeout=3)
            if server_holder:
                server_holder[0].shutdown()
                server_holder[0].server_close()
            thread.join(timeout=5)

        self.assertEqual(server_error, [])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertGreaterEqual(elapsed, 0.20)
        self.assertLess(elapsed, 5.0)
        self.assertEqual(received_paths, ["/api/status"])

    def test_admin_readiness_gate_fails_closed_within_a_fixed_bound(self) -> None:
        self.assertIn("wait_admin_ready_loopback() {\n", self.deployment)
        readiness = _shell_function(self.deployment, "wait_admin_ready_loopback")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as candidate:
            candidate.bind(("127.0.0.1", 0))
            port = candidate.getsockname()[1]

        script = f"""
set -Eeuo pipefail
{readiness}
systemctl() {{
  case "$*" in
    '--user show wirtelprimpf-admin.service -p ActiveState --value')
      printf 'active\n'
      ;;
    '--user show wirtelprimpf-admin.service -p SubState --value')
      printf 'running\n'
      ;;
    '--user show wirtelprimpf-admin.service -p InvocationID --value')
      printf '22222222222222222222222222222222\n'
      ;;
    *) return 97 ;;
  esac
}}
wait_admin_ready_loopback "$1"
"""
        started = time.monotonic()
        result = subprocess.run(  # nosec B603 -- exact helper against unused loopback port
            ["/bin/bash", "-c", script, "admin-readiness-unbound", str(port)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=8,
            env={"HOME": "/home/teladi", "PATH": "/usr/bin:/bin"},
        )
        elapsed = time.monotonic() - started

        self.assertNotEqual(result.returncode, 0)
        self.assertLess(elapsed, 7.0)
        self.assertIn("admin readiness deadline exhausted", result.stderr)

        invalid = subprocess.run(  # nosec B603 -- exact helper rejects non-port input
            ["/bin/bash", "-c", script, "admin-readiness-invalid", "example.invalid"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=2,
            env={"HOME": "/home/teladi", "PATH": "/usr/bin:/bin"},
        )
        self.assertNotEqual(invalid.returncode, 0)

    def test_admin_readiness_gate_rejects_activation_change_during_probe(self) -> None:
        self.assertIn("wait_admin_ready_loopback() {\n", self.deployment)
        readiness = _shell_function(self.deployment, "wait_admin_ready_loopback")
        received_paths: list[str] = []

        class ImmediateReadinessHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                received_paths.append(self.path)
                body = b"{}"
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: object) -> None:
                del format, args

        server = ThreadingHTTPServer(("127.0.0.1", 0), ImmediateReadinessHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = server.server_address[1]
        try:
            with tempfile.TemporaryDirectory(prefix="wirtelprimpf-admin-readiness-") as tmp:
                invocation_calls = Path(tmp) / "invocation-calls"
                invocation_calls.write_text("0\n", encoding="utf-8")
                script = f"""
set -Eeuo pipefail
{readiness}
systemctl() {{
  case "$*" in
    '--user show wirtelprimpf-admin.service -p ActiveState --value')
      printf 'active\n'
      ;;
    '--user show wirtelprimpf-admin.service -p SubState --value')
      printf 'running\n'
      ;;
    '--user show wirtelprimpf-admin.service -p InvocationID --value')
      count="$(<"$INVOCATION_CALLS")"
      count=$((count + 1))
      printf '%s\n' "$count" >"$INVOCATION_CALLS"
      if [[ "$count" == 1 ]]; then
        printf 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n'
      else
        printf 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\n'
      fi
      ;;
    *) return 97 ;;
  esac
}}
wait_admin_ready_loopback "$1"
"""
                result = subprocess.run(  # nosec B603 -- exact helper and real loopback server
                    ["/bin/bash", "-c", script, "admin-readiness-race", str(port)],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=5,
                    env={
                        "HOME": "/home/teladi",
                        "PATH": "/usr/bin:/bin",
                        "INVOCATION_CALLS": str(invocation_calls),
                    },
                )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("admin activation changed during readiness probe", result.stderr)
        self.assertEqual(received_paths, ["/api/status"])

    def test_step9_provisions_one_exact_backend_wheel_then_builds_offline_both_ways(self) -> None:
        backend = _marked_block(
            self.deployment,
            "TASK4_BUILD_BACKEND_BUNDLE",
        )
        self.assertIn("setuptools-83.0.0-py3-none-any.whl", backend)
        self.assertIn(
            "29b23c360f22f414dc7336bb39178cc7bcbf6021ed2733cde173f09dba19abb3",
            backend,
        )
        self.assertIn("1008090", backend)
        self.assertIn(
            "https://files.pythonhosted.org/packages/5d/40/e1e72872c6354b306daef1703549e8e83b4d43cfea356311bf722a043752/setuptools-83.0.0-py3-none-any.whl",
            backend,
        )
        self.assertIn("setuptools==83.0.0", backend)
        self.assertIn("4723b97f4d3f3c1d817e4896c0f7d59642e326ad891c7037482d2455b8a6bb4c", backend)
        self.assertIn("--retry 0", backend)
        self.assertIn("--no-index", backend)
        self.assertIn("--find-links", backend)
        self.assertIn("--build-constraint", backend)
        self.assertNotIn("--no-build-isolation", self.deployment)
        self.assertEqual(
            self.deployment.count('install_editable_offline_bounded "$runtime"'),
            2,
        )
        self.assertLess(
            self.deployment.index("provision_build_backend_bundle"),
            self.deployment.index("# The first operational mutation"),
        )

    def test_backend_bundle_helpers_are_hash_bound_atomic_idempotent_and_no_retry(self) -> None:
        backend = _marked_block(
            self.deployment,
            "TASK4_BUILD_BACKEND_BUNDLE",
        )
        validate = _shell_function(backend, "validate_exact_build_backend_file")
        download = _shell_function(backend, "download_exact_build_backend")
        install = _shell_function(backend, "install_editable_offline_bounded")

        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-backend-bundle-") as tmp:
            root = Path(tmp)
            fakebin = root / "bin"
            fakebin.mkdir()
            fixture = root / "fixture.whl"
            fixture.write_bytes(b"exact-wheel\n")
            expected_hash = hashlib.sha256(fixture.read_bytes()).hexdigest()
            calls = root / "curl-calls"
            pip_log = root / "pip-log"
            fake_curl = fakebin / "curl"
            fake_curl.write_text(
                "#!/bin/bash\n"
                "set -Eeuo pipefail\n"
                ": \"${BACKEND_FIXTURE:?}\" \"${BACKEND_CALLS:?}\"\n"
                "printf 'call\\n' >>\"$BACKEND_CALLS\"\n"
                "destination=\n"
                "while (($#)); do\n"
                "  case \"$1\" in\n"
                "    --output) destination=\"$2\"; shift 2 ;;\n"
                "    *) shift ;;\n"
                "  esac\n"
                "done\n"
                "test -n \"$destination\"\n"
                "cp -- \"$BACKEND_FIXTURE\" \"$destination\"\n",
                encoding="utf-8",
            )
            fake_curl.chmod(0o755)
            runtime = root / "runtime"
            python = runtime / ".venv" / "bin" / "python"
            python.parent.mkdir(parents=True)
            python.write_text(
                "#!/bin/bash\n"
                "set -Eeuo pipefail\n"
                ": \"${PIP_LOG:?}\"\n"
                "printf 'NO_INDEX=%s\\nFIND_LINKS=%s\\nCACHE=%s\\nTMP=%s\\n' "
                "\"${PIP_NO_INDEX:-}\" \"${PIP_FIND_LINKS:-}\" \"${PIP_CACHE_DIR:-}\" "
                "\"${TMPDIR:-}\" >>\"$PIP_LOG\"\n"
                "printf '%q ' \"$@\" >>\"$PIP_LOG\"\n"
                "printf '\\n' >>\"$PIP_LOG\"\n",
                encoding="utf-8",
            )
            python.chmod(0o755)
            wheelhouse = root / "wheelhouse"
            wheelhouse.mkdir(mode=0o700)
            destination = wheelhouse / fixture.name
            constraint = wheelhouse / "build-constraint.txt"
            constraint.write_text("fixture==1\n", encoding="utf-8")
            constraint.chmod(0o600)
            constraint_hash = hashlib.sha256(constraint.read_bytes()).hexdigest()
            script = "\n".join(
                (
                    "set -Eeuo pipefail",
                    "runtime=$RUNTIME",
                    "backend_constraint_value=fixture==1",
                    validate,
                    download,
                    install,
                    'download_exact_build_backend "https://example.invalid/exact.whl" '
                    '"$DESTINATION" "$EXPECTED_SIZE" "$EXPECTED_HASH"',
                    'download_exact_build_backend "https://example.invalid/exact.whl" '
                    '"$DESTINATION" "$EXPECTED_SIZE" "$EXPECTED_HASH"',
                    'install_editable_offline_bounded "$RUNTIME" "$WHEELHOUSE" '
                    '"$DESTINATION" "$EXPECTED_SIZE" "$EXPECTED_HASH" '
                    '"$CONSTRAINT" "$CONSTRAINT_HASH"',
                )
            )
            environment = {
                "PATH": f"{fakebin}:/usr/bin:/bin",
                "HOME": str(root),
                "BACKEND_FIXTURE": str(fixture),
                "BACKEND_CALLS": str(calls),
                "PIP_LOG": str(pip_log),
                "DESTINATION": str(destination),
                "EXPECTED_SIZE": str(fixture.stat().st_size),
                "EXPECTED_HASH": expected_hash,
                "RUNTIME": str(runtime),
                "WHEELHOUSE": str(wheelhouse),
                "CONSTRAINT": str(constraint),
                "CONSTRAINT_HASH": constraint_hash,
                "PIP_CACHE_DIR": str(root / "pip-cache"),
                "TMPDIR": str(root / "pip-tmp"),
            }
            result = subprocess.run(  # nosec B603 -- reviewed plan functions and isolated fakes
                ["/bin/bash", "-c", script],
                text=True,
                capture_output=True,
                check=False,
                timeout=15,
                env=environment,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(calls.read_text(encoding="utf-8"), "call\n")
            pip_arguments = pip_log.read_text(encoding="utf-8")
            self.assertIn("NO_INDEX=1", pip_arguments)
            self.assertIn(f"FIND_LINKS={wheelhouse}", pip_arguments)
            self.assertIn(f"CACHE={root / 'pip-cache'}", pip_arguments)
            self.assertIn(f"TMP={root / 'pip-tmp'}", pip_arguments)
            self.assertIn("--build-constraint", pip_arguments)
            self.assertNotIn("--no-build-isolation", pip_arguments)

            destination.write_bytes(b"corrupt\n")
            rejected = subprocess.run(  # nosec B603 -- reviewed plan functions and isolated fakes
                [
                    "/bin/bash",
                    "-c",
                    "\n".join(
                        (
                            "set -Eeuo pipefail",
                            validate,
                            download,
                            'download_exact_build_backend "https://example.invalid/exact.whl" '
                            '"$DESTINATION" "$EXPECTED_SIZE" "$EXPECTED_HASH"',
                        )
                    ),
                ],
                text=True,
                capture_output=True,
                check=False,
                timeout=15,
                env=environment,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertEqual(calls.read_text(encoding="utf-8"), "call\n")

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

    def test_shared_git_and_agent_worktree_repair_is_an_exact_two_root_gate(self) -> None:
        _prefix, program = _quoted_heredoc(
            self.ownership_gate,
            "TASK4_SHARED_GIT_OWNERSHIP_PY",
        )
        namespace: dict[str, object] = {"__name__": "shared_git_contract_test"}
        exec(compile(program, "<task4-shared-git-contract>", "exec"), namespace)  # nosec B102 -- reviewed plan source is the test subject
        records = namespace["EXPECTED_SHARED_GIT_INVENTORY"]
        digest = namespace["canonical_shared_git_inventory_digest"]
        self.assertEqual(len(records), 16)
        self.assertEqual(
            digest(records),
            namespace["EXPECTED_SHARED_GIT_INVENTORY_SHA256"],
        )
        by_path = {record["path"]: record for record in records}
        self.assertEqual(
            set(by_path),
            {
                "objects/36/5ac97aa8e7d6e5e57a8cbd28fd4d6fb726f305",
                "objects/72",
                "objects/72/32f8d030b796cfc3f3f3d58ab5c4274b7a9d15",
                "objects/88",
                "objects/88/728187e9d0b9b06f0d645f12292c2ba4433a5f",
                "objects/95",
                "objects/95/6c9fa1c5f623e5c5280a5f76e32c4266b95e90",
                "objects/a1",
                "objects/a1/1733f4032575b4ff75ccff8d8875dcdc0c8fd5",
                "objects/b2",
                "objects/b2/51ed552f7eaf74e18dd0362b9e10db50a3001a",
                "objects/c8",
                "objects/c8/4d957dee6206774a4d98689726dce38472e4b3",
                "objects/cb/0cea7105f5cc3fd1ae622e6513ea09681821b0",
                "refs/heads/agent/pr4-closed-merge-reconcile",
                "worktrees/Wirtelprimpf-generator-transactional/index",
            },
        )
        self.assertEqual(
            {
                path
                for path, record in by_path.items()
                if record.get("mutable_after_handoff")
            },
            {
                "refs/heads/agent/pr4-closed-merge-reconcile",
                "worktrees/Wirtelprimpf-generator-transactional/index",
            },
        )
        expected_files = {
            "objects/36/5ac97aa8e7d6e5e57a8cbd28fd4d6fb726f305": (
                8255432,
                122911,
                "f30bc04feea78c722b9e5ceedc538cb37f71a8c3c1afb3d6bc57cf160a5c8580",
            ),
            "objects/72/32f8d030b796cfc3f3f3d58ab5c4274b7a9d15": (
                8255441,
                54,
                "deb7ce19bde9b9581efa0e4a09a4c070749cd67112fb8d253d1a7b085d962397",
            ),
            "objects/88/728187e9d0b9b06f0d645f12292c2ba4433a5f": (
                8255439,
                110,
                "a03625cf425d2f01446ba96f47d5b78bcb076e2d96e76ade42bb81d4a9ea205c",
            ),
            "objects/95/6c9fa1c5f623e5c5280a5f76e32c4266b95e90": (
                8255434,
                42909,
                "9b392082ba24bb04ed012787f64d85bb26347716b298825ce29849c3963fbccb",
            ),
            "objects/a1/1733f4032575b4ff75ccff8d8875dcdc0c8fd5": (
                8255437,
                212,
                "e264dcdbf636ec8d7f9bb099a2bb98d51cacae5068181897d1d2d18d78671c87",
            ),
            "objects/b2/51ed552f7eaf74e18dd0362b9e10db50a3001a": (
                8255444,
                542,
                "afa9a26b1fa7f6a53a5d5566ac90732141c8ad5a322e1d06ec8fe4f9370e8857",
            ),
            "objects/c8/4d957dee6206774a4d98689726dce38472e4b3": (
                8255446,
                185,
                "d4a47fdefa6800ac688b9ebb72f069a60137a72c08e15809d4883a6c5fa8d8bc",
            ),
            "objects/cb/0cea7105f5cc3fd1ae622e6513ea09681821b0": (
                8255442,
                453,
                "a4f55d1f9586d51eeaa44c7a6f2e3161e51f23c59b9cd128545eed1c28f64c5a",
            ),
            "refs/heads/agent/pr4-closed-merge-reconcile": (
                8255448,
                41,
                "3f80500cb40140e6642e336b26e8246d538cb3d82d6351724b79dd460e9a8633",
            ),
            "worktrees/Wirtelprimpf-generator-transactional/index": (
                8255435,
                16384,
                "27711dcae0f8384c048416b540b052dfebd27ce790e67ba6717230653defd10b",
            ),
        }
        self.assertEqual(
            {
                path: (record["ino"], record["size"], record["sha256"])
                for path, record in by_path.items()
                if record["type"] == "f"
            },
            expected_files,
        )
        self.assertTrue(all(record["dev"] == 53 for record in records))
        worktree_records = namespace["EXPECTED_AGENT_WORKTREE_INVENTORY"]
        self.assertEqual(len(worktree_records), 7)
        self.assertEqual(
            digest(worktree_records),
            namespace["EXPECTED_AGENT_WORKTREE_INVENTORY_SHA256"],
        )
        self.assertEqual(
            {
                record["path"]: (
                    record["ino"],
                    record["size"],
                    record["sha256"],
                )
                for record in worktree_records
            },
            {
                "Sourcecode/__pycache__/wirtelprimpf_generator.cpython-314.pyc": (
                    8260528,
                    179978,
                    "a87459c4d56cb0f4a19c8c9887b2e063bd4439cfbd103420f3e43aa563c90ba4",
                ),
                "files/wirtelprimfgenerator@H234598/__pycache__/SettingsLogo.cpython-314.pyc": (
                    8260530,
                    79049,
                    "88da66685a5126fa15f86ef0dbd4ff8f87d81cc9acd018bc92845f566c64b6a8",
                ),
                "files/wirtelprimfgenerator@H234598/__pycache__/StoryDirectives.cpython-314.pyc": (
                    8260533,
                    17229,
                    "c2db579a19d9ab4fc6da858ab4794bb12fd50a6f4b148c94956901d73a173f72",
                ),
                "files/wirtelprimfgenerator@H234598/__pycache__/helper.cpython-314.pyc": (
                    8260529,
                    103680,
                    "4c4eb97a67f1699ead445bed3caa703522b99470f97eecdbd4b3118023619a25",
                ),
                "files/wirtelprimfgenerator@H234598/__pycache__/settings_sync.cpython-314.pyc": (
                    8260531,
                    71684,
                    "2dd89ccf346e4215a49a425a4755aeea51b5c106865e25a53b5f4122629ff41d",
                ),
                "files/wirtelprimfgenerator@H234598/__pycache__/story_directives_core.cpython-314.pyc": (
                    8260532,
                    40742,
                    "ced12684398a0f49b4f581ce393809150cc4f1e0d7f3ce3ac2d8e4a0b2e4dc68",
                ),
                "tests/__pycache__/test_rollout_plan_contract.cpython-314.pyc": (
                    8255088,
                    233891,
                    "1d2bf1c7cccad0c82e0e224f8546a47a0e2992144db0187cf3e44adcf86da377",
                ),
            },
        )
        self.assertTrue(
            all(
                record["dev"] == 53
                and record["mode"] == 0o644
                and record["nlink"] == 1
                and record["mutable_after_handoff"] is False
                for record in worktree_records
            )
        )
        self.assertIn("expected_agent_worktree_inventory_count=7", self.ownership_gate)
        self.assertIn(
            "capture_shared_git_repair_inventory",
            namespace,
        )

    def test_shared_git_repair_rejects_foreign_or_hash_drift_and_rolls_back(self) -> None:
        _prefix, program = _quoted_heredoc(
            self.ownership_gate,
            "TASK4_SHARED_GIT_OWNERSHIP_PY",
        )
        namespace: dict[str, object] = {"__name__": "shared_git_contract_test"}
        exec(compile(program, "<task4-shared-git-contract>", "exec"), namespace)  # nosec B102 -- reviewed plan source is the test subject
        capture = namespace["capture_shared_git_repair_inventory"]
        bind = namespace["bind_shared_git_inventory_fds"]
        apply_transaction = namespace["apply_shared_git_ownership_transaction"]
        close_bound = namespace["close_bound_shared_git_inventory"]
        contract_os = namespace["os"]
        source, target, third = _ownership_test_owner_pairs()

        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-shared-git-") as tmp:
            root = Path(tmp).resolve()
            objects = root / "objects"
            shard = objects / "aa"
            shard.mkdir(parents=True)
            payload = shard / "0123456789abcdef"
            payload.write_bytes(b"bound object\n")
            os.chown(root, *target)
            os.chown(objects, *target)
            expected = (
                {
                    "type": "d",
                    "path": "objects/aa",
                    "dev": shard.stat().st_dev,
                    "ino": shard.stat().st_ino,
                    "mode": shard.stat().st_mode & 0o7777,
                    "nlink": shard.stat().st_nlink,
                    "mutable_after_handoff": False,
                },
                {
                    "type": "f",
                    "path": "objects/aa/0123456789abcdef",
                    "dev": payload.stat().st_dev,
                    "ino": payload.stat().st_ino,
                    "mode": payload.stat().st_mode & 0o7777,
                    "nlink": payload.stat().st_nlink,
                    "size": payload.stat().st_size,
                    "sha256": hashlib.sha256(payload.read_bytes()).hexdigest(),
                    "mutable_after_handoff": False,
                },
            )
            records = capture(str(root), expected, *source, *target)
            bound = bind(str(root), records, *source, *target)
            original_fchown = contract_os.fchown
            calls = 0

            def fail_second_target_write(fd: int, uid: int, gid: int) -> None:
                nonlocal calls
                if (uid, gid) == target:
                    calls += 1
                    if calls == 2:
                        raise OSError("injected shared-git ownership failure")
                original_fchown(fd, uid, gid)

            contract_os.fchown = fail_second_target_write
            try:
                with self.assertRaisesRegex(RuntimeError, "rollback complete"):
                    apply_transaction(bound, *source, *target)
                self.assertEqual((shard.stat().st_uid, shard.stat().st_gid), source)
                self.assertEqual((payload.stat().st_uid, payload.stat().st_gid), source)
            finally:
                contract_os.fchown = original_fchown
                close_bound(bound)

            payload.write_bytes(b"other object\n")
            with self.assertRaisesRegex(RuntimeError, "digest drift"):
                capture(str(root), expected, *source, *target)
            payload.write_bytes(b"bound object\n")
            foreign = root / "foreign"
            foreign.write_text("foreign\n", encoding="utf-8")
            os.chown(foreign, *third)
            with self.assertRaisesRegex(RuntimeError, "unexpected foreign"):
                capture(str(root), expected, *source, *target)
            foreign.unlink()

            expected[1]["mutable_after_handoff"] = True
            records = capture(str(root), expected, *source, *target)
            bound = bind(str(root), records, *source, *target)
            try:
                apply_transaction(bound, *source, *target)
            finally:
                close_bound(bound)
            self.assertEqual((shard.stat().st_uid, shard.stat().st_gid), target)
            self.assertEqual((payload.stat().st_uid, payload.stat().st_gid), target)

            payload.unlink()
            payload.write_bytes(b"target-owned replacement after handoff\n")
            payload.chmod(expected[1]["mode"])
            os.chown(payload, *target)
            capture(str(root), expected, *source, *target)

    def test_exact_ownership_transaction_rolls_back_across_both_roots(self) -> None:
        _prefix, program = _quoted_heredoc(
            self.ownership_gate,
            "TASK4_SHARED_GIT_OWNERSHIP_PY",
        )
        namespace: dict[str, object] = {"__name__": "two_root_contract_test"}
        exec(compile(program, "<task4-two-root-contract>", "exec"), namespace)  # nosec B102 -- reviewed plan source is the test subject
        capture = namespace["capture_shared_git_repair_inventory"]
        bind = namespace["bind_shared_git_inventory_fds"]
        apply_transaction = namespace["apply_shared_git_ownership_transaction"]
        close_bound = namespace["close_bound_shared_git_inventory"]
        contract_os = namespace["os"]
        source, target, _third = _ownership_test_owner_pairs()

        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-two-root-") as tmp:
            roots = [Path(tmp) / "shared", Path(tmp) / "worktree"]
            bound: list[dict[str, object]] = []
            candidates = []
            for index, root in enumerate(roots):
                root.mkdir()
                os.chown(root, *target)
                candidate = root / f"candidate-{index}"
                candidate.write_bytes(f"root-{index}\n".encode())
                candidates.append(candidate)
                expected = (
                    {
                        "type": "f",
                        "path": candidate.name,
                        "dev": candidate.stat().st_dev,
                        "ino": candidate.stat().st_ino,
                        "mode": candidate.stat().st_mode & 0o7777,
                        "nlink": candidate.stat().st_nlink,
                        "size": candidate.stat().st_size,
                        "sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
                        "mutable_after_handoff": False,
                    },
                )
                observed = capture(str(root), expected, *source, *target)
                bound.extend(bind(str(root), observed, *source, *target))

            original_fchown = contract_os.fchown
            writes = 0

            def fail_second_root(fd: int, uid: int, gid: int) -> None:
                nonlocal writes
                if (uid, gid) == target:
                    writes += 1
                    if writes == 2:
                        raise OSError("injected second-root failure")
                original_fchown(fd, uid, gid)

            contract_os.fchown = fail_second_root
            try:
                with self.assertRaisesRegex(RuntimeError, "rollback complete"):
                    apply_transaction(bound, *source, *target)
                self.assertEqual(
                    [(path.stat().st_uid, path.stat().st_gid) for path in candidates],
                    [source, source],
                )
            finally:
                contract_os.fchown = original_fchown
                close_bound(bound)  # type: ignore[arg-type]

    def test_task4_ownership_program_uses_its_normative_isolated_interpreter(self) -> None:
        prefix, program = _quoted_heredoc(
            self.ownership_gate,
            "TASK4_OWNERSHIP_BINDING_PY",
        )
        invocation_line = next(
            line
            for line in prefix.splitlines()
            if line.startswith("/usr/bin/python3 ") and '"$runtime"' in line
        ).rstrip()
        self.assertTrue(invocation_line.endswith("\\"))
        invocation = shlex.split(invocation_line[:-1].rstrip())
        self.assertEqual(invocation[-1], "$runtime")
        interpreter = invocation[:-1]

        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-hostile-cwd-") as tmp:
            hostile_root = Path(tmp)
            sentinel = hostile_root / "hostile-hashlib-imported"
            (hostile_root / "hashlib.py").write_text(
                "with open('hostile-hashlib-imported', 'w', encoding='utf-8') as f:\n"
                "    f.write('unsafe import\\n')\n"
                "raise RuntimeError('hostile hashlib imported')\n",
                encoding="utf-8",
            )
            result = subprocess.run(  # nosec B603 -- plan-derived absolute interpreter argv
                interpreter,
                input=program,
                text=True,
                capture_output=True,
                cwd=hostile_root,
                env={
                    "HOME": str(hostile_root),
                    "PATH": "/usr/bin:/bin",
                    "LANG": "C.UTF-8",
                    "LC_ALL": "C.UTF-8",
                },
                check=False,
                timeout=10,
            )
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(
                result.stderr,
                "exact runtime/count/digest arguments required\n",
            )
            self.assertFalse(sentinel.exists())

    def test_task4_ownership_program_self_rejects_unisolated_python_before_imports(self) -> None:
        _prefix, program = _quoted_heredoc(
            self.ownership_gate,
            "TASK4_OWNERSHIP_BINDING_PY",
        )
        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-unisolated-cwd-") as tmp:
            hostile_root = Path(tmp)
            sentinel = hostile_root / "hostile-hashlib-imported"
            (hostile_root / "hashlib.py").write_text(
                "with open('hostile-hashlib-imported', 'w', encoding='utf-8') as f:\n"
                "    f.write('unsafe import\\n')\n"
                "raise RuntimeError('hostile hashlib imported')\n",
                encoding="utf-8",
            )
            result = subprocess.run(  # nosec B603 -- fixed absolute interpreter argv
                ["/usr/bin/python3", "-"],
                input=program,
                text=True,
                capture_output=True,
                cwd=hostile_root,
                env={
                    "HOME": str(hostile_root),
                    "PATH": "/usr/bin:/bin",
                    "LANG": "C.UTF-8",
                    "LC_ALL": "C.UTF-8",
                },
                check=False,
                timeout=10,
            )
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(
                result.stderr,
                "ownership gate requires isolated safe-path Python\n",
            )
            self.assertFalse(sentinel.exists())

    def test_task4_ownership_gate_binds_the_exact_current_allowlist(self) -> None:
        _prefix, program = _quoted_heredoc(
            self.ownership_gate,
            "TASK4_OWNERSHIP_BINDING_PY",
        )
        namespace: dict[str, object] = {"__name__": "ownership_contract_test"}
        exec(compile(program, "<task4-ownership-contract>", "exec"), namespace)  # nosec B102 -- reviewed plan source is the test subject
        expected = namespace["EXPECTED_RUNTIME_INVENTORY"]
        self.assertIsInstance(expected, tuple)
        assert isinstance(expected, tuple)
        self.assertEqual(len(expected), 84)
        digest = namespace["canonical_inventory_digest"](expected)
        self.assertEqual(digest, namespace["EXPECTED_RUNTIME_INVENTORY_SHA256"])
        self.assertNotIn("450", self.ownership_gate)
        self.assertIn("expected_runtime_inventory_count=84", self.ownership_gate)
        self.assertNotIn("--rebuild", program)
        self.assertNotIn("audit", program.lower())
        for required in (
            "O_NOFOLLOW",
            "st_dev",
            "st_ino",
            "st_nlink",
            "os.fchown",
            "rollback",
            "S_ISREG",
            "S_ISDIR",
            "commonpath",
        ):
            self.assertIn(required, program)

    def test_task4_ownership_inventory_rejects_path_type_link_and_object_drift(self) -> None:
        _prefix, program = _quoted_heredoc(
            self.ownership_gate,
            "TASK4_OWNERSHIP_BINDING_PY",
        )
        namespace: dict[str, object] = {"__name__": "ownership_contract_test"}
        exec(compile(program, "<task4-ownership-contract>", "exec"), namespace)  # nosec B102 -- reviewed plan source is the test subject
        capture = namespace["capture_runtime_inventory"]
        validate = namespace["validate_expected_inventory"]
        bind = namespace["bind_runtime_inventory_fds"]
        assert_fd_binding = namespace["_assert_fd_binding"]
        close_bound = namespace["close_bound_inventory"]
        uid = os.geteuid()
        gid = os.getegid()
        foreign_target_uid = uid + 100_000
        foreign_target_gid = gid + 100_000

        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-ownership-") as tmp:
            root = Path(tmp).resolve()
            (root / "nested").mkdir()
            (root / "nested" / "one").write_text("one\n", encoding="utf-8")
            (root / "two").write_text("two\n", encoding="utf-8")
            expected = capture(
                str(root),
                foreign_target_uid,
                foreign_target_gid,
            )
            validate(str(root), expected, uid, gid)
            bound = bind(str(root), expected, uid, gid)
            try:
                self.assertEqual(len(bound), len(expected))
                link_drift_record = dict(bound[0]["record"])
                link_drift_record["nlink"] = int(link_drift_record["nlink"]) + 1
                with self.assertRaises(RuntimeError):
                    assert_fd_binding(
                        int(bound[0]["fd"]), link_drift_record, uid, gid
                    )
            finally:
                close_bound(bound)

            (root / "unexpected").write_text("drift\n", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                validate(str(root), expected, uid, gid)
            (root / "unexpected").unlink()

            (root / "link").symlink_to(root / "two")
            with self.assertRaises(RuntimeError):
                capture(str(root), foreign_target_uid, foreign_target_gid)
            (root / "link").unlink()

            os.link(root / "two", root / "hardlink")
            with self.assertRaises(RuntimeError):
                capture(str(root), foreign_target_uid, foreign_target_gid)
            (root / "hardlink").unlink()

            fifo = root / "special"
            os.mkfifo(fifo)
            with self.assertRaises(RuntimeError):
                capture(str(root), foreign_target_uid, foreign_target_gid)
            fifo.unlink()

            escaped = list(expected)
            escaped[0] = dict(escaped[0], path="../escape")
            with self.assertRaises(RuntimeError):
                validate(str(root), tuple(escaped), uid, gid)

            object_drift = list(expected)
            object_drift[0] = dict(
                object_drift[0],
                ino=int(object_drift[0]["ino"]) + 1,
            )
            with self.assertRaises(RuntimeError):
                bind(str(root), tuple(object_drift), uid, gid)

            link_count_drift = list(expected)
            link_count_drift[0] = dict(
                link_count_drift[0],
                nlink=int(link_count_drift[0]["nlink"]) + 1,
            )
            with self.assertRaises(RuntimeError):
                bind(str(root), tuple(link_count_drift), uid, gid)

            submount_drift = list(expected)
            submount_drift[0] = dict(
                submount_drift[0],
                dev=int(submount_drift[0]["dev"]) + 1,
            )
            with self.assertRaises(RuntimeError):
                bind(str(root), tuple(submount_drift), uid, gid)

    def test_task4_ownership_retry_completes_a_mixed_static_allowlist_targetward(self) -> None:
        _prefix, program = _quoted_heredoc(
            self.ownership_gate,
            "TASK4_OWNERSHIP_BINDING_PY",
        )
        namespace: dict[str, object] = {"__name__": "ownership_contract_test"}
        exec(compile(program, "<task4-ownership-contract>", "exec"), namespace)  # nosec B102 -- reviewed plan source is the test subject
        self.assertIn("capture_allowlisted_runtime_inventory", namespace)
        capture_allowlisted = namespace["capture_allowlisted_runtime_inventory"]
        bind = namespace["bind_runtime_inventory_fds"]
        apply_transaction = namespace["apply_runtime_ownership_transaction"]
        close_bound = namespace["close_bound_inventory"]
        source, target, _third = _ownership_test_owner_pairs()

        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-mixed-retry-") as tmp:
            root = Path(tmp).resolve()
            first = root / "one"
            second = root / "two"
            first.write_text("one\n", encoding="utf-8")
            second.write_text("two\n", encoding="utf-8")
            expected_static = (
                {"type": "f", "path": "one"},
                {"type": "f", "path": "two"},
            )
            os.chown(first, *target)
            records = capture_allowlisted(
                str(root),
                expected_static,
                *source,
                *target,
            )
            self.assertEqual(
                {(int(item["uid"]), int(item["gid"])) for item in records},
                {source, target},
            )
            bound = bind(str(root), records, *source)
            try:
                apply_transaction(bound, *source, *target)
                self.assertEqual((first.stat().st_uid, first.stat().st_gid), target)
                self.assertEqual((second.stat().st_uid, second.stat().st_gid), target)
            finally:
                close_bound(bound)

    def test_task4_signal_after_real_fchown_rolls_back_each_entry_owner_and_is_nonzero(self) -> None:
        _prefix, program = _quoted_heredoc(
            self.ownership_gate,
            "TASK4_OWNERSHIP_BINDING_PY",
        )
        namespace: dict[str, object] = {"__name__": "ownership_contract_test"}
        exec(compile(program, "<task4-ownership-contract>", "exec"), namespace)  # nosec B102 -- reviewed plan source is the test subject
        for symbol in (
            "capture_allowlisted_runtime_inventory",
            "OwnershipInterrupted",
        ):
            self.assertIn(symbol, namespace)
        capture_allowlisted = namespace["capture_allowlisted_runtime_inventory"]
        bind = namespace["bind_runtime_inventory_fds"]
        apply_transaction = namespace["apply_runtime_ownership_transaction"]
        close_bound = namespace["close_bound_inventory"]
        interrupted_type = namespace["OwnershipInterrupted"]
        contract_os = namespace["os"]
        source, target, _third = _ownership_test_owner_pairs()

        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-signal-rollback-") as tmp:
            root = Path(tmp).resolve()
            already_target = root / "already-target"
            mutation_target = root / "mutation-target"
            already_target.write_text("target\n", encoding="utf-8")
            mutation_target.write_text("source\n", encoding="utf-8")
            expected_static = (
                {"type": "f", "path": "already-target"},
                {"type": "f", "path": "mutation-target"},
            )
            os.chown(already_target, *target)
            records = capture_allowlisted(
                str(root),
                expected_static,
                *source,
                *target,
            )
            bound = bind(str(root), records, *source)
            original_fchown = contract_os.fchown
            injected = False
            prior_handlers = {
                signum: signal.getsignal(signum)
                for signum in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM)
            }

            def signal_after_real_fchown(
                fd: int,
                next_uid: int,
                next_gid: int,
            ) -> None:
                nonlocal injected
                original_fchown(fd, next_uid, next_gid)
                if not injected and (next_uid, next_gid) == target:
                    injected = True
                    signal.raise_signal(signal.SIGTERM)

            contract_os.fchown = signal_after_real_fchown
            try:
                with self.assertRaises(interrupted_type) as caught:
                    apply_transaction(bound, *source, *target)
                self.assertTrue(injected)
                self.assertEqual(caught.exception.signum, signal.SIGTERM)
                self.assertEqual(caught.exception.exit_code, 128 + signal.SIGTERM)
                self.assertEqual(
                    (already_target.stat().st_uid, already_target.stat().st_gid),
                    target,
                )
                self.assertEqual(
                    (mutation_target.stat().st_uid, mutation_target.stat().st_gid),
                    source,
                )
                self.assertEqual(
                    {
                        signum: signal.getsignal(signum)
                        for signum in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM)
                    },
                    prior_handlers,
                )
            finally:
                contract_os.fchown = original_fchown
                close_bound(bound)

    def test_task4_commit_boundary_never_swallows_a_late_catchable_signal(self) -> None:
        _prefix, program = _quoted_heredoc(
            self.ownership_gate,
            "TASK4_OWNERSHIP_BINDING_PY",
        )
        namespace: dict[str, object] = {"__name__": "ownership_contract_test"}
        exec(compile(program, "<task4-ownership-contract>", "exec"), namespace)  # nosec B102 -- reviewed plan source is the test subject
        capture_allowlisted = namespace["capture_allowlisted_runtime_inventory"]
        bind = namespace["bind_runtime_inventory_fds"]
        apply_transaction = namespace["apply_runtime_ownership_transaction"]
        close_bound = namespace["close_bound_inventory"]
        contract_signal = namespace["signal"]
        source, target, _third = _ownership_test_owner_pairs()

        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-late-signal-") as tmp:
            root = Path(tmp).resolve()
            candidate = root / "candidate"
            candidate.write_text("candidate\n", encoding="utf-8")
            records = capture_allowlisted(
                str(root),
                ({"type": "f", "path": "candidate"},),
                *source,
                *target,
            )
            bound = bind(str(root), records, *source)
            original_sigpending = contract_signal.sigpending
            original_handler = signal.getsignal(signal.SIGTERM)
            observed: list[int] = []
            injected = False

            def prior_handler(signum: int, _frame: object) -> None:
                observed.append(signum)

            def queue_signal_after_pending_snapshot() -> set[signal.Signals]:
                nonlocal injected
                snapshot = original_sigpending()
                if not injected:
                    injected = True
                    signal.raise_signal(signal.SIGTERM)
                return snapshot

            signal.signal(signal.SIGTERM, prior_handler)
            contract_signal.sigpending = queue_signal_after_pending_snapshot
            try:
                apply_transaction(bound, *source, *target)
                self.assertTrue(injected)
                self.assertEqual(observed, [signal.SIGTERM])
                self.assertEqual(
                    (candidate.stat().st_uid, candidate.stat().st_gid),
                    target,
                )
                self.assertIs(signal.getsignal(signal.SIGTERM), prior_handler)
            finally:
                contract_signal.sigpending = original_sigpending
                signal.signal(signal.SIGTERM, original_handler)
                if (candidate.stat().st_uid, candidate.stat().st_gid) != source:
                    os.chown(candidate, *source)
                close_bound(bound)

    def test_task4_rollback_rejects_a_third_owner_without_overwriting_it(self) -> None:
        _prefix, program = _quoted_heredoc(
            self.ownership_gate,
            "TASK4_OWNERSHIP_BINDING_PY",
        )
        namespace: dict[str, object] = {"__name__": "ownership_contract_test"}
        exec(compile(program, "<task4-ownership-contract>", "exec"), namespace)  # nosec B102 -- reviewed plan source is the test subject
        self.assertIn("capture_allowlisted_runtime_inventory", namespace)
        capture_allowlisted = namespace["capture_allowlisted_runtime_inventory"]
        bind = namespace["bind_runtime_inventory_fds"]
        apply_transaction = namespace["apply_runtime_ownership_transaction"]
        close_bound = namespace["close_bound_inventory"]
        contract_os = namespace["os"]
        source, target, third = _ownership_test_owner_pairs()

        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-third-owner-") as tmp:
            root = Path(tmp).resolve()
            candidate = root / "candidate"
            candidate.write_text("candidate\n", encoding="utf-8")
            records = capture_allowlisted(
                str(root),
                ({"type": "f", "path": "candidate"},),
                *source,
                *target,
            )
            bound = bind(str(root), records, *source)
            original_fchown = contract_os.fchown
            injected = False

            def inject_third_owner(
                fd: int,
                next_uid: int,
                next_gid: int,
            ) -> None:
                nonlocal injected
                original_fchown(fd, next_uid, next_gid)
                if not injected and (next_uid, next_gid) == target:
                    injected = True
                    original_fchown(fd, *third)
                    raise OSError("injected third-owner drift")

            contract_os.fchown = inject_third_owner
            try:
                with self.assertRaisesRegex(RuntimeError, "rollback INCOMPLETE"):
                    apply_transaction(bound, *source, *target)
                self.assertTrue(injected)
                self.assertEqual((candidate.stat().st_uid, candidate.stat().st_gid), third)
            finally:
                contract_os.fchown = original_fchown
                original_fchown(int(bound[0]["fd"]), *source)
                close_bound(bound)

    def test_task4_ownership_transaction_rolls_back_completed_fchowns(self) -> None:
        _prefix, program = _quoted_heredoc(
            self.ownership_gate,
            "TASK4_OWNERSHIP_BINDING_PY",
        )
        namespace: dict[str, object] = {"__name__": "ownership_contract_test"}
        exec(compile(program, "<task4-ownership-contract>", "exec"), namespace)  # nosec B102 -- reviewed plan source is the test subject
        capture = namespace["capture_runtime_inventory"]
        bind = namespace["bind_runtime_inventory_fds"]
        close_bound = namespace["close_bound_inventory"]
        apply_transaction = namespace["apply_runtime_ownership_transaction"]
        contract_os = namespace["os"]
        source, target, _third = _ownership_test_owner_pairs()

        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-ownership-rollback-") as tmp:
            root = Path(tmp).resolve()
            first = root / "one"
            second = root / "two"
            first.write_text("one\n", encoding="utf-8")
            second.write_text("two\n", encoding="utf-8")
            expected = capture(str(root), *target)
            bound = bind(str(root), expected, *source)
            original_fchown = contract_os.fchown
            calls: list[tuple[int, int, int]] = []

            def injected_fchown(fd: int, next_uid: int, next_gid: int) -> None:
                calls.append((fd, next_uid, next_gid))
                if len(calls) == 2 and (next_uid, next_gid) == target:
                    raise OSError("injected second-fchown failure")
                original_fchown(fd, next_uid, next_gid)

            contract_os.fchown = injected_fchown
            try:
                with self.assertRaisesRegex(RuntimeError, "rollback complete"):
                    apply_transaction(bound, *source, *target)
                self.assertEqual(len(calls), 3)
                self.assertEqual(calls[0][0], calls[2][0])
                self.assertEqual(
                    (first.stat().st_uid, first.stat().st_gid),
                    source,
                )
                self.assertEqual(
                    (second.stat().st_uid, second.stat().st_gid),
                    source,
                )
            finally:
                contract_os.fchown = original_fchown
                close_bound(bound)

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
        self.assertIn("backend-single-fetch", self.harness)
        self.assertIn("backend-offline-forward", self.harness)
        self.assertIn("backend-offline-rollback", self.harness)
        self.assertIn("backend-corruption-rejected", self.harness)

    def test_step10_models_search_precedence_and_the_interrupted_retry(self) -> None:
        for state_file in (
            "service-legacy-mask",
            "service-control-mask",
            "timer-legacy-mask",
            "timer-control-mask",
        ):
            self.assertIn(state_file, self.harness)
        self.assertIn("runtime_load_state_harness", self.harness)
        self.assertIn("lower-priority-mask-is-ineffective", self.harness)
        self.assertIn("interrupted-four-link-adoption", self.harness)
        self.assertIn("timer-recovery-normalized", self.harness)
        self.assertIn("historical-HNkEdc-evidence", self.harness)
        self.assertIn("current-f1iePQ-inode-hash-chain", self.harness)

        quiesce = _shell_function(self.harness, "quiesce_generator_harness")
        lower = quiesce.index("service-legacy-mask")
        ineffective = quiesce.index("lower-priority-mask-is-ineffective")
        control = quiesce.index("service-control-mask", ineffective)
        masked = quiesce.index("runtime_load_state_harness service", control)
        self.assertLess(lower, ineffective)
        self.assertLess(ineffective, control)
        self.assertLess(control, masked)

        recovery = _marked_block(
            self.harness,
            "TASK4_INTERRUPTED_FOUR_LINK_HARNESS",
        )
        service_before = recovery.index("runtime_load_state_harness service")
        timer_remove = recovery.index('rm -f -- "$sandbox/timer-legacy-mask"')
        service_after = recovery.rindex("runtime_load_state_harness service")
        self.assertLess(service_before, timer_remove)
        self.assertGreater(service_after, timer_remove)

    def test_step10_runtime_cas_moves_main_from_the_old_commit_to_the_target(self) -> None:
        detach_old = 'git -C "$runtime_harness" switch --detach -q "$runtime_sha_before"'
        update_main = (
            'git -C "$runtime_harness" update-ref refs/heads/main \\\n'
            '  "$target_sha" "$runtime_sha_before"'
        )
        self.assertIn(detach_old, self.harness)
        self.assertIn(update_main, self.harness)
        self.assertLess(
            self.harness.index(detach_old),
            self.harness.index("printf 'target-tree\\n'"),
        )

    def test_step9_preflights_the_canonical_private_backup_root_without_mutating_it(self) -> None:
        preflight = _marked_block(self.deployment, "TASK4_BACKUP_ROOT_PREFLIGHT")
        function = _shell_function(f"{preflight}\n", "assert_private_backup_root")
        call = (
            'assert_private_backup_root "$backup_root" '
            '"/home/teladi/.local/state/wirtelprimpf/deploy-backups" '
            '1000 1000 53 7999241'
        )
        self.assertIn(call, self.deployment)
        self.assertNotIn('install -d -m0700 "$backup_root"', self.deployment)
        self.assertLess(self.deployment.index(call), self.deployment.index("deploy_backup="))
        self.assertLess(
            self.deployment.index(call),
            self.deployment.index("systemctl --user stop wirtelprimpf.timer"),
        )

        script = f"""
set -Eeuo pipefail
{function}
assert_private_backup_root "$1" "$2" "$3" "$4" "$5" "$6"
"""
        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-backup-root-") as tmp:
            root = Path(tmp) / "deploy-backups"
            root.mkdir(mode=0o700)
            uid = os.geteuid()
            gid = os.getegid()

            valid = subprocess.run(  # nosec B603 -- fixed Bash argv and local fixture
                [
                    "/bin/bash",
                    "-c",
                    script,
                    "backup-root-test",
                    str(root),
                    str(root),
                    str(uid),
                    str(gid),
                    str(root.stat().st_dev),
                    str(root.stat().st_ino),
                ],
                text=True,
                capture_output=True,
                check=False,
                timeout=5,
                env={"HOME": "/nonexistent", "PATH": "/usr/bin:/bin"},
            )
            self.assertEqual(valid.returncode, 0, valid.stderr)

            root.chmod(0o755)
            wrong_mode = subprocess.run(  # nosec B603 -- fixed Bash argv and local fixture
                [
                    "/bin/bash",
                    "-c",
                    script,
                    "backup-root-test",
                    str(root),
                    str(root),
                    str(uid),
                    str(gid),
                    str(root.stat().st_dev),
                    str(root.stat().st_ino),
                ],
                text=True,
                capture_output=True,
                check=False,
                timeout=5,
                env={"HOME": "/nonexistent", "PATH": "/usr/bin:/bin"},
            )
            self.assertNotEqual(wrong_mode.returncode, 0)
            self.assertEqual(root.stat().st_mode & 0o777, 0o755)

            root.chmod(0o700)
            alias = Path(tmp) / "backup-alias"
            alias.symlink_to(root, target_is_directory=True)
            symlink = subprocess.run(  # nosec B603 -- fixed Bash argv and local fixture
                [
                    "/bin/bash",
                    "-c",
                    script,
                    "backup-root-test",
                    str(alias),
                    str(alias),
                    str(uid),
                    str(gid),
                    str(root.stat().st_dev),
                    str(root.stat().st_ino),
                ],
                text=True,
                capture_output=True,
                check=False,
                timeout=5,
                env={"HOME": "/nonexistent", "PATH": "/usr/bin:/bin"},
            )
            self.assertNotEqual(symlink.returncode, 0)
            self.assertTrue(alias.is_symlink())

            wrong_inode = subprocess.run(  # nosec B603 -- fixed Bash argv and local fixture
                [
                    "/bin/bash",
                    "-c",
                    script,
                    "backup-root-test",
                    str(root),
                    str(root),
                    str(uid),
                    str(gid),
                    str(root.stat().st_dev),
                    str(root.stat().st_ino + 1),
                ],
                text=True,
                capture_output=True,
                check=False,
                timeout=5,
                env={"HOME": "/nonexistent", "PATH": "/usr/bin:/bin"},
            )
            self.assertNotEqual(wrong_inode.returncode, 0)

    def test_runtime_barrier_uses_high_priority_control_and_bound_exact_removal(self) -> None:
        _prefix, program = _quoted_heredoc(
            self.deployment,
            "TASK4_RUNTIME_BARRIER_PY",
        )
        namespace: dict[str, object] = {"__name__": "runtime_barrier_contract_test"}
        exec(compile(program, "<task4-runtime-barrier-contract>", "exec"), namespace)  # nosec B102 -- reviewed plan source is the test subject
        ensure = namespace["ensure_runtime_barrier"]
        remove = namespace["remove_runtime_barrier"]
        capture = namespace["capture_runtime_barrier"]
        uid = os.geteuid()
        gid = os.getegid()

        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-runtime-barrier-") as tmp:
            root = Path(tmp)
            control = root / "systemd" / "user.control"
            legacy = root / "systemd" / "user"
            control.mkdir(parents=True, mode=0o700)
            legacy.mkdir(mode=0o755)
            unit = "wirtelprimpf.service"
            legacy_link = legacy / unit
            legacy_link.symlink_to("/dev/null")
            unrelated = control / "unrelated.service"
            unrelated.symlink_to("/dev/null")

            binding = ensure(str(control), str(legacy), unit, uid, gid)
            control_link = control / unit
            self.assertTrue(control_link.is_symlink())
            self.assertEqual(os.readlink(control_link), "/dev/null")
            self.assertEqual(
                int(binding["control"]["ino"]),
                control_link.lstat().st_ino,
            )
            self.assertEqual(
                int(binding["legacy"]["ino"]),
                legacy_link.lstat().st_ino,
            )

            adopted = ensure(str(control), str(legacy), unit, uid, gid)
            self.assertEqual(adopted, binding)

            control_link.unlink()
            control_link.symlink_to("/dev/null")
            with self.assertRaises(RuntimeError):
                remove(str(control), str(legacy), unit, binding, uid, gid)
            self.assertTrue(control_link.is_symlink())
            self.assertTrue(legacy_link.is_symlink())
            self.assertTrue(unrelated.is_symlink())

            rebound = {
                "control": capture(str(control), unit, uid, gid),
                "legacy": capture(str(legacy), unit, uid, gid),
            }
            remove(str(control), str(legacy), unit, rebound, uid, gid)
            self.assertFalse(control_link.exists())
            self.assertFalse(control_link.is_symlink())
            self.assertFalse(legacy_link.exists())
            self.assertFalse(legacy_link.is_symlink())
            self.assertTrue(unrelated.is_symlink())

            fresh = root / "fresh" / "systemd"
            fresh.mkdir(parents=True, mode=0o755)
            fresh_legacy = fresh / "user"
            fresh_legacy.mkdir(mode=0o755)
            (fresh_legacy / unit).symlink_to("/dev/null")
            fresh_control = fresh / "user.control"
            self.assertFalse(fresh_control.exists())
            fresh_binding = ensure(
                str(fresh_control), str(fresh_legacy), unit, uid, gid
            )
            self.assertTrue(fresh_control.is_dir())
            self.assertFalse(fresh_control.is_symlink())
            self.assertEqual(fresh_control.stat().st_mode & 0o777, 0o700)
            self.assertEqual(
                (fresh_control.stat().st_uid, fresh_control.stat().st_gid),
                (uid, gid),
            )
            remove(
                str(fresh_control),
                str(fresh_legacy),
                unit,
                fresh_binding,
                uid,
                gid,
            )

            hostile = root / "hostile" / "systemd"
            hostile.mkdir(parents=True, mode=0o755)
            hostile_legacy = hostile / "user"
            hostile_legacy.mkdir(mode=0o755)
            (hostile_legacy / unit).symlink_to("/dev/null")
            redirect = root / "redirect"
            redirect.mkdir(mode=0o700)
            (hostile / "user.control").symlink_to(
                redirect, target_is_directory=True
            )
            with self.assertRaises((OSError, RuntimeError)):
                ensure(
                    str(hostile / "user.control"),
                    str(hostile_legacy),
                    unit,
                    uid,
                    gid,
                )
            self.assertEqual(list(redirect.iterdir()), [])

    def test_step9_adopts_only_the_bound_interrupted_four_link_prestate(self) -> None:
        _prefix, program = _quoted_heredoc(
            self.deployment,
            "TASK4_RUNTIME_BARRIER_PY",
        )
        namespace: dict[str, object] = {"__name__": "runtime_barrier_contract_test"}
        exec(compile(program, "<task4-runtime-barrier-contract>", "exec"), namespace)  # nosec B102 -- reviewed plan source is the test subject
        validate_prestate = namespace["validate_interrupted_prestate"]
        validate_chain = namespace["validate_interrupted_attempt_chain"]
        interrupted_chain = namespace["INTERRUPTED_ATTEMPT_CHAIN"]
        barrier_history = namespace["INTERRUPTED_BARRIER_HISTORY"]
        current_attempt = namespace["CURRENT_INTERRUPTED_ATTEMPT"]

        self.assertEqual(current_attempt, "f1iePQ")
        self.assertEqual(
            [(record["name"], record["path"], record["current"]) for record in interrupted_chain],
            [
                (
                    "HNkEdc",
                    "/home/teladi/.local/state/wirtelprimpf/deploy-backups/20260801-admin-live.HNkEdc",
                    False,
                ),
                (
                    "f1iePQ",
                    "/home/teladi/.local/state/wirtelprimpf/deploy-backups/20260801-admin-live.f1iePQ",
                    True,
                ),
            ],
        )
        historical_prestate, current_prestate = interrupted_chain
        self.assertEqual(
            (historical_prestate["dev"], historical_prestate["ino"]),
            (53, 8250927),
        )
        self.assertEqual(
            (current_prestate["dev"], current_prestate["ino"]),
            (53, 8256518),
        )
        self.assertEqual(
            {
                name: (record["ino"], record["sha256"])
                for name, record in current_prestate["files"].items()
            },
            {
                "runtime-sha-before": (8256519, "c884bec764a03e4c876acf6beaee32b17ad55b863c11b22b5d80724f51392873"),
                "runtime-branch-before": (8256520, "6403203dd5a0867eb14d104ee8a73730bd72dd9ad92e78d996a6dba0a5dcfc01"),
                "target-sha": (8256521, "784140f1bd8201950fe8f91ba37775371cc87530643efe6fb3d814203ca81aa2"),
                "timer-enabled-before": (8256522, "e056a35db086947e2f5969d747f0a7517bff00c7ffff1f9e7b47b72bfac9d948"),
                "timer-active-before": (8256523, "45df5ad5e0ecfa54d3226343e0e6857337494ba6e32f189d1174070665d8c659"),
                "admin-active-before": (8256524, "45df5ad5e0ecfa54d3226343e0e6857337494ba6e32f189d1174070665d8c659"),
                "service-unit-state-before": (
                    8256525,
                    "652cabf0de6cd70f66f72b17d6409203b84909be9864261feb614943f2e6cc62",
                ),
                "service-load-state-before": (
                    8256526,
                    "25dbd4fa5b9f0710b9f27009c1e38969b8cbb2806502388beae5063d460a85f5",
                ),
            },
        )
        self.assertEqual(
            {
                name: (record["ino"], record["sha256"])
                for name, record in current_prestate["evidence_files"].items()
            },
            {
                "config-manifest.tsv": (8256539, "76aaf7d6461ae8460b62c6abdec2976fe0c3cc7920c7159e7ef705fdee2cdbd3"),
                "install-manifest.tsv": (8256540, "806f2a93095233058b2e787abde9f1a9196c5292db412f66fbc1f44c5336c486"),
                "directory-modes-before.tsv": (
                    8256541,
                    "9eb4d6d28e9058ff0297965dee2f2d1eaa5649fb849549a1bbd2deb71c416c89",
                ),
            },
        )
        self.assertEqual(
            current_prestate["payload_directory"],
            {
                "path": "files",
                "dev": 53,
                "ino": 8256538,
                "mode": 0o700,
                "entries": {
                    "001": {"type": "f", "dev": 53, "ino": 8256542, "mode": 0o600, "nlink": 1, "size": 2080},
                    "002": {"type": "f", "dev": 53, "ino": 8256543, "mode": 0o600, "nlink": 1, "size": 75},
                    "003": {"type": "f", "dev": 53, "ino": 8256544, "mode": 0o644, "nlink": 1, "size": 128},
                    "005": {"type": "d", "dev": 53, "ino": 8256545, "mode": 0o755, "nlink": 1, "size": 326},
                    "007": {"type": "f", "dev": 53, "ino": 8256571, "mode": 0o755, "nlink": 1, "size": 24639},
                    "008": {"type": "f", "dev": 53, "ino": 8256572, "mode": 0o644, "nlink": 1, "size": 1047},
                    "009": {"type": "f", "dev": 53, "ino": 8256573, "mode": 0o644, "nlink": 1, "size": 187},
                    "010": {"type": "f", "dev": 53, "ino": 8256574, "mode": 0o644, "nlink": 1, "size": 968},
                },
            },
        )
        current_barriers = barrier_history[current_attempt]
        self.assertEqual(
            {
                (side, unit): (record["dev"], record["ino"])
                for side, units in current_barriers["links"].items()
                for unit, record in units.items()
            },
            {
                ("control", "wirtelprimpf.service"): (84, 48465),
                ("control", "wirtelprimpf.timer"): (84, 49929),
                ("legacy", "wirtelprimpf.service"): (84, 47828),
                ("legacy", "wirtelprimpf.timer"): (84, 49854),
            },
        )

        values = {
            "runtime-sha-before": "59ba29418e3c299973b20b590f86a6b2d18c2f06",
            "runtime-branch-before": "main",
            "target-sha": "274b25c9e1f9ea97d3b060997ed5c425d2b30e9f",
            "timer-enabled-before": "enabled",
            "timer-active-before": "active",
            "admin-active-before": "active",
            "service-unit-state-before": "static",
            "service-load-state-before": "loaded",
        }
        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-interrupted-prestate-") as tmp:
            chain_fixture = []
            for index, attempt_name in enumerate(("old", "current")):
                root = Path(tmp) / attempt_name
                root.mkdir(mode=0o700)
                for name, value in values.items():
                    path = root / name
                    path.write_text(value + "\n", encoding="utf-8")
                    path.chmod(0o600)
                chain_fixture.append(
                    {
                        "name": attempt_name,
                        "current": index == 1,
                        "path": str(root),
                        "dev": root.stat().st_dev,
                        "ino": root.stat().st_ino,
                        "files": {
                            name: {
                                "dev": (root / name).stat().st_dev,
                                "ino": (root / name).stat().st_ino,
                                "ctime_ns": (root / name).stat().st_ctime_ns,
                                "sha256": hashlib.sha256((value + "\n").encode()).hexdigest(),
                            }
                            for name, value in values.items()
                        },
                    }
                )
            expected = chain_fixture[-1]
            validated = validate_prestate(
                expected["path"], expected, os.geteuid(), os.getegid()
            )
            self.assertEqual(validated, values)
            self.assertEqual(
                validate_chain(tuple(chain_fixture), os.geteuid(), os.getegid()),
                values,
            )

            ctime_drift = copy.deepcopy(expected)
            ctime_drift["files"]["admin-active-before"]["ctime_ns"] += 1
            with self.assertRaisesRegex(RuntimeError, "identity drift"):
                validate_prestate(
                    ctime_drift["path"], ctime_drift, os.geteuid(), os.getegid()
                )

            ambiguous = copy.deepcopy(chain_fixture)
            ambiguous[0]["current"] = True
            with self.assertRaisesRegex(RuntimeError, "unique current"):
                validate_chain(tuple(ambiguous), os.geteuid(), os.getegid())

            replaced = Path(expected["path"]) / "admin-active-before"
            replaced.unlink()
            replaced.write_text("active\n", encoding="utf-8")
            replaced.chmod(0o600)
            with self.assertRaises(RuntimeError):
                validate_prestate(expected["path"], expected, os.geteuid(), os.getegid())

        recovery = _marked_block(
            self.deployment,
            "TASK4_INTERRUPTED_MASK_RECOVERY",
        )
        self.assertIn("runtime_barrier_python recover-interrupted", recovery)
        self.assertIn("runtime_barrier_python adopt-interrupted", recovery)
        self.assertIn("interrupted_runtime_barriers=1", recovery)
        self.assertIn("runtime_service_barrier_binding", recovery)
        self.assertIn("runtime_timer_barrier_binding", recovery)
        self.assertNotIn("rm ", recovery)
        self.assertNotIn("chmod", recovery)
        self.assertNotIn("systemctl --user unmask", recovery)
        target_gate = (
            'test "$(jq -er \'."target-sha"\' '
            '<<<"$interrupted_prestate_json")" = "$target_sha"'
        )
        self.assertIn(target_gate, recovery)

        normalize = _shell_function(
            self.deployment,
            "normalize_interrupted_timer_barrier",
        )
        service_proofs = [
            match.start()
            for match in re.finditer(
                "systemctl --user show wirtelprimpf.service -p LoadState --value",
                normalize,
            )
        ]
        timer_remove = normalize.index("unmask_timer_runtime_stopped")
        self.assertEqual(len(service_proofs), 2)
        self.assertLess(service_proofs[0], timer_remove)
        self.assertGreater(service_proofs[1], timer_remove)

    def test_partial_unmask_keeps_control_effective_and_rebinds_only_legacy(self) -> None:
        _prefix, program = _quoted_heredoc(
            self.deployment,
            "TASK4_RUNTIME_BARRIER_PY",
        )
        namespace: dict[str, object] = {"__name__": "runtime_barrier_contract_test"}
        exec(compile(program, "<task4-runtime-barrier-contract>", "exec"), namespace)  # nosec B102 -- reviewed plan source is the test subject
        ensure = namespace["ensure_runtime_barrier"]
        remove = namespace["remove_runtime_barrier"]
        reconcile = namespace["reconcile_runtime_barrier_binding"]
        contract_os = namespace["os"]
        uid = os.geteuid()
        gid = os.getegid()

        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-partial-unmask-") as tmp:
            systemd = Path(tmp) / "systemd"
            control = systemd / "user.control"
            legacy = systemd / "user"
            control.mkdir(parents=True, mode=0o700)
            legacy.mkdir(mode=0o755)
            unit = "wirtelprimpf.service"
            (legacy / unit).symlink_to("/dev/null")
            binding = ensure(str(control), str(legacy), unit, uid, gid)
            original_unlink = contract_os.unlink
            calls = 0

            def injected_unlink(path: str, *, dir_fd: int | None = None) -> None:
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("injected control unlink failure")
                original_unlink(path, dir_fd=dir_fd)

            contract_os.unlink = injected_unlink
            try:
                with self.assertRaisesRegex(OSError, "injected control"):
                    remove(str(control), str(legacy), unit, binding, uid, gid)
            finally:
                contract_os.unlink = original_unlink

            self.assertTrue((control / unit).is_symlink())
            self.assertFalse((legacy / unit).exists())
            self.assertEqual(os.readlink(control / unit), "/dev/null")
            repaired = ensure(str(control), str(legacy), unit, uid, gid)
            self.assertEqual(
                reconcile(binding, repaired),
                repaired,
            )

            ctime_drift = copy.deepcopy(repaired)
            ctime_drift["control"]["ctime_ns"] = (
                ctime_drift["control"].get("ctime_ns", 0) + 1
            )
            with self.assertRaisesRegex(
                RuntimeError, "effective runtime barrier identity drift"
            ):
                reconcile(repaired, ctime_drift)

            (control / unit).unlink()
            (control / unit).symlink_to("/dev/null")
            replaced_control = ensure(str(control), str(legacy), unit, uid, gid)
            with self.assertRaises(RuntimeError):
                reconcile(repaired, replaced_control)

    def test_normative_mask_and_unmask_bind_the_effective_and_legacy_pair(self) -> None:
        service_mask = _shell_function(self.deployment, "mask_generator_runtime")
        timer_mask = _shell_function(self.deployment, "mask_timer_runtime_stopped")
        service_unmask = _shell_function(self.deployment, "unmask_generator_runtime")
        timer_unmask = _shell_function(self.deployment, "unmask_timer_runtime_stopped")

        service_lower = service_mask.index(
            "systemctl --user mask --runtime wirtelprimpf.service"
        )
        service_effective = service_mask.index("runtime_barrier_python ensure")
        service_reload = service_mask.index("systemctl --user daemon-reload")
        self.assertLess(service_lower, service_effective)
        self.assertLess(service_effective, service_reload)
        self.assertIn("runtime_service_barrier_binding", service_mask)
        self.assertIn("reconcile", service_mask)
        self.assertIn("$runtime_control_dir", service_mask)
        self.assertIn("$runtime_legacy_dir", service_mask)

        timer_lower = timer_mask.index(
            "systemctl --user mask --runtime wirtelprimpf.timer"
        )
        timer_effective = timer_mask.index("runtime_barrier_python ensure")
        timer_reload = timer_mask.index("systemctl --user daemon-reload")
        self.assertLess(timer_lower, timer_effective)
        self.assertLess(timer_effective, timer_reload)
        self.assertIn("runtime_timer_barrier_binding", timer_mask)
        self.assertIn("reconcile", timer_mask)

        for unmask, unit, binding in (
            (service_unmask, "wirtelprimpf.service", "runtime_service_barrier_binding"),
            (timer_unmask, "wirtelprimpf.timer", "runtime_timer_barrier_binding"),
        ):
            remove = unmask.index("runtime_barrier_python remove")
            reload = unmask.index("systemctl --user daemon-reload")
            self.assertLess(remove, reload)
            self.assertIn(unit, unmask)
            self.assertIn(binding, unmask)
            self.assertNotIn("systemctl --user unmask --runtime", unmask)

    def test_normative_quiesce_handles_auto_restart_without_stopping_a_running_job(self) -> None:
        self.assertIn("# BEGIN TASK4_GENERATOR_QUIESCE", self.deployment)
        quiesce = _marked_block(self.deployment, "TASK4_GENERATOR_QUIESCE")
        quiesce_generator = _shell_function(f"{quiesce}\n", "quiesce_generator")
        self.assertIn("deadline=$((SECONDS + 300))", quiesce)
        self.assertIn(
            "systemctl --user --job-mode=fail stop wirtelprimpf.service",
            quiesce,
        )
        self.assertNotIn(
            "systemctl --user stop wirtelprimpf.service",
            quiesce_generator,
        )
        self.assertIn(
            "systemctl --user show wirtelprimpf.service -p LoadState --value",
            quiesce,
        )

        fail_closed = _shell_function(self.deployment, "fail_closed_runtime")
        self.assertLess(
            fail_closed.index("wait_generator_inactive"),
            fail_closed.index("mask_generator_runtime"),
        )
        self.assertNotIn("mask --runtime wirtelprimpf.service", fail_closed)

        script = f"""
set -Eeuo pipefail
{quiesce}
case_name=$1
events=$2
state_counter=$3
mask_state=$4
state_spec=$5
effective_state=$6
printf '0\n' >"$state_counter"
case "$case_name" in
  unexpected-unit-state) printf 'enabled\n' >"$mask_state" ;;
  lower-only-mask-repaired) printf 'masked-runtime\n' >"$mask_state" ;;
  *) printf 'static\n' >"$mask_state" ;;
esac

next_generator_state() {{
  local index state active sub
  index="$(<"$state_counter")"
  IFS=',' read -r -a states <<<"$state_spec"
  if (( index >= ${{#states[@]}} )); then
    index=$((${{#states[@]}} - 1))
  fi
  state="${{states[$index]}}"
  printf '%s\n' "$(( $(<"$state_counter") + 1 ))" >"$state_counter"
  active="${{state%%:*}}"
  sub="${{state#*:}}"
  printf 'observe:%s/%s\n' "$active" "$sub" >>"$events"
  printf 'ActiveState=%s\nSubState=%s\n' "$active" "$sub"
}}

systemctl() {{
  case "$*" in
    '--user stop wirtelprimpf.timer')
      printf 'timer-stop\n' >>"$events"
      ;;
    '--user show wirtelprimpf.service -p ActiveState -p SubState --no-pager')
      next_generator_state
      ;;
    '--user --job-mode=fail stop wirtelprimpf.service')
      if [[ "$case_name" == post-snapshot-stop-race ]]; then
        printf 'service-stop-job-rejected\n' >>"$events"
        return 1
      fi
      printf 'service-stop\n' >>"$events"
      ;;
    '--user stop wirtelprimpf.service')
      printf 'destructive-default-service-stop\n' >>"$events"
      ;;
    '--user is-enabled wirtelprimpf.service')
      cat "$mask_state"
      ;;
    '--user mask --runtime wirtelprimpf.service')
      printf 'service-mask\n' >>"$events"
      printf 'masked-runtime\n' >"$mask_state"
      ;;
    '--user daemon-reload')
      printf 'daemon-reload\n' >>"$events"
      ;;
    '--user show wirtelprimpf.service -p LoadState --value')
      if [[ -e "$effective_state" ]]; then printf 'masked\n'; else printf 'loaded\n'; fi
      ;;
    *)
      printf 'unexpected-systemctl:%s\n' "$*" >>"$events"
      return 97
      ;;
  esac
}}

runtime_barrier_python() {{
  case "$1:$4" in
    'ensure:wirtelprimpf.service')
      printf 'service-control-barrier\n' >>"$events"
      : >"$effective_state"
      printf '{{"control":{{}},"legacy":{{}}}}\n'
      ;;
    *) return 97 ;;
  esac
}}

normalize_interrupted_timer_barrier() {{ return 0; }}

sleep() {{
  printf 'natural-wait\n' >>"$events"
  if [[ "$case_name" == timeout ]]; then
    SECONDS=301
  fi
}}

runtime_service_masked=0
runtime_service_barrier_binding=
runtime_control_dir=/fixture/user.control
runtime_legacy_dir=/fixture/user
SECONDS=0
set +e
quiesce_generator
status=$?
set -e
printf 'status:%s\nruntime-mask-flag:%s\n' "$status" "$runtime_service_masked"
"""

        cases = {
            "current-auto-restart": {
                "states": "activating:auto-restart,activating:auto-restart,inactive:dead,inactive:dead,inactive:dead",
                "success": True,
                "service_stop": True,
            },
            "running-start-pre-success": {
                "states": "activating:start-pre,inactive:dead,inactive:dead,inactive:dead",
                "success": True,
                "service_stop": False,
            },
            "running-success": {
                "states": "activating:start,inactive:dead,inactive:dead,inactive:dead",
                "success": True,
                "service_stop": False,
            },
            "running-auto-restart": {
                "states": (
                    "activating:start,activating:auto-restart,activating:auto-restart,"
                    "inactive:dead,inactive:dead,inactive:dead"
                ),
                "success": True,
                "service_stop": True,
            },
            "queued-auto-restart": {
                "states": "activating:auto-restart-queued,inactive:dead,inactive:dead,inactive:dead",
                "success": True,
                "service_stop": False,
            },
            "auto-restart-race": {
                "states": "activating:auto-restart,activating:start",
                "success": False,
                "service_stop": False,
            },
            "post-snapshot-stop-race": {
                "states": (
                    "activating:auto-restart,activating:auto-restart,"
                    "inactive:dead,inactive:dead"
                ),
                "success": False,
                "service_stop": False,
            },
            "after-mask-race": {
                "states": "inactive:dead,activating:start",
                "success": False,
                "service_stop": False,
            },
            "unexpected": {
                "states": "active:running",
                "success": False,
                "service_stop": False,
            },
            "unexpected-unit-state": {
                "states": "inactive:dead",
                "success": False,
                "service_stop": False,
            },
            "lower-only-mask-repaired": {
                "states": "inactive:dead,inactive:dead,inactive:dead",
                "success": True,
                "service_stop": False,
                "lower_mask": False,
            },
            "timeout": {
                "states": "activating:start",
                "success": False,
                "service_stop": False,
            },
        }
        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-quiesce-contract-") as tmp:
            for case_name, expected in cases.items():
                with self.subTest(case=case_name):
                    events = Path(tmp) / f"{case_name}.events"
                    counter = Path(tmp) / f"{case_name}.counter"
                    mask_state = Path(tmp) / f"{case_name}.mask"
                    result = subprocess.run(  # nosec B603 -- fixed Bash argv and local stub
                        [
                            "/bin/bash",
                            "-c",
                            script,
                            "quiesce-test",
                            case_name,
                            str(events),
                            str(counter),
                            str(mask_state),
                            str(expected["states"]),
                            str(Path(tmp) / f"{case_name}.effective"),
                        ],
                        text=True,
                        capture_output=True,
                        check=False,
                        timeout=5,
                        env={"HOME": "/home/teladi", "PATH": "/usr/bin:/bin"},
                    )
                    event_lines = events.read_text(encoding="utf-8").splitlines()
                    self.assertEqual(event_lines[0], "timer-stop", result.stderr)
                    self.assertFalse(
                        any(line.startswith("unexpected-systemctl:") for line in event_lines),
                        event_lines,
                    )
                    status_line = next(
                        line for line in result.stdout.splitlines() if line.startswith("status:")
                    )
                    status = int(status_line.removeprefix("status:"))
                    if expected["success"]:
                        self.assertEqual(status, 0, (result.stderr, event_lines))
                        self.assertIn("service-control-barrier", event_lines)
                        mask_index = event_lines.index("service-control-barrier")
                        inactive_indexes = [
                            index
                            for index, line in enumerate(event_lines)
                            if line == "observe:inactive/dead"
                        ]
                        self.assertTrue(inactive_indexes, event_lines)
                        self.assertLess(inactive_indexes[0], mask_index, event_lines)
                        self.assertTrue(
                            any(index > mask_index for index in inactive_indexes),
                            event_lines,
                        )
                        self.assertIn("runtime-mask-flag:1", result.stdout)
                        if expected.get("lower_mask", True):
                            self.assertIn("service-mask", event_lines)
                            self.assertLess(
                                event_lines.index("service-mask"),
                                mask_index,
                            )
                        else:
                            self.assertNotIn("service-mask", event_lines)
                    else:
                        self.assertNotEqual(status, 0, (result.stderr, event_lines))
                        if expected.get("fail_closed_mask"):
                            self.assertIn("service-control-barrier", event_lines)
                            self.assertIn("runtime-mask-flag:1", result.stdout)
                            self.assertGreater(
                                event_lines.index("observe:activating/start"),
                                event_lines.index("service-mask"),
                                event_lines,
                            )
                        else:
                            self.assertNotIn("service-control-barrier", event_lines)
                            self.assertIn("runtime-mask-flag:0", result.stdout)
                    if expected["service_stop"]:
                        self.assertIn("service-stop", event_lines)
                        self.assertLess(
                            event_lines.index("observe:activating/auto-restart"),
                            event_lines.index("service-stop"),
                            event_lines,
                        )
                    else:
                        self.assertNotIn("service-stop", event_lines)
                    if case_name == "current-auto-restart":
                        self.assertNotIn("natural-wait", event_lines)
                    if case_name in {
                        "running-start-pre-success",
                        "running-success",
                        "running-auto-restart",
                        "queued-auto-restart",
                        "timeout",
                    }:
                        self.assertIn("natural-wait", event_lines)
                    self.assertNotIn("destructive-default-service-stop", event_lines)

    def test_fail_closed_runtime_stops_then_masks_after_quiescence_failure(self) -> None:
        fail_closed = _shell_function(self.deployment, "fail_closed_runtime")
        script = f"""
set -Eeuo pipefail
{fail_closed}
events=$1
wait_calls=0
runtime_service_masked=0

wait_generator_inactive() {{
  wait_calls=$((wait_calls + 1))
  printf 'wait:%s\n' "$wait_calls" >>"$events"
  (( wait_calls > 1 ))
}}
mask_timer_runtime_stopped() {{ printf 'timer-mask\n' >>"$events"; }}
mask_generator_runtime() {{
  printf 'service-mask\n' >>"$events"
  runtime_service_masked=1
}}
systemctl() {{
  case "$*" in
    '--user stop wirtelprimpf-admin.service')
      printf 'admin-stop\n' >>"$events"
      ;;
    '--user stop wirtelprimpf.service')
      printf 'service-stop\n' >>"$events"
      ;;
    '--user is-active wirtelprimpf-admin.service'|'--user is-active wirtelprimpf.timer')
      printf 'inactive\n'
      ;;
    '--user is-enabled wirtelprimpf.timer'|'--user is-enabled wirtelprimpf.service')
      printf 'masked-runtime\n'
      ;;
    '--user show wirtelprimpf.service -p LoadState --value')
      printf 'masked\n'
      ;;
    *) return 97 ;;
  esac
}}

set +e
fail_closed_runtime
status=$?
set -e
test "$status" = 1
test "$runtime_service_masked" = 1
"""
        with tempfile.TemporaryDirectory(prefix="wirtelprimpf-fail-closed-") as tmp:
            events = Path(tmp) / "events"
            result = subprocess.run(  # nosec B603 -- fixed Bash argv and local stub
                ["/bin/bash", "-c", script, "fail-closed-test", str(events)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
                timeout=10,
                env={"HOME": "/home/teladi", "PATH": "/usr/bin:/bin"},
            )
            event_lines = events.read_text(encoding="utf-8").splitlines()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            event_lines,
            [
                "admin-stop",
                "timer-mask",
                "wait:1",
                "service-stop",
                "wait:2",
                "service-mask",
            ],
        )

    def test_restore_unmasks_an_inactive_generator_without_starting_it(self) -> None:
        unmask = _shell_function(self.deployment, "unmask_generator_runtime")
        first_inactive_proof = unmask.index("assert_generator_inactive")
        unmask_call = unmask.index("runtime_barrier_python remove")
        final_inactive_proof = unmask.rindex("assert_generator_inactive")
        self.assertLess(first_inactive_proof, unmask_call)
        self.assertLess(unmask_call, final_inactive_proof)
        self.assertNotIn("start wirtelprimpf.service", unmask)
        self.assertNotIn("restart wirtelprimpf.service", unmask)
        self.assertNotIn("systemctl --user unmask --runtime", unmask)

        rollback = _marked_block(self.deployment, "TASK4_ROLLBACK_DEPLOYMENT")
        self.assertLess(rollback.index("quiesce_generator"), rollback.index("restore_targets"))
        self.assertLess(
            rollback.index("unmask_generator_runtime"),
            rollback.index("restore_timer_activity"),
        )
        self.assertIn("service-auto-restart-stop", self.harness)
        self.assertIn("auto-restart-race", self.harness)
        self.assertIn("after-mask-reactivation", self.harness)

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
backend_wheelhouse=/nonexistent/wheelhouse
backend_wheel=/nonexistent/wheelhouse/backend.whl
backend_wheel_size=1
backend_wheel_sha256={'0' * 64}
backend_constraint=/nonexistent/wheelhouse/constraint.txt
backend_constraint_sha256={'1' * 64}
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
install_editable_offline_bounded() {{ return 0; }}
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
            communicated = False
            try:
                armed_deadline = time.monotonic() + 5
                while not armed.exists() and time.monotonic() < armed_deadline:
                    time.sleep(0.01)
                self.assertTrue(armed.exists(), "normative rollback probe did not arm")
                process.send_signal(signal.SIGTERM)
                recovery_deadline = time.monotonic() + 5
                while not recovery_ready.exists() and time.monotonic() < recovery_deadline:
                    time.sleep(0.01)
                self.assertTrue(
                    recovery_ready.exists(), "normative rollback did not enter recovery"
                )
                process.send_signal(signal.SIGHUP)
                time.sleep(0.05)
                self.assertIsNone(process.poll(), "second signal interrupted normative recovery")
                recovery_release.touch()
                stdout, stderr = process.communicate(timeout=10)
                communicated = True
                self.assertEqual(process.returncode, 143, stderr)
                self.assertEqual(stdout, "")
                self.assertTrue(
                    release_proof.exists(), "normative rollback did not release its lock"
                )
            finally:
                if process.poll() is None:
                    process.kill()
                if not communicated:
                    try:
                        process.communicate(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.communicate(timeout=2)

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

    def test_task4_binds_remote_factory_and_local_hardening_target_separately(self) -> None:
        marker = "TASK4_FACTORY_TARGET_BINDING"
        self.assertIn(f"# BEGIN {marker}", self.deployment)
        binding = _marked_block(self.deployment, marker)
        self.assertIn(
            "factory_sha=\"${GENERATOR_MERGE_SHA:?verified Task-3 receipt SHA required}\"",
            self.deployment,
        )
        self.assertIn(
            "target_ref=refs/heads/agent/pr4-closed-merge-reconcile",
            self.deployment,
        )
        self.assertIn('[[ "$factory_sha" =~ ^[0-9a-f]{40}$ ]]', binding)
        self.assertIn(
            'test "$factory_sha" = 274b25c9e1f9ea97d3b060997ed5c425d2b30e9f',
            binding,
        )
        self.assertIn('[[ "$target_sha" =~ ^[0-9a-f]{40}$ ]]', binding)
        self.assertIn('test "$factory_sha" != "$target_sha"', binding)
        self.assertIn('git_runtime cat-file -e "$factory_sha^{commit}"', binding)
        self.assertIn('git_runtime cat-file -e "$target_sha^{tree}"', binding)
        self.assertIn(
            'test "$(git_runtime rev-parse refs/remotes/origin/main)" = "$factory_sha"',
            binding,
        )
        self.assertIn(
            'test "$(git_runtime rev-parse "$target_ref^{commit}")" = "$target_sha"',
            binding,
        )
        self.assertIn(
            'git_runtime merge-base --is-ancestor "$factory_sha" "$target_sha"',
            binding,
        )
        initial_binding = self.deployment.index(
            "\nassert_task4_factory_target_binding\n"
        )
        first_mutation = self.deployment.index(
            'deploy_backup="$(mktemp -d', initial_binding
        )
        fetch = self.deployment.index("\ngit_runtime_fetch_bounded\n")
        rebound = self.deployment.index(
            "\nassert_task4_factory_target_binding\n", fetch
        )
        self.assertLess(initial_binding, first_mutation)
        self.assertLess(fetch, rebound)
        self.assertNotIn(
            'test "$(git_runtime rev-parse origin/main)" = "$target_sha"',
            self.deployment,
        )

    def test_step6_redacts_every_unexpected_http_status_or_payload(self) -> None:
        marker = "STEP6_REDACTED_HTTP_ASSERTION"
        self.assertIn(f"# BEGIN {marker}", self.smoke_sync)
        helper = _marked_block(self.smoke_sync, marker)
        namespace: dict[str, object] = {"json": json, "FIELD": "output_resolution"}
        exec(compile(helper, "<step6-redacted-http>", "exec"), namespace)  # nosec B102 -- reviewed plan source is the test subject
        require_http = namespace["require_http"]
        secret = "OPENAI_API_KEY=must-never-escape"
        path = "/home/teladi/.config/wirtelprimpf/openai.env"
        payload = {
            "error": f"{secret}:{path}",
            "conflicts": ["output_resolution", secret, path],
            "rollback_succeeded": True,
            "settings": {"output_resolution": "source", "secret": secret},
        }
        with self.assertRaises(AssertionError) as caught:
            require_http(False, 403, payload)
        evidence = json.loads(str(caught.exception))
        self.assertEqual(
            set(evidence),
            {
                "status",
                "error",
                "conflicts",
                "rollback_succeeded",
                "expected_field",
                "expected_value_class",
            },
        )
        self.assertEqual(evidence["status"], 403)
        self.assertEqual(evidence["error"], "redacted-unexpected-error")
        self.assertEqual(evidence["conflicts"], "redacted-unexpected-conflicts")
        self.assertEqual(evidence["rollback_succeeded"], True)
        self.assertEqual(evidence["expected_field"], "output_resolution")
        self.assertEqual(evidence["expected_value_class"], "string-choice")
        self.assertNotIn(secret, str(caught.exception))
        self.assertNotIn(path, str(caught.exception))
        self.assertNotIn("settings", str(caught.exception))
        malformed_payload = {
            "error": [secret, {"path": path}],
            "conflicts": {"secret": secret, "path": path},
            "rollback_succeeded": "yes",
            "settings": {"secret": secret},
        }
        with self.assertRaises(AssertionError) as malformed_caught:
            require_http(False, f"403:{secret}", malformed_payload)
        malformed_evidence = json.loads(str(malformed_caught.exception))
        self.assertEqual(malformed_evidence["status"], "redacted-unexpected-status")
        self.assertEqual(malformed_evidence["error"], "redacted-unexpected-error")
        self.assertEqual(
            malformed_evidence["conflicts"], "redacted-unexpected-conflicts"
        )
        self.assertIsNone(malformed_evidence["rollback_succeeded"])
        self.assertNotIn(secret, str(malformed_caught.exception))
        self.assertNotIn(path, str(malformed_caught.exception))
        self.assertNotIn("assert status ==", self.smoke_sync)
        self.assertGreaterEqual(self.smoke_sync.count("require_http("), 10)
        self.assertEqual(self.deployment.count(self.smoke_sync), 1)

    def test_task5_pins_factory_while_runtime_main_is_the_hardening_target(self) -> None:
        marker = "TASK5_GENERATOR_BOOTSTRAP_GATE"
        for name, script in (
            ("step1", self.task5_step1),
            ("step2", self.task5_step2),
            ("step3", self.task5_step3),
            ("step4", self.task5_step4),
            ("step5", self.task5_step5),
            ("step6", self.task5_step6),
        ):
            with self.subTest(name=name):
                self.assertIn(f"# BEGIN {marker}", script)
                self.assertIn("assert_task5_generator_bootstrap", script)
                self.assertNotIn(
                    'test "$generator_factory_sha" = \\\n  "$(/usr/bin/git -C "$generator_checkout" rev-parse HEAD)"',
                    script,
                )
        gate = _marked_block(self.task5_step1, marker)
        self.assertIn(
            "generator_target_ref=refs/heads/agent/pr4-closed-merge-reconcile",
            self.task5_step1,
        )
        self.assertIn('test "$generator_factory_sha" != "$generator_target_sha"', gate)
        self.assertIn(
            'test "$(/usr/bin/git -C "$generator_checkout" rev-parse HEAD)" = '
            '"$generator_target_sha"',
            gate,
        )
        self.assertIn(
            'test "$(/usr/bin/git -C "$generator_checkout" rev-parse origin/main)" = '
            '"$generator_factory_sha"',
            gate,
        )
        self.assertIn(
            '"$generator_factory_sha:.github/workflows/archive-pages.yml"', gate
        )
        self.assertIn(
            '"$generator_target_sha:.github/workflows/archive-pages.yml"', gate
        )
        self.assertIn('test "$factory_blob" = "$target_blob"', gate)

    def test_generator_followup_runs_only_after_task5_and_verifies_merge_before_cas(self) -> None:
        heading = "### Task 5a: Publish the locally deployed generator hardening"
        self.assertIn(heading, self.document)
        followup_offset = self.document.index(heading)
        task6_offset = self.document.index("### Task 6:")
        self.assertLess(followup_offset, task6_offset)
        followup = _code_block_after(
            self.document[followup_offset:task6_offset],
            "**Step 1: Gate, publish, merge, and reconcile the generator hardening**",
        )
        archive_gate = followup.index("assert_followup_archive_complete")
        local_gate = followup.index("assert_followup_local_rollout")
        identity_gate_offset = followup.index("# BEGIN FOLLOWUP_REMOTE_IDENTITY_GATE")
        push = followup.index("git_followup_remote push")
        pull_request = followup.index("followup_gh pr create")
        checks = followup.index("followup_gh pr checks")
        review = followup.index("assert_followup_review")
        final_pr_gate = followup.index("assert_followup_final_pr_gate")
        merge = followup.index('merge_sha="$(git_followup_commit_tree')
        atomic_push = followup.index("git_followup_remote push --atomic")
        fetch = followup.index("git_followup_fetch_main_bounded")
        tree_gate = followup.index('test "$merge_tree" = "$target_tree"')
        parent_gate = followup.index('test "${merge_parents[0]}" = "$factory_sha"')
        cas = followup.index(
            'update-ref refs/heads/main "$merge_sha" "$target_sha"'
        )
        postflight = followup.rindex("assert_followup_local_rollout")
        self.assertLess(local_gate, archive_gate)
        self.assertLess(archive_gate, push)
        self.assertLess(identity_gate_offset, push)
        self.assertLess(push, pull_request)
        self.assertLess(pull_request, checks)
        self.assertLess(checks, review)
        self.assertLess(review, final_pr_gate)
        self.assertLess(final_pr_gate, merge)
        self.assertLess(review, merge)
        self.assertLess(merge, tree_gate)
        self.assertLess(tree_gate, parent_gate)
        self.assertLess(parent_gate, atomic_push)
        self.assertLess(atomic_push, fetch)
        self.assertLess(fetch, cas)
        self.assertLess(cas, postflight)
        self.assertIn('test "$merge_sha" = "$remote_main_sha"', followup)
        self.assertIn('test -z "$(git_followup status --porcelain)"', followup)
        self.assertNotIn("followup_gh pr merge", followup)
        identity_gate = _marked_block(followup, "FOLLOWUP_REMOTE_IDENTITY_GATE")
        self.assertIn("H234598:54270221", identity_gate)
        self.assertIn("R_kgDOTpr2BA", identity_gate)
        self.assertIn("H234598/Wirtelprimpf-generator", identity_gate)
        git_config_guard = _marked_block(followup, "FOLLOWUP_GIT_CONFIG_GUARD")
        for rejected_key_family in (
            "include",
            "url",
            "http",
            "protocol",
            "credential",
            "core\\.(askpass|hookspath|sshcommand|gitproxy|fsmonitor)",
            "remote\\..*\\.(proxy|vcs|receivepack|uploadpack|pushurl)",
        ):
            self.assertIn(rejected_key_family, git_config_guard)
        self.assertIn('assert_safe_followup_git_config "$runtime"', followup)
        self.assertIn('assert_safe_followup_git_config "$hardening_checkout"', followup)
        receipt = _marked_block(followup, "FOLLOWUP_TASK3_RECEIPT_V3")
        self.assertIn("keys == [", receipt)
        self.assertIn('.version == 3 and .state == "verified"', receipt)
        self.assertIn('.review_state == "APPROVED"', receipt)
        self.assertIn("274b25c9e1f9ea97d3b060997ed5c425d2b30e9f", followup)
        self.assertIn('test "$package_version" = 1.1.0', followup)
        for unit_gate in (
            'test "$(systemctl --user is-enabled wirtelprimpf.timer)" = enabled',
            'test "$(systemctl --user show wirtelprimpf.timer -p ActiveState --value)" = active',
            'test "$(systemctl --user show wirtelprimpf.timer -p SubState --value)" = waiting',
            'test "$(systemctl --user is-enabled wirtelprimpf.service)" = static',
            'test "$(systemctl --user show wirtelprimpf.service -p ActiveState --value)" = inactive',
            'test "$(systemctl --user show wirtelprimpf.service -p SubState --value)" = dead',
            'test "$(systemctl --user is-enabled wirtelprimpf-admin.service)" = enabled',
            'test "$(systemctl --user show wirtelprimpf-admin.service -p ActiveState --value)" = active',
            'test "$(systemctl --user show wirtelprimpf-admin.service -p SubState --value)" = running',
        ):
            self.assertIn(unit_gate, followup)
        final_gate = _marked_block(followup, "FOLLOWUP_FINAL_PR_GATE")
        for predicate in (
            '.state == "OPEN"',
            '.headRefOid == $target',
            '.baseRefName == "main"',
            ".statusCheckRollup",
            "assert_followup_review",
            'test "$final_remote_main_sha" = "$factory_sha"',
        ):
            self.assertIn(predicate, final_gate)
        exact_cas = _marked_block(followup, "FOLLOWUP_EXACT_REMOTE_CAS")
        self.assertIn('"$remote_ref" == refs/heads/main', exact_cas)
        self.assertIn('"$remote_sha" == "$FOLLOWUP_EXPECTED_FACTORY"', exact_cas)
        self.assertIn('"$local_sha" == "$FOLLOWUP_EXPECTED_MERGE"', exact_cas)
        self.assertIn('test "$record_count" = 1', exact_cas)
        self.assertNotIn("FOLLOWUP_EXPECTED_TARGET", exact_cas)
        self.assertIn(
            'FOLLOWUP_EXPECTED_FACTORY="${FOLLOWUP_EXPECTED_FACTORY:-}"',
            followup,
        )
        self.assertIn(
            'FOLLOWUP_EXPECTED_MERGE="${FOLLOWUP_EXPECTED_MERGE:-}"',
            followup,
        )
        self.assertIn(
            'FOLLOWUP_EXPECTED_ORIGIN="${FOLLOWUP_EXPECTED_ORIGIN:-}"',
            followup,
        )
        self.assertIn("--atomic", followup)
        self.assertNotIn('":$remote_target_ref"', followup)
        self.assertIn(
            'test "$postmerge_remote_target_sha" = "$target_sha"', followup
        )
        remote_commitpoint = _marked_block(
            followup, "FOLLOWUP_REMOTE_COMMITPOINT"
        )
        self.assertIn('printf "push\\n"', remote_commitpoint)
        self.assertIn('printf "reconcile\\n"', remote_commitpoint)
        self.assertIn('"$remote_main_sha" == "$factory_sha"', remote_commitpoint)
        self.assertIn('"$remote_main_sha" == "$merge_sha"', remote_commitpoint)
        self.assertIn('"$remote_target_sha" == "$target_sha"', remote_commitpoint)
        self.assertEqual(followup.count("git_followup_remote push --atomic"), 1)
        discovery = _marked_block(followup, "FOLLOWUP_IDEMPOTENT_PR_DISCOVERY")
        self.assertIn("--state all", discovery)
        self.assertIn('"OPEN"|"MERGED"', discovery)
        self.assertIn("followup_gh pr create", discovery)
        local_cas = _marked_block(followup, "FOLLOWUP_IDEMPOTENT_LOCAL_CAS")
        self.assertIn('"$target_sha")', local_cas)
        self.assertIn('"$merge_sha")', local_cas)
        self.assertLess(postflight, followup.index("unset followup_ephemeral_token"))
        self.assertLess(postflight, followup.rindex("unset GH_TOKEN"))
        self.assertIn('test -z "${GH_TOKEN+x}"', followup)
        self.assertIn("No reinstall is performed", self.document[followup_offset:task6_offset])
        self.assertIn("Run or reconcile", self.document[followup_offset:task6_offset])
        self.assertNotIn("Run once", self.document[followup_offset:task6_offset])
        self.assertNotRegex(followup, r"(?:--force|-f)(?:\s|$)")

    def test_generator_followup_exact_main_cas_runs_in_a_real_bare_remote(self) -> None:
        heading = "### Task 5a: Publish the locally deployed generator hardening"
        offset = self.document.index(heading)
        followup = _code_block_after(
            self.document[offset : self.document.index("### Task 6:")],
            "**Step 1: Gate, publish, merge, and reconcile the generator hardening**",
        )
        hook = "#!/bin/bash\nset -Eeuo pipefail\n" + _marked_block(
            followup, "FOLLOWUP_EXACT_REMOTE_CAS"
        )
        classifier = _marked_block(followup, "FOLLOWUP_REMOTE_COMMITPOINT")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            local = root / "local"
            remote = root / "remote.git"
            hooks = root / "hooks"
            hooks.mkdir(mode=0o700)
            hook_path = hooks / "pre-push"
            hook_path.write_text(hook, encoding="utf-8")
            hook_path.chmod(0o700)

            def git(*arguments: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    ["/usr/bin/git", "-c", "protocol.file.allow=always", *arguments],
                    input=input_text,
                    text=True,
                    capture_output=True,
                    check=True,
                    timeout=15,
                    env=dict(_FIXTURE_GIT_ENV),
                )

            git("init", "--bare", str(remote))
            git("init", "-b", "main", str(local))
            git("-C", str(local), "config", "user.name", "H234598")
            git(
                "-C",
                str(local),
                "config",
                "user.email",
                "54270221+H234598@users.noreply.github.com",
            )
            (local / "state.txt").write_text("factory\n", encoding="utf-8")
            git("-C", str(local), "add", "state.txt")
            git("-C", str(local), "commit", "-m", "factory")
            factory = git("-C", str(local), "rev-parse", "HEAD").stdout.strip()
            git("-C", str(local), "push", str(remote), "main:refs/heads/main")
            git("-C", str(local), "switch", "-c", "agent/pr4-closed-merge-reconcile")
            (local / "state.txt").write_text("target\n", encoding="utf-8")
            git("-C", str(local), "commit", "-am", "target")
            target = git("-C", str(local), "rev-parse", "HEAD").stdout.strip()
            git(
                "-C",
                str(local),
                "push",
                str(remote),
                "HEAD:refs/heads/agent/pr4-closed-merge-reconcile",
            )
            tree = git("-C", str(local), "rev-parse", "HEAD^{tree}").stdout.strip()
            merge = git(
                "-C",
                str(local),
                "commit-tree",
                tree,
                "-p",
                factory,
                "-p",
                target,
                input_text="deterministic merge\n",
            ).stdout.strip()
            push_env = {
                **_FIXTURE_GIT_ENV,
                "FOLLOWUP_EXPECTED_ORIGIN": str(remote),
                "FOLLOWUP_EXPECTED_FACTORY": factory,
                "FOLLOWUP_EXPECTED_MERGE": merge,
            }

            def classify_remote(main_sha: str) -> str:
                script = (
                    classifier
                    + "\nclassify_followup_remote_state "
                    + "\"$TEST_MAIN\" \"$TEST_TARGET\" "
                    + "\"$TEST_FACTORY\" \"$TEST_MERGE\" "
                    + "\"$TEST_TARGET\"\n"
                )
                result = subprocess.run(
                    ["/usr/bin/bash"],
                    input=script,
                    text=True,
                    capture_output=True,
                    check=True,
                    timeout=15,
                    env={
                        "HOME": "/home/teladi",
                        "PATH": "/usr/bin:/bin",
                        "TEST_MAIN": main_sha,
                        "TEST_TARGET": target,
                        "TEST_FACTORY": factory,
                        "TEST_MERGE": merge,
                    },
                )
                return result.stdout.strip()

            self.assertEqual(classify_remote(factory), "push")
            push_command = [
                "/usr/bin/git",
                "-c",
                "protocol.file.allow=always",
                "-c",
                f"core.hooksPath={hooks}",
                "-C",
                str(local),
                "push",
                "--atomic",
                str(remote),
                f"{merge}:refs/heads/main",
            ]
            accepted = subprocess.run(
                push_command,
                text=True,
                capture_output=True,
                check=False,
                timeout=15,
                env=push_env,
            )
            self.assertEqual(accepted.returncode, 0, accepted.stderr)
            self.assertEqual(
                git("--git-dir", str(remote), "rev-parse", "refs/heads/main").stdout.strip(),
                merge,
            )
            self.assertEqual(
                git(
                    "--git-dir",
                    str(remote),
                    "rev-parse",
                    "refs/heads/agent/pr4-closed-merge-reconcile",
                ).stdout.strip(),
                target,
            )
            self.assertEqual(classify_remote(merge), "reconcile")

            git(
                "--git-dir",
                str(remote),
                "update-ref",
                "refs/heads/main",
                target,
                merge,
            )
            rejected = subprocess.run(
                push_command,
                text=True,
                capture_output=True,
                check=False,
                timeout=15,
                env=push_env,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertEqual(
                git("--git-dir", str(remote), "rev-parse", "refs/heads/main").stdout.strip(),
                target,
            )

    def test_generator_followup_git_config_guard_rejects_transport_overrides(self) -> None:
        heading = "### Task 5a: Publish the locally deployed generator hardening"
        offset = self.document.index(heading)
        followup = _code_block_after(
            self.document[offset : self.document.index("### Task 6:")],
            "**Step 1: Gate, publish, merge, and reconcile the generator hardening**",
        )
        guard = _marked_block(followup, "FOLLOWUP_GIT_CONFIG_GUARD")
        canonical_origin = "https://github.com/H234598/Wirtelprimpf-generator.git"
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary) / "repository"
            _fixture_git(["init", "-q", "-b", "main", str(repository)], check=True)
            _fixture_git(
                ["-C", str(repository), "remote", "add", "origin", canonical_origin],
                check=True,
            )
            script = (
                "set -Eeuo pipefail\n"
                'canonical_origin="$2"\n'
                + guard
                + '\nassert_safe_followup_git_config "$1"\n'
            )

            def execute() -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    ["/usr/bin/bash", "-c", script, "followup-config", str(repository), canonical_origin],
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=15,
                    env=dict(_FIXTURE_GIT_ENV),
                )

            accepted = execute()
            self.assertEqual(accepted.returncode, 0, accepted.stderr)
            forbidden = (
                ("include.path", "/tmp/foreign-config"),
                ("url.https://attacker.invalid/.insteadOf", "https://github.com/"),
                ("http.proxy", "https://attacker.invalid"),
                ("protocol.file.allow", "always"),
                ("credential.helper", "/bin/false"),
                ("core.hooksPath", "/tmp/foreign-hooks"),
                ("remote.origin.uploadpack", "/bin/false"),
            )
            for key, value in forbidden:
                with self.subTest(key=key):
                    _fixture_git(
                        ["-C", str(repository), "config", "--local", key, value],
                        check=True,
                    )
                    rejected = execute()
                    self.assertNotEqual(rejected.returncode, 0)
                    _fixture_git(
                        ["-C", str(repository), "config", "--local", "--unset-all", key],
                        check=True,
                    )

    def test_make_check_runs_the_rollout_contract(self) -> None:
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn(
            "$(PYTHON) -m unittest tests.test_rollout_plan_contract",
            makefile,
        )

    def test_disposable_step10_harness_executes_successfully(self) -> None:
        result = subprocess.run(
            ["/bin/bash"],
            input=self.harness,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
            env={"HOME": "/home/teladi", "PATH": "/usr/bin:/bin"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
