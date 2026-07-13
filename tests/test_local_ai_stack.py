import unittest
import tempfile
from pathlib import Path

from human_ai.config import Config
from human_ai.local_ai_stack import local_ai_stack_payload


class LocalAiStackTests(unittest.TestCase):
    def test_payload_matches_i7_7700hq_laptop_and_writes_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Config(workspace=Path(temp))
            payload = local_ai_stack_payload(config)
            csv_text = Path(payload["files"]["csv"]).read_text(encoding="utf-8")
            markdown = Path(payload["files"]["markdown"]).read_text(encoding="utf-8")

        self.assertEqual(payload["hardware"]["ram_gb"], 16)
        self.assertIn("i7-7700HQ", payload["hardware"]["cpu"])
        self.assertTrue(any(row["tool"] == "LM Studio" for row in payload["tools"]))
        self.assertTrue(any(row["area"] == "Editing video" and row["tool"] == "CapCut / DaVinci Resolve" for row in payload["tools"]))
        self.assertTrue(any(row["area"] == "Local knowledge base" and row["works_on_laptop"] == "Yes" for row in payload["tools"]))
        self.assertTrue(any(row["area"] == "Live conversation AI" and "Whisper.cpp + Ollama + Piper" in row["tool"] for row in payload["tools"]))
        self.assertTrue(any(row["area"] == "Terminal coding agent" and "review-gated" in row["notes"] for row in payload["tools"]))
        self.assertTrue(any(row["area"] == "Automation and app control" for row in payload["tools"]))
        self.assertTrue(any(row["tool"] == "Ollama" for row in payload["install_order"]))
        self.assertIn("ollama pull qwen2.5:7b", payload["ollama_commands"])
        self.assertIn("ollama pull nomic-embed-text", payload["ollama_commands"])
        self.assertIn("csv", payload["files"])
        self.assertIn("update_possible", csv_text)
        self.assertIn("Live conversation AI", csv_text)
        self.assertIn("Not practical without GPU", csv_text)
        self.assertIn("| Area | Best system | Update possible? |", markdown)
        self.assertIn("A real local conversation AI needs a pipeline", "\n".join(payload["truth"]))

    def test_payload_can_skip_writing_files(self):
        payload = local_ai_stack_payload(Config(), write_files=False)
        self.assertNotIn("files", payload)
        self.assertTrue(any(row["model_size"] == "7B Q4" and row["fit"] == "Usable" for row in payload["model_sizes"]))


if __name__ == "__main__":
    unittest.main()
