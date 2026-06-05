from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from .agent import Agent
from .brain import BrainServer
from .services import dependency_report


@dataclass(frozen=True)
class ChecklistItem:
    area: str
    target: str
    status: str
    next_action: str


def build_world_checklist(agent: Agent, brain: BrainServer) -> List[ChecklistItem]:
    """Build a practical scorecard for improving Gima toward frontier-assistant quality."""
    deps = dependency_report()
    brain_status = brain.status()
    providers = agent.list_ai_providers()
    active_heart = agent.heart.list_policies("active")
    pending_reviews = agent.memory.list_source_reviews("pending", 500)
    eval_cases = _count_csv_rows(agent.config.resolved_data_dir / "evals" / "cases.csv")
    eval_results = _count_csv_rows(agent.config.resolved_data_dir / "evals" / "results.csv")
    scale_reports = _count_csv_rows(agent.config.resolved_data_dir / "scale" / "scale_reports.csv")

    missing_tools = [name for name, ok in deps.items() if not ok]
    ready_providers = [row["provider"] for row in providers if row["available"] == "yes"]

    return [
        ChecklistItem(
            "Brain",
            "Run a local LLM reliably for terminal and voice conversations.",
            "done" if brain_status["running"] else "needs work",
            "Start the brain with `python3 -m human_ai.gima start` and keep model health checked.",
        ),
        ChecklistItem(
            "Model Quality",
            "Move from a small local model toward stronger reasoning, coding, and conversation.",
            "started" if ready_providers else "needs work",
            "Add larger local GGUF models as hardware allows, then benchmark answers against ChatGPT/Gemini.",
        ),
        ChecklistItem(
            "Voice",
            "Wake word, live microphone, spoken replies, and kill phrase for safe 24/7 use.",
            "done" if deps.get("ffmpeg") and deps.get("whisper-cli") else "needs work",
            "Run `python3 -m human_ai.gima talk --voice`; use the configured end phrase to stop.",
        ),
        ChecklistItem(
            "Vision",
            "Camera capture, person counting, screenshots, OCR, and video frame analysis.",
            "started" if deps.get("ffmpeg") else "needs work",
            "Install any missing vision tools, then test camera and screen commands with scoped permission.",
        ),
        ChecklistItem(
            "Memory",
            "Conversation history plus categorized brain files and searchable source-reviewed knowledge.",
            "started",
            "Review pending sources regularly so useful learning moves from review into active memory.",
        ),
        ChecklistItem(
            "Internet Learning",
            "Learn from public sources with source review, citations, and category-specific brain files.",
            "started",
            "Keep adding research profiles and approve/reject source reviews after checking correctness.",
        ),
        ChecklistItem(
            "Teacher Models",
            "Use other LLMs as teachers without copying hidden instructions or non-human machine payloads.",
            "started" if ready_providers else "needs work",
            "Set provider API keys when available, then run bounded daily learning with human-language storage.",
        ),
        ChecklistItem(
            "Tool Use",
            "Use files, terminal, CSV tools, media tools, and safe allowlisted actions.",
            "done" if not missing_tools else "started",
            "Close optional tool gaps: " + (", ".join(missing_tools) if missing_tools else "none right now."),
        ),
        ChecklistItem(
            "Safety Heart",
            "Keep permanent policies, parent review, scoped permissions, and violation reporting.",
            "done" if len(active_heart) >= 6 else "started",
            "Never add hidden bypasses; improve transparent approvals and reporting instead.",
        ),
        ChecklistItem(
            "Evaluation",
            "Measure Gima with repeatable tests, benchmarks, user ratings, and regression checks.",
            "started" if eval_cases and eval_results else ("needs run" if eval_cases else "needs work"),
            (
                f"Run `python3 -m human_ai.gima eval-run`; current eval cases: {eval_cases}, "
                f"saved results: {eval_results}. Expand toward coding, web, voice, vision, and tool safety."
            ),
        ),
        ChecklistItem(
            "Autonomy",
            "Plan, code, test, summarize, and ask permission only when needed.",
            "started",
            "Add task queues and explicit approval checkpoints for higher-risk actions.",
        ),
        ChecklistItem(
            "Multimodal Creation",
            "Support image, video, audio, and lip-sync planning with consent checks.",
            "started",
            "Connect approved local generators or APIs, then log every generated artifact and consent proof.",
        ),
        ChecklistItem(
            "Scale",
            "Run faster with better hardware, bigger context, and stronger retrieval.",
            "started" if scale_reports else "needs work",
            (
                f"Run `python3 -m human_ai.gima scale-report`; saved scale reports: {scale_reports}. "
                "Use the report before adding larger models, bigger context, or more retrieval data."
            ),
        ),
        ChecklistItem(
            "Product",
            "Make Gima easy to start, stop, debug, update, and understand from the terminal.",
            "started",
            "Add one-command launch, logs, health monitor, and a clean command reference.",
        ),
        ChecklistItem(
            "World Rank",
            "Compete with frontier systems on quality, reliability, safety, latency, and usefulness.",
            "early prototype",
            f"Current realistic rank: personal local prototype. Pending source reviews: {len(pending_reviews)}.",
        ),
    ]


def _count_csv_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(newline="", encoding="utf-8") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def format_world_checklist(items: Iterable[ChecklistItem]) -> str:
    lines = [
        "Gima world-best checklist",
        "Real answer: Gima is not near ChatGPT/Codex yet. It is an early local assistant with useful building blocks.",
        "",
    ]
    for index, item in enumerate(items, 1):
        lines.append(f"{index}. [{item.status}] {item.area}: {item.target}")
        lines.append(f"   Next: {item.next_action}")
    return "\n".join(lines)
