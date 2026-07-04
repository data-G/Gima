from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List

from .agent import Agent
from .brain import BrainServer
from .memory import now_iso
from .services import dependency_report


CAPABILITY_FIELDS = [
    "id",
    "family",
    "capability",
    "status",
    "local_support",
    "next_action",
    "source",
    "updated_at",
]


@dataclass(frozen=True)
class CapabilitySpec:
    id: str
    family: str
    capability: str
    local_support: str
    next_action: str
    source: str
    status_fn: Callable[[dict], str]


def _done_when(key: str) -> Callable[[dict], str]:
    return lambda state: "done" if state.get(key) else "missing"


def _started_when(key: str) -> Callable[[dict], str]:
    return lambda state: "started" if state.get(key) else "missing"


def _always_started(_: dict) -> str:
    return "started"


def _planned(_: dict) -> str:
    return "planned"


CAPABILITY_SPECS: List[CapabilitySpec] = [
    CapabilitySpec(
        "llm_text_chat",
        "Core Intelligence",
        "Text conversation with local or teacher LLMs",
        "Local llama.cpp brain plus ChatGPT/Gemini teacher adapters.",
        "Keep benchmarking fast and strong local model levels.",
        "https://openai.com/index/hello-gpt-4o/",
        _started_when("brain_running"),
    ),
    CapabilitySpec(
        "reasoning_modes",
        "Core Intelligence",
        "Fast and deeper reasoning modes",
        "Fast/strong local model tiers; teacher models can be used for deeper review.",
        "Add explicit latency and answer-quality benchmarks per model level.",
        "https://www.anthropic.com/news/claude-4",
        _started_when("strong_model_available"),
    ),
    CapabilitySpec(
        "extended_thinking_tool_use",
        "Core Intelligence",
        "Reasoning that can alternate with tools",
        "Self-update workflow, teacher learning, and allowlisted tool runner exist.",
        "Add a visible plan/act/observe loop with eval cases.",
        "https://www.anthropic.com/engineering/claude-think-tool",
        _always_started,
    ),
    CapabilitySpec(
        "structured_outputs",
        "Core Intelligence",
        "Structured JSON/CSV outputs",
        "CSV memory, eval, scale, Dream, and capability stores.",
        "Add schema validation for every tool-producing assistant action.",
        "https://platform.openai.com/docs/guides/structured-outputs",
        _always_started,
    ),
    CapabilitySpec(
        "realtime_voice",
        "Audio",
        "Realtime voice conversation",
        "Whisper CLI, ffmpeg microphone capture, macOS speech output, wake word, kill phrase.",
        "Benchmark wake latency and improve streaming partial transcription.",
        "https://openai.com/index/introducing-gpt-realtime/",
        lambda state: "done" if state.get("ffmpeg") and state.get("whisper-cli") else "missing",
    ),
    CapabilitySpec(
        "speech_to_text",
        "Audio",
        "Speech-to-text transcription",
        "whisper.cpp CLI model support.",
        "Add language/accent profiles and confidence tracking.",
        "https://openai.com/index/hello-gpt-4o/",
        _done_when("whisper-cli"),
    ),
    CapabilitySpec(
        "text_to_speech",
        "Audio",
        "Text-to-speech replies",
        "macOS say command.",
        "Add selectable voices and faster interruption handling.",
        "https://openai.com/index/hello-gpt-4o/",
        _done_when("say"),
    ),
    CapabilitySpec(
        "translation_multilingual",
        "Audio",
        "Multilingual understanding and translation",
        "Language lock, Sinhala learning, teacher/local model translation ability.",
        "Add explicit translation evals for English, Sinhala, Japanese, and mixed transcripts.",
        "https://openai.com/index/hello-gpt-4o/",
        _always_started,
    ),
    CapabilitySpec(
        "image_understanding",
        "Vision",
        "Image and screenshot understanding",
        "Screenshot/camera capture, OCR tools, file ingestion.",
        "Add a local vision-language model or API adapter for image question answering.",
        "https://openai.com/index/hello-gpt-4o/",
        lambda state: "started" if state.get("ffmpeg") and state.get("tesseract") else "missing",
    ),
    CapabilitySpec(
        "camera_scene",
        "Vision",
        "Camera scene capture and person counting",
        "Camera capture plus configurable detector command and scene memory.",
        "Install/configure a local detector for richer object/person recognition.",
        "https://deepmind.google/technologies/veo/",
        _started_when("ffmpeg"),
    ),
    CapabilitySpec(
        "video_understanding",
        "Vision",
        "Video frame analysis and temporal summaries",
        "ffmpeg/ffprobe frame extraction and media analysis hooks.",
        "Add sampled-frame captioning and timeline memory.",
        "https://openai.com/index/hello-gpt-4o/",
        lambda state: "started" if state.get("ffmpeg") and state.get("ffprobe") else "missing",
    ),
    CapabilitySpec(
        "ocr_documents",
        "Vision",
        "OCR and document reading",
        "tesseract, pdftotext, readers, CSV/spreadsheet loaders.",
        "Add document QA evals and source-page citations.",
        "https://openai.com/index/gpt-4o-and-more-tools-to-chatgpt-free/",
        lambda state: "done" if state.get("tesseract") and state.get("pdftotext") else "started",
    ),
    CapabilitySpec(
        "image_generation",
        "Creation",
        "Image generation and editing",
        "Can use external image generation when integrated; no local image generator is configured.",
        "Add an approved provider/local model adapter and artifact logging.",
        "https://openai.com/index/introducing-4o-image-generation/",
        _planned,
    ),
    CapabilitySpec(
        "video_generation",
        "Creation",
        "Text-to-video and image-to-video generation",
        "Local ffmpeg image+audio video rendering, advanced scene/storyboard/pitch planner, and frontier prompt ladder exist; neural text-to-video backend is not configured.",
        "Add approved neural video backend after consent/provenance logging and media evals.",
        "https://deepmind.google/technologies/veo/",
        lambda state: "started" if state.get("ffmpeg") and state.get("ffprobe") else "planned",
    ),
    CapabilitySpec(
        "local_music_video",
        "Creation",
        "Local MP3/audio-to-video visualizer rendering",
        "Offline ffmpeg renderer creates waveform or spectrum MP4 videos from consented audio.",
        "Add beat detection, templates, lyric captions, and optional local image/video overlays.",
        "https://ffmpeg.org/ffmpeg-filters.html",
        _started_when("ffmpeg"),
    ),
    CapabilitySpec(
        "lip_sync",
        "Creation",
        "Lip-sync project planning from one prompt",
        "Consent-gated lip-sync manifest planner exists.",
        "Add an approved renderer backend and artifact evals.",
        "https://openai.com/index/introducing-4o-image-generation/",
        _always_started,
    ),
    CapabilitySpec(
        "audio_music",
        "Creation",
        "Audio/music understanding and generation planning",
        "Audio capture/transcription exists; generation backend is not configured.",
        "Add consented audio-generation adapter and copyright-safe policies.",
        "https://openai.com/index/introducing-gpt-realtime/",
        _planned,
    ),
    CapabilitySpec(
        "web_search_learning",
        "Knowledge",
        "Web search, internet learning, source review",
        "DuckDuckGo/Wikipedia search fallback, public URL import, source review CSV.",
        "Add citation quality scoring and scheduled source review reminders.",
        "https://openai.com/index/gpt-4o-and-more-tools-to-chatgpt-free/",
        _always_started,
    ),
    CapabilitySpec(
        "rag_memory",
        "Knowledge",
        "Retrieval-augmented memory",
        "CSV source of truth plus SQLite FTS index and categorized brain files.",
        "Add ranking evals, embeddings, and category-specific retrieval tuning.",
        "https://openai.com/index/gpt-4o-and-more-tools-to-chatgpt-free/",
        _always_started,
    ),
    CapabilitySpec(
        "teacher_models",
        "Knowledge",
        "Learning from external teacher LLMs",
        "OpenAI/ChatGPT and Gemini teacher adapters with human-language-only storage.",
        "Add provider health checks and per-provider learning evals.",
        "https://ai.google.dev/gemini-api/docs/models",
        _started_when("teacher_ready"),
    ),
    CapabilitySpec(
        "coding_agent",
        "Tools",
        "Code editing, testing, self-update copies",
        "Offline vibe-code planner, self-update prepare/ready/sync workflow, backups, tests, GitHub push.",
        "Add patch review scoring, automatic rollback tests, and optional local model patch drafts.",
        "https://www.anthropic.com/news/claude-4",
        _always_started,
    ),
    CapabilitySpec(
        "function_tool_calling",
        "Tools",
        "Tool/function calling",
        "Allowlisted local tool runner and permission-gated assistant actions.",
        "Add structured tool plans and per-tool eval coverage.",
        "https://openai.com/index/introducing-gpt-realtime/",
        _started_when("tools_configured"),
    ),
    CapabilitySpec(
        "computer_use",
        "Tools",
        "Computer/browser/screen use",
        "Screenshots and local terminal commands exist; unrestricted computer control is not enabled.",
        "Add explicit UI automation only through approved, auditable actions.",
        "https://docs.anthropic.com/en/docs/agents-and-tools/computer-use",
        _started_when("ffmpeg"),
    ),
    CapabilitySpec(
        "files_data_analysis",
        "Tools",
        "File reading, CSV, spreadsheet, and data analysis",
        "File readers, CSV memory, Miller/csvkit optional tooling.",
        "Add chart/table generation and notebook-like analysis evals.",
        "https://openai.com/index/gpt-4o-and-more-tools-to-chatgpt-free/",
        lambda state: "done" if state.get("mlr") and state.get("csvcut") else "started",
    ),
    CapabilitySpec(
        "automation_scheduling",
        "Tools",
        "Scheduled learning and recurring automations",
        "launchd daily learning schedule support.",
        "Add health monitors and failed-job retry reporting.",
        "https://openai.com/index/introducing-gpt-realtime/",
        _always_started,
    ),
    CapabilitySpec(
        "mcp_remote_tools",
        "Tools",
        "MCP-style external tool/context integration",
        "Not yet exposed as Gima runtime MCP server/client.",
        "Add a small local MCP-compatible bridge after tool safety evals.",
        "https://openai.com/index/introducing-gpt-realtime/",
        _planned,
    ),
    CapabilitySpec(
        "policy_safety",
        "Safety",
        "Policies, refusal, permissions, violation reporting",
        "Heart policies, scoped grants, parent review, violation email reports.",
        "Expand evals for misuse, privacy, and provenance.",
        "https://cdn.openai.com/gpt-4o-system-card.pdf",
        _always_started,
    ),
    CapabilitySpec(
        "provenance_watermarking",
        "Safety",
        "Generated artifact provenance and audit trails",
        "Audit CSVs and artifact manifests exist; C2PA/watermarking is not configured.",
        "Add artifact manifests for every generated media output and provenance metadata when possible.",
        "https://openai.com/index/introducing-4o-image-generation/",
        _started_when("audit_ready"),
    ),
    CapabilitySpec(
        "evaluation_benchmarks",
        "Quality",
        "Repeatable evals and regression tests",
        "Eval CSV runner plus unit tests.",
        "Expand evals to all capability families.",
        "https://www.anthropic.com/news/claude-4",
        _started_when("eval_ready"),
    ),
    CapabilitySpec(
        "model_routing",
        "Quality",
        "Multi-model routing and fallback",
        "Fast/strong local model levels plus teacher providers.",
        "Add automatic route selection by task type and latency budget.",
        "https://openai.com/index/gpt-4o-and-more-tools-to-chatgpt-free/",
        _started_when("strong_model_available"),
    ),
    CapabilitySpec(
        "privacy_security",
        "Safety",
        "Privacy, secrets, local-first storage, safe networking",
        "Private secrets file, local memory, blocked private web hosts.",
        "Add secret scanning and encrypted memory options.",
        "https://cdn.openai.com/gpt-4o-system-card.pdf",
        _always_started,
    ),
    CapabilitySpec(
        "deep_research_agent",
        "Future Agents",
        "Long-running cited research with planning, source comparison, and interruption",
        "Gima has public-web import, research reasoning, citations, files, and continuous work logs.",
        "Add a resumable research plan, trusted-domain controls, claim-to-source checks, and progress UI.",
        "https://openai.com/index/introducing-deep-research/",
        _always_started,
    ),
    CapabilitySpec(
        "long_horizon_agent",
        "Future Agents",
        "Long-horizon task execution with checkpoints, recovery, and human approval",
        "Continuous work CSVs, snapshots, self-update copies, tests, and approval gates are started.",
        "Add resumable task state, milestone budgets, retry policy, and independent completion checks.",
        "https://hai.stanford.edu/ai-index/2025-ai-index-report",
        _always_started,
    ),
    CapabilitySpec(
        "multi_agent_collaboration",
        "Future Agents",
        "Specialist agents that divide work, challenge results, and merge evidence",
        "Provider routing exists, but autonomous specialist collaboration is not implemented.",
        "Add planner, researcher, builder, verifier, and safety-review roles with shared trace IDs.",
        "https://hai.stanford.edu/assets/files/hai_ai_index_report_2025.pdf",
        _planned,
    ),
    CapabilitySpec(
        "proactive_personal_assistant",
        "Future Personal AI",
        "User-controlled proactive monitoring, reminders, and workflow suggestions",
        "Scheduled learning and continuous cycles exist; proactive user workflows are not yet generalized.",
        "Add opt-in monitors, notification controls, quiet hours, relevance scoring, and easy disable/delete.",
        "https://openai.com/index/introducing-deep-research/",
        _always_started,
    ),
    CapabilitySpec(
        "scientific_discovery",
        "Future Science",
        "Hypothesis generation, simulation, literature synthesis, and reproducible analysis",
        "Gima can research and run sandboxed code, but is not a validated scientific discovery system.",
        "Add dataset provenance, notebook artifacts, statistical checks, replication tasks, and expert review.",
        "https://hai.stanford.edu/ai-index/2025-ai-index-report",
        _planned,
    ),
    CapabilitySpec(
        "embodied_robotics",
        "Future Robotics",
        "Vision-language-action reasoning for safe physical-world assistance",
        "No robot-control backend is connected; Gima only tracks public research concepts.",
        "Start with simulation, typed action schemas, emergency stop, workspace limits, and supervised evaluation.",
        "https://deepmind.google/discover/blog/gemini-robotics-brings-ai-into-the-physical-world",
        _planned,
    ),
    CapabilitySpec(
        "spatial_world_models",
        "Future Multimodal",
        "Persistent 3D/spatial scene understanding and editable world simulation",
        "Image/video plans exist, but Gima does not maintain a metric 3D world model.",
        "Add scene graphs, camera geometry, temporal identity tracking, simulation, and spatial consistency evals.",
        "https://hai.stanford.edu/assets/files/hai_ai_index_report_2025.pdf",
        _planned,
    ),
    CapabilitySpec(
        "trustworthy_autonomy",
        "Future Safety",
        "Risk-budgeted autonomy with least privilege, monitoring, rollback, and audit",
        "Permissions, secrets, review states, audit CSVs, backups, and approval-gated sync are started.",
        "Add per-tool risk tiers, action simulation, policy tests, incident review, and signed audit records.",
        "https://www.nist.gov/itl/ai-risk-management-framework",
        _always_started,
    ),
    CapabilitySpec(
        "high_stakes_assistance",
        "Future Human Support",
        "Evidence-grounded education, accessibility, health, legal, and financial assistance",
        "Gima can organize information but is not certified for diagnosis, legal judgment, or financial decisions.",
        "Add domain-specific sources, uncertainty display, professional escalation, accessibility tests, and strict no-diagnosis rules.",
        "https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf",
        _planned,
    ),
]


