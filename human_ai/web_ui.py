from __future__ import annotations

import json
import threading
import time
import urllib.parse
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

from .agent import Agent
from .brain import BrainServer
from .config import Config


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Gima Chat</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #050608;
      --panel: #0d1117;
      --panel-2: #111827;
      --line: #242b35;
      --text: #f5f7fb;
      --muted: #9aa4b2;
      --accent: #7c5cff;
      --accent-2: #00d4ff;
      --user: #1f2937;
      --assistant: #0f172a;
      --danger: #ff6b6b;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at top left, rgba(124, 92, 255, 0.16), transparent 34rem),
        radial-gradient(circle at bottom right, rgba(0, 212, 255, 0.12), transparent 30rem),
        var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    .app {
      display: grid;
      grid-template-columns: 280px 1fr;
      min-height: 100vh;
    }
    aside {
      border-right: 1px solid var(--line);
      background: rgba(13, 17, 23, 0.88);
      padding: 20px;
      backdrop-filter: blur(18px);
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 22px;
    }
    .logo {
      display: grid;
      place-items: center;
      width: 42px;
      height: 42px;
      border-radius: 14px;
      background: linear-gradient(135deg, var(--accent), var(--accent-2));
      color: white;
      font-weight: 800;
      box-shadow: 0 0 24px rgba(124, 92, 255, 0.28);
    }
    h1, h2, p { margin: 0; }
    h1 { font-size: 20px; letter-spacing: 0.2px; }
    .subtitle { color: var(--muted); font-size: 13px; margin-top: 3px; }
    .card {
      border: 1px solid var(--line);
      background: rgba(17, 24, 39, 0.66);
      border-radius: 18px;
      padding: 14px;
      margin: 14px 0;
    }
    .status-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      font-size: 13px;
      color: var(--muted);
      margin: 8px 0;
    }
    .pill {
      border: 1px solid rgba(0, 212, 255, 0.35);
      color: #b9f3ff;
      background: rgba(0, 212, 255, 0.08);
      border-radius: 999px;
      padding: 4px 9px;
      font-size: 12px;
      white-space: nowrap;
    }
    .quick button, .search button {
      width: 100%;
      margin-top: 8px;
      border: 1px solid var(--line);
      background: #0b1220;
      color: var(--text);
      border-radius: 12px;
      padding: 10px 12px;
      text-align: left;
      cursor: pointer;
    }
    .quick button:hover, .search button:hover { border-color: var(--accent); }
    .search input {
      width: 100%;
      background: #050608;
      border: 1px solid var(--line);
      border-radius: 12px;
      color: var(--text);
      padding: 10px 12px;
      outline: none;
    }
    .results {
      margin-top: 10px;
      max-height: 220px;
      overflow: auto;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.4;
    }
    main {
      display: grid;
      grid-template-rows: auto 1fr auto;
      min-width: 0;
    }
    header {
      border-bottom: 1px solid var(--line);
      padding: 18px 24px;
      background: rgba(5, 6, 8, 0.72);
      backdrop-filter: blur(16px);
    }
    .chat {
      overflow: auto;
      padding: 28px max(24px, 10vw);
    }
    .message {
      display: grid;
      grid-template-columns: 42px minmax(0, 1fr);
      gap: 14px;
      margin: 0 0 20px;
    }
    .avatar {
      display: grid;
      place-items: center;
      width: 42px;
      height: 42px;
      border-radius: 14px;
      background: var(--panel-2);
      color: var(--muted);
      font-weight: 800;
      border: 1px solid var(--line);
    }
    .bubble {
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 15px 16px;
      line-height: 1.55;
      white-space: pre-wrap;
      background: var(--assistant);
      box-shadow: 0 12px 26px rgba(0, 0, 0, 0.18);
    }
    .user .bubble { background: var(--user); }
    .assistant .avatar {
      background: linear-gradient(135deg, rgba(124, 92, 255, 0.26), rgba(0, 212, 255, 0.14));
      color: white;
    }
    .composer {
      padding: 18px max(24px, 10vw) 24px;
      border-top: 1px solid var(--line);
      background: rgba(5, 6, 8, 0.78);
    }
    form {
      display: flex;
      gap: 10px;
      border: 1px solid var(--line);
      border-radius: 20px;
      background: #080b11;
      padding: 10px;
    }
    textarea {
      flex: 1;
      min-height: 48px;
      max-height: 180px;
      resize: vertical;
      border: 0;
      outline: 0;
      color: var(--text);
      background: transparent;
      font: inherit;
      padding: 10px;
    }
    .send {
      align-self: end;
      border: 0;
      border-radius: 14px;
      color: white;
      background: linear-gradient(135deg, var(--accent), var(--accent-2));
      padding: 12px 18px;
      font-weight: 700;
      cursor: pointer;
    }
    .send:disabled { opacity: 0.55; cursor: wait; }
    .hint {
      color: var(--muted);
      font-size: 12px;
      margin-top: 10px;
    }
    @media (max-width: 840px) {
      .app { grid-template-columns: 1fr; }
      aside { display: none; }
      .chat, .composer { padding-left: 16px; padding-right: 16px; }
    }
  </style>
