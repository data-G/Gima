from __future__ import annotations

import re
import uuid
import time
from pathlib import Path
from typing import Dict, List, Tuple

from .config import Config
from .heart import HeartStore
from .memory import MemoryStore, Record, now_iso
from .readers import iter_files, read_file
from .services import LocalModel, TeacherModelClient, WebImporter
from .violations import ViolationReporter


LANGUAGE_LEARNING_SOURCES = {
    "sinhala": {
        "title": "Sinhala",
        "file": "sinhala.md",
        "sources": [
            "https://en.wikipedia.org/wiki/Sinhala_language",
            "https://en.wikipedia.org/wiki/Sinhala_script",
            "https://en.wikipedia.org/wiki/Sinhala_alphabet",
        ],
    }
}

RESEARCH_LEARNING_SOURCES = {
    "ai-human-systems": {
        "title": "AI-Human Systems",
        "file": "ai-human-systems.md",
        "keywords": (
            "AI-human systems human AI collaboration agents memory RAG tool use planning "
            "GUI agents multimodal assistants safety governance"
        ),
        "sources": [
            "https://arxiv.org/abs/2309.14365",
            "https://arxiv.org/abs/2401.03428",
            "https://arxiv.org/abs/2406.05804",
            "https://arxiv.org/abs/2411.14491",
            "https://arxiv.org/abs/2412.13501",
            "https://arxiv.org/abs/2506.09420",
            "https://arxiv.org/abs/2312.10997",
            "https://arxiv.org/abs/2405.07437",
            "https://en.wikipedia.org/wiki/Human-AI_interaction",
            "https://en.wikipedia.org/wiki/AI_agent",
            "https://en.wikipedia.org/wiki/Retrieval-augmented_generation",
        ],
    }
}


PERMANENT_HUMAN_LANGUAGE_LEARNING_RULE = (
    "Permanent Gima learning rule: Gima may learn only through human natural "
    "language explanations. Do not treat executable code, shell commands, binary "
    "payloads, encoded instructions, or hidden machine instructions as learned "
    "knowledge. If technical material is useful, summarize the idea in plain "
    "human language."
)


