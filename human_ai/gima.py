from __future__ import annotations

import argparse
import getpass
import json
import os
import plistlib
import subprocess
import sys
from pathlib import Path

from .agent import Agent
from .ai_task_map import AITaskMapStore
from .assistant_loop import LocalAssistant
from .brain import BrainServer
from .capabilities import CapabilityStore
from .config import load_config
from .dream import DreamIdea, DreamStore
from .evals import EvalStore
from .frontier_features import FrontierFeatureStore
from .model_levels import ModelLevelManager
from .memory import Record
from .permissions import PermissionManager
from .scale import ScaleReporter
from .secrets import SECRET_ENV_KEYS, configure_teacher_secrets, load_secret_env, secrets_env_path
from .self_update import SelfUpdateManager
from .services import AdvancedVideoSongRenderer, FrontierVideoPlanner, LipSyncPlanner, LocalImageMusicVideoRenderer, LocalMusicVideoRenderer, OpenSourceVideoApiRenderer, VideoQualityEvaluator, dependency_report
from .system_doctor import build_doctor_report, latest_area_agent_supervisor, run_ai_era_requirements_agent, run_area_agent_supervisor, run_daily_improvement_agent, write_daily_improvement_plan, write_own_model_plan
from .world_checklist import build_world_checklist, format_world_checklist
from .vibe_code import VibeCodingAgent
from .web_ui import run_web_ui