@dataclass(frozen=True)
class CapabilityReport:
    path: Path
    total: int
    done: int
    started: int
    planned: int
    missing: int


class CapabilityStore:
    def __init__(self, data_dir: Path):
        self.root = data_dir / "capabilities"
        self.capabilities_path = self.root / "capabilities.csv"
        self.sources_path = self.root / "sources.md"

    def build(self, agent: Agent, brain: BrainServer) -> CapabilityReport:
        self.root.mkdir(parents=True, exist_ok=True)
        state = self._state(agent, brain)
        rows = [self._row(spec, state) for spec in CAPABILITY_SPECS]
        with self.capabilities_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=CAPABILITY_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        self._write_sources(rows)
        counts = {status: sum(1 for row in rows if row["status"] == status) for status in {"done", "started", "planned", "missing"}}
        return CapabilityReport(
            self.capabilities_path,
            len(rows),
            counts["done"],
            counts["started"],
            counts["planned"],
            counts["missing"],
        )

    def list_rows(self) -> List[Dict[str, str]]:
        if not self.capabilities_path.exists():
            return []
        with self.capabilities_path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    @staticmethod
    def _row(spec: CapabilitySpec, state: dict) -> Dict[str, str]:
        return {
            "id": spec.id,
            "family": spec.family,
            "capability": spec.capability,
            "status": spec.status_fn(state),
            "local_support": spec.local_support,
            "next_action": spec.next_action,
            "source": spec.source,
            "updated_at": now_iso(),
        }

    @staticmethod
    def _state(agent: Agent, brain: BrainServer) -> dict:
        deps = dependency_report()
        brain_status = brain.status()
        providers = agent.list_ai_providers()
        strong_model = Path("~/.local/share/gima/models/qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf").expanduser()
        return {
            **deps,
            "brain_running": bool(brain_status.get("running")),
            "teacher_ready": any(row["available"] == "yes" and row["provider"] != "local" for row in providers),
            "tools_configured": bool(agent.config.tools.enabled),
            "audit_ready": agent.memory.audit_path.exists(),
            "eval_ready": (agent.config.resolved_data_dir / "evals" / "results.csv").exists(),
            "strong_model_available": strong_model.exists() or agent.config.model.active_level == "strong",
        }

    def _write_sources(self, rows: Iterable[Dict[str, str]]) -> None:
        seen: set[str] = set()
        lines = [
            "# Gima Capability Sources",
            "",
            "These public sources are used only to map capability categories and next actions.",
            "Gima still requires local tests, permissions, and parent review before enabling risky actions.",
            "",
        ]
        for row in rows:
            source = row["source"]
            if source in seen:
                continue
            seen.add(source)
            lines.append(f"- {source}")
        lines.append("")
        self.sources_path.write_text("\n".join(lines), encoding="utf-8")
