from __future__ import annotations

import argparse
import json
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

    search = commands.add_parser("search", help="Search Gima memory")
    search.add_argument("query")
    search.add_argument("--category")
    search.add_argument("--limit", type=int, default=8)

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
        elif args.command == "search":
            _print_rows(agent.search(args.query, args.category, args.limit))
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
