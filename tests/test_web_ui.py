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


if __name__ == "__main__":
    unittest.main()
