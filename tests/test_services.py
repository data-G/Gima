import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from human_ai.config import Config
from human_ai.memory import MemoryStore
from human_ai.services import SafeToolRunner, TeacherModelClient, WebImporter


class ServiceSafetyTests(unittest.TestCase):
    def test_web_import_blocks_local_addresses(self):
        with self.assertRaises(PermissionError):
            WebImporter([]).fetch("http://127.0.0.1/private")

    def test_tool_runner_is_disabled_by_default(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Config(workspace=Path(temp))
            memory = MemoryStore(config.resolved_data_dir)
            with self.assertRaises(PermissionError):
                SafeToolRunner(config, memory).run(["git", "status"])

    def test_tool_runner_rejects_non_allowlisted_command(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Config(workspace=Path(temp))
            config.tools.enabled = True
            config.permissions.require_scoped_grants = False
            memory = MemoryStore(config.resolved_data_dir)
            with self.assertRaises(PermissionError):
                SafeToolRunner(config, memory).run(["rm", "-rf", "something"])

    def test_web_search_falls_back_to_wikipedia(self):
        importer = WebImporter([])
        with patch.object(importer, "_duckduckgo_search", return_value=[]), patch.object(
            importer, "_wikipedia_search", return_value=["https://en.wikipedia.org/wiki/Large_language_model"]
        ):
            self.assertEqual(
                importer.search("large language model", limit=1),
                ["https://en.wikipedia.org/wiki/Large_language_model"],
            )

    def test_teacher_model_requires_known_provider(self):
        with self.assertRaises(ValueError):
            TeacherModelClient(Config()).ask("unknown", "hello")

    def test_openai_response_text_is_parsed(self):
        client = TeacherModelClient(Config())
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test"}), patch(
            "urllib.request.urlopen"
        ) as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = (
                b'{"output_text":"teacher answer"}'
            )
            self.assertEqual(client.ask("chatgpt", "hello"), "teacher answer")

    def test_gemini_response_text_is_parsed(self):
        client = TeacherModelClient(Config())
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test"}), patch(
            "urllib.request.urlopen"
        ) as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = (
                b'{"candidates":[{"content":{"parts":[{"text":"gemini answer"}]}}]}'
            )
            self.assertEqual(client.ask("gemini", "hello"), "gemini answer")


if __name__ == "__main__":
    unittest.main()
