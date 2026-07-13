import json
import tempfile
import unittest
from pathlib import Path

from human_ai.agent_registry import AgentRegistry
from human_ai.config import Config
from human_ai.memory import MemoryStore


class AgentRegistryTests(unittest.TestCase):
    def test_self_update_agent_creates_manifest_and_isolated_update(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            (workspace / "README.md").write_text("gima\n", encoding="utf-8")
            config = Config(workspace=workspace)
            memory = MemoryStore(config.resolved_data_dir)
            memory.initialize()

            created = AgentRegistry(config).create(
                name="Gima UI Updater",
                template="self_update",
                goal="Improve the route preview UI and run tests.",
                memory=memory,
            )

            manifest = json.loads(created.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(created.template, "self_update")
            self.assertEqual(created.status, "self_update_prepared")
            self.assertTrue(created.self_update_id.startswith("update_"))
            self.assertTrue(Path(created.working_copy).exists())
            self.assertTrue(Path(created.plan_path).exists())
            self.assertIn("edit live workspace directly", "\n".join(manifest["blocked_actions"]))
            self.assertTrue((config.resolved_data_dir / "agents" / "registry.json").exists())
            self.assertTrue(memory.search("Gima UI Updater", category="agent", limit=1))


if __name__ == "__main__":
    unittest.main()