</head>
<body>
  <div class="app">
    <aside>
      <div class="brand">
        <div class="logo">G</div>
        <div>
          <h1>Gima</h1>
          <p class="subtitle">local black chat interface</p>
        </div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">System</h2>
        <div class="status-row"><span>Brain</span><span class="pill" id="brain">checking</span></div>
        <div class="status-row"><span>Model</span><span id="model">...</span></div>
        <div class="status-row"><span>Memory</span><span id="memory">local</span></div>
      </div>
      <div class="card quick">
        <h2 style="font-size: 14px;">Quick Prompts</h2>
        <button data-prompt="What can you do right now on this PC?">PC capabilities</button>
        <button data-prompt="Search your memory for Gima latest upgrades.">Memory summary</button>
        <button data-prompt="Give me the next 5 best improvements for Gima.">Improve Gima</button>
      </div>
      <div class="card search">
        <h2 style="font-size: 14px; margin-bottom: 10px;">Memory Search</h2>
        <input id="search" placeholder="Search local memory">
        <button id="searchBtn">Search</button>
        <div class="results" id="results"></div>
      </div>
    </aside>
    <main>
      <header>
        <h1>Chat With Gima</h1>
        <p class="subtitle">Local web UI. Conversations still save to Gima memory.</p>
      </header>
      <section class="chat" id="chat">
        <div class="message assistant">
          <div class="avatar">G</div>
          <div class="bubble">Hi. I am Gima. This is the local dark web interface. Ask me anything, or use memory search on the left.</div>
        </div>
      </section>
      <div class="composer">
        <form id="form">
          <textarea id="message" placeholder="Message Gima..." autofocus></textarea>
          <button class="send" id="send" type="submit">Send</button>
        </form>
        <div class="hint">Enter sends. Shift+Enter makes a new line. Server is local by default.</div>
      </div>
    </main>
  </div>
  <script>
    const chat = document.getElementById('chat');
    const form = document.getElementById('form');
    const message = document.getElementById('message');
    const send = document.getElementById('send');

    function addMessage(role, text) {
      const row = document.createElement('div');
      row.className = `message ${role}`;
      row.innerHTML = `<div class="avatar">${role === 'user' ? 'You' : 'G'}</div><div class="bubble"></div>`;
      row.querySelector('.bubble').textContent = text;
      chat.appendChild(row);
      chat.scrollTop = chat.scrollHeight;
    }

    async function refreshStatus() {
      const res = await fetch('/api/status');
      const data = await res.json();
      document.getElementById('brain').textContent = data.brain.running ? 'running' : 'stopped';
      document.getElementById('model').textContent = data.model || 'not configured';
      document.getElementById('memory').textContent = data.memory_rows + ' rows';
    }

    async function sendMessage(text) {
      addMessage('user', text);
      addMessage('assistant', 'Thinking...');
      const pending = chat.lastElementChild.querySelector('.bubble');
      send.disabled = true;
      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({message: text})
        });
        const data = await res.json();
        pending.textContent = data.reply || data.error || 'No reply.';
      } catch (error) {
        pending.textContent = 'Error: ' + error;
      } finally {
        send.disabled = false;
        message.focus();
        refreshStatus();
      }
    }

    form.addEventListener('submit', (event) => {
      event.preventDefault();
      const text = message.value.trim();
      if (!text) return;
      message.value = '';
      sendMessage(text);
    });
    message.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        form.requestSubmit();
      }
    });
    document.querySelectorAll('[data-prompt]').forEach(button => {
      button.addEventListener('click', () => sendMessage(button.dataset.prompt));
    });
    document.getElementById('searchBtn').addEventListener('click', async () => {
      const q = document.getElementById('search').value.trim();
      if (!q) return;
      const res = await fetch('/api/memory/search?q=' + encodeURIComponent(q));
      const data = await res.json();
      document.getElementById('results').innerHTML = data.results.length
        ? data.results.map(row => `<p><b>${row.title}</b><br>${row.content}</p>`).join('')
        : '<p>No matching memory.</p>';
    });
    refreshStatus();
  </script>
