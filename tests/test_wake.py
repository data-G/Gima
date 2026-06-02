import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from human_ai.config import Config
from human_ai.memory import MemoryStore
from human_ai.wake import WakeAssistant, contains_wake_word, normalize_speech


class WakeWordTests(unittest.TestCase):
    def test_normalize_speech_preserves_unicode_words(self):
        self.assertEqual(normalize_speech("こんにちは、GIMA!"), "こんにちは gima")

    def test_detects_case_insensitive_word_in_mixed_language_transcript(self):
        self.assertTrue(contains_wake_word("こんにちは GIMA 元気ですか"))

    def test_does_not_match_word_fragment(self):
        self.assertFalse(contains_wake_word("imaginary"))

    @patch("human_ai.wake.Voice.speak")
    def test_wake_uses_local_profile_without_camera_by_default(self, speak):
        with tempfile.TemporaryDirectory() as temp:
            config = Config(data_dir=Path(temp))
            config.wake.profile_about = "Your enrolled profile is available locally."
            memory = MemoryStore(config.resolved_data_dir)
            result = WakeAssistant(config, memory).respond("Gima")
        self.assertTrue(result.activated)
        self.assertIsNone(result.photo_path)
        self.assertIn("Hi Gima.", result.message)
        self.assertIn("enrolled profile", result.message)
        speak.assert_called_once_with(result.message)

    def test_non_match_does_not_activate(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Config(data_dir=Path(temp))
            memory = MemoryStore(config.resolved_data_dir)
            result = WakeAssistant(config, memory).respond("hello")
        self.assertFalse(result.activated)


if __name__ == "__main__":
    unittest.main()
