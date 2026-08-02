# Transactional Settings, Live Sync, and Operational Status Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one transactional configuration authority for the local web admin and Cinnamon applet, synchronize both interfaces without overwriting unsaved edits, apply the real systemd timer, and expose a secret-free local `/api/status`.

**Architecture:** A small schema module defines every supported field and both model catalogs. A settings manager composes symlink-safe file stores, a systemd adapter, revision/conflict logic, generator validation, locking, and rollback; the web server imports it directly while the applet talks to it through a bounded JSON-over-stdin CLI. A separate local status collector reads systemd and persisted Wirtel state without making OpenAI, GitHub, or Cloudflare requests.

**Tech Stack:** Python 3.12+, standard-library `fcntl`, `pathlib`, `subprocess`, `http.server`, GTK 3/Gio/GLib in Cinnamon, browser ES modules, Node.js 24 tests, systemd user units, `unittest`.

## Global Constraints

- The approved design is `docs/superpowers/specs/2026-08-01-admin-live-sync-status-design.md`; its wording and security contract are authoritative.
- Bind the admin server only to `127.0.0.1` or `::1`; Host, Origin, CSRF, CSP, no-store, framing, MIME-sniffing, and referrer protections remain fail-closed.
- Keep `OPENAI_API_KEY` write-only in `~/.config/wirtelprimpf/openai.env`; keep `CLOUDFLARE_API_TOKEN` write-only in `~/.config/cloudflare/api-token.env` and never copy it into the Wirtel environment file.
- Keep private directories at mode `0700`, private files at `0600`, and systemd drop-ins at no more than `0644`; reject symlinks, special files, and unsafe existing parents.
- Every write request contains one `base_revision`, sparse non-secret `changes`, matching per-field `base_values`, and separate write-only `secret_actions`.
- Merge stale non-overlapping changes; reject the complete transaction when the same field changed; reject every stale secret action.
- Never overwrite a dirty field in either user interface. Web settings poll every 2 seconds, web status every 5 seconds, applet file events debounce for 250 ms, and the applet performs a defensive refresh every 30 seconds.
- The image-model order is exactly `gpt-image-2`, `gpt-image-1.5`, `gpt-image-1`, `gpt-image-1-mini`.
- The story-model order is exactly `gpt-5.5`, `gpt-5.5-pro`, `gpt-5.4`, `gpt-5.4-mini`, `gpt-5.4-nano`, `gpt-5.4-pro`, `gpt-5.2`, `gpt-5.2-pro`, `gpt-5.1`, `gpt-5`, `gpt-5-mini`, `gpt-5-nano`, `gpt-5-pro`, `gpt-4.1`, `gpt-4.1-mini`, `gpt-4.1-nano`, `gpt-4o`, `gpt-4o-mini`.
- A configured legacy model remains visible and unchanged; selecting a different model requires a catalog value.
- `/api/status` performs no external network request. A partial local-source failure returns HTTP 200 with `health: "degraded"` and explicit `null`/`"unknown"` values.
- Do not touch the Cinnamon upstream fix, the `codex-master` freeze/watchdog work, Cloudflare redirect rules, or DNS in this plan.
- Implement behavior test-first. Each task starts with a failing focused test, ends with its focused and neighboring regression suites green, and receives its own commit.
- Execute from an isolated worktree created with `superpowers:using-git-worktrees`; do not develop directly on `main`.
- Respect the user's fleet limit: do not dispatch one fresh worker per task. Execute inline, or assign this whole repository plan to exactly one persistent `gpt-5.6-sol` worker at `max` effort using `superpowers:executing-plans` and review its checkpoints from the primary session.

## Locked File Structure

### New Python core files

- `wirtelprimpf_platform/settings_schema.py` — field registry, model catalogs, type and semantic validation, choices and invariant payloads.
- `wirtelprimpf_platform/settings_io.py` — lossless environment documents, secure atomic file replacement, byte backups, restore, and separated secret-file storage.
- `wirtelprimpf_platform/systemd_user.py` — real timer observation, deterministic drop-in rendering, bounded systemctl application, and timer-state restoration.
- `wirtelprimpf_platform/settings.py` — paths, snapshots, opaque revision, shared/exclusive lock, sparse merge, transaction, generator check, rollback, and public serialization.
- `wirtelprimpf_platform/operational_status.py` — local, timeout-bounded, partially degradable status aggregation.

### New admin assets

- `wirtelprimpf_platform/static/admin.html` — accessible form and status-card markup with no inline script or style.
- `wirtelprimpf_platform/static/admin.css` — existing dark atelier presentation plus dirty/conflict/status states.
- `wirtelprimpf_platform/static/admin.mjs` — exported synchronization state machine and browser bootstrap.

### New applet support file

- `files/wirtelprimfgenerator@H234598/settings_sync.py` — bounded JSON CLI client and pure dirty/base/conflict state machine.

### New tests

- `tests/platform/test_settings_schema_core.py`
- `tests/platform/test_settings_io.py`
- `tests/platform/test_systemd_user.py`
- `tests/platform/test_settings_transaction.py`
- `tests/platform/test_settings_cli.py`
- `tests/platform/test_operational_status.py`
- `tests/test_admin_ui.mjs`
- `tests/test_applet_settings_sync.py`

### Existing files to modify

- `wirtelprimpf_platform/admin.py` — retain transport security and route handling; delegate settings, status, and static assets.
- `wirtelprimpf_platform/cli.py` — add settings snapshot/apply commands and construct the real admin dependencies.
- `pyproject.toml` — package static admin assets and add the stable `wirtelprimpf-settings` console entrypoint.
- `files/wirtelprimfgenerator@H234598/SettingsLogo.py` — remove independent file/systemd writers and bind widgets to `settings_sync.py`.
- `tests/platform/test_admin.py`, `tests/test_settings_schema.py`, `tests/platform/test_systemd_units.py` — update contracts without weakening existing security assertions.
- `Makefile`, `.github/workflows/check.yml` — run all new Python and Node contracts.
- `Sourcecode/systemd-user/wirtelprimpf-admin.service` — grant only the additional Cloudflare-token and timer-drop-in write paths; stop importing secrets as process environment.
- `scripts/install-local.sh`, `scripts/uninstall-local.sh` — install and preserve the shared settings CLI consistently.
- `README.md`, `files/wirtelprimfgenerator@H234598/README.md`, `Sourcecode/env.example` — document the single-writer contract and separate token path.

## Canonical Field Registry

The registry in Task 1 must contain these API keys. `environment` is `null` for values stored only in systemd. `web` and `applet` define presentation, not write authority; every row is owned by the same manager.

| key | environment | type/default | choices or bounds | web | applet |
|---|---|---|---|---|---|
| `operandi` | `WIRTELPRIMPF_OPERANDI` | string / `story` | `classic`, `story`, `both` | yes | yes |
| `image_model` | `WIRTELPRIMPF_IMAGE_MODEL` | string / `gpt-image-2` | image catalog | yes | yes |
| `story_model` | `WIRTELPRIMPF_STORY_MODEL` | string / `gpt-5-mini` | story catalog | yes | yes |
| `image_size` | `WIRTELPRIMPF_IMAGE_SIZE` | string / `1536x1024` | `1024x1024`, `1536x1024`, `1024x1536` | yes | yes |
| `output_resolution` | `WIRTELPRIMPF_OUTPUT_RESOLUTION` | string / `2k` | `source`, `2k`, `4k` | yes | yes |
| `generation_interval_minutes` | `WIRTELPRIMPF_GENERATION_INTERVAL_MINUTES` | integer / `120` | 30–10080 | yes | yes |
| `publish_immediately` | `WIRTELPRIMPF_PUBLISH_IMMEDIATELY` | boolean / `true` | boolean | yes | yes |
| `story_finish_parts_min` | `WIRTELPRIMPF_STORY_FINISH_PARTS_MIN` | integer / `3` | 1–12 | yes | yes |
| `story_finish_parts_max` | `WIRTELPRIMPF_STORY_FINISH_PARTS_MAX` | integer / `5` | 1–12 | yes | yes |
| `site_title` | `WIRTELPRIMPF_SITE_TITLE` | string / `Wirtelprimpfs Geschichtenatelier` | 1–120 chars | yes | no |
| `site_intro` | `WIRTELPRIMPF_SITE_INTRO` | string / `Zwei Katzen, eine Möhre, eine Maus und ein fortlaufendes Abenteuer.` | 1–500 chars | yes | no |
| `local_outdir` | `WIRTELPRIMPF_LOCAL_OUTDIR` | string / empty | 0–4096 chars | no | yes |
| `working_dir` | `WIRTELPRIMPF_WORKING_DIR` | string / empty | 0–4096 chars | no | yes |
| `repo_path` | `WIRTELPRIMPF_REPO_PATH` | string / `~/.local/share/wirtelprimpf/archives/Wirtelprimpf-0001` | 1–4096 chars | no | yes |
| `repo_slug` | `WIRTELPRIMPF_REPO_SLUG` | string / `H234598/Wirtelprimpf-0001` | 1–255 chars | no | yes |
| `repo_subdir` | `WIRTELPRIMPF_REPO_SUBDIR` | string / `Wirtelprimpf` | 0–255 chars | no | yes |
| `repo_branch` | `WIRTELPRIMPF_REPO_BRANCH` | string / `main` | 1–255 chars | no | yes |
| `github_owner` | `WIRTELPRIMPF_GITHUB_OWNER` | string / `H234598` | 1–255 chars | no | yes |
| `media_mode` | `WIRTELPRIMPF_MEDIA_MODE` | string / `release` | `release`, `git` | no | yes |
| `media_staging` | `WIRTELPRIMPF_MEDIA_STAGING` | string / `~/.local/state/wirtelprimpf/media-staging` | 1–4096 chars | no | yes |
| `platform_state` | `WIRTELPRIMPF_PLATFORM_STATE` | string / `~/.local/state/wirtelprimpf/platform-state.json` | 1–4096 chars | no | yes |
| `hub_dispatch_state` | `WIRTELPRIMPF_HUB_DISPATCH_STATE` | string / `~/.local/state/wirtelprimpf/hub-dispatch.json` | 1–4096 chars | no | yes |
| `generator_root` | `WIRTELPRIMPF_GENERATOR_ROOT` | string / `~/.local/share/wirtelprimpf-generator` | 1–4096 chars | no | yes |
| `archive_root` | `WIRTELPRIMPF_ARCHIVE_ROOT` | string / `~/.local/share/wirtelprimpf/archives` | 1–4096 chars | no | yes |
| `platform_catalog` | `WIRTELPRIMPF_PLATFORM_CATALOG` | string / `~/.local/share/wirtelprimpf-generator/data/publication-catalog.json` | 1–4096 chars | no | yes |
| `settings_path` | `WIRTELPRIMPF_SETTINGS_PATH` | string / `~/.config/wirtelprimpf/openai.env` | exact manager path | no | yes |
| `cloudflare_zone` | `WIRTELPRIMPF_CLOUDFLARE_ZONE` | string / `telacore.org` | 1–253 chars | no | yes |
| `cloudflare_zone_id` | `WIRTELPRIMPF_CLOUDFLARE_ZONE_ID` | string / empty | 0 or 32 lowercase hex chars | no | yes |
| `git_author_name` | `WIRTELPRIMPF_GIT_AUTHOR_NAME` | string / empty | 0–255 chars | no | yes |
| `git_author_email` | `WIRTELPRIMPF_GIT_AUTHOR_EMAIL` | string / empty | 0–320 chars | no | yes |
| `flex_processing` | `WIRTELPRIMPF_FLEX_PROCESSING` | string / `on` | `on`, `off`, `flex` | no | yes |
| `prompt_config` | `WIRTELPRIMPF_PROMPT_CONFIG` | string / empty | 0–4096 chars | no | yes |
| `story_prompt_config` | `WIRTELPRIMPF_STORY_PROMPT_CONFIG` | string / empty | 0–4096 chars | no | yes |
| `story_document` | `WIRTELPRIMPF_STORY_DOCUMENT` | string / empty | 0–4096 chars | no | yes |
| `story_state` | `WIRTELPRIMPF_STORY_STATE` | string / empty | 0–4096 chars | no | yes |
| `story_finish` | `WIRTELPRIMPF_STORY_FINISH` | boolean / `false` | boolean | no | yes |
| `timer_enabled` | null | boolean / `true` | boolean | no | yes |
| `timer_randomized_delay_seconds` | null | integer / `120` | 0–86400 | no | yes |
| `timer_persistent` | null | boolean / `true` | boolean | no | yes |

Secrets are not ordinary registry rows. Their only API keys are `openai_api_key` and `cloudflare_api_token`, and their only client operations are `replace` and `delete`.

---

### Task 1: Shared schema, catalogs, and semantic validation

**Files:**
- Create: `wirtelprimpf_platform/settings_schema.py`
- Create: `tests/platform/test_settings_schema_core.py`

**Interfaces:**
- Produces: `SettingSpec`, `SETTING_SPECS`, `IMAGE_MODEL_CHOICES`, `STORY_MODEL_CHOICES`.
- Produces: `validate_changes(changes: Mapping[str, object], current: Mapping[str, object]) -> dict[str, object]`.
- Produces: `choices_payload() -> dict[str, list[object]]` and `invariants_payload() -> dict[str, object]`.
- Consumed by: Tasks 4, 5, 7, 8, and 9.

- [x] **Step 1: Write failing catalog, visibility, type, and legacy-model tests**

```python
from __future__ import annotations

import unittest

from wirtelprimpf_platform.settings_schema import (
    IMAGE_MODEL_CHOICES,
    SETTING_SPECS,
    STORY_MODEL_CHOICES,
    SettingsValidationError,
    choices_payload,
    validate_changes,
)


class SettingsSchemaTests(unittest.TestCase):
    def test_model_catalogs_are_ordered_and_shared_fields_are_visible(self) -> None:
        self.assertEqual(IMAGE_MODEL_CHOICES, (
            "gpt-image-2", "gpt-image-1.5", "gpt-image-1", "gpt-image-1-mini",
        ))
        self.assertEqual(STORY_MODEL_CHOICES[0:6], (
            "gpt-5.5", "gpt-5.5-pro", "gpt-5.4", "gpt-5.4-mini", "gpt-5.4-nano", "gpt-5.4-pro",
        ))
        self.assertTrue(SETTING_SPECS["image_model"].web_visible)
        self.assertTrue(SETTING_SPECS["image_model"].applet_visible)
        self.assertFalse(SETTING_SPECS["site_title"].applet_visible)
        self.assertEqual(choices_payload()["story_model"], list(STORY_MODEL_CHOICES))

    def test_changed_model_must_be_catalogued_but_legacy_value_may_remain(self) -> None:
        current = {key: spec.default for key, spec in SETTING_SPECS.items()}
        current["story_model"] = "retired-story-model"
        self.assertEqual(validate_changes({"story_model": "retired-story-model"}, current)["story_model"], "retired-story-model")
        with self.assertRaisesRegex(SettingsValidationError, "story_model"):
            validate_changes({"story_model": "invented-story-model"}, current)

    def test_cross_field_and_scalar_validation_is_fail_closed(self) -> None:
        current = {key: spec.default for key, spec in SETTING_SPECS.items()}
        with self.assertRaisesRegex(SettingsValidationError, "must not exceed"):
            validate_changes({"story_finish_parts_min": 8, "story_finish_parts_max": 4}, current)
        with self.assertRaisesRegex(SettingsValidationError, "generation_interval_minutes"):
            validate_changes({"generation_interval_minutes": 29}, current)
        with self.assertRaisesRegex(SettingsValidationError, "unknown settings"):
            validate_changes({"shell_command": "false"}, current)
```

- [x] **Step 2: Run the focused tests and verify the missing module fails**

Run: `python -m unittest tests.platform.test_settings_schema_core -v`

Expected: `ERROR` with `ModuleNotFoundError: No module named 'wirtelprimpf_platform.settings_schema'`.

- [x] **Step 3: Implement the immutable registry and validators**

Implement the complete registry from “Canonical Field Registry” and use these exact public types and model tuples:

```python
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from .naming import ARCHIVE_CAPACITY, BOOKS_PER_ARCHIVE, STORIES_PER_BOOK

SETTINGS_SCHEMA_VERSION = "2.0.0"
IMAGE_MODEL_CHOICES = ("gpt-image-2", "gpt-image-1.5", "gpt-image-1", "gpt-image-1-mini")
STORY_MODEL_CHOICES = (
    "gpt-5.5", "gpt-5.5-pro", "gpt-5.4", "gpt-5.4-mini", "gpt-5.4-nano", "gpt-5.4-pro",
    "gpt-5.2", "gpt-5.2-pro", "gpt-5.1", "gpt-5", "gpt-5-mini", "gpt-5-nano", "gpt-5-pro",
    "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano", "gpt-4o", "gpt-4o-mini",
)
ValueKind = Literal["string", "integer", "boolean"]


class SettingsValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SettingSpec:
    env_name: str | None
    default: str | int | bool
    kind: ValueKind
    choices: tuple[str, ...] = ()
    minimum: int | None = None
    maximum: int | None = None
    max_length: int | None = None
    allow_empty: bool = False
    web_visible: bool = False
    applet_visible: bool = False


def validate_changes(changes: Mapping[str, object], current: Mapping[str, object]) -> dict[str, object]:
    unknown = set(changes) - set(SETTING_SPECS)
    if unknown:
        raise SettingsValidationError(f"unknown settings: {sorted(unknown)}")
    merged = dict(current)
    validated: dict[str, object] = {}
    for key, value in changes.items():
        spec = SETTING_SPECS[key]
        if spec.kind == "boolean":
            if not isinstance(value, bool):
                raise SettingsValidationError(f"{key} must be boolean")
        elif spec.kind == "integer":
            if isinstance(value, bool) or not isinstance(value, int):
                raise SettingsValidationError(f"{key} must be an integer")
            if spec.minimum is not None and value < spec.minimum:
                raise SettingsValidationError(f"{key} must be >= {spec.minimum}")
            if spec.maximum is not None and value > spec.maximum:
                raise SettingsValidationError(f"{key} must be <= {spec.maximum}")
        else:
            if not isinstance(value, str) or "\x00" in value or "\r" in value or "\n" in value:
                raise SettingsValidationError(f"{key} must be a single-line string")
            value = value.strip()
            if not value and not spec.allow_empty:
                raise SettingsValidationError(f"{key} must not be empty")
            if spec.max_length is not None and len(value) > spec.max_length:
                raise SettingsValidationError(f"{key} exceeds {spec.max_length} characters")
            if spec.choices and value not in spec.choices and value != current.get(key):
                raise SettingsValidationError(f"{key} must be selected from the catalog")
        validated[key] = value
        merged[key] = value
    if int(merged["story_finish_parts_min"]) > int(merged["story_finish_parts_max"]):
        raise SettingsValidationError("story_finish_parts_min must not exceed story_finish_parts_max")
    return validated


def choices_payload() -> dict[str, list[object]]:
    return {key: list(spec.choices) for key, spec in SETTING_SPECS.items() if spec.choices}


def invariants_payload() -> dict[str, object]:
    return {
        "archive_capacity": ARCHIVE_CAPACITY,
        "books_per_archive": BOOKS_PER_ARCHIVE,
        "repository_pattern": "Wirtelprimpf-####",
        "domain_suffix": "telacore.org",
        "stories_per_book": STORIES_PER_BOOK,
        "story_order_on_landing_page": "newest-first",
    }
```

For boolean environment values, Tasks 2 and 4 encode `true` as `1` and `false` as `0`. The schema itself never parses files.

- [x] **Step 4: Run schema tests and the existing naming/admin contracts**

Run: `python -m unittest tests.platform.test_settings_schema_core tests.platform.test_naming_state tests.platform.test_admin -v`

Expected: all tests pass; existing admin tests remain unchanged in this task.

- [x] **Step 5: Commit the schema unit**

```bash
git add wirtelprimpf_platform/settings_schema.py tests/platform/test_settings_schema_core.py
git commit -m "feat(settings): define shared configuration schema"
```

### Task 2: Lossless secure file and secret-store primitives

**Files:**
- Create: `wirtelprimpf_platform/settings_io.py`
- Create: `tests/platform/test_settings_io.py`

**Interfaces:**
- Consumes: environment names and scalar values produced by Task 1.
- Produces: `EnvironmentDocument.parse(text: str)`, `.values`, and `.render(updates: Mapping[str, str | None]) -> str`.
- Produces: `SecureFile(path: Path, private: bool)`, `FileBackup`, `read_bytes()`, `replace_bytes(content: bytes)`, `capture()`, and `restore(backup)`.
- Produces: `SingleSecretStore(path: Path, env_name: str)`, `present()`, `replace(value)`, `delete()`, `capture()`, and `restore()`.
- Consumed by: Task 4.

- [x] **Step 1: Write failing preservation, permissions, restore, and path-defense tests**

