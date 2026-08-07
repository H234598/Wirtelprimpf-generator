from __future__ import annotations

import importlib.util
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = ROOT / "Sourcecode" / "wirtelprimpf_generator.py"


def load_generator():
    spec = importlib.util.spec_from_file_location("wirtelprimpf_generator_flex_test", GENERATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load generator module from {GENERATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeImages:
    def __init__(self, failures: list[Exception]) -> None:
        self.failures = list(failures)
        self.requests: list[dict[str, object]] = []

    def generate(self, **request: object):
        self.requests.append(request)
        if self.failures:
            raise self.failures.pop(0)
        return SimpleNamespace(data=[SimpleNamespace(b64_json="image-data")])


class FakeClient:
    def __init__(self, failures: list[Exception]) -> None:
        self.images = FakeImages(failures)


class FakeResponses:
    def __init__(self) -> None:
        self.requests: list[dict[str, object]] = []

    def create(self, **request: object):
        self.requests.append(request)
        return SimpleNamespace(output_text="x" * 600)


class FlexContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.generator = load_generator()

    def test_flex_is_default_and_explicit_activation(self) -> None:
        with patch.dict(os.environ, {"WIRTELPRIMPF_FLEX_PROCESSING": ""}, clear=False):
            self.assertEqual(self.generator.parse_flex_processing(), "flex")
        for value in ("on", "true", "yes", "enabled", "flex"):
            with self.subTest(value=value), patch.dict(
                os.environ, {"WIRTELPRIMPF_FLEX_PROCESSING": value}, clear=False
            ):
                self.assertEqual(self.generator.parse_flex_processing(), "flex")

    def test_only_explicit_service_tier_unsupported_error_drops_flex_once(self) -> None:
        request = {"model": "gpt-image-2", "prompt": "cat"}
        client = FakeClient([RuntimeError("temporary timeout")])

        with patch.object(self.generator.time, "sleep"):
            result = self.generator.generate_image_with_retries(client, request)

        self.assertEqual(result, "image-data")
        self.assertEqual(len(client.images.requests), 2)
        self.assertTrue(all("extra_body" not in item for item in client.images.requests))

    def test_story_text_receives_flex_service_tier(self) -> None:
        client = FakeClient([])
        client.responses = FakeResponses()

        result = self.generator.generate_story_part(
            client,
            model="gpt-5-mini",
            story_config="rules",
            recent_entries=["history"],
            service_tier="flex",
        )

        self.assertEqual(len(result), 600)
        self.assertEqual(client.responses.requests[0]["service_tier"], "flex")


if __name__ == "__main__":
    unittest.main()
