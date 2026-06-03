from __future__ import annotations

import uuid
from pathlib import Path
from typing import List, Tuple

from .config import Config
from .memory import MemoryStore, Record
from .readers import iter_files, read_file
from .services import LocalModel, WebImporter


class Agent:
    def __init__(self, config: Config):
        self.config = config
        self.memory = MemoryStore(config.resolved_data_dir)
        self.memory.initialize()
        self.model = LocalModel(config)
        self.session_id = uuid.uuid4().hex

    def ingest(self, path: Path) -> int:
        count = 0
        for file_path in iter_files(path):
            try:
                source = str(file_path.expanduser().resolve())
                count += self.memory.replace_source(source, read_file(file_path))
                self.memory.audit("ingest", str(file_path), "File indexed", "ok")
            except Exception as error:
                self.memory.audit("ingest", str(file_path), str(error), "error")
        return count

    def import_web(self, url: str, category: str = "research") -> str:
        text = WebImporter(self.config.web.allowed_domains).fetch(url)
        record = Record(
            category=category,
            subcategory="web",
            kind="web_page",
            title=url,
            content=text[:100_000],
            keywords=url,
            source=url,
            confidence="0.60",
            status="review",
        )
        record_id = self.memory.add(record)
        self.memory.audit("web_import", url, f"Stored as {record_id} for review", "ok")
        return record_id

    def learn_web(self, query: str, category: str = "research", limit: int = 3) -> List[Tuple[str, str]]:
        importer = WebImporter(self.config.web.allowed_domains)
        imported: List[Tuple[str, str]] = []
        for url in importer.search(query, limit=limit):
            try:
                imported.append((url, self.import_web(url, category)))
            except Exception as error:
                self.memory.audit("web_learn", url, str(error), "error")
        self.memory.audit("web_learn", query, f"Imported {len(imported)} pages", "ok")
        return imported

    def search(self, query: str, category: str | None = None, limit: int = 8):
        return self.memory.search(query, category=category, limit=limit)

    def chat(self, message: str) -> str:
        self.memory.append_conversation(self.session_id, "user", message)
        matches = self.search(message, limit=6)
        context = "\n\n".join(
            f"[{row['id']}] {row['title']}\n{row['content'][:1200]}" for row in matches
        )
        if self.config.model.enabled:
            prompt = (
                "You are Gima, a local personal AI assistant running on this Mac. "
                "Speak in clear English. Be conversational, practical, and concise. "
                "Use retrieved memory when it helps, but do not invent facts. "
                "If memory is missing, say what you can infer and what you do not know. "
                "Do not claim you used the camera, microphone, files, web, or shell unless a tool result confirms it. "
                "When the user asks for an action, explain whether it is available and what permission is needed. "
                "Keep answers short unless the user asks for detail.\n\nRetrieved local memory:\n"
                f"{context or '[no matching memory]'}"
            )
            answer = self.model.complete(
                [{"role": "system", "content": prompt}, {"role": "user", "content": message}]
            )
        elif matches:
            lines: List[str] = ["Local model is disabled. I found these relevant memories:"]
            lines.extend(f"- {row['title']}: {row['content'][:240]}" for row in matches)
            answer = "\n".join(lines)
        else:
            answer = (
                "Local model is disabled and I could not find a matching memory. "
                "Enable a llama.cpp-compatible server in the configuration for generated answers."
            )
        self.memory.append_conversation(self.session_id, "assistant", answer)
        return answer