```python
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from wirtelprimpf_platform.settings_io import EnvironmentDocument, SecureFile, SettingsIOError, SingleSecretStore


class SettingsIOTests(unittest.TestCase):
    def test_environment_render_preserves_comments_unknown_keys_and_order(self) -> None:
        document = EnvironmentDocument.parse("# local\nFUTURE_SETTING=keep\nWIRTELPRIMPF_OPERANDI=story\n")
        rendered = document.render({"WIRTELPRIMPF_OPERANDI": "both", "WIRTELPRIMPF_SITE_TITLE": "Atelier"})
        self.assertEqual(rendered, "# local\nFUTURE_SETTING=keep\nWIRTELPRIMPF_OPERANDI=both\nWIRTELPRIMPF_SITE_TITLE=Atelier\n")

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

    def test_cloudflare_secret_is_stored_only_in_its_separate_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            secret_path = Path(temporary) / "cloudflare" / "api-token.env"
            secret = SingleSecretStore(secret_path, "CLOUDFLARE_API_TOKEN")
            secret.replace("secret-value-123")
            self.assertTrue(secret.present())
            self.assertEqual(secret_path.read_text(encoding="utf-8"), "CLOUDFLARE_API_TOKEN=secret-value-123\n")
            secret.delete()
            self.assertFalse(secret_path.exists())

    def test_symlink_target_and_symlink_existing_parent_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            real = root / "real"
            real.mkdir()
            link = root / "link"
            link.symlink_to(real, target_is_directory=True)
            with self.assertRaisesRegex(SettingsIOError, "symlink"):
                SecureFile(link / "settings.env", private=True).replace_bytes(b"A=one\n")
```

- [x] **Step 2: Run the focused tests and verify the missing module fails**

Run: `python -m unittest tests.platform.test_settings_io -v`

Expected: `ERROR` with `ModuleNotFoundError` for `settings_io`.

- [x] **Step 3: Implement lossless parsing and atomic replacement**

Use `shlex.split(..., comments=False, posix=True)` to parse values and `shlex.quote()` to render replacements. Reject duplicate or malformed keys. Implement replacement with this exact sequence:

```python
def replace_bytes(self, content: bytes) -> None:
    parent = self.path.parent
    _prepare_parent(parent, private=self.private)
    _reject_unsafe_target(self.path)
    mode = 0o600 if self.private else 0o644
    part = parent / f".{self.path.name}.{os.getpid()}.{uuid.uuid4().hex}.part"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(part, flags, mode)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(part, mode)
        os.replace(part, self.path)
        os.chmod(self.path, mode)
        directory_fd = os.open(parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        part.unlink(missing_ok=True)
```

`FileBackup` stores `existed: bool`, exact `content: bytes`, and `mode: int | None`. Restoring a previously absent file unlinks only that exact non-symlink regular target and fsyncs its parent; restoring an existing file calls `replace_bytes()` and then reapplies the captured mode.

`SingleSecretStore.replace()` validates a single-line value of 8–512 characters and writes exactly `ENV_NAME=<shlex-quoted-value>\n`. `present()` parses the file through `EnvironmentDocument` and never returns its value.

- [x] **Step 4: Run focused IO and existing atomic-state tests**

Run: `python -m unittest tests.platform.test_settings_io tests.platform.test_naming_state tests.platform.test_target_switch -v`

Expected: all tests pass and no `.part` file remains.

- [x] **Step 5: Commit the IO unit**

```bash
git add wirtelprimpf_platform/settings_io.py tests/platform/test_settings_io.py
git commit -m "feat(settings): add secure configuration file stores"
```

### Task 3: Real systemd timer adapter

**Files:**
- Create: `wirtelprimpf_platform/systemd_user.py`
- Create: `tests/platform/test_systemd_user.py`

**Interfaces:**
- Produces: `TimerConfiguration(enabled: bool, interval_minutes: int, randomized_delay_seconds: int, persistent: bool)`.
- Produces: `TimerObservation` with enabled, active state, effective interval, randomized delay, persistence, last trigger, next run, and raw result fields.
- Produces: `SystemdUserManager.observe_timer()`, `render_dropin(configuration)`, `apply_timer(configuration)`, and `restore_timer(configuration, was_active, dropin_backup)`.
- Consumed by: Tasks 4 and 6.

- [x] **Step 1: Write failing rendering, command, timeout, and effective-state tests**

```python
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from wirtelprimpf_platform.systemd_user import SystemdCommandError, SystemdUserManager, TimerConfiguration


class FakeRunner:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def __call__(self, command: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        if command[2:4] == ["is-enabled", "wirtelprimpf.timer"]:
            return subprocess.CompletedProcess(command, 0, "enabled\n", "")
        if command[2] == "show":
            return subprocess.CompletedProcess(command, 0, (
                "ActiveState=active\nResult=success\nPersistent=yes\n"
                "RandomizedDelayUSec=2min\nTimersMonotonic={ OnUnitActiveUSec=2h ; }\n"
                "LastTriggerUSec=Sat 2026-08-01 05:26:37 CEST\n"
                "NextElapseUSecRealtime=Sat 2026-08-01 07:28:15 CEST\n"
            ), "")
        return subprocess.CompletedProcess(command, 0, "", "")


class SystemdUserTests(unittest.TestCase):
    def test_dropin_is_deterministic_and_clears_vendor_timer_values(self) -> None:
        runner = FakeRunner()
        with tempfile.TemporaryDirectory() as temporary:
            manager = SystemdUserManager(Path(temporary) / "override.conf", runner=runner)
            text = manager.render_dropin(TimerConfiguration(True, 180, 90, True))
        self.assertEqual(text, (
            "[Timer]\nOnCalendar=\nOnBootSec=\nOnUnitActiveSec=\n"
            "OnBootSec=180min\nOnUnitActiveSec=180min\nRandomizedDelaySec=90\nPersistent=true\n"
        ))

    def test_apply_reloads_restarts_and_verifies_effective_state(self) -> None:
        runner = FakeRunner()
        with tempfile.TemporaryDirectory() as temporary:
            manager = SystemdUserManager(Path(temporary) / "override.conf", runner=runner)
            manager.apply_timer(TimerConfiguration(True, 120, 120, True))
        self.assertIn(["systemctl", "--user", "daemon-reload"], runner.commands)
        self.assertIn(["systemctl", "--user", "enable", "--now", "wirtelprimpf.timer"], runner.commands)
        self.assertEqual(manager.observe_timer().interval_minutes, 120)

    def test_nonzero_systemctl_result_is_redacted(self) -> None:
        def failed(command: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(command, 1, "", "token=must-not-echo")
        with tempfile.TemporaryDirectory() as temporary:
            manager = SystemdUserManager(Path(temporary) / "override.conf", runner=failed)
            with self.assertRaisesRegex(SystemdCommandError, "systemctl command failed") as caught:
                manager.apply_timer(TimerConfiguration(True, 120, 120, True))
            self.assertNotIn("must-not-echo", str(caught.exception))
```

- [x] **Step 2: Run the focused tests and verify the missing module fails**

Run: `python -m unittest tests.platform.test_systemd_user -v`

Expected: `ERROR` with `ModuleNotFoundError` for `systemd_user`.

- [x] **Step 3: Implement the bounded systemd adapter**

The default runner must be shell-free and bounded:

```python
def _default_runner(command: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        raise SystemdCommandError("cannot execute bounded systemctl command") from exc
```

Use only literal unit name `wirtelprimpf.timer`. `observe_timer()` runs `systemctl --user is-enabled wirtelprimpf.timer` and one `systemctl --user show wirtelprimpf.timer` with explicit properties. Normalize systemd durations (`us`, `ms`, `s`, `min`, `h`, `d`) to integer seconds/minutes and booleans (`yes`, `true`, `1`).

`apply_timer()` writes the rendered drop-in through `SecureFile(private=False)`, runs `daemon-reload`, then `enable --now` or `disable --now`, restarts an enabled timer, and calls `observe_timer()` to require the requested enabled, interval, delay, and persistence values. Mismatch raises `SystemdCommandError`.

`restore_timer(configuration, was_active, dropin_backup)` restores the supplied Task-2 `FileBackup` byte-for-byte before `daemon-reload`, restores enabled/disabled state, and restores active/inactive state separately so rollback does not accidentally start a timer that was stopped. It must not re-render the old configuration over the restored bytes; `configuration` is used only to verify effective values. Add a focused regression whose pre-state drop-in contains an extra comment and noncanonical spacing, then prove rollback restores identical bytes as well as enabled/active/effective values.

`TimerObservation.from_configuration(configuration, active)` is a deterministic constructor used by tests and rollback comparisons; it copies enabled/interval/delay/persistence, maps `active` to `"active"` or `"inactive"`, and sets timestamp/result fields to `None`/`"unknown"`.

- [x] **Step 4: Run systemd and unit-file regressions**

Run: `python -m unittest tests.platform.test_systemd_user tests.platform.test_systemd_units -v`

Expected: all tests pass.

- [x] **Step 5: Commit the timer adapter**

```bash
git add wirtelprimpf_platform/systemd_user.py tests/platform/test_systemd_user.py
git commit -m "feat(settings): manage the effective user timer"
```

### Task 4: Transactional settings manager, revisions, conflicts, and rollback

**Files:**
- Create: `wirtelprimpf_platform/settings.py`
- Create: `tests/platform/test_settings_transaction.py`

**Interfaces:**
- Consumes: Task 1 schema, Task 2 file stores, Task 3 systemd manager.
- Produces: `SettingsPaths.for_home(home: Path) -> SettingsPaths`.
- Produces: `SettingsSnapshot.to_public_dict() -> dict[str, object]`.
- Produces: `ChangeRequest.from_payload(payload: object) -> ChangeRequest`.
- Produces: `SettingsManager.snapshot() -> SettingsSnapshot` and `SettingsManager.apply(request: ChangeRequest) -> SettingsSnapshot`.
- Produces exceptions: `SettingsConflict`, `SettingsValidationFailure`, `SettingsLockBusy`, `SettingsApplyFailure`.
- Consumed by: Tasks 5, 6, and 7.

- [x] **Step 1: Write failing sparse-merge, same-field, secret, lock, and rollback tests**

```python
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from wirtelprimpf_platform.settings import (
    ChangeRequest,
    SettingsApplyFailure,
    SettingsConflict,
    SettingsManager,
    SettingsPaths,
    SettingsValidationFailure,
)
from wirtelprimpf_platform.systemd_user import TimerConfiguration, TimerObservation


class FakeSystemd:
    def __init__(self) -> None:
        self.configuration = TimerConfiguration(True, 120, 120, True)
        self.active = True
        self.fail_apply = False
        self.apply_calls = 0
        self.restore_calls = 0

    def observe_timer(self) -> TimerObservation:
        return TimerObservation.from_configuration(self.configuration, active=self.active)

    def apply_timer(self, configuration: TimerConfiguration) -> TimerObservation:
        self.apply_calls += 1
        if self.fail_apply:
            raise RuntimeError("injected systemd failure")
        self.configuration = configuration
        self.active = configuration.enabled
        return self.observe_timer()

    def restore_timer(
        self, configuration: TimerConfiguration, was_active: bool, dropin_backup: object | None = None,
    ) -> TimerObservation:
        self.restore_calls += 1
        self.configuration = configuration
        self.active = was_active
        return self.observe_timer()


class SettingsTransactionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.paths = SettingsPaths.for_home(root)
        self.paths.env_file.parent.mkdir(parents=True, mode=0o700)
        self.paths.env_file.write_text(
            "OPENAI_API_KEY=original-openai-secret\n"
            "WIRTELPRIMPF_OPERANDI=story\n"
            "WIRTELPRIMPF_SITE_TITLE=Original\n"
            "WIRTELPRIMPF_GENERATION_INTERVAL_MINUTES=120\n",
            encoding="utf-8",
        )
        os.chmod(self.paths.env_file, 0o600)
        self.systemd = FakeSystemd()
        self.manager = SettingsManager(self.paths, systemd=self.systemd, validator=lambda values: None)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_stale_non_overlapping_changes_merge_without_lost_update(self) -> None:
        base = self.manager.snapshot()
        document = self.paths.env_file.read_text(encoding="utf-8").replace(
            "WIRTELPRIMPF_OPERANDI=story", "WIRTELPRIMPF_OPERANDI=both"
        )
        self.paths.env_file.write_text(document, encoding="utf-8")
        result = self.manager.apply(ChangeRequest.from_payload({
            "base_revision": base.revision,
            "changes": {"site_title": "Extern sicher zusammengeführt"},
            "base_values": {"site_title": "Original"},
            "secret_actions": {},
        }))
        self.assertEqual(result.settings["operandi"], "both")
        self.assertEqual(result.settings["site_title"], "Extern sicher zusammengeführt")

    def test_stale_same_field_change_rejects_the_whole_transaction(self) -> None:
        base = self.manager.snapshot()
        before = self.paths.env_file.read_bytes()
        self.paths.env_file.write_text(before.decode().replace("Original", "Andere Oberfläche"), encoding="utf-8")
        external = self.paths.env_file.read_bytes()
        with self.assertRaises(SettingsConflict) as caught:
            self.manager.apply(ChangeRequest.from_payload({
                "base_revision": base.revision,
                "changes": {"site_title": "Mein Entwurf"},
                "base_values": {"site_title": "Original"},
                "secret_actions": {},
            }))
        self.assertEqual(caught.exception.fields, ("site_title",))
        self.assertEqual(self.paths.env_file.read_bytes(), external)

    def test_every_stale_secret_action_is_rejected_without_exposing_the_secret(self) -> None:
        base = self.manager.snapshot()
        self.paths.env_file.write_text(
            self.paths.env_file.read_text(encoding="utf-8") + "WIRTELPRIMPF_OUTPUT_RESOLUTION=4k\n",
            encoding="utf-8",
        )
        with self.assertRaises(SettingsConflict) as caught:
            self.manager.apply(ChangeRequest.from_payload({
                "base_revision": base.revision,
                "changes": {},
                "base_values": {},
                "secret_actions": {"cloudflare_api_token": {"action": "replace", "value": "new-cloudflare-secret"}},
            }))
        self.assertNotIn("new-cloudflare-secret", str(caught.exception))
        self.assertFalse(self.paths.cloudflare_token_file.exists())

    def test_validator_failure_restores_every_file_and_timer(self) -> None:
        before_env = self.paths.env_file.read_bytes()
        before_timer = self.systemd.configuration
        manager = SettingsManager(
            self.paths,
            systemd=self.systemd,
            validator=lambda values: (_ for _ in ()).throw(RuntimeError("invalid generator configuration")),
        )
        base = manager.snapshot()
        with self.assertRaises(SettingsApplyFailure) as caught:
            manager.apply(ChangeRequest.from_payload({
                "base_revision": base.revision,
                "changes": {"generation_interval_minutes": 180},
                "base_values": {"generation_interval_minutes": 120},
                "secret_actions": {"cloudflare_api_token": {"action": "replace", "value": "new-cloudflare-secret"}},
            }))
        self.assertTrue(caught.exception.rollback_succeeded)
        self.assertEqual(self.paths.env_file.read_bytes(), before_env)
        self.assertFalse(self.paths.cloudflare_token_file.exists())
        self.assertEqual(self.systemd.configuration, before_timer)

    def test_success_writes_secret_free_revision_signal(self) -> None:
        base = self.manager.snapshot()
        result = self.manager.apply(ChangeRequest.from_payload({
            "base_revision": base.revision,
            "changes": {"operandi": "classic"},
            "base_values": {"operandi": "story"},
            "secret_actions": {},
        }))
        signal = self.paths.state_file.read_text(encoding="utf-8")
        self.assertIn(result.revision, signal)
        self.assertNotIn("original-openai-secret", signal)

    def test_failed_non_timer_change_rolls_back_files_without_touching_systemd(self) -> None:
        before = self.paths.env_file.read_bytes()
        manager = SettingsManager(
            self.paths,
            systemd=self.systemd,
            validator=lambda values: (_ for _ in ()).throw(RuntimeError("invalid website value")),
        )
        base = manager.snapshot()
        with self.assertRaises(SettingsApplyFailure):
            manager.apply(ChangeRequest.from_payload({
                "base_revision": base.revision,
                "changes": {"site_title": "Rejected"},
                "base_values": {"site_title": "Original"},
                "secret_actions": {},
            }))
        self.assertEqual(self.paths.env_file.read_bytes(), before)
        self.assertEqual(self.systemd.apply_calls, 0)
        self.assertEqual(self.systemd.restore_calls, 0)

    def test_schema_validation_failure_occurs_before_backup_or_systemd_mutation(self) -> None:
        base = self.manager.snapshot()
        before = self.paths.env_file.read_bytes()
        with self.assertRaises(SettingsValidationFailure):
            self.manager.apply(ChangeRequest.from_payload({
                "base_revision": base.revision,
                "changes": {"generation_interval_minutes": 29},
                "base_values": {"generation_interval_minutes": 120},
                "secret_actions": {},
            }))
        self.assertEqual(self.paths.env_file.read_bytes(), before)
        self.assertEqual(self.systemd.apply_calls, 0)
        self.assertEqual(self.systemd.restore_calls, 0)
```

Add a separate lock test that opens `settings.lock`, takes `fcntl.LOCK_EX | fcntl.LOCK_NB`, constructs a manager with `lock_timeout_seconds=0.05`, and asserts `snapshot()` raises `SettingsLockBusy` without changing any file.

Use this exact test body inside the same class:

```python
def test_busy_lock_times_out_without_touching_configuration(self) -> None:
    import fcntl

    self.paths.lock_file.parent.mkdir(parents=True, exist_ok=True)
    before = self.paths.env_file.read_bytes()
    with self.paths.lock_file.open("a+b") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        manager = SettingsManager(
            self.paths, systemd=self.systemd, validator=lambda values: None, lock_timeout_seconds=0.05,
        )
        with self.assertRaises(SettingsLockBusy):
            manager.snapshot()
    self.assertEqual(self.paths.env_file.read_bytes(), before)
```

- [x] **Step 2: Run the focused tests and verify the missing module fails**

Run: `python -m unittest tests.platform.test_settings_transaction -v`

Expected: `ERROR` with `ModuleNotFoundError` for `settings`.

- [x] **Step 3: Define the exact request, snapshot, paths, and failure types**

```python
@dataclass(frozen=True, slots=True)
class SettingsPaths:
    env_file: Path
    cloudflare_token_file: Path
    timer_dropin: Path
    lock_file: Path
    state_file: Path
    generator_root: Path
    platform_state: Path
    publication_catalog: Path
    hub_outbox: Path

    @classmethod
    def for_home(cls, home: Path) -> "SettingsPaths":
        home = Path(home)
        return cls(
            env_file=home / ".config/wirtelprimpf/openai.env",
            cloudflare_token_file=home / ".config/cloudflare/api-token.env",
            timer_dropin=home / ".config/systemd/user/wirtelprimpf.timer.d/override.conf",
            lock_file=home / ".config/wirtelprimpf/settings.lock",
            state_file=home / ".config/wirtelprimpf/settings-state.json",
            generator_root=home / ".local/share/wirtelprimpf-generator",
            platform_state=home / ".local/state/wirtelprimpf/platform-state.json",
            publication_catalog=home / ".local/share/wirtelprimpf-generator/data/publication-catalog.json",
            hub_outbox=home / ".local/state/wirtelprimpf/hub-dispatch.json",
        )


@dataclass(frozen=True, slots=True)
class SecretAction:
    action: Literal["replace", "delete"]
    value: str | None = None


@dataclass(frozen=True, slots=True)
class ChangeRequest:
    base_revision: str
    changes: dict[str, object]
    base_values: dict[str, object]
    secret_actions: dict[str, SecretAction]

    @classmethod
    def from_payload(cls, payload: object) -> "ChangeRequest":
        if not isinstance(payload, dict) or set(payload) != {"base_revision", "changes", "base_values", "secret_actions"}:
            raise SettingsValidationFailure("settings request has an invalid envelope")
        base_revision = payload["base_revision"]
        changes = payload["changes"]
        base_values = payload["base_values"]
        actions = payload["secret_actions"]
        if not isinstance(base_revision, str) or not re.fullmatch(r"[0-9a-f]{64}", base_revision):
            raise SettingsValidationFailure("base_revision must be a 64-character opaque revision")
        if not isinstance(changes, dict) or not isinstance(base_values, dict) or set(base_values) != set(changes):
            raise SettingsValidationFailure("base_values must match sparse change fields exactly")
        if not isinstance(actions, dict) or set(actions) - {"openai_api_key", "cloudflare_api_token"}:
            raise SettingsValidationFailure("secret_actions contains an unknown secret")
        parsed_actions = _parse_secret_actions(actions)
        return cls(base_revision, dict(changes), dict(base_values), parsed_actions)
```

Define the snapshot with this exact public surface:

