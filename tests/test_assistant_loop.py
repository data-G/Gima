import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from human_ai.agent import Agent
from human_ai.assistant_loop import LocalAssistant
from human_ai.config import Config
from human_ai.memory import Record


class LocalAssistantTests(unittest.TestCase):
    def make_assistant(self):
        temp = tempfile.TemporaryDirectory()
        config = Config(data_dir=Path(temp.name))
        agent = Agent(config)
        self.addCleanup(temp.cleanup)
        return LocalAssistant(agent)

    def test_time_command_answers_from_pc(self):
        reply = self.make_assistant().run_text_command("what time is it")
        self.assertIn("It is", reply.message)

    def test_sleep_command_stops(self):
        reply = self.make_assistant().run_text_command("sleep")
        self.assertEqual(reply.action, "stop")

    def test_end_game_command_stops(self):
        reply = self.make_assistant().run_text_command("End Game")
        self.assertEqual(reply.action, "stop")
        self.assertIn("sleep", reply.message)

    def test_end_game_alias_command_stops(self):
        reply = self.make_assistant().run_text_command("endgame")
        self.assertEqual(reply.action, "stop")

    def test_status_command_reports_tools(self):
        reply = self.make_assistant().run_text_command("status")
        self.assertTrue(
            "core" in reply.message.casefold()
            or "local tools are available" in reply.message.casefold()
        )

    def test_memory_search_reads_local_memory(self):
        assistant = self.make_assistant()
        assistant.agent.memory.add(
            Record(category="files", title="Blue umbrella", content="The umbrella is near the door.")
        )
        reply = assistant.run_text_command("search memory umbrella")
        self.assertIn("Blue umbrella", reply.message)

    def test_direct_conversation_stops_on_end_game(self):
        assistant = self.make_assistant()
        assistant.config.permissions.require_scoped_grants = False
        with patch.object(assistant, "listen_once", return_value="End Game"), patch.object(
            assistant.voice, "speak"
        ) as speak:
            self.assertEqual(
                assistant.run_conversation(Path("/tmp/whisper.bin"), conversation_turns=3),
                0,
            )
        self.assertGreaterEqual(speak.call_count, 2)

    def test_voice_can_learn_from_internet_topic(self):
        assistant = self.make_assistant()
        assistant.config.permissions.require_scoped_grants = False
        with patch.object(
            assistant.agent,
            "learn_web",
            return_value=[("https://example.com/gima", "kb_123")],
        ):
            reply = assistant.run_text_command("Can't you learn from internet about local LLM memory?")
        self.assertEqual(reply.action, "web_learn")
        self.assertIn("internet pages", reply.message)

    def test_voice_can_import_internet_url(self):
        assistant = self.make_assistant()
        assistant.config.permissions.require_scoped_grants = False
        with patch.object(assistant.agent, "import_web", return_value="kb_456"):
            reply = assistant.run_text_command("learn from internet https://example.com/page")
        self.assertEqual(reply.action, "web_learn")
        self.assertIn("kb_456", reply.message)

    def test_voice_can_learn_sinhala(self):
        assistant = self.make_assistant()
        assistant.config.permissions.require_scoped_grants = False
        with patch.object(
            assistant.agent,
            "learn_language",
            return_value=Path("/tmp/sinhala.md"),
        ):
            reply = assistant.run_text_command("learn Sinhala")
        self.assertEqual(reply.action, "language_learn")
        self.assertIn("Sinhala", reply.message)
        self.assertIn("sinhala.md", reply.message)


if __name__ == "__main__":
    unittest.main()
