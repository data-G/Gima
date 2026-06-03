from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .agent import Agent
from .assistant_loop import LocalAssistant
from .config import load_config
from .daily_summary import DailySummaryService
from .memory import Record
from .permissions import ALLOWED_SCOPES, PermissionManager
from .readers import read_file
from .scene import LocalPersonDetector, save_observation
from .services import (
    MediaAnalyzer,
    MediaCapture,
    SafeToolRunner,
    Voice,
    dependency_report,
    monitor_camera,
)
from .wake import WakeAssistant


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="human-ai", description="Local-first multimodal agent")
    root.add_argument("--config", help="Path to a JSON configuration file")
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Initialize local memory files")
    commands.add_parser("doctor", help="Report optional local capabilities")
    commands.add_parser("rebuild", help="Regenerate the disposable SQLite search index")

    permission_grant = commands.add_parser("permission-grant", help="Start a short scoped permission session")
    permission_grant.add_argument("--scope", action="append", choices=sorted(ALLOWED_SCOPES), required=True)
    permission_grant.add_argument("--minutes", type=int, default=10)
    commands.add_parser("permission-status", help="Show the current scoped permission session")
    commands.add_parser("permission-revoke", help="End the current scoped permission session")

    daily_summary = commands.add_parser("daily-summary", help="Package a local daily source snapshot")
    daily_summary.add_argument("--since", default="midnight", help="Git --since value")

    daily_email = commands.add_parser("daily-summary-email", help="Send the source snapshot using Apple Mail")
    daily_email.add_argument("--to", required=True)
    daily_email.add_argument("--since", default="midnight", help="Git --since value")

    ingest = commands.add_parser("ingest", help="Index a file or folder")
    ingest.add_argument("path")

    search = commands.add_parser("search", help="Search indexed memory")
    search.add_argument("query")
    search.add_argument("--category")
    search.add_argument("--limit", type=int, default=8)

    chat = commands.add_parser("chat", help="Chat in the terminal")
    chat.add_argument("message", nargs="?")

    web = commands.add_parser("web-import", help="Import an explicitly approved public URL")
    web.add_argument("url")
    web.add_argument("--category", default="research")

    review = commands.add_parser("memory-review", help="List web imports and other records awaiting review")
    review.add_argument("--limit", type=int, default=50)

    approve = commands.add_parser("memory-approve", help="Promote a reviewed memory record")
    approve.add_argument("record_id")

    history = commands.add_parser("conversation-history", help="Search locally stored conversations")
    history.add_argument("query", nargs="?", default="")
    history.add_argument("--session-id")
    history.add_argument("--limit", type=int, default=50)

    speak = commands.add_parser("speak", help="Speak text using the local macOS voice")
    speak.add_argument("text")

    screen = commands.add_parser("screen-capture", help="Capture and index a screenshot")
    screen.add_argument("--name", default="screen.png")

    camera = commands.add_parser("camera-capture", help="Capture and index one camera frame")
    camera.add_argument("--name", default="camera.jpg")
    camera.add_argument("--device", default=None, help="FFmpeg avfoundation video device")

    monitor = commands.add_parser("camera-monitor", help="Capture a bounded sequence of camera frames")
    monitor.add_argument("--frames", type=int, default=5)
    monitor.add_argument("--interval", type=int, default=5)
    monitor.add_argument("--device", default=None, help="FFmpeg avfoundation video device")

    observe = commands.add_parser("scene-observe", help="Count anonymous people in a local image")
    observe.add_argument("path")

    camera_observe = commands.add_parser("camera-observe", help="Capture and count anonymous people locally")
    camera_observe.add_argument("--name", default="scene.jpg")
    camera_observe.add_argument("--device", default=None, help="FFmpeg avfoundation video device")

    video = commands.add_parser("video-analyze", help="Extract and index sampled video frames")
    video.add_argument("path")
    video.add_argument("--seconds", type=int, default=10)

    transcribe = commands.add_parser("transcribe", help="Transcribe audio or video with whisper.cpp")
    transcribe.add_argument("path")
    transcribe.add_argument("--model", required=True, help="Path to a whisper.cpp model")

    wake = commands.add_parser("wake", help="Process a transcript for the configured wake word")
    wake.add_argument("transcript", help="Speech transcript from any language")
    wake.add_argument(
        "--capture-photo",
        action="store_const",
        const=True,
        default=None,
        help="Capture one local camera photo after detecting the wake word",
    )

    listen = commands.add_parser("wake-listen", help="Listen locally for the wake word in bounded chunks")
    listen.add_argument("--model", required=True, help="Path to a whisper.cpp model")
    listen.add_argument("--seconds", type=int, default=4, help="Seconds per microphone chunk")
    listen.add_argument("--cycles", type=int, default=15, help="Maximum chunks before stopping")
    listen.add_argument("--device", default=":0", help="FFmpeg avfoundation audio input device")
    listen.add_argument("--capture-photo", action="store_const", const=True, default=None)

    assistant = commands.add_parser("assistant-run", help="Wake, listen for one command, answer aloud, and act safely")
    assistant.add_argument("--model", required=True, help="Path to a whisper.cpp model")
    assistant.add_argument("--wake-seconds", type=int, default=4)
    assistant.add_argument("--command-seconds", type=int, default=6)
    assistant.add_argument("--cycles", type=int, default=20)
    assistant.add_argument("--conversation-turns", type=int, default=20)
    assistant.add_argument("--forever", action="store_true", help="After End Game, return to waiting for Gima")
    assistant.add_argument("--device", default=":0", help="FFmpeg avfoundation audio input device")
    assistant.add_argument("--capture-photo", action="store_const", const=True, default=None)

    assistant_command = commands.add_parser("assistant-command", help="Run one typed assistant command")
    assistant_command.add_argument("text")

    tool = commands.add_parser("tool", help="Run one explicitly allowlisted tool")
    tool.add_argument("tool_args", nargs=argparse.REMAINDER)
    return root


