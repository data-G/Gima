import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from human_ai.brain import BrainServer
from human_ai.config import Config
from human_ai.memory import MemoryStore


class BrainServerTests(unittest.TestCase):
    def test_status_uses_healthy_endpoint_when_pid_file_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Config(workspace=Path(temp))
            config.model.model = "model.gguf"
            config.model.model_path = str(Path(temp) / "model.gguf")
            memory = MemoryStore(config.resolved_data_dir)
            memory.initialize()
            brain = BrainServer(config, memory)
            with patch.object(brain, "_models", return_value={"data": [{"id": "model.gguf"}]}):
                status = brain.status()
            self.assertTrue(status["running"])
            self.assertTrue(status["ready"])
            self.assertIsNone(status["pid"])

    def test_status_discards_pid_reused_by_another_process(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Config(workspace=Path(temp))
            memory = MemoryStore(config.resolved_data_dir)
            memory.initialize()
            brain = BrainServer(config, memory)
            brain.pid_path.write_text("123", encoding="utf-8")
            process = type("ProcessResult", (), {"returncode": 0, "stdout": "/usr/bin/python3 other_app.py"})()
            with patch("human_ai.brain.os.kill"), patch("human_ai.brain.subprocess.run", return_value=process), patch.object(
                brain, "_models", return_value=None
            ):
                status = brain.status()
            self.assertFalse(status["running"])
            self.assertFalse(status["ready"])
            self.assertFalse(brain.pid_path.exists())

    def test_status_tolerates_restricted_signal_probe(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Config(workspace=Path(temp))
            memory = MemoryStore(config.resolved_data_dir)
            memory.initialize()
            brain = BrainServer(config, memory)
            brain.pid_path.write_text("123", encoding="utf-8")
            with patch("human_ai.brain.os.kill", side_effect=PermissionError), patch.object(
                brain, "_pid_matches_brain", return_value=True
            ), patch("human_ai.brain.urllib.request.urlopen", side_effect=OSError):
                status = brain.status()
            self.assertTrue(status["running"])
            self.assertFalse(status["ready"])
            self.assertEqual(status["state"], "starting")

    def test_start_requires_existing_model(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Config(workspace=Path(temp))
            config.model.model_path = str(Path(temp) / "missing.gguf")
            memory = MemoryStore(config.resolved_data_dir)
            memory.initialize()

            with self.assertRaises(FileNotFoundError):
                BrainServer(config, memory).start()

    def test_start_requires_llama_server(self):
        with tempfile.TemporaryDirectory() as temp:
            model_path = Path(temp) / "model.gguf"
            model_path.write_text("fake", encoding="utf-8")
            model_path = model_path.resolve()
            config = Config(workspace=Path(temp))
            config.model.model_path = str(model_path)
            memory = MemoryStore(config.resolved_data_dir)
            memory.initialize()

            with patch("human_ai.brain.shutil.which", return_value=None), patch.object(
                Path, "exists", lambda path: path == model_path
            ):
                with self.assertRaisesRegex(RuntimeError, "llama-server"):
                    BrainServer(config, memory).start()


if __name__ == "__main__":
    unittest.main()