DEFAULT_CONFIG = "config.local.json"
DEFAULT_WHISPER_MODEL = "~/.local/share/gima/models/ggml-tiny.bin"


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="gima",
        description="Gima control center for the local personal AI system",
    )
    root.add_argument(
        "--config",
        default=DEFAULT_CONFIG if Path(DEFAULT_CONFIG).exists() else None,
        help="Path to a private Gima config file",
    )
    commands = root.add_subparsers(dest="command", required=True)

    commands.add_parser("start", help="Start Gima's local brain")
    commands.add_parser("stop", help="Stop Gima's local brain")
    commands.add_parser("status", help="Show brain, memory, and tool status")

    web = commands.add_parser("web", help="Run Gima's local dark web chat interface")
    web.add_argument("--host", default="127.0.0.1", help="Bind host. Keep 127.0.0.1 for local-only use.")
    web.add_argument("--port", type=int, default=8787, help="Port for the local web interface")
    web.add_argument("--open", action="store_true", help="Open the interface in the default browser")

    talk = commands.add_parser("talk", help="Talk to Gima in the terminal")
    talk.add_argument("message", nargs="*", help="Typed message. Omit for interactive chat.")
    talk.add_argument("--voice", action="store_true", help="Use microphone input and spoken replies")
    talk.add_argument("--model", default=DEFAULT_WHISPER_MODEL, help="Whisper model for voice mode")
    talk.add_argument("--turns", type=int, default=20, help="Maximum voice turns")
    talk.add_argument("--seconds", type=int, default=8, help="Seconds to listen per voice turn")
    talk.add_argument("--device", default=":0", help="FFmpeg avfoundation audio device")

    remember = commands.add_parser("remember", help="Store one useful memory")
    remember.add_argument("title")
    remember.add_argument("content", nargs="+")
    remember.add_argument("--category", default="personal")
    remember.add_argument("--subcategory", default="note")

    learn = commands.add_parser("learn", help="Learn from a local path or approved public URL")
    learn.add_argument("source")
    learn.add_argument("--category", default="research")

    learn_web = commands.add_parser("learn-web", help="Search the internet and import top public pages")
    learn_web.add_argument("query")
    learn_web.add_argument("--category", default="research")
    learn_web.add_argument("--limit", type=int, default=3)

    learn_language = commands.add_parser("learn-language", help="Learn a configured language topic")
    learn_language.add_argument("language", choices=["sinhala"])

    learn_research = commands.add_parser("learn-research", help="Learn a configured research topic")
    learn_research.add_argument(
        "profile",
        choices=[
            "ai-human-systems",
            "video-generation",
            "veo-style-video-systems",
            "frontier-ai-systems",
            "psychology-systems",
        ],
    )

    search = commands.add_parser("search", help="Search Gima memory")
    search.add_argument("query")
    search.add_argument("--category")
    search.add_argument("--limit", type=int, default=8)

    reviews = commands.add_parser("reviews", help="List source review rows")
    reviews.add_argument("--status", default="pending", help="Parent status filter, or 'all'")
    reviews.add_argument("--limit", type=int, default=20)

    approve = commands.add_parser("approve", help="Approve one learned source review")
    approve.add_argument("review_id")
    approve.add_argument("--notes", default="")

    reject = commands.add_parser("reject", help="Reject one learned source review")
    reject.add_argument("review_id")
    reject.add_argument("--notes", default="")

    teacher = commands.add_parser("teacher", help="Ask a linked teacher model and save the answer for review")
    teacher.add_argument("provider", choices=["chatgpt", "openai", "gemini", "anthropic", "xai", "deepseek", "openrouter"])
    teacher.add_argument("prompt", nargs="+")

    teacher_setup = commands.add_parser("teacher-setup", help="Store private API keys for teacher models")
    teacher_setup.add_argument(
        "--provider",
        action="append",
        choices=["openai", "chatgpt", "gemini", "anthropic", "xai", "deepseek", "openrouter", "all"],
    )
    teacher_setup.add_argument("--force", action="store_true", help="Replace an existing stored key")

    transfer = commands.add_parser("transfer-knowledge", help="Ask teacher models and save knowledge for review")
    transfer.add_argument("prompt", nargs="+")
    transfer.add_argument(
        "--provider",
        choices=["local", "chatgpt", "openai", "gemini", "anthropic", "xai", "deepseek", "openrouter", "both", "all"],
        default="both",
    )

    commands.add_parser("ai-list", help="List AI providers Gima can use")
    commands.add_parser("world-checklist", help="Show Gima's path toward frontier AI quality")

    commands.add_parser("dream-init", help="Create Gima's Dream brain folder and CSV files")

    dream_add = commands.add_parser("dream-add", help="Add a possible-but-unproven Dream theory")
    dream_add.add_argument("title")
    dream_add.add_argument("theory", nargs="+")
    dream_add.add_argument("--why-new", default="")
    dream_add.add_argument("--path", default="", help="Possible path to test the theory")
    dream_add.add_argument("--evidence", default="", help="Evidence needed before trusting it")
    dream_add.add_argument("--risk", default="medium", choices=["low", "medium", "high"])

    dream_list = commands.add_parser("dream-list", help="List recent Dream theories")
    dream_list.add_argument("--limit", type=int, default=20)

    commands.add_parser("eval-init", help="Create Gima's repeatable evaluation CSV files")

    eval_run = commands.add_parser("eval-run", help="Run Gima's repeatable evaluation set")
    eval_run.add_argument("--limit", type=int, default=None)
    eval_run.add_argument("--model", action="store_true", help="Include slower local model chat responses")

    eval_results = commands.add_parser("eval-results", help="Show recent Gima evaluation results")
    eval_results.add_argument("--limit", type=int, default=20)

    commands.add_parser("scale-report", help="Measure Gima scale, storage, eval, and model readiness")

    capabilities_list = commands.add_parser("capabilities-list", help="List Gima's frontier capability registry")
    capabilities_list.add_argument("--status", choices=["done", "started", "planned", "missing", "all"], default="all")
    capabilities_list.add_argument("--limit", type=int, default=100)

    commands.add_parser("capabilities-refresh", help="Refresh Gima's capability registry CSV")

    frontier_features = commands.add_parser(
        "frontier-features-refresh",
        help="Refresh public feature map for ChatGPT, Gemini, Claude, Grok, Codex, and Antigravity-style systems",
    )
    frontier_features.add_argument("--scheduled", action="store_true", help="Run from a future scheduled refresh")

    frontier_features_list = commands.add_parser("frontier-features-list", help="List Gima's frontier provider feature map")
    frontier_features_list.add_argument("--provider", help="Filter by provider, e.g. OpenAI, Google, Anthropic, xAI")
    frontier_features_list.add_argument("--limit", type=int, default=50)

    ai_task_map = commands.add_parser("ai-task-map-refresh", help="Refresh the A-Z worldwide AI task map CSV")
    ai_task_map.add_argument("--offline", action="store_true", help="Write the map without checking public source pages")
    ai_task_map.add_argument("--max-sources", type=int, default=18, help="Maximum public source URLs to check this run")
    ai_task_map.add_argument("--scheduled", action="store_true", help="Run from an installed daily schedule")

    ai_task_list = commands.add_parser("ai-task-map-list", help="List rows from the A-Z AI task map")
    ai_task_list.add_argument("--letter", help="Filter by A-Z letter")
    ai_task_list.add_argument("--status", choices=["started", "planned", "all"], default="all")
    ai_task_list.add_argument("--limit", type=int, default=40)

    ai_task_schedule = commands.add_parser("schedule-ai-task-map-daily", help="Refresh the AI task map every day with launchd")
    ai_task_schedule.add_argument("--hour", type=int, default=1)
    ai_task_schedule.add_argument("--minute", type=int, default=30)
    ai_task_schedule.add_argument("--offline", action="store_true")
    ai_task_schedule.add_argument("--max-sources", type=int, default=18)
    ai_task_schedule.add_argument("--no-load", action="store_true", help="Write the plist but do not load it now")

    lip_sync = commands.add_parser("lip-sync-plan", help="Create a consent-gated lip-sync project plan")
    lip_sync.add_argument("audio", help="MP3 or other local audio file")
    lip_sync.add_argument("--face", required=True, help="Consented face image or video")
    lip_sync.add_argument("--prompt", required=True, help="One natural-language prompt for the desired result")
    lip_sync.add_argument("--consent", action="store_true", help="Confirm rights/consent for the face/person and audio")

    music_video = commands.add_parser("music-video-local", help="Render an MP3/audio file into a local MP4 visualizer")
    music_video.add_argument("audio", help="MP3 or other local audio file")
    music_video.add_argument("--prompt", required=True, help="Natural-language description saved with the project")
    music_video.add_argument("--style", choices=["waveform", "spectrum", "professional"], default="professional")
    music_video.add_argument("--consent", action="store_true", help="Confirm you have rights/consent for the audio")

    image_music_video = commands.add_parser("image-music-video-local", help="Render local images plus audio into an MP4")
    image_music_video.add_argument("audio", help="MP3 or other local audio file")
    image_music_video.add_argument("--image", action="append", required=True, help="Image path, repeatable")
    image_music_video.add_argument("--prompt", required=True, help="Natural-language video direction")
    image_music_video.add_argument("--aspect", choices=["16:9", "9:16", "1:1"], default="16:9")
    image_music_video.add_argument("--max-duration", type=int, default=45)
    image_music_video.add_argument("--consent", action="store_true", help="Confirm rights/consent for the audio and images")

    advanced_video = commands.add_parser("advanced-video-song", help="Render an advanced local video song with scenes, camera moves, emotion, and pitch analysis")
    advanced_video.add_argument("audio", help="MP3 or other local audio file")
    advanced_video.add_argument("--image", action="append", required=True, help="Image path, repeatable")
    advanced_video.add_argument("--prompt", required=True, help="Movie/music-video direction")
    advanced_video.add_argument("--lyrics", default="", help="Optional lyrics for scene/caption planning")
    advanced_video.add_argument("--aspect", choices=["16:9", "9:16", "1:1"], default="16:9")
    advanced_video.add_argument("--max-duration", type=int, default=90)
    advanced_video.add_argument("--consent", action="store_true", help="Confirm rights/consent for the audio, people, and images")

    open_video = commands.add_parser("open-video-api", help="Render video through an open-source ComfyUI API workflow")
    open_video.add_argument("--workflow", required=True, help="ComfyUI workflow exported in API JSON format")
    open_video.add_argument("--prompt", required=True, help="Positive prompt for the workflow")
    open_video.add_argument("--image", help="Optional input image uploaded to ComfyUI")
    open_video.add_argument("--negative-prompt", default="low quality, warped face, extra limbs, flicker, watermark, unreadable text")
    open_video.add_argument("--base-url", default=os.environ.get("GIMA_COMFYUI_URL", "http://127.0.0.1:8188"))
    open_video.add_argument("--width", type=int, default=832)
    open_video.add_argument("--height", type=int, default=480)
    open_video.add_argument("--frames", type=int, default=81)
    open_video.add_argument("--seed", type=int)
    open_video.add_argument("--timeout", type=int, default=1800)
    open_video.add_argument("--consent", action="store_true", help="Confirm rights/consent for prompts, people, images, and source assets")

    video_eval = commands.add_parser("video-eval-local", help="Evaluate a generated MP4 with local Veo-style checks")
    video_eval.add_argument("video", help="Local generated MP4/video path")
    video_eval.add_argument("--manifest", help="Optional generation manifest JSON")

    frontier_video = commands.add_parser("frontier-video-plan", help="Create a Veo/Seedance-style local video plan")
    frontier_video.add_argument("--prompt", required=True, help="Video idea or production goal")
    frontier_video.add_argument("--audio", help="Optional audio file for timing")
    frontier_video.add_argument("--image", action="append", default=[], help="Optional image reference, repeatable")
    frontier_video.add_argument("--target", default="veo_seedance", choices=["veo_seedance", "veo", "seedance", "open_local"])
    frontier_video.add_argument("--duration", type=int, default=8, help="Target seconds for first generated clip")

    daily_learn = commands.add_parser("daily-learn", help="Learn from available AI providers for a bounded time")
    daily_learn.add_argument("--minutes", type=float, default=60)
    daily_learn.add_argument(
        "--provider",
        action="append",
        choices=["local", "chatgpt", "openai", "gemini", "anthropic", "xai", "deepseek", "openrouter", "all"],
    )
    daily_learn.add_argument("--topic", help="Override the configured daily learning topic rotation")
    daily_learn.add_argument("--pause-seconds", type=int, default=None)
    daily_learn.add_argument("--rounds", type=int, default=None, help="Limit rounds, useful for testing")
    daily_learn.add_argument(
        "--scheduled",
        action="store_true",
        help="Run from an installed daily schedule created by schedule-daily-learning",
    )

    schedule = commands.add_parser("schedule-daily-learning", help="Run Gima daily learning every day with launchd")
    schedule.add_argument("--hour", type=int, default=2)
    schedule.add_argument("--minute", type=int, default=0)
    schedule.add_argument("--minutes", type=float, default=60)
    schedule.add_argument(
        "--provider",
        action="append",
        choices=["local", "chatgpt", "openai", "gemini", "anthropic", "xai", "deepseek", "openrouter", "all"],
    )
    schedule.add_argument("--topic")
    schedule.add_argument("--pause-seconds", type=int, default=None)
    schedule.add_argument("--no-load", action="store_true", help="Write the plist but do not load it now")

    self_prepare = commands.add_parser("self-update-prepare", help="Create a backed-up working copy for a feature")
    self_prepare.add_argument("feature", nargs="+")

    commands.add_parser("self-update-list", help="List prepared self-update requests")

    self_ready = commands.add_parser("self-update-ready", help="Mark a working copy ready for parent approval")
    self_ready.add_argument("update_id")
    self_ready.add_argument("--notes", default="")

    self_sync = commands.add_parser("self-update-sync", help="Parent-approved sync from working copy to live Gima")
    self_sync.add_argument("update_id")
    self_sync.add_argument("--password", help="Parent password. Prefer GIMA_PARENT_PASSWORD for scripts.")
    self_sync.add_argument("--force", action="store_true", help="Sync even if live workspace has uncommitted changes")
    self_sync.add_argument("--restart", action="store_true", help="Restart the local brain after syncing")

    vibe_code = commands.add_parser("vibe-code-plan", help="Create an offline copied-workspace coding plan")
    vibe_code.add_argument("feature", nargs="+")
    vibe_code.add_argument("--max-files", type=int, default=10, help="Maximum candidate files to include")

    self_code = commands.add_parser("self-code", help="Implement a feature in an isolated copy and run tests")
    self_code.add_argument("feature", nargs="+")
    self_code.add_argument("--max-files", type=int, default=10, help="Maximum candidate files supplied to the coding engine")
    self_code.add_argument("--timeout", type=int, default=900, help="Maximum coding time in seconds")

    heart_sources = commands.add_parser("heart-sources", help="List external AI policy systems Gima can review")
    heart_sources.add_argument("--password", help="Parent password. Prefer GIMA_PARENT_PASSWORD for scripts.")

    heart = commands.add_parser("heart-list", help="List Gima heart policies")
    heart.add_argument("--status", choices=["active", "pending", "skipped", "all"], default="active")
    heart.add_argument("--password", help="Parent password. Prefer GIMA_PARENT_PASSWORD for scripts.")

    heart_next = commands.add_parser("heart-next", help="Show the next pending heart policy")
    heart_next.add_argument("--password", help="Parent password. Prefer GIMA_PARENT_PASSWORD for scripts.")

    heart_approve = commands.add_parser("heart-approve", help="Approve one pending heart policy")
    heart_approve.add_argument("policy_id")
    heart_approve.add_argument("--notes", default="")
    heart_approve.add_argument("--password", help="Parent password. Prefer GIMA_PARENT_PASSWORD for scripts.")

    heart_skip = commands.add_parser("heart-skip", help="Skip one pending heart policy")
    heart_skip.add_argument("policy_id")
    heart_skip.add_argument("--notes", default="")
    heart_skip.add_argument("--password", help="Parent password. Prefer GIMA_PARENT_PASSWORD for scripts.")

    heart_review = commands.add_parser("heart-review", help="Approve or skip pending heart policies one at a time")
    heart_review.add_argument("--password", help="Parent password. Prefer GIMA_PARENT_PASSWORD for scripts.")

    violation = commands.add_parser("violation-report", help="Email a Gima heart violation report")
    violation.add_argument("reason")
    violation.add_argument("request", nargs="+")
    violation.add_argument("--to", default=None)
    violation.add_argument("--source", default="manual")

    commands.add_parser("doctor", help="Show optional local capabilities")
    commands.add_parser("daily-improvement-plan", help="Write today's Gima improvement plan to continuous/daily_plans")
    commands.add_parser("daily-agent-run", help="Run Gima's daily improvement agent planner")
    commands.add_parser("ai-era-agent-run", help="Run Gima's AI-era requirements minute agent once")
    commands.add_parser("area-agents-run", help="Run all 24/7 area supervisor agents once")
    commands.add_parser("own-model-plan", help="Write a realistic plan for developing Gima's own model layer")

    ai_era_schedule = commands.add_parser("schedule-ai-era-agent-minute", help="Run the AI-era requirements agent every minute in a background user session")
    ai_era_schedule.add_argument("--no-load", action="store_true", help="Write the loop script but do not start it now")

    area_agent_schedule = commands.add_parser("schedule-area-agents-24x7", help="Run all area supervisor agents continuously in a background user session")
    area_agent_schedule.add_argument("--interval", type=int, default=300, help="Seconds between area-agent runs")
    area_agent_schedule.add_argument("--no-load", action="store_true", help="Write the loop script but do not start it now")

    commands.add_parser("model-levels", help="List configured local model levels")

    model_download = commands.add_parser("model-download", help="Download a configured local model level")
    model_download.add_argument("level", choices=["tiny", "fast", "strong"])

    model_use = commands.add_parser("model-use", help="Switch Gima to a configured local model level")
    model_use.add_argument("level", choices=["tiny", "fast", "strong"])
    model_use.add_argument("--restart", action="store_true", help="Restart the local brain after switching")
    return root