</body>
</html>
"""


@dataclass(frozen=True)
class GimaWebServer:
    url: str
    server: ThreadingHTTPServer

    def serve_forever(self) -> None:
        self.server.serve_forever()

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()


def create_web_server(config: Config, agent: Agent, brain: BrainServer, host: str, port: int) -> GimaWebServer:
    handler = _handler_factory(config, agent, brain)
    server = ThreadingHTTPServer((host, port), handler)
    actual_host, actual_port = server.server_address
    return GimaWebServer(f"http://{actual_host}:{actual_port}", server)


def run_web_ui(config: Config, agent: Agent, brain: BrainServer, host: str, port: int, open_browser: bool = False) -> str:
    web = create_web_server(config, agent, brain, host, port)
    if open_browser:
        _open_browser(web.url)
    print(f"Gima web UI running at {web.url}")
    print("Press Ctrl+C to stop.")
    try:
        web.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        web.stop()
    return web.url


def _handler_factory(config: Config, agent: Agent, brain: BrainServer) -> type[BaseHTTPRequestHandler]:
    class GimaWebHandler(BaseHTTPRequestHandler):
        server_version = "GimaWeb/1.0"

        def do_GET(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/":
                self._send_text(INDEX_HTML, "text/html; charset=utf-8")
            elif parsed.path == "/api/status":
                self._send_json(_status_payload(config, agent, brain))
            elif parsed.path == "/api/memory/search":
                params = urllib.parse.parse_qs(parsed.query)
                query = params.get("q", [""])[0]
                limit = _safe_int(params.get("limit", ["6"])[0], 6)
                results = [
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "category": row["category"],
                        "content": row["content"][:260],
                    }
                    for row in agent.search(query, limit=limit)
                ]
                self._send_json({"results": results})
            else:
                self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != "/api/chat":
                self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
                return
            try:
                payload = self._read_json()
                message = str(payload.get("message", "")).strip()
                if not message:
                    self._send_json({"error": "message is required"}, HTTPStatus.BAD_REQUEST)
                    return
                started = time.time()
                reply = agent.chat(message)
                self._send_json(
                    {
                        "reply": reply,
                        "elapsed_seconds": round(time.time() - started, 3),
                        "session_id": agent.session_id,
                    }
                )
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR)

        def log_message(self, fmt: str, *args: Any) -> None:
            print(f"[web] {self.address_string()} {fmt % args}")

        def _read_json(self) -> dict[str, Any]:
            length = _safe_int(self.headers.get("Content-Length", "0"), 0)
            raw = self.rfile.read(max(0, min(length, 2_000_000)))
            if not raw:
                return {}
            return json.loads(raw.decode("utf-8"))

        def _send_text(self, body: str, content_type: str, status: HTTPStatus = HTTPStatus.OK) -> None:
            encoded = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def _send_json(self, body: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
            encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    return GimaWebHandler


def _status_payload(config: Config, agent: Agent, brain: BrainServer) -> dict[str, Any]:
    brain_status = brain.status()
    return {
        "name": config.name,
        "workspace": str(config.resolved_workspace),
        "memory": str(config.resolved_data_dir),
        "memory_rows": _count_csv_rows(config.resolved_data_dir / "csv" / "knowledge.csv"),
        "conversation_rows": _count_csv_rows(config.resolved_data_dir / "csv" / "conversations.csv"),
        "brain": brain_status,
        "model": brain_status.get("models") or config.model.model,
        "session_id": agent.session_id,
    }


def _count_csv_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8", errors="replace") as handle:
        return max(0, sum(1 for _ in handle) - 1)


def _safe_int(value: str, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _open_browser(url: str) -> None:
    try:
        import subprocess

        subprocess.Popen(["open", url])
    except Exception:
        pass


def serve_in_thread(
    config: Config,
    agent: Agent,
    brain: BrainServer,
    host: str = "127.0.0.1",
    port: int = 0,
) -> GimaWebServer:
    web = create_web_server(config, agent, brain, host, port)
    thread = threading.Thread(target=web.serve_forever, daemon=True)
    thread.start()
    return web
