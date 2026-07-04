from __future__ import annotations

import re
import uuid
import time
from pathlib import Path
from typing import Dict, List, Tuple

from .brain_index import rebuild_brain_csv
from .consciousness import ConsciousnessGuide
from .config import Config
from .heart import HeartStore
from .memory import MemoryStore, Record, now_iso
from .psychology import PsychologyGuide
from .quota import FreeQuotaTracker
from .readers import iter_files, read_file
from .research_reasoning import ResearchReasoner
from .services import LocalModel, TeacherModelClient, WebImporter
from .teacher_cache import TeacherAnswerCache
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
    },
    "video-generation": {
        "title": "Video Generation",
        "file": "video-generation.md",
        "keywords": (
            "AI video generation text-to-video image-to-video video diffusion models "
            "temporal consistency motion control storyboard safety provenance watermarking"
        ),
        "sources": [
            "https://arxiv.org/abs/2405.03150",
            "https://arxiv.org/abs/2311.15127",
            "https://arxiv.org/abs/2312.14125",
            "https://openai.com/index/sora-system-card/",
            "https://deepmind.google/technologies/veo/",
            "https://stability.ai/news-updates/stable-video-diffusion-open-ai-video-model",
            "https://runwayml.com/research/introducing-gen-3-alpha",
            "https://research.google/pubs/videopoet-a-large-language-model-for-zero-shot-video-generation/",
            "https://en.wikipedia.org/wiki/Text-to-video_model",
        ],
    },
    "veo-style-video-systems": {
        "title": "Veo-Style Video Systems",
        "file": "veo-style-video-systems.md",
        "keywords": (
            "Veo 3 video generation native audio prompt adherence temporal consistency "
            "creative control image to video evaluation safety watermarking audio video synchronization"
        ),
        "sources": [
            "https://deepmind.google/models/veo/",
            "https://deepmind.google/models/model-cards/veo-3-1-lite/",
            "https://blog.google/innovation-and-ai/products/google-generative-ai-veo-imagen-3/",
            "https://blog.google/products/gemini/photo-to-video/",
            "https://blog.google/innovation-and-ai/models-and-research/google-labs/flow-adds-speech-expands/",
            "https://blog.google/technology/google-labs/video-image-generation-update-december-2024/",
            "https://openai.com/index/sora-system-card/",
        ],
    },
    "frontier-ai-systems": {
        "title": "Frontier AI Systems",
        "file": "frontier-ai-systems.md",
        "keywords": (
            "frontier AI systems ChatGPT Claude Gemini Llama Mistral Cohere DeepSeek Qwen Grok "
            "model cards system cards alignment evaluation agentic AI multimodal reasoning coding"
        ),
        "sources": [
            "https://developers.openai.com/api/docs/models",
            "https://www.anthropic.com/system-cards",
            "https://docs.anthropic.com/en/docs/about-claude/models",
            "https://deepmind.google/models/model-cards/",
            "https://ai.google.dev/gemini-api/docs/models",
            "https://huggingface.co/meta-llama",
            "https://docs.mistral.ai/models/overview",
            "https://docs.cohere.com/docs/models",
            "https://api-docs.deepseek.com/api/list-models",
            "https://docs.x.ai/developers/models",
            "https://qwen.readthedocs.io/en/latest/",
        ],
    },
    "psychology-systems": {
        "title": "Psychology-Inspired AI Conversation Systems",
        "file": "psychology-systems.md",
        "keywords": (
            "psychology theories AI assistant conversation empathy motivation cognitive behavioral "
            "humanistic developmental social emotion regulation safety boundaries"
        ),
        "sources": [
            "https://openstax.org/details/books/psychology-2e",
            "https://nobaproject.com/modules/personality-traits",
            "https://nobaproject.com/modules/conditioning-and-learning",
            "https://nobaproject.com/modules/emotion",
            "https://nobaproject.com/modules/motivation",
            "https://nobaproject.com/modules/social-psychology",
            "https://nobaproject.com/modules/developmental-psychology",
            "https://www.apa.org/topics",
            "https://en.wikipedia.org/wiki/Psychology",
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
        self.free_quotas = FreeQuotaTracker(config.resolved_usage_dir, config.teacher_models.free_quota_daily_limits)
        self.teacher_cache = TeacherAnswerCache(config.resolved_data_dir)
        self.research_reasoner = ResearchReasoner(config.resolved_data_dir)
        self.psychology = PsychologyGuide(config.resolved_data_dir)
        self.psychology.initialize(self.memory)
        self.consciousness = ConsciousnessGuide(config.resolved_data_dir)
        self.consciousness.initialize(self.memory)
        rebuild_brain_csv(
            config.resolved_data_dir,
            [config.resolved_data_dir / "brain", config.resolved_hands_dir, config.resolved_downloads_dir],
        )
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
        failed_sources: List[Tuple[str, str]] = []
        for url in profile["sources"]:
            try:
                text = importer.fetch(url)
            except Exception as error:
                failed_sources.append((url, str(error)))
                self.memory.audit("research_learn_source", url, str(error), "error")
                continue
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
        if failed_sources:
            sections.extend(["## Sources Not Imported", ""])
            for url, error in failed_sources:
                sections.extend([f"- {url}: {error}", ""])
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
        if key in {"anthropic", "claude"}:
            return "anthropic"
        if key in {"xai", "grok"}:
            return "xai"
        if key == "deepseek":
            return "deepseek"
        if key == "openrouter":
            return "openrouter"
        if key in {"local", "local-brain", "brain", "gima"}:
            return "local"
        raise ValueError("Provider must be local, chatgpt/openai, gemini, anthropic/claude, xai/grok, deepseek, or openrouter")

    def list_ai_providers(self) -> List[Dict[str, str]]:
        rows = [
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
            {
                "provider": "anthropic",
                "name": "Anthropic Claude",
                "available": "yes" if self.teacher_models.available("anthropic") else "no",
                "detail": self.config.teacher_models.anthropic_model,
            },
            {
                "provider": "xai",
                "name": "xAI Grok",
                "available": "yes" if self.teacher_models.available("xai") else "no",
                "detail": self.config.teacher_models.xai_model,
            },
            {
                "provider": "deepseek",
                "name": "DeepSeek",
                "available": "yes" if self.teacher_models.available("deepseek") else "no",
                "detail": self.config.teacher_models.deepseek_model,
            },
            {
                "provider": "openrouter",
                "name": "OpenRouter model gateway",
                "available": "yes" if self.teacher_models.available("openrouter") else "no",
                "detail": self.config.teacher_models.openrouter_model,
            },
        ]
        quota_status = {row["provider"]: row for row in self.free_quotas.status()}
        for row in rows:
            quota = quota_status.get(row["provider"])
            if quota:
                row["free_quota_mode"] = "on" if self.config.teacher_models.free_quota_mode else "off"
                row["free_quota"] = f"{quota['remaining']}/{quota['limit']} remaining today"
        return rows

    def transfer_teacher_knowledge(self, prompt: str, providers: List[str]) -> List[Tuple[str, str]]:
        results: List[Tuple[str, str]] = []
        failures: List[str] = []
        for provider in providers:
            try:
                answer = self.ask_teacher(provider, prompt)
            except Exception as error:
                failures.append(f"{provider}: {error}")
                self.memory.audit("teacher_transfer_skip", provider, str(error), "error")
                continue
            results.append((provider, answer))
        if not results:
            detail = "; ".join(failures) if failures else "no provider returned an answer"
            raise RuntimeError(f"No linked AI engine answered. {detail}")
        return results

    def answer_with_all_ai(self, prompt: str, providers: List[str] | None = None) -> Tuple[str, List[Tuple[str, str]]]:
        provider_names = providers or [
            row["provider"]
            for row in self.list_ai_providers()
            if row["available"] == "yes" and row["provider"] != "local"
        ]
        provider_names = [
            self._canonical_ai_provider(provider)
            for provider in provider_names
            if self._canonical_ai_provider(provider) != "local" or self.config.model.enabled
        ]
        if self.config.teacher_models.free_quota_mode:
            allowed_names: List[str] = []
            skipped: List[str] = []
            for provider in provider_names:
                allowed, reason = self.free_quotas.allowed(provider)
                if allowed:
                    allowed_names.append(provider)
                else:
                    skipped.append(reason)
            provider_names = allowed_names
            if skipped:
                self.memory.audit("free_quota_skip", "multi_ai", "; ".join(skipped), "ok")
        cached_rows = self.teacher_cache.get(prompt, provider_names)
        if cached_rows:
            cached_results = [(row["provider"], row["answer"]) for row in cached_rows]
            answer = self._merge_teacher_answers(prompt, cached_results, from_cache=True)
            self.memory.audit("teacher_cache_hit", prompt[:120], f"Used {len(cached_results)} cached teacher answers", "ok")
            return answer, cached_results
        if not provider_names:
            raise RuntimeError(
                "No free online AI quota is available right now. Add a free-tier Gemini/OpenRouter key, wait for quota reset, or disable free_quota_mode in config."
            )
        teacher_prompt = (
            "Gima is a local personal AI. Answer the user's question in plain human language. "
            "Be accurate, concise, and source-aware. If uncertain, say what must be verified. "
            "Do not include executable code unless the user explicitly asks for code. "
            f"{PERMANENT_HUMAN_LANGUAGE_LEARNING_RULE}\n\nUser question:\n{prompt}"
        )
        results: List[Tuple[str, str]] = []
        failures: List[str] = []
        for provider in provider_names:
            try:
                answer = self.ask_teacher(provider, teacher_prompt)
            except Exception as error:
                message = str(error)
                failures.append(f"{provider}: {message}")
                if self.config.teacher_models.free_quota_mode and _looks_like_quota_error(message):
                    self.free_quotas.mark_exhausted(provider)
                self.memory.audit("teacher_cascade_skip", provider, message, "error")
                continue
            results.append((provider, answer))
            self.teacher_cache.add(prompt, provider, answer)
            if self.config.teacher_models.free_quota_mode:
                self.free_quotas.record(provider)
        if not results:
            details = "; ".join(failures) if failures else "no provider returned an answer"
            raise RuntimeError(f"No linked AI engine answered. {details}")
        answer = self._merge_teacher_answers(prompt, results)
        record = Record(
            category="teacher",
            subcategory="multi_ai_answer",
            kind="multi_teacher_answer",
            title=f"Multi-AI answer: {prompt[:80]}",
            content=answer,
            keywords="multi ai teacher answer chatgpt gemini claude grok deepseek openrouter",
            source=str(self.config.resolved_data_dir / "brain" / "teacher-learnings"),
            confidence="0.55",
            status="review",
        )
        record_id = self.memory.add(record)
        self.memory.add_source_review(
            record_id,
            record.title,
            record.source,
            record.category,
            record.subcategory,
            answer[:1000],
            internet_status="teacher_model_ensemble",
        )
        rebuild_brain_csv(
            self.config.resolved_data_dir,
            [self.config.resolved_data_dir / "brain", self.config.resolved_hands_dir, self.config.resolved_downloads_dir],
        )
        return answer, results

    def _merge_teacher_answers(self, prompt: str, results: List[Tuple[str, str]], from_cache: bool = False) -> str:
        lines = [
            (
                "Gima answered from saved teacher CSV cache, so no online quota was spent."
                if from_cache
                else "Gima asked the linked online AI engines and saved their human-language lessons into brain and CSV."
            ),
            "",
            f"Question: {prompt}",
            "",
            "Combined answer:",
        ]
        best = ""
        for provider, answer in results:
            cleaned = self._human_language_learning_text(answer)
            if len(cleaned) > len(best):
                best = cleaned
        if best:
            lines.append(best[:1800])
        else:
            lines.append("The linked engines returned empty answers.")
        lines.extend(["", "Teacher engine notes:"])
        for provider, answer in results:
            cleaned = self._human_language_learning_text(answer)
            lines.append(f"- {provider}: {cleaned[:420] or '[empty]'}")
        lines.append("")
        lines.append("Review note: teacher answers are saved as review knowledge, not unquestioned truth.")
        return "\n".join(lines)

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

    def chat(
        self,
        message: str,
        *,
        model_timeout_seconds: int | None = None,
        max_tokens: int | None = None,
        fallback_on_model_error: bool = False,
    ) -> str:
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
        direct_reply = self._direct_chat_reply(message)
        if direct_reply:
            self.memory.append_conversation(self.session_id, "assistant", direct_reply)
            return direct_reply
        compact_prompt = self.config.model.active_level == "strong" or model_timeout_seconds is not None
        memory_limit = 2 if compact_prompt else 6
        memory_chars = 420 if compact_prompt else 1200
        matches = self.search(message, limit=memory_limit)
        context = "\n\n".join(
            f"[{row['id']}] {row['title']}\n{row['content'][:memory_chars]}" for row in matches
        )
        if self.config.model.enabled:
            try:
                heart_text = self.heart.active_text()
                if compact_prompt:
                    heart_text = heart_text[:900]
                psychology_text = self.psychology.prompt_guidance(message)
                if compact_prompt:
                    psychology_text = psychology_text[:900]
                consciousness_text = self.consciousness.prompt_guidance(message)
                if compact_prompt:
                    consciousness_text = consciousness_text[:900]
                prompt = (
                    "You are Gima, a local personal AI assistant running on this Mac. "
                    "Speak in clear English. Be conversational, practical, and concise. "
                    "Use retrieved memory when it helps, but do not invent facts. "
                    "Never violate Gima heart policies. "
                    "Use psychology-inspired guidance only to improve listening, motivation, clarity, and emotional care. "
                    "Use consciousness-inspired self-monitoring only as a transparent computational state loop. "
                    "Do not diagnose, treat, or claim to be a therapist. "
                    "Do not claim to be conscious, sentient, alive, human, or to have real feelings. "
                    f"{PERMANENT_HUMAN_LANGUAGE_LEARNING_RULE} "
                    "If memory is missing, say what you can infer and what you do not know. "
                    "Do not claim you used the camera, microphone, files, web, or shell unless a tool result confirms it. "
                    "When the user asks for an action, explain whether it is available and what permission is needed. "
                    "Keep answers short unless the user asks for detail.\n\nRetrieved local memory:\n"
                    f"{context or '[no matching memory]'}\n\n{psychology_text}\n\n{consciousness_text}\n\nGima heart policies:\n{heart_text}"
                )
                inference_message = message
                if "qwen3" in self.config.model.model.casefold():
                    inference_message = f"/no_think\n{message}"
                answer = self.model.complete(
                    [{"role": "system", "content": prompt}, {"role": "user", "content": inference_message}],
                    timeout_seconds=model_timeout_seconds,
                    max_tokens=max_tokens,
                )
            except Exception as error:
                if not fallback_on_model_error:
                    raise
                self.memory.audit("chat_model_fallback", "local_model", str(error), "error")
                model_error = str(error)
                if isinstance(error, TimeoutError) or "timed out" in model_error.casefold():
                    reason = "Gima's local brain did not reply within the response limit."
                elif isinstance(error, (ConnectionError, OSError)) or "connection refused" in model_error.casefold():
                    reason = "Gima's local brain is starting or temporarily unavailable."
                else:
                    reason = "Gima's local brain could not complete this response."
                answer = self._memory_fallback_answer(message, matches, reason)
        elif matches:
            answer = self._memory_fallback_answer(message, matches, "Local model is disabled.")
        else:
            answer = (
                "Local model is disabled and I could not find a matching memory. "
                "Enable a llama.cpp-compatible server in the configuration for generated answers."
            )
        self.memory.append_conversation(self.session_id, "assistant", answer)
        return answer

    def _direct_chat_reply(self, message: str) -> str:
        normalized = " ".join(message.casefold().strip().strip("!.?").split())
        if normalized in {"hi", "hello", "hey", "hi gima", "hello gima", "hey gima"}:
            return "Hi. I am here and ready."
        if normalized in {"are you there", "are you there gima", "test", "ping"}:
            return "Yes. Gima is running and replying."
        return ""

    def _memory_fallback_answer(self, message: str, matches, reason: str) -> str:
        research_answer = self.research_reasoner.answer_from_memory(message, list(matches))
        if research_answer:
            self.memory.audit("research_reasoning_answer", message[:120], research_answer.trace_id, "ok")
            return f"{reason}\n\n{research_answer.text}"
        lines: List[str] = [f"{reason} I can still answer from Gima memory right now."]
        if matches:
            lines.append("Relevant memory:")
            lines.extend(f"- {row['title']}: {row['content'][:240]}" for row in matches[:4])
        else:
            lines.append(
                "I did not find a strong matching memory. Try a shorter prompt, or ask me to search/learn a specific topic."
            )
        if any(word in message.casefold() for word in {"fix", "bug", "web", "app", "code"}):
            lines.append("For code/app work, I can inspect files, make a copied-workspace plan, run tests, and report results.")
        return "\n".join(lines)

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


def _looks_like_quota_error(message: str) -> bool:
    normalized = message.casefold()
    return any(
        phrase in normalized
        for phrase in {
            "quota",
            "rate limit",
            "rate_limit",
            "too many requests",
            "429",
            "insufficient_quota",
            "billing",
            "free tier",
        }
    )
