from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from wirtelprimpf_platform.settings_io import (
    EnvironmentDocument,
    SecureFile,
    SettingsIOError,
    SingleSecretStore,
)


class SettingsIOTests(unittest.TestCase):
    def test_environment_render_preserves_comments_unknown_keys_and_order(self) -> None:
        document = EnvironmentDocument.parse(
            "# local\nFUTURE_SETTING=keep\nWIRTELPRIMPF_OPERANDI=story\n"
        )
        rendered = document.render(
            {"WIRTELPRIMPF_OPERANDI": "both", "WIRTELPRIMPF_SITE_TITLE": "Atelier"}
        )
        self.assertEqual(
            rendered,
            "# local\nFUTURE_SETTING=keep\nWIRTELPRIMPF_OPERANDI=both\nWIRTELPRIMPF_SITE_TITLE=Atelier\n",
        )

    def test_environment_render_quotes_values_and_deletes_only_named_keys(self) -> None:
        document = EnvironmentDocument.parse("A=one\nB='two words'\n# keep\n")
        self.assertEqual(document.values, {"A": "one", "B": "two words"})
        self.assertEqual(document.render({"A": None, "B": "new value"}), "B='new value'\n# keep\n")

    def test_duplicate_and_malformed_environment_keys_are_rejected(self) -> None:
        for text in ("A=one\nA=two\n", "lower=value\n", "A='unterminated\n"):
            with self.subTest(text=text), self.assertRaises(SettingsIOError):
                EnvironmentDocument.parse(text)

    def test_atomic_private_replace_and_byte_restore_are_exact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "private" / "openai.env"
            store = SecureFile(target, private=True)
            store.replace_bytes(b"A=one\n")
            before = store.capture()
            store.replace_bytes(b"A=two\n")
            store.restore(before)
            self.assertEqual(target.read_bytes(), b"A=one\n")
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            self.assertEqual(target.parent.stat().st_mode & 0o777, 0o700)
            self.assertEqual(list(target.parent.glob(".*.part")), [])

    def test_every_new_private_parent_component_has_private_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "first"
            second = first / "second"
            SecureFile(second / "settings.env", private=True).replace_bytes(b"A=one\n")
            self.assertEqual(first.stat().st_mode & 0o777, 0o700)
            self.assertEqual(second.stat().st_mode & 0o777, 0o700)

    def test_existing_private_final_parent_is_hardened_to_private_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary) / "existing"
            parent.mkdir(mode=0o755)
            os.chmod(parent, 0o755)

            SecureFile(parent / "settings.env", private=True).replace_bytes(b"A=one\n")

            self.assertEqual(parent.stat().st_mode & 0o777, 0o700)

    def test_new_public_parent_components_ignore_restrictive_umask(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            existing_parent = Path(temporary) / "existing"
            existing_parent.mkdir(mode=0o700)
            os.chmod(existing_parent, 0o700)
            first = existing_parent / "first"
            final_parent = first / "second"

            previous_umask = os.umask(0o077)
            try:
                SecureFile(final_parent / "settings.env", private=False).replace_bytes(
                    b"A=one\n"
                )
            finally:
                os.umask(previous_umask)

            self.assertEqual(existing_parent.stat().st_mode & 0o777, 0o700)
            self.assertEqual(first.stat().st_mode & 0o777, 0o755)
            self.assertEqual(final_parent.stat().st_mode & 0o777, 0o755)

    def test_restore_of_previously_absent_file_removes_only_the_regular_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "private" / "new.env"
            store = SecureFile(target, private=True)
            before = store.capture()
            store.replace_bytes(b"A=one\n")
            store.restore(before)
            self.assertFalse(target.exists())

    def test_cloudflare_secret_is_stored_only_in_its_separate_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            secret_path = Path(temporary) / "cloudflare" / "api-token.env"
            secret = SingleSecretStore(secret_path, "CLOUDFLARE_API_TOKEN")
            secret.replace("secret-value-123")
            self.assertTrue(secret.present())
            self.assertEqual(
                secret_path.read_text(encoding="utf-8"),
                "CLOUDFLARE_API_TOKEN=secret-value-123\n",
            )
            secret.delete()
            self.assertFalse(secret_path.exists())

    def test_secret_presence_rejects_unexpected_keys_without_returning_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            secret_path = Path(temporary) / "cloudflare" / "api-token.env"
            secret_path.parent.mkdir()
            secret_path.write_text("OTHER=not-allowed\n", encoding="utf-8")
            with self.assertRaises(SettingsIOError):
                SingleSecretStore(secret_path, "CLOUDFLARE_API_TOKEN").present()

    def test_symlink_target_and_symlink_existing_parent_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            real = root / "real"
            real.mkdir()
            link = root / "link"
            link.symlink_to(real, target_is_directory=True)
            with self.assertRaisesRegex(SettingsIOError, "symlink"):
                SecureFile(link / "settings.env", private=True).replace_bytes(b"A=one\n")

    def test_special_file_target_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fifo = Path(temporary) / "fifo"
            os.mkfifo(fifo)
            with self.assertRaisesRegex(SettingsIOError, "regular"):
                SecureFile(fifo, private=True).replace_bytes(b"A=one\n")


if __name__ == "__main__":
    unittest.main()
