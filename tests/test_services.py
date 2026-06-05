import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from human_ai.config import Config
from human_ai.memory import MemoryStore
from human_ai.services import (
    LipSyncPlanner,
    LocalMusicVideoRenderer,
    SafeToolRunner,
    TeacherModelClient,
    WebImporter,
)


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

    def test_lip_sync_planner_requires_consent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            audio = root / "song.mp3"
            face = root / "face.jpg"
            audio.write_bytes(b"fake mp3")
            face.write_bytes(b"fake jpg")
            with self.assertRaises(PermissionError):
                LipSyncPlanner(root / "out").create_project(audio, face, "sing", consent=False)

    def test_lip_sync_planner_creates_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            audio = root / "song.mp3"
            face = root / "face.jpg"
            audio.write_bytes(b"fake mp3")
            face.write_bytes(b"fake jpg")
            project = LipSyncPlanner(root / "out").create_project(
                audio,
                face,
                "make a respectful lip sync performance",
                consent=True,
            )
            self.assertTrue(project.manifest_path.exists())
            text = project.manifest_path.read_text(encoding="utf-8")
            self.assertIn("make a respectful lip sync performance", text)
            self.assertIn(str(audio.resolve()), text)
            self.assertIn(str(face.resolve()), text)

    def test_local_music_video_renderer_requires_consent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            audio = root / "song.mp3"
            audio.write_bytes(b"fake mp3")
            with self.assertRaises(PermissionError):
                LocalMusicVideoRenderer(root / "out").render(audio, "make video", consent=False)

    def test_local_music_video_renderer_creates_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            audio = root / "song.mp3"
            audio.write_bytes(b"fake mp3")

            def fake_run(command, **kwargs):
                output = Path(command[-1])
                output.write_bytes(b"fake mp4")
                return None

            with patch("human_ai.services.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
                "human_ai.services.subprocess.run", side_effect=fake_run
            ):
                project = LocalMusicVideoRenderer(root / "out").render(
                    audio,
                    "make a waveform music video",
                    style="waveform",
                    consent=True,
                )

            self.assertTrue(project.output_path.exists())
            text = project.manifest_path.read_text(encoding="utf-8")
            self.assertIn("local_music_video", text)
            self.assertIn("make a waveform music video", text)
            self.assertIn(str(audio.resolve()), text)


if __name__ == "__main__":
    unittest.main()
