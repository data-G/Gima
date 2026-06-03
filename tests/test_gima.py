import io
import hashlib
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from human_ai import gima


class GimaControlCenterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp.name) / "config.json"
        self.config_path.write_text(
            json.dumps(
                {
                    "workspace": self.temp.name,
                    "data_dir": ".human-ai",
                    "model": {"enabled": False},
                    "permissions": {"require_scoped_grants": False},
                    "parent_approval": {
                        "reviewer_name": "Gima parent",
                        "password_sha256": hashlib.sha256("parent-pass".encode("utf-8")).hexdigest(),
                    },
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp.cleanup()

    def run_gima(self, *args):
        output = io.StringIO()
        with redirect_stdout(output):
            code = gima.main(["--config", str(self.config_path), *args])
        self.assertEqual(code, 0)
        return output.getvalue()

    def test_remember_and_search(self):
        remember = self.run_gima("remember", "Goal", "Build", "the", "best", "Gima")
        self.assertIn("Remembered as", remember)
        search = self.run_gima("search", "best Gima")
        self.assertIn("Goal", search)

    def test_status_prints_control_center_summary(self):
        with patch("human_ai.gima.BrainServer.status") as status:
            status.return_value = {"running": False, "pid": None, "models": None}
            output = self.run_gima("status")
        self.assertIn("Gima config:", output)
        self.assertIn("Brain: stopped", output)

    def test_learn_web_imports_search_results(self):
        with patch("human_ai.agent.Agent.learn_web") as learn_web:
            learn_web.return_value = [("https://example.com/source", "kb_web")]
            output = self.run_gima("learn-web", "local LLM memory")
        self.assertIn("Imported https://example.com/source as kb_web", output)
        learn_web.assert_called_once_with("local LLM memory", "research", 3)

    def test_learn_language_saves_knowledge_file(self):
        with patch("human_ai.agent.Agent.learn_language") as learn_language:
            learn_language.return_value = Path(self.temp.name) / ".human-ai" / "brain" / "sinhala.md"
            output = self.run_gima("learn-language", "sinhala")
        self.assertIn("sinhala.md", output)
        learn_language.assert_called_once_with("sinhala")

    def test_learn_research_saves_brain_file(self):
        with patch("human_ai.agent.Agent.learn_research_profile") as learn_research:
            learn_research.return_value = (
                Path(self.temp.name) / ".human-ai" / "brain" / "ai-human-systems.md"
            )
            output = self.run_gima("learn-research", "ai-human-systems")
        self.assertIn("ai-human-systems.md", output)
        learn_research.assert_called_once_with("ai-human-systems")

    def test_reviews_and_parent_approval(self):
        from human_ai.agent import Agent
        from human_ai.config import load_config
        from human_ai.memory import Record

        agent = Agent(load_config(str(self.config_path)))
        record = Record(category="research", title="Source", content="claim", status="review")
        record_id = agent.memory.add(record)
        review_id = agent.memory.add_source_review(
            record_id,
            "Source",
            "https://example.com",
            "research",
            "web",
            "claim",
        )
        output = self.run_gima("reviews")
        self.assertIn(review_id, output)
        with patch("getpass.getpass", return_value="parent-pass"):
            approved = self.run_gima("approve", review_id, "--notes", "checked")
        self.assertIn("Approved", approved)
        self.assertIn("Source", self.run_gima("search", "claim", "--category", "research"))


if __name__ == "__main__":
    unittest.main()
