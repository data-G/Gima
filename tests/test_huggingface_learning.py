import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from human_ai.config import Config
from human_ai.huggingface_learning import HuggingFaceLearner, extract_huggingface_url
from human_ai.memory import MemoryStore


class HuggingFaceLearningTests(unittest.TestCase):
    def test_extracts_public_huggingface_url(self):
        self.assertEqual(
            extract_huggingface_url("learn https://huggingface.co/empero-ai/Qwythos-9B-Claude-Mythos-5-1M-GGUF now"),
            "https://huggingface.co/empero-ai/Qwythos-9B-Claude-Mythos-5-1M-GGUF",
        )

    def test_learns_model_metadata_card_and_recommendations(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = Config(workspace=root, data_dir=Path(".human-ai"))
            memory = MemoryStore(config.resolved_data_dir)
            metadata = {
                "id": "owner/test-gguf",
                "pipeline_tag": "text-generation",
                "library_name": "llama.cpp",
                "tags": ["gguf", "chat", "text-generation"],
                "cardData": {"license": "apache-2.0"},
                "siblings": [{"rfilename": "model-q4_k_m.gguf"}, {"rfilename": "README.md"}],
            }

            def fake_fetch(url):
                if url == "https://huggingface.co/api/models/owner/test-gguf":
                    return json.dumps(metadata)
                if url == "https://huggingface.co/owner/test-gguf/raw/main/README.md":
                    return "A GGUF chat model card with benchmark and eval notes."
                raise AssertionError(url)

            with patch("human_ai.huggingface_learning.WebImporter.fetch", side_effect=fake_fetch):
                result = HuggingFaceLearner(config, memory).learn("https://huggingface.co/owner/test-gguf")

            self.assertEqual(result.repo_id, "owner/test-gguf")
            self.assertEqual(result.repo_type, "model")
            self.assertEqual(len(result.files), 3)
            self.assertTrue(any("local model candidate" in item for item in result.recommendations))
            self.assertTrue(any("conversation" in item for item in result.recommendations))
            self.assertTrue((config.resolved_hands_out_dir / "huggingface_learning").exists())
            rows = memory.list_by_status("review", 5)
            self.assertTrue(rows)
            self.assertEqual(rows[0]["status"], "review")
            reviews = memory.list_source_reviews("pending", 5)
            self.assertTrue(any(review["record_id"] == result.record_id for review in reviews))

    def test_learns_top_level_model_id(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Config(workspace=Path(temp), data_dir=Path(".human-ai"))
            memory = MemoryStore(config.resolved_data_dir)

            def fake_fetch(url):
                if url == "https://huggingface.co/api/models/gpt2":
                    return json.dumps({"id": "gpt2", "pipeline_tag": "text-generation", "siblings": []})
                if url == "https://huggingface.co/gpt2/raw/main/README.md":
                    return "GPT-2 model card."
                raise AssertionError(url)

            with patch("human_ai.huggingface_learning.WebImporter.fetch", side_effect=fake_fetch):
                result = HuggingFaceLearner(config, memory).learn("https://huggingface.co/gpt2")

            self.assertEqual(result.repo_id, "gpt2")
            self.assertEqual(result.repo_type, "model")


if __name__ == "__main__":
    unittest.main()