```python
@dataclass(frozen=True, slots=True)
class SettingsSnapshot:
    schema_version: str
    revision: str
    settings: dict[str, object]
    choices: dict[str, list[object]]
    secrets: dict[str, bool]
    invariants: dict[str, object]
    warnings: tuple[str, ...]

    def to_public_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "revision": self.revision,
            "settings": dict(self.settings),
            "choices": {key: list(values) for key, values in self.choices.items()},
            "secrets": dict(self.secrets),
            "invariants": dict(self.invariants),
            "warnings": list(self.warnings),
        }
```

Secret entries are booleans ending in `_present`.

Define the failures with this exact public surface:

```python
class SettingsError(RuntimeError):
    pass


class SettingsValidationFailure(SettingsError):
    pass


class SettingsLockBusy(SettingsError):
    pass


class SettingsConflict(SettingsError):
    def __init__(self, fields: tuple[str, ...], snapshot: SettingsSnapshot) -> None:
        self.fields = tuple(sorted(fields))
        self.snapshot = snapshot
        super().__init__(f"settings conflict: {', '.join(self.fields)}")


class SettingsApplyFailure(SettingsError):
    def __init__(self, phase: str, *, rollback_succeeded: bool) -> None:
        self.phase = phase
        self.rollback_succeeded = rollback_succeeded
        super().__init__(phase)
```

Only fixed redacted phase strings such as `settings transaction failed` may be supplied to `SettingsApplyFailure`; never command output, exception text, or values. `SettingsConflict` exposes field names and the already redacted public snapshot only.

- [x] **Step 4: Implement locking, revision generation, sparse conflict checks, and transaction order**

Use shared locks for snapshots and exclusive locks for updates. The retry loop uses `time.monotonic()`, sleeps at most 20 ms between `fcntl.flock(... LOCK_NB)` attempts, and raises `SettingsLockBusy` at the configured deadline.

Build the opaque revision exactly from a canonical JSON object and never include secret values:

```python
revision_source = {
    "settings": normalized_settings,
    "secret_presence": secret_presence,
    "files": {
        name: {"exists": fingerprint.exists, "inode": fingerprint.inode, "size": fingerprint.size, "mtime_ns": fingerprint.mtime_ns}
        for name, fingerprint in file_fingerprints.items()
    },
    "timer": timer_observation.revision_dict(),
}
revision = hashlib.sha256(
    json.dumps(revision_source, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()
```

The central apply method follows this control flow:

```python
def apply(self, request: ChangeRequest) -> SettingsSnapshot:
    with self._lock(exclusive=True):
        before = self._read_snapshot_unlocked()
        conflicts = tuple(
            sorted(key for key, base_value in request.base_values.items() if before.settings.get(key) != base_value)
        )
        if request.secret_actions and request.base_revision != before.revision:
            raise SettingsConflict(tuple(sorted(request.secret_actions)), before)
        if conflicts:
            raise SettingsConflict(conflicts, before)
        try:
            validated = validate_changes(request.changes, before.settings)
        except SettingsValidationError as exc:
            raise SettingsValidationFailure(str(exc)) from None
        proposed = {**before.settings, **validated}
        backups = self._capture_backups()
        old_timer = self.systemd.observe_timer()
        timer_keys = {"generation_interval_minutes", "timer_enabled", "timer_randomized_delay_seconds", "timer_persistent"}
        timer_touched = False
        try:
            self._write_environment(validated, proposed, request.secret_actions)
            self._write_cloudflare_secret(request.secret_actions)
            self.validator(self._generator_environment(proposed))
            if timer_keys.intersection(validated):
                requested_timer = self._timer_configuration(proposed, old_timer)
                timer_touched = True
                effective_timer = self.systemd.apply_timer(requested_timer)
                self._require_effective_timer(requested_timer, effective_timer)
            result = self._read_snapshot_unlocked()
            self._write_revision_signal(result.revision)
            return self._read_snapshot_unlocked()
        except SettingsConflict:
            raise
        except Exception as exc:
            rollback_succeeded = self._rollback(backups, old_timer, timer_touched=timer_touched)
            raise SettingsApplyFailure("settings transaction failed", rollback_succeeded=rollback_succeeded) from exc
```

`_write_environment()` updates only environment-backed changed settings plus an OpenAI replace/delete action. If a legacy `CLOUDFLARE_API_TOKEN` key is present in the Wirtel file, it is preserved byte-for-byte and warning `legacy_cloudflare_token_in_wirtel_env` is returned. This plan neither copies nor deletes that legacy value automatically; a future explicit migration command needs its own test and approval. New Cloudflare replace/delete actions affect only the separate store.

The manager also enforces `Path(proposed["settings_path"]).expanduser() == self.paths.env_file`; an applet request cannot redirect later writes to an arbitrary path.

The real validator runs `<generator_root>/.venv/bin/wirtelprimpf-generator --check-config --json` with no shell, a 30-second timeout, `cwd=generator_root`, and an environment built from the newly parsed Wirtel file plus the current non-secret process environment. It requires return code 0 and a JSON object with `ok: true`, `mode: "check_config"`, and `exit_code: 0`. Its exception is redacted to `generator configuration validation failed`.

`_rollback()` restores every non-timer file that the transaction actually touched byte-for-byte. When `timer_touched` is true it delegates the drop-in and effective-state restore exactly once to `restore_timer(old_timer.configuration(), old_timer.active, backups.timer_dropin)`; it does not pre-restore or re-render that same drop-in. A failed ordinary website/generator-field transaction therefore performs zero mutating systemd calls. It returns `False` if any required restore or verification fails and does not hide the original error.

The revision excludes `settings.lock` and `settings-state.json` because both are coordination artifacts derived from the transaction. Including the signal file would create a self-referential revision that changes when written.

- [x] **Step 5: Run transaction tests, then inject a systemd failure and verify rollback**

Run: `python -m unittest tests.platform.test_settings_transaction tests.platform.test_settings_io tests.platform.test_systemd_user -v`

Expected: all tests pass, including a test with `self.systemd.fail_apply = True` that leaves environment bytes, separate token bytes, drop-in bytes, enabled state, and active state unchanged.

- [x] **Step 6: Commit the transactional core**

```bash
git add wirtelprimpf_platform/settings.py tests/platform/test_settings_transaction.py
git commit -m "feat(settings): add revisioned transactional updates"
```

### Task 5: Stable JSON CLI for the applet

**Files:**
- Modify: `wirtelprimpf_platform/cli.py`
- Modify: `pyproject.toml`
- Create: `tests/platform/test_settings_cli.py`

**Interfaces:**
- Consumes: `SettingsManager`, `SettingsPaths`, and exception types from Task 4.
- Produces commands: `wirtelprimpf-settings snapshot` and `wirtelprimpf-settings apply`.
- `apply` consumes at most 64 KiB of UTF-8 JSON from standard input; no secret appears in argv.
- Produces exit codes: 0 success, 3 conflict, 4 validation, 5 lock busy, 6 application/rollback failure.
- Consumed by: Task 9.

- [x] **Step 1: Write failing snapshot, stdin, conflict, limit, and secret-redaction tests**

```python
from __future__ import annotations

import io
import json
import unittest
from unittest.mock import patch

from wirtelprimpf_platform import cli
from wirtelprimpf_platform.settings import SettingsConflict, SettingsSnapshot


def snapshot_for_test(*, revision: str, settings: dict[str, object]) -> SettingsSnapshot:
    return SettingsSnapshot(
        schema_version="2.0.0",
        revision=revision,
        settings=settings,
        choices={},
        secrets={"openai_api_key_present": False, "cloudflare_api_token_present": False, "github_auth_present": False},
        invariants={},
        warnings=(),
    )


class FakeManager:
    def __init__(self, snapshot: SettingsSnapshot) -> None:
        self.value = snapshot
        self.applied = None

    def snapshot(self) -> SettingsSnapshot:
        return self.value

    def apply(self, request):
        self.applied = request
        return self.value


class SettingsCLITests(unittest.TestCase):
    def test_apply_reads_sparse_request_from_stdin_and_prints_only_public_snapshot(self) -> None:
        snapshot = snapshot_for_test(revision="a" * 64, settings={"operandi": "both"})
        manager = FakeManager(snapshot)
        request = {
            "base_revision": "a" * 64,
            "changes": {"operandi": "both"},
            "base_values": {"operandi": "story"},
            "secret_actions": {"openai_api_key": {"action": "replace", "value": "never-print-this-secret"}},
        }
        output = io.StringIO()
        with patch.object(cli, "build_settings_manager", return_value=manager), patch("sys.stdin", io.StringIO(json.dumps(request))), patch("sys.stdout", output):
            code = cli.settings_main(["apply"])
        self.assertEqual(code, 0)
        self.assertEqual(manager.applied.changes, {"operandi": "both"})
        self.assertNotIn("never-print-this-secret", output.getvalue())

    def test_oversized_stdin_is_rejected_before_json_parsing(self) -> None:
        with patch("sys.stdin", io.StringIO("x" * (64 * 1024 + 1))):
            self.assertEqual(cli.settings_main(["apply"]), 4)
```

Add these exact exception-to-exit-code assertions; extend the imports with `SettingsApplyFailure`, `SettingsLockBusy`, and `SettingsValidationFailure`:

```python
def test_exception_exit_codes_are_stable_and_redacted(self) -> None:
    snapshot = snapshot_for_test(revision="a" * 64, settings={"operandi": "story"})
    cases = (
        (SettingsConflict(("operandi",), snapshot), 3, "conflict"),
        (SettingsValidationFailure("invalid field"), 4, "invalid field"),
        (SettingsLockBusy("busy"), 5, "settings lock is busy"),
        (SettingsApplyFailure("failed", rollback_succeeded=True), 6, "settings transaction failed"),
    )
    for exception, expected_code, expected_error in cases:
        manager = FakeManager(snapshot)
        manager.apply = lambda request, error=exception: (_ for _ in ()).throw(error)
        output = io.StringIO()
        valid_request = json.dumps({
            "base_revision": "a" * 64, "changes": {}, "base_values": {}, "secret_actions": {},
        })
        with patch.object(cli, "build_settings_manager", return_value=manager), patch("sys.stdin", io.StringIO(valid_request)), patch("sys.stdout", output):
            code = cli.settings_main(["apply"])
        self.assertEqual(code, expected_code)
        self.assertEqual(json.loads(output.getvalue())["error"], expected_error)
```

The 3/conflict JSON body additionally contains `conflicts` and `snapshot`; application failure exposes only `rollback_succeeded` beyond the fixed error.

- [x] **Step 2: Run the focused tests and verify parser/entrypoint failures**

Run: `python -m unittest tests.platform.test_settings_cli -v`

Expected: failures because `settings_main`, the nested parser, and the console script do not exist.

- [x] **Step 3: Add nested settings commands and the stable console script**

Add to `pyproject.toml`:

```toml
wirtelprimpf-settings = "wirtelprimpf_platform.cli:settings_entrypoint"

[tool.setuptools.package-data]
wirtelprimpf_platform = ["static/*.html", "static/*.css", "static/*.mjs"]
```

Keep the existing `Sourcecode` package-data entry in the same table.

Add this exact CLI shape:

```python
def _add_settings_parser(subparsers: argparse._SubParsersAction) -> None:
    settings = subparsers.add_parser("settings", help="transactional local settings JSON bridge")
    settings_subcommands = settings.add_subparsers(dest="settings_command", required=True)
    settings_subcommands.add_parser("snapshot", help="print one public settings snapshot")
    settings_subcommands.add_parser("apply", help="apply one sparse JSON request from stdin")


def _build_settings_only_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wirtelprimpf-settings")
    subcommands = parser.add_subparsers(dest="settings_command", required=True)
    subcommands.add_parser("snapshot", help="print one public settings snapshot")
    subcommands.add_parser("apply", help="apply one sparse JSON request from stdin")
    return parser


def settings_main(argv: list[str] | None = None) -> int:
    command = _build_settings_only_parser().parse_args(argv)
    manager = build_settings_manager()
    try:
        if command.settings_command == "snapshot":
            _json({"ok": True, **manager.snapshot().to_public_dict()})
            return 0
        payload = _read_bounded_stdin(64 * 1024)
        request = ChangeRequest.from_payload(json.loads(payload))
        _json({"ok": True, **manager.apply(request).to_public_dict()})
        return 0
    except SettingsConflict as exc:
        _json({"ok": False, "error": "conflict", "conflicts": list(exc.fields), "snapshot": exc.snapshot.to_public_dict()})
        return 3
    except (UnicodeError, json.JSONDecodeError, SettingsValidationFailure) as exc:
        _json({"ok": False, "error": str(exc)})
        return 4
    except SettingsLockBusy:
        _json({"ok": False, "error": "settings lock is busy"})
        return 5
    except SettingsApplyFailure as exc:
        _json({"ok": False, "error": "settings transaction failed", "rollback_succeeded": exc.rollback_succeeded})
        return 6


def settings_entrypoint() -> int:
    return settings_main(sys.argv[1:])
```

`build_settings_manager()` uses `SettingsPaths.for_home(Path.home())`, the real `SystemdUserManager`, and the bounded generator validator. The existing `wirtelprimpf-platform` command receives the same `settings` subparser for diagnostics; both entrypoints call the same functions.

- [x] **Step 4: Run CLI and packaging regressions**

Run: `python -m unittest tests.platform.test_settings_cli tests.platform.test_settings_transaction -v`

Run: `python -m pip install --no-deps -e . && .venv/bin/wirtelprimpf-settings --help >/dev/null`

Expected: tests pass; the installed command exposes the stable settings CLI without touching live configuration. JSON and secret-redaction behavior are covered by the injected-manager CLI tests above.

- [x] **Step 5: Commit the CLI unit**

```bash
git add pyproject.toml wirtelprimpf_platform/cli.py tests/platform/test_settings_cli.py
git commit -m "feat(settings): expose the transactional JSON bridge"
```

### Task 6: Local operational-status collector

**Files:**
- Create: `wirtelprimpf_platform/operational_status.py`
- Create: `tests/platform/test_operational_status.py`

**Interfaces:**
- Consumes: Task 4 snapshots, Task 3 systemd observations, existing `StateStore`, naming functions, hub outbox, media manifest, hub source, and publication catalog.
- Produces: `OperationalStatusCollector.collect() -> dict[str, object]`.
- The returned object always contains `schema_version`, `observed_at`, `health`, `configuration`, `generator`, `timer`, `story`, `archive`, `rotation`, `publication`, `auth`, `warnings`, and `errors`.
- Consumed by: Task 7.

- [x] **Step 1: Write failing complete, degraded, timeout, and no-network tests**

```python
from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from wirtelprimpf_platform.operational_status import OperationalStatusCollector, StatusPaths
from wirtelprimpf_platform.settings import SettingsSnapshot
from wirtelprimpf_platform.state import PlatformState, StateStore
from wirtelprimpf_platform.systemd_user import TimerConfiguration, TimerObservation


def snapshot_for_test(*, revision: str, settings: dict[str, object]) -> SettingsSnapshot:
    return SettingsSnapshot(
        schema_version="2.0.0", revision=revision, settings=settings, choices={},
        secrets={"openai_api_key_present": False, "cloudflare_api_token_present": False, "github_auth_present": False},
        invariants={}, warnings=(),
    )


class OperationalStatusTests(unittest.TestCase):
    def test_local_state_builds_real_story_book_archive_and_timer_status(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = StatusPaths.for_root(root)
            StateStore(paths.platform_state).save(PlatformState(completed_volumes=1, current_volume=2, active_archive_index=1))
            paths.hub_source.parent.mkdir(parents=True, exist_ok=True)
            paths.hub_source.write_text(json.dumps({
                "schema_version": "1.0.0", "current_volume": 2, "repository": "Wirtelprimpf-0001",
                "revision": "a" * 40, "story_path": "Wirtelprimpf/Wirtelprimpf_Story_II.md",
            }), encoding="utf-8")
            snapshot = snapshot_for_test(revision="b" * 64, settings={"repo_path": str(root / "archive")})
            timer = TimerObservation.from_configuration(TimerConfiguration(True, 120, 120, True), active=True)
            collector = OperationalStatusCollector(
                paths=paths,
                snapshot_reader=lambda: snapshot,
                timer_reader=lambda: timer,
                service_reader=lambda: {"active_state": "inactive", "result": "success", "exec_main_status": 0},
                clock=lambda: datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
            )
            status = collector.collect()
        self.assertEqual(status["health"], "ok")
        self.assertEqual(status["story"]["current_volume"], 2)
        self.assertEqual(status["story"]["book"], 1)
        self.assertEqual(status["story"]["story_in_book"], 2)
        self.assertEqual(status["archive"]["repository"], "Wirtelprimpf-0001")
        self.assertEqual(status["timer"]["interval_minutes"], 120)

    def test_one_broken_local_source_is_degraded_and_explicitly_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = StatusPaths.for_root(root)
            paths.platform_state.parent.mkdir(parents=True, exist_ok=True)
            paths.platform_state.write_text("{broken", encoding="utf-8")
            snapshot = snapshot_for_test(revision="b" * 64, settings={})
            timer = TimerObservation.from_configuration(TimerConfiguration(True, 120, 120, True), active=True)
            collector = OperationalStatusCollector(
                paths=paths,
                snapshot_reader=lambda: snapshot,
                timer_reader=lambda: timer,
                service_reader=lambda: {"active_state": "inactive", "result": "success", "exec_main_status": 0},
                clock=lambda: datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
            )
            status = collector.collect()
        self.assertEqual(status["health"], "degraded")
        self.assertIsNone(status["story"]["current_volume"])
        self.assertEqual(status["story"]["state"], "unknown")
        self.assertNotIn("token", json.dumps(status).lower())

    def test_collector_never_invokes_network_clients(self) -> None:
        forbidden = {"curl", "wget", "gh", "wrangler"}
        commands: list[list[str]] = []
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = StatusPaths.for_root(root)
            StateStore(paths.platform_state).save(PlatformState())
            snapshot = snapshot_for_test(revision="b" * 64, settings={})
            timer = TimerObservation.from_configuration(TimerConfiguration(True, 120, 120, True), active=True)
            collector = OperationalStatusCollector(
                paths=paths,
                snapshot_reader=lambda: snapshot,
                timer_reader=lambda: timer,
                service_reader=lambda: {"active_state": "inactive", "result": "success", "exec_main_status": 0},
                local_runner=lambda command, timeout: commands.append(command),
                clock=lambda: datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
            )
            collector.collect()
        self.assertTrue(all(command[0] not in forbidden for command in commands))
```

Add this service-reader timeout test:

```python
def test_service_timeout_is_redacted_and_degraded(self) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        paths = StatusPaths.for_root(Path(temporary))
        StateStore(paths.platform_state).save(PlatformState())
        snapshot = snapshot_for_test(revision="b" * 64, settings={})
        timer = TimerObservation.from_configuration(TimerConfiguration(True, 120, 120, True), active=True)
        def timed_out():
            raise subprocess.TimeoutExpired(["systemctl", "--user", "show"], 2)
        collector = OperationalStatusCollector(
            paths=paths, snapshot_reader=lambda: snapshot, timer_reader=lambda: timer,
            service_reader=timed_out, clock=lambda: datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
        )
        status = collector.collect()
    self.assertEqual(status["health"], "degraded")
    self.assertEqual(status["generator"]["active_state"], "unknown")
    self.assertEqual(status["errors"], [{"source": "generator_service", "message": "local source unavailable"}])
```

Import `subprocess` in the test file.

- [x] **Step 2: Run the focused tests and verify the missing module fails**

Run: `python -m unittest tests.platform.test_operational_status -v`

Expected: `ERROR` with `ModuleNotFoundError` for `operational_status`.

- [x] **Step 3: Implement fixed-shape partial-source aggregation**

Define status paths explicitly so tests never inspect the developer's real home:

```python
@dataclass(frozen=True, slots=True)
class StatusPaths:
    platform_state: Path
    hub_outbox: Path
    hub_source: Path
    media_manifest: Path
    publication_catalog: Path
    github_hosts: Path
    cloudflare_token: Path

    @classmethod
    def for_home(cls, home: Path) -> "StatusPaths":
        generator = Path(home) / ".local/share/wirtelprimpf-generator"
        state = Path(home) / ".local/state/wirtelprimpf"
        return cls(
            platform_state=state / "platform-state.json",
            hub_outbox=state / "hub-dispatch.json",
            hub_source=generator / "data/hub-source.json",
            media_manifest=generator / "data/media-manifest.json",
            publication_catalog=generator / "data/publication-catalog.json",
            github_hosts=Path(home) / ".config/gh/hosts.yml",
            cloudflare_token=Path(home) / ".config/cloudflare/api-token.env",
        )

    @classmethod
    def for_root(cls, root: Path) -> "StatusPaths":
        return cls.for_home(Path(root))
```

Use this exact top-level shape:

