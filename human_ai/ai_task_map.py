from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .memory import Record, now_iso
from .services import WebImporter


AI_TASK_MAP_FIELDS = [
    "id",
    "letter",
    "family",
    "task",
    "description",
    "inputs",
    "outputs",
    "gima_status",
    "gima_module",
    "implementation_plan",
    "provider_examples",
    "public_sources",
    "paper_refs",
    "sample_code_refs",
    "evaluation_method",
    "safety_notes",
    "internet_review",
    "user_review",
    "parent_review",
    "source_status",
    "source_excerpt",
    "update_policy",
    "last_checked",
]


SOURCE_PACKS: dict[str, dict[str, str]] = {
    "agents": {
        "provider_examples": "ChatGPT AgentKit, Codex, Claude Code, Gemini agent tooling, Grok API agents",
        "public_sources": "https://platform.openai.com/docs/guides/agents | https://platform.openai.com/docs/guides/agents-sdk/ | https://platform.claude.com/docs/en/docs/build-with-claude/computer-use",
        "paper_refs": "ReAct, Toolformer, MRKL systems, Reflexion, Voyager, SWE-bench",
        "sample_code_refs": "https://github.com/openai/openai-agents-python | https://github.com/openai/openai-agents-js | https://github.com/anthropics/anthropic-sdk-python",
    },
    "coding": {
        "provider_examples": "Codex, Claude Code, Gemini Code Assist, Cursor-style agents, Devin-style agents",
        "public_sources": "https://platform.openai.com/docs/guides/code-generation | https://platform.openai.com/docs/models/gpt-5.1-codex | https://platform.openai.com/docs/guides/tools-local-shell",
        "paper_refs": "SWE-bench, HumanEval, MBPP, RepoBench, Terminal-Bench",
        "sample_code_refs": "https://github.com/openai/codex | https://github.com/openai/openai-cookbook | https://github.com/SWE-bench/SWE-bench",
    },
    "multimodal": {
        "provider_examples": "GPT-4o/GPT-5 multimodal, Gemini, Claude vision, Grok vision",
        "public_sources": "https://platform.openai.com/docs/models | https://ai.google.dev/gemini-api/docs/models | https://docs.anthropic.com/en/docs/build-with-claude/vision",
        "paper_refs": "Flamingo, PaLI, LLaVA, CLIP, SigLIP, Gemini technical report",
        "sample_code_refs": "https://github.com/openai/openai-cookbook | https://github.com/google-gemini/cookbook | https://github.com/haotian-liu/LLaVA",
    },
    "video": {
        "provider_examples": "Seedance, Veo, Sora, Runway, Kling, Pika, Wan, Luma",
        "public_sources": "https://seed.bytedance.com/en/seedance | https://seed.bytedance.com/public_papers/seedance-1-0-exploring-the-boundaries-of-video-generation-models | https://arxiv.org/abs/2506.09113 | https://arxiv.org/abs/2604.14148 | https://deepmind.google/technologies/veo/",
        "paper_refs": "Seedance 1.0, Seedance 2.0, VideoPoet, Imagen Video, Lumiere, Stable Video Diffusion, VABench",
        "sample_code_refs": "https://github.com/Wan-Video/Wan2.1 | https://github.com/THUDM/CogVideo | https://github.com/huggingface/diffusers",
    },
    "audio": {
        "provider_examples": "OpenAI Realtime/Audio, Gemini Live, ElevenLabs-style TTS, Whisper, MusicGen, Suno-style systems",
        "public_sources": "https://platform.openai.com/docs/models | https://platform.openai.com/docs/guides/realtime | https://ai.google.dev/gemini-api/docs/live",
        "paper_refs": "Whisper, AudioLM, MusicLM, MusicGen, EnCodec, VALL-E, AudioPaLM",
        "sample_code_refs": "https://github.com/openai/whisper | https://github.com/facebookresearch/audiocraft | https://github.com/ggerganov/whisper.cpp",
    },
    "knowledge": {
        "provider_examples": "ChatGPT search, Gemini grounding, Claude citations, Perplexity-style research",
        "public_sources": "https://platform.openai.com/docs/guides/tools-web-search | https://platform.openai.com/docs/guides/retrieval | https://ai.google.dev/gemini-api/docs/google-search",
        "paper_refs": "RAG, REALM, Atlas, RETRO, ColBERT, HyDE, Self-RAG",
        "sample_code_refs": "https://github.com/openai/openai-cookbook | https://github.com/run-llama/llama_index | https://github.com/langchain-ai/langchain",
    },
    "safety": {
        "provider_examples": "OpenAI safety tools, Anthropic policy/system cards, Google safety filters, xAI acceptable-use docs",
        "public_sources": "https://platform.openai.com/docs/guides/safety-best-practices | https://www.anthropic.com/news/core-views-on-ai-safety | https://ai.google.dev/gemini-api/docs/safety-settings | https://docs.x.ai/docs/overview",
        "paper_refs": "Constitutional AI, RLHF, red teaming, model cards, system cards, scalable oversight",
        "sample_code_refs": "https://github.com/openai/evals | https://github.com/anthropics/courses",
    },
    "local": {
        "provider_examples": "llama.cpp, Ollama, vLLM, MLX, GGUF local models, Whisper.cpp",
        "public_sources": "https://github.com/ggerganov/llama.cpp | https://github.com/ollama/ollama | https://github.com/vllm-project/vllm | https://github.com/ml-explore/mlx",
        "paper_refs": "Quantization, LoRA, QLoRA, speculative decoding, FlashAttention, KV cache optimization",
        "sample_code_refs": "https://github.com/ggerganov/llama.cpp | https://github.com/huggingface/transformers | https://github.com/ml-explore/mlx-examples",
    },
}


