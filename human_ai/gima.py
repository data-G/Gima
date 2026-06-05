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
from .assistant_loop import LocalAssistant
from .brain import BrainServer
from .config import load_config
from .dream import DreamIdea, DreamStore
from .evals import EvalStore
from .model_levels import ModelLevelManager
from .memory import Record
from .permissions import PermissionManager
from .scale import ScaleReporter
from .secrets import SECRET_ENV_KEYS, configure_teacher_secrets, load_secret_env, secrets_env_path
from .self_update import SelfUpdateManager
from .services import dependency_report
from .world_checklist import build_world_checklist, format_world_checklist


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
    learn_research.add_argument("profile", choices=["ai-human-systems", "video-generation", "frontier-ai-systems"])

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

    teacher = commands.add_parser("teacher", help="Ask ChatGPT/OpenAI or Gemini and save the answer for review")
    teacher.add_argument("provider", choices=["chatgpt", "openai", "gemini"])
    teacher.add_argument("prompt", nargs="+")

    teacher_setup = commands.add_parser("teacher-setup", help="Store private API keys for teacher models")
    teacher_setup.add_argument("--provider", action="append", choices=["openai", "chatgpt", "gemini", "all"])
    teacher_setup.add_argument("--force", action="store_true", help="Replace an existing stored key")

    transfer = commands.add_parser("transfer-knowledge", help="Ask teacher models and save knowledge for review")
    transfer.add_argument("prompt", nargs="+")
    transfer.add_argument(
        "--provider",
        choices=["local", "chatgpt", "openai", "gemini", "both", "all"],
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

    daily_learn = commands.add_parser("daily-learn", help="Learn from available AI providers for a bounded time")
    daily_learn.add_argument("--minutes", type=float, default=60)
    daily_learn.add_argument("--provider", action="append", choices=["local", "chatgpt", "openai", "gemini", "all"])
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
    schedule.add_argument("--provider", action="append", choices=["local", "chatgpt", "openai", "gemini", "all"])
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

    commands.add_parser("model-levels", help="List configured local model levels")

    model_download = commands.add_parser("model-download", help="Download a configured local model level")
    model_download.add_argument("level", choices=["fast", "strong"])

    model_use = commands.add_parser("model-use", help="Switch Gima to a configured local model level")
    model_use.add_argument("level", choices=["fast", "strong"])
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


def _teacher_setup_providers(values: list[str] | None) -> list[str]:
    if not values or "all" in values:
        return ["openai", "gemini"]
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
        elif args.command == "doctor":
            print(json.dumps(dependency_report(), indent=2))
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