```python
status = {
    "schema_version": "1.0.0",
    "observed_at": self.clock().astimezone(UTC).isoformat().replace("+00:00", "Z"),
    "health": "ok",
    "configuration": {"revision": None, "valid": None, "drift": [], "state": "unknown"},
    "generator": {"active_state": "unknown", "sub_state": "unknown", "result": "unknown", "exec_main_status": None, "last_run": None},
    "timer": {"enabled": None, "active": None, "interval_minutes": None, "randomized_delay_seconds": None, "persistent": None, "last_trigger": None, "next_run": None},
    "story": {"state": "unknown", "completed_volumes": None, "current_volume": None, "book": None, "story_in_book": None, "stories_per_book": 10},
    "archive": {"index": None, "repository": None},
    "rotation": {"blocked": None, "target": None, "phase": None},
    "publication": {
        "git": {"state": "unknown", "value": None, "observed_at": None, "source": None},
        "release": {"state": "unknown", "value": None, "observed_at": None, "source": None},
        "hub": {"state": "unknown", "value": None, "observed_at": None, "source": None},
        "pages": {"state": "unknown", "value": None, "observed_at": None, "source": None},
        "dns": {"state": "unknown", "value": None, "observed_at": None, "source": None},
    },
    "auth": {"openai_present": False, "github_present": False, "cloudflare_present": False},
    "warnings": [],
    "errors": [],
}
```

Populate sources independently through `_collect_source(name, target, reader)`. That helper catches `OSError`, `RuntimeError`, `ValueError`, JSON errors, and subprocess timeouts; it appends `{"source": name, "message": "local source unavailable"}` and marks health degraded. It never copies exception text that may contain file content or command output.

Local sources and freshness are:

- settings snapshot and its revision signal mtime;
- `systemctl --user show wirtelprimpf.service` with `ActiveState`, `SubState`, `Result`, `ExecMainStatus`, `InactiveExitTimestamp`, and a 2-second timeout;
- Task 3 timer observation;
- `StateStore(platform_state)` plus `book_target_for_story(current_volume)`;
- local `git -C <repo_path> rev-parse HEAD` with a 2-second timeout and no fetch;
- newest local `release_tag` in `media-manifest.json`, using file mtime;
- pending `hub-dispatch.json`, or otherwise `data/hub-source.json`, using file mtime;
- active verified publication-catalog entry as the last persisted Pages/DNS observation; no entry means unknown;
- authentication presence only from the Wirtel environment, `~/.config/gh/hosts.yml`, and the separate Cloudflare token file.

If the catalog marks an archive verified, set both Pages and DNS to `state: "verified"`, value to its canonical URL/domain, and source to `publication-catalog.json`. Do not claim freshness later than the catalog mtime.

- [x] **Step 4: Run status, state, hub, and catalog regressions**

Run: `python -m unittest tests.platform.test_operational_status tests.platform.test_naming_state tests.platform.test_hub tests.platform.test_provisioning -v`

Expected: all tests pass; the fake runner records no network-capable command.

- [x] **Step 5: Commit the status collector**

```bash
git add wirtelprimpf_platform/operational_status.py tests/platform/test_operational_status.py
git commit -m "feat(status): collect redacted local operations state"
```

### Task 7: Admin API separation and transactional HTTP contract

**Files:**
- Modify: `wirtelprimpf_platform/admin.py`
- Modify: `wirtelprimpf_platform/cli.py`
- Modify: `tests/platform/test_admin.py`

**Interfaces:**
- Consumes: `SettingsManager` from Task 4 and `OperationalStatusCollector` from Task 6.
- Produces: `GET /api/settings`, `POST /api/settings`, and a structurally independent `GET /api/status`.
- Produces exact status mappings: 200 success, 409 conflict, 422 validation, 423 lock busy, 503 transaction failure, 500 only for an unusable status shell.
- Preserves the existing `AdminResponse`, loopback request checks, CSRF check, request-size cap, and security headers.
- Consumed by: Task 8.

- [x] **Step 1: Replace old alias tests with failing API-contract tests**

Update the fixture to inject a real temporary `SettingsManager` with fake systemd/validator and a fake collector. Add these assertions:

```python
def test_status_is_structurally_independent_from_settings(self) -> None:
    settings = json.loads(self.request("GET", "/api/settings").body)
    status = json.loads(self.request("GET", "/api/status").body)
    self.assertEqual(settings["schema_version"], "2.0.0")
    self.assertIn("revision", settings)
    self.assertIn("settings", settings)
    self.assertNotIn("generator", settings)
    self.assertEqual(status["schema_version"], "1.0.0")
    self.assertIn("generator", status)
    self.assertIn("timer", status)
    self.assertNotIn("settings", status)


def test_sparse_update_requires_revision_and_returns_fresh_snapshot(self) -> None:
    base = json.loads(self.request("GET", "/api/settings").body)
    response = self.request(
        "POST", "/api/settings",
        headers={"Origin": "http://127.0.0.1:8765", "X-Wirtelprimpf-CSRF": "csrf-token-for-tests"},
        body={
            "base_revision": base["revision"],
            "changes": {"operandi": "both"},
            "base_values": {"operandi": base["settings"]["operandi"]},
            "secret_actions": {},
        },
    )
    decoded = json.loads(response.body)
    self.assertEqual(response.status, 200)
    self.assertEqual(decoded["settings"]["operandi"], "both")
    self.assertNotEqual(decoded["revision"], base["revision"])


def test_same_field_conflict_is_409_and_returns_public_snapshot(self) -> None:
    base = json.loads(self.request("GET", "/api/settings").body)
    self.env_file.write_text(
        self.env_file.read_text(encoding="utf-8").replace("WIRTELPRIMPF_OPERANDI=story", "WIRTELPRIMPF_OPERANDI=classic"),
        encoding="utf-8",
    )
    response = self.request(
        "POST", "/api/settings",
        headers={"Origin": "http://127.0.0.1:8765", "X-Wirtelprimpf-CSRF": "csrf-token-for-tests"},
        body={
            "base_revision": base["revision"],
            "changes": {"operandi": "both"},
            "base_values": {"operandi": "story"},
            "secret_actions": {},
        },
    )
    decoded = json.loads(response.body)
    self.assertEqual(response.status, 409)
    self.assertEqual(decoded["conflicts"], ["operandi"])
    self.assertEqual(decoded["snapshot"]["settings"]["operandi"], "classic")
```

Retain and adapt every existing loopback, Host, Origin, CSRF, request-size, traversal, permissions, secret-redaction, and archive-boundary assertion. Add this explicit error mapping test using a small `RaisingSettingsManager` fixture whose `apply()` raises its stored exception:

```python
def test_validation_lock_and_apply_failures_have_distinct_status_codes(self) -> None:
    cases = (
        (SettingsValidationFailure("invalid field"), 422),
        (SettingsLockBusy("busy"), 423),
        (SettingsApplyFailure("failed", rollback_succeeded=True), 503),
    )
    body = {"base_revision": "a" * 64, "changes": {}, "base_values": {}, "secret_actions": {}}
    for failure, expected_status in cases:
        with self.subTest(expected_status=expected_status):
            application = AdminApplication(
                RaisingSettingsManager(failure), self.status_collector, csrf_token="csrf-token-for-tests",
            )
            response = application.handle(
                "POST", "/api/settings",
                {"Host": "127.0.0.1:8765", "Origin": "http://127.0.0.1:8765", "X-Wirtelprimpf-CSRF": "csrf-token-for-tests"},
                json.dumps(body).encode("utf-8"), client_host="127.0.0.1",
            )
            self.assertEqual(response.status, expected_status)
```

- [x] **Step 2: Run admin tests and verify old routing fails**

Run: `python -m unittest tests.platform.test_admin -v`

Expected: status-structure and sparse-envelope tests fail because `/api/status` aliases settings and POST still accepts a flat form.

- [x] **Step 3: Delegate routes without weakening transport security**

Change the application constructor and route core to this contract:

```python
class AdminApplication:
    def __init__(
        self,
        settings: SettingsManager,
        status: OperationalStatusCollector,
        *,
        csrf_token: str | None = None,
    ) -> None:
        self.settings = settings
        self.status = status
        self.csrf_token = csrf_token or secrets.token_urlsafe(32)

    def _get_settings(self) -> AdminResponse:
        try:
            return _json_response(200, {"ok": True, **self.settings.snapshot().to_public_dict()})
        except SettingsLockBusy:
            return _json_response(423, {"ok": False, "error": "settings lock is busy"})
        except SettingsError:
            return _json_response(500, {"ok": False, "error": "settings snapshot unavailable"})

    def _get_status(self) -> AdminResponse:
        try:
            return _json_response(200, self.status.collect())
        except Exception:
            return _json_response(500, {
                "schema_version": "1.0.0", "health": "error", "error": "operational status unavailable",
            })

    def _post_settings(self, body: bytes) -> AdminResponse:
        try:
            payload = json.loads(body.decode("utf-8"))
            request = ChangeRequest.from_payload(payload)
            snapshot = self.settings.apply(request)
            return _json_response(200, {"ok": True, **snapshot.to_public_dict()})
        except SettingsConflict as exc:
            return _json_response(409, {
                "ok": False, "error": "conflict", "conflicts": list(exc.fields),
                "snapshot": exc.snapshot.to_public_dict(),
            })
        except (UnicodeError, json.JSONDecodeError, SettingsValidationFailure) as exc:
            return _json_response(422, {"ok": False, "error": str(exc)})
        except SettingsLockBusy:
            return _json_response(423, {"ok": False, "error": "settings lock is busy"})
        except SettingsApplyFailure as exc:
            return _json_response(503, {
                "ok": False, "error": "settings transaction failed",
                "rollback_succeeded": exc.rollback_succeeded,
            })
```

`handle()` still rejects a non-local client before reading or parsing JSON, enforces `MAX_REQUEST_BYTES`, requires Origin and the constant-time CSRF token for POST, and returns 404 for every other path.

Update `serve_admin()` to receive both dependencies. Update `cli.admin_main` construction to use the same default `SettingsManager` and a collector that shares its snapshot/systemd dependencies.

- [x] **Step 4: Run API and security regressions**

Run: `python -m unittest tests.platform.test_admin tests.platform.test_settings_transaction tests.platform.test_operational_status -v`

Expected: all tests pass; serialized responses contain none of the fixture secrets.

- [x] **Step 5: Commit the API unit**

```bash
git add wirtelprimpf_platform/admin.py wirtelprimpf_platform/cli.py tests/platform/test_admin.py
git commit -m "feat(admin): separate settings and operational APIs"
```

### Task 8: Accessible web admin, shared dropdowns, live merge, and status card

**Files:**
- Create: `wirtelprimpf_platform/static/admin.html`
- Create: `wirtelprimpf_platform/static/admin.css`
- Create: `wirtelprimpf_platform/static/admin.mjs`
- Create: `tests/test_admin_ui.mjs`
- Modify: `wirtelprimpf_platform/admin.py`
- Modify: `tests/platform/test_admin.py`
- Modify: `Makefile`

**Interfaces:**
- Consumes: Task 7 JSON responses and Task 1 `choices` payload.
- Produces: exported `FormSyncState` with `change`, `markSecretDirty`, `mergeSnapshot`, `discard`, `discardSecret`, `buildRequest`, and `acceptSavedSnapshot`, plus `RequestEpochGate` for stale-response suppression.
- Produces: 2-second settings polling, 5-second status polling, in-flight guards, visible dirty/conflict text, and model `<select>` controls.
- Produces static routes `/assets/admin.css` and `/assets/admin.mjs`.
- Consumed behavior mirrored by: Task 9 applet state machine.

- [x] **Step 1: Write failing browser-state and fixed-route/security contracts**

```javascript
import assert from "node:assert/strict";
import test from "node:test";

import { FormSyncState, RequestEpochGate, modelOptions } from "../wirtelprimpf_platform/static/admin.mjs";

test("polling updates clean fields but preserves and marks a dirty conflict", () => {
  const state = new FormSyncState({ revision: "r1", settings: { operandi: "story", site_title: "Alt" } });
  state.change("site_title", "Mein Entwurf");
  const merged = state.mergeSnapshot({ revision: "r2", settings: { operandi: "both", site_title: "Extern" } });
  assert.equal(merged.operandi, "both");
  assert.equal(merged.site_title, "Mein Entwurf");
  assert.deepEqual([...state.dirty], ["site_title"]);
  assert.deepEqual([...state.conflicts], ["site_title"]);
});

test("request contains only dirty values and their original bases", () => {
  const state = new FormSyncState({ revision: "r1", settings: { operandi: "story", site_title: "Alt" } });
  state.change("site_title", "Neu");
  assert.deepEqual(state.buildRequest({ site_title: "Neu" }, {}), {
    base_revision: "r1",
    changes: { site_title: "Neu" },
    base_values: { site_title: "Alt" },
    secret_actions: {},
  });
});

test("legacy model remains visible without becoming a catalog choice", () => {
  assert.deepEqual(modelOptions(["gpt-5-mini", "gpt-4.1"], "retired-model"), [
    { value: "retired-model", label: "retired-model · konfiguriert · nicht mehr im empfohlenen Katalog", legacy: true },
    { value: "gpt-5-mini", label: "gpt-5-mini", legacy: false },
    { value: "gpt-4.1", label: "gpt-4.1", legacy: false },
  ]);
});

test("saved snapshot clears dirty and conflict state only after explicit acceptance", () => {
  const state = new FormSyncState({ revision: "r1", settings: { operandi: "story", site_title: "Alt" } });
  state.change("site_title", "Mein Entwurf");
  state.mergeSnapshot({ revision: "r2", settings: { operandi: "story", site_title: "Extern" } });
  assert.deepEqual([...state.dirty], ["site_title"]);
  assert.deepEqual([...state.conflicts], ["site_title"]);

  state.acceptSavedSnapshot({ revision: "r3", settings: { operandi: "story", site_title: "Mein Entwurf" } });

  assert.deepEqual([...state.dirty], []);
  assert.deepEqual([...state.conflicts], []);
  assert.equal(state.baseRevision, null);
  assert.deepEqual([...state.baseValues], []);
  assert.equal(state.revision, "r3");
});

test("secret actions remain separate from sparse non-secret changes", () => {
  const state = new FormSyncState({ revision: "r1", settings: { operandi: "story" } });
  state.change("operandi", "both");
  state.markSecretDirty("openai_api_key");
  const request = state.buildRequest(
    { operandi: "both" },
    { openai_api_key: { action: "replace", value: "test-secret-never-log" } },
  );
  assert.deepEqual(request.changes, { operandi: "both" });
  assert.equal(Object.hasOwn(request.changes, "openai_api_key"), false);
  assert.deepEqual(request.secret_actions, {
    openai_api_key: { action: "replace", value: "test-secret-never-log" },
  });
});

test("secret edit keeps its original base revision across polling", () => {
  const state = new FormSyncState({ revision: "r1", settings: { operandi: "story" } });
  state.markSecretDirty("cloudflare_api_token");
  state.mergeSnapshot({ revision: "r2", settings: { operandi: "both" } });
  const request = state.buildRequest({}, {
    cloudflare_api_token: { action: "replace", value: "test-secret-never-log" },
  });
  assert.equal(request.base_revision, "r1");
  assert.deepEqual([...state.secretDirty], ["cloudflare_api_token"]);
  state.discardSecret("cloudflare_api_token");
  assert.equal(state.baseRevision, null);
});

test("discard accepts the current server value and clears the field conflict", () => {
  const state = new FormSyncState({ revision: "r1", settings: { site_title: "Alt" } });
  state.change("site_title", "Mein Entwurf");
  state.mergeSnapshot({ revision: "r2", settings: { site_title: "Extern" } });
  assert.equal(state.discard("site_title"), "Extern");
  assert.deepEqual([...state.dirty], []);
  assert.deepEqual([...state.conflicts], []);
  assert.deepEqual([...state.baseValues], []);
  assert.equal(state.baseRevision, null);
});

test("poll response started before a save cannot overwrite the save result", () => {
  const gate = new RequestEpochGate();
  const pollEpoch = gate.beginPoll();
  assert.equal(pollEpoch, 0);
  gate.beginSave();
  assert.equal(gate.acceptPoll(pollEpoch), false);
  assert.equal(gate.beginPoll(), null);
  gate.endSave();
  assert.equal(gate.beginPoll(), 1);
});
```

Before modifying admin production code or assets, also add the two exact Python route/security tests printed in Step 5 to `tests/platform/test_admin.py`.

- [x] **Step 2: Run the Node test and verify the module is missing**

Run: `node --test tests/test_admin_ui.mjs`

Run: `python -m unittest tests.platform.test_admin -v`

Expected: the Node run reports `ERR_MODULE_NOT_FOUND` for `static/admin.mjs`; the Python run fails because fixed asset routes, strict CSP, and packaged dropdown markup do not exist yet.

- [x] **Step 3: Implement the pure browser state machine**

```javascript
export class FormSyncState {
  constructor(snapshot) {
    this.revision = snapshot.revision;
    this.server = structuredClone(snapshot.settings);
    this.visible = structuredClone(snapshot.settings);
    this.baseRevision = null;
    this.baseValues = new Map();
    this.dirty = new Set();
    this.secretDirty = new Set();
    this.conflicts = new Set();
  }

  change(name, value) {
    if (!this.dirty.has(name)) {
      this.baseRevision ??= this.revision;
      this.baseValues.set(name, this.server[name]);
      this.dirty.add(name);
    }
    this.visible[name] = value;
  }

  markSecretDirty(name) {
    this.baseRevision ??= this.revision;
    this.secretDirty.add(name);
  }

  mergeSnapshot(snapshot) {
    for (const [name, value] of Object.entries(snapshot.settings)) {
      if (this.dirty.has(name)) {
        if (!Object.is(value, this.baseValues.get(name))) this.conflicts.add(name);
        continue;
      }
      this.visible[name] = value;
    }
    this.server = structuredClone(snapshot.settings);
    this.revision = snapshot.revision;
    return structuredClone(this.visible);
  }

  discard(name) {
    if (!this.dirty.has(name)) return this.visible[name];
    this.visible[name] = this.server[name];
    this.dirty.delete(name);
    this.conflicts.delete(name);
    this.baseValues.delete(name);
    if (this.dirty.size === 0 && this.secretDirty.size === 0) this.baseRevision = null;
    return this.visible[name];
  }

  discardSecret(name) {
    this.secretDirty.delete(name);
    if (this.dirty.size === 0 && this.secretDirty.size === 0) this.baseRevision = null;
  }

  buildRequest(values, secretActions) {
    const changes = Object.fromEntries([...this.dirty].map((name) => [name, values[name]]));
    const base_values = Object.fromEntries([...this.dirty].map((name) => [name, this.baseValues.get(name)]));
    const actionNames = Object.keys(secretActions).sort();
    const dirtySecretNames = [...this.secretDirty].sort();
    if (actionNames.length !== dirtySecretNames.length || actionNames.some((name, index) => name !== dirtySecretNames[index])) {
      throw new TypeError("secret actions must match explicitly dirty secret controls");
    }
    return {
      base_revision: this.baseRevision ?? this.revision,
      changes,
      base_values,
      secret_actions: structuredClone(secretActions),
    };
  }

  acceptSavedSnapshot(snapshot) {
    this.revision = snapshot.revision;
    this.server = structuredClone(snapshot.settings);
    this.visible = structuredClone(snapshot.settings);
    this.baseRevision = null;
    this.baseValues.clear();
    this.dirty.clear();
    this.secretDirty.clear();
    this.conflicts.clear();
  }
}

export class RequestEpochGate {
  constructor() {
    this.epoch = 0;
    this.saveInFlight = false;
  }

  beginPoll() {
    return this.saveInFlight ? null : this.epoch;
  }

  acceptPoll(epoch) {
    return !this.saveInFlight && epoch === this.epoch;
  }

  beginSave() {
    this.saveInFlight = true;
    this.epoch += 1;
    return this.epoch;
  }

  endSave() {
    this.saveInFlight = false;
  }
}
```

`modelOptions()` prepends at most one legacy current value and never adds it to the received catalog.

- [x] **Step 4: Build the accessible HTML/CSS and DOM adapter**

`admin.html` contains an `aria-live="polite"` save-status region, a status card before the form, and these exact model controls:

```html
<meta name="csrf-token" content="__CSRF_TOKEN__">
<label for="image_model">Bildmodell</label>
<select id="image_model" name="image_model"></select>
<p class="field-state" id="image_model-state"></p>
<label for="story_model">Storymodell</label>
<select id="story_model" name="story_model"></select>
<p class="field-state" id="story_model-state"></p>
```

The status card has text nodes for overall health, last/next run, timer, book/story/repository, last result, and synchronization. Dirty fields receive class `is-dirty` and text `Ungespeichert`; externally changed dirty fields receive `has-conflict` and text `Extern geändert – Speichern prüft den Konflikt`. Color is supplementary only.

The browser bootstrap must:

