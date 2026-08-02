from __future__ import annotations

from wirtelprimpf_platform.settings import SettingsSnapshot


def snapshot_for_test(*, revision: str, settings: dict[str, object]) -> SettingsSnapshot:
    return SettingsSnapshot(
        schema_version="2.0.0",
        revision=revision,
        settings=settings,
        choices={},
        secrets={
            "openai_api_key_present": False,
            "cloudflare_api_token_present": False,
            "github_auth_present": False,
        },
        invariants={},
        warnings=(),
    )
