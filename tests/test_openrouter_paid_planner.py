import json
import tempfile
import unittest
from pathlib import Path

from human_ai.config import Config
from human_ai.openrouter_paid_planner import paid_openrouter_plan


class OpenRouterPaidPlannerTests(unittest.TestCase):
    def test_paid_plan_uses_cached_catalog_and_writes_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Config(workspace=Path(temp))
            cache_dir = config.resolved_data_dir / "openrouter"
            cache_dir.mkdir(parents=True, exist_ok=True)
            (cache_dir / "models_catalog.json").write_text(
                json.dumps(
                    {
                        "data": [
                            {
                                "id": "openai/gpt-4o",
                                "name": "GPT-4o",
                                "context_length": 128000,
                                "architecture": {"input_modalities": ["text", "image"], "output_modalities": ["text"]},
                                "pricing": {"prompt": "0.0000025", "completion": "0.00001"},
                            },
                            {
                                "id": "deepseek/deepseek-chat",
                                "name": "DeepSeek Chat",
                                "context_length": 64000,
                                "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
                                "pricing": {"prompt": "0.00000014", "completion": "0.00000028"},
                            },
                            {
                                "id": "google/veo-3.1",
                                "name": "Veo 3.1",
                                "architecture": {"input_modalities": ["text"], "output_modalities": ["video"]},
                                "pricing": {"request": "0.4"},
                            },
                            {
                                "id": "openai/gpt-image-1",
                                "name": "GPT Image",
                                "architecture": {"input_modalities": ["text"], "output_modalities": ["image"]},
                                "pricing": {"request": "0.04"},
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            payload = paid_openrouter_plan(config)
            csv_text = Path(payload["files"]["csv"]).read_text(encoding="utf-8")
            markdown = Path(payload["files"]["markdown"]).read_text(encoding="utf-8")

        self.assertEqual(payload["source"], "cache")
        self.assertIn("cost_controls", payload)
        self.assertIn("files", payload)
        areas = {row["area"]: row for row in payload["recommendations"]}
        self.assertEqual(areas["Main powerful brain"]["paid_model_type"], "GPT / Claude / Gemini flagship models")
        self.assertEqual(areas["Cheap daily assistant"]["cheap_choice"], "deepseek/deepseek-chat")
        self.assertEqual(areas["Video generation"]["first_choice"], "google/veo-3.1")
        self.assertIn("submit, poll status, and download", areas["Video generation"]["note"])
        self.assertEqual(areas["Agent/tool calling"]["local_fallback"], "Ollama local tools")
        self.assertIn("paid_model_type", csv_text)
        self.assertIn("Web research/report writing", csv_text)
        self.assertIn("| Area | Best paid API model type | Use in Gima |", markdown)
        self.assertIn("Models with tool/function calling", markdown)

    def test_paid_plan_can_skip_file_writes(self):
        payload = paid_openrouter_plan(Config(), write_files=False)
        self.assertNotIn("files", payload)
        self.assertTrue(any(row["layer"] == "Free local daily AI" for row in payload["architecture"]))


if __name__ == "__main__":
    unittest.main()
