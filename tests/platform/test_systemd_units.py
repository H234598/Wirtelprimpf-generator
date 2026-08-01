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


if __name__ == "__main__":
    unittest.main()
