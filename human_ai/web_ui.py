from __future__ import annotations

import json
import mimetypes
import re
import threading
import time
import urllib.parse
import uuid
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

from .agent import Agent
from .brain import BrainServer
from .config import Config
from .memory import Record
from .services import LocalImageMusicVideoRenderer, LocalMusicVideoDirector, LocalMusicVideoRenderer, LocalSongSketcher
from .vibe_code import VibeCodingAgent


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
      grid-template-columns: 280px minmax(0, 1fr) 360px;
      min-height: 100vh;
    }
    aside, .workspace {
      background: rgba(13, 17, 23, 0.88);
      padding: 20px;
      backdrop-filter: blur(18px);
    }
    aside { border-right: 1px solid var(--line); }
    .workspace {
      border-left: 1px solid var(--line);
      overflow: auto;
      max-height: 100vh;
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
    .search input, .tool-input, .tool-select {
      width: 100%;
      background: #050608;
      border: 1px solid var(--line);
      border-radius: 12px;
      color: var(--text);
      padding: 10px 12px;
      outline: none;
    }
    .tool-input, .tool-select { margin-top: 8px; }
    .tool-textarea {
      width: 100%;
      min-height: 78px;
      margin-top: 8px;
      background: #050608;
      border: 1px solid var(--line);
      border-radius: 12px;
      color: var(--text);
      padding: 10px 12px;
      outline: none;
      resize: vertical;
      font: inherit;
    }
    .tool-button {
      width: 100%;
      margin-top: 8px;
      border: 1px solid rgba(124, 92, 255, 0.45);
      background: linear-gradient(135deg, rgba(124, 92, 255, 0.28), rgba(0, 212, 255, 0.16));
      color: var(--text);
      border-radius: 12px;
      padding: 10px 12px;
      text-align: center;
      cursor: pointer;
      font-weight: 700;
    }
    .tool-button:disabled { opacity: 0.55; cursor: wait; }
    .results {
      margin-top: 10px;
      max-height: 220px;
      overflow: auto;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.4;
    }
    .tool-output {
      margin-top: 10px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }
    .file-list {
      margin-top: 10px;
      display: grid;
      gap: 8px;
      color: var(--muted);
      font-size: 12px;
    }
    .file-chip {
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 8px;
      background: rgba(5, 6, 8, 0.58);
      overflow-wrap: anywhere;
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
      aside, .workspace { display: none; }
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
    <section class="workspace">
      <div class="brand">
        <div class="logo">W</div>
        <div>
          <h1>Workspace</h1>
          <p class="subtitle">files, media, coding split</p>
        </div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">Attach Files</h2>
        <input class="tool-input" id="fileInput" type="file" multiple>
        <button class="tool-button" id="uploadBtn">Upload to Gima</button>
        <div class="file-list" id="fileList"></div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">Generate Song Sketch</h2>
        <textarea class="tool-textarea" id="songPrompt" placeholder="Example: happy cinematic intro for Gima"></textarea>
        <input class="tool-input" id="songDuration" type="number" min="4" max="60" value="12">
        <button class="tool-button" id="songBtn">Generate Local WAV</button>
        <div class="tool-output" id="songOutput"></div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">Generate Video From Audio</h2>
        <input class="tool-input" id="videoAudioPath" placeholder="Audio path or uploaded file path">
        <textarea class="tool-textarea" id="videoPrompt" placeholder="Describe the video mood"></textarea>
        <select class="tool-select" id="videoStyle">
          <option value="waveform">Waveform</option>
          <option value="spectrum">Spectrum</option>
        </select>
        <button class="tool-button" id="videoBtn">Render Local MP4</button>
        <div class="tool-output" id="videoOutput"></div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">Images + MP3 Video</h2>
        <input class="tool-input" id="imageVideoAudioPath" placeholder="MP3/audio path">
        <textarea class="tool-textarea" id="imageVideoPaths" placeholder="Image paths, one per line or comma-separated"></textarea>
        <textarea class="tool-textarea" id="imageVideoPrompt" placeholder="Describe this image music video"></textarea>
        <input class="tool-input" id="imageVideoDuration" type="number" min="4" max="300" value="45">
        <select class="tool-select" id="imageVideoAspect">
          <option value="16:9">16:9</option>
          <option value="9:16">9:16</option>
          <option value="1:1">1:1</option>
        </select>
        <button class="tool-button" id="imageVideoBtn">Render Images + MP3 MP4</button>
        <div class="tool-output" id="imageVideoOutput"></div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">Freebeat-Style Director</h2>
        <input class="tool-input" id="directorAudioPath" placeholder="Audio path or uploaded file path">
        <textarea class="tool-textarea" id="directorPrompt" placeholder="Music video idea, e.g. neon city dance story"></textarea>
        <input class="tool-input" id="directorStyle" value="cinematic" placeholder="Style">
        <select class="tool-select" id="directorMode">
          <option value="story">Story</option>
          <option value="stage">Stage</option>
          <option value="lyrics">Lyrics</option>
          <option value="visualizer">Visualizer</option>
        </select>
        <select class="tool-select" id="directorAspect">
          <option value="16:9">16:9</option>
          <option value="9:16">9:16</option>
          <option value="1:1">1:1</option>
        </select>
        <textarea class="tool-textarea" id="directorLyrics" placeholder="Optional lyrics, one line at a time"></textarea>
        <button class="tool-button" id="directorBtn">Create Director Plan</button>
        <div class="tool-output" id="directorOutput"></div>
      </div>
      <div class="card">
        <h2 style="font-size: 14px;">Coding Split</h2>
        <textarea class="tool-textarea" id="codeFeature" placeholder="Feature to plan offline, e.g. add file preview"></textarea>
        <button class="tool-button" id="codeBtn">Create Vibe Code Plan</button>
        <div class="tool-output" id="codeOutput"></div>
      </div>
    </section>
  </div>
  <script>
    const chat = document.getElementById('chat');
    const form = document.getElementById('form');
    const message = document.getElementById('message');
    const send = document.getElementById('send');
    const fileList = document.getElementById('fileList');

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

    async function apiPost(path, payload) {
      const res = await fetch(path, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      });
      return await res.json();
    }

    function setOutput(id, data) {
      document.getElementById(id).textContent = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
    }

    async function refreshFiles() {
      const res = await fetch('/api/files');
      const data = await res.json();
      fileList.innerHTML = data.files.length
        ? data.files.map(file => `<div class="file-chip"><b>${file.name}</b><br>${file.path}<br>${file.size_bytes} bytes</div>`).join('')
        : '<div class="file-chip">No uploaded files yet.</div>';
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
    document.getElementById('uploadBtn').addEventListener('click', async () => {
      const input = document.getElementById('fileInput');
      if (!input.files.length) return;
      const formData = new FormData();
      Array.from(input.files).forEach(file => formData.append('files', file));
      document.getElementById('uploadBtn').disabled = true;
      try {
        const res = await fetch('/api/files/upload', { method: 'POST', body: formData });
        const data = await res.json();
        await refreshFiles();
        addMessage('assistant', `Attached ${data.files.length} file(s) to Gima memory.`);
      } finally {
        document.getElementById('uploadBtn').disabled = false;
      }
    });
    document.getElementById('songBtn').addEventListener('click', async () => {
      const prompt = document.getElementById('songPrompt').value.trim();
      const duration = Number(document.getElementById('songDuration').value || 12);
      if (!prompt) return;
      document.getElementById('songBtn').disabled = true;
      try {
        setOutput('songOutput', await apiPost('/api/media/song-local', { prompt, duration_seconds: duration }));
      } finally {
        document.getElementById('songBtn').disabled = false;
      }
    });
    document.getElementById('videoBtn').addEventListener('click', async () => {
      const audio_path = document.getElementById('videoAudioPath').value.trim();
      const prompt = document.getElementById('videoPrompt').value.trim();
      const style = document.getElementById('videoStyle').value;
      if (!audio_path || !prompt) return;
      document.getElementById('videoBtn').disabled = true;
      try {
        setOutput('videoOutput', await apiPost('/api/media/music-video-local', { audio_path, prompt, style, consent: true }));
      } finally {
        document.getElementById('videoBtn').disabled = false;
      }
    });
    document.getElementById('imageVideoBtn').addEventListener('click', async () => {
      const audio_path = document.getElementById('imageVideoAudioPath').value.trim();
      const rawImages = document.getElementById('imageVideoPaths').value;
      const image_paths = rawImages.split(/[\n,]+/).map(value => value.trim()).filter(Boolean);
      const prompt = document.getElementById('imageVideoPrompt').value.trim();
      const aspect = document.getElementById('imageVideoAspect').value;
      const max_duration_seconds = Number(document.getElementById('imageVideoDuration').value || 45);
      if (!audio_path || !image_paths.length || !prompt) return;
      document.getElementById('imageVideoBtn').disabled = true;
      try {
        setOutput('imageVideoOutput', await apiPost('/api/media/image-music-video-local', { audio_path, image_paths, prompt, aspect, max_duration_seconds, consent: true }));
      } finally {
        document.getElementById('imageVideoBtn').disabled = false;
      }
    });
    document.getElementById('directorBtn').addEventListener('click', async () => {
      const audio_path = document.getElementById('directorAudioPath').value.trim();
      const prompt = document.getElementById('directorPrompt').value.trim();
      const mode = document.getElementById('directorMode').value;
      const style = document.getElementById('directorStyle').value.trim() || 'cinematic';
      const aspect = document.getElementById('directorAspect').value;
      const lyrics = document.getElementById('directorLyrics').value;
      if (!audio_path || !prompt) return;
      document.getElementById('directorBtn').disabled = true;
      try {
        setOutput('directorOutput', await apiPost('/api/media/music-video-director', { audio_path, prompt, mode, style, aspect, lyrics }));
      } finally {
        document.getElementById('directorBtn').disabled = false;
      }
    });
    document.getElementById('codeBtn').addEventListener('click', async () => {
      const feature = document.getElementById('codeFeature').value.trim();
      if (!feature) return;
      document.getElementById('codeBtn').disabled = true;
      try {
        setOutput('codeOutput', await apiPost('/api/code/vibe-plan', { feature, max_files: 8 }));
      } finally {
        document.getElementById('codeBtn').disabled = false;
      }
    });
    refreshStatus();
    refreshFiles();
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
            elif parsed.path == "/api/files":
                self._send_json({"files": _list_uploaded_files(config)})
            else:
                self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/api/files/upload":
                self._handle_file_upload()
                return
            if parsed.path == "/api/media/song-local":
                self._handle_song_local()
                return
            if parsed.path == "/api/media/music-video-local":
                self._handle_music_video_local()
                return
            if parsed.path == "/api/media/image-music-video-local":
                self._handle_image_music_video_local()
                return
            if parsed.path == "/api/media/music-video-director":
                self._handle_music_video_director()
                return
            if parsed.path == "/api/code/vibe-plan":
                self._handle_vibe_plan()
                return
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

        def _handle_file_upload(self) -> None:
            try:
                files = self._read_multipart_files()
                saved = []
                upload_dir = _uploads_dir(config)
                upload_dir.mkdir(parents=True, exist_ok=True)
                for file in files:
                    name = _safe_filename(file["name"])
                    target = _unique_path(upload_dir / name)
                    target.write_bytes(file["content"])
                    record_id = agent.memory.add(
                        Record(
                            category="files",
                            subcategory="web_upload",
                            kind="uploaded_file",
                            title=name,
                            content=f"Uploaded through Gima web UI: {target}",
                            source=str(target),
                            media_path=str(target),
                            status="active",
                        )
                    )
                    saved.append(_file_payload(target, record_id))
                self._send_json({"files": saved})
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _handle_song_local(self) -> None:
            try:
                payload = self._read_json()
                project = LocalSongSketcher(config.resolved_data_dir / "media" / "song_sketch").render(
                    str(payload.get("prompt", "")),
                    duration_seconds=_safe_int(str(payload.get("duration_seconds", "12")), 12),
                )
                record_id = agent.memory.add(
                    Record(
                        category="audio",
                        subcategory="local_song_sketch",
                        kind="generated_media",
                        title="Local song sketch",
                        content=project.manifest_path.read_text(encoding="utf-8"),
                        source=str(project.manifest_path),
                        media_path=str(project.output_path),
                        status="review",
                    )
                )
                self._send_json(_project_payload(project.output_path, project.manifest_path, record_id))
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _handle_music_video_local(self) -> None:
            try:
                payload = self._read_json()
                project = LocalMusicVideoRenderer(config.resolved_data_dir / "media" / "music_video").render(
                    Path(str(payload.get("audio_path", ""))),
                    str(payload.get("prompt", "")),
                    style=str(payload.get("style", "waveform")),
                    consent=bool(payload.get("consent", False)),
                )
                record_id = agent.memory.add(
                    Record(
                        category="video",
                        subcategory="local_music_video",
                        kind="generated_media",
                        title=f"Local music video: {Path(str(payload.get('audio_path', 'audio'))).name}",
                        content=project.manifest_path.read_text(encoding="utf-8"),
                        source=str(project.manifest_path),
                        media_path=str(project.output_path),
                        status="review",
                    )
                )
                self._send_json(_project_payload(project.output_path, project.manifest_path, record_id))
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _handle_image_music_video_local(self) -> None:
            try:
                payload = self._read_json()
                project = LocalImageMusicVideoRenderer(config.resolved_data_dir / "media" / "image_music_video").render(
                    Path(str(payload.get("audio_path", ""))),
                    [Path(str(path)) for path in payload.get("image_paths", [])],
                    str(payload.get("prompt", "")),
                    aspect=str(payload.get("aspect", "16:9")),
                    max_duration_seconds=_safe_int(str(payload.get("max_duration_seconds", "45")), 45),
                    consent=bool(payload.get("consent", False)),
                )
                record_id = agent.memory.add(
                    Record(
                        category="video",
                        subcategory="image_music_video",
                        kind="generated_media",
                        title=f"Image music video: {Path(str(payload.get('audio_path', 'audio'))).name}",
                        content=project.manifest_path.read_text(encoding="utf-8"),
                        source=str(project.manifest_path),
                        media_path=str(project.output_path),
                        status="review",
                    )
                )
                self._send_json(_project_payload(project.output_path, project.manifest_path, record_id))
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _handle_music_video_director(self) -> None:
            try:
                payload = self._read_json()
                project = LocalMusicVideoDirector(config.resolved_data_dir / "media" / "music_video_director").plan(
                    Path(str(payload.get("audio_path", ""))),
                    str(payload.get("prompt", "")),
                    mode=str(payload.get("mode", "story")),
                    style=str(payload.get("style", "cinematic")),
                    aspect=str(payload.get("aspect", "16:9")),
                    lyrics=str(payload.get("lyrics", "")),
                )
                record_id = agent.memory.add(
                    Record(
                        category="video",
                        subcategory="music_video_director",
                        kind="generation_plan",
                        title=f"Music video director: {Path(str(payload.get('audio_path', 'audio'))).name}",
                        content=project.manifest_path.read_text(encoding="utf-8"),
                        source=str(project.manifest_path),
                        status="review",
                    )
                )
                self._send_json(
                    {
                        "storyboard": str(project.storyboard_path),
                        "manifest": str(project.manifest_path),
                        "record_id": record_id,
                    }
                )
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def _handle_vibe_plan(self) -> None:
            try:
                payload = self._read_json()
                plan = VibeCodingAgent(config.resolved_workspace, config.resolved_data_dir, agent.memory).plan(
                    str(payload.get("feature", "")),
                    max_files=_safe_int(str(payload.get("max_files", "8")), 8),
                )
                self._send_json(
                    {
                        "update_id": plan.update_request.update_id,
                        "working_copy": str(plan.update_request.working_copy),
                        "plan": str(plan.plan_path),
                        "patch_skeleton": str(plan.patch_skeleton_path),
                        "snapshot": str(plan.snapshot_path),
                        "record_id": plan.record_id,
                        "candidate_files": [file.__dict__ for file in plan.candidate_files],
                    }
                )
            except Exception as error:
                self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

        def log_message(self, fmt: str, *args: Any) -> None:
            print(f"[web] {self.address_string()} {fmt % args}")

        def _read_json(self) -> dict[str, Any]:
            length = _safe_int(self.headers.get("Content-Length", "0"), 0)
            raw = self.rfile.read(max(0, min(length, 2_000_000)))
            if not raw:
                return {}
            return json.loads(raw.decode("utf-8"))

        def _read_multipart_files(self) -> list[dict[str, Any]]:
            content_type = self.headers.get("Content-Type", "")
            match = re.search(r"boundary=([^;]+)", content_type)
            if not match:
                raise ValueError("multipart boundary is missing")
            boundary = match.group(1).strip().strip('"').encode("utf-8")
            length = _safe_int(self.headers.get("Content-Length", "0"), 0)
            raw = self.rfile.read(max(0, min(length, 50_000_000)))
            files: list[dict[str, Any]] = []
            for part in raw.split(b"--" + boundary):
                if b"filename=" not in part:
                    continue
                header, _, content = part.partition(b"\r\n\r\n")
                filename_match = re.search(rb'filename="([^"]*)"', header)
                if not filename_match:
                    continue
                filename = filename_match.group(1).decode("utf-8", errors="replace")
                content = content.rstrip(b"\r\n-")
                if filename and content:
                    files.append({"name": filename, "content": content})
            if not files:
                raise ValueError("No files were uploaded")
            return files

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


def _uploads_dir(config: Config) -> Path:
    return config.resolved_data_dir / "web_uploads"


def _list_uploaded_files(config: Config) -> list[dict[str, Any]]:
    root = _uploads_dir(config)
    if not root.exists():
        return []
    files = [_file_payload(path) for path in sorted(root.iterdir(), key=lambda item: item.stat().st_mtime, reverse=True) if path.is_file()]
    return files[:50]


def _file_payload(path: Path, record_id: str = "") -> dict[str, Any]:
    stat = path.stat()
    return {
        "name": path.name,
        "path": str(path),
        "size_bytes": stat.st_size,
        "content_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        "record_id": record_id,
    }


def _project_payload(output_path: Path, manifest_path: Path, record_id: str) -> dict[str, Any]:
    return {
        "output": str(output_path),
        "manifest": str(manifest_path),
        "record_id": record_id,
        "size_bytes": output_path.stat().st_size if output_path.exists() else 0,
    }


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._ -]+", "_", Path(name).name).strip(" .")
    return cleaned or f"upload_{int(time.time())}"


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for index in range(1, 1000):
        candidate = path.with_name(f"{stem}_{index}{suffix}")
        if not candidate.exists():
            return candidate
    return path.with_name(f"{stem}_{uuid.uuid4().hex[:8]}{suffix}")


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
