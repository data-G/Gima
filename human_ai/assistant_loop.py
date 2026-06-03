from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from .agent import Agent
from .daily_summary import DailySummaryService
from .permissions import PermissionManager
from .readers import read_file
from .services import MediaAnalyzer, MediaCapture, Voice, dependency_report
from .wake import WakeAssistant


@dataclass
class AssistantReply:
    message: str
    action: str = "answer"


class LocalAssistant:
    """Voice-first assistant that answers locally and runs bounded actions."""

    def __init__(self, agent: Agent):
        self.agent = agent
        self.config = agent.config
        self.permissions = PermissionManager(self.config, agent.memory)
        self.voice = Voice()

    def run_text_command(self, text: str) -> AssistantReply:
        normalized = " ".join(text.casefold().strip().split())
        if not normalized:
            return AssistantReply("I did not hear a command.")
        if normalized in {"stop", "exit", "quit", "goodbye", "sleep"}:
            return AssistantReply("Okay. I am going back to sleep.", "stop")
        if "time" in normalized:
            return AssistantReply(f"It is {datetime.now().astimezone().strftime('%H:%M on %A, %B %d')}.")
        if "doctor" in normalized or "status" in normalized:
            report = dependency_report()
            missing = [name for name, ok in report.items() if not ok]
            if missing:
                return AssistantReply(f"The core is running. Missing optional tools: {', '.join(missing)}.")
            return AssistantReply("All checked local tools are available.")
        if "take photo" in normalized or "take a photo" in normalized or "camera" in normalized:
            self.permissions.require("camera")
            path = MediaCapture(self.config.resolved_data_dir / "media").camera(
                "assistant_photo.jpg", self.config.vision.camera_device
            )
            self.agent.memory.add_many(read_file(path))
            return AssistantReply(f"I took a photo and saved it locally at {path}.", "camera")
        if "screenshot" in normalized or "screen shot" in normalized:
            self.permissions.require("camera")
            path = MediaCapture(self.config.resolved_data_dir / "media").screen("assistant_screen.png")
            self.agent.memory.add_many(read_file(path))
            return AssistantReply(f"I captured the screen and saved it locally at {path}.", "screenshot")
        if "daily summary" in normalized:
            summary = DailySummaryService(
                self.config.resolved_workspace,
                self.config.resolved_data_dir,
                self.agent.memory,
            ).generate()
            return AssistantReply(f"I created the daily source summary attachment at {summary.attachment_path}.")
        if normalized.startswith("remember ") or normalized.startswith("search memory "):
            query = normalized.replace("search memory ", "", 1).replace("remember ", "", 1)
            rows = self.agent.search(query, limit=3)
            if not rows:
                return AssistantReply("I could not find that in local memory.")
            titles = "; ".join(row["title"] for row in rows)
            return AssistantReply(f"I found these local memories: {titles}.")
        return AssistantReply(self.agent.chat(text), "chat")

    def listen_once(self, analyzer: MediaAnalyzer, model: Path, seconds: int, device: str) -> str:
        source = analyzer.record_microphone("assistant_command.wav", seconds, device)
        return analyzer.transcribe(source, model).strip()

    def run_after_wake(
        self,
        model: Path,
        wake_seconds: int = 4,
        command_seconds: int = 6,
        cycles: int = 20,
        device: str = ":0",
        capture_photo: Optional[bool] = None,
    ) -> int:
        self.permissions.require("microphone")
        analyzer = MediaAnalyzer(self.config.resolved_data_dir / "media" / "assistant_audio")
        wake = WakeAssistant(self.config, self.agent.memory)
        for cycle in range(max(1, cycles)):
            transcript = self.listen_once(analyzer, model, wake_seconds, device)
            print(f"heard wake> {transcript}")
            result = wake.respond(transcript, capture_photo=capture_photo)
            if not result.activated:
                continue
            self.voice.speak("I am listening.")
            command = self.listen_once(analyzer, model, command_seconds, device)
            print(f"heard command> {command}")
            self.agent.memory.append_conversation(self.agent.session_id, "user", command, category="voice_command")
            reply = self.run_text_command(command)
            self.agent.memory.append_conversation(
                self.agent.session_id, "assistant", reply.message, category="voice_command"
            )
            print(reply.message)
            self.voice.speak(reply.message)
            return 0
        print("Wake word not detected.")
        return 2