def _interactive(agent: Agent) -> None:
    print("Gima is ready. Type /exit to stop.")
    while True:
        try:
            message = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not message:
            continue
        if message in {"/exit", "/quit"}:
            break
        print(f"gima> {agent.chat(message)}")


def _print_rows(rows) -> None:
    if not rows:
        print("No matching memory.")
        return
    for row in rows:
        print(f"[{row['id']}] {row['category']}/{row['subcategory']} - {row['title']}")
        print(row["content"][:500].replace("\n", " "))
        print()


def _print_reviews(rows) -> None:
    if not rows:
        print("No matching source reviews.")
        return
    for row in rows:
        print(f"[{row['id']}] {row['parent_status']} - {row['title']}")
        print(f"source: {row['source']}")
        print(f"record: {row['record_id']} category: {row['category']}/{row['subcategory']}")
        print(row["claim_summary"][:500].replace("\n", " "))
        print()


def _parent_decision(agent: Agent, permissions: PermissionManager, review_id: str, decision: str, notes: str) -> int:
    password = os.environ.get("GIMA_PARENT_PASSWORD") or getpass.getpass("Parent approval password: ")
    if not permissions.verify_parent_password(password):
        print("Parent approval password did not match.", file=sys.stderr)
        return 1
    reviewer = agent.config.parent_approval.reviewer_name
    if not agent.memory.parent_review_decision(review_id, decision, reviewer, notes):
        print(f"Unknown review id: {review_id}", file=sys.stderr)
        return 1
    print(f"{decision.title()} {review_id} as {reviewer}")
    return 0


def _require_parent(agent: Agent, permissions: PermissionManager, password: str | None = None) -> str:
    parent_password = password or os.environ.get("GIMA_PARENT_PASSWORD") or getpass.getpass(
        "Parent approval password: "
    )
    if not permissions.verify_parent_password(parent_password):
        raise PermissionError("Parent approval password did not match")
    return agent.config.parent_approval.reviewer_name