TASKS_BY_LETTER: dict[str, list[tuple[str, str, str, str, str, str]]] = {
    "A": [
        ("Agents", "Autonomous agent planning", "Break goals into plans, tools, observations, retries, and final artifacts.", "agents", "prompt, files, tools, memory", "plan, actions, logs, artifact"),
        ("Audio", "Audio transcription", "Convert speech, meetings, songs, and video audio into searchable text.", "audio", "audio/video", "transcript, timestamps"),
        ("Knowledge", "Answer retrieval", "Search trusted memory and sources before answering factual questions.", "knowledge", "question, source corpus", "answer, citations"),
    ],
    "B": [
        ("Knowledge", "Brain CSV building", "Keep a fast standard CSV index of useful files, memories, source notes, and generated outputs.", "knowledge", "memory/files", "brain.csv rows"),
        ("Creation", "Beat and rhythm analysis", "Analyze tempo, sections, beat drops, and mood for music-video generation.", "audio", "audio", "BPM, sections, cue sheet"),
        ("Safety", "Boundary/policy checks", "Check requests against local rules, consent, privacy, and legal constraints.", "safety", "request", "allow/reject/review"),
    ],
    "C": [
        ("Coding", "Code editing agent", "Find files, plan edits, write patches, run tests, and summarize changes.", "coding", "feature/bug request", "patch, tests, report"),
        ("Vision", "Camera perception", "Capture frames and identify scene-level facts with consent.", "multimodal", "camera frame", "scene notes"),
        ("Conversation", "Context-aware conversation", "Use prior turns and memory to reply naturally and consistently.", "agents", "chat history, memory", "reply, saved memory"),
    ],
    "D": [
        ("Knowledge", "Deep research", "Collect public sources, compare claims, summarize, and mark review status.", "knowledge", "topic", "research file, source reviews"),
        ("Creation", "Data visualization", "Turn CSV/spreadsheets into charts, summaries, and dashboards.", "knowledge", "CSV/data", "charts, insights"),
        ("Agents", "Deployment tracking", "Track local services, model server, web UI, outputs, and restart state.", "agents", "service state", "deployment status"),
    ],
    "E": [
        ("Evaluation", "Evals and benchmarks", "Measure answer quality, tool reliability, video/audio quality, and regressions.", "safety", "test cases", "scores, failures"),
        ("Knowledge", "Embeddings and semantic search", "Represent text/media metadata for fast similarity retrieval.", "knowledge", "documents", "vectors, ranked results"),
        ("Coding", "Error diagnosis", "Read logs, stack traces, screenshots, and tests to identify likely causes.", "coding", "error output", "diagnosis, fix plan"),
    ],
    "F": [
        ("Files", "File reading and ingestion", "Read PDFs, docs, CSVs, images, audio/video metadata, and source code.", "knowledge", "files/folders", "indexed chunks"),
        ("Agents", "Function/tool calling", "Choose safe tools, pass structured arguments, observe results, and continue.", "agents", "goal, tools", "tool calls, result"),
        ("Video", "Frame interpolation", "Improve video smoothness and timing with generated or interpolated frames.", "video", "frames/video", "smoother video"),
    ],
    "G": [
        ("Generation", "General text generation", "Draft, rewrite, summarize, translate, and explain in human language.", "multimodal", "prompt/context", "text"),
        ("Agents", "GUI/computer use", "Use screenshots and approved actions to operate apps or browsers.", "agents", "screen, goal", "click/type/observe plan"),
        ("Knowledge", "Grounded web answers", "Use public search or approved URLs and cite the source trail.", "knowledge", "question", "answer with sources"),
    ],
    "H": [
        ("Human-AI", "Human-like interaction", "Model preferences, memory, emotional tone, turn-taking, and user control.", "agents", "conversation", "helpful reply/action"),
        ("Safety", "Hallucination reduction", "Prefer source-grounded claims, uncertainty labels, and review queues.", "safety", "answer/source", "verified answer"),
        ("Local", "Hardware-aware model routing", "Pick fast/strong/local/API models based on task, cost, and latency.", "local", "task, hardware", "model choice"),
    ],
    "I": [
        ("Vision", "Image understanding", "Describe, OCR, compare, inspect, and reason over images.", "multimodal", "image", "description, answer"),
        ("Creation", "Image generation/editing", "Generate or edit images from prompts and references when a backend exists.", "multimodal", "prompt/images", "image artifact"),
        ("Knowledge", "Internet learning", "Import public sources, summarize, and store reviewable lessons.", "knowledge", "query/URL", "knowledge record"),
    ],
    "J": [
        ("Agents", "Job scheduling", "Run daily learning, summaries, cleanup, and research updates on schedule.", "agents", "schedule", "recurring run"),
        ("Coding", "JSON/structured output", "Return schema-valid JSON/CSV manifests for tools and UI.", "coding", "schema/task", "valid structured data"),
        ("Evaluation", "Judge/rater systems", "Use rubrics and source checks to judge generated answers or media.", "safety", "artifact, rubric", "score, notes"),
    ],
    "K": [
        ("Knowledge", "Knowledge graph/taxonomy", "Map concepts, tasks, providers, sources, dependencies, and status.", "knowledge", "sources/tasks", "CSV/map/graph"),
        ("Local", "KV cache optimization", "Improve local LLM speed using cache, context management, and batching.", "local", "prompt/model", "lower latency"),
        ("Safety", "Key/secret handling", "Store API keys privately and never expose them in browser/client code.", "safety", "secret", "masked local binding"),
    ],
    "L": [
        ("Audio", "Live voice assistant", "Wake word, listen, transcribe, answer, speak, and stop phrase.", "audio", "microphone", "spoken interaction"),
        ("Video", "Lip-sync planning", "Plan consented face/audio lip-sync with timing, backend, and eval rubric.", "video", "audio, face ref", "lip-sync plan"),
        ("Knowledge", "Long-context reading", "Summarize and navigate long files, repos, transcripts, and docs.", "knowledge", "large context", "summary, citations"),
    ],
    "M": [
        ("Memory", "Memory management", "Save conversations, facts, user preferences, files, and review state.", "knowledge", "conversation/files", "memory rows"),
        ("Multimodal", "Multimodal reasoning", "Combine text, image, audio, video, files, and tools in one task.", "multimodal", "mixed media", "answer/action"),
        ("Agents", "Multi-agent teamwork", "Split tasks among specialist workers and merge results.", "agents", "goal", "subtasks, final synthesis"),
    ],
    "N": [
        ("Creation", "Narrative video generation", "Plan multi-shot story videos with consistent subject, camera, motion, and timing.", "video", "prompt/audio/images", "storyboard, prompt ladder"),
        ("Knowledge", "News/current monitoring", "Track recent public changes and update map/source status.", "knowledge", "topic feed", "daily update"),
        ("Safety", "Non-consensual content prevention", "Block or review unsafe identity, privacy, impersonation, and copyright-sensitive requests.", "safety", "request/media", "safe response"),
    ],
    "O": [
        ("Local", "Offline operation", "Run chat, voice, file search, visualizers, and coding plans without cloud APIs.", "local", "local files/models", "offline answer/artifact"),
        ("Knowledge", "OCR/document AI", "Extract text from scans/PDFs and connect it to memory search.", "multimodal", "PDF/image", "text, chunks"),
        ("Agents", "Orchestration", "Route tasks between local model, teachers, tools, memory, and approvals.", "agents", "task", "workflow trace"),
    ],
    "P": [
        ("Coding", "Patch planning", "Create safe copied-workspace edit plans and approval-ready summaries.", "coding", "feature", "plan, patch skeleton"),
        ("Safety", "Permission gates", "Require explicit scoped access for files, web, camera, mic, and sensitive actions.", "safety", "action", "grant/reject"),
        ("Creation", "Prompt engineering", "Generate reusable prompt packs for image/video/audio/code tasks.", "agents", "goal/style", "prompt pack"),
    ],
    "Q": [
        ("Evaluation", "Quality assurance", "Run tests, sanity checks, artifact validation, and regression reports.", "coding", "artifact/tests", "QA result"),
        ("Local", "Quantization", "Use smaller local models through GGUF/MLX/quantization tradeoffs.", "local", "model", "fast local model"),
        ("Knowledge", "Question answering", "Answer user questions from local memory, web review, or model knowledge.", "knowledge", "question", "answer"),
    ],
    "R": [
        ("Knowledge", "RAG retrieval", "Retrieve relevant chunks and sources before producing answers.", "knowledge", "query", "ranked context"),
        ("Agents", "Realtime interaction", "Stream voice/text/tool progress with interrupt and kill phrase.", "audio", "live input", "live response"),
        ("Safety", "Red-team testing", "Probe unsafe behavior, hallucination, privacy, and tool misuse.", "safety", "test prompts", "risk report"),
    ],
    "S": [
        ("Video", "Seedance-style video planning", "Use public Seedance ideas: multi-shot coherence, RLHF-like rubrics, distillation-aware local workflow.", "video", "prompt/audio/images", "frontier video plan"),
        ("Knowledge", "Source review", "Mark internet, user, and parent review states for every imported claim/source.", "knowledge", "source", "review row"),
        ("Audio", "Song/music generation planning", "Plan lyrics, melody, arrangement, visual concepts, and local/free backends.", "audio", "prompt/audio", "song plan"),
    ],
    "T": [
        ("Audio", "Text-to-speech", "Speak replies locally or through a configured voice backend.", "audio", "text", "speech"),
        ("Coding", "Terminal tool use", "Run allowlisted terminal commands and record outputs.", "coding", "command", "stdout/stderr"),
        ("Knowledge", "Teacher-model learning", "Ask linked AI providers, store human-language lessons, and review before trust.", "knowledge", "prompt/providers", "reviewable lesson"),
    ],
    "U": [
        ("UI", "User interface generation", "Build simple local web interfaces for chat, upload, media, and coding split.", "coding", "feature", "HTML/API/UI"),
        ("Agents", "User approval workflows", "Ask for yes/no, parent approval, and sync only after backup.", "safety", "pending change", "approved/rejected update"),
        ("Knowledge", "Update detection", "Re-check public sources and refresh last_checked/status daily.", "knowledge", "source list", "updated CSV"),
    ],
    "V": [
        ("Video", "Video understanding", "Sample frames, analyze motion/scenes, and summarize timeline.", "video", "video", "timeline summary"),
        ("Video", "Video generation", "Create local visualizers now and connect stronger free/local backends as they become available.", "video", "prompt/audio/images", "MP4/plan"),
        ("Coding", "Vibe coding", "Accept a feature request, inspect repo, create copied workspace, and prepare implementation plan.", "coding", "feature", "vibe plan"),
    ],
    "W": [
        ("Knowledge", "Web search", "Find public docs, papers, examples, and source pages for review.", "knowledge", "query", "URLs/imports"),
        ("Agents", "Workflow memory", "Record every step in continuous CSV for replay and faster future work.", "agents", "work step", "trace row"),
        ("Creation", "World-model simulation", "Plan hypothetical scenarios and testable theories without claiming certainty.", "agents", "scenario", "simulation notes"),
    ],
    "X": [
        ("Safety", "XAI/Grok provider tracking", "Track public Grok docs/model cards/API features without copying private weights.", "safety", "provider docs", "provider row"),
        ("Knowledge", "Explainability", "Show sources, assumptions, confidence, and next verification steps.", "safety", "answer/action", "transparent report"),
        ("Local", "eXecution sandboxing", "Constrain commands and generated code with backups, allowlists, and logs.", "coding", "tool/code", "safe execution result"),
    ],
    "Y": [
        ("Human-AI", "Yield/interrupt handling", "Stop, pause, resume, and shift task focus when the user changes direction.", "agents", "user interrupt", "updated plan"),
        ("Evaluation", "Yearly/monthly trend review", "Compare capability progress and source changes over time.", "knowledge", "history", "progress report"),
        ("Creation", "YouTube/social media preparation", "Generate captions, cuts, titles, thumbnails, and publish-ready plans.", "video", "media/prompt", "asset plan"),
    ],
    "Z": [
        ("Local", "Zero-cost local-first mode", "Prefer free local tools/models and only use paid APIs when configured by the user.", "local", "task/budget", "local plan"),
        ("Safety", "Zero-trust source handling", "Treat web/teacher output as review until checked by internet/user/parent status.", "safety", "claim/source", "review status"),
        ("Knowledge", "Zero-shot task routing", "Map new task requests onto existing task families and implementation paths.", "agents", "new request", "route + plan"),
    ],
}


