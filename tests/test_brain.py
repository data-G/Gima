import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from human_ai.brain import BrainServer
from human_ai.config import Config
from human_ai.memory import MemoryStore


class BrainServerTests(unittest.TestCase):
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