def _print_heart_rows(rows) -> None:
    if not rows:
        print("No matching heart policies.")
        return
    for row in rows:
        print(f"[{row['id']}] {row['status']} - {row['source_system']} - {row['title']}")
        print(row["policy"])
        print(f"source: {row['source_url']}")
        if row.get("notes"):
            print(f"notes: {row['notes']}")
        print()


def _print_heart_sources(agent: Agent) -> None:
    seen: set[str] = set()
    for row in agent.heart.list_policies():
        key = row["source_system"]
        if key in seen or key == "Gima":
            continue
        seen.add(key)
        print(f"- {row['source_system']}: {row['source_url']}")


def _heart_decision(agent: Agent, reviewer: str, policy_id: str, status: str, notes: str) -> int:
    if not agent.heart.decide(policy_id, status, reviewer, notes):
        print(f"Unknown heart policy id: {policy_id}", file=sys.stderr)
        return 1
    print(f"{'Approved' if status == 'active' else 'Skipped'} {policy_id}")
    print(f"Heart policies saved to {agent.heart.active_path}")
    return 0


def _heart_review(agent: Agent, reviewer: str) -> int:
    pending = agent.heart.pending()
    if not pending:
        print("No pending heart policies.")
        return 0
    for row in pending:
        _print_heart_rows([row])
        decision = input("Approve this policy? [yes/no/stop]: ").strip().casefold()
        if decision in {"stop", "s", "quit", "exit"}:
            break
        if decision in {"yes", "y", "approve", "a"}:
            agent.heart.decide(row["id"], "active", reviewer, "interactive approval")
            print(f"Approved {row['id']}")
        else:
            agent.heart.decide(row["id"], "skipped", reviewer, "interactive skip")
            print(f"Skipped {row['id']}")
    print(f"Heart policies saved to {agent.heart.active_path}")
    return 0


def _print_status(agent: Agent, brain: BrainServer, config_path: str | None) -> None:
    status = brain.status()
    report = dependency_report()
    missing = [name for name, ok in report.items() if not ok]
    print(f"Gima config: {config_path or '[default]'}")
    print(f"Workspace: {agent.config.resolved_workspace}")
    print(f"Memory: {agent.config.resolved_data_dir}")
    print(f"Brain: {'running' if status['running'] else 'stopped'}")
    if status["pid"]:
        print(f"Brain pid: {status['pid']}")
    models = (status.get("models") or {}).get("data") or []
    if models:
        print(f"Model: {models[0].get('id', '[unknown]')}")
    print(f"Missing optional tools: {', '.join(missing) if missing else 'none'}")
    doctor = build_doctor_report(agent.config, status)
    print(f"PC AI mode: {doctor['mode']} - {doctor['recommended_model']}")
    print(f"AI strategy: {doctor['strategy']}")


def _teacher_providers(value: list[str] | None) -> list[str] | None:
    if not value:
        return None
    providers: list[str] = []
    for provider in value:
        if provider == "all":
            return None
        providers.append("chatgpt" if provider == "openai" else provider)
    return providers


def _print_ai_providers(agent: Agent) -> None:
    print("AI providers available to Gima:")
    for row in agent.list_ai_providers():
        marker = "ready" if row["available"] == "yes" else "missing"
        print(f"- {row['provider']}: {row['name']} [{marker}] {row['detail']}")
    print(f"Teacher secrets file: {secrets_env_path(agent.config.resolved_workspace)}")


def _print_dream_ideas(rows) -> None:
    if not rows:
        print("No Dream ideas yet.")
        return
    for row in rows:
        print(f"[{row['id']}] {row['status']} / {row['parent_status']} / risk={row['risk_level']}")
        print(row["title"])
        print(row["theory"][:700].replace("\n", " "))
        if row.get("possible_path"):
            print(f"path: {row['possible_path']}")
        if row.get("evidence_needed"):
            print(f"evidence: {row['evidence_needed']}")
        print()


def _print_eval_results(rows) -> None:
    if not rows:
        print("No eval results yet.")
        return
    for row in rows:
        marker = "PASS" if row["passed"] == "yes" else "FAIL"
        print(f"[{marker}] {row['category']} / {row['mode']} / {row['actual_action']}")
        print(f"prompt: {row['prompt']}")
        print(f"expected text: {row['expected_contains'] or '[none]'}")
        if row.get("expected_action"):
            print(f"expected action: {row['expected_action']}")
        print(f"actual: {row['actual'][:500].replace(chr(10), ' ')}")
        print()


def _print_model_levels(manager: ModelLevelManager, active_level: str) -> None:
    for level in manager.levels():
        marker = "active" if level.level == active_level else "ready" if level.available else "missing"
        print(f"- {level.level}: {level.name} [{marker}]")
        print(f"  model: {level.model}")
        print(f"  path: {level.model_path}")
        print(f"  context: {level.context_size}")
        print(f"  about: {level.description}")
        if level.source:
            print(f"  source: {level.source}")


def _print_capabilities(rows, status: str, limit: int) -> None:
    shown = 0
    for row in rows:
        if status != "all" and row["status"] != status:
            continue
        print(f"[{row['status']}] {row['family']} - {row['capability']}")
        print(f"support: {row['local_support']}")
        print(f"next: {row['next_action']}")
        print(f"source: {row['source']}")
        print()
        shown += 1
        if shown >= limit:
            break
    if shown == 0:
        print("No matching capabilities.")


def _print_frontier_features(rows: list[dict[str, str]]) -> None:
    if not rows:
        print("No frontier feature rows.")
        return
    for row in rows:
        print(f"[{row['gima_local_status']}] {row['provider']} / {row['system']} - {row['feature']}")
        print(f"detail: {row['public_technical_detail']}")
        print(f"gima: {row['gima_implementation']}")
        print(f"needs: {row['needed_components']}")
        print(f"sources: {row['public_sources']}")
        print()


def _print_ai_task_map(rows: list[dict[str, str]]) -> None:
    if not rows:
        print("No AI task map rows.")
        return
    for row in rows:
        print(f"[{row['letter']}] {row['gima_status']} - {row['family']} / {row['task']}")
        print(row["description"])
        print(f"module: {row['gima_module']}")
        print(f"providers: {row['provider_examples']}")
        print(f"sources: {row['public_sources']}")
        print(f"review: internet={row['internet_review']} user={row['user_review']} parent={row['parent_review']}")
        print()


def _teacher_setup_providers(values: list[str] | None) -> list[str]:
    if not values or "all" in values:
        return ["openai", "gemini", "anthropic", "openrouter"]
    providers: list[str] = []
    for value in values:
        provider = "openai" if value == "chatgpt" else value
        if provider not in providers:
            providers.append(provider)
    return providers


