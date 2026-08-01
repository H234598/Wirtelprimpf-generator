from __future__ import annotations

import unittest

from wirtelprimpf_platform.settings_schema import (
    IMAGE_MODEL_CHOICES,
    SETTING_SPECS,
    STORY_MODEL_CHOICES,
    SettingsValidationError,
    choices_payload,
    invariants_payload,
    validate_changes,
)


class SettingsSchemaTests(unittest.TestCase):
    def test_model_catalogs_are_ordered_and_shared_fields_are_visible(self) -> None:
        self.assertEqual(
            IMAGE_MODEL_CHOICES,
            ("gpt-image-2", "gpt-image-1.5", "gpt-image-1", "gpt-image-1-mini"),
        )
        self.assertEqual(
            STORY_MODEL_CHOICES[0:6],
            ("gpt-5.5", "gpt-5.5-pro", "gpt-5.4", "gpt-5.4-mini", "gpt-5.4-nano", "gpt-5.4-pro"),
        )
        self.assertTrue(SETTING_SPECS["image_model"].web_visible)
        self.assertTrue(SETTING_SPECS["image_model"].applet_visible)
        self.assertFalse(SETTING_SPECS["site_title"].applet_visible)
        self.assertEqual(choices_payload()["story_model"], list(STORY_MODEL_CHOICES))

    def test_changed_model_must_be_catalogued_but_legacy_value_may_remain(self) -> None:
        current = {key: spec.default for key, spec in SETTING_SPECS.items()}
        current["story_model"] = "retired-story-model"
        self.assertEqual(
            validate_changes({"story_model": "retired-story-model"}, current)["story_model"],
            "retired-story-model",
        )
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

    def test_boolean_integer_and_single_line_types_cannot_cross_coerce(self) -> None:
        current = {key: spec.default for key, spec in SETTING_SPECS.items()}
        invalid = (
            ({"publish_immediately": 1}, "publish_immediately"),
            ({"generation_interval_minutes": True}, "generation_interval_minutes"),
            ({"site_title": "line one\nline two"}, "site_title"),
        )
        for changes, field in invalid:
            with self.subTest(field=field), self.assertRaisesRegex(SettingsValidationError, field):
                validate_changes(changes, current)

    def test_public_invariants_report_story_and_archive_boundaries(self) -> None:
        self.assertEqual(
            invariants_payload(),
            {
                "archive_capacity": 50,
                "books_per_archive": 5,
                "repository_pattern": "Wirtelprimpf-####",
                "domain_suffix": "telacore.org",
                "stories_per_book": 10,
                "story_order_on_landing_page": "newest-first",
            },
        )


if __name__ == "__main__":
    unittest.main()
