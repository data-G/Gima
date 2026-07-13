import hashlib
import re
import http.client
import json
import shutil
import subprocess
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
        self.assertIn("--bg: #090a0c", INDEX_HTML)
        self.assertIn("soft gray local AI workspace", INDEX_HTML)
        self.assertIn("--glow:", INDEX_HTML)
        self.assertIn("/api/chat", INDEX_HTML)
        self.assertIn("manifest.webmanifest", INDEX_HTML)
        self.assertIn("Install Gima App", INDEX_HTML)
        self.assertIn("split(/[\\n,]+/)", INDEX_HTML)
        self.assertNotIn("split(/[\n,]+/)", INDEX_HTML)
        self.assertIn("API Bindings", INDEX_HTML)
        self.assertIn("Free quota mode", INDEX_HTML)
        self.assertIn("Ask All Linked Minds", INDEX_HTML)
        self.assertIn("Use Brain", INDEX_HTML)
        self.assertIn("Browse Web", INDEX_HTML)
        self.assertIn("browse the web for latest AI news and give sources", INDEX_HTML)
        self.assertIn("Human Folder Map", INDEX_HTML)
        self.assertIn("Apps & Automation", INDEX_HTML)
        self.assertIn("response time:", INDEX_HTML)
        self.assertIn("Copy code", INDEX_HTML)
        self.assertIn("attach-inline", INDEX_HTML)
        self.assertIn("Hello there", INDEX_HTML)
        self.assertIn("Type a message or upload files to get started", INDEX_HTML)
        self.assertIn("drawer-backdrop", INDEX_HTML)
        self.assertIn("action-tray", INDEX_HTML)
        self.assertIn("modelChip", INDEX_HTML)
        self.assertIn("routePreviewChip", INDEX_HTML)
        self.assertIn("/api/ai-router/plan", INDEX_HTML)
        self.assertIn("scheduleRoutePreview", INDEX_HTML)
        self.assertIn("privacy local", INDEX_HTML)
        self.assertIn("localModelSelect", INDEX_HTML)
        self.assertIn("/api/model-level/use", INDEX_HTML)
        self.assertIn("data-open-panel", INDEX_HTML)
        self.assertIn("nav-rail", INDEX_HTML)
        self.assertIn("standard-shell", INDEX_HTML)
        self.assertIn("Add to chat", INDEX_HTML)
        self.assertIn("addSheet", INDEX_HTML)
        self.assertIn("data-file-category", INDEX_HTML)
        self.assertIn("MCP Servers / AI APIs", INDEX_HTML)
        self.assertIn("System Message", INDEX_HTML)
        self.assertIn("Send message on Enter", INDEX_HTML)
        self.assertIn("/api/brain/search", Path("human_ai/web_ui.py").read_text(encoding="utf-8"))
        self.assertIn("Attach to chat", INDEX_HTML)
        self.assertIn("Memory Search", INDEX_HTML)
        self.assertIn("Attach Files", INDEX_HTML)
        self.assertIn("Generate Song Sketch", INDEX_HTML)
        self.assertIn("Generate Video From Audio", INDEX_HTML)
        self.assertIn("Images + MP3 Video", INDEX_HTML)
        self.assertIn("Hugging Face Video", INDEX_HTML)
        self.assertIn("/api/media/huggingface-video-generate", INDEX_HTML)
        self.assertIn("hfVideoBtn", INDEX_HTML)
        self.assertIn("Hugging Face Image", INDEX_HTML)
        self.assertIn("/api/media/huggingface-image-generate", INDEX_HTML)
        self.assertIn("hfImageBtn", INDEX_HTML)
        self.assertIn("Hugging Face Feature Extraction", INDEX_HTML)
        self.assertIn("/api/ai/huggingface-feature-extract", INDEX_HTML)
        self.assertIn("hfFeatureBtn", INDEX_HTML)
        self.assertIn("Local Transformers Chat", INDEX_HTML)
        self.assertIn("/api/local/transformers-generate", INDEX_HTML)
        self.assertIn("transformersBtn", INDEX_HTML)
        self.assertIn("WhatsApp Messenger", INDEX_HTML)
        self.assertIn("/api/whatsapp/draft", INDEX_HTML)
        self.assertIn("/api/whatsapp/send", INDEX_HTML)
        self.assertIn("/api/whatsapp/messages", INDEX_HTML)
        self.assertIn("whatsappDraftBtn", INDEX_HTML)
        self.assertIn("whatsappSendBtn", INDEX_HTML)
        self.assertIn("whatsappSearchBtn", INDEX_HTML)
        self.assertIn("Neural Lip-Sync", INDEX_HTML)
        self.assertIn("My Voice Profile", INDEX_HTML)
        self.assertIn("/api/voice-profile/save", INDEX_HTML)
        self.assertIn("Advanced Local Video Draft", INDEX_HTML)
        self.assertIn("Render Local Movie Draft", INDEX_HTML)
        self.assertIn("Render Neural Lip-Sync", INDEX_HTML)
        self.assertIn("Freebeat-Style Director", INDEX_HTML)
        self.assertIn("Coding Split", INDEX_HTML)
        self.assertIn("What Gima Can Do", INDEX_HTML)
        self.assertIn("Codex Mode", INDEX_HTML)
        self.assertIn("AI Task Map A-Z", INDEX_HTML)
        self.assertIn("Deployments", INDEX_HTML)
        self.assertIn("Agents & Vibe Code", INDEX_HTML)
        self.assertIn("Create Task Agent", INDEX_HTML)
        self.assertIn("agentTemplate", INDEX_HTML)
        self.assertIn("/api/agents/create", INDEX_HTML)
        self.assertIn("Safe Self-Update Agent", INDEX_HTML)
        self.assertIn("Outputs", INDEX_HTML)
        self.assertIn("renderMarkdownLite", INDEX_HTML)
        self.assertIn("file-card-list", INDEX_HTML)
        self.assertIn("download-button", INDEX_HTML)
        self.assertIn("Open Location", INDEX_HTML)
        self.assertIn("/api/reveal", INDEX_HTML)
        self.assertIn("resultFileEntries", INDEX_HTML)
        self.assertIn("--font-md: 14px", INDEX_HTML)
        self.assertIn("font-size: 15px", INDEX_HTML)
        self.assertIn("Copy full answer", INDEX_HTML)
        self.assertIn("Copy answer + files", INDEX_HTML)
        self.assertIn("copyText", INDEX_HTML)
        self.assertIn("renderCodeExecutionResult", INDEX_HTML)
        self.assertIn("Codex output", INDEX_HTML)
        self.assertIn("Unified diff", INDEX_HTML)
        self.assertIn("Code + Output", INDEX_HTML)
        self.assertIn("renderCodeRunResult", INDEX_HTML)
        self.assertIn("screenRecordBtn", INDEX_HTML)
        self.assertIn("getDisplayMedia", INDEX_HTML)
        self.assertIn("MediaRecorder", INDEX_HTML)
        self.assertIn("Screen Rec", INDEX_HTML)

    def test_index_javascript_parses_as_served(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not installed")
        match = re.search(r"<script>(.*?)</script>", INDEX_HTML, re.S)
        self.assertIsNotNone(match)
        script_path = Path(self.temp.name) / "gima_index.js"
        script_path.write_text(match.group(1), encoding="utf-8")
        result = subprocess.run([node, "--check", str(script_path)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_all_static_buttons_have_handlers_or_declarative_actions(self):
        buttons = re.findall(r"<button\b([^>]*)>(.*?)</button>", INDEX_HTML, re.S)
        ids = set(re.findall(r'id="([^"]+)"', INDEX_HTML))
        handled_ids = set(re.findall(r"getElementById\('([^']+)'\)\.addEventListener\('click'", INDEX_HTML))
        variable_ids = dict(
            re.findall(r"const\s+([A-Za-z_$][\w$]*)\s*=\s*document\.getElementById\('([^']+)'\)", INDEX_HTML)
        )
        for variable, element_id in variable_ids.items():
            if re.search(rf"\b{re.escape(variable)}\.addEventListener\('click'", INDEX_HTML):
                handled_ids.add(element_id)
        dead_buttons = []
        for attrs, body in buttons:
            attr_map = dict(re.findall(r'([A-Za-z0-9_-]+)="([^"]*)"', attrs))
            focus = attr_map.get("data-focus")
            if focus:
                self.assertIn(focus, ids)
            if (
                attr_map.get("id") in handled_ids
                or attr_map.get("type") == "submit"
                or "onclick=" in attrs
                or any(
                    key in attr_map
                    for key in [
                        "data-prompt",
                        "data-open-panel",
                        "data-action",
                        "data-file-category",
                        "data-copy-kind",
                        "data-code-copy",
                        "data-result-copy",
                    ]
                )
            ):
                continue
            label = re.sub(r"<.*?>", "", body).strip()
            dead_buttons.append({"label": label, "attrs": attrs})
        self.assertEqual(dead_buttons, [])

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
                self.assertEqual(status["downloads"], str(self.config.resolved_downloads_dir))
                self.assertEqual(status["hands"], str(self.config.resolved_hands_dir))
                self.assertEqual(status["hands_in"], str(self.config.resolved_hands_in_dir))
                self.assertEqual(status["hands_out"], str(self.config.resolved_hands_out_dir))
                self.assertEqual(status["brain_csv"], str(self.config.resolved_brain_csv_path))
                self.assertEqual(status["stomach"], str(self.config.resolved_stomach_dir))
                self.assertEqual(status["continuous"], str(self.config.resolved_continuous_dir))
                self.assertGreaterEqual(status["memory_rows"], 1)
                self.assertGreaterEqual(status["brain_csv_rows"], 1)

                search = self._request(host, port, "GET", "/api/memory/search?q=black")
                self.assertEqual(search["results"][0]["title"], "Blue goal")

                brain_search = self._request(host, port, "GET", "/api/brain/search?q=black")
                self.assertEqual(brain_search["results"][0]["title"], "Blue goal")
                self.assertEqual(brain_search["path"], str(self.config.resolved_brain_csv_path))

                chat = self._request(
                    host,
                    port,
                    "POST",
                    "/api/chat",
                    {"message": "what do you remember about black interface?"},
                )
                self.assertIn("reply", chat)
                self.assertIn("Blue goal", chat["reply"])
                continuous_csv = self.config.resolved_continuous_dir / "work_steps.csv"
                self.assertTrue(continuous_csv.exists())
                self.assertIn("what do you remember about black interface?", continuous_csv.read_text(encoding="utf-8"))

                manifest = self._request(host, port, "GET", "/manifest.webmanifest")
                self.assertEqual(manifest["short_name"], "Gima")
                service_worker = self._raw_request(host, port, "GET", "/service-worker.js")
                self.assertIn(b"gima-local-app", service_worker)
                icon = self._raw_request(host, port, "GET", "/api/app-icon.svg")
                self.assertIn(b"<svg", icon)
            finally:
                web.stop()

    def test_web_api_status_lists_model_levels_and_switches_active_level(self):
        tiny_model = Path(self.temp.name) / "tiny.gguf"
        gemma_model = Path(self.temp.name) / "gemma.gguf"
        tiny_model.write_text("tiny", encoding="utf-8")
        gemma_model.write_text("gemma", encoding="utf-8")
        self.config.model.active_level = "tiny"
        self.config.model.model = "tiny-model"
        self.config.model.model_path = str(tiny_model)
        self.config.model.profiles = {
            "tiny": {
                "name": "Tiny Test",
                "model": "tiny-model",
                "model_path": str(tiny_model),
                "context_size": 1024,
                "max_tokens": 64,
                "description": "fast tiny test model",
            },
            "gemma4_12b": {
                "name": "Gemma 4 12B QAT Q4",
                "model": "gemma4-test",
                "model_path": str(gemma_model),
                "context_size": 8192,
                "max_tokens": 384,
                "description": "gemma test model",
                "files": [],
            },
        }
        setattr(self.config, "_config_path", str(self.config_path))

        with patch.object(BrainServer, "status", return_value={"running": False, "pid": None, "models": None}):
            web = serve_in_thread(self.config, self.agent, self.brain)
            try:
                host, port = web.server.server_address
                status = self._request(host, port, "GET", "/api/status")
                levels = {row["level"]: row for row in status["model_levels"]}
                self.assertEqual(status["active_model_level"], "tiny")
                self.assertTrue(levels["gemma4_12b"]["available"])
                self.assertEqual(levels["gemma4_12b"]["status"], "ready")

                switched = self._request(
                    host,
                    port,
                    "POST",
                    "/api/model-level/use",
                    {"level": "gemma4_12b", "restart": False},
                )
            finally:
                web.stop()

        self.assertTrue(switched["ok"])
        self.assertEqual(switched["active_level"], "gemma4_12b")
        self.assertEqual(self.config.model.active_level, "gemma4_12b")
        self.assertEqual(self.config.model.model, "gemma4-test")

    def test_web_chat_falls_back_when_local_model_is_slow(self):
        self.config.model.enabled = True
        self.agent.memory.add(
            Record(
                category="technical",
                title="Web reply bug",
                content="If the local model is slow, web chat should return a memory fallback.",
            )
        )
        with patch.object(BrainServer, "status", return_value={"running": True, "pid": 123, "models": None}):
            with patch.object(self.agent.model, "complete", side_effect=TimeoutError("slow model")) as complete:
                web = serve_in_thread(self.config, self.agent, self.brain)
                try:
                    host, port = web.server.server_address
                    chat = self._request(
                        host,
                        port,
                        "POST",
                        "/api/chat",
                        {"message": "web reply bug"},
                    )
                finally:
                    web.stop()
        self.assertIn("reply", chat)
        self.assertIn("local brain did not reply within the response limit", chat["reply"])
        self.assertIn("Web reply bug", chat["reply"])
        complete.assert_called_once()
        self.assertEqual(complete.call_args.kwargs["timeout_seconds"], 75)

    def test_web_chat_uses_longer_timeout_for_gemma_12b(self):
        self.config.model.enabled = True
        self.config.model.active_level = "gemma4_12b"
        self.config.model.model = "google-gemma-4-12b-it-qat-q4_0"
        self.config.model.timeout_seconds = 75
        self.config.model.max_tokens = 32
        with patch.object(BrainServer, "status", return_value={"running": True, "ready": True, "pid": 123, "models": None}):
            with patch.object(self.agent.model, "complete", return_value="Gemma answer") as complete:
                web = serve_in_thread(self.config, self.agent, self.brain)
                try:
                    host, port = web.server.server_address
                    chat = self._request(host, port, "POST", "/api/chat", {"message": "gemma check"})
                finally:
                    web.stop()
        self.assertEqual(chat["reply"], "Gemma answer")
        self.assertEqual(chat["model_level_used"], "gemma4_12b")
        complete.assert_called_once()
        self.assertEqual(complete.call_args.kwargs["timeout_seconds"], 75)

    def test_web_chat_health_question_answers_directly(self):
        self.config.model.enabled = True
        with patch.object(BrainServer, "status", return_value={"running": True, "ready": True, "pid": 123, "models": None}):
            with patch.object(self.agent.model, "complete") as complete:
                web = serve_in_thread(self.config, self.agent, self.brain)
                try:
                    host, port = web.server.server_address
                    chat = self._request(host, port, "POST", "/api/chat", {"message": "is it working now"})
                finally:
                    web.stop()
        self.assertIn("Gima is running and replying", chat["reply"])
        self.assertIn("linked Chat mode", chat["reply"])
        complete.assert_not_called()

    def test_web_chat_self_code_request_answers_with_safe_coding_path(self):
        self.config.model.enabled = True
        with patch.object(BrainServer, "status", return_value={"running": True, "ready": True, "pid": 123, "models": None}):
            with patch.object(self.agent.model, "complete") as complete:
                web = serve_in_thread(self.config, self.agent, self.brain)
                try:
                    host, port = web.server.server_address
                    chat = self._request(host, port, "POST", "/api/chat", {"message": "self code and update itself required"})
                finally:
                    web.stop()
        self.assertIn("Gima can self-code safely", chat["reply"])
        self.assertIn("Implement in Isolated Copy", chat["reply"])
        self.assertIn("Screen Rec button", chat["reply"])
        complete.assert_not_called()

    def test_web_chat_screen_record_request_answers_with_real_button(self):
        self.config.model.enabled = True
        with patch.object(BrainServer, "status", return_value={"running": True, "ready": True, "pid": 123, "models": None}):
            with patch.object(self.agent.model, "complete") as complete:
                web = serve_in_thread(self.config, self.agent, self.brain)
                try:
                    host, port = web.server.server_address
                    chat = self._request(host, port, "POST", "/api/chat", {"message": "video record of what i do"})
                finally:
                    web.stop()
        self.assertIn("Screen Rec button", chat["reply"])
        self.assertIn("browser permission", chat["reply"])
        complete.assert_not_called()

    def test_web_chat_connect_codex_answers_with_coding_workflow(self):
        self.config.model.enabled = True
        with patch.object(BrainServer, "status", return_value={"running": True, "ready": True, "pid": 123, "models": None}):
            with patch.object(self.agent.model, "complete") as complete:
                web = serve_in_thread(self.config, self.agent, self.brain)
                try:
                    host, port = web.server.server_address
                    chat = self._request(host, port, "POST", "/api/chat", {"message": "connect codex"})
                finally:
                    web.stop()
        self.assertIn("Codex is connected", chat["reply"])
        self.assertIn("Implement in Isolated Copy", chat["reply"])
        complete.assert_not_called()

    def test_web_chat_connection_error_does_not_claim_brain_starting_when_status_ready(self):
        self.config.model.enabled = True
        self.agent.memory.add(
            Record(
                category="technical",
                title="Connection fallback",
                content="When generation fails but status is ready, Gima should say the local model could not complete.",
            )
        )
        with patch.object(BrainServer, "status", return_value={"running": True, "ready": True, "pid": 123, "models": None}):
            with patch.object(self.agent.model, "complete", side_effect=ConnectionError("connection refused")):
                web = serve_in_thread(self.config, self.agent, self.brain)
                try:
                    host, port = web.server.server_address
                    chat = self._request(host, port, "POST", "/api/chat", {"message": "connection fallback"})
                finally:
                    web.stop()
        self.assertIn("local model could not complete this response", chat["reply"])
        self.assertNotIn("local brain is starting", chat["reply"])

    def test_web_chat_can_retry_with_small_model_for_one_request(self):
        fast_model = Path(self.temp.name) / "fast.gguf"
        fast_model.write_text("model", encoding="utf-8")
        self.config.model.enabled = True
        self.config.model.active_level = "strong"
        self.config.model.model = "gima-local-qwen2.5-7b"
        self.config.model.profiles = {
            "fast": {
                "model": "gima-local-qwen2.5-1.5b",
                "model_path": str(fast_model),
                "context_size": 4096,
                "max_tokens": 384,
            }
        }
        seen: dict[str, str] = {}

        def fake_chat(*args, **kwargs):
            seen["active_level"] = self.config.model.active_level
            seen["model"] = self.config.model.model
            return "small model reply"

        with patch.object(BrainServer, "status", return_value={"running": True, "pid": 123, "models": None}):
            with patch.object(self.agent, "chat", side_effect=fake_chat) as chat_call:
                web = serve_in_thread(self.config, self.agent, self.brain)
                try:
                    host, port = web.server.server_address
                    chat = self._request(
                        host,
                        port,
                        "POST",
                        "/api/chat",
                        {"message": "retry with small ai", "prefer_small_model": True},
                    )
                finally:
                    web.stop()
        self.assertEqual(chat["reply"], "small model reply")
        self.assertEqual(chat["model_level_used"], "fast")
        self.assertTrue(chat["small_model_retry"])
        self.assertEqual(seen["active_level"], "fast")
        self.assertEqual(seen["model"], "gima-local-qwen2.5-1.5b")
        self.assertEqual(self.config.model.active_level, "strong")
        self.assertEqual(self.config.model.model, "gima-local-qwen2.5-7b")
        chat_call.assert_called_once()

    def test_web_chat_answers_simple_greeting_without_model(self):
        self.config.model.enabled = True
        with patch.object(BrainServer, "status", return_value={"running": True, "pid": 123, "models": None}):
            with patch.object(self.agent.model, "complete") as complete:
                web = serve_in_thread(self.config, self.agent, self.brain)
                try:
                    host, port = web.server.server_address
                    chat = self._request(host, port, "POST", "/api/chat", {"message": "hi"})
                finally:
                    web.stop()
        self.assertEqual(chat["reply"], "Hi. I am here and ready.")
        complete.assert_not_called()

    def test_web_chat_reports_github_cli_authentication_required_without_model(self):
        self.config.model.enabled = True
        auth_result = subprocess.CompletedProcess(["gh", "auth", "status"], 1, "", "not logged in")
        with patch("human_ai.web_ui.shutil.which", return_value="/usr/local/bin/gh"), patch(
            "human_ai.web_ui.subprocess.run", return_value=auth_result
        ), patch.object(self.agent.model, "complete") as complete:
            web = serve_in_thread(self.config, self.agent, self.brain)
            try:
                host, port = web.server.server_address
                chat = self._request(host, port, "POST", "/api/chat", {"message": "sync Gima to GitHub"})
            finally:
                web.stop()
        self.assertEqual(chat["github_status"], "authentication_required")
        self.assertIn("GitHub CLI is installed", chat["reply"])
        self.assertIn("gh auth login", chat["reply"])
        complete.assert_not_called()

    def test_web_chat_video_song_with_image_asks_for_audio_without_model_timeout(self):
        image = self.config.resolved_hands_in_dir / "portrait.jpeg"
        image.parent.mkdir(parents=True, exist_ok=True)
        image.write_bytes(b"jpeg")
        message = f"make a video song from uploaded image\n\nAttached files in hands/in:\n- portrait.jpeg: {image}"
        with patch.object(BrainServer, "status", return_value={"running": True, "pid": 123, "models": None}):
            with patch.object(self.agent.model, "complete") as complete:
                web = serve_in_thread(self.config, self.agent, self.brain)
                try:
                    host, port = web.server.server_address
                    chat = self._request(host, port, "POST", "/api/chat", {"message": message})
                finally:
                    web.stop()

        self.assertEqual(chat["media_status"], "needs_audio")
        self.assertIn("Attach the MP3", chat["reply"])
        complete.assert_not_called()

    def test_web_chat_plain_video_request_answers_conversationally_before_model(self):
        self.config.model.enabled = True
        with patch.object(BrainServer, "status", return_value={"running": False, "ready": False, "pid": None, "models": None}):
            with patch.object(self.agent.model, "complete") as complete:
                web = serve_in_thread(self.config, self.agent, self.brain)
                try:
                    host, port = web.server.server_address
                    chat = self._request(host, port, "POST", "/api/chat", {"message": "can you make a aeroplane video"})
                finally:
                    web.stop()

        self.assertEqual(chat["media_status"], "video_conversation_prompt")
        self.assertIn("Yes. I can help you make a video", chat["reply"])
        self.assertIn("aeroplane", chat["suggested_prompt"])
        self.assertIn("storyboard", chat["reply"])
        complete.assert_not_called()

    def test_web_chat_own_voice_request_asks_for_audio_sample(self):
        self.config.model.enabled = True
        with patch.object(BrainServer, "status", return_value={"running": False, "ready": False, "pid": None, "models": None}):
            with patch.object(self.agent.model, "complete") as complete:
                web = serve_in_thread(self.config, self.agent, self.brain)
                try:
                    host, port = web.server.server_address
                    chat = self._request(host, port, "POST", "/api/chat", {"message": "Add my own voice. This voice is my own voice."})
                finally:
                    web.stop()

        self.assertEqual(chat["media_status"], "own_voice_needs_audio_sample")
        self.assertIn("Upload an MP3/WAV/M4A sample", chat["reply"])
        complete.assert_not_called()

    def test_web_api_saves_own_voice_profile_with_consent(self):
        voice = Path(self.temp.name) / "voice.mp3"
        voice.write_bytes(b"mp3 voice")
        with patch.object(BrainServer, "status", return_value={"running": True, "pid": 123, "models": None}):
            web = serve_in_thread(self.config, self.agent, self.brain)
            try:
                host, port = web.server.server_address
                saved = self._request(
                    host,
                    port,
                    "POST",
                    "/api/voice-profile/save",
                    {"profile_name": "Gimhan original voice 2", "audio_path": str(voice), "consent": True},
                )
            finally:
                web.stop()

        self.assertEqual(saved["profile_name"], "Gimhan original voice 2")
        self.assertEqual(saved["backend_status"], "reference_saved_not_cloned")
        self.assertTrue(Path(saved["sample_path"]).exists())
        self.assertEqual(Path(saved["sample_path"]).read_bytes(), b"mp3 voice")
        self.assertTrue((self.config.resolved_data_dir / "voice" / "profiles" / "default_voice_profile.json").exists())

    def test_web_chat_lip_sync_with_audio_and_image_returns_fast_stage_draft(self):
        from human_ai.services import AdvancedVideoSongProject, LipSyncProject

        input_dir = self.config.resolved_hands_in_dir
        input_dir.mkdir(parents=True, exist_ok=True)
        audio = input_dir / "song.mp3"
        image = input_dir / "portrait.jpeg"
        audio.write_bytes(b"mp3")
        image.write_bytes(b"jpeg")
        project_dir = Path(self.temp.name) / "stage_draft"
        project_dir.mkdir()
        output_path = project_dir / "output_advanced_video_song.mp4"
        manifest_path = project_dir / "manifest.json"
        storyboard_path = project_dir / "storyboard.md"
        analysis_path = project_dir / "audio_analysis.json"
        prompt_pack_path = project_dir / "scene_prompt_pack.md"
        for path, content in [
            (output_path, b"mp4"),
            (manifest_path, b"{}"),
            (storyboard_path, b"# storyboard"),
            (analysis_path, b"{}"),
            (prompt_pack_path, b"# prompts"),
        ]:
            path.write_bytes(content)
        lip_dir = Path(self.temp.name) / "lip_plan"
        lip_dir.mkdir()
        lip_manifest = lip_dir / "manifest.json"
        lip_prompt = lip_dir / "prompt.txt"
        lip_safety = lip_dir / "safety.md"
        lip_timing = lip_dir / "timing.md"
        lip_backend = lip_dir / "backend.md"
        lip_eval = lip_dir / "eval.md"
        for path in [lip_manifest, lip_prompt, lip_safety, lip_timing, lip_backend, lip_eval]:
            path.write_text("plan", encoding="utf-8")
        message = (
            "make lip sync stage performing video song live singing for uploaded song\n\n"
            "Attached files in hands/in:\n"
            f"- song.mp3: {audio}\n"
            f"- portrait.jpeg: {image}"
        )
        with patch.object(BrainServer, "status", return_value={"running": True, "pid": 123, "models": None}):
            with patch.object(self.agent.model, "complete") as complete, patch(
                "human_ai.web_ui.NeuralLipSyncRenderer.status",
                return_value={"ready": False, "missing": ["inference.py"], "backend_dir": "/missing"},
            ), patch("human_ai.web_ui.AdvancedVideoSongRenderer.render") as render, patch(
                "human_ai.web_ui.LipSyncPlanner.create_project"
            ) as plan:
                render.return_value = AdvancedVideoSongProject(
                    project_dir,
                    output_path,
                    manifest_path,
                    storyboard_path,
                    analysis_path,
                    prompt_pack_path,
                )
                plan.return_value = LipSyncProject(
                    lip_dir,
                    lip_manifest,
                    lip_prompt,
                    lip_safety,
                    lip_timing,
                    lip_backend,
                    lip_eval,
                )
                web = serve_in_thread(self.config, self.agent, self.brain)
                try:
                    host, port = web.server.server_address
                    chat = self._request(host, port, "POST", "/api/chat", {"message": message})
                finally:
                    web.stop()

        self.assertEqual(chat["media_status"], "fast_lip_sync_stage_draft_rendered")
        self.assertIn("local stage-performance draft", chat["reply"])
        self.assertEqual(chat["generation_truth"], "local_ffmpeg_draft_not_ai_generated_frames")
        self.assertTrue(any(file["path"] == str(output_path) for file in chat["files"]))
        self.assertTrue(any(file["download_url"].startswith("/api/download?path=") for file in chat["files"]))
        complete.assert_not_called()

    def test_web_chat_true_ai_video_request_requires_open_video_backend(self):
        input_dir = self.config.resolved_hands_in_dir
        input_dir.mkdir(parents=True, exist_ok=True)
        audio = input_dir / "song.mp3"
        image = input_dir / "portrait.jpeg"
        audio.write_bytes(b"mp3")
        image.write_bytes(b"jpeg")
        message = (
            "make true AI generated video frames with lip sync\n\n"
            "Attached files in hands/in:\n"
            f"- song.mp3: {audio}\n"
            f"- portrait.jpeg: {image}"
        )
        with patch.object(BrainServer, "status", return_value={"running": True, "pid": 123, "models": None}):
            with patch.object(self.agent.model, "complete") as complete, patch(
                "human_ai.web_ui.OpenSourceVideoApiRenderer.status",
                return_value={"backend": "ComfyUI", "ready": False, "error": "connection refused"},
            ):
                web = serve_in_thread(self.config, self.agent, self.brain)
                try:
                    host, port = web.server.server_address
                    chat = self._request(host, port, "POST", "/api/chat", {"message": message})
                finally:
                    web.stop()

        self.assertEqual(chat["media_status"], "needs_true_ai_video_backend")
        self.assertEqual(chat["generation_truth"], "no_ai_video_frames_generated")
        self.assertIn("will not label the local FFmpeg draft as AI-generated", chat["reply"])
        self.assertFalse(chat["open_video_backend"]["ready"])
        complete.assert_not_called()

    def test_web_chat_can_force_brain_answer_without_model(self):
        self.config.model.enabled = True
        self.agent.memory.add(
            Record(
                category="technical",
                title="Brain first mode",
                content="Gima should answer use brain requests from brain.csv before using the local model.",
                source="test_memory",
                status="active",
                confidence="1.0",
            )
        )
        with patch.object(BrainServer, "status", return_value={"running": True, "pid": 123, "models": None}):
            with patch.object(self.agent.model, "complete") as complete:
                web = serve_in_thread(self.config, self.agent, self.brain)
                try:
                    host, port = web.server.server_address
                    chat = self._request(
                        host,
                        port,
                        "POST",
                        "/api/chat",
                        {"message": "use brain: brain first mode"},
                    )
                finally:
                    web.stop()
        self.assertTrue(chat["used_brain"])
        self.assertIn("Research-backed answer from Gima memory", chat["reply"])
        self.assertIn("Brain first mode", chat["reply"])
        self.assertEqual(chat["brain_rows"][0]["title"], "Brain first mode")
        complete.assert_not_called()

    def test_web_chat_generates_fastest_cars_table_files_without_model_timeout(self):
        self.config.model.enabled = True
        with patch.object(BrainServer, "status", return_value={"running": True, "pid": 123, "models": None}):
            with patch.object(self.agent.model, "complete") as complete:
                web = serve_in_thread(self.config, self.agent, self.brain)
                try:
                    host, port = web.server.server_address
                    chat = self._request(host, port, "POST", "/api/chat", {"message": "make a table of fastest cars"})
                finally:
                    web.stop()
        self.assertIn("Koenigsegg", chat["reply"])
        self.assertIn("| rank | car |", chat["reply"])
        self.assertIn("files", chat)
        paths = [Path(file["path"]) for file in chat["files"]]
        self.assertTrue(any(path.name == "fastest_cars.csv" for path in paths))
        self.assertTrue(any(path.name == "fastest_cars_report.pdf" for path in paths))
        for path in paths:
            self.assertTrue(path.exists(), path)
        complete.assert_not_called()

    def test_web_api_saves_bindings_and_multi_mind_learning(self):
        with patch.object(BrainServer, "status", return_value={"running": False, "pid": None, "models": None}):
            web = serve_in_thread(self.config, self.agent, self.brain)
            try:
                host, port = web.server.server_address
                before = self._request(host, port, "GET", "/api/bindings")
                self.assertIn("bindings", before)
                quotas = self._request(host, port, "GET", "/api/free-quotas")
                self.assertTrue(quotas["free_quota_mode"])
                self.assertIn("free_quota_usage.csv", quotas["path"])

                saved = self._request(
                    host,
                    port,
                    "POST",
                    "/api/bindings/save",
                    {"provider": "openai", "api_key": "sk-test-openai"},
                )
                self.assertTrue(saved["ok"])
                saved_veo = self._request(
                    host,
                    port,
                    "POST",
                    "/api/bindings/save",
                    {"provider": "openrouter_veo", "api_key": "sk-test-openrouter-video"},
                )
                saved_mai = self._request(
                    host,
                    port,
                    "POST",
                    "/api/bindings/save",
                    {"provider": "openrouter_mai", "api_key": "sk-test-openrouter-speech"},
                )
                saved_management = self._request(
                    host,
                    port,
                    "POST",
                    "/api/bindings/save",
                    {"provider": "openrouter_management", "api_key": "sk-test-openrouter-management"},
                )
                self.assertTrue(saved_veo["ok"])
                self.assertTrue(saved_mai["ok"])
                self.assertTrue(saved_management["ok"])
                secrets_text = (self.config.resolved_workspace / ".human-ai" / "secrets.env").read_text(encoding="utf-8")
                self.assertIn("OPENAI_API_KEY", secrets_text)
                self.assertIn("OPENROUTER_VIDEO_API_KEY", secrets_text)
                self.assertIn("OPENROUTER_SPEECH_API_KEY", secrets_text)
                self.assertIn("OPENROUTER_MANAGEMENT_KEY", secrets_text)
                providers = {row["provider"] for row in saved_management["bindings"]}
                self.assertIn("openrouter_veo", providers)
                self.assertIn("openrouter_mai", providers)
                self.assertIn("openrouter_management", providers)

                with patch.object(
                    self.agent,
                    "transfer_teacher_knowledge",
                    return_value=[("local", "local answer"), ("chatgpt", "teacher answer")],
                ) as transfer:
                    minds = self._request(
                        host,
                        port,
                        "POST",
                        "/api/minds/ask",
                        {"prompt": "teach Gima video UI", "providers": ["local", "chatgpt"]},
                    )
                self.assertEqual(minds["results"][1]["answer"], "teacher answer")
                transfer.assert_called_once_with("teach Gima video UI", ["local", "chatgpt"])
                continuous_csv = self.config.resolved_continuous_dir / "work_steps.csv"
                self.assertIn("multi_mind_ask", continuous_csv.read_text(encoding="utf-8"))
            finally:
                web.stop()

    def test_web_api_lists_and_selects_openrouter_models(self):
        cache_dir = self.config.resolved_data_dir / "openrouter"
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "models_catalog.json").write_text(
            json.dumps(
                {
                    "data": [
                        {
                            "id": "openai/gpt-4o",
                            "name": "GPT-4o",
                            "context_length": 128000,
                            "architecture": {"input_modalities": ["text", "image"], "output_modalities": ["text"]},
                            "pricing": {"prompt": "0.0000025", "completion": "0.00001"},
                        },
                        {
                            "id": "openrouter/free",
                            "name": "OpenRouter Free",
                            "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
                            "pricing": {"prompt": "0", "completion": "0"},
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        with patch.object(BrainServer, "status", return_value={"running": False, "pid": None, "models": None}):
            web = serve_in_thread(self.config, self.agent, self.brain)
            try:
                host, port = web.server.server_address
                models = self._request(host, port, "GET", "/api/openrouter/models?q=gpt&limit=10")
                selected = self._request(host, port, "POST", "/api/openrouter/select", {"model": "openai/gpt-4o"})
                routing = self._request(
                    host,
                    port,
                    "POST",
                    "/api/openrouter/routing",
                    {
                        "routing_sort": "throughput",
                        "data_collection": "deny",
                        "fallback_models": "openrouter/auto, openrouter/free",
                    },
                )
            finally:
                web.stop()
        self.assertEqual(models["source"], "cache")
        self.assertEqual(models["models"][0]["id"], "openai/gpt-4o")
        self.assertTrue(selected["ok"])
        self.assertEqual(selected["selected_model"], "openai/gpt-4o")
        self.assertEqual(routing["routing_sort"], "throughput")
        self.assertEqual(routing["fallback_models"], ["openrouter/auto", "openrouter/free"])
        self.assertEqual((cache_dir / "selected_model.txt").read_text(encoding="utf-8"), "openai/gpt-4o")

    def test_web_api_ai_router_plan_keeps_private_tasks_local(self):
        with patch.object(BrainServer, "status", return_value={"running": False, "pid": None, "models": None}):
            web = serve_in_thread(self.config, self.agent, self.brain)
            try:
                host, port = web.server.server_address
                plan = self._request(
                    host,
                    port,
                    "GET",
                    "/api/ai-router/plan?message=debug%20private%20api%20key&privacy=high",
                )
            finally:
                web.stop()

        self.assertEqual(plan["provider"], "local")
        self.assertEqual(plan["task_category"], "PRIVATE_LOCAL_TASK")
        self.assertFalse(plan["security"]["secrets_returned"])
        self.assertFalse(plan["security"]["management_key_used_for_inference"])
        serialized = json.dumps(plan)
        self.assertNotIn("Authorization", serialized)
        self.assertNotIn("sk-", serialized)

    def test_web_api_generates_openai_image_artifact(self):
        image_dir = self.config.resolved_hands_out_dir / "fake_openai_image"
        image_dir.mkdir(parents=True, exist_ok=True)
        image_path = image_dir / "generated_image.png"
        manifest_path = image_dir / "manifest.json"
        prompt_path = image_dir / "prompt.txt"
        image_path.write_bytes(b"\x89PNG\r\n\x1a\nfake")
        manifest_path.write_text('{"provider":"openai"}', encoding="utf-8")
        prompt_path.write_text("logo", encoding="utf-8")

        def fake_generate(prompt, model="gpt-image-2", size="1024x1024", quality="auto", consent=False):
            self.assertEqual(prompt, "Gima logo")
            self.assertEqual(model, "gpt-image-2")
            self.assertTrue(consent)
            return {
                "output_path": str(image_path),
                "manifest_path": str(manifest_path),
                "prompt_path": str(prompt_path),
                "model": model,
                "size": size,
                "quality": quality,
                "revised_prompt": "polished Gima logo",
            }

        with patch.object(BrainServer, "status", return_value={"running": False, "pid": None, "models": None}), patch(
            "human_ai.web_ui.OpenAIImageGenerator.generate", side_effect=fake_generate
        ):
            web = serve_in_thread(self.config, self.agent, self.brain)
            try:
                host, port = web.server.server_address
                image = self._request(
                    host,
                    port,
                    "POST",
                    "/api/media/openai-image-generate",
                    {"prompt": "Gima logo", "model": "gpt-image-2", "size": "1024x1024", "quality": "auto", "consent": True},
                )
            finally:
                web.stop()

        self.assertEqual(image["status"], "generated")
        self.assertEqual(image["generated_path"], str(image_path))
        self.assertEqual(image["manifest"], str(manifest_path))
        self.assertEqual(image["revised_prompt"], "polished Gima logo")

    def test_web_api_generates_huggingface_image_artifact(self):
        image_dir = self.config.resolved_hands_out_dir / "fake_huggingface_image"
        image_dir.mkdir(parents=True, exist_ok=True)
        image_path = image_dir / "output_huggingface_image.png"
        manifest_path = image_dir / "manifest.json"
        prompt_path = image_dir / "prompt.txt"
        image_path.write_bytes(b"\x89PNG\r\n\x1a\nfake")
        manifest_path.write_text('{"provider":"huggingface"}', encoding="utf-8")
        prompt_path.write_text("Astronaut riding a horse", encoding="utf-8")

        def fake_generate(prompt, model="black-forest-labs/FLUX.1-dev", provider="wavespeed", consent=False):
            self.assertEqual(prompt, "Astronaut riding a horse")
            self.assertEqual(model, "black-forest-labs/FLUX.1-dev")
            self.assertEqual(provider, "wavespeed")
            self.assertTrue(consent)
            return {
                "status": "generated",
                "provider": "huggingface",
                "inference_provider": provider,
                "model": model,
                "output_path": str(image_path),
                "manifest_path": str(manifest_path),
                "prompt_path": str(prompt_path),
            }

        with patch.object(BrainServer, "status", return_value={"running": False, "pid": None, "models": None}), patch(
            "human_ai.web_ui.HuggingFaceImageGenerator.generate", side_effect=fake_generate
        ):
            web = serve_in_thread(self.config, self.agent, self.brain)
            try:
                host, port = web.server.server_address
                image = self._request(
                    host,
                    port,
                    "POST",
                    "/api/media/huggingface-image-generate",
                    {
                        "prompt": "Astronaut riding a horse",
                        "model": "black-forest-labs/FLUX.1-dev",
                        "provider": "wavespeed",
                        "consent": True,
                    },
                )
            finally:
                web.stop()

        self.assertEqual(image["status"], "generated")
        self.assertEqual(image["provider"], "huggingface")
        self.assertEqual(image["inference_provider"], "wavespeed")
        self.assertEqual(image["model"], "black-forest-labs/FLUX.1-dev")
        self.assertEqual(image["generated_path"], str(image_path))

    def test_web_api_extracts_huggingface_features(self):
        feature_dir = self.config.resolved_hands_out_dir / "fake_huggingface_features"
        feature_dir.mkdir(parents=True, exist_ok=True)
        input_path = feature_dir / "input.txt"
        features_path = feature_dir / "features.json"
        csv_path = feature_dir / "features.csv"
        manifest_path = feature_dir / "manifest.json"
        input_path.write_text("Today is sunny.", encoding="utf-8")
        features_path.write_text("[[0.1, 0.2]]", encoding="utf-8")
        csv_path.write_text("index,value\n0,0.1\n1,0.2\n", encoding="utf-8")
        manifest_path.write_text('{"provider":"huggingface"}', encoding="utf-8")

        def fake_extract(text, model="microsoft/harrier-oss-v1-0.6b", provider="hf-inference", consent=False):
            self.assertEqual(text, "Today is a sunny day and I will get some ice cream.")
            self.assertEqual(model, "microsoft/harrier-oss-v1-0.6b")
            self.assertEqual(provider, "hf-inference")
            self.assertTrue(consent)
            return {
                "status": "generated",
                "provider": "huggingface",
                "inference_provider": provider,
                "model": model,
                "input_path": str(input_path),
                "features_path": str(features_path),
                "csv_path": str(csv_path),
                "manifest_path": str(manifest_path),
                "stats": {"count": 2, "preview_count": 2, "mean": 0.15},
            }

        with patch.object(BrainServer, "status", return_value={"running": False, "pid": None, "models": None}), patch(
            "human_ai.web_ui.HuggingFaceFeatureExtractor.extract", side_effect=fake_extract
        ):
            web = serve_in_thread(self.config, self.agent, self.brain)
            try:
                host, port = web.server.server_address
                features = self._request(
                    host,
                    port,
                    "POST",
                    "/api/ai/huggingface-feature-extract",
                    {
                        "text": "Today is a sunny day and I will get some ice cream.",
                        "model": "microsoft/harrier-oss-v1-0.6b",
                        "provider": "hf-inference",
                        "consent": True,
                    },
                )
            finally:
                web.stop()

        self.assertEqual(features["status"], "generated")
        self.assertEqual(features["provider"], "huggingface")
        self.assertEqual(features["inference_provider"], "hf-inference")
        self.assertEqual(features["model"], "microsoft/harrier-oss-v1-0.6b")
        self.assertEqual(features["stats"]["count"], 2)
        self.assertIn("/api/download?path=", features["features_download_url"])

    def test_web_api_generates_transformers_text_artifact(self):
        text_dir = self.config.resolved_hands_out_dir / "fake_transformers_text"
        text_dir.mkdir(parents=True, exist_ok=True)
        response_path = text_dir / "response.txt"
        manifest_path = text_dir / "manifest.json"
        prompt_path = text_dir / "prompt.txt"
        response_path.write_text("Ahoy from local Gemma.\n", encoding="utf-8")
        manifest_path.write_text('{"provider":"local"}', encoding="utf-8")
        prompt_path.write_text("Who are you?", encoding="utf-8")

        def fake_generate(prompt, model="google/gemma-2-2b-it", device="auto", max_new_tokens=256, local_files_only=True, consent=False):
            self.assertEqual(prompt, "Who are you?")
            self.assertEqual(model, "google/gemma-2-2b-it")
            self.assertEqual(device, "mps")
            self.assertEqual(max_new_tokens, 256)
            self.assertTrue(local_files_only)
            self.assertTrue(consent)
            return {
                "status": "generated",
                "provider": "local",
                "model": model,
                "device": device,
                "answer": "Ahoy from local Gemma.",
                "prompt_path": str(prompt_path),
                "response_path": str(response_path),
                "manifest_path": str(manifest_path),
                "local_files_only": local_files_only,
            }

        with patch.object(BrainServer, "status", return_value={"running": False, "pid": None, "models": None}), patch(
            "human_ai.web_ui.TransformersTextGenerator.generate", side_effect=fake_generate
        ):
            web = serve_in_thread(self.config, self.agent, self.brain)
            try:
                host, port = web.server.server_address
                response = self._request(
                    host,
                    port,
                    "POST",
                    "/api/local/transformers-generate",
                    {
                        "prompt": "Who are you?",
                        "model": "google/gemma-2-2b-it",
                        "device": "mps",
                        "max_new_tokens": 256,
                        "local_files_only": True,
                        "consent": True,
                    },
                )
            finally:
                web.stop()

        self.assertEqual(response["status"], "generated")
        self.assertEqual(response["provider"], "local")
        self.assertEqual(response["model"], "google/gemma-2-2b-it")
        self.assertEqual(response["answer"], "Ahoy from local Gemma.")
        self.assertIn("/api/download?path=", response["response_download_url"])

    def test_web_api_creates_whatsapp_draft(self):
        whatsapp_dir = self.config.resolved_hands_out_dir / "fake_whatsapp"
        whatsapp_dir.mkdir(parents=True, exist_ok=True)
        message_path = whatsapp_dir / "message.txt"
        manifest_path = whatsapp_dir / "manifest.json"
        message_path.write_text("Hello from Gima", encoding="utf-8")
        manifest_path.write_text('{"provider":"whatsapp"}', encoding="utf-8")

        def fake_draft(to, message):
            self.assertEqual(to, "+94771234567")
            self.assertEqual(message, "Hello from Gima")
            return {
                "status": "drafted",
                "provider": "whatsapp",
                "recipient": "94771234567",
                "message": message,
                "wa_me_link": "https://wa.me/94771234567?text=Hello%20from%20Gima",
                "message_path": str(message_path),
                "manifest_path": str(manifest_path),
            }

        with patch.object(BrainServer, "status", return_value={"running": False, "pid": None, "models": None}), patch(
            "human_ai.web_ui.WhatsAppMessenger.draft_link", side_effect=fake_draft
        ):
            web = serve_in_thread(self.config, self.agent, self.brain)
            try:
                host, port = web.server.server_address
                response = self._request(
                    host,
                    port,
                    "POST",
                    "/api/whatsapp/draft",
                    {"to": "+94771234567", "message": "Hello from Gima"},
                )
            finally:
                web.stop()

        self.assertEqual(response["status"], "drafted")
        self.assertEqual(response["recipient"], "94771234567")
        self.assertIn("wa.me", response["wa_me_link"])
        self.assertIn("/api/download?path=", response["manifest_download_url"])

    def test_web_api_sends_whatsapp_message(self):
        whatsapp_dir = self.config.resolved_hands_out_dir / "fake_whatsapp_send"
        whatsapp_dir.mkdir(parents=True, exist_ok=True)
        message_path = whatsapp_dir / "message.txt"
        response_path = whatsapp_dir / "response.json"
        manifest_path = whatsapp_dir / "manifest.json"
        message_path.write_text("Hello from Gima", encoding="utf-8")
        response_path.write_text('{"messages":[{"id":"wamid.test"}]}', encoding="utf-8")
        manifest_path.write_text('{"provider":"whatsapp"}', encoding="utf-8")

        def fake_send(to, message, consent=False):
            self.assertEqual(to, "+94771234567")
            self.assertEqual(message, "Hello from Gima")
            self.assertTrue(consent)
            return {
                "status": "sent",
                "provider": "whatsapp",
                "recipient": "94771234567",
                "message_path": str(message_path),
                "response_path": str(response_path),
                "manifest_path": str(manifest_path),
                "api_response": {"messages": [{"id": "wamid.test"}]},
            }

        with patch.object(BrainServer, "status", return_value={"running": False, "pid": None, "models": None}), patch(
            "human_ai.web_ui.WhatsAppMessenger.send_text", side_effect=fake_send
        ):
            web = serve_in_thread(self.config, self.agent, self.brain)
            try:
                host, port = web.server.server_address
                response = self._request(
                    host,
                    port,
                    "POST",
                    "/api/whatsapp/send",
                    {"to": "+94771234567", "message": "Hello from Gima", "consent": True},
                )
            finally:
                web.stop()

        self.assertEqual(response["status"], "sent")
        self.assertEqual(response["recipient"], "94771234567")
        self.assertEqual(response["api_response"]["messages"][0]["id"], "wamid.test")
        self.assertIn("/api/download?path=", response["response_download_url"])

    def test_web_api_retrieves_whatsapp_messages(self):
        with patch.object(BrainServer, "status", return_value={"running": False, "pid": None, "models": None}):
            web = serve_in_thread(self.config, self.agent, self.brain)
            try:
                host, port = web.server.server_address
                self._request(
                    host,
                    port,
                    "POST",
                    "/api/whatsapp/draft",
                    {"to": "+94771234567", "message": "Need the invoice please"},
                )
                response = self._request(host, port, "GET", "/api/whatsapp/messages?query=invoice&limit=5")
            finally:
                web.stop()

        self.assertEqual(response["status"], "ok")
        self.assertEqual(response["count"], 1)
        self.assertIn("invoice", response["messages"][0]["text"])

    def test_web_api_receives_whatsapp_webhook(self):
        payload = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "from": "94771234567",
                                        "id": "wamid.inbound",
                                        "timestamp": "123456",
                                        "type": "text",
                                        "text": {"body": "Can you send the quote?"},
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        }
        with patch.object(BrainServer, "status", return_value={"running": False, "pid": None, "models": None}):
            web = serve_in_thread(self.config, self.agent, self.brain)
            try:
                host, port = web.server.server_address
                response = self._request(host, port, "POST", "/api/whatsapp/webhook", payload)
                saved = self._request(host, port, "GET", "/api/whatsapp/messages?query=quote&direction=inbound")
            finally:
                web.stop()

        self.assertEqual(response["status"], "received")
        self.assertEqual(response["received_count"], 1)
        self.assertEqual(saved["count"], 1)
        self.assertIn("quote", saved["messages"][0]["text"])

    def test_web_api_generates_openrouter_veo_video_artifact(self):
        video_dir = self.config.resolved_hands_out_dir / "fake_openrouter_video"
        video_dir.mkdir(parents=True, exist_ok=True)
        video_path = video_dir / "output_openrouter_video.mp4"
        manifest_path = video_dir / "manifest.json"
        prompt_path = video_dir / "prompt.txt"
        video_path.write_bytes(b"fake mp4")
        manifest_path.write_text('{"provider":"openrouter"}', encoding="utf-8")
        prompt_path.write_text("cinematic video", encoding="utf-8")

        def fake_generate(prompt, model="google/veo-3.1", aspect_ratio="16:9", duration=8, resolution="720p", generate_audio=True, timeout_seconds=900, consent=False):
            self.assertEqual(prompt, "cinematic video")
            self.assertEqual(model, "google/veo-3.1")
            self.assertEqual(aspect_ratio, "16:9")
            self.assertTrue(consent)
            return {
                "output_path": str(video_path),
                "manifest_path": str(manifest_path),
                "prompt_path": str(prompt_path),
                "job_id": "job-1",
                "generation_id": "gen-1",
                "model": model,
                "status": "completed",
                "usage": {"cost": 0.5},
            }

        with patch.object(BrainServer, "status", return_value={"running": False, "pid": None, "models": None}), patch(
            "human_ai.web_ui.OpenRouterVideoGenerator.generate", side_effect=fake_generate
        ):
            web = serve_in_thread(self.config, self.agent, self.brain)
            try:
                host, port = web.server.server_address
                video = self._request(
                    host,
                    port,
                    "POST",
                    "/api/media/openrouter-video-generate",
                    {
                        "prompt": "cinematic video",
                        "model": "google/veo-3.1",
                        "aspect_ratio": "16:9",
                        "duration": 8,
                        "resolution": "720p",
                        "generate_audio": True,
                        "consent": True,
                    },
                )
            finally:
                web.stop()

        self.assertEqual(video["status"], "completed")
        self.assertEqual(video["generated_path"], str(video_path))
        self.assertEqual(video["manifest"], str(manifest_path))
        self.assertEqual(video["job_id"], "job-1")

    def test_web_chat_can_answer_from_all_linked_ai_engines(self):
        with patch.object(BrainServer, "status", return_value={"running": False, "pid": None, "models": None}):
            web = serve_in_thread(self.config, self.agent, self.brain)
            try:
                host, port = web.server.server_address
                self._request(host, port, "POST", "/api/bindings/save", {"provider": "openai", "api_key": "sk-test-openai"})
                self._request(host, port, "POST", "/api/bindings/save", {"provider": "anthropic", "api_key": "sk-test-anthropic"})
                with patch.dict("os.environ", {"CLOUD_ALLOWED": "true"}), patch.object(
                    self.agent,
                    "answer_with_all_ai",
                    return_value=("combined teacher answer", [("chatgpt", "a"), ("anthropic", "b")]),
                ) as answer_all:
                    chat = self._request(host, port, "POST", "/api/chat", {"message": "ask all ai engines how to improve Gima"})
            finally:
                web.stop()
        self.assertEqual(chat["reply"], "combined teacher answer")
        self.assertEqual(chat["providers"], ["chatgpt", "anthropic"])
        answer_all.assert_called_once()
        call_prompt, call_providers = answer_all.call_args.args
        self.assertEqual(call_prompt, "how to improve")
        self.assertIn("chatgpt", call_providers)
        self.assertIn("anthropic", call_providers)
        self.assertNotIn("local", call_providers)

    def test_web_chat_blocks_all_ai_when_cloud_is_not_allowed(self):
        with patch.object(BrainServer, "status", return_value={"running": True, "pid": 123, "models": None}):
            web = serve_in_thread(self.config, self.agent, self.brain)
            try:
                host, port = web.server.server_address
                self._request(host, port, "POST", "/api/bindings/save", {"provider": "openai", "api_key": "sk-test-openai"})
                with patch.dict("os.environ", {}, clear=True), patch.object(self.agent, "answer_with_all_ai") as answer_all:
                    chat = self._request(host, port, "POST", "/api/chat", {"message": "ask all ai engines how to improve Gima"})
            finally:
                web.stop()
        self.assertTrue(chat["cloud_blocked"])
        self.assertIn("CLOUD_ALLOWED", chat["reply"])
        answer_all.assert_not_called()

    def test_web_chat_blocks_explicit_chatgpt_mode_when_cloud_is_not_allowed(self):
        with patch.object(BrainServer, "status", return_value={"running": True, "pid": 123, "models": None}):
            web = serve_in_thread(self.config, self.agent, self.brain)
            try:
                host, port = web.server.server_address
                self._request(host, port, "POST", "/api/bindings/save", {"provider": "openai", "api_key": "sk-test-openai"})
                with patch.dict("os.environ", {}, clear=True), patch.object(self.agent.teacher_models, "ask") as ask:
                    chat = self._request(host, port, "POST", "/api/chat", {"message": "hello", "chat_provider": "chatgpt"})
            finally:
                web.stop()
        self.assertTrue(chat["cloud_blocked"])
        self.assertEqual(chat["requested_provider"], "chatgpt")
        self.assertIn("CLOUD_ALLOWED", chat["reply"])
        ask.assert_not_called()

    def test_web_chat_uses_explicit_chatgpt_mode_when_cloud_is_allowed(self):
        with patch.object(BrainServer, "status", return_value={"running": True, "pid": 123, "models": None}):
            web = serve_in_thread(self.config, self.agent, self.brain)
            try:
                host, port = web.server.server_address
                self._request(host, port, "POST", "/api/bindings/save", {"provider": "openai", "api_key": "sk-test-openai"})
                with patch.dict("os.environ", {"CLOUD_ALLOWED": "true"}), patch.object(self.agent.teacher_models, "ask", return_value="chatgpt mode answer") as ask:
                    chat = self._request(host, port, "POST", "/api/chat", {"message": "hello", "chat_provider": "openai"})
            finally:
                web.stop()
        self.assertEqual(chat["reply"], "chatgpt mode answer")
        self.assertEqual(chat["provider"], "chatgpt")
        ask.assert_called_once()

    def test_web_chat_explicit_chatgpt_mode_beats_weather_artifact_handler(self):
        with patch.object(BrainServer, "status", return_value={"running": True, "pid": 123, "models": None}):
            web = serve_in_thread(self.config, self.agent, self.brain)
            try:
                host, port = web.server.server_address
                self._request(host, port, "POST", "/api/bindings/save", {"provider": "openai", "api_key": "sk-test-openai"})
                with patch.dict("os.environ", {"CLOUD_ALLOWED": "true"}), patch.object(self.agent.teacher_models, "ask", return_value="chatgpt weather answer") as ask:
                    chat = self._request(host, port, "POST", "/api/chat", {"message": "current weather in Osaka", "chat_provider": "chatgpt"})
            finally:
                web.stop()
        self.assertEqual(chat["reply"], "chatgpt weather answer")
        self.assertEqual(chat["provider"], "chatgpt")
        self.assertFalse(chat.get("used_internet", False))
        ask.assert_called_once()

    def test_web_chat_explicit_local_mode_does_not_auto_cloud_when_cloud_allowed(self):
        self.config.model.enabled = True
        with patch.object(BrainServer, "status", return_value={"running": True, "ready": True, "pid": 123, "models": None}):
            web = serve_in_thread(self.config, self.agent, self.brain)
            try:
                host, port = web.server.server_address
                self._request(host, port, "POST", "/api/bindings/save", {"provider": "openai", "api_key": "sk-test-openai"})
                with patch.dict("os.environ", {"CLOUD_ALLOWED": "true"}), patch.object(self.agent.teacher_models, "ask") as ask, patch.object(
                    self.agent.model, "complete", return_value="local mode answer"
                ) as complete:
                    chat = self._request(host, port, "POST", "/api/chat", {"message": "explain Gima simply", "chat_provider": "local"})
            finally:
                web.stop()
        self.assertEqual(chat["reply"], "local mode answer")
        ask.assert_not_called()
        complete.assert_called_once()

    def test_web_chat_uses_cloud_when_linked_before_local_model(self):
        with patch.object(BrainServer, "status", return_value={"running": True, "pid": 123, "models": None}):
            web = serve_in_thread(self.config, self.agent, self.brain)
            try:
                host, port = web.server.server_address
                self._request(host, port, "POST", "/api/bindings/save", {"provider": "openai", "api_key": "sk-test-openai"})
                with patch.dict("os.environ", {"CLOUD_ALLOWED": "true"}), patch.object(self.agent.teacher_models, "ask", return_value="openai answer") as ask, patch.object(
                    self.agent.model, "complete"
                ) as complete:
                    chat = self._request(host, port, "POST", "/api/chat", {"message": "explain Gima simply"})
            finally:
                web.stop()
        self.assertEqual(chat["reply"], "openai answer")
        self.assertEqual(chat["provider"], "chatgpt")
        self.assertEqual(chat["configured_model"], self.config.teacher_models.openai_model)
        ask.assert_called_once()
        complete.assert_not_called()

    def test_web_chat_falls_back_to_next_cloud_provider_when_openai_quota_fails(self):
        def fake_ask(provider, prompt):
            if provider == "chatgpt":
                raise RuntimeError("insufficient_quota")
            if provider == "openrouter":
                return "openrouter answer"
            raise AssertionError(provider)

        with patch.object(BrainServer, "status", return_value={"running": True, "pid": 123, "models": None}):
            web = serve_in_thread(self.config, self.agent, self.brain)
            try:
                host, port = web.server.server_address
                self._request(host, port, "POST", "/api/bindings/save", {"provider": "openai", "api_key": "sk-test-openai"})
                self._request(host, port, "POST", "/api/bindings/save", {"provider": "openrouter", "api_key": "sk-test-openrouter"})
                with patch.dict("os.environ", {"CLOUD_ALLOWED": "true"}), patch.object(self.agent.teacher_models, "ask", side_effect=fake_ask) as ask, patch.object(
                    self.agent.model, "complete"
                ) as complete:
                    chat = self._request(host, port, "POST", "/api/chat", {"message": "explain Gima simply"})
            finally:
                web.stop()
        self.assertEqual(chat["reply"], "openrouter answer")
        self.assertEqual(chat["provider"], "openrouter")
        self.assertIn("chatgpt: insufficient_quota", chat["cloud_errors"][0])
        self.assertEqual(ask.call_count, 2)
        complete.assert_not_called()

    def test_web_chat_routes_weather_to_weather_artifact(self):
        from human_ai.artifacts import ArtifactAnswer

        weather = ArtifactAnswer(
            reply="Current weather for **Osaka, Japan**: 29°C.",
            files=[],
            sources=["https://api.open-meteo.com/v1/forecast"],
            used_internet=True,
        )
        with patch.object(BrainServer, "status", return_value={"running": True, "pid": 123, "models": None}):
            web = serve_in_thread(self.config, self.agent, self.brain)
            try:
                host, port = web.server.server_address
                with patch("human_ai.web_ui.ChatArtifactEngine._weather_answer", return_value=weather) as weather_answer:
                    chat = self._request(host, port, "POST", "/api/chat", {"message": "Gima, search the web for current weather in Osaka."})
            finally:
                web.stop()
        self.assertEqual(chat["reply"], weather.reply)
        self.assertTrue(chat["used_internet"])
        weather_answer.assert_called_once_with("Osaka")

    def test_cloud_prompt_explains_gima_web_route_without_no_browsing_refusal(self):
        from human_ai.web_ui import _cloud_chat_prompt

        prompt = _cloud_chat_prompt("What is the latest AI news today?")

        self.assertIn("Gima can route explicit web/current-information requests", prompt)
        self.assertIn("do not say this chat has no browsing tool", prompt)
        self.assertIn("Gimhan Gunarathne", prompt)
        self.assertIn("not as the raw model provider", prompt)
        self.assertIn("do not answer 'I am OpenAI'", prompt)
        self.assertNotIn("I don’t have access to a browsing tool", prompt)

    def test_status_csv_counter_tolerates_nul_bytes(self):
        from human_ai.web_ui import _count_csv_records

        path = Path(self.temp.name) / "broken.csv"
        path.write_bytes(b"title,content\nok,row\n\x00\x00bad,row\n")

        self.assertEqual(_count_csv_records(path), 2)

    def test_web_api_dashboards_report_capabilities_deployments_agents_and_outputs(self):
        with patch.object(BrainServer, "status", return_value={"running": True, "pid": 123, "models": "test-model"}):
            web = serve_in_thread(self.config, self.agent, self.brain)
            try:
                host, port = web.server.server_address
                output_dir = self.config.resolved_hands_out_dir / "demo"
                output_dir.mkdir(parents=True, exist_ok=True)
                output_file = output_dir / "result.mp4"
                output_file.write_bytes(b"mp4")

                capabilities = self._request(host, port, "GET", "/api/capabilities")
                self.assertIn("capabilities", capabilities)
                self.assertGreaterEqual(len(capabilities["capabilities"]), 1)
                self.assertIn("embodied_robotics", [row["id"] for row in capabilities["capabilities"]])

                doctor = self._request(host, port, "GET", "/api/doctor")
                self.assertIn("hardware", doctor)
                self.assertIn("improvement_plan", doctor)
                self.assertIn("growth_plan", doctor)
                self.assertIn("hardware_upgrade_plan", doctor)
                self.assertIn("legal_earning_plan", doctor)
                self.assertIn("master_ai_director_plan", doctor)
                self.assertIn("criticism_defense_matrix", doctor)
                self.assertIn("daily_improvement_plan", doctor)
                self.assertIn("ai_era_requirements", doctor)
                self.assertIn("own_model_plan", doctor)
                self.assertTrue(any(row["phase"] == "P0 Reliability Core" for row in doctor["improvement_plan"]))
                self.assertEqual(doctor["master_ai_director_plan"]["kind"], "gima_master_ai_director_plan")
                self.assertTrue(any(row["task"] == "Deep reasoning and current research" for row in doctor["master_ai_director_plan"]["routing_rules"]))
                self.assertTrue(any(row["criticism"] == "RAG can still be wrong" for row in doctor["criticism_defense_matrix"]))
                self.assertEqual(doctor["daily_improvement_plan"]["kind"], "gima_daily_improvement_plan")

                codex_mode = self._request(host, port, "GET", "/api/codex-mode")
                self.assertIn("capabilities", codex_mode)
                self.assertIn("Codex CLI connection", [row["capability"] for row in codex_mode["capabilities"]])
                self.assertIn("Vibe coding agent", [row["capability"] for row in codex_mode["capabilities"]])

                from human_ai.ai_task_map import AITaskMapStore

                AITaskMapStore(self.config.resolved_data_dir).refresh(self.agent, fetch_public_sources=False)
                task_map = self._request(host, port, "GET", "/api/ai-task-map")
                self.assertEqual(task_map["status"], "ready")
                self.assertEqual(task_map["rows"], 79)
                self.assertIn("ai_task_map.csv", task_map["path"])
                downloaded_map = self._raw_request(host, port, "GET", "/api/download?path=" + task_map["path"])
                self.assertIn(b"Seedance-style video planning", downloaded_map)

                local_stack = self._request(host, port, "GET", "/api/local-ai-stack")
                self.assertIn("i7-7700HQ", local_stack["hardware"]["cpu"])
                self.assertTrue(any(row["tool"] == "LM Studio" for row in local_stack["tools"]))
                self.assertIn("csv", local_stack["files"])

                paid_plan = self._request(host, port, "GET", "/api/openrouter/paid-plan")
                self.assertIn("recommendations", paid_plan)
                self.assertTrue(any(row["area"] == "Coding agent" for row in paid_plan["recommendations"]))
                self.assertTrue(any(row["area"] == "Agent/tool calling" for row in paid_plan["recommendations"]))
                self.assertTrue(any(row.get("paid_model_type") == "GPT / Claude / Gemini flagship models" for row in paid_plan["recommendations"]))
                self.assertIn("cost_controls", paid_plan)

                public_apis_cache = self.config.resolved_data_dir / "public_apis" / "catalog.json"
                public_apis_cache.parent.mkdir(parents=True, exist_ok=True)
                public_apis_cache.write_text(
                    json.dumps(
                        {
                            "source": "https://github.com/public-apis/public-apis",
                            "license": "MIT",
                            "cached_at": "2026-07-08T00:00:00Z",
                            "categories": ["Weather"],
                            "entries": [
                                {
                                    "name": "Open-Meteo",
                                    "url": "https://open-meteo.com/",
                                    "description": "Weather forecast API",
                                    "auth": "No",
                                    "https": "Yes",
                                    "cors": "Yes",
                                    "category": "Weather",
                                }
                            ],
                        }
                    ),
                    encoding="utf-8",
                )
                public_apis = self._request(host, port, "GET", "/api/public-apis?q=weather&no_auth=1&https=1")
                self.assertEqual(public_apis["count"], 1)
                self.assertEqual(public_apis["entries"][0]["name"], "Open-Meteo")

                free_llm = self._request(host, port, "GET", "/api/free-llm-plan?task=fast%20voice%20chat&privacy=balanced")
                self.assertIn("recommendations", free_llm)
                self.assertIn("Groq", [row["name"] for row in free_llm["recommendations"][:3]])
                self.assertIn("OpenRouter blog", free_llm["source"])

                council = self._request(host, port, "GET", "/api/model-council?request=make%20speech%20with%20Microsoft%20MAI")
                self.assertEqual(council["winner"]["model"], "microsoft/mai-voice-2")
                self.assertIn("interaction_plan", council)

                deployments = self._request(host, port, "GET", "/api/deployments")
                self.assertIn("Brain Server", [row["name"] for row in deployments["deployments"]])

                agents = self._request(host, port, "GET", "/api/agents")
                self.assertIn("agents", agents)
                self.assertIn("templates", agents)
                self.assertIn("self_update", [row["template"] for row in agents["templates"]])
                self.assertGreaterEqual(len(agents["agents"]), 1)

                outputs = self._request(host, port, "GET", "/api/outputs")
                self.assertIn("result.mp4", [row["name"] for row in outputs["outputs"]])

                folders = self._request(host, port, "GET", "/api/folders")
                folder_names = [row["name"] for row in folders["folders"]]
                self.assertIn("brain", folder_names)
                self.assertIn("hands/in", folder_names)
                self.assertIn("hands/out", folder_names)
                self.assertIn("continuous", folder_names)

                apps = self._request(host, port, "GET", "/api/apps")
                app_names = [row["name"] for row in apps["apps"]]
                self.assertIn("Web/PWA", app_names)
                self.assertIn("Automation runner", app_names)
            finally:
                web.stop()

    def test_web_api_creates_safe_self_update_agent(self):
        (Path(self.temp.name) / "README.md").write_text("gima\n", encoding="utf-8")
        with patch.object(BrainServer, "status", return_value={"running": False, "pid": None, "models": None}):
            web = serve_in_thread(self.config, self.agent, self.brain)
            try:
                host, port = web.server.server_address
                created = self._request(
                    host,
                    port,
                    "POST",
                    "/api/agents/create",
                    {
                        "name": "Gima Self Update Agent",
                        "template": "self_update",
                        "goal": "Improve Gima agent builder and run tests.",
                    },
                )
                agents = self._request(host, port, "GET", "/api/agents")
            finally:
                web.stop()

        self.assertEqual(created["template"], "self_update")
        self.assertEqual(created["status"], "self_update_prepared")
        self.assertTrue(Path(created["manifest_path"]).exists())
        self.assertTrue(Path(created["working_copy"]).exists())
        self.assertTrue(Path(created["plan_path"]).exists())
        self.assertIn("Gima Self Update Agent", [row["name"] for row in agents["agents"]])

    def test_web_chat_learns_from_huggingface_url(self):
        with patch.object(BrainServer, "status", return_value={"running": False, "pid": None, "models": None}):
            web = serve_in_thread(self.config, self.agent, self.brain)
            try:
                host, port = web.server.server_address
                with patch("human_ai.huggingface_learning.WebImporter.fetch") as fetch:
                    fetch.side_effect = [
                        json.dumps(
                            {
                                "id": "owner/test-gguf",
                                "pipeline_tag": "text-generation",
                                "library_name": "llama.cpp",
                                "tags": ["gguf", "chat"],
                                "cardData": {"license": "apache-2.0"},
                                "siblings": [{"rfilename": "model-q4.gguf"}],
                            }
                        ),
                        "GGUF chat model card with eval notes.",
                    ]
                    chat = self._request(
                        host,
                        port,
                        "POST",
                        "/api/chat",
                        {"message": "learn this https://huggingface.co/owner/test-gguf and improve Gima"},
                    )
            finally:
                web.stop()

        self.assertTrue(chat["huggingface_learning"])
        self.assertEqual(chat["repo_id"], "owner/test-gguf")
        self.assertEqual(chat["status"], "review_saved")
        self.assertEqual(len(chat["files"]), 3)
        self.assertIn("What Gima can use to improve itself", chat["reply"])
        self.assertTrue(any(row["id"] == chat["record_id"] for row in self.agent.memory.list_by_status("review", 5)))

    def test_web_api_uploads_files_and_lists_them(self):
        with patch.object(BrainServer, "status", return_value={"running": False, "pid": None, "models": None}):
            web = serve_in_thread(self.config, self.agent, self.brain)
            try:
                host, port = web.server.server_address
                uploaded = self._multipart_upload(host, port, "note.txt", b"hello gima")
                self.assertEqual(uploaded["files"][0]["name"], "note.txt")
                self.assertTrue(Path(uploaded["files"][0]["path"]).exists())
                self.assertIn("/api/download?path=", uploaded["files"][0]["download_url"])
                self.assertTrue(Path(uploaded["files"][0]["path"]).is_relative_to(self.config.resolved_hands_in_dir))
                self.assertTrue(self.config.resolved_brain_csv_path.exists())
                self.assertIn("note.txt", self.config.resolved_brain_csv_path.read_text(encoding="utf-8"))
                stomach_csv = self.config.resolved_stomach_dir / "uploaded_items.csv"
                self.assertTrue(stomach_csv.exists())
                stomach_text = stomach_csv.read_text(encoding="utf-8")
                self.assertIn("note.txt", stomach_text)
                self.assertIn(uploaded["files"][0]["path"], stomach_text)
                continuous_csv = self.config.resolved_continuous_dir / "work_steps.csv"
                self.assertTrue(continuous_csv.exists())
                continuous_text = continuous_csv.read_text(encoding="utf-8")
                self.assertIn("file_upload", continuous_text)
                self.assertIn("note.txt", continuous_text)

                listed = self._request(host, port, "GET", "/api/files")
                self.assertEqual(listed["files"][0]["name"], "note.txt")
                downloaded = self._raw_request(host, port, "GET", listed["files"][0]["download_url"])
                self.assertEqual(downloaded, b"hello gima")
                forbidden = self._raw_request(host, port, "GET", "/api/download?path=/etc/hosts", expect_status=403)
                self.assertIn(b"Download is limited", forbidden)
            finally:
                web.stop()

    def test_web_api_reveals_gima_file_location(self):
        with patch.object(BrainServer, "status", return_value={"running": False, "pid": None, "models": None}):
            web = serve_in_thread(self.config, self.agent, self.brain)
            try:
                host, port = web.server.server_address
                output_file = self.config.resolved_hands_out_dir / "video" / "result.mp4"
                output_file.parent.mkdir(parents=True, exist_ok=True)
                output_file.write_bytes(b"mp4")
                with patch("human_ai.web_ui.subprocess.run") as run:
                    run.return_value = subprocess.CompletedProcess([], 0, "", "")
                    revealed = self._request(
                        host,
                        port,
                        "POST",
                        "/api/reveal",
                        {"path": str(output_file)},
                    )
                self.assertEqual(revealed["status"], "opened")
                self.assertEqual(revealed["path"], str(output_file))
                self.assertEqual(revealed["folder"], str(output_file.parent))
                run.assert_called_once()
                self.assertIn(str(output_file), run.call_args.args[0])
            finally:
                web.stop()

    def test_web_api_generates_local_song_sketch(self):
        from human_ai.services import SongSketchProject

        with patch.object(BrainServer, "status", return_value={"running": False, "pid": None, "models": None}):
            web = serve_in_thread(self.config, self.agent, self.brain)
            try:
                host, port = web.server.server_address
                project_dir = Path(self.temp.name) / "song_project"
                project_dir.mkdir()
                output_path = project_dir / "song.wav"
                output_path.write_bytes(b"wav")
                manifest_path = project_dir / "manifest.json"
                manifest_path.write_text("{}", encoding="utf-8")
                prompt_path = project_dir / "prompt.txt"
                prompt_path.write_text("prompt", encoding="utf-8")
                with patch("human_ai.web_ui.LocalSongSketcher.render") as render:
                    render.return_value = SongSketchProject(project_dir, output_path, manifest_path, prompt_path)
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
                self.assertIn("/api/download?path=", song["download_url"])
                self.assertIn("/api/download?path=", song["manifest_download_url"])
            finally:
                web.stop()

    def test_web_api_generates_external_music_api_song(self):
        from human_ai.services import ExternalMusicApiProject

        with patch.object(BrainServer, "status", return_value={"running": False, "pid": None, "models": None}):
            web = serve_in_thread(self.config, self.agent, self.brain)
            try:
                host, port = web.server.server_address
                project_dir = Path(self.temp.name) / "external_music_project"
                project_dir.mkdir()
                output_path = project_dir / "song.wav"
                output_path.write_bytes(b"wav")
                manifest_path = project_dir / "manifest.json"
                manifest_path.write_text("{}", encoding="utf-8")
                prompt_path = project_dir / "prompt.txt"
                prompt_path.write_text("prompt", encoding="utf-8")
                with patch("human_ai.web_ui.ExternalMusicApiGenerator.generate") as generate:
                    generate.return_value = ExternalMusicApiProject(project_dir, output_path, manifest_path, prompt_path)
                    song = self._request(
                        host,
                        port,
                        "POST",
                        "/api/media/music-api-generate",
                        {
                            "provider": "huggingface_musicgen",
                            "prompt": "cinematic Gima song",
                            "lyrics": "owned lyrics",
                            "duration_seconds": 8,
                            "consent": True,
                        },
                    )
                self.assertEqual(song["output"], str(output_path))
                self.assertEqual(song["provider"], "huggingface_musicgen")
                self.assertEqual(song["prompt_file"], str(prompt_path))
                self.assertIn("/api/download?path=", song["download_url"])
            finally:
                web.stop()

    def test_web_api_video_and_code_tools(self):
        from human_ai.services import CodeExecutionResult, MusicVideoProject, OpenSourceVideoApiProject
        from human_ai.vibe_code import VibeCodeExecution, VibeCodeFile, VibeCodePlan
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
                        {"audio_path": str(project_dir / "song.mp3"), "prompt": "waveform", "style": "waveform", "consent": True},
                    )
                self.assertEqual(video["output"], str(output_path))
                self.assertIn("/api/download?path=", video["download_url"])

                with patch("human_ai.web_ui.LocalImageMusicVideoRenderer.render") as render_images:
                    render_images.return_value = type(
                        "ImageVideoProject",
                        (),
                        {
                            "output_path": output_path,
                            "manifest_path": manifest_path,
                        },
                    )()
                    image_video = self._request(
                        host,
                        port,
                        "POST",
                        "/api/media/image-music-video-local",
                        {
                            "audio_path": str(project_dir / "song.mp3"),
                            "image_paths": [str(project_dir / "image.jpg")],
                            "prompt": "image mp3 video",
                            "aspect": "16:9",
                            "consent": True,
                        },
                    )
                self.assertEqual(image_video["output"], str(output_path))

                storyboard_path = project_dir / "advanced_storyboard.md"
                analysis_path = project_dir / "audio_analysis.json"
                prompt_pack_path = project_dir / "scene_prompt_pack.md"
                storyboard_path.write_text("# storyboard", encoding="utf-8")
                analysis_path.write_text("{}", encoding="utf-8")
                prompt_pack_path.write_text("# prompts", encoding="utf-8")
                with patch("human_ai.web_ui.AdvancedVideoSongRenderer.render") as advanced_render:
                    advanced_render.return_value = type(
                        "AdvancedProject",
                        (),
                        {
                            "output_path": output_path,
                            "manifest_path": manifest_path,
                            "storyboard_path": storyboard_path,
                            "audio_analysis_path": analysis_path,
                            "prompt_pack_path": prompt_pack_path,
                        },
                    )()
                    advanced_video = self._request(
                        host,
                        port,
                        "POST",
                        "/api/media/advanced-video-song",
                        {
                            "audio_path": str(project_dir / "song.mp3"),
                            "image_paths": [str(project_dir / "image.jpg")],
                            "prompt": "cinematic emotional movie",
                            "aspect": "16:9",
                            "consent": True,
                        },
                    )
                self.assertEqual(advanced_video["output"], str(output_path))
                self.assertEqual(advanced_video["storyboard"], str(storyboard_path))
                self.assertEqual(advanced_video["audio_analysis"], str(analysis_path))

                workflow_path = project_dir / "workflow.json"
                workflow_path.write_text("{}", encoding="utf-8")
                open_manifest = project_dir / "open_manifest.json"
                open_manifest.write_text("{}", encoding="utf-8")
                open_workflow = project_dir / "workflow_api.json"
                open_workflow.write_text("{}", encoding="utf-8")
                open_prompt = project_dir / "open_prompt.txt"
                open_prompt.write_text("prompt", encoding="utf-8")
                with patch("human_ai.web_ui.OpenSourceVideoApiRenderer.render") as open_render:
                    open_render.return_value = OpenSourceVideoApiProject(
                        project_dir,
                        output_path,
                        open_manifest,
                        open_workflow,
                        open_prompt,
                    )
                    open_video = self._request(
                        host,
                        port,
                        "POST",
                        "/api/media/open-video-api",
                        {
                            "workflow_path": str(workflow_path),
                            "prompt": "open source video",
                            "consent": True,
                        },
                    )
                self.assertEqual(open_video["output"], str(output_path))
                self.assertEqual(open_video["workflow"], str(open_workflow))

                hf_manifest = project_dir / "hf_manifest.json"
                hf_prompt = project_dir / "hf_prompt.txt"
                hf_manifest.write_text("{}", encoding="utf-8")
                hf_prompt.write_text("prompt", encoding="utf-8")
                with patch("human_ai.web_ui.HuggingFaceVideoGenerator.generate") as hf_video:
                    hf_video.return_value = {
                        "status": "generated",
                        "provider": "huggingface",
                        "inference_provider": "replicate",
                        "model": "Wan-AI/Wan2.2-TI2V-5B",
                        "output_path": str(output_path),
                        "manifest_path": str(hf_manifest),
                        "prompt_path": str(hf_prompt),
                    }
                    hf_response = self._request(
                        host,
                        port,
                        "POST",
                        "/api/media/huggingface-video-generate",
                        {
                            "prompt": "A young man walking on the street",
                            "model": "Wan-AI/Wan2.2-TI2V-5B",
                            "provider": "replicate",
                            "consent": True,
                        },
                    )
                self.assertEqual(hf_response["provider"], "huggingface")
                self.assertEqual(hf_response["inference_provider"], "replicate")
                self.assertEqual(hf_response["model"], "Wan-AI/Wan2.2-TI2V-5B")
                self.assertEqual(hf_response["output"], str(output_path))

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
                            "audio_path": str(project_dir / "song.mp3"),
                            "prompt": "freebeat style music video",
                            "mode": "story",
                            "style": "cinematic",
                            "aspect": "16:9",
                            "lyrics": "",
                        },
                    )
                self.assertEqual(director_response["storyboard"], str(director_storyboard))
                self.assertIn("/api/download?path=", director_response["download_url"])

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
                fake_code_path = self.config.resolved_workspace / "human_ai" / "web_ui.py"
                fake_code_path.parent.mkdir(parents=True, exist_ok=True)
                fake_code_path.write_text("print('hello gima')\n", encoding="utf-8")
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
                code_lines_csv = self.config.resolved_continuous_dir / "code_lines.csv"
                self.assertTrue(code_lines_csv.exists())
                self.assertIn("human_ai/web_ui.py", code_lines_csv.read_text(encoding="utf-8"))

                with patch("human_ai.web_ui.VibeCodingAgent.implement") as implement:
                    (project_dir / "implemented.patch").write_text(
                        "--- a/human_ai/web_ui.py\n+++ b/human_ai/web_ui.py\n-old\n+new\n",
                        encoding="utf-8",
                    )
                    (project_dir / "coding.log").write_text("Codex changed the renderer.\n", encoding="utf-8")
                    (project_dir / "tests.log").write_text("Ran 86 tests\nOK\n", encoding="utf-8")
                    implement.return_value = VibeCodeExecution(
                        plan.return_value,
                        "implemented_pending_review",
                        ["human_ai/web_ui.py"],
                        project_dir / "implemented.patch",
                        project_dir / "coding.log",
                        project_dir / "tests.log",
                        True,
                    )
                    self_code = self._request(
                        host,
                        port,
                        "POST",
                        "/api/code/self-code",
                        {"feature": "add split coding", "confirm": True},
                    )
                self.assertEqual(self_code["status"], "implemented_pending_review")
                self.assertTrue(self_code["tests_passed"])
                self.assertEqual(self_code["changed_files"], ["human_ai/web_ui.py"])
                self.assertIn("+new", self_code["patch_preview"])
                self.assertIn("Codex changed", self_code["coding_output"])
                self.assertIn("Ran 86 tests", self_code["test_output"])
                self.assertEqual(self_code["diff_stats"], {"files": 1, "additions": 1, "deletions": 1})

                with patch("human_ai.web_ui.SandboxedCodeRunner.run") as run_code:
                    run_code.return_value = CodeExecutionResult(
                        "python",
                        project_dir / "main.py",
                        project_dir / "output.txt",
                        project_dir / "run_manifest.json",
                        "323\n",
                        "",
                        0,
                        0.042,
                        False,
                    )
                    code_run = self._request(
                        host,
                        port,
                        "POST",
                        "/api/code/run",
                        {"language": "python", "code": "print(17 * 19)", "confirm": True},
                    )
                self.assertEqual(code_run["kind"], "code_execution")
                self.assertEqual(code_run["stdout"], "323\n")
                self.assertEqual(code_run["exit_code"], 0)
                self.assertEqual(code_run["source_file"], str(project_dir / "main.py"))
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

    def _raw_request(self, host, port, method, path, expect_status=200):
        connection = http.client.HTTPConnection(host, port, timeout=10)
        connection.request(method, path)
        response = connection.getresponse()
        data = response.read()
        connection.close()
        self.assertEqual(response.status, expect_status, data)
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