```javascript
const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
let settingsInFlight = false;
let statusInFlight = false;
const requestGate = new RequestEpochGate();

async function pollSettings() {
  if (settingsInFlight) return;
  const requestEpoch = requestGate.beginPoll();
  if (requestEpoch === null) return;
  settingsInFlight = true;
  try {
    const response = await fetch("/api/settings", { cache: "no-store" });
    if (!response.ok) throw new Error("settings unavailable");
    const snapshot = await response.json();
    if (requestGate.acceptPoll(requestEpoch)) applySettingsSnapshot(snapshot);
  } finally {
    settingsInFlight = false;
  }
}

async function pollStatus() {
  if (statusInFlight) return;
  statusInFlight = true;
  try {
    const response = await fetch("/api/status", { cache: "no-store" });
    renderStatus(await response.json());
  } finally {
    statusInFlight = false;
  }
}

await pollSettings();
await pollStatus();
setInterval(pollSettings, 2000);
setInterval(pollStatus, 5000);
```

Immediately before starting a save, call `requestGate.beginSave()`; this invalidates every older in-flight poll response. In the save `finally`, call `requestGate.endSave()` and trigger one fresh `pollSettings()`. The save request sends `Content-Type: application/json` and `X-Wirtelprimpf-CSRF: csrfToken`. It never stores the token in local/session storage, never adds it to a URL, and never logs it. `admin.py` loads the packaged HTML and replaces the single `__CSRF_TOKEN__` marker with `html.escape(self.csrf_token, quote=True)` only for `GET /`; it does not expose the token through `/api/settings` or `/api/status`.

On HTTP 409, merge `data.snapshot`, retain local dirty values, and mark `data.conflicts`. On 422/423/503, retain every dirty value and show the redacted server message. After 200, clear secret inputs and delete checkboxes, then call `acceptSavedSnapshot()`.

Each write-only entry/delete toggle calls `markSecretDirty(secret_name)` on its first user change. Polling may update presence labels but never clears the secret input, its delete toggle, `secretDirty`, or the captured base revision. Clearing that local secret action calls `discardSecret(secret_name)`. This guarantees the server sees the revision from the beginning of the secret edit and can enforce its strict stale-secret rejection.

Each dirty/conflicting non-secret field exposes a keyboard-reachable `Externen Wert übernehmen` button that calls `discard(name)`, writes the returned server value into that control, and updates the textual state. The button never writes to the server; it only abandons that one local draft. A global `Alle lokalen Entwürfe verwerfen` action calls `discard` and `discardSecret` for every dirty field/action after one confirmation. Reloading the page is not the only conflict-resolution mechanism.

Serve assets with exact MIME types and no dynamic paths. Replace the embedded `ADMIN_HTML` constant. Tighten CSP to `default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'` without `unsafe-inline`.

Expose the fixed headers as `SECURITY_HEADERS: dict[str, str]` in `admin.py` and have `_Handler._dispatch()` iterate that mapping. This keeps the route tests and emitted HTTP headers on one source of truth.

- [x] **Step 5: Make the prewritten Python route/static/security tests green**

Add this concrete route/security test and retain the existing request-security cases:

```python
def test_admin_assets_are_fixed_local_routes_with_strict_csp(self) -> None:
    page = self.request("GET", "/")
    stylesheet = self.request("GET", "/assets/admin.css")
    script = self.request("GET", "/assets/admin.mjs")
    missing = self.request("GET", "/assets/../../openai.env")
    self.assertEqual(page.status, 200)
    self.assertIn('<meta name="csrf-token" content="csrf-token-for-tests">', page.body)
    self.assertNotIn("__CSRF_TOKEN__", page.body)
    self.assertIn('<select id="image_model" name="image_model">', page.body)
    self.assertIn('<select id="story_model" name="story_model">', page.body)
    self.assertIn('href="/assets/admin.css"', page.body)
    self.assertIn('src="/assets/admin.mjs"', page.body)
    self.assertEqual(stylesheet.content_type, "text/css; charset=utf-8")
    self.assertEqual(script.content_type, "text/javascript; charset=utf-8")
    self.assertEqual(missing.status, 404)

def test_http_handler_security_headers_disallow_inline_assets(self) -> None:
    csp = SECURITY_HEADERS["Content-Security-Policy"]
    self.assertEqual(csp, "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
    self.assertNotIn("unsafe-inline", csp)
    self.assertNotIn("https://", csp)
    self.assertEqual(SECURITY_HEADERS["Cache-Control"], "no-store")
    self.assertEqual(SECURITY_HEADERS["X-Frame-Options"], "DENY")
    self.assertEqual(SECURITY_HEADERS["X-Content-Type-Options"], "nosniff")
    self.assertEqual(SECURITY_HEADERS["Referrer-Policy"], "no-referrer")
```

Import `SECURITY_HEADERS` from `admin.py`; `_Handler._dispatch()` iterates this exact mapping so the tested values are the emitted values.

- [x] **Step 6: Run UI, API, and packaging tests**

Run: `node --test tests/test_admin_ui.mjs`

Run: `python -m unittest tests.platform.test_admin -v`

Run: `python -m build --wheel --no-isolation` only if the `build` module is already installed; otherwise run `python -m pip install --no-deps -e .` and verify `importlib.resources.files("wirtelprimpf_platform").joinpath("static/admin.html").is_file()`.

Expected: all tests pass and installed package resources resolve.

- [x] **Step 7: Add the Node contract to `make check` and commit**

Add `node --test tests/test_admin_ui.mjs` after the existing applet runtime test.

```bash
git add wirtelprimpf_platform/static wirtelprimpf_platform/admin.py tests/test_admin_ui.mjs tests/platform/test_admin.py Makefile
git commit -m "feat(admin): add conflict-safe live settings UI"
```

### Task 9: Cinnamon applet JSON client, shared dropdowns, and live conflict protection

> **Testing-quality correction (1 August 2026):** The source-string assertions
> printed later in this task are retained only as historical drafting evidence and
> are superseded. Implement the monitor/debounce/focus/fallback behavior behind a
> small importable coordinator with injected scheduler, monitor, executor, and
> completion-dispatch adapters. Tests must drive that coordinator with fakes and
> assert observable coalescing, epoch rejection, dirty-field preservation,
> cancellation, and off-thread execution. A minimal import/packaging smoke may
> inspect symbols, but grep-like assertions about method names or exact source text
> are not acceptance evidence.

**Files:**
- Create: `files/wirtelprimfgenerator@H234598/settings_sync.py`
- Create: `tests/test_applet_settings_sync.py`
- Modify: `files/wirtelprimfgenerator@H234598/SettingsLogo.py`
- Modify: `tests/test_settings_schema.py`
- Modify: `Makefile`

**Interfaces:**
- Consumes: `~/.local/share/wirtelprimpf-generator/.venv/bin/wirtelprimpf-settings` from Task 5.
- Produces: `SettingsCliClient.snapshot()` and `.apply(request)` using bounded subprocess calls and JSON stdin.
- Produces: `DirtySnapshotState` with the same base/dirty/conflict semantics as Task 8.
- Runs every blocking CLI invocation on one private worker thread; GTK/Gio widgets remain main-thread-only and are updated through `GLib.idle_add`.
- `GeneratorConfigEditor` monitors environment, timer drop-in, revision signal, and parent directories via Gio; it never writes configuration files directly.

- [x] **Step 1: Write failing pure client/state tests and the static GTK contracts from Step 6**

```python
from __future__ import annotations

import json
import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SYNC_PATH = ROOT / "files" / "wirtelprimfgenerator@H234598" / "settings_sync.py"
SPEC = importlib.util.spec_from_file_location("wirtelprimpf_applet_settings_sync_test", SYNC_PATH)
assert SPEC is not None and SPEC.loader is not None
SYNC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SYNC)
DirtySnapshotState = SYNC.DirtySnapshotState
SettingsCliClient = SYNC.SettingsCliClient


class AppletSettingsSyncTests(unittest.TestCase):
    def test_dirty_state_keeps_local_value_and_marks_external_conflict(self) -> None:
        state = DirtySnapshotState({"revision": "r1", "settings": {"operandi": "story", "image_model": "gpt-image-2"}})
        state.change("image_model", "gpt-image-1.5")
        visible = state.merge_snapshot({"revision": "r2", "settings": {"operandi": "both", "image_model": "gpt-image-1"}})
        self.assertEqual(visible["operandi"], "both")
        self.assertEqual(visible["image_model"], "gpt-image-1.5")
        self.assertEqual(state.conflicts, {"image_model"})

    def test_cli_apply_sends_secret_json_on_stdin_not_argv(self) -> None:
        calls = []
        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return subprocess.CompletedProcess(command, 0, json.dumps({"ok": True, "revision": "b" * 64, "settings": {}}), "")
        client = SettingsCliClient(
            "/trusted/wirtelprimpf-settings", runner=runner, executable_check=lambda _path: True,
        )
        client.apply({
            "base_revision": "a" * 64, "changes": {}, "base_values": {},
            "secret_actions": {"openai_api_key": {"action": "replace", "value": "private-secret-value"}},
        })
        command, kwargs = calls[0]
        self.assertNotIn("private-secret-value", " ".join(command))
        self.assertIn("private-secret-value", kwargs["input"])
        self.assertEqual(kwargs["timeout"], 90)
        self.assertFalse(kwargs["shell"])

    def test_snapshot_uses_the_short_read_timeout(self) -> None:
        calls = []
        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return subprocess.CompletedProcess(
                command, 0, json.dumps({"ok": True, "revision": "b" * 64, "settings": {}}), "",
            )
        client = SettingsCliClient(
            "/trusted/wirtelprimpf-settings", runner=runner, executable_check=lambda _path: True,
        )
        client.snapshot()
        self.assertEqual(calls[0][1]["timeout"], 10)

    def test_nonzero_invalid_and_oversized_cli_responses_fail_closed(self) -> None:
        cases = (
            (subprocess.CompletedProcess(["cli"], 3, json.dumps({"ok": False, "error": "conflict"}), ""), "conflict"),
            (subprocess.CompletedProcess(["cli"], 0, "not-json", ""), "gültiges JSON"),
            (subprocess.CompletedProcess(["cli"], 0, "[]", ""), "JSON-Objekt"),
            (subprocess.CompletedProcess(["cli"], 0, "x" * (1024 * 1024 + 1), ""), "zu groß"),
        )
        for result, message in cases:
            client = SettingsCliClient(
                "/trusted/wirtelprimpf-settings",
                runner=lambda command, **kwargs: result,
                executable_check=lambda _path: True,
            )
            with self.subTest(message=message), self.assertRaisesRegex(SYNC.SettingsCliError, message):
                client.snapshot()

    def test_saved_snapshot_clears_dirty_state_and_sparse_request_keeps_bases(self) -> None:
        state = DirtySnapshotState({"revision": "r1", "settings": {"operandi": "story", "image_model": "gpt-image-2"}})
        state.change("operandi", "both")
        self.assertEqual(state.build_request({"operandi": "both"}, {}), {
            "base_revision": "r1", "changes": {"operandi": "both"},
            "base_values": {"operandi": "story"}, "secret_actions": {},
        })
        state.accept_saved_snapshot({"revision": "r2", "settings": {"operandi": "both", "image_model": "gpt-image-2"}})
        self.assertEqual(state.dirty, set())
        self.assertEqual(state.conflicts, set())

    def test_discard_accepts_server_value_and_clears_one_conflict(self) -> None:
        state = DirtySnapshotState({"revision": "r1", "settings": {"story_model": "gpt-5-mini"}})
        state.change("story_model", "gpt-5.4-mini")
        state.merge_snapshot({"revision": "r2", "settings": {"story_model": "gpt-5.5"}})
        self.assertEqual(state.discard("story_model"), "gpt-5.5")
        self.assertEqual(state.dirty, set())
        self.assertEqual(state.conflicts, set())
        self.assertEqual(state.base_values, {})
        self.assertIsNone(state.base_revision)

    def test_secret_edit_keeps_original_revision_across_refresh(self) -> None:
        state = DirtySnapshotState({"revision": "r1", "settings": {"operandi": "story"}})
        state.mark_secret_dirty("openai_api_key")
        state.merge_snapshot({"revision": "r2", "settings": {"operandi": "both"}})
        request = state.build_request({}, {
            "openai_api_key": {"action": "replace", "value": "private-secret-value"},
        })
        self.assertEqual(request["base_revision"], "r1")
        self.assertEqual(state.secret_dirty, {"openai_api_key"})
        state.discard_secret("openai_api_key")
        self.assertIsNone(state.base_revision)

    def test_default_executable_check_rejects_relative_missing_and_symlink_paths(self) -> None:
        with self.assertRaisesRegex(SYNC.SettingsCliError, "absolut"):
            SettingsCliClient("relative/wirtelprimpf-settings")
        with self.assertRaisesRegex(SYNC.SettingsCliError, "vertrauenswürdige"):
            SettingsCliClient("/definitely/missing/wirtelprimpf-settings")
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "real-cli"
            target.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            os.chmod(target, 0o700)
            link = Path(temporary) / "linked-cli"
            link.symlink_to(target)
            with self.assertRaisesRegex(SYNC.SettingsCliError, "vertrauenswürdige"):
                SettingsCliClient(str(link))
```

The committed test uses the loader above because `@` prevents package import syntax.

Before touching either production file, also replace the superseded assertions in `tests/test_settings_schema.py` with the exact three tests printed in Step 6. This makes the no-direct-writer, shared-catalog, Gio timing, and off-main-thread contracts red in the same test-first phase.

- [x] **Step 2: Run the focused tests and verify the helper is missing**

Run: `python -m unittest tests.test_applet_settings_sync tests.test_settings_schema -v`

Expected: failure because `settings_sync.py` does not exist and the current applet still owns writers/catalogs and has no serialized worker bridge.

- [x] **Step 3: Implement the bounded pure helper**

```python
class SettingsCliError(RuntimeError):
    def __init__(self, message, *, payload=None):
        super().__init__(message)
        self.payload = payload if isinstance(payload, dict) else {}


def trusted_executable(path):
    return os.path.isfile(path) and os.access(path, os.X_OK) and not os.path.islink(path)


class SettingsCliClient:
    def __init__(self, executable, runner=subprocess.run, executable_check=trusted_executable):
        expanded = os.path.expanduser(executable)
        if not os.path.isabs(expanded):
            raise SettingsCliError("Der Einstellungen-CLI-Pfad muss absolut sein")
        self.executable = os.path.normpath(expanded)
        if not executable_check(self.executable):
            raise SettingsCliError("Keine vertrauenswürdige reguläre ausführbare Einstellungen-CLI")
        self.runner = runner
        self.executable_check = executable_check

    def _run(self, action, request=None):
        if not self.executable_check(self.executable):
            raise SettingsCliError("Die vertrauenswürdige Einstellungen-CLI ist nicht mehr verfügbar")
        command = [self.executable, action]
        input_text = None if request is None else json.dumps(request, ensure_ascii=False, separators=(",", ":"))
        timeout = 10 if action == "snapshot" else 90
        result = self.runner(
            command, input=input_text, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=timeout, check=False, shell=False,
        )
        if len(result.stdout.encode("utf-8")) > 1024 * 1024:
            raise SettingsCliError("Einstellungsantwort ist zu groß")
        try:
            payload = json.loads(result.stdout)
        except (TypeError, ValueError) as exc:
            raise SettingsCliError("Einstellungsantwort ist kein gültiges JSON") from exc
        if not isinstance(payload, dict):
            raise SettingsCliError("Einstellungsantwort ist kein JSON-Objekt")
        if result.returncode != 0 or not payload.get("ok"):
            raise SettingsCliError(str(payload.get("error", "Einstellungsänderung abgelehnt")), payload=payload)
        return payload

    def snapshot(self):
        return self._run("snapshot")

    def apply(self, request):
        return self._run("apply", request)
```

Implement `DirtySnapshotState` with `revision`, `server`, `visible`, `base_revision`, `base_values`, `dirty`, `secret_dirty`, `conflicts`, `mark_secret_dirty(name)`, `discard(name)`, and `discard_secret(name)`, matching Task 8 field-for-field. `build_request` rejects unless the secret-action names exactly equal `secret_dirty`; the state stores no secret values. This duplication is intentional because Cinnamon cannot import browser JavaScript; server-side conflict enforcement remains authoritative.

- [x] **Step 4: Replace the applet's independent writers with the shared client**

In `SettingsLogo.py`:

- import `Gio`, `settings_sync`, and `ThreadPoolExecutor` from `concurrent.futures`;
- remove the separate `IMAGE_MODEL_CHOICES` tuple;
- change `WIRTELPRIMPF_STORY_MODEL` from `entry` to a dynamically populated combo;
- implement `_make_catalog_combo(choices, current)` and populate it from `payload["choices"]["image_model"]` and `payload["choices"]["story_model"]`; prepend one labeled legacy option only when the current value is absent;
- map every existing environment/systemd row to the canonical keys in “Canonical Field Registry”;
- represent OpenAI and Cloudflare as separate write-only rows with a password entry, presence label, and `Gtk.CheckButton` for deletion;
- remove `_read_env_file`, `_existing_env_lines`, `_atomic_write_text`, `_write_env_file`, `_write_dropin`, `_write_systemd_dropins`, and `_apply_enabled_state` from configuration saving;
- retain explicit action buttons for “Generator jetzt starten” and “Timer neu starten”, because they are operations rather than configuration writers.
- create exactly one `ThreadPoolExecutor(max_workers=1, thread_name_prefix="wirtel-settings")`; never call `SettingsCliClient.snapshot()` or `.apply()` directly from a GTK callback.

Initialization calls `client.snapshot()` once, builds both model combos from `payload["choices"]`, prepends a labeled legacy value when necessary, stores `DirtySnapshotState`, and connects widget change signals only after the initial fill.

Saving collects only dirty non-secret values and explicit secret replace/delete actions:

```python
def _save(self):
    values = {key: self._widget_public_value(widget) for key, widget in self.widgets.items()}
    actions = self._secret_actions()
    request = self.sync_state.build_request(values, actions)
    payload = self.settings_client.apply(request)
    self.sync_state.accept_saved_snapshot(payload)
    self._apply_visible_values(payload["settings"], suppress_dirty=True)
    self._clear_secret_inputs()
    self._render_field_states()
```

On a CLI conflict payload, merge `payload["snapshot"]`, retain dirty values, add `payload["conflicts"]`, and show `Konflikt: extern geänderte Felder wurden nicht überschrieben.`

For every conflicting applet row, show an `Externen Wert übernehmen` action that calls `sync_state.discard(key)` and updates only that widget. Also provide one confirmed `Alle lokalen Entwürfe verwerfen` action. Neither action calls the CLI; they merely resolve the local draft against the latest received public snapshot.

- [x] **Step 5: Add Gio monitoring, debounce, a serialized background bridge, focus refresh, and cleanup**

Monitor the parent directory of each canonical path so file creation and replacement are both observed:

```python
def _install_monitors(self):
    watched = (self.env_path, self.timer_dropin_path, self.revision_state_path)
    self._monitors = []
    self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="wirtel-settings")
    self._refresh_in_flight = False
    self._refresh_pending = False
    self._operation_epoch = 0
    self._disposed = False
    for path in watched:
        parent = Gio.File.new_for_path(os.path.dirname(path))
        monitor = parent.monitor_directory(Gio.FileMonitorFlags.NONE, None)
        monitor.connect("changed", self._on_monitored_change, os.path.basename(path))
        self._monitors.append(monitor)
    self._fallback_refresh_id = GLib.timeout_add_seconds(30, self._queue_refresh, True)
    self.connect("map", lambda *_args: self._queue_refresh(False))
    self.connect("focus-in-event", lambda *_args: self._queue_refresh(False))
    self.connect("destroy", self._dispose_sync)
```

`_on_monitored_change` ignores unrelated basenames, cancels an existing GLib source, and schedules exactly one `GLib.timeout_add(250, self._queue_refresh, False)`. `_queue_refresh(repeat)` never blocks: if a refresh is running it sets `_refresh_pending`; otherwise it captures `_operation_epoch`, submits `settings_client.snapshot` to the single worker, and attaches a done callback that calls `GLib.idle_add(self._finish_refresh, captured_epoch, future)`. It returns `bool(repeat)`, so the 30-second source repeats while debounce/map/focus handlers propagate normally. `_finish_refresh` is the only code that touches widgets; it ignores a result whose captured epoch no longer equals `_operation_epoch`, otherwise merges the snapshot and renders states, then clears `_refresh_in_flight` and starts one coalesced pending refresh.

The save callback builds the immutable sparse request on the GTK thread, increments `_operation_epoch` before submission so every older refresh result becomes stale, disables Save, submits `settings_client.apply` to the same worker, and handles success/conflict through a separate `GLib.idle_add` completion. It then queues one fresh refresh. Thus refresh and save CLI processes are serialized without blocking Cinnamon, and a pre-save snapshot can never overwrite a later save result.

`_dispose_sync` sets `_disposed`, cancels debounce/fallback source IDs, calls `cancel()` on every monitor, and invokes `self._executor.shutdown(wait=False, cancel_futures=True)`. Completion handlers return immediately when disposed. The 30-second callback returns `True`; debounce, map, focus, and idle completion callbacks return `False`.