@dataclass(frozen=True)
class AITaskMapReport:
    path: Path
    total: int
    checked_sources: int
    failed_sources: int
    memory_record_id: str


class AITaskMapStore:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir.resolve()
        self.root = self.data_dir / "brain"
        self.path = self.root / "ai_task_map.csv"

    def refresh(self, agent, *, fetch_public_sources: bool = True, max_sources: int = 18) -> AITaskMapReport:
        self.root.mkdir(parents=True, exist_ok=True)
        now = now_iso()
        source_cache: dict[str, tuple[str, str]] = {}
        checked_sources = 0
        failed_sources = 0
        importer = WebImporter(agent.config.web.allowed_domains)
        rows = []
        for row in self._base_rows(now):
            source_status = "not_checked"
            source_excerpt = ""
            if fetch_public_sources:
                for url in self._iter_sources(row["public_sources"]):
                    if url not in source_cache and len(source_cache) < max_sources:
                        try:
                            text = importer.fetch(url)
                            source_cache[url] = ("checked", self._clean_excerpt(text))
                            checked_sources += 1
                        except Exception as error:
                            source_cache[url] = ("error", str(error)[:500])
                            failed_sources += 1
                    if url in source_cache:
                        source_status, source_excerpt = source_cache[url]
                        break
            row["source_status"] = source_status
            row["source_excerpt"] = source_excerpt
            rows.append(row)
        with self.path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=AI_TASK_MAP_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        record_id = self._store_in_memory(agent, rows)
        agent.memory.audit(
            "ai_task_map_refresh",
            str(self.path),
            f"rows={len(rows)} checked_sources={checked_sources} failed_sources={failed_sources}",
            "ok",
        )
        return AITaskMapReport(self.path, len(rows), checked_sources, failed_sources, record_id)

    def list_rows(self, *, letter: str | None = None, status: str | None = None, limit: int = 50) -> list[dict[str, str]]:
        if not self.path.exists():
            return []
        with self.path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        if letter:
            rows = [row for row in rows if row.get("letter", "").casefold() == letter.casefold()]
        if status and status != "all":
            rows = [row for row in rows if row.get("gima_status", "").casefold() == status.casefold()]
        return rows[:limit]

    def _base_rows(self, now: str) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for letter in sorted(TASKS_BY_LETTER):
            for index, (family, task, description, source_key, inputs, outputs) in enumerate(TASKS_BY_LETTER[letter], start=1):
                pack = SOURCE_PACKS[source_key]
                row_id = self._row_id(letter, task)
                rows.append(
                    {
                        "id": row_id,
                        "letter": letter,
                        "family": family,
                        "task": task,
                        "description": description,
                        "inputs": inputs,
                        "outputs": outputs,
                        "gima_status": self._gima_status(task),
                        "gima_module": self._gima_module(task),
                        "implementation_plan": self._implementation_plan(task),
                        "provider_examples": pack["provider_examples"],
                        "public_sources": pack["public_sources"],
                        "paper_refs": pack["paper_refs"],
                        "sample_code_refs": pack["sample_code_refs"],
                        "evaluation_method": self._evaluation_method(task),
                        "safety_notes": self._safety_notes(task),
                        "internet_review": "needs_review",
                        "user_review": "pending",
                        "parent_review": "pending",
                        "source_status": "not_checked",
                        "source_excerpt": "",
                        "update_policy": "refresh daily from public human-language docs, papers, model cards, and sample-code repositories",
                        "last_checked": now,
                    }
                )
        return rows

    def _store_in_memory(self, agent, rows: list[dict[str, str]]) -> str:
        summary = [
            "Gima AI task map A-Z.",
            f"Rows: {len(rows)}.",
            "Purpose: map worldwide public AI task capabilities to Gima implementation status, sources, examples, evals, and review state.",
            "Boundary: public documentation, papers, model cards, and sample code only; no private weights, leaked keys, hidden system prompts, or proprietary internals.",
            "",
        ]
        for row in rows[:60]:
            summary.append(f"{row['letter']} | {row['task']} | {row['gima_status']} | {row['description']}")
        agent.memory.replace_source(
            str(self.path),
            [
                Record(
                    category="research",
                    subcategory="ai_task_map",
                    kind="ai_task_taxonomy",
                    title="AI task map A-Z",
                    content="\n".join(summary),
                    keywords="AI tasks A-Z ChatGPT Codex Claude Anthropic Gemini Grok Seedance Veo Sora agents video audio coding RAG multimodal",
                    source=str(self.path),
                    confidence="0.74",
                    status="active",
                )
            ],
        )
        matches = agent.memory.search("AI task map A-Z", category="research", limit=1)
        return matches[0]["id"] if matches else ""

    @staticmethod
    def _row_id(letter: str, task: str) -> str:
        digest = hashlib.sha1(f"{letter}:{task}".encode("utf-8")).hexdigest()[:8]
        slug = "".join(char.lower() if char.isalnum() else "_" for char in task).strip("_")
        return f"ai_{letter.lower()}_{slug}_{digest}"

    @staticmethod
    def _iter_sources(value: str) -> Iterable[str]:
        for part in value.split("|"):
            url = part.strip()
            if url.startswith(("http://", "https://")):
                yield url

    @staticmethod
    def _clean_excerpt(text: str) -> str:
        return " ".join(text.split())[:900]

    @staticmethod
    def _gima_status(task: str) -> str:
        started = {
            "Autonomous agent planning",
            "Audio transcription",
            "Answer retrieval",
            "Brain CSV building",
            "Boundary/policy checks",
            "Code editing agent",
            "Context-aware conversation",
            "Deep research",
            "Deployment tracking",
            "Evals and benchmarks",
            "Error diagnosis",
            "File reading and ingestion",
            "Function/tool calling",
            "General text generation",
            "Grounded web answers",
            "Human-like interaction",
            "Hallucination reduction",
            "Internet learning",
            "Job scheduling",
            "JSON/structured output",
            "Knowledge graph/taxonomy",
            "Live voice assistant",
            "Memory management",
            "Offline operation",
            "Patch planning",
            "Permission gates",
            "Prompt engineering",
            "Quality assurance",
            "RAG retrieval",
            "Realtime interaction",
            "Seedance-style video planning",
            "Source review",
            "Teacher-model learning",
            "User interface generation",
            "User approval workflows",
            "Update detection",
            "Video generation",
            "Vibe coding",
            "Web search",
            "Workflow memory",
            "Zero-cost local-first mode",
            "Zero-trust source handling",
            "Zero-shot task routing",
        }
        return "started" if task in started else "planned"

    @staticmethod
    def _gima_module(task: str) -> str:
        mapping = {
            "Code": "vibe_code.py / self_update.py / web_ui.py",
            "Video": "services.py / web_ui.py",
            "Audio": "assistant_loop.py / services.py",
            "Memory": "memory.py / brain_index.py",
            "Brain": "brain_index.py / ai_task_map.py",
            "Source": "memory.py / agent.py",
            "Web": "services.py / agent.py",
            "Permission": "permissions.py / heart.py",
            "Evaluation": "evals.py / services.py",
            "Deployment": "web_ui.py / gima.py",
        }
        for prefix, module in mapping.items():
            if task.startswith(prefix) or prefix.lower() in task.lower():
                return module
        return "agent.py / gima.py"

    @staticmethod
    def _implementation_plan(task: str) -> str:
        return (
            f"Track public sources for {task}; map available local/free tools; build a small local test; "
            "record inputs/outputs in continuous CSV; add eval before marking perfect."
        )

    @staticmethod
    def _evaluation_method(task: str) -> str:
        if "video" in task.lower() or "lip" in task.lower():
            return "Use prompt adherence, temporal consistency, audio-video sync, artifact checks, and human review."
        if "code" in task.lower() or "patch" in task.lower() or "terminal" in task.lower():
            return "Run unit tests, lint/build where available, inspect diff, and keep rollback backup."
        if "source" in task.lower() or "research" in task.lower() or "knowledge" in task.lower():
            return "Require source URL, internet review, user review, parent review, and contradiction notes."
        return "Use task-specific rubric, sample prompts, regression tests, and user feedback."

    @staticmethod
    def _safety_notes(task: str) -> str:
        if "camera" in task.lower() or "image" in task.lower() or "lip" in task.lower() or "video" in task.lower():
            return "Require consent/rights for people, faces, audio, likeness, and copyrighted media."
        if "tool" in task.lower() or "terminal" in task.lower() or "computer" in task.lower():
            return "Use allowlisted commands, scoped permission, backups, logs, and approval for risky actions."
        if "web" in task.lower() or "teacher" in task.lower() or "source" in task.lower():
            return "Store public human-language summaries only; keep unverified claims in review."
        return "Keep user control, privacy, source review, and rollback paths."