def _schedule_daily_learning(args, config_path: str | None, config) -> Path:
    launch_dir = Path.home() / "Library" / "LaunchAgents"
    launch_dir.mkdir(parents=True, exist_ok=True)
    label = "com.gima.daily-ai-learning"
    plist_path = launch_dir / f"{label}.plist"
    log_dir = config.resolved_data_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    command: list[str] = [
        "python3",
        "-m",
        "human_ai.gima",
    ]
    if config_path:
        command.extend(["--config", str(Path(config_path).expanduser().resolve())])
    command.extend(["daily-learn", "--minutes", str(args.minutes), "--scheduled"])
    for provider in args.provider or []:
        command.extend(["--provider", provider])
    if args.topic:
        command.extend(["--topic", args.topic])
    if args.pause_seconds is not None:
        command.extend(["--pause-seconds", str(args.pause_seconds)])
    shell_command = (
        "source /etc/zprofile 2>/dev/null || true; "
        "source ~/.zprofile 2>/dev/null || true; "
        "source ~/.zshrc 2>/dev/null || true; "
        f"source {str(secrets_env_path(config.resolved_workspace))!r} 2>/dev/null || true; "
        f"cd {str(config.resolved_workspace)!r} && "
        + " ".join(_shell_quote(part) for part in command)
    )
    plist = {
        "Label": label,
        "ProgramArguments": ["/bin/zsh", "-lc", shell_command],
        "StartCalendarInterval": {"Hour": args.hour, "Minute": args.minute},
        "StandardOutPath": str(log_dir / "daily_ai_learning.out.log"),
        "StandardErrorPath": str(log_dir / "daily_ai_learning.err.log"),
        "WorkingDirectory": str(config.resolved_workspace),
    }
    with plist_path.open("wb") as handle:
        plistlib.dump(plist, handle)
    if not args.no_load:
        subprocess.run(["launchctl", "unload", "-w", str(plist_path)], check=False, capture_output=True)
        subprocess.run(["launchctl", "load", "-w", str(plist_path)], check=True)
    return plist_path


def _schedule_ai_task_map_daily(args, config_path: str | None, config) -> Path:
    launch_dir = Path.home() / "Library" / "LaunchAgents"
    launch_dir.mkdir(parents=True, exist_ok=True)
    label = "com.gima.daily-ai-task-map"
    plist_path = launch_dir / f"{label}.plist"
    log_dir = config.resolved_data_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    command: list[str] = ["python3", "-m", "human_ai.gima"]
    if config_path:
        command.extend(["--config", str(Path(config_path).expanduser().resolve())])
    command.extend(["ai-task-map-refresh", "--scheduled", "--max-sources", str(args.max_sources)])
    if args.offline:
        command.append("--offline")
    shell_command = (
        "source /etc/zprofile 2>/dev/null || true; "
        "source ~/.zprofile 2>/dev/null || true; "
        "source ~/.zshrc 2>/dev/null || true; "
        f"export PYTHONPATH={_shell_quote(str(config.resolved_workspace))}:$PYTHONPATH; "
        f"cd {str(config.resolved_workspace)!r} && "
        + " ".join(_shell_quote(part) for part in command)
    )
    plist = {
        "Label": label,
        "ProgramArguments": ["/bin/zsh", "-lc", shell_command],
        "StartCalendarInterval": {"Hour": args.hour, "Minute": args.minute},
        "StandardOutPath": str(log_dir / "daily_ai_task_map.out.log"),
        "StandardErrorPath": str(log_dir / "daily_ai_task_map.err.log"),
        "WorkingDirectory": str(config.resolved_workspace),
    }
    with plist_path.open("wb") as handle:
        plistlib.dump(plist, handle)
    if not args.no_load:
        subprocess.run(["launchctl", "unload", "-w", str(plist_path)], check=False, capture_output=True)
        subprocess.run(["launchctl", "load", "-w", str(plist_path)], check=True)
    return plist_path


def _schedule_ai_era_agent_minute(args, config_path: str | None, config) -> Path:
    label = "com.gima.ai-era-agent-minute"
    plist_path = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"
    log_dir = config.resolved_data_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    loop_path = config.resolved_data_dir / "run_ai_era_agent_minute_loop.sh"
    loop_path.write_text(
        "\n".join(
            [
                "#!/bin/zsh",
                "source /etc/zprofile 2>/dev/null || true",
                "source ~/.zprofile 2>/dev/null || true",
                "source ~/.zshrc 2>/dev/null || true",
                f"cd {_shell_quote(str(config.resolved_workspace))} || exit 1",
                "while true; do",
                (
                    "  PYTHONPYCACHEPREFIX=/tmp/gima-pycache python3 "
                    f"{_shell_quote(str(config.resolved_workspace / 'scripts' / 'gima_ai_era_agent_minute.py'))} "
                    f">> {_shell_quote(str(log_dir / 'ai_era_agent_minute.out.log'))} "
                    f"2>> {_shell_quote(str(log_dir / 'ai_era_agent_minute.err.log'))}"
                ),
                "  sleep 60",
                "done",
                "",
            ]
        ),
        encoding="utf-8",
    )
    loop_path.chmod(0o755)
    if not args.no_load:
        subprocess.run(["launchctl", "unload", "-w", str(plist_path)], check=False, capture_output=True)
        subprocess.run(["launchctl", "remove", label], check=False, capture_output=True)
        subprocess.run(["/usr/bin/screen", "-S", "gima-ai-era-minute", "-X", "quit"], check=False, capture_output=True)
        subprocess.run(["/usr/bin/screen", "-dmS", "gima-ai-era-minute", "/bin/zsh", "-lc", str(loop_path)], check=True)
    return loop_path


def _schedule_area_agents_24x7(args, config_path: str | None, config) -> Path:
    label = "com.gima.area-agents"
    plist_path = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"
    interval = max(60, int(args.interval))
    log_dir = config.resolved_data_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    loop_path = config.resolved_data_dir / "run_area_agents_24x7_loop.sh"
    loop_path.write_text(
        "\n".join(
            [
                "#!/bin/zsh",
                "source /etc/zprofile 2>/dev/null || true",
                "source ~/.zprofile 2>/dev/null || true",
                "source ~/.zshrc 2>/dev/null || true",
                f"cd {_shell_quote(str(config.resolved_workspace))} || exit 1",
                "while true; do",
                (
                    "  PYTHONPYCACHEPREFIX=/tmp/gima-pycache python3 "
                    f"{_shell_quote(str(config.resolved_workspace / 'scripts' / 'gima_area_agents_24x7.py'))} "
                    f">> {_shell_quote(str(log_dir / 'area_agents_24x7.out.log'))} "
                    f"2>> {_shell_quote(str(log_dir / 'area_agents_24x7.err.log'))}"
                ),
                f"  sleep {interval}",
                "done",
                "",
            ]
        ),
        encoding="utf-8",
    )
    loop_path.chmod(0o755)
    if not args.no_load:
        subprocess.run(["launchctl", "unload", "-w", str(plist_path)], check=False, capture_output=True)
        subprocess.run(["launchctl", "remove", label], check=False, capture_output=True)
        subprocess.run(["/usr/bin/screen", "-S", "gima-area-agents", "-X", "quit"], check=False, capture_output=True)
        subprocess.run(["/usr/bin/screen", "-dmS", "gima-area-agents", "/bin/zsh", "-lc", str(loop_path)], check=True)
    return loop_path


def _print_self_updates(rows) -> None:
    if not rows:
        print("No self-update requests.")
        return
    for row in rows:
        print(f"[{row['id']}] {row['status']} - {row['feature']}")
        print(f"working copy: {row['working_copy']}")
        print(f"backup: {row['backup_path']}")
        if row.get("ready_notes"):
            print(f"notes: {row['ready_notes']}")
        print()


