"""Canonical, presentation-neutral settings schema for every local client."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from .naming import ARCHIVE_CAPACITY, BOOKS_PER_ARCHIVE, STORIES_PER_BOOK

SETTINGS_SCHEMA_VERSION = "2.0.0"
IMAGE_MODEL_CHOICES = ("gpt-image-2", "gpt-image-1.5", "gpt-image-1", "gpt-image-1-mini")
STORY_MODEL_CHOICES = (
    "gpt-5.5",
    "gpt-5.5-pro",
    "gpt-5.4",
    "gpt-5.4-mini",
    "gpt-5.4-nano",
    "gpt-5.4-pro",
    "gpt-5.2",
    "gpt-5.2-pro",
    "gpt-5.1",
    "gpt-5",
    "gpt-5-mini",
    "gpt-5-nano",
    "gpt-5-pro",
    "gpt-4.1",
    "gpt-4.1-mini",
    "gpt-4.1-nano",
    "gpt-4o",
    "gpt-4o-mini",
)
ValueKind = Literal["string", "integer", "boolean"]
_HEX32 = re.compile(r"[0-9a-f]{32}")


class SettingsValidationError(ValueError):
    """A sparse settings change violates the shared public contract."""


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
    open_choices: bool = False
    pattern: re.Pattern[str] | None = None
    web_visible: bool = False
    applet_visible: bool = False


def _string(
    env_name: str,
    default: str,
    *,
    choices: tuple[str, ...] = (),
    max_length: int,
    allow_empty: bool = False,
    open_choices: bool = False,
    pattern: re.Pattern[str] | None = None,
    web: bool = False,
    applet: bool = False,
) -> SettingSpec:
    return SettingSpec(
        env_name,
        default,
        "string",
        choices=choices,
        max_length=max_length,
        allow_empty=allow_empty,
        open_choices=open_choices,
        pattern=pattern,
        web_visible=web,
        applet_visible=applet,
    )


def _integer(
    env_name: str | None,
    default: int,
    *,
    minimum: int,
    maximum: int,
    web: bool = False,
    applet: bool = False,
) -> SettingSpec:
    return SettingSpec(
        env_name,
        default,
        "integer",
        minimum=minimum,
        maximum=maximum,
        web_visible=web,
        applet_visible=applet,
    )


def _boolean(
    env_name: str | None,
    default: bool,
    *,
    web: bool = False,
    applet: bool = False,
) -> SettingSpec:
    return SettingSpec(env_name, default, "boolean", web_visible=web, applet_visible=applet)


SETTING_SPECS: dict[str, SettingSpec] = {
    "operandi": _string(
        "WIRTELPRIMPF_OPERANDI",
        "story",
        choices=("classic", "story", "both"),
        max_length=7,
        web=True,
        applet=True,
    ),
    "image_model": _string(
        "WIRTELPRIMPF_IMAGE_MODEL",
        "gpt-image-2",
        choices=IMAGE_MODEL_CHOICES,
        open_choices=True,
        max_length=80,
        web=True,
        applet=True,
    ),
    "story_model": _string(
        "WIRTELPRIMPF_STORY_MODEL",
        "gpt-5-mini",
        choices=STORY_MODEL_CHOICES,
        open_choices=True,
        max_length=80,
        web=True,
        applet=True,
    ),
    "image_size": _string(
        "WIRTELPRIMPF_IMAGE_SIZE",
        "1536x1024",
        choices=("1024x1024", "1536x1024", "1024x1536"),
        max_length=9,
        web=True,
        applet=True,
    ),
    "output_resolution": _string(
        "WIRTELPRIMPF_OUTPUT_RESOLUTION",
        "2k",
        choices=("source", "2k", "4k"),
        max_length=6,
        web=True,
        applet=True,
    ),
    "generation_interval_minutes": _integer(
        "WIRTELPRIMPF_GENERATION_INTERVAL_MINUTES", 120, minimum=30, maximum=10_080, web=True, applet=True
    ),
    "publish_immediately": _boolean(
        "WIRTELPRIMPF_PUBLISH_IMMEDIATELY", True, web=True, applet=True
    ),
    "story_finish_parts_min": _integer(
        "WIRTELPRIMPF_STORY_FINISH_PARTS_MIN", 3, minimum=1, maximum=12, web=True, applet=True
    ),
    "story_finish_parts_max": _integer(
        "WIRTELPRIMPF_STORY_FINISH_PARTS_MAX", 5, minimum=1, maximum=12, web=True, applet=True
    ),
    "site_title": _string(
        "WIRTELPRIMPF_SITE_TITLE", "Wirtelprimpfs Geschichtenatelier", max_length=120, web=True
    ),
    "site_intro": _string(
        "WIRTELPRIMPF_SITE_INTRO",
        "Zwei Katzen, eine Möhre, eine Maus und ein fortlaufendes Abenteuer.",
        max_length=500,
        web=True,
    ),
    "local_outdir": _string(
        "WIRTELPRIMPF_LOCAL_OUTDIR", "", max_length=4096, allow_empty=True, applet=True
    ),
    "working_dir": _string(
        "WIRTELPRIMPF_WORKING_DIR", "", max_length=4096, allow_empty=True, applet=True
    ),
    "repo_path": _string(
        "WIRTELPRIMPF_REPO_PATH",
        "~/.local/share/wirtelprimpf/archives/Wirtelprimpf-0001",
        max_length=4096,
        applet=True,
    ),
    "repo_slug": _string(
        "WIRTELPRIMPF_REPO_SLUG", "H234598/Wirtelprimpf-0001", max_length=255, applet=True
    ),
    "repo_subdir": _string(
        "WIRTELPRIMPF_REPO_SUBDIR", "Wirtelprimpf", max_length=255, allow_empty=True, applet=True
    ),
    "repo_branch": _string("WIRTELPRIMPF_REPO_BRANCH", "main", max_length=255, applet=True),
    "github_owner": _string("WIRTELPRIMPF_GITHUB_OWNER", "H234598", max_length=255, applet=True),
    "media_mode": _string(
        "WIRTELPRIMPF_MEDIA_MODE", "release", choices=("release", "git"), max_length=7, applet=True
    ),
    "media_staging": _string(
        "WIRTELPRIMPF_MEDIA_STAGING",
        "~/.local/state/wirtelprimpf/media-staging",
        max_length=4096,
        applet=True,
    ),
    "platform_state": _string(
        "WIRTELPRIMPF_PLATFORM_STATE",
        "~/.local/state/wirtelprimpf/platform-state.json",
        max_length=4096,
        applet=True,
    ),
    "hub_dispatch_state": _string(
        "WIRTELPRIMPF_HUB_DISPATCH_STATE",
        "~/.local/state/wirtelprimpf/hub-dispatch.json",
        max_length=4096,
        applet=True,
    ),
    "generator_root": _string(
        "WIRTELPRIMPF_GENERATOR_ROOT", "~/.local/share/wirtelprimpf-generator", max_length=4096, applet=True
    ),
    "archive_root": _string(
        "WIRTELPRIMPF_ARCHIVE_ROOT", "~/.local/share/wirtelprimpf/archives", max_length=4096, applet=True
    ),
    "platform_catalog": _string(
        "WIRTELPRIMPF_PLATFORM_CATALOG",
        "~/.local/share/wirtelprimpf-generator/data/publication-catalog.json",
        max_length=4096,
        applet=True,
    ),
    "settings_path": _string(
        "WIRTELPRIMPF_SETTINGS_PATH", "~/.config/wirtelprimpf/openai.env", max_length=4096, applet=True
    ),
    "cloudflare_zone": _string("WIRTELPRIMPF_CLOUDFLARE_ZONE", "telacore.org", max_length=253, applet=True),
    "cloudflare_zone_id": _string(
        "WIRTELPRIMPF_CLOUDFLARE_ZONE_ID",
        "",
        max_length=32,
        allow_empty=True,
        pattern=_HEX32,
        applet=True,
    ),
    "git_author_name": _string(
        "WIRTELPRIMPF_GIT_AUTHOR_NAME", "", max_length=255, allow_empty=True, applet=True
    ),
    "git_author_email": _string(
        "WIRTELPRIMPF_GIT_AUTHOR_EMAIL", "", max_length=320, allow_empty=True, applet=True
    ),
    "flex_processing": _string(
        "WIRTELPRIMPF_FLEX_PROCESSING",
        "on",
        choices=("on", "off", "flex"),
        max_length=4,
        applet=True,
    ),
    "prompt_config": _string(
        "WIRTELPRIMPF_PROMPT_CONFIG", "", max_length=4096, allow_empty=True, applet=True
    ),
    "story_prompt_config": _string(
        "WIRTELPRIMPF_STORY_PROMPT_CONFIG", "", max_length=4096, allow_empty=True, applet=True
    ),
    "story_document": _string(
        "WIRTELPRIMPF_STORY_DOCUMENT", "", max_length=4096, allow_empty=True, applet=True
    ),
    "story_state": _string(
        "WIRTELPRIMPF_STORY_STATE", "", max_length=4096, allow_empty=True, applet=True
    ),
    "story_finish": _boolean("WIRTELPRIMPF_STORY_FINISH", False, applet=True),
    "timer_enabled": _boolean(None, True, applet=True),
    "timer_randomized_delay_seconds": _integer(None, 120, minimum=0, maximum=86_400, applet=True),
    "timer_persistent": _boolean(None, True, applet=True),
}


def validate_changes(changes: Mapping[str, object], current: Mapping[str, object]) -> dict[str, object]:
    """Validate a sparse update, including invariants against current values."""

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
            if not isinstance(value, str) or any(character in value for character in "\x00\r\n"):
                raise SettingsValidationError(f"{key} must be a single-line string")
            value = value.strip()
            if not value and not spec.allow_empty:
                raise SettingsValidationError(f"{key} must not be empty")
            if spec.max_length is not None and len(value) > spec.max_length:
                raise SettingsValidationError(f"{key} exceeds {spec.max_length} characters")
            if value and spec.pattern is not None and spec.pattern.fullmatch(value) is None:
                raise SettingsValidationError(f"{key} has an invalid format")
            # ``open_choices`` means the centrally served catalog may evolve;
            # it does not authorize free-form client submissions.  A legacy
            # value may only remain byte-for-byte unchanged.
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
    numeric_bounds = {
        key: {"minimum": SETTING_SPECS[key].minimum, "maximum": SETTING_SPECS[key].maximum}
        for key in (
            "generation_interval_minutes",
            "story_finish_parts_min",
            "story_finish_parts_max",
        )
    }
    return {
        "archive_capacity": ARCHIVE_CAPACITY,
        "books_per_archive": BOOKS_PER_ARCHIVE,
        "repository_pattern": "Wirtelprimpf-####",
        "domain_suffix": "telacore.org",
        "stories_per_book": STORIES_PER_BOOK,
        "story_order_on_landing_page": "newest-first",
        "numeric_bounds": numeric_bounds,
    }
