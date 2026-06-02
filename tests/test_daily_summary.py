import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

from human_ai.daily_summary import DailySummaryService
from human_ai.memory import MemoryStore


class DailySummaryTests(unittest.TestCase):
    def test_snapshot_contains_tracked_source_but_not_runtime_memory(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            subprocess.run(["git", "init", "-q"], cwd=workspace, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=workspace, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=workspace, check=True)
            (workspace / "app.py").write_text("print('hello')\n", encoding="utf-8")
            memory = MemoryStore(workspace / ".human-ai")
            memory.initialize()
            memory.append_conversation("session", "user", "private conversation")
            subprocess.run(["git", "add", "app.py"], cwd=workspace, check=True)
            subprocess.run(["git", "commit", "-qm", "Add app"], cwd=workspace, check=True)
            service = DailySummaryService(workspace, workspace / ".human-ai", memory)
            summary = service.generate()
            with zipfile.ZipFile(summary.attachment_path) as archive:
                names = archive.namelist()
                contents = "\n".join(
                    archive.read(name).decode("utf-8", errors="replace") for name in names
                )
        self.assertIn("app.py", names)
        self.assertFalse(any(".human-ai" in name for name in names))
        self.assertNotIn("private conversation", contents)


if __name__ == "__main__":
    unittest.main()
