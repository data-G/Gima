import tempfile
import unittest
from pathlib import Path

from human_ai.config import Config
from human_ai.memory import MemoryStore
from human_ai.services import SafeToolRunner, WebImporter


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


if __name__ == "__main__":
    unittest.main()
