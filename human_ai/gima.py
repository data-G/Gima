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
from .memory import Record
from .permissions import PermissionManager
from .services import dependency_report


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
    learn_research.add_argument("profile", choices=["ai-human-systems"])

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

    transfer = commands.add_parser("transfer-knowledge", help="Ask teacher models and save knowledge for review")
    transfer.add_argument("prompt", nargs="+")
    transfer.add_argument(
        "--provider",
        choices=["local", "chatgpt", "openai", "gemini", "both", "all"],
        default="both",
    )

    commands.add_parser("ai-list", help="List AI providers Gima can use")

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

    commands.add_parser("doctor", help="Show optional local capabilities")
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


def _shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    config = load_config(args.config)
    agent = Agent(config)
    brain = BrainServer(config, agent.memory)
    permissions = PermissionManager(config, agent.memory)
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
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