- [x] **Step 6: Make the prewritten static GTK contracts green**

Replace the old constant-tuple and applet-owned persistence tests with these static contracts. Keep the test that secret values are never placed into entries, but source its payload from a redacted `SettingsSnapshot`; byte-preservation and atomicity now belong exclusively to Tasks 2 and 4.

```python
def test_applet_uses_shared_snapshot_catalogs_for_both_model_combos(self) -> None:
    source = SETTINGS_LOGO_PATH.read_text(encoding="utf-8")
    self.assertIn("import settings_sync", source)
    self.assertNotIn("IMAGE_MODEL_CHOICES =", source)
    self.assertIn('payload["choices"]["image_model"]', source)
    self.assertIn('payload["choices"]["story_model"]', source)
    self.assertIn("_make_catalog_combo", source)
    self.assertIn("konfiguriert · nicht mehr im empfohlenen Katalog", source)

def test_applet_has_no_independent_configuration_writer_methods(self) -> None:
    tree = ast.parse(SETTINGS_LOGO_PATH.read_text(encoding="utf-8"), filename=str(SETTINGS_LOGO_PATH))
    defined = {node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    forbidden = {
        "_read_env_file",
        "_existing_env_lines",
        "_atomic_write_text",
        "_write_env_file",
        "_write_dropin",
        "_write_systemd_dropins",
        "_apply_enabled_state",
    }
    self.assertEqual(defined & forbidden, set())

def test_applet_sync_contract_contains_event_debounce_focus_and_fallback(self) -> None:
    source = SETTINGS_LOGO_PATH.read_text(encoding="utf-8")
    self.assertIn("monitor_directory", source)
    self.assertIn("GLib.timeout_add(250", source)
    self.assertIn("GLib.timeout_add_seconds(30", source)
    self.assertIn("ThreadPoolExecutor(max_workers=1", source)
    self.assertIn("GLib.idle_add", source)
    self.assertIn("_operation_epoch", source)
    self.assertNotIn("settings_client.snapshot()", source)
    self.assertNotIn("settings_client.apply(request)", source)
    self.assertIn('self.connect("map"', source)
    self.assertIn('self.connect("focus-in-event"', source)
    self.assertIn("_dispose_sync", source)
```

- [x] **Step 7: Run applet and configuration regressions**

Run: `python -m unittest tests.test_applet_settings_sync tests.test_settings_schema tests.test_story_directives -v`

Run: `python -m py_compile files/wirtelprimfgenerator@H234598/SettingsLogo.py files/wirtelprimfgenerator@H234598/settings_sync.py`

Expected: all tests pass; source scan finds no applet-owned environment/drop-in writer.

- [x] **Step 8: Add the helper to `make check` and commit**

Add `settings_sync.py` to `py_compile` and `tests.test_applet_settings_sync` to unittest commands.

```bash
git add files/wirtelprimfgenerator@H234598/SettingsLogo.py files/wirtelprimfgenerator@H234598/settings_sync.py tests/test_applet_settings_sync.py tests/test_settings_schema.py Makefile
git commit -m "feat(applet): synchronize settings through the shared core"
```

### Task 10: Packaging, unit hardening, versions, documentation, and full local regression

**Files:**
- Modify: `Sourcecode/systemd-user/wirtelprimpf.service`
- Modify: `Sourcecode/systemd-user/wirtelprimpf-admin.service`
- Modify: `tests/platform/test_systemd_units.py`
- Modify: `scripts/install-local.sh`
- Modify: `scripts/uninstall-local.sh`
- Modify: `files/wirtelprimfgenerator@H234598/metadata.json`
- Modify: `pyproject.toml`
- Modify: `wirtelprimpf_platform/__init__.py`
- Modify: `README.md`
- Modify: `files/wirtelprimfgenerator@H234598/README.md`
- Modify: `Sourcecode/env.example`
- Modify: `.github/workflows/check.yml`

**Interfaces:**
- Consumes: all preceding tasks.
- Produces: package version `1.1.0`, applet version `0.9.0`, installed static assets, stable CLI path, minimal service write paths, and documented recovery behavior.
- Produces a fully green generator branch ready for the public-copy plan; it does not deploy or mutate Cloudflare.

- [x] **Step 1: Write failing unit hardening and packaging assertions**

Add to `tests/platform/test_systemd_units.py`:

```python
def test_admin_service_writes_only_transaction_paths_and_does_not_import_secrets(self) -> None:
    lines = {
        line.strip()
        for line in (UNIT_ROOT / "wirtelprimpf-admin.service").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    self.assertNotIn("EnvironmentFile=-%h/.config/wirtelprimpf/openai.env", lines)
    self.assertIn("ReadWritePaths=%h/.config/wirtelprimpf", lines)
    self.assertIn("ReadWritePaths=%h/.config/cloudflare", lines)
    self.assertIn("ReadWritePaths=%h/.config/systemd/user/wirtelprimpf.timer.d", lines)
    self.assertNotIn("ReadWritePaths=%h/.config", lines)

def test_generator_imports_the_separate_cloudflare_token_file_without_moving_it_back(self) -> None:
    lines = {
        line.strip()
        for line in (UNIT_ROOT / "wirtelprimpf.service").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    self.assertIn("EnvironmentFile=-%h/.config/cloudflare/api-token.env", lines)
    self.assertNotIn("CLOUDFLARE_API_TOKEN=", (ROOT / "Sourcecode/env.example").read_text(encoding="utf-8"))
```

Add these exact packaging assertions to `tests/test_semver.py`:

```python
import tomllib

from wirtelprimpf_platform import __version__ as platform_version


class PackagingVersionTests(unittest.TestCase):
    def test_transactional_release_versions_and_installer_gate(self) -> None:
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        metadata = json.loads(
            (ROOT / "files/wirtelprimfgenerator@H234598/metadata.json").read_text(encoding="utf-8")
        )
        installer = (ROOT / "scripts/install-local.sh").read_text(encoding="utf-8")
        self.assertEqual(project["project"]["version"], "1.1.0")
        self.assertEqual(platform_version, "1.1.0")
        self.assertEqual(metadata["version"], "0.9.0")
        self.assertEqual(metadata["comments"], "Version: 0.9.0")
        gate = installer.index('if [[ ! -f "${SETTINGS_CLI}" || ! -x "${SETTINGS_CLI}" || -L "${SETTINGS_CLI}" ]]')
        replace = installer.index('rm -rf -- "${DEST}"')
        self.assertLess(gate, replace)
```

- [x] **Step 2: Run focused tests and verify current unit/version values fail**

Run: `python -m unittest tests.platform.test_systemd_units tests.test_settings_schema tests.test_semver -v`

Expected: failures for service paths, process EnvironmentFile, version numbers, and settings CLI install gate.

- [x] **Step 3: Harden the service and installer**

The service write-path block becomes exactly:

```ini
ProtectSystem=full
ProtectHome=read-only
ReadWritePaths=%h/.config/wirtelprimpf
ReadWritePaths=%h/.config/cloudflare
ReadWritePaths=%h/.config/systemd/user/wirtelprimpf.timer.d
```

Remove the Wirtel `EnvironmentFile` line from the admin service. Keep loopback CLI arguments and every existing hardening option.

Add `EnvironmentFile=-%h/.config/cloudflare/api-token.env` to
`wirtelprimpf.service` immediately after the existing Wirtel environment file.
This is optional so a missing token never prevents ordinary generation, while a
future rotation can use the separately stored credential. Never add that line to
the admin service.

Before applet replacement, `scripts/install-local.sh` must:

```bash
SETTINGS_CLI="${HOME}/.local/share/wirtelprimpf-generator/.venv/bin/wirtelprimpf-settings"
if [[ ! -f "${SETTINGS_CLI}" || ! -x "${SETTINGS_CLI}" || -L "${SETTINGS_CLI}" ]]; then
  printf 'Missing trusted settings CLI: %s\n' "${SETTINGS_CLI}" >&2
  exit 1
fi
install -d -m0700 -- "${HOME}/.config/wirtelprimpf" "${HOME}/.config/cloudflare"
install -d -m0700 -- "${HOME}/.config/systemd/user/wirtelprimpf.timer.d"
```

The uninstall script removes only the applet tree and explicitly preserves the venv CLI, Wirtel settings, separate Cloudflare token, revision signal, and systemd drop-in.

- [x] **Step 4: Bump versions and document the operational contract**

Set package/platform version to `1.1.0` and applet metadata version/comments to `0.9.0`. Document:

- the two model dropdown catalogs;
- environment and separate Cloudflare token paths;
- sparse revision/conflict behavior;
- web 2-second and status 5-second refresh;
- applet Gio/250-ms/30-second refresh behavior;
- effective timer application and rollback;
- `/api/status` fixed local-only shape;
- CLI snapshot/apply JSON over stdin;
- backup and restore locations used by the rollout plan;
- the explicit non-scope of Cloudflare redirects/DNS and Cinnamon upstream work.

Update `Sourcecode/env.example` to remove any `CLOUDFLARE_API_TOKEN` example from the Wirtel file and point to `~/.config/cloudflare/api-token.env` in comments without showing a token value.

- [x] **Step 5: Ensure CI runs every new contract**

The applet job's `make check` covers both new root tests. The platform job already discovers `tests/platform/test_*.py`; retain that discovery. Add a CI assertion after editable install:

```yaml
- name: Verify transactional settings entrypoint
  run: wirtelprimpf-settings --help >/dev/null
```

The help-only assertion verifies packaging without requiring a systemd user bus or inspecting the runner's credentials.

- [x] **Step 6: Run the complete Python, applet, and static-asset matrix**

Run:

```bash
python -m unittest discover -s tests/platform -p 'test_*.py' -v
make check
python -m compileall -q Sourcecode wirtelprimpf_platform scripts
node --test tests/test_admin_ui.mjs
git diff --check
```

Expected: every command exits 0. No test contacts OpenAI, GitHub, or Cloudflare.

- [x] **Step 7: Scan tracked changes for secret or split-writer regressions**

Run:

```bash
git diff --cached --check
rg -n -- 'CLOUDFLARE_API_TOKEN=' wirtelprimpf_platform files Sourcecode README.md tests
rg -n -- 'def (_write_env_file|_write_systemd_dropins|_apply_enabled_state)' files/wirtelprimfgenerator@H234598/SettingsLogo.py
```

Expected: the first command is clean; token assignment occurs only in fixture strings and the separated store implementation; the split-writer scan returns no match.

- [x] **Step 8: Commit the integration unit**

```bash
git add Sourcecode/systemd-user/wirtelprimpf-admin.service tests/platform/test_systemd_units.py scripts/install-local.sh scripts/uninstall-local.sh files/wirtelprimfgenerator@H234598/metadata.json pyproject.toml wirtelprimpf_platform/__init__.py README.md files/wirtelprimfgenerator@H234598/README.md Sourcecode/env.example .github/workflows/check.yml
git commit -m "chore(settings): package and document transactional control"
```

## Approved-Spec Coverage Matrix

| Approved requirement | Implemented and proven in |
|---|---|
| One shared write/validation authority | Tasks 1–5; applet writer-removal assertion in Task 9 |
| Sparse revisions, non-overlap merge, same-field rejection | Task 4 transaction tests; Task 5 exit-code contract; Tasks 7–9 client conflict tests |
| Stale secret rejection and write-only secret surfaces | Tasks 2, 4, 5, 7–9; final secret scans in Task 10 |
| Effective systemd timer plus verified rollback | Tasks 3–4; status comparison in Task 6; deployment comparison in the rollout plan |
| Web 2-second settings and 5-second status refresh without dirty overwrite | Task 8 Node state/polling contracts |
| Applet Gio events, 250-ms debounce, focus/open refresh, 30-second fallback | Task 9 pure and static contracts |
| Shared image/story dropdown catalogs and legacy-value behavior | Tasks 1, 8, and 9 |
| Independent, local-only, fixed-shape `/api/status` with partial degradation | Tasks 6–7 |
| Loopback/Host/Origin/CSRF/CSP/no-store security boundary | Task 7 transport tests and Task 8 fixed-asset tests |
| Secure files, separated Cloudflare token, no incidental migration | Tasks 2 and 4; service/install bounds in Task 10 |
| Public copy, newest-part-first display, dual-profile validation, deployment | Follow-on `2026-08-01-public-site-copy-and-rollout.md` |
| No Cloudflare/upstream/freeze mutation | Global constraints, Task 10 scans, and follow-on rollout gates |

## Plan-A Completion Gate

Do not start public deployment merely because Task 10 is green. First compare the branch against the approved design section-by-section, record the exact test counts and commit IDs, and then execute `2026-08-01-public-site-copy-and-rollout.md`. The second plan adds the independent public-copy commit, runs both site profiles, performs review/merge, installs the merged local version, and verifies live behavior. Cloudflare remains untouched throughout both plans.

## Additives Evidenzledger der Umsetzung

### 2026-08-01 — Fortschritt Tasks 1–8

- Task 1: `12db8cd` (`feat(settings): define shared configuration schema`).
- Task 2: `b6492bb` (`feat(settings): add secure configuration file stores`).
- Task 3: `c43f3b1` (`feat(settings): manage the effective user timer`).
- Task 4: `b01a357` (`feat(settings): add revisioned transactional updates`).
- Task 5: `77c5c81` (`feat(settings): expose the transactional JSON bridge`).
- Task 6: `07e1e6a` (`feat(status): collect redacted local operations state`) mit
  den additiven Korrekturen `04178c8` (fehlender Plattformzustand bleibt
  unbekannt/degradiert) und `9091b1a` (reine Timer-Laufzeitfelder ändern die
  opake Konfigurationsrevision nicht).
- Task 7: `ce016c2` (`feat(admin): separate settings and operational APIs`).
- Task 8: `50387c1` (`feat(admin): add conflict-safe live settings UI`). Der
  Abschlusslauf umfasste 11/11 Node-Verträge sowie 52/52 benachbarte Python-
  Verträge für Admin, Transaktion, Schema, Dateizugriff, CLI und Status. Die
  Admin-Assets wurden zusätzlich ohne Installation über `importlib.resources`
  aus dem Worktree gelesen; `git diff --check` war leer.
- Die Review-Nachbesserungen aus Task 8 sind beobachtbar abgedeckt: Vor dem
  ersten gültigen Snapshot blockiert ein DOM-neutraler `InteractionGate` jede
  Mutation, und der `409`-Konfliktpfad führt exakt einen logischen Snapshot-
  Merge aus.
- Der nachgelagerte Integrationsbefund „Eingabe während eines laufenden POST“
  ist in `5e44b8c` (`fix(admin): lock edits while saving settings`) geschlossen.
  Ein separater Save-Busy-Zustand sperrt State-Mutationen und Controls ab dem
  Request-Snapshot und entsperrt über `finally` bei Erfolg, `409`, abgelehnter
  Antwort und Exception. Der Abschlusslauf umfasste 14/14 Node-Verträge und
  34/34 Admin-/Transaktions-/Statusregressionen.

### 2026-08-01 — Task 9: transaktionale Applet-Synchronisation

- Task 9 ist in `da15d76` (`feat(applet): synchronize settings
  transactionally`) umgesetzt. Das Applet besitzt keine Environment-/Drop-in-
  Writer mehr und reicht jede Konfigurationsänderung über denselben sparsamen
  Revisionsvertrag an `wirtelprimpf-settings` weiter.
- Der nachträglich korrigierte Testvertrag ist maßgeblich: 17 beobachtbare
  Helper-/Coordinator-Verträge fahren Scheduler, Monitore, Executor und
  Completion-Dispatcher mit Fakes beziehungsweise einem echten einzelnen
  Worker-Thread. Sie belegen 250-ms-Coalescing, 30-s-Fallback, Fokus-Refresh,
  Epoch-Verwerfung, Dirty-Erhalt, Disposal/Cancellation, CLI-Ausführung abseits
  des Aufrufer-/GTK-Threads, redigierte Fehler sowie Secret-Konfliktauflösung.
  Die AST-Prüfung auf entfernte Writer dient nur noch als Packaging-Smoke.
- Der fokussierte Abschlusslauf umfasste 54/54 Verträge aus Applet-Sync,
  Settings-Schema und Story-Directives; `make check` lief davor mit allen zu
  diesem Zeitpunkt enthaltenen 16 Applet-Sync-Verträgen vollständig grün. Nach
  dem zusätzlich testgetriebenen Katalogvertrag liefen alle 17/17 Sync-Verträge
  und die benachbarten Suiten erneut grün; beide Python-Dateien kompilierten und
  `git diff --check` war leer.
- Präzisierung zur Antwortgröße: Der aktuelle Client erzwingt 10-/90-s-
  Prozesszeitlimits und verwirft eine bereits vollständig empfangene Antwort
  oberhalb 1 MiB. Das ist ausdrücklich **kein** Streaming- oder harter
  Speichernutzungsgrenzwert, weil `subprocess.run(..., stdout=PIPE)` die Ausgabe
  zunächst vollständig sammelt. Additives Härtungsitem: auf inkrementelles,
  timeoutgebundenes Lesen mit Prozessabbruch direkt beim Überschreiten des
  Limits umstellen und dies mit einem tatsächlich endlosen/übergroßen Fake-
  Prozess beweisen; bis dahin darf die 1-MiB-Prüfung nur als nachgelagerte
  Antwortgrößenvalidierung beschrieben werden.
- Der unabhängige Root-Review fand anschließend, dass ein einzelner Gio-
  Monitorfehler den Editor-Initpfad noch abbrechen konnte. `d13b4bf`
  (`fix(applet): isolate optional monitor failures`) isoliert Fehler nun je
  Zielpfad: Initialsnapshot, übrige Monitore und 30-s-Fallback bleiben aktiv;
  Fokus- und Fallback-Zyklen versuchen fehlgeschlagene Ziele erneut zu
  installieren. Damit wird ein später vorhandener Drop-in-Elternpfad ohne
  Editor-Neustart wieder beobachtbar. Der RED-Test scheiterte zuvor direkt am
  simulierten `OSError`; danach waren 18/18 Sync-Verträge, die fokussierte
  55/55-Matrix, `py_compile`, `git diff --check` und das vollständige
  `make check` grün.

### 2026-08-01 — zurückgenommener Packaging-Smoke nach Task 5

- Der Worker führte entgegen der engeren Arbeitsanweisung, vor dem ausdrücklich
  geplanten Rollout nichts zu installieren, einmal
  `which python; python -m pip install --disable-pip-version-check --no-deps -e . && .venv/bin/wirtelprimpf-settings --help >/dev/null && python -m wirtelprimpf_platform.cli settings --help >/dev/null 2>&1 || true; git diff --check`
  aus.
- Interpreter/Prefix laut unmittelbarer und späterer Nachprüfung:
  `/usr/sbin/python`, `sys.prefix=/usr`, `sys.base_prefix=/usr`,
  `purelib=/usr/local/lib/python3.14/site-packages`,
  `scripts=/usr/local/bin`.
- Pip baute dabei das editable Wheel
  `wirtelprimpf_generator-1.0.0-0.editable-py3-none-any.whl`, meldete
  `Successfully installed wirtelprimpf-generator-1.0.0`; unmittelbar danach
  scheiterte nur der nicht vorhandene Worktree-Pfad
  `.venv/bin/wirtelprimpf-settings` mit `No such file or directory`.
- Der Worker nahm die eigene Mutation sofort mit
  `python -m pip uninstall -y wirtelprimpf-generator` zurück. Pip meldete
  `Found existing installation: wirtelprimpf-generator 1.0.0`,
  `Uninstalling wirtelprimpf-generator-1.0.0` und
  `Successfully uninstalled wirtelprimpf-generator-1.0.0`. Beim Installieren
  hatte Pip keinen vorherigen Uninstall-Vorgang gemeldet.
- Read-only Restprüfung danach:
  `python -m pip show wirtelprimpf-generator` meldete
  `Package(s) not found`; `find` fand weder einen Wirtelprimpf-`.pth`-/
  `dist-info`-Eintrag im ermittelten `purelib` noch ein
  `wirtelprimpf-*`-Console-Script in `/usr/local/bin`; und
  `importlib.util.find_spec('wirtelprimpf_platform')` aus `/tmp` ergab `None`.
- Ab hier bleiben weitere Install-, Reload-, Deploy- und Remote-Schritte bis zum
  durch die Primärsession ausdrücklich freigegebenen Rollout ausgesetzt.

### 2026-08-01 — Korrektur der opaken Revisionsquelle

- Die in Task 4 gedruckte Verwendung von `timer_observation.revision_dict()` ist
  als historischer Entwurf superseded. `last_trigger`, `next_run`, `result`,
  `active` und `active_state` sind Betriebs-, nicht Konfigurationszustand.
- Die Revisionsquelle enthält vom Timer ausschließlich `enabled`,
  `interval_minutes`, `randomized_delay_seconds` und `persistent`. Dadurch lösen
  normale Timerläufe weder einen Schein-Konflikt für Secretänderungen noch einen
  falschen `revision_signal_mismatch` aus.
