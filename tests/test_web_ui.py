import hashlib
import http.client
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from human_ai.agent import Agent
from human_ai.brain import BrainServer
from human_ai.config import load_config
from human_ai.memory import Record
from human_ai.web_ui import INDEX_HTML, serve_in_thread


class WebUiTests(unittest.TestCase):
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
        self.config = load_config(str(self.config_path))
        self.agent = Agent(self.config)
        self.brain = BrainServer(self.config, self.agent.memory)

    def tearDown(self):
        self.temp.cleanup()

    def test_index_html_is_dark_chat_interface(self):
        self.assertIn("Chat With Gima", INDEX_HTML)
        self.assertIn("--bg: #050608", INDEX_HTML)
        self.assertIn("/api/chat", INDEX_HTML)
        self.assertIn("Memory Search", INDEX_HTML)
        self.assertIn("Attach Files", INDEX_HTML)
        self.assertIn("Generate Song Sketch", INDEX_HTML)
        self.assertIn("Generate Video From Audio", INDEX_HTML)
        self.assertIn("Freebeat-Style Director", INDEX_HTML)
        self.assertIn("Coding Split", INDEX_HTML)

    def test_web_api_status_chat_and_memory_search(self):
        self.agent.memory.add(
            Record(
                category="personal",
                title="Blue goal",
                content="Gima should have a black web interface.",
            )
        )
        with patch.object(BrainServer, "status", return_value={"running": False, "pid": None, "models": None}):
            web = serve_in_thread(self.config, self.agent, self.brain)
            try:
                host, port = web.server.server_address
                status = self._request(host, port, "GET", "/api/status")
                self.assertEqual(status["name"], "Gima")
                self.assertGreaterEqual(status["memory_rows"], 1)

                search = self._request(host, port, "GET", "/api/memory/search?q=black")
                self.assertEqual(search["results"][0]["title"], "Blue goal")

                chat = self._request(
                    host,
                    port,
                    "POST",
                    "/api/chat",
                    {"message": "what do you remember about black interface?"},
                )
                self.assertIn("reply", chat)
                self.assertIn("Blue goal", chat["reply"])
            finally:
                web.stop()

    def test_web_api_uploads_files_and_lists_them(self):
        with patch.object(BrainServer, "status", return_value={"running": False, "pid": None, "models": None}):
            web = serve_in_thread(self.config, self.agent, self.brain)
            try:
                host, port = web.server.server_address
                uploaded = self._multipart_upload(host, port, "note.txt", b"hello gima")
                self.assertEqual(uploaded["files"][0]["name"], "note.txt")
                self.assertTrue(Path(uploaded["files"][0]["path"]).exists())

                listed = self._request(host, port, "GET", "/api/files")
                self.assertEqual(listed["files"][0]["name"], "note.txt")
            finally:
                web.stop()

    def test_web_api_generates_local_song_sketch(self):
        with patch.object(BrainServer, "status", return_value={"running": False, "pid": None, "models": None}):
            web = serve_in_thread(self.config, self.agent, self.brain)
            try:
                host, port = web.server.server_address
                song = self._request(
                    host,
                    port,
                    "POST",
                    "/api/media/song-local",
                    {"prompt": "happy Gima intro", "duration_seconds": 4},
                )
                self.assertTrue(Path(song["output"]).exists())
                self.assertTrue(song["output"].endswith(".wav"))
                self.assertTrue(Path(song["manifest"]).exists())
            finally:
                web.stop()

    def test_web_api_video_and_code_tools(self):
        from human_ai.services import MusicVideoProject
        from human_ai.vibe_code import VibeCodeFile, VibeCodePlan
        from human_ai.self_update import SelfUpdateRequest

        with patch.object(BrainServer, "status", return_value={"running": False, "pid": None, "models": None}):
            web = serve_in_thread(self.config, self.agent, self.brain)
            try:
                host, port = web.server.server_address
                project_dir = Path(self.temp.name) / "project"
                project_dir.mkdir()
                output_path = project_dir / "video.mp4"
                output_path.write_bytes(b"mp4")
                manifest_path = project_dir / "manifest.json"
                manifest_path.write_text("{}", encoding="utf-8")
                prompt_path = project_dir / "prompt.txt"
                prompt_path.write_text("prompt", encoding="utf-8")
                with patch("human_ai.web_ui.LocalMusicVideoRenderer.render") as render:
                    render.return_value = MusicVideoProject(project_dir, output_path, manifest_path, prompt_path)
                    video = self._request(
                        host,
                        port,
                        "POST",
                        "/api/media/music-video-local",
                        {"audio_path": str(project_dir / "song.wav"), "prompt": "waveform", "style": "waveform", "consent": True},
                    )
                self.assertEqual(video["output"], str(output_path))

                director_manifest = project_dir / "director_manifest.json"
                director_storyboard = project_dir / "storyboard.md"
                director_manifest.write_text("{}", encoding="utf-8")
                director_storyboard.write_text("# storyboard", encoding="utf-8")
                with patch("human_ai.web_ui.LocalMusicVideoDirector.plan") as director:
                    director.return_value = type(
                        "DirectorProject",
                        (),
                        {
                            "manifest_path": director_manifest,
                            "storyboard_path": director_storyboard,
                        },
                    )()
                    director_response = self._request(
                        host,
                        port,
                        "POST",
                        "/api/media/music-video-director",
                        {
                            "audio_path": str(project_dir / "song.wav"),
                            "prompt": "freebeat style music video",
                            "mode": "story",
                            "style": "cinematic",
                            "aspect": "16:9",
                            "lyrics": "",
                        },
                    )
                self.assertEqual(director_response["storyboard"], str(director_storyboard))

                update = SelfUpdateRequest(
                    "update_test",
                    "add split coding",
                    project_dir,
                    project_dir / "copy",
                    project_dir / "backup.tar.gz",
                    project_dir / "plan.md",
                    project_dir / "manifest.json",
                    "prepared",
                )
                with patch("human_ai.web_ui.VibeCodingAgent.plan") as plan:
                    plan.return_value = VibeCodePlan(
                        update,
                        project_dir / "vibe.md",
                        project_dir / "patch.patch",
                        project_dir / "snapshot.json",
                        [VibeCodeFile("human_ai/web_ui.py", 9, "path matches web", 100)],
                        "kb_plan",
                    )
                    code = self._request(
                        host,
                        port,
                        "POST",
                        "/api/code/vibe-plan",
                        {"feature": "add split coding", "max_files": 8},
                    )
                self.assertEqual(code["update_id"], "update_test")
                self.assertEqual(code["candidate_files"][0]["path"], "human_ai/web_ui.py")
            finally:
                web.stop()

    def _request(self, host, port, method, path, body=None):
        connection = http.client.HTTPConnection(host, port, timeout=10)
        payload = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json"} if body is not None else {}
        connection.request(method, path, body=payload, headers=headers)
        response = connection.getresponse()
        data = json.loads(response.read().decode("utf-8"))
        connection.close()
        self.assertLess(response.status, 400, data)
        return data

    def _multipart_upload(self, host, port, filename, content):
        boundary = "----gima-test-boundary"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="files"; filename="{filename}"\r\n'
            "Content-Type: text/plain\r\n\r\n"
        ).encode("utf-8") + content + f"\r\n--{boundary}--\r\n".encode("utf-8")
        connection = http.client.HTTPConnection(host, port, timeout=10)
        connection.request(
            "POST",
            "/api/files/upload",
            body=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        response = connection.getresponse()
        data = json.loads(response.read().decode("utf-8"))
        connection.close()
        self.assertLess(response.status, 400, data)
        return data


if __name__ == "__main__":
    unittest.main()