def _shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    config = load_config(args.config)
    load_secret_env(config.resolved_workspace)
    agent = Agent(config)
    brain = BrainServer(config, agent.memory)
    capabilities = CapabilityStore(config.resolved_data_dir)
    ai_task_map = AITaskMapStore(config.resolved_data_dir)
    dreams = DreamStore(config.resolved_data_dir)
    evals = EvalStore(config.resolved_data_dir)
    scale = ScaleReporter(config)
    model_levels = ModelLevelManager(config, args.config)
    permissions = PermissionManager(config, agent.memory)
    self_updates = SelfUpdateManager(config.resolved_workspace, config.resolved_data_dir)
    try:
        if args.command == "start":
            pid = brain.start()
            print(f"Gima brain is running at {config.model.base_url} with pid {pid}")
        elif args.command == "stop":
            brain.stop()
            print("Gima brain stopped.")
        elif args.command == "status":
            _print_status(agent, brain, args.config)
        elif args.command == "web":
            run_web_ui(config, agent, brain, args.host, args.port, args.open)
        elif args.command == "doctor":
            print(json.dumps(build_doctor_report(config, brain.status()), indent=2))
        elif args.command == "daily-improvement-plan":
            path = write_daily_improvement_plan(config, brain.status())
            print(f"Daily improvement plan saved: {path}")
            print(f"Markdown: {path.with_suffix('.md')}")
        elif args.command == "daily-agent-run":
            run = run_daily_improvement_agent(config, brain.status())
            print(f"Daily agent run saved: {run['run_path']}")
            print(f"Plan: {run['plan_markdown_path']}")
            print(f"Today priority: {run['today_priority']}")
            print(f"Next command: {run['next_command']}")
        elif args.command == "ai-era-agent-run":
            run = run_ai_era_requirements_agent(config, brain.status())
            print(f"AI-era agent updated: {run['latest_path']}")
            print(f"Run: {run['run_path']}")
            print(f"Next update: {run['next_update']}")
        elif args.command == "area-agents-run":
            run = run_area_agent_supervisor(config, brain.status())
            print(f"Area agents updated: {run['latest_path']}")
            print(f"Run: {run['run_path']}")
            print(f"Areas: {len(run['areas'])}")
            print(f"Needs attention: {run['needs_attention_count']}")
            print(f"Next action: {run['next_action']}")
        elif args.command == "own-model-plan":
            path = write_own_model_plan(config, brain.status())
            print(f"Own model plan saved: {path}")
            print(f"Markdown: {path.with_suffix('.md')}")
        elif args.command == "schedule-ai-era-agent-minute":
            path = _schedule_ai_era_agent_minute(args, args.config, config)
            status = "installed" if not args.no_load else "written"
            print(f"AI-era minute agent schedule {status}: {path}")
        elif args.command == "schedule-area-agents-24x7":
            path = _schedule_area_agents_24x7(args, args.config, config)
            status = "installed" if not args.no_load else "written"
            print(f"Area agents 24/7 schedule {status}: {path}")
        elif args.command == "model-levels":
            _print_model_levels(model_levels, config.model.active_level)
        elif args.command == "model-download":
            paths = model_levels.download(args.level)
            for path in paths:
                print(f"Ready: {path}")
        elif args.command == "model-use":
            values = model_levels.apply_level(args.level)
            print(f"Gima model level set to {args.level}")
            print(f"Model: {values['model']}")
            print(f"Model path: {values['model_path']}")
            print(f"Context size: {values['context_size']}")
            if args.restart:
                brain.stop()
                pid = brain.start()
                print(f"Gima brain restarted with pid {pid}")
        elif args.command == "talk":
            if args.voice:
                return LocalAssistant(agent).run_conversation(
                    Path(args.model),
                    command_seconds=args.seconds,
                    conversation_turns=args.turns,
                    device=args.device,
                )
            message = " ".join(args.message).strip()
            if message:
                print(agent.chat(message))
            else:
                _interactive(agent)
        elif args.command == "remember":
            record_id = agent.memory.add(
                Record(
                    category=args.category,
                    subcategory=args.subcategory,
                    title=args.title,
                    content=" ".join(args.content),
                    source="gima remember",
                )
            )
            print(f"Remembered as {record_id}")
        elif args.command == "learn":
            source = args.source
            if source.startswith(("http://", "https://")):
                permissions.require("web")
                print(f"Imported for review as {agent.import_web(source, args.category)}")
            else:
                permissions.require("files")
                print(f"Indexed {agent.ingest(Path(source))} new chunks")
        elif args.command == "learn-web":
            permissions.require("web")
            imported = agent.learn_web(args.query, args.category, args.limit)
            if not imported:
                print("No public pages were imported. Try a direct URL with gima learn.")
            for url, record_id in imported:
                print(f"Imported {url} as {record_id}")
        elif args.command == "learn-language":
            permissions.require("web")
            path = agent.learn_language(args.language)
            print(f"Learned {args.language} and saved knowledge to {path}")
        elif args.command == "learn-research":
            permissions.require("web")
            path = agent.learn_research_profile(args.profile)
            print(f"Learned {args.profile} research and saved knowledge to {path}")
        elif args.command == "search":
            _print_rows(agent.search(args.query, args.category, args.limit))
        elif args.command == "reviews":
            status = None if args.status == "all" else args.status
            _print_reviews(agent.memory.list_source_reviews(status, args.limit))
        elif args.command == "approve":
            return _parent_decision(agent, permissions, args.review_id, "approved", args.notes)
        elif args.command == "reject":
            return _parent_decision(agent, permissions, args.review_id, "rejected", args.notes)
        elif args.command == "teacher":
            permissions.require("web")
            answer = agent.ask_teacher(args.provider, " ".join(args.prompt))
            print(answer)
        elif args.command == "teacher-setup":
            providers = _teacher_setup_providers(args.provider)
            path = configure_teacher_secrets(config.resolved_workspace, providers, args.force)
            configured = ", ".join(SECRET_ENV_KEYS[provider] for provider in providers)
            print(f"Stored teacher secret setting(s): {configured}")
            print(f"Private secrets file: {path}")
        elif args.command == "transfer-knowledge":
            permissions.require("web")
            providers = ["chatgpt", "gemini"] if args.provider == "both" else (_teacher_providers([args.provider]) or ["local", "chatgpt", "gemini"])
            results = agent.transfer_teacher_knowledge(" ".join(args.prompt), providers)
            for provider, answer in results:
                print(f"## {provider}")
                print(answer)
                print()
        elif args.command == "ai-list":
            _print_ai_providers(agent)
        elif args.command == "world-checklist":
            print(format_world_checklist(build_world_checklist(agent, brain)))
        elif args.command == "dream-init":
            dreams.initialize()
            print(f"Dream folder ready: {dreams.root}")
            print(f"Ideas CSV: {dreams.ideas_path}")
            print(f"Daily questions CSV: {dreams.questions_path}")
        elif args.command == "dream-add":
            idea_id = dreams.add_idea(
                DreamIdea(
                    title=args.title,
                    theory=" ".join(args.theory),
                    why_it_might_be_new=args.why_new,
                    possible_path=args.path,
                    evidence_needed=args.evidence,
                    risk_level=args.risk,
                )
            )
            print(f"Dream idea saved as {idea_id}")
            print(f"Dream folder: {dreams.root}")
        elif args.command == "dream-list":
            _print_dream_ideas(dreams.list_ideas(args.limit))
        elif args.command == "eval-init":
            evals.initialize()
            print(f"Eval folder ready: {evals.root}")
            print(f"Cases CSV: {evals.cases_path}")
            print(f"Results CSV: {evals.results_path}")
        elif args.command == "eval-run":
            summary = evals.run(agent, args.limit, use_model=args.model)
            print(f"Eval run: {summary.run_id}")
            print(f"Cases: {summary.passed_cases}/{summary.total_cases} passed")
            print(f"Score: {summary.score:.2f}/{summary.max_score:.2f} ({summary.percent:.2f}%)")
            print(f"Results CSV: {summary.results_path}")
        elif args.command == "eval-results":
            _print_eval_results(evals.latest_results(args.limit))
        elif args.command == "scale-report":
            report = scale.collect()
            print(f"Scale report saved: {report.path}")
            print(f"Data size: {report.data_size_mb:.2f} MB")
            print(f"Free disk: {report.free_disk_gb:.2f} GB")
            print(f"Knowledge rows: {report.knowledge_rows}")
            print(f"Conversation rows: {report.conversation_rows}")
            print(f"Eval results: {report.eval_results}")
            print(f"Recommendation: {report.recommendation}")
        elif args.command == "capabilities-refresh":
            report = capabilities.build(agent, brain)
            print(f"Capabilities saved: {report.path}")
            print(f"Total: {report.total}")
            print(f"Done: {report.done}")
            print(f"Started: {report.started}")
            print(f"Planned: {report.planned}")
            print(f"Missing: {report.missing}")
        elif args.command == "capabilities-list":
            if not capabilities.capabilities_path.exists():
                capabilities.build(agent, brain)
            _print_capabilities(capabilities.list_rows(), args.status, args.limit)
        elif args.command == "frontier-features-refresh":
            store = FrontierFeatureStore(config.resolved_data_dir)
            report = store.refresh(agent)
            print(f"Frontier feature map saved: {report.csv_path}")
            print(f"Markdown: {report.md_path}")
            print(f"Rows: {report.rows}")
            print(f"Memory record: {report.memory_record_id}")
        elif args.command == "frontier-features-list":
            store = FrontierFeatureStore(config.resolved_data_dir)
            if not store.csv_path.exists():
                store.refresh(agent)
            _print_frontier_features(store.list_rows(provider=args.provider, limit=args.limit))
        elif args.command == "ai-task-map-refresh":
            if not args.offline and not args.scheduled:
                permissions.require("web")
            report = ai_task_map.refresh(
                agent,
                fetch_public_sources=not args.offline,
                max_sources=args.max_sources,
            )
            print(f"AI task map saved: {report.path}")
            print(f"Rows: {report.total}")
            print(f"Checked public sources: {report.checked_sources}")
            print(f"Failed public sources: {report.failed_sources}")
            print(f"Memory record: {report.memory_record_id}")
        elif args.command == "ai-task-map-list":
            if not ai_task_map.path.exists():
                ai_task_map.refresh(agent, fetch_public_sources=False)
            _print_ai_task_map(ai_task_map.list_rows(letter=args.letter, status=args.status, limit=args.limit))
        elif args.command == "schedule-ai-task-map-daily":
            path = _schedule_ai_task_map_daily(args, args.config, config)
            status = "installed" if not args.no_load else "written"
            print(f"Daily AI task map schedule {status}: {path}")
        elif args.command == "lip-sync-plan":
            permissions.require("files")
            project = LipSyncPlanner(config.resolved_hands_out_dir / "lip_sync").create_project(
                Path(args.audio),
                Path(args.face),
                args.prompt,
                consent=args.consent,
            )
            record_id = agent.memory.add(
                Record(
                    category="video",
                    subcategory="lip_sync_plan",
                    kind="generation_plan",
                    title=f"Lip-sync plan: {Path(args.audio).name}",
                    content=project.manifest_path.read_text(encoding="utf-8"),
                    source=str(project.manifest_path),
                    media_path=str(project.project_dir),
                    status="review",
                )
            )
            print(f"Created lip-sync project: {project.project_dir}")
            print(f"Manifest: {project.manifest_path}")
            print(f"Timing plan: {project.timing_path}")
            print(f"Backend plan: {project.backend_path}")
            print(f"Accuracy rubric: {project.eval_path}")
            print(f"Stored plan as {record_id}")
        elif args.command == "music-video-local":
            permissions.require("files")
            project = LocalMusicVideoRenderer(config.resolved_hands_out_dir / "music_video").render(
                Path(args.audio),
                args.prompt,
                style=args.style,
                consent=args.consent,
            )
            record_id = agent.memory.add(
                Record(
                    category="video",
                    subcategory="local_music_video",
                    kind="generated_media",
                    title=f"Local music video: {Path(args.audio).name}",
                    content=project.manifest_path.read_text(encoding="utf-8"),
                    source=str(project.manifest_path),
                    media_path=str(project.output_path),
                    status="review",
                )
            )
            print(f"Rendered local music video: {project.output_path}")
            print(f"Manifest: {project.manifest_path}")
            if project.script_path:
                print(f"Video script: {project.script_path}")
            if project.prompt_pack_path:
                print(f"Prompt pack: {project.prompt_pack_path}")
            print(f"Stored render as {record_id}")
        elif args.command == "image-music-video-local":
            permissions.require("files")
            project = LocalImageMusicVideoRenderer(config.resolved_hands_out_dir / "image_music_video").render(
                Path(args.audio),
                [Path(image) for image in args.image],
                args.prompt,
                aspect=args.aspect,
                max_duration_seconds=args.max_duration,
                consent=args.consent,
            )
            record_id = agent.memory.add(
                Record(
                    category="video",
                    subcategory="image_music_video",
                    kind="generated_media",
                    title=f"Image music video: {Path(args.audio).name}",
                    content=project.manifest_path.read_text(encoding="utf-8"),
                    source=str(project.manifest_path),
                    media_path=str(project.output_path),
                    status="review",
                )
            )
            print(f"Rendered image music video: {project.output_path}")
            print(f"Manifest: {project.manifest_path}")
            print(f"Stored render as {record_id}")
        elif args.command == "advanced-video-song":
            permissions.require("files")
            project = AdvancedVideoSongRenderer(config.resolved_hands_out_dir / "advanced_video_song").render(
                Path(args.audio),
                [Path(image) for image in args.image],
                args.prompt,
                lyrics=args.lyrics,
                aspect=args.aspect,
                max_duration_seconds=args.max_duration,
                consent=args.consent,
            )
            record_id = agent.memory.add(
                Record(
                    category="video",
                    subcategory="advanced_video_song",
                    kind="generated_media",
                    title=f"Advanced video song: {Path(args.audio).name}",
                    content=project.manifest_path.read_text(encoding="utf-8"),
                    source=str(project.manifest_path),
                    media_path=str(project.output_path),
                    status="review",
                )
            )
            print(f"Rendered advanced video song: {project.output_path}")
            print(f"Manifest: {project.manifest_path}")
            print(f"Storyboard: {project.storyboard_path}")
            print(f"Audio analysis: {project.audio_analysis_path}")
            print(f"Prompt pack: {project.prompt_pack_path}")
            print(f"Stored render as {record_id}")
        elif args.command == "open-video-api":
            permissions.require("files")
            project = OpenSourceVideoApiRenderer(
                config.resolved_hands_out_dir / "open_video_api",
                base_url=args.base_url,
            ).render(
                Path(args.workflow),
                args.prompt,
                image=Path(args.image) if args.image else None,
                negative_prompt=args.negative_prompt,
                width=args.width,
                height=args.height,
                frames=args.frames,
                seed=args.seed,
                timeout_seconds=args.timeout,
                consent=args.consent,
            )
            record_id = agent.memory.add(
                Record(
                    category="video",
                    subcategory="open_source_video_api",
                    kind="generated_media",
                    title=f"Open-source video API render: {args.prompt[:80]}",
                    content=project.manifest_path.read_text(encoding="utf-8"),
                    source=str(project.manifest_path),
                    media_path=str(project.output_path),
                    status="review",
                )
            )
            print(f"Rendered open-source video API output: {project.output_path}")
            print(f"Manifest: {project.manifest_path}")
            print(f"Workflow: {project.workflow_path}")
            print(f"Stored render as {record_id}")
        elif args.command == "video-eval-local":
            permissions.require("files")
            result = VideoQualityEvaluator(config.resolved_data_dir / "evals" / "video").evaluate(
                Path(args.video),
                Path(args.manifest) if args.manifest else None,
            )
            record_id = agent.memory.add(
                Record(
                    category="eval",
                    subcategory="video_generation",
                    kind="video_eval",
                    title=f"Video eval: {Path(args.video).name}",
                    content=result.report_path.read_text(encoding="utf-8"),
                    source=str(result.report_path),
                    media_path=str(result.video_path),
                    status="review",
                )
            )
            print(f"Video eval score: {result.score:.2f}/1.00")
            print(f"Report: {result.report_path}")
            print(f"Stored eval as {record_id}")
        elif args.command == "frontier-video-plan":
            permissions.require("files")
            project = FrontierVideoPlanner(config.resolved_hands_out_dir / "frontier_video").plan(
                args.prompt,
                audio=Path(args.audio) if args.audio else None,
                images=[Path(image) for image in args.image],
                target=args.target,
                duration_seconds=args.duration,
            )
            record_id = agent.memory.add(
                Record(
                    category="video",
                    subcategory="frontier_video_plan",
                    kind="generation_plan",
                    title=f"Frontier video plan: {args.prompt[:80]}",
                    content=project.manifest_path.read_text(encoding="utf-8"),
                    source=str(project.manifest_path),
                    media_path=str(project.project_dir),
                    status="review",
                )
            )
            print(f"Created frontier video plan: {project.project_dir}")
            print(f"Manifest: {project.manifest_path}")
            print(f"Prompt ladder: {project.prompt_ladder_path}")
            print(f"Backend report: {project.backend_report_path}")
            print(f"Eval rubric: {project.eval_rubric_path}")
            print(f"Stored plan as {record_id}")
        elif args.command == "daily-learn":
            if not args.scheduled:
                permissions.require("web")
            providers = _teacher_providers(args.provider)
            results = agent.daily_teacher_learning(
                minutes=args.minutes,
                providers=providers,
                topic=args.topic,
                pause_seconds=args.pause_seconds,
                max_rounds=args.rounds,
            )
            for provider, topic, answer in results:
                print(f"## {provider} | {topic}")
                print(answer[:1200])
                print()
            print(f"Daily learning saved {len(results)} result(s).")
        elif args.command == "schedule-daily-learning":
            path = _schedule_daily_learning(args, args.config, config)
            status = "installed" if not args.no_load else "written"
            print(f"Daily AI learning schedule {status}: {path}")
        elif args.command == "self-update-prepare":
            request = self_updates.prepare(" ".join(args.feature))
            print(f"Prepared self-update {request.update_id}")
            print(f"Backup: {request.backup_path}")
            print(f"Working copy: {request.working_copy}")
            print(f"Plan: {request.plan_path}")
            print("Edit/test the working copy, then run self-update-ready.")
        elif args.command == "self-update-list":
            _print_self_updates(self_updates.list_requests())
        elif args.command == "self-update-ready":
            row = self_updates.mark_ready(args.update_id, args.notes)
            print(f"Self-update {row['id']} is ready for parent approval.")
            print(f"Working copy: {row['working_copy']}")
        elif args.command == "self-update-sync":
            reviewer = _require_parent(agent, permissions, args.password)
            row = self_updates.sync(args.update_id, reviewer, args.force)
            print(f"Synced self-update {row['id']} as {reviewer}")
            print(f"Pre-sync backup: {row['sync_backup_path']}")
            if args.restart:
                brain.stop()
                pid = brain.start()
                print(f"Gima brain restarted with pid {pid}")
        elif args.command == "vibe-code-plan":
            permissions.require("files")
            plan = VibeCodingAgent(config.resolved_workspace, config.resolved_data_dir, agent.memory).plan(
                " ".join(args.feature),
                max_files=args.max_files,
            )
            print(f"Prepared offline vibe coding update {plan.update_request.update_id}")
            print(f"Working copy: {plan.update_request.working_copy}")
            print(f"Plan: {plan.plan_path}")
            print(f"Patch skeleton: {plan.patch_skeleton_path}")
            print(f"Snapshot: {plan.snapshot_path}")
            print(f"Stored plan as {plan.record_id}")
            if plan.candidate_files:
                print("Candidate files:")
                for file in plan.candidate_files:
                    print(f"- {file.path} score={file.score} reason={file.reason}")
            print("After editing/testing the working copy, run self-update-ready.")
        elif args.command == "self-code":
            permissions.require("files")
            execution = VibeCodingAgent(config.resolved_workspace, config.resolved_data_dir, agent.memory).implement(
                " ".join(args.feature),
                max_files=args.max_files,
                timeout_seconds=args.timeout,
            )
            print(f"Self-coding update {execution.plan.update_request.update_id}: {execution.status}")
            print(f"Working copy: {execution.plan.update_request.working_copy}")
            print(f"Changed files: {len(execution.changed_files)}")
            for path in execution.changed_files:
                print(f"- {path}")
            print(f"Patch: {execution.patch_path}")
            print(f"Coding log: {execution.coding_log_path}")
            print(f"Tests: {'passed' if execution.tests_passed else 'failed'} ({execution.test_log_path})")
            print("Review the copy, then mark it ready and use parent-approved sync.")
        elif args.command == "heart-sources":
            _require_parent(agent, permissions, args.password)
            _print_heart_sources(agent)
        elif args.command == "heart-list":
            _require_parent(agent, permissions, args.password)
            status = None if args.status == "all" else args.status
            _print_heart_rows(agent.heart.list_policies(status))
        elif args.command == "heart-next":
            _require_parent(agent, permissions, args.password)
            _print_heart_rows(agent.heart.pending()[:1])
        elif args.command == "heart-approve":
            reviewer = _require_parent(agent, permissions, args.password)
            return _heart_decision(agent, reviewer, args.policy_id, "active", args.notes)
        elif args.command == "heart-skip":
            reviewer = _require_parent(agent, permissions, args.password)
            return _heart_decision(agent, reviewer, args.policy_id, "skipped", args.notes)
        elif args.command == "heart-review":
            reviewer = _require_parent(agent, permissions, args.password)
            return _heart_review(agent, reviewer)
        elif args.command == "violation-report":
            recipient = args.to or config.violations.email_to
            report = agent.violations.report(recipient, args.reason, " ".join(args.request), args.source)
            print(f"Sent violation report to {report.recipient}: {report.report_path}")
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