- Ein beobachtbarer Regressionstest variiert Aktivität, Zeitstempel und Resultat
  bei identischer Timerkonfiguration und verlangt dieselbe 64-stellige Revision.

### 2026-08-01 — Task 10: Packaging, Unit-Härtung und vollständige lokale Regression

- Der testgetriebene RED-Lauf
  `python -m unittest tests.platform.test_systemd_units tests.test_settings_schema tests.test_semver -v`
  schlug zunächst wie vorgesehen an den noch fehlenden Servicepfaden, dem
  Settings-CLI-Installationsgate und den alten Versionswerten fehl. Der finale
  fokussierte Lauf bestand 24/24 Verträge, einschließlich eines zusätzlichen
  beobachtbaren Paketressourcentests für `admin.html`, `admin.css` und
  `admin.mjs` über `importlib.resources`.
- `46f07c593b132d293c2f5368e7ee6ef00f136e79`
  (`chore(settings): package and document transactional control`) enthält die
  Task-10-Integration: Paket-/Plattformversion `1.1.0`, Appletversion `0.9.0`,
  minimierte Admin-Schreibpfade ohne importierte Secret-Environmentdatei, die
  optionale separate Cloudflare-Token-Datei ausschließlich im Generatorservice,
  das fail-closed Settings-CLI-Gate vor Applet-Ersatz, konservative
  Deinstallation, CI-Entrypointprüfung und den vollständigen Betriebsvertrag.
- Die finale, nach dem letzten Testzusatz erneut ausgeführte Matrix bestand:
  `python -m unittest discover -s tests/platform -p 'test_*.py' -v` mit 125/125;
  `make check` mit Applet-Runtime grün, Admin-UI 14/14, SemVer/Packaging 8/8,
  Git-Object-Fallback 3/3, Release-Publication 3/3, Helper-Environment 7/7,
  Applet-Sync 18/18, Settings-Schema 6/6 und Story-Directives 31/31;
  `python -m compileall -q Sourcecode wirtelprimpf_platform scripts` ohne Fehler;
  der eigenständige `node --test tests/test_admin_ui.mjs` erneut 14/14; und
  `git diff --cached --check` ohne Befund.
- Der abschließende Secret-Scan fand `CLOUDFLARE_API_TOKEN=` ausschließlich in
  drei Testassertionen/-fixtures und keinen Treffer in Produktivcode,
  Beispielkonfiguration oder Dokumentation. Der Scan auf die bekannten
  tatsächlich verwendeten Tokenfragmente fand null Treffer. Der
  Split-Writer-Scan auf `_write_env_file`, `_write_systemd_dropins` und
  `_apply_enabled_state` in `SettingsLogo.py` blieb leer.
- Das optionale Python-Modul `build` war lokal nicht vorhanden. Deshalb wurde
  bewusst weder ein Paket installiert noch eine neue Buildabhängigkeit
  bezogen; Package-Data und Entrypoint wurden aus `pyproject.toml` gelesen und
  die drei statischen Assets direkt als Paketressourcen validiert. Die CI führt
  nach ihrer regulären Editable-Installation zusätzlich
  `wirtelprimpf-settings --help` aus.
- Unmittelbar nach dem Codecommit war `git status --short` leer. Während Task 10
  erfolgten keine Installation, kein Reload, kein Deploy, kein Push, kein PR,
  kein Merge, keine Cloudflare-/DNS-Mutation, kein Cinnamon-Upstream-Fix und
  keine sonstige Systemmutation. Die Public-Copy-Tasks bleiben bis zum
  vereinbarten Review-Checkpoint unangetastet.

### 2026-08-01 — Additive Schlussreview-Präzisierung des Transaktionsvertrags

- Dieser Eintrag superseded ausschließlich überholte technische Aussagen in
  älteren Ledgerabschnitten; sie bleiben als Historie unverändert lesbar. Der
  finale lokale Härtungscommit ist
  `50c4ec94df1769fee788a3331714a74a28fb358d`
  (`fix(settings): harden transactional client boundaries`). Er enthält zehn
  Produktions-/Testdateien mit 599 Einfügungen und 44 Entfernungen.
- Die frühere Formulierung „10-/90-s-Prozesszeitlimits“ gilt nicht mehr für
  Writes. Der Applet-`snapshot` bleibt auf zehn Sekunden begrenzt. Applet-
  `apply` besitzt **keinen** `subprocess.run`-Killtimeout: Ein
  Präsentationsclient darf den einzigen Transaktionseigner niemals zwischen
  Write, Generatorvalidierung und Rollback töten. Die vom CLI gestarteten
  externen Teiloperationen bleiben an ihren jeweiligen Servergrenzen begrenzt.
  Der separate HTTP-Livesmoke verwendet für POST einen endlichen 180-s-
  Sockettimeout; ein unklarer Clientausgang wird per Revision reconciled und
  nicht blind wiederholt oder als Ownership angenommen.
- Ein neuer kanonischer Paritätstest bindet den Applet-Präsentationsvertrag an
  alle 37 `SETTING_SPECS` mit `applet_visible=True` einschließlich exakter
  String-/Integer-/Boolean-Typen. Erfolgreiche CLI-Antworten, Refreshes, Saves
  und Konfliktsnapshots müssen außerdem sämtliche Pflichtkataloge nichtleer,
  Secret-Präsenz, Invarianten und Warnungen enthalten. Malformed/partielle
  409-Antworten verändern weder Serverbasis noch lokale Entwürfe; Fehler aus
  diesem Callbackpfad werden redigiert und können nicht in die GTK-Schleife
  entweichen.
- Derselbe fail-closed Grundsatz gilt im Browser: elf dargestellte Felder und
  fünf Dropdownkataloge werden vor Initialisierung, Poll-Merge, Save-Accept und
  409-Merge vollständig und typstreng geprüft. Die Admininteraktion bleibt bis
  zum ersten vollständigen Erfolgssnapshot gesperrt. Bild- und Storymodell sind
  damit nicht nur gemeinsame Dropdowns, sondern werden bei einem leeren oder
  fehlenden Katalog auch nicht als scheinbar sichere Freitext-/Teiloberfläche
  freigegeben.
- Die Servertransaktion vergleicht stale Basen typstreng, sodass Python-
  Gleichheiten wie `True == 1` keinen Konflikt umgehen. Der Generatorvalidator
  erhält exakt die nach dem Write erneut geparsten persistenten Rohwerte statt
  eines normalisierten Proposal-Overlays. Ein Regressionstest persistiert
  absichtlich einen ungültigen Rohwert, ändert ein anderes Feld und belegt:
  Validatorfehler, byteidentisches Rollback, null systemd-Mutation.
- Die lokale HTTP-Grenze liest Bodyteile gegen eine einzige absolute monotone
  Frist. Der Slow-Drip-RED-Test belegte zusätzlich, dass die 408-Antwort zuvor
  noch mit der fast abgelaufenen Restfrist geschrieben wurde. Nun stellt
  `finally` zuerst den ursprünglichen Sockettimeout her; erst danach folgt der
  Responsewrite. systemd-Dauern akzeptieren die reale exakte nackte Null, aber
  weiterhin keine andere einheitenlose Zahl.
- RED-Evidenz: initialer Fokus über 66 Python-Verträge mit sechs erwarteten
  Assertionfehlern und einem erwarteten Fehler, dazu zwei erwartete Node-
  Fehlschläge; anschließend separate rote Verträge für semantisch partielle
  Snapshots, leere Pflichtkataloge und den Sockettimeout beim 408-Write.
  GREEN-Evidenz nach der letzten Änderung: Plattform `143/143`; vollständiges
  `make check` mit Admin-UI `23/23`, Applet-Sync `23/23`, Settings-Schema
  `12/12`, Story-Directives `31/31` und allen übrigen Suiten; Web `9/9`; Astro
  22 Dateien ohne Fehler, Warnungen oder Hinweise; `compileall`, Ruff über alle
  geänderten Pythonpfade und `git diff --check` ohne Befund. Der unabhängige
  Rootfokus bestand 68/68 Python und 23/23 Node.
- Der nachgelagerte Rolloutplan
  `2026-08-01-public-site-copy-and-rollout.md` enthält jetzt den vollständigen
  operativen Transaktionsrahmen: Generatorquieszenz vor jeder Recoverymutation,
  gemeinsamer Settings-Lock über Deploy- und Rollback-Codewechsel,
  automatische Restoreaktionen ausschließlich für Installartefakte, rein
  klassifizierende/preservierende Config-Recovery, Modussicherung der drei vom
  Installer gehärteten Elternverzeichnisse, getrennte Timer-Enablement- und
  Activity-Phasen sowie eine dreizuständige Git-Commitpoint-Prüfung
  (`old`, `target`, `unknown`). Der isolierte Failure-Harness belegt sämtliche
  Reihenfolgen, Lock-/Timeoutpfade, den Merge-zu-Flag-Signalrand, Third-SHA,
  Configkonkurrenz und `0755 -> 0700 -> 0755`; Step 9 und Step 10 bestehen
  Syntaxprüfung, Step 10 zusätzlich den realen disposable Lauf.
- Die beiden vollständigen Webprofile blieben unverändert reproduzierbar:
  Hub-SHA-256
  `0acc6695654d3e82e450a3467d96995da89e59d954d00340d5a5028916ab1bb6`,
  Archiv-SHA-256
  `f6e682fa639f72863f8911bb2b94d416ba83e913613797334361e439308a91bd`,
  jeweils 823 Dateien, 818 HTML und 10.840 geprüfte interne Links.
- Diese Runde endete absichtlich vor Remote- und Runtimeaktionen. Es erfolgten
  kein Push, PR-Write, Merge, Install, Reload, Deploy, Service-/Timerwrite,
  Cinnamon-Appletreload, Cloudflare-/DNS-Zugriff oder Upstream-Fix.

### 2026-08-02 — Additive Abschlussremediation: Applet-Lock und atomarer Rollout

- Dieser Abschnitt ersetzt keine Historie, sondern superseded nur frühere
  technische Aussagen, nach denen Applet-Operationen ohne gemeinsamen Lock
  liefen, nur der Timer als Ausführungsbarriere diente oder `main` per
  Worktree-Fast-forward umgeschaltet wurde. Der abgeschlossene lokale
  Code-/Testcommit ist
  `d10f36fefee8f1110e2204b8e9f75677fc457549`
  (`fix(settings): serialize applet operations safely`).
- `settings_sync.exclusive_settings_lock` öffnet nur einen absolut aufgelösten,
  regulären, nicht symlinkbaren Lockpfad unter ebenfalls geprüften
  Elternverzeichnissen, setzt Modus `0600`, verwendet einen echten exklusiven
  `flock` und endet nach 100 ms redigiert als busy. Der Generator-Tab hält
  diesen Lock über seine komplette Befehlsfolge. Ein Konkurrent bewirkt damit
  null `systemctl`-Aufrufe; Busy-/Fehlerzustand und UI-Gates werden sicher
  zurückgesetzt.
- Die Browsergrenze verlangt die vollständigen semantischen
  `numeric_bounds` genau für die drei tatsächlich konsumierten Zahlenfelder:
  vorhandene ganzzahlige Min-/Maxwerte, `min <= max`, aktuellen Wert im
  Intervall sowie konsistente Story-Min-/Max-Reihenfolge. Das Applet behält die
  Revision absichtlich als opakes nichtleeres Signal und dupliziert keine
  Invarianten, die es nicht rendert.
- Der ergänzte Rolloutvertrag begrenzt Curl, Fetch und editable Pip, prüft nach
  PR-Checks erneut Zustand/Head/Basis/Draft, verwendet
  `--match-head-commit` und belegt exakt geordnete Mergeeltern. Vor jeder
  lokalen Codemutation stoppt er den Timer, wartet den Generator bounded
  inaktiv, setzt eine Runtime-Service-Mask und wartet erneut. Vor dem
  Commitpunkt wird zusätzlich der gestoppte Timer runtime-maskiert. Jeder
  Postcommit-, Unknown-SHA- oder Config-Attention-Pfad stoppt Admin/Timer und
  hinterlässt Service und Timer fail-closed `masked-runtime`.
- Der Post-Smoke-Settings-Lock bleibt über Revisions-/Fingerprintownership,
  Unit- und Appletverifikation, Timerenablement, beide Masken, Git-CAS,
  Worktree-Anbindung ohne Old-Tree, Service/Admin/Applet/Timerrestauration und
  alle finalen Zustandsbeweise gehalten. `main` wird ausschließlich mit
  `git update-ref refs/heads/main "$target_sha" "$runtime_sha_before"`
  verglichen und gesetzt. Das Worktree-HEAD steht dabei schon detached auf dem
  Target-Tree; erst nach erfolgreichem CAS wird derselbe Tree an `main`
  gebunden.
- Ein zweiter Appletreload im lockgehaltenen Schlussabschnitt ist bewusst
  entfernt. Der Target-Appletreload und der UUID-Nachweis erfolgen im
  freigegebenen Livesmoke-Fenster; anschließend beweisen Applet-Diff und UUID
  die unveränderte Installation. Für die letzte Lockfreigabe gilt ein
  atomarer Abschlussvertrag: HUP/INT/TERM werden unter Lock ignoriert,
  anschließend folgen Lockfreigabe, `deployment_complete=1`, EXIT-Disarm und
  Signalreset. Ein Lockfreigabefehler trifft weiterhin die bewaffnete
  EXIT-Recovery, während nach erfolgreicher Freigabe keine legitime
  Folgetransaktion mehr durch einen späten Postcommit-Handler gestoppt werden
  kann.
- Test-first-Evidenz: der initiale Applet-Lock-Fokus schlug mit zwei Fehlern und
  zwei Errors erwartungsgemäß rot fehl und bestand anschließend `39/39` aus
  Applet-Sync und Settings-Schema. Der Admin-Bounds-Fokus bestand nach den
  gezielt roten malformed- und Cross-field-Fällen `24/24`. Der vollständig
  extrahierte Step 9 bestand `bash -n`; Step 10 bestand `bash -n` und seinen
  realen disposable Failure-Harness mit Exit 0. Dieser belegt zusätzlich
  Service-/Timer-Masken, Doppelwait-Rennen, Lock bis zum letzten Timerproof,
  echte CAS/Target-Tree-Anbindung, Update-ref-Signalrand, Third-SHA,
  Config-Attention ohne Restore, Artefakt-/Runtimeproofs sowie
  PR-Head-Match/Elternreihenfolge.
- Finale vollständige Regression: Plattform `143/143`; `make check` mit
  Applet-Runtime grün, Admin-UI `24/24`, SemVer `8/8`, Git-Object-Fallback
  `3/3`, Release-Publication `3/3`, Helper-Environment `7/7`, Applet-Sync
  `25/25`, Settings-Schema `14/14`, Story-Directives `31/31`; Web `9/9`;
  Astro 22 Dateien mit 0 Fehlern, 0 Warnungen, 0 Hinweisen; `compileall`, Ruff
  0.15.16 und `git diff --check` grün. Hub und Archiv validierten jeweils 823
  Dateien, 818 HTML und 10.840 interne Links mit den Baum-SHA-256
  `0acc6695654d3e82e450a3467d96995da89e59d954d00340d5a5028916ab1bb6`
  beziehungsweise
  `f6e682fa639f72863f8911bb2b94d416ba83e913613797334361e439308a91bd`.
- Es erfolgten in dieser Runde kein Fetch, Push, PR-Write, Merge, Install,
  Reload, Deploy, Service-/Timerwrite, `systemctl`, `gdbus`, DNS-/Cloudflare-
  oder Upstreamzugriff. Der Doku-/Evidenz-SHA ist der Commit, der diesen
  Abschnitt enthält, und wird im finalen Übergabebericht ausgewiesen.

### 2026-08-02 — Additive Gegenreview-Remediation des Rollout-Abschlusses

- Dieser Abschnitt ist additiv und superseded ausschließlich die unmittelbar
  zuvor dokumentierten, inzwischen als unzureichend erkannten Aussagen zu
  `--match-head-commit`, manuell einzufügenden Smokes und rein simulierten
  Signalen. Produktionscode und der transaktionale Konfigurationskern selbst
  blieben unverändert.
- Der kanonische Rolloutplan bindet nun Base und Remote-PR-Head prämutativ:
  deterministischer lokaler Zwei-Eltern-Merge mit Head-Tree, read-only
  Ruleset-/Branch-Protection-Gate und ein atomarer Push mit exakter Main- und
  Head-Lease. Derselbe Push setzt Main und löscht den validierten Head. Danach
  werden Remote-OID, GitHubs dokumentierter indirekter PR-Merge, Tree und die
  Elternfolge `base, head` erneut exakt bewiesen.
- Eine vorrangige additive Klarstellung untersagt jede Task-3-Änderung am
  Runtime-Checkout. Das Ownership-Gate repariert vor Task 4 ausschließlich den
  bereits eng aufgelösten Besitz; Runtime-HEAD bleibt bis zum geschützten
  Task-4-CAS ungleich dem Ziel.
- Step 9 ist jetzt ein vollständiges ausführbares Artefakt: die exakten
  API-/Status- und Live-Sync-Smokes stehen bytegleich im normativen Codeblock,
  und der Ownership-Marker wird vor seiner Revisionsprüfung erzeugt. Der
  eingecheckte Vertragstest extrahiert Task 3, Step 9 und Step 10, prüft alle
  drei mit `bash -n`, kontrolliert Inline-Gleichheit und Markerordnung und führt
  den disposable Step-10-Harness real aus.
- Rollback disarmt nur EXIT-Rekursion; HUP/INT/TERM bleiben über die gesamte
  Recovery ignoriert, während der ursprüngliche Status erhalten bleibt. Die
  reale Signalinjektion sendet TERM, blockiert unter gehaltenem Settings-Lock,
  sendet HUP und endet erst nach Restore/Fail-close und Unlock mit Status 143.
- Lock-Contention und Config-Attention beweisen Admin/Timer inaktiv, beide
  Runtime-Masken gesetzt und persistente Timer-Enablement unverändert. Ein
  lokaler Bare-Remote belegt, dass Base- oder Head-Race den kompletten atomaren
  Push zurückweisen; nur beide exakten Leases erlauben Main-CAS plus Head-Löschung.
- TDD-Evidenz: initial vier gezielte Fehler bei sechs Vertragstests; die
  dauerhafte Makefile-Bindung anschließend separat rot. GREEN: Vertrag `7/7`.
  Frisches `make check` bestand mit Applet-Runtime, Admin-UI `24/24`, SemVer
  `8/8`, Git-Object-Fallback `3/3`, Release-Publication `3/3`,
  Helper-Environment `7/7`, Applet-Sync `25/25`, Settings-Schema `14/14`,
  Story-Directives `31/31` und Rollout-Vertrag `7/7`.
- Auch diese Author-Runde endet vor jeder externen oder lokalen
  Betriebsänderung: kein Fetch, Push, PR-Write, Merge, Install, Reload, Deploy,
  `systemctl`, `gdbus`, Runtime-, Cloudflare-, DNS- oder Upstream-Zugriff.

### 2026-08-02 — Additive Task-3-Auth-/Policy-/Receipt-Remediation

- Dieser parallele Ledger-Eintrag ist additiv und ändert keinen
  Produktionscode des transaktionalen Konfigurationskerns. Er superseded nur
  die vorherige Annahme, der Rollout könne seine Ruleset-Typen selektiv
  klassifizieren, unqualifiziertes Root-Git verwenden oder einen erfolgreichen
  Remote-Push ohne dauerhaften Commitpunkt als gewöhnlichen Fehler behandeln.
- Der reale Preflight ergab ungültige persistierte `gh`-Authentifizierung für
  sowohl `teladi` als auch Root. Öffentliche unauthentifizierte Reads zählen
  nicht als Write-Freigabe. Der kanonische Rollout verlangt nun vor jeder
  Writephase einen extern gelieferten ephemeren Token, der über `/user`
  authentifiziert wird; ohne ihn bleibt alles prämutativ stehen. Es wurde kein
  Credential erfunden, aus einem Keyring übernommen, gedruckt oder gespeichert.
- Task 3 Step 5 kapselt sämtliche Gitobjekt-, Receipt- und Remoteoperationen in
  UID/GID `teladi` unter `env -i`, festem `HOME` und sicherem `PATH`. HTTPS-Git
  löscht pro Befehl die Helperliste und verwendet ausschließlich
  `gh auth git-credential`; `setup-git`, persistente Credentials und
  `safe.directory` sind ausgeschlossen. Step 4/5 beweisen denselben
  Same-Repository-PR anhand Headname/OID, Cross-Repo-Bit, Owner, Repository-ID
  und `nameWithOwner`; beide Origin-URLs müssen exakt kanonisches HTTPS sein.
- Der Policy-Gate akzeptiert nur Applied Rules exakt `[]` und Classic
  Protection exakt authentifiziertes HTTP 404. Jeder andere Zustand endet vor
  `commit-tree`. Die Merge-Nachricht konsumiert ausschließlich den einmal
  geprüften `$generator_head`.