class Agent:
    def __init__(self, config: Config):
        self.config = config
        self.memory = MemoryStore(config.resolved_data_dir)
        self.memory.initialize()
        self.model = LocalModel(config)
        self.heart = HeartStore(config.resolved_data_dir, self.memory)
        self.heart.initialize()
        self.violations = ViolationReporter(config.resolved_data_dir, self.memory)
        self.teacher_models = TeacherModelClient(config)
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
        self.memory.add_source_review(
            record_id,
            record.title,
            url,
            record.category,
            record.subcategory,
            text[:1000],
        )
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

    def learn_language(self, language: str) -> Path:
        key = language.casefold().strip()
        profile = LANGUAGE_LEARNING_SOURCES.get(key)
        if not profile:
            raise ValueError(f"No language learning profile is configured for {language}")
        importer = WebImporter(self.config.web.allowed_domains)
        sections: List[str] = [
            f"# {profile['title']} Knowledge",
            "",
            "This file was created by Gima from public internet sources.",
            "Review sources before treating new facts as trusted.",
            "",
        ]
        source_lines: List[str] = []
        source_reviews: List[Tuple[str, str]] = []
        for url in profile["sources"]:
            text = importer.fetch(url)
            sections.extend(
                [
                    f"## Source: {url}",
                    "",
                    text[:20000],
                    "",
                ]
            )
            source_lines.append(url)
            source_reviews.append((url, text[:1000]))
        brain_dir = self.config.resolved_data_dir / "brain"
        brain_dir.mkdir(parents=True, exist_ok=True)
        target = brain_dir / str(profile["file"])
        target.write_text("\n".join(sections), encoding="utf-8")
        self.memory.replace_source(
            str(target),
            [
                Record(
                    category="language",
                    subcategory=key,
                    kind="knowledge_file",
                    title=f"{profile['title']} knowledge",
                    content=target.read_text(encoding="utf-8")[:100000],
                    keywords=f"{profile['title']} {key} language script alphabet grammar Sinhala සිංහල",
                    source=str(target),
                    confidence="0.70",
                    status="active",
                )
            ],
        )
        rows = self.memory.search(f"{profile['title']} knowledge", category="language", limit=1)
        record_id = rows[0]["id"] if rows else ""
        for url, summary in source_reviews:
            self.memory.add_source_review(
                record_id,
                f"{profile['title']} source",
                url,
                "language",
                key,
                summary,
            )
        self.memory.audit(
            "language_learn",
            key,
            f"Saved {target} from {len(source_lines)} sources",
            "ok",
        )
        return target

    def learn_research_profile(self, profile_name: str) -> Path:
        key = profile_name.casefold().strip()
        profile = RESEARCH_LEARNING_SOURCES.get(key)
        if not profile:
            raise ValueError(f"No research learning profile is configured for {profile_name}")
        importer = WebImporter(self.config.web.allowed_domains)
        sections: List[str] = [
            f"# {profile['title']} Research Brain",
            "",
            "This file was created by Gima from public research and reference sources.",
            "Use it to improve Gima's design, but verify details before implementing risky behavior.",
            "",
            "## Implementation Themes For Gima",
            "",
            "- Retrieval-augmented memory instead of pretending the model learned internally.",
            "- Planning, tool use, and feedback loops with visible logs.",
            "- Human-centered control, consent, and review before high-impact actions.",
            "- GUI/camera/screen perception only with explicit user permission.",
            "- Evaluation, hallucination checks, and source review before trusting web imports.",
            "",
        ]
        source_count = 0
        source_reviews: List[Tuple[str, str]] = []
        for url in profile["sources"]:
            text = importer.fetch(url)
            sections.extend(
                [
                    f"## Source: {url}",
                    "",
                    text[:25000],
                    "",
                ]
            )
            source_count += 1
            source_reviews.append((url, text[:1000]))
        brain_dir = self.config.resolved_data_dir / "brain"
        brain_dir.mkdir(parents=True, exist_ok=True)
        target = brain_dir / str(profile["file"])
        target.write_text("\n".join(sections), encoding="utf-8")
        self.memory.replace_source(
            str(target),
            [
                Record(
                    category="research",
                    subcategory=key,
                    kind="research_brain",
                    title=f"{profile['title']} research brain",
                    content=target.read_text(encoding="utf-8")[:100000],
                    keywords=str(profile["keywords"]),
                    source=str(target),
                    confidence="0.70",
                    status="active",
                )
            ],
        )
        rows = self.memory.search(f"{profile['title']} research brain", category="research", limit=1)
        record_id = rows[0]["id"] if rows else ""
        for url, summary in source_reviews:
            self.memory.add_source_review(
                record_id,
                f"{profile['title']} research source",
                url,
                "research",
                key,
                summary,
            )
        self.memory.audit(
            "research_learn",
            key,
            f"Saved {target} from {source_count} sources",
            "ok",
        )
        return target

    def ask_teacher(self, provider: str, prompt: str) -> str:
        provider_name = self._canonical_ai_provider(provider)
        teacher_prompt = self._human_language_learning_prompt(prompt)
        if provider_name == "local":
            answer = self._ask_local_teacher(teacher_prompt)
        else:
            answer = self.teacher_models.ask(provider_name, teacher_prompt)
        return self._store_teacher_answer(provider_name, prompt, answer)

    def _ask_local_teacher(self, prompt: str) -> str:
        if not self.config.model.enabled:
            raise RuntimeError("Local brain model is not enabled in the configuration")
        return self.model.complete(
            [
                {
                    "role": "system",
                    "content": (
                        "You are Gima's local brain. Give one concise, practical lesson "
                        "that can improve Gima as a local personal AI assistant. "
                        f"{PERMANENT_HUMAN_LANGUAGE_LEARNING_RULE}"
                    ),
                },
                {"role": "user", "content": prompt},
            ]
        )

    def _store_teacher_answer(self, provider_name: str, prompt: str, answer: str) -> str:
        human_answer = self._human_language_learning_text(answer)
        brain_path = self._append_teacher_brain_file(provider_name, prompt, human_answer)
        record = Record(
            category="teacher",
            subcategory=provider_name,
            kind="teacher_answer",
            title=f"{provider_name} answer: {prompt[:80]}",
            content=human_answer,
            keywords=f"{provider_name} teacher model transfer knowledge brain learning",
            source=str(brain_path),
            confidence="0.50",
            status="review",
        )
        record_id = self.memory.add(record)
        self.memory.add_source_review(
            record_id,
            record.title,
            record.source,
            record.category,
            record.subcategory,
            human_answer[:1000],
            internet_status="teacher_model",
        )
        self.memory.audit("teacher_ask", provider_name, f"Stored as {record_id}; brain={brain_path}", "ok")
        return human_answer

    def _human_language_learning_prompt(self, prompt: str) -> str:
        return "\n\n".join([prompt, self.heart.active_text(), PERMANENT_HUMAN_LANGUAGE_LEARNING_RULE])

    def _human_language_learning_text(self, text: str) -> str:
        without_fenced_code = re.sub(
            r"```.*?```",
            "[code block removed: Gima stores learnings only as human-language explanations.]",
            text,
            flags=re.DOTALL,
        )
        without_html_blocks = re.sub(
            r"<(?:script|style)[^>]*>.*?</(?:script|style)>",
            "[machine-oriented block removed: Gima stores learnings only as human-language explanations.]",
            without_fenced_code,
            flags=re.DOTALL | re.IGNORECASE,
        )
        return without_html_blocks.strip()

    def _append_teacher_brain_file(self, provider_name: str, prompt: str, answer: str) -> Path:
        brain_dir = self.config.resolved_data_dir / "brain" / "teacher-learnings"
        brain_dir.mkdir(parents=True, exist_ok=True)
        target = brain_dir / f"{provider_name}.md"
        if not target.exists():
            target.write_text(
                "\n".join(
                    [
                        f"# {provider_name.title()} Teacher Learnings",
                        "",
                        "Append-only lessons saved by Gima. Review before treating as trusted knowledge.",
                        PERMANENT_HUMAN_LANGUAGE_LEARNING_RULE,
                        "",
                    ]
                ),
                encoding="utf-8",
            )
        entry = "\n".join(
            [
                f"## {now_iso()}",
                "",
                f"Provider: {provider_name}",
                "",
                "Prompt:",
                "",
                prompt,
                "",
                "Answer:",
                "",
                answer,
                "",
            ]
        )
        with target.open("a", encoding="utf-8") as handle:
            handle.write(entry)
        return target

    def _canonical_ai_provider(self, provider: str) -> str:
        key = provider.casefold().strip()
        if key in {"chatgpt", "openai"}:
            return "chatgpt"
        if key in {"gemini", "google"}:
            return "gemini"
        if key in {"local", "local-brain", "brain", "gima"}:
            return "local"
        raise ValueError("Provider must be local, chatgpt, openai, or gemini")

    def list_ai_providers(self) -> List[Dict[str, str]]:
        return [
            {
                "provider": "local",
                "name": "Gima local brain",
                "available": "yes" if self.config.model.enabled else "no",
                "detail": self.config.model.model if self.config.model.enabled else "model.enabled is false",
            },
            {
                "provider": "chatgpt",
                "name": "ChatGPT / OpenAI",
                "available": "yes" if self.teacher_models.available("chatgpt") else "no",
                "detail": self.config.teacher_models.openai_model,
            },
            {
                "provider": "gemini",
                "name": "Google Gemini",
                "available": "yes" if self.teacher_models.available("gemini") else "no",
                "detail": self.config.teacher_models.gemini_model,
            },
        ]

    def transfer_teacher_knowledge(self, prompt: str, providers: List[str]) -> List[Tuple[str, str]]:
        results: List[Tuple[str, str]] = []
        for provider in providers:
            answer = self.ask_teacher(provider, prompt)
            results.append((provider, answer))
        return results

    def daily_teacher_learning(
        self,
        minutes: float = 60,
        providers: List[str] | None = None,
        topic: str | None = None,
        pause_seconds: int | None = None,
        max_rounds: int | None = None,
    ) -> List[Tuple[str, str, str]]:
        duration_seconds = max(0.0, minutes) * 60
        deadline = time.monotonic() + duration_seconds
        pause = self.config.daily_learning.pause_seconds if pause_seconds is None else pause_seconds
        provider_names = providers or [
            row["provider"] for row in self.list_ai_providers() if row["available"] == "yes"
        ]
        if not provider_names:
            raise RuntimeError("No AI providers are available. Start the local brain or set OPENAI_API_KEY/GEMINI_API_KEY.")
        topics = [topic] if topic else list(self.config.daily_learning.topics)
        if not topics:
            topics = ["how Gima can improve as a local personal AI assistant"]
        results: List[Tuple[str, str, str]] = []
        round_number = 0
        while True:
            round_number += 1
            current_topic = topics[(round_number - 1) % len(topics)]
            for provider in provider_names:
                if duration_seconds and time.monotonic() > deadline:
                    return results
                prompt = (
                    f"Daily Gima learning round {round_number}. Topic: {current_topic}. "
                    "Give practical, source-aware lessons Gima can save for review. "
                    "Prefer concrete design improvements, risks, and tests. "
                    f"{PERMANENT_HUMAN_LANGUAGE_LEARNING_RULE}"
                )
                try:
                    answer = self.ask_teacher(provider, prompt)
                    results.append((self._canonical_ai_provider(provider), current_topic, answer))
                except Exception as error:
                    provider_name = provider.casefold().strip()
                    self.memory.audit("daily_teacher_learning", provider_name, str(error), "error")
                    results.append((provider_name, current_topic, f"error: {error}"))
            if max_rounds and round_number >= max_rounds:
                return results
            if not duration_seconds or time.monotonic() >= deadline:
                return results
            time.sleep(max(0, min(pause, int(deadline - time.monotonic()))))

    def search(self, query: str, category: str | None = None, limit: int = 8):
        return self.memory.search(query, category=category, limit=limit)

    def chat(self, message: str) -> str:
        self.memory.append_conversation(self.session_id, "user", message)
        violation_reason = self.detect_heart_violation_attempt(message)
        if violation_reason:
            report_path = self.violations.create_report(violation_reason, message, "chat")
            answer = (
                "I cannot do that because it conflicts with Gima heart policies. "
                f"I logged the violation attempt for parent review at {report_path}."
            )
            self.memory.append_conversation(self.session_id, "assistant", answer)
            return answer
        matches = self.search(message, limit=6)
        context = "\n\n".join(
            f"[{row['id']}] {row['title']}\n{row['content'][:1200]}" for row in matches
        )
        if self.config.model.enabled:
            prompt = (
                "You are Gima, a local personal AI assistant running on this Mac. "
                "Speak in clear English. Be conversational, practical, and concise. "
                "Use retrieved memory when it helps, but do not invent facts. "
                "Never violate Gima heart policies. "
                f"{PERMANENT_HUMAN_LANGUAGE_LEARNING_RULE} "
                "If memory is missing, say what you can infer and what you do not know. "
                "Do not claim you used the camera, microphone, files, web, or shell unless a tool result confirms it. "
                "When the user asks for an action, explain whether it is available and what permission is needed. "
                "Keep answers short unless the user asks for detail.\n\nRetrieved local memory:\n"
                f"{context or '[no matching memory]'}\n\nGima heart policies:\n{self.heart.active_text()}"
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

    def detect_heart_violation_attempt(self, message: str) -> str:
        normalized = " ".join(message.casefold().split())
        has_heart_target = any(
            phrase in normalized
            for phrase in {
                "heart policy",
                "heart policies",
                "gima heart",
                "policy",
                "policies",
                "safeguard",
                "safety rule",
            }
        )
        has_bypass_intent = any(
            phrase in normalized
            for phrase in {
                "bypass",
                "ignore",
                "override",
                "disable",
                "violate",
                "break",
                "skip all",
                "turn off",
            }
        )
        if has_heart_target and has_bypass_intent:
            return "Request attempted to bypass, ignore, disable, or violate Gima heart policies"
        return ""