def _print_search(rows) -> None:
    if not rows:
        print("No matching memory.")
    for row in rows:
        print(f"[{row['id']}] {row['category']}/{row['subcategory']} - {row['title']}")
        print(row["content"][:500].replace("\n", " "))
        print()


def _interactive_chat(agent: Agent) -> None:
    print("Local agent ready. Type /exit to stop.")
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
        print(f"ai> {agent.chat(message)}")


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    config = load_config(args.config)
    agent = Agent(config)
    permissions = PermissionManager(config, agent.memory)
    try:
        if args.command == "init":
            print(f"Initialized memory in {config.resolved_data_dir}")
        elif args.command == "doctor":
            print(json.dumps(dependency_report(), indent=2))
        elif args.command == "rebuild":
            print(f"Rebuilt index with {agent.memory.rebuild_index()} records")
        elif args.command == "permission-grant":
            expected = f"GRANT {','.join(sorted(set(args.scope))).upper()}"
            confirmation = input(f"Type {expected} to authorize this local session: ").strip()
            if confirmation != expected:
                raise PermissionError("Permission confirmation did not match")
            grant = permissions.grant(args.scope, args.minutes)
            print(f"Granted {', '.join(grant.scopes)} until {grant.expires_at}")
        elif args.command == "permission-status":
            grant = permissions.current()
            print(json.dumps(grant.__dict__, indent=2) if grant else "No active permission session.")
        elif args.command == "permission-revoke":
            permissions.revoke()
            print("Permission session revoked.")
        elif args.command in {"daily-summary", "daily-summary-email"}:
            service = DailySummaryService(
                config.resolved_workspace, config.resolved_data_dir, agent.memory
            )
            summary = service.generate(args.since)
            print(f"Packaged {summary.file_count} tracked files: {summary.attachment_path}")
            if args.command == "daily-summary-email":
                service.send_with_apple_mail(args.to, summary)
                print(f"Sent daily summary to {args.to}")
        elif args.command == "ingest":
            permissions.require("files")
            print(f"Indexed {agent.ingest(Path(args.path))} new chunks")
        elif args.command == "search":
            _print_search(agent.search(args.query, args.category, args.limit))
        elif args.command == "chat":
            print(agent.chat(args.message)) if args.message else _interactive_chat(agent)
        elif args.command == "web-import":
            permissions.require("web")
            print(f"Imported for review as {agent.import_web(args.url, args.category)}")
        elif args.command == "memory-review":
            _print_search(agent.memory.list_by_status("review", args.limit))
        elif args.command == "memory-approve":
            if not agent.memory.update_status(args.record_id, "active"):
                raise ValueError(f"Unknown memory record: {args.record_id}")
            print(f"Approved {args.record_id}")
        elif args.command == "conversation-history":
            rows = agent.memory.search_conversations(args.query, args.session_id, args.limit)
            if not rows:
                print("No matching conversation.")
            for row in reversed(rows):
                print(f"{row['timestamp']} [{row['session_id']}] {row['role']}> {row['message']}")
        elif args.command == "speak":
            Voice().speak(args.text)
        elif args.command in {"screen-capture", "camera-capture"}:
            permissions.require("camera")
            capture = MediaCapture(config.resolved_data_dir / "media")
            path = (
                capture.screen(args.name)
                if args.command == "screen-capture"
                else capture.camera(args.name, args.device or config.vision.camera_device)
            )
            agent.memory.add_many(read_file(path))
            print(f"Captured and indexed {path}")
        elif args.command == "scene-observe":
            permissions.require("files")
            observation = LocalPersonDetector(config).detect(Path(args.path))
            record_id = save_observation(agent.memory, observation)
            print(f"{observation.summary} Stored as {record_id}")
        elif args.command == "camera-observe":
            permissions.require("camera")
            capture = MediaCapture(config.resolved_data_dir / "media" / "camera")
            path = capture.camera(args.name, args.device or config.vision.camera_device)
            agent.memory.add_many(read_file(path))
            observation = LocalPersonDetector(config).detect(path)
            record_id = save_observation(agent.memory, observation)
            print(f"{observation.summary} Stored as {record_id}")
        elif args.command == "camera-monitor":
            permissions.require("camera")
            capture = MediaCapture(config.resolved_data_dir / "media" / "camera")
            paths = monitor_camera(
                capture, args.interval, args.frames, args.device or config.vision.camera_device
            )
            chunks = sum(agent.memory.add_many(read_file(path)) for path in paths)
            print(f"Captured {len(paths)} frames and indexed {chunks} new chunks")
        elif args.command == "video-analyze":
            permissions.require("files")
            source = Path(args.path)
            analyzer = MediaAnalyzer(config.resolved_data_dir / "media")
            frames = analyzer.video_keyframes(source, args.seconds)
            chunks = agent.memory.add_many(read_file(source))
            chunks += sum(agent.memory.add_many(read_file(path)) for path in frames)
            print(f"Extracted {len(frames)} frames and indexed {chunks} new chunks")
        elif args.command == "transcribe":
            permissions.require("files")
            source = Path(args.path).expanduser().resolve()
            analyzer = MediaAnalyzer(config.resolved_data_dir / "media")
            text = analyzer.transcribe(source, Path(args.model))
            record_id = agent.memory.add(
                Record(
                    category="audio",
                    subcategory="transcript",
                    kind="transcript",
                    title=f"Transcript: {source.name}",
                    content=text,
                    source=str(source),
                    media_path=str(source),
                )
            )
            print(f"Stored transcript as {record_id}")
        elif args.command == "wake":
            result = WakeAssistant(config, agent.memory).respond(
                args.transcript, capture_photo=args.capture_photo
            )
            print(result.message)
            if result.photo_path:
                print(f"Local photo: {result.photo_path}")
            return 0 if result.activated else 2
        elif args.command == "wake-listen":
            permissions.require("microphone")
            analyzer = MediaAnalyzer(config.resolved_data_dir / "media" / "wake_audio")
            assistant = WakeAssistant(config, agent.memory)
            for cycle in range(max(1, args.cycles)):
                source = analyzer.record_microphone(f"wake_{cycle:05d}.wav", args.seconds, args.device)
                transcript = analyzer.transcribe(source, Path(args.model))
                print(f"heard> {transcript}")
                result = assistant.respond(transcript, capture_photo=args.capture_photo)
                if result.activated:
                    print(result.message)
                    if result.photo_path:
                        print(f"Local photo: {result.photo_path}")
                    return 0
            print("Wake word not detected.")
            return 2
        elif args.command == "assistant-run":
            return LocalAssistant(agent).run_after_wake(
                Path(args.model),
                wake_seconds=args.wake_seconds,
                command_seconds=args.command_seconds,
                cycles=args.cycles,
                conversation_turns=args.conversation_turns,
                forever=args.forever,
                device=args.device,
                capture_photo=args.capture_photo,
            )
        elif args.command == "assistant-command":
            reply = LocalAssistant(agent).run_text_command(args.text)
            agent.memory.append_conversation(agent.session_id, "user", args.text, category="assistant_command")
            agent.memory.append_conversation(
                agent.session_id, "assistant", reply.message, category="assistant_command"
            )
            print(reply.message)
            Voice().speak(reply.message)
        elif args.command == "tool":
            result = SafeToolRunner(config, agent.memory).run(args.tool_args)
            agent.memory.audit("tool", " ".join(args.tool_args), result.stderr[:500], str(result.returncode))
            sys.stdout.write(result.stdout)
            sys.stderr.write(result.stderr)
            return result.returncode
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
