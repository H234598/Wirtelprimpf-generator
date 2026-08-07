from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = ROOT / "Sourcecode" / "wirtelprimpf_generator.py"


def load_generator():
    spec = importlib.util.spec_from_file_location("wirtelprimpf_generator_batch_test", GENERATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load generator module from {GENERATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeFiles:
    def __init__(self, output: str = "") -> None:
        self.output = output
        self.create_calls: list[dict[str, object]] = []
        self.content_calls: list[str] = []

    def create(self, **request: object):
        self.create_calls.append(request)
        return SimpleNamespace(id="input-file")

    def content(self, file_id: str):
        self.content_calls.append(file_id)
        return SimpleNamespace(read=lambda: self.output)


class FakeBatches:
    def __init__(self, status: str = "completed") -> None:
        self.status = status
        self.create_calls: list[dict[str, object]] = []
        self.retrieve_calls: list[str] = []

    def create(self, **request: object):
        self.create_calls.append(request)
        return SimpleNamespace(id="batch-1")

    def retrieve(self, batch_id: str):
        self.retrieve_calls.append(batch_id)
        return SimpleNamespace(status=self.status, output_file_id="output-file")


class FakeClient:
    def __init__(self, *, status: str = "completed", output: str = "") -> None:
        self.files = FakeFiles(output)
        self.batches = FakeBatches(status)


class ImageBatchContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.generator = load_generator()

    def _config(self, root: Path):
        return SimpleNamespace(
            working_dir=root,
            image_model="gpt-image-2",
            image_size="1536x1024",
            story_document_path=root / "Wirtelprimpf_Story_I.md",
        )

    def test_batch_mode_parser_is_fail_closed(self) -> None:
        with patch.dict(os.environ, {"WIRTELPRIMPF_IMAGE_BATCH_MODE": ""}, clear=False):
            self.assertEqual(self.generator.parse_image_batch_mode(), "off")
        with self.assertRaises(ValueError):
            with patch.dict(os.environ, {"WIRTELPRIMPF_IMAGE_BATCH_MODE": "invalid"}, clear=False):
                self.generator.parse_image_batch_mode()

    def test_submit_uses_image_endpoint_without_flex(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            client = FakeClient()
            plan = self.generator.GenerationPlan(prompt="A cat in an atelier", kind=self.generator.OPERANDI_CLASSIC)

            self.generator._submit_image_batch(self._config(root), client, [plan])

            input_payload = client.files.create_calls[0]["file"]
            self.assertIsInstance(input_payload, tuple)
            request = json.loads(input_payload[1].decode("utf-8").strip())
            self.assertEqual(request["url"], "/v1/images/generations")
            self.assertEqual(request["body"]["model"], "gpt-image-2")
            self.assertEqual(request["body"]["quality"], "high")
            self.assertNotIn("service_tier", request["body"])
            self.assertEqual(client.batches.create_calls[0]["endpoint"], "/v1/images/generations")
            self.assertTrue((root / self.generator.IMAGE_BATCH_PENDING_NAME).is_file())

    def test_resume_completed_batch_rehydrates_plan_and_removes_state(self) -> None:
        output = json.dumps(
            {
                "custom_id": "wirtelprimpf-0001",
                "response": {"body": {"data": [{"b64_json": "aW1hZ2U="}]}},
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = self._config(root)
            client = FakeClient(output=output)
            plan = self.generator.GenerationPlan(prompt="A cat in an atelier", kind=self.generator.OPERANDI_CLASSIC)
            pending = {
                "version": 1,
                "batch_id": "batch-1",
                "input_file_id": "input-file",
                "entries": [
                    {
                        "custom_id": "wirtelprimpf-0001",
                        "stem": "wirtelprimpf_2026-08-07_00-00-00-000000",
                        "plan": self.generator._serialize_generation_plan(plan),
                    }
                ],
            }
            pending_path = root / self.generator.IMAGE_BATCH_PENDING_NAME
            pending_path.write_text(json.dumps(pending), encoding="utf-8")

            resumed = self.generator._resume_image_batch(config, client)

            self.assertIsNotNone(resumed)
            plans, stems, images = resumed
            self.assertEqual(plans[0].prompt, plan.prompt)
            self.assertEqual(stems[1], "wirtelprimpf_2026-08-07_00-00-00-000000")
            self.assertEqual(images[stems[1]], "aW1hZ2U=")
            self.assertFalse(pending_path.exists())

    def test_pending_batch_is_retryable_without_deleting_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pending_path = root / self.generator.IMAGE_BATCH_PENDING_NAME
            pending_path.write_text(
                json.dumps({"version": 1, "batch_id": "batch-1", "input_file_id": "input-file"}),
                encoding="utf-8",
            )
            client = FakeClient(status="in_progress")

            with self.assertRaises(self.generator.ImageBatchPending):
                self.generator._resume_image_batch(self._config(root), client)
            self.assertTrue(pending_path.exists())


if __name__ == "__main__":
    unittest.main()
