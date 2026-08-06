"""Host-compatible temporary-directory contracts for user services."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
UNIT_ROOT = ROOT / "Sourcecode" / "systemd-user"


class SystemdUnitTests(unittest.TestCase):
    def test_services_use_isolated_runtime_tmp_without_private_tmp_namespace(self) -> None:
        expected = {
            "wirtelprimpf.service": "wirtelprimpf-generator",
            "wirtelprimpf-atelier.service": "wirtelprimpf-generator",
            "wirtelprimpf-admin.service": "wirtelprimpf-admin",
            "wirtelprimpf-version-watch.service": "wirtelprimpf-version-watch",
        }

        for filename, runtime_directory in expected.items():
            with self.subTest(unit=filename):
                lines = {
                    line.strip()
                    for line in (UNIT_ROOT / filename).read_text(encoding="utf-8").splitlines()
                    if line.strip() and not line.lstrip().startswith("#")
                }
                self.assertIn("PrivateTmp=false", lines)
                self.assertNotIn("PrivateTmp=true", lines)
                self.assertIn(f"RuntimeDirectory={runtime_directory}", lines)
                self.assertIn("RuntimeDirectoryMode=0700", lines)
                for variable in ("TMPDIR", "TMP", "TEMP"):
                    self.assertIn(
                        f"Environment={variable}=%t/{runtime_directory}",
                        lines,
                    )

    def test_python_validation_accepts_security_positive_mount_flags(self) -> None:
        for relative in (
            "Sourcecode/watch_minor_version.sh",
            "Sourcecode/check_wirtelprimpf.sh",
        ):
            with self.subTest(script=relative):
                source = (ROOT / relative).read_text(encoding="utf-8")
                self.assertIn('== *",noexec,"*', source)
                self.assertNotIn('== *",nosuid,"*', source)
                self.assertNotIn('== *",nodev,"*', source)

    def test_full_check_discovers_versioned_non_symlink_python(self) -> None:
        source = (ROOT / "Sourcecode/check_wirtelprimpf.sh").read_text(encoding="utf-8")
        self.assertNotIn('SECURITY_PYTHON_CANDIDATES=("python3")', source)
        self.assertIn("discover_python_candidates()", source)
        self.assertIn("mapfile -t candidates < <(discover_python_candidates)", source)

    def test_full_check_exposes_only_the_trusted_project_root_for_imports(self) -> None:
        source = (ROOT / "Sourcecode/check_wirtelprimpf.sh").read_text(encoding="utf-8")
        self.assertIn('PYTHONPATH="$ROOT_DIR"', source)
        self.assertNotIn("PYTHONPATH= \\", source)

    def test_shell_validators_recognize_only_verified_unmapped_root(self) -> None:
        for relative in (
            "Sourcecode/watch_minor_version.sh",
            "Sourcecode/check_wirtelprimpf.sh",
        ):
            with self.subTest(script=relative):
                source = (ROOT / relative).read_text(encoding="utf-8")
                self.assertIn("root_uid_is_unmapped()", source)
                self.assertIn("detect_system_root_uid()", source)
                self.assertIn("is_trusted_owner_id()", source)
                self.assertIn('SYSTEM_ROOT_UID="$(detect_system_root_uid)"', source)
                self.assertNotIn('!= "$CURRENT_UID" && "$resolved_owner" != 0', source)

    def test_watcher_uid_map_parser_overrides_the_global_restricted_ifs(self) -> None:
        source = (ROOT / "Sourcecode/watch_minor_version.sh").read_text(encoding="utf-8")

        self.assertIn(
            "while IFS=$' \\t' read -r inside outside length extra; do",
            source,
        )

    def test_full_check_tmpdir_cannot_be_redirected_by_environment(self) -> None:
        source = (ROOT / "Sourcecode/check_wirtelprimpf.sh").read_text(encoding="utf-8")
        invocation = 'mktemp -d -p "$CHECK_TMP_BASE_DIR" wirtelprimpf-check-XXXXXX'
        self.assertIn(invocation, source)
        self.assertNotIn('mktemp -d -p "$CHECK_TMP_BASE_DIR" -t', source)

    def test_version_watcher_logs_to_journal_not_git_checkout(self) -> None:
        source = (UNIT_ROOT / "wirtelprimpf-version-watch.service").read_text(encoding="utf-8")
        self.assertIn("StandardOutput=journal", source)
        self.assertIn("StandardError=journal", source)
        self.assertNotIn("StandardOutput=append:", source)
        self.assertNotIn("StandardError=append:", source)

    def test_admin_service_writes_only_transaction_paths_and_does_not_import_secrets(self) -> None:
        lines = {
            line.strip()
            for line in (UNIT_ROOT / "wirtelprimpf-admin.service")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        environment_files = {
            line.partition("=")[2].removeprefix("-")
            for line in lines
            if line.startswith("EnvironmentFile=")
        }
        self.assertEqual(environment_files, set())
        self.assertNotIn("%h/.config/wirtelprimpf/openai.env", environment_files)
        self.assertEqual(
            {line for line in lines if line.startswith("ReadWritePaths=")},
            {
                "ReadWritePaths=%h/.config/wirtelprimpf",
                "ReadWritePaths=%h/.config/cloudflare",
                "ReadWritePaths=%h/.config/systemd/user/wirtelprimpf.timer.d",
            },
        )

    def test_generator_imports_the_separate_cloudflare_token_file_without_moving_it_back(self) -> None:
        lines = {
            line.strip()
            for line in (UNIT_ROOT / "wirtelprimpf.service")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        self.assertIn("EnvironmentFile=-%h/.config/cloudflare/api-token.env", lines)
        self.assertNotIn(
            "CLOUDFLARE_API_TOKEN=",
            (ROOT / "Sourcecode/env.example").read_text(encoding="utf-8"),
        )

    def test_manual_atelier_unit_is_fixed_to_classic_mode_and_shared_lock(self) -> None:
        source = (UNIT_ROOT / "wirtelprimpf-atelier.service").read_text(encoding="utf-8")
        self.assertIn("Environment=WIRTELPRIMPF_OPERANDI=classic", source)
        self.assertIn(
            "ExecStart=/usr/bin/env WIRTELPRIMPF_OPERANDI=classic /usr/bin/flock",
            source,
        )
        self.assertIn("generation.lock", source)
        self.assertIn("EnvironmentFile=%h/.config/wirtelprimpf/openai.env", source)


if __name__ == "__main__":
    unittest.main()
