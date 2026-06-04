import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from human_ai.agent import Agent
from human_ai.assistant_loop import LocalAssistant, clean_voice_transcript
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

    def test_voice_cleanup_corrects_common_transcript_errors(self):
        self.assertEqual(clean_voice_transcript("and game"), "end game")
        self.assertEqual(clean_voice_transcript("yeah"), "yes")
        self.assertEqual(clean_voice_transcript("Yes."), "yes")
        self.assertEqual(clean_voice_transcript("Yes. Yes."), "yes")
        self.assertEqual(clean_voice_transcript("[Music]"), "")
        self.assertEqual(clean_voice_transcript("[BLANK_AUDIO]"), "")
        self.assertEqual(clean_voice_transcript("[MUSIC PLAYING]"), "")
        self.assertEqual(clean_voice_transcript("thanks for watching"), "")

    def test_status_command_reports_tools(self):
        reply = self.make_assistant().run_text_command("status")
        self.assertTrue(
            "core" in reply.message.casefold()
            or "local tools are available" in reply.message.casefold()
        )

    def test_language_switch_requires_explicit_permission(self):
        assistant = self.make_assistant()
        reply = assistant.run_text_command("speak Japanese")
        self.assertEqual(reply.action, "language_lock")
        self.assertIn("stay in English", reply.message)
        self.assertEqual(assistant.response_language, "English")

    def test_language_switch_with_permission_changes_terminal_session(self):
        assistant = self.make_assistant()
        reply = assistant.run_text_command("I approve switching language to Japanese")
        self.assertEqual(reply.action, "language_switch")
        self.assertIn("Japanese", reply.message)
        self.assertEqual(assistant.response_language, "Japanese")

    def test_chat_fallback_uses_terminal_language_lock(self):
        assistant = self.make_assistant()
        with patch.object(assistant.agent, "chat", return_value="locked answer") as chat:
            reply = assistant.run_text_command("はい")
        self.assertEqual(reply.action, "chat")
        self.assertEqual(reply.message, "locked answer")
        sent = chat.call_args.args[0]
        self.assertIn("reply only in English", sent)
        self.assertIn("User message: はい", sent)

    def test_voice_self_update_request_asks_yes_no_then_marks_ready(self):
        assistant = self.make_assistant()
        reply = assistant.run_text_command("update Gima add a better memory feature")
        self.assertEqual(reply.action, "self_update_confirm")
        self.assertIn("Are you sure", reply.message)
        self.assertIsNotNone(assistant.pending_self_update)
        update_id = assistant.pending_self_update["id"]

        approved = assistant.run_text_command("yes")

        self.assertEqual(approved.action, "self_update_ready")
        self.assertIn(update_id, approved.message)
        self.assertIsNone(assistant.pending_self_update)
        manifest = (
            assistant.config.resolved_data_dir
            / "self_updates"
            / "requests"
            / update_id
            / "manifest.json"
        )
        self.assertIn("ready_for_parent_approval", manifest.read_text(encoding="utf-8"))

    def test_voice_self_update_accepts_noisy_yes_transcript(self):
        assistant = self.make_assistant()
        assistant.run_text_command("update Gima add a better memory feature")

        approved = assistant.run_text_command("Yes. Yes.")

        self.assertEqual(approved.action, "self_update_ready")

    def test_voice_self_update_understands_approval_intent_phrases(self):
        for phrase in ["I said yes", "approve it", "go ahead", "ok", "Есть."]:
            with self.subTest(phrase=phrase):
                assistant = self.make_assistant()
                assistant.run_text_command("update Gima add a better memory feature")

                approved = assistant.run_text_command(phrase)

                self.assertEqual(approved.action, "self_update_ready")

    def test_voice_self_update_understands_cancel_intent_phrases(self):
        for phrase in ["no thanks", "cancel it", "do not approve", "reject"]:
            with self.subTest(phrase=phrase):
                assistant = self.make_assistant()
                assistant.run_text_command("update Gima add a better memory feature")

                cancelled = assistant.run_text_command(phrase)

                self.assertEqual(cancelled.action, "self_update_cancel")

    def test_pending_self_update_empty_audio_asks_for_yes_or_no(self):
        assistant = self.make_assistant()
        assistant.run_text_command("update Gima add a better memory feature")

        reply = assistant.run_text_command("[BLANK_AUDIO]")

        self.assertEqual(reply.action, "self_update_confirm")
        self.assertIn("did not catch yes or no", reply.message)

    def test_voice_self_update_request_can_be_cancelled_with_no(self):
        assistant = self.make_assistant()
        reply = assistant.run_text_command("self update add a better voice feature")
        self.assertEqual(reply.action, "self_update_confirm")
        self.assertIsNotNone(assistant.pending_self_update)

        cancelled = assistant.run_text_command("no")

        self.assertEqual(cancelled.action, "self_update_cancel")
        self.assertIsNone(assistant.pending_self_update)

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

    def test_direct_conversation_retries_empty_or_filler_transcripts(self):
        assistant = self.make_assistant()
        assistant.config.permissions.require_scoped_grants = False
        with patch.object(
            assistant,
            "listen_once",
            side_effect=["[Music]", "End Game"],
        ), patch.object(assistant.voice, "speak") as speak:
            self.assertEqual(
                assistant.run_conversation(Path("/tmp/whisper.bin"), conversation_turns=3),
                0,
            )
        spoken = [call.args[0] for call in speak.call_args_list]
        self.assertIn("I did not catch that. Please say it again.", spoken)

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

    def test_voice_can_learn_ai_human_research(self):
        assistant = self.make_assistant()
        assistant.config.permissions.require_scoped_grants = False
        with patch.object(
            assistant.agent,
            "learn_research_profile",
            return_value=Path("/tmp/ai-human-systems.md"),
        ):
            reply = assistant.run_text_command("learn AI-human systems papers to improve Gima")
        self.assertEqual(reply.action, "research_learn")
        self.assertIn("AI-human systems", reply.message)
        self.assertIn("ai-human-systems.md", reply.message)

    def test_voice_can_learn_video_generation_research(self):
        assistant = self.make_assistant()
        assistant.config.permissions.require_scoped_grants = False
        with patch.object(
            assistant.agent,
            "learn_research_profile",
            return_value=Path("/tmp/video-generation.md"),
        ) as learn_research:
            reply = assistant.run_text_command("learn video generation")
        self.assertEqual(reply.action, "research_learn")
        self.assertIn("video generation", reply.message)
        self.assertIn("video-generation.md", reply.message)
        learn_research.assert_called_once_with("video-generation")

    def test_voice_can_learn_frontier_ai_systems_research(self):
        assistant = self.make_assistant()
        assistant.config.permissions.require_scoped_grants = False
        with patch.object(
            assistant.agent,
            "learn_research_profile",
            return_value=Path("/tmp/frontier-ai-systems.md"),
        ) as learn_research:
            reply = assistant.run_text_command("learn from other AI systems like ChatGPT and Gemini")
        self.assertEqual(reply.action, "research_learn")
        self.assertIn("frontier AI systems", reply.message)
        self.assertIn("frontier-ai-systems.md", reply.message)
        learn_research.assert_called_once_with("frontier-ai-systems")

    def test_voice_can_ask_chatgpt_teacher(self):
        assistant = self.make_assistant()
        assistant.config.permissions.require_scoped_grants = False
        with patch.object(assistant.agent, "ask_teacher", return_value="teacher answer") as ask:
            reply = assistant.run_text_command("ask ChatGPT how to improve Gima")
        self.assertEqual(reply.action, "teacher")
        self.assertIn("teacher answer", reply.message)
        ask.assert_called_once_with("chatgpt", "how to improve")

    def test_voice_can_ask_gemini_teacher(self):
        assistant = self.make_assistant()
        assistant.config.permissions.require_scoped_grants = False
        with patch.object(assistant.agent, "ask_teacher", return_value="gemini answer") as ask:
            reply = assistant.run_text_command("ask Gemini explain camera interaction")
        self.assertEqual(reply.action, "teacher")
        self.assertIn("gemini answer", reply.message)
        ask.assert_called_once_with("gemini", "explain camera interaction")


if __name__ == "__main__":
    unittest.main()