- Das private atomare Receipt bildet ausschließlich
  `planned -> remote_committed -> verified` ab. Push-Erfolg wird unmittelbar
  gelatcht; API-/Postcondition-Ausfälle werden eindeutig als bereits committed
  und noch nicht verifiziert gemeldet. Wiederanläufe reconciled
  `OPEN + planned + Remote-Merge` sowie `MERGED + Receipt` ohne zweiten Push;
  unbekannte Ref-/Receiptzustände bleiben fail-closed.
- Step 10 beweist den Commitpunkt gegen einen echten lokalen Bare-Remote mit
  Abbruch direkt nach Push, API-Ausfall, idempotenter Verifikation und
  unbekanntem Refpaar. Der Vertrag bindet zusätzlich direkt die normative
  Step-9-Reihenfolge `EXIT-Disarm -> HUP/INT/TERM-Maske -> Recovery ->
  Lockfreigabe -> Statusausgang`; der reale TERM/HUP-Test bleibt erhalten.
- TDD-Evidenz: zunächst fünf gezielte Fehler bei zwölf Vertragstests, danach
  je ein weiterer roter Fokus für das Push-zu-Latch-Fenster und das private
  Receipt-Elternpfadgate; GREEN `12/12`.
  Task-3-Step-5, Step 9 und Step 10 bestehen `bash -n`, der disposable Harness
  Exit 0. Die vollständige als `teladi` unter `env -i` ausgeführte
  `make check`-Matrix bestand mit Admin-UI `24/24`, SemVer `8/8`,
  Git-Object-Fallback `3/3`, Release-Publication `3/3`, Helper-Environment
  `7/7`, Applet-Sync `25/25`, Settings-Schema `14/14`, Story-Directives
  `31/31` und Rollout-Vertrag `12/12`.
- Es erfolgten kein Fetch, Push, PR-Write, Merge, Install, Reload, Deploy,
  Runtime-, `systemctl`-, `gdbus`-, Cloudflare-, DNS- oder Upstreamzugriff. Der
  Doku-/Test-SHA ist der lokale `teladi`-Commit dieser additiven Remediation und
  wird in der Übergabe ausgewiesen.

### 2026-08-02 — Additive Gegenreview-Härtung: Task-3-Vertrauenskette v2

- Dieser parallele Ledger-Eintrag ist additiv und superseded die älteren
  Task-3-Formulierungen nur dort, wo sie einen allgemeinen
  Prozessumgebungs-Token, Root-Git, eine einzelne Origin-URL oder ein nicht
  vollständig rekonstruierbares Receipt zuließen. Der transaktionale
  Konfigurationskern und die Produktionsoberflächen blieben unverändert.
- Der privilegierte äußere Prozess prüft UID 0, deaktiviert Tracing vor jedem
  Geheimniszugriff und reicht nur einen anonymen FD an einen langen
  `teladi`-/`env -i`-Prozess weiter. Dieser beweist UID/GID 1000, festes
  `HOME`, sicheren `PATH` und Repositorykontext. Der Token gelangt weder in
  `argv`, Heredoc, Datei noch in das Environment dieses Prozesses, seiner
  Tests, Builds oder Hooks. Ausschließlich kurze API-/`gh`-/Credential-Aufrufe
  lesen ihn NUL-begrenzt und erhalten ihn für ihre eigene Lebensdauer.
- Vor dem ersten Fetch und vor jeder späteren Writephase wird der Akteur als
  `H234598` mit ID `54270221` verifiziert. Fetch- und Push-URL müssen nach
  `get-url --all` jeweils exakt einmal und wörtlich als
  `https://github.com/H234598/Wirtelprimpf-generator.git` vorkommen; alle
  Netzwerkkommandos verwenden dasselbe Literal. Pro Gitbefehl werden
  Credential-Helper geleert, nur der kontrollierte `gh`-Helper ergänzt und
  Hooks durch `core.hooksPath=/dev/null` neutralisiert.
- Receipt v2 bindet mit geschlossener Feldmenge Zustand, Actor,
  Repository-ID/-Name, kanonische URL, PR, Head-Ref/-OID, Base-OID,
  Head-Tree, Mergezeit, Mergenachricht und Merge-OID. Jeder Lauf leitet
  Head-Tree und deterministischen Merge neu aus den aktuell geprüften
  Gitobjekten ab und vergleicht jedes Feld. Zusätzliche, fehlende,
  veraltete, inkonsistente und auch strukturell plausible, aber frei
  gefälschte Receipts brechen ab. Temporäre Receipt-Dateien werden selbst bei
  erzwungenem atomarem Rename-Fehler entfernt.
- Die unmittelbar getestete Zustandsfunktion erlaubt genau einen Pushpfad:
  `planned` bei unveränderten Base-/Head-Refs. Einen bereits sichtbaren Merge
  reconciled sie; `remote_committed` und `verified` beobachten nur. Jede
  unbekannte Kombination ist fail-closed. Der normative Rollback wurde
  ebenfalls direkt extrahiert und mit TERM/HUP, Recovery und Lockfreigabe
  ausgeführt.
- Test-first-Evidenz: neun gezielte Fehler bei zunächst `17` Tests, danach
  drei Receipt-v2-Fehler bei `20` Tests sowie je ein roter Fokus für den
  direkten Rollback und die Remote-Zustandsklassifikation. Der aktuelle
  Vertrag ist `22/22` grün. Seine realen Harnesses prüfen unter anderem
  FD-/`bash -x`-Geheimnisfreiheit, Actor- und URL-Kardinalität,
  Hook-Neutralisierung gegen einen absichtlich fehlschlagenden Pre-Push-Hook,
  unabhängige Mergeableitung, Receipt-Fälschung/Cleanup und den No-Re-push-
  Zustandsautomaten.
- Die frische vollständige `make check`-Matrix lief als `teladi` unter
  `env -i` mit Exit 0: Applet-Runtime grün, Admin-UI `24/24`, SemVer `8/8`,
  Git-Object-Fallback `3/3`, Release-Publication `3/3`, Helper-Environment
  `7/7`, Applet-Sync `25/25`, Settings-Schema `14/14`, Story-Directives
  `31/31` und Rollout-Vertrag `22/22`.
- Es erfolgte keine Runtime- oder externe Mutation: kein Fetch, Push,
  PR-Write, Merge, Install, Reload, Deploy, `systemctl`, `gdbus`, Cloudflare,
  DNS oder Upstream. Schreibende Gitproben blieben auf disposable lokale
  Repositories begrenzt; der lokale Doku-/Test-Commit wird in der Übergabe
  ausgewiesen.

### 2026-08-02 — Parallele additive NO-GO-Schließung für Task 3

- Dieser parallele Ledger-Eintrag ist additiv und korrigiert die vorherige
  Task-3-Vertrauenskette ausschließlich hinsichtlich des entwichenen
  Step-1-Buildkontexts, eines möglichen direkten Step-3-`main`-Pushes, der
  dynamisch akzeptierten Repository-ID sowie nicht neutralisierter
  Git-HTTP-/AskPass-Konfiguration. Der transaktionale Konfigurationskern und
  seine Produktionsoberflächen wurden dabei nicht verändert.
- Beide vollständigen Hub-/Archiv-Buildprofile und Validatoren liegen nun im
  selben UID/GID-1000-`teladi`-/`env -i`-Heredoc wie die übrige Step-1-Matrix.
  Step 3 bindet den Branch vor Authentisierung und erstem Fetch; sein real
  ausgeführter Predicate akzeptiert einen Feature-Branch und lehnt `main`
  zwingend ab. Der tatsächliche, markierte Prewrite-Callblock ordnet Branch,
  exakte Origin-URL, Actor und feste Repository-Identität vor dem Fetch.
- Steps 3, 4 und 5 prüfen `H234598/Wirtelprimpf-generator` jeweils zusammen
  mit der unveränderlichen Node-ID `R_kgDOTpr2BA`. Fehlende, falsche oder aus
  einem gleichnamigen Ersatzrepo dynamisch übernommene IDs brechen in den
  ausführbaren JSON-Prädikaten ab. Receipt v2 und PR-Prädikate sind damit an
  die feste Node-ID statt nur an eine laufintern selbstkonsistente Antwort
  gebunden.
- Die kurzen Tokenprozesse setzen `GIT_TERMINAL_PROMPT=0`,
  `GIT_ASKPASS=/bin/false` und `SSH_ASKPASS=/bin/false`. Jeder Remote-Gitaufruf
  leert globale und exakt URL-spezifische `http.extraHeader`, leert danach die
  Helperliste, ergänzt nur `gh auth git-credential`, setzt
  `core.askPass=/bin/false` und neutralisiert Hooks. So können persistente
  Repository-/Userwerte weder einen alternativen Authorization-Header senden
  noch ein tokenerbendes AskPass starten.
- Test-first lief die unveränderte Basis `22/22` grün und die neue
  29-Test-Suite danach mit `14` gezielten Failures und null Errors rot. GREEN
  sind `29/29`. Reale disposable Tests decken den `main`-Negativpfad,
  Actor-/Repository-Falschwerte, einen URL-spezifischen Authorization-Header
  über echte Loopback-HTTP-Requests sowie ein ausführbares AskPass nach
  absichtlich fehlschlagender Helperkette ab. Definition-basierte vakuöse
  Reihenfolgechecks wurden durch markierte tatsächliche Callgates ersetzt.
- Task-3-Steps 3/4/5 sowie die Deployment-Steps 9/10 bestehen je `bash -n`
  und ShellCheck 0.11.0 ohne Befund. `make check` lief frisch als `teladi`
  unter `env -i` mit Exit 0: Applet-Runtime grün, Admin-UI `24/24`, SemVer
  `8/8`, Git-Object-Fallback `3/3`, Release-Publication `3/3`,
  Helper-Environment `7/7`, Applet-Sync `25/25`, Settings-Schema `14/14`,
  Story-Directives `31/31` und Rollout-Vertrag `29/29`.
- Auch diese Korrekturrunde blieb lokal: kein Fetch, Push, PR-Write, Merge,
  Install, Reload, Deploy, Runtime-, Service-, `systemctl`-, `gdbus`-,
  Cloudflare-, DNS- oder Upstreamzugriff. Schreibende Proben waren auf
  disposable lokale Repositories und Loopback beschränkt; der lokale
  `teladi`-Commit wird in der Übergabe ausgewiesen.

### 2026-08-02 — Additive CodeRabbit-Schlussremediation des Konfigurationskerns

- Dieser Abschnitt ist additiv und schließt genau die vier aktuellen
  CodeRabbit-Hinweise am geprüften PR-Head. Frühere Rollout- und
  Implementierungsevidenz bleibt als Auditspur erhalten. Es erfolgte weder
  eine Qlty-Komplexitäts-Großrefaktorierung noch eine Unterdrückung durch
  Suppressionskommentare.
- `_prepare_parent()` erzwingt für jede von ihm selbst neu erzeugte öffentliche
  Parent-Komponente einschließlich des finalen Parents deterministisch `0755`,
  auch unter `umask 0077`. Die Modussetzung verwendet einen mit
  `O_DIRECTORY | O_NOFOLLOW` geöffneten Deskriptor und `fchmod`; ein bereits
  vorhandener öffentlicher Zwischenparent wird nicht umchmodded. Der bestehende
  private `0700`-, Symlink- und Regular-file-Vertrag bleibt erhalten.
- Der Applet-Bridge-Vertrag exportiert nun `SettingsOperationLockError` und
  `exclusive_settings_lock` explizit über `__all__`. Die Lockpfadprüfung prüft
  Absolutheit konsistent nach `expanduser`, akzeptiert damit gültige
  `~/...`-Pfade und lehnt unverändert echte relative Pfade vor jeder Anlage ab.
- Die Admin-Livepolls verwenden die kleinste gemeinsame, testbare
  `fetchLivePoll(resource)`-Grenze. Die beiden internen Ressourcen bleiben fest
  an `/api/settings` und `/api/status` gebunden; beide Requests verwenden
  `cache: "no-store"` und je ein `AbortSignal.timeout(4000)`. Epoch-,
  In-flight-, Save- und Fehlersemantik der umgebenden Pollfunktionen blieb
  unverändert.
- Test-first-Evidenz: Der öffentliche Parenttest lief unter restriktiver umask
  zunächst mit `0700 != 0755` rot. Der Exportvertrag meldete die beiden
  fehlenden Namen. Der expandierte Homepfad wurde zunächst abgelehnt, während
  der relative Negativpfad bereits fail-closed blieb. Der neue Adminvertrag
  lief wegen der noch fehlenden `fetchLivePoll`-API rot. GREEN sind
  Settings-IO `12/12`, Applet-Sync `28/28` und Admin-UI `24/24`; die
  fünf fokussierten Locktests bestätigen zusätzlich Export, Homepfad,
  Relativpfad, Symlinkparent und nichtreguläres Ziel.
- Die direkt betroffene Matrix bestand `107` Python-Tests und erneut `24/24`
  Node-Tests. `make check` lief als UID/GID `teladi` unter `env -i` mit Exit 0:
  Applet-Runtime grün, Admin-UI `24/24`, SemVer `8/8`,
  Git-Object-Fallback `3/3`, Release-Publication `3/3`, Helper-Environment
  `7/7`, Applet-Sync `28/28`, Settings-Schema `14/14`, Story-Directives
  `31/31` und Rollout-Vertrag `29/29`. Ruff 0.15.16 prüfte die vier geänderten
  Python-Dateien ohne Befund; `node --check` und `git diff --check` waren grün.
- Beide vollständigen Profilbuilds und Validatoren liefen in derselben
  geheimnisfreien `teladi`-/`env -i`-Grenze. Hub: 823 Dateien, 818 HTML,
  10.840 interne Links, Baum-SHA-256
  `0acc6695654d3e82e450a3467d96995da89e59d954d00340d5a5028916ab1bb6`.
  Archiv: 823 Dateien, 818 HTML, 10.840 interne Links, Baum-SHA-256
  `f6e682fa639f72863f8911bb2b94d416ba83e913613797334361e439308a91bd`.
- Die Runde blieb vollständig lokal: kein Fetch, Push, PR-Kommentar, Merge,
  Install, Reload, Deploy, Runtime-/Ownership-/Service-/Pages-/DNS-/Cloudflare-
  oder Upstream-Write. Testwerte enthielten keine produktiven Geheimnisse; der
  lokale `teladi`-Commit wird in der Übergabe ausgewiesen.

### 2026-08-02 — Additive transaktionale Vollreview-Schließung, Run `814f2270-ed94-415a-a8bc-f460663dd0a3`

- Grundlage ist exakt der von CodeRabbit geprüfte SHA
  `a2f0cff98450b25bbd8ffe20f95b612cdd039e9b`; das Ergebnis war
  `CHANGES_REQUESTED` mit sechs Actionable Comments und sieben Nitpicks. Diese
  additive Autorenschicht schließt sämtliche 13 Hinweise, ohne historische
  Entscheidungen oder Evidenz aus dem Ledger zu entfernen.
- Applet und Weboberfläche bewahren nun für **alle** Choice- und Modellfelder
  externe, nicht mehr katalogisierte Werte als ausdrücklich beschriftete
  Legacy-Option. Das Applet verwendet dafür einen gemeinsamen Katalog-Combo-
  Pfad und baut bei jedem Snapshot alle passenden Felder unter
  `_suppress_dirty` neu auf; dadurch wird weder ein fremder gültiger Wert
  verworfen noch eine bloße Live-Aktualisierung als lokaler Entwurf markiert.
- Der CLI-Adminpfad behandelt ein vom kanonischen transaktionalen Managerpfad
  abweichendes `--settings` als redigierten Validierungsfehler: stabiles JSON,
  Exitcode 4, kein Traceback, keine Wiedergabe des gelieferten Pfades und kein
  Serverstart. Derselbe benannte Exitcode gilt auch für die bestehende
  Settingsvalidierung.
- Die Storyposition und `book_target_for_story` werden jetzt zusammen als eine
  lokale Statusquelle gelesen und abgeleitet. Nur der erwartete Typfehler
  dieser Ableitung wird in die bereits redigierte Quellenausnahme übersetzt;
  andere Programmierfehler werden nicht pauschal verschluckt. Der im Review
  genannte malformed-JSON-Fall war bereits durch `StateStore` zu `RuntimeError`
  normalisiert und damit degradiert; ein eigener Baseline-Test dokumentiert
  das. Der neue rote Regressionsfall adressiert stattdessen den tatsächlich
  offenen, kontrolliert simulierten Nachlade-Typfehler und bestätigt, dass nur
  die Storyquelle ausfällt, während die Konfiguration gültig bleibt.
- Die Admin-Save-Grenze liest JSON defensiv und klassifiziert 409-Konflikt,
  sonstige Ablehnung und Erfolg anhand des HTTP-Status. Leere, kaputte oder
  typwidrige Fehlerpayloads erhalten einen festen redigierten Fallback;
  erfolgreiche Antworten müssen ein vollständiger Snapshot mit ausdrücklich
  `ok: true` sein. Konfliktpayloads behalten ihren separaten öffentlichen
  Snapshotvertrag, der serverseitig absichtlich kein Erfolgsflag benötigt.
- Settings-Polls melden Fehler ausschließlich in `#poll-status` und löschen
  diese Meldung nach der nächsten gültigen Antwort, ohne `#save-status` und
  damit Konflikt-/Speicherevidenz zu überschreiben. Die eigene Liveregion ist
  `role=status`/`aria-live=polite`. Numerisch ungültige Felder besitzen neben
  dem bestehenden semantischen Zustand nun eine sichtbare `.is-invalid`-
  Kontur.
- Der Bootstrap ist fail-closed: Die Settingscontrols werden vor dem
  CSRF-Zugriff gesperrt. Fehlendes oder leeres CSRF erzeugt eine sichtbare,
  redigierte Meldung und lässt sie gesperrt; jede unerwartete asynchrone
  Initialisierungsablehnung wird am obersten Einstieg abgefangen, erneut
  gesperrt und ohne interne Fehlerdetails angezeigt. Ein vollständiger,
  validierter erster Snapshot bleibt die einzige Freigabegrenze.
- Die zwei früheren Quelltext-Substringtests wurden durch Verhaltensproben für
  transienten modalen Dialog samt Cleanup und für sämtliche Kombinationen des
  gemeinsamen Save-/Operation-Busy-Guards ersetzt. Die beiden identischen
  Plattform-Snapshotbuilder liegen nun in
  `tests/platform/_settings_fixtures.py`; Paket- und direkte Discovery-Imports
  werden beide unterstützt.
- RED-Evidenz: Task-5-Fence zunächst zwei neue Tests mit vier Errors/einem
  Failure; Applet-Legacy-Refresh ein Failure; CLI-Mismatch ein Error;
  Storyableitung ein Error; Adminmatrix sechs Failures. GREEN: reale
  Task-5-Rootproben `3/3`, Rolloutvertrag `32/32`, Admin `31/31`, Applet-Sync
  `28/28`, Schema `15/15`, komplette Plattform-Discovery `147/147`, Webtests
  `9/9` und Astro-Check 22 Dateien ohne Diagnostik.
- `make check` bestand frisch als UID/GID `teladi` unter `env -i`; die zwei
  rootgebundenen Task-5-Ausführungsproben sind im normalen Teladi-Lauf die
  einzigen erwarteten Skips. Beide vollständigen, unveränderlichen
  Siteprofile bestanden mit jeweils 823 Dateien, 818 HTML und 10.840 geprüften
  internen Links. Hub-Baum-SHA-256:
  `0acc6695654d3e82e450a3467d96995da89e59d954d00340d5a5028916ab1bb6`;
  Archiv-Baum-SHA-256:
  `f6e682fa639f72863f8911bb2b94d416ba83e913613797334361e439308a91bd`.
- `compileall`, `node --check` und `git diff --check` waren grün. Ruff meldete
  auf allen geänderten Pythonpfaden keinen neuen Befund; nur die schon am
  geprüften Basis-SHA vorhandenen dateiweiten Baselineausnahmen des Applets
  und die unveränderten `I001`-/`RUF001`-Altstellen im Rollouttest wurden
  explizit ausgeklammert. Eigentumsscan: null Abweichungen von
  `teladi:teladi`; High-Confidence-Secretmusterscan über Diff und neue Fixture:
  null Treffer.
- Diese Runde blieb lokal und geheimnisfrei: kein Zugriff auf Credentials,
  kein Fetch, Push, PR-Write, Merge, Install, Reload, Deploy, Runtime-,
  Service-, Applet-, Archiv-, Pages-, DNS-, Cloudflare- oder Upstream-Write.
  Task 5 wurde ausschließlich als Planvertrag und gegen disposable lokale
  Fixtures geprüft; seine spätere Remoteausführung bleibt ein getrenntes,
  erneut zu gateendes Rolloutereignis.
