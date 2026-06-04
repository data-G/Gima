from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
import uuid
import time
import os
import re

from .agent import Agent
from .daily_summary import DailySummaryService
from .permissions import PermissionManager
from .readers import read_file
from .services import MediaAnalyzer, MediaCapture, Voice, dependency_report
from .wake import WakeAssistant
from .wake import normalize_speech


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

    def terminal_event(self, event: str, detail: str = "") -> None:
        timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
        suffix = f" | {detail}" if detail else ""
        print(f"[{timestamp}] {event}{suffix}", flush=True)

    def run_text_command(self, text: str) -> AssistantReply:
        normalized = " ".join(text.casefold().strip().split())
        self.terminal_event("COMMAND ROUTER", normalized or "[empty]")
        if not normalized:
            return AssistantReply("I did not hear a command.", "empty")
        if self.is_end_phrase(normalized) or normalized in {"stop", "exit", "quit", "goodbye", "sleep"}:
            return AssistantReply("Okay. I am going back to sleep.", "stop")
        if "time" in normalized:
            return AssistantReply(f"It is {datetime.now().astimezone().strftime('%H:%M on %A, %B %d')}.")
        if "doctor" in normalized or "status" in normalized:
            report = dependency_report()
            missing = [name for name, ok in report.items() if not ok]
            if missing:
                return AssistantReply(f"The core is running. Missing optional tools: {', '.join(missing)}.")
            return AssistantReply("All checked local tools are available.")
        teacher_provider = self._teacher_provider(normalized)
        if teacher_provider:
            self.permissions.require("web")
            prompt = self._teacher_prompt(text, teacher_provider)
            if not prompt:
                return AssistantReply(f"What should I ask {teacher_provider}?", "teacher")
            self.terminal_event("ACTION", f"teacher: {teacher_provider}")
            answer = self.agent.ask_teacher(teacher_provider, prompt)
            return AssistantReply(
                f"{teacher_provider} says: {answer[:900]}",
                "teacher",
            )
        if "take photo" in normalized or "take a photo" in normalized or "camera" in normalized:
            self.permissions.require("camera")
            self.terminal_event("ACTION", "camera photo requested")
            path = MediaCapture(self.config.resolved_data_dir / "media").camera(
                "assistant_photo.jpg", self.config.vision.camera_device
            )
            self.agent.memory.add_many(read_file(path))
            return AssistantReply(f"I took a photo and saved it locally at {path}.", "camera")
        if "screenshot" in normalized or "screen shot" in normalized:
            self.permissions.require("camera")
            self.terminal_event("ACTION", "screenshot requested")
            path = MediaCapture(self.config.resolved_data_dir / "media").screen("assistant_screen.png")
            self.agent.memory.add_many(read_file(path))
            return AssistantReply(f"I captured the screen and saved it locally at {path}.", "screenshot")
        if "daily summary" in normalized:
            self.terminal_event("ACTION", "daily summary requested")
            summary = DailySummaryService(
                self.config.resolved_workspace,
                self.config.resolved_data_dir,
                self.agent.memory,
            ).generate()
            return AssistantReply(f"I created the daily source summary attachment at {summary.attachment_path}.")
        if self._is_language_learn_request(normalized, "sinhala"):
            self.permissions.require("web")
            self.terminal_event("ACTION", "learn language: sinhala")
            path = self.agent.learn_language("sinhala")
            return AssistantReply(
                f"I learned Sinhala from public internet sources, saved it in {path}, and indexed it in language memory. Ask me anything about Sinhala.",
                "language_learn",
            )
        if self._is_ai_human_research_request(normalized):
            self.permissions.require("web")
            self.terminal_event("ACTION", "learn research: ai-human-systems")
            path = self.agent.learn_research_profile("ai-human-systems")
            return AssistantReply(
                f"I learned AI-human systems research from public papers and sources, saved it in {path}, and indexed it in research memory.",
                "research_learn",
            )
        if self._is_video_generation_research_request(normalized):
            self.permissions.require("web")
            self.terminal_event("ACTION", "learn research: video-generation")
            path = self.agent.learn_research_profile("video-generation")
            return AssistantReply(
                f"I learned video generation research from public papers and sources, saved it in {path}, and indexed it in research memory.",
                "research_learn",
            )
        if self._is_web_learn_request(normalized):
            self.permissions.require("web")
            url = self._first_url(text)
            if url:
                self.terminal_event("ACTION", f"web import: {url}")
                record_id = self.agent.import_web(url, "research")
                return AssistantReply(
                    f"I imported that web page into memory for review as {record_id}.",
                    "web_learn",
                )
            query = self._web_learn_query(text)
            if not query:
                return AssistantReply(
                    "Yes, I can learn from the internet. Say a topic, like learn from internet about local LLMs, or give me a URL.",
                    "web_learn",
                )
            self.terminal_event("ACTION", f"web learn: {query}")
            imported = self.agent.learn_web(query, "research", limit=3)
            if not imported:
                return AssistantReply(
                    "I searched the web but could not import a public page. Try giving me a direct URL.",
                    "web_learn",
                )
            return AssistantReply(
                f"I imported {len(imported)} internet pages about {query} into memory for review.",
                "web_learn",
            )
        if normalized.startswith("remember ") or normalized.startswith("search memory "):
            query = normalized.replace("search memory ", "", 1).replace("remember ", "", 1)
            self.terminal_event("ACTION", f"memory search: {query}")
            rows = self.agent.search(query, limit=3)
            if not rows:
                return AssistantReply("I could not find that in local memory.")
            titles = "; ".join(row["title"] for row in rows)
            return AssistantReply(f"I found these local memories: {titles}.")
        self.terminal_event("ACTION", "chat fallback")
        return AssistantReply(self.agent.chat(text), "chat")

    def _is_language_learn_request(self, normalized: str, language: str) -> bool:
        return language in normalized and any(
            phrase in normalized
            for phrase in {
                "learn",
                "study",
                "teach yourself",
                "know about",
            }
        )

    def _is_ai_human_research_request(self, normalized: str) -> bool:
        has_learn_intent = any(
            phrase in normalized
            for phrase in {
                "learn",
                "research",
                "study",
                "papers",
                "improve gima",
            }
        )
        has_topic = any(
            phrase in normalized
            for phrase in {
                "ai-human",
                "ai human",
                "human-ai",
                "human ai",
                "ai agent",
                "agentic ai",
                "gima improvement",
            }
        )
        return has_learn_intent and has_topic

    def _is_video_generation_research_request(self, normalized: str) -> bool:
        has_learn_intent = any(
            phrase in normalized
            for phrase in {
                "learn",
                "research",
                "study",
                "papers",
                "know about",
            }
        )
        has_topic = any(
            phrase in normalized
            for phrase in {
                "video generation",
                "text to video",
                "text-to-video",
                "image to video",
                "image-to-video",
                "video diffusion",
                "ai video",
                "generative video",
            }
        )
        return has_learn_intent and has_topic

    def _teacher_provider(self, normalized: str) -> str:
        if any(phrase in normalized for phrase in {"ask chatgpt", "ask openai", "use chatgpt"}):
            return "chatgpt"
        if any(phrase in normalized for phrase in {"ask gemini", "use gemini"}):
            return "gemini"
        return ""

    def _teacher_prompt(self, text: str, provider: str) -> str:
        cleaned = re.sub(
            rf"\b(please|gima|ask|use|{provider}|chatgpt|openai|gemini)\b",
            " ",
            text,
            flags=re.IGNORECASE,
        )
        return " ".join(cleaned.strip(" ?.!,;:").split())

    def _is_web_learn_request(self, normalized: str) -> bool:
        return any(
            phrase in normalized
            for phrase in {
                "learn from internet",
                "learn from the internet",
                "learn from web",
                "learn from the web",
                "search internet",
                "search the internet",
                "import web",
                "web import",
                "can't you learn",
                "can you learn",
            }
        )

    def _first_url(self, text: str) -> str:
        match = re.search(r"https?://[^\s]+", text)
        return match.group(0).rstrip(".,)") if match else ""

    def _web_learn_query(self, text: str) -> str:
        cleaned = re.sub(r"https?://[^\s]+", "", text, flags=re.IGNORECASE)
        cleaned = re.sub(
            r"\b(please|can't you|can you|could you|cannot you|you|gima|learn from the internet|learn from internet|learn from the web|learn from web|search the internet|search internet|import web|web import|learn|about|for)\b",
            " ",
            cleaned,
            flags=re.IGNORECASE,
        )
        return " ".join(cleaned.strip(" ?.!,;:").split())

    def is_end_phrase(self, text: str) -> bool:
        spoken = normalize_speech(text)
        accepted = {
            normalize_speech(self.config.wake.end_phrase),
            *[normalize_speech(value) for value in self.config.wake.end_aliases],
        }
        return spoken in accepted or any(phrase and phrase in spoken for phrase in accepted)

    def listen_once(
        self, analyzer: MediaAnalyzer, model: Path, seconds: int, device: str, label: str = "command"
    ) -> str:
        source = analyzer.record_microphone(
            f"assistant_{label}_{uuid.uuid4().hex}.wav", seconds, device
        )
        self.terminal_event("AUDIO SAVED", str(source))
        transcript = analyzer.transcribe(source, model).strip()
        self.terminal_event("TRANSCRIPT", transcript or "[empty]")
        return transcript

    def answer_voice_command(self, command: str) -> AssistantReply:
        self.terminal_event("HEARD COMMAND", command or "[empty]")
        self.agent.memory.append_conversation(
            self.agent.session_id, "user", command, category="voice_command"
        )
        reply = self.run_text_command(command)
        self.agent.memory.append_conversation(
            self.agent.session_id, "assistant", reply.message, category="voice_command"
        )
        self.terminal_event("REPLY", f"{reply.action}: {reply.message}")
        self.terminal_event("SPEAKING", reply.message)
        self.voice.speak(reply.message)
        return reply

    def run_conversation(
        self,
        model: Path,
        command_seconds: int = 8,
        conversation_turns: int = 20,
        device: str = ":0",
    ) -> int:
        self.permissions.require("microphone")
        self.terminal_event(
            "START",
            f"direct voice chat, end='{self.config.wake.end_phrase}', turns={conversation_turns}",
        )
        analyzer = MediaAnalyzer(self.config.resolved_data_dir / "media" / "assistant_audio")
        self.terminal_event("SPEAKING", "I am listening. Say End Game to stop.")
        self.voice.speak("I am listening. Say End Game to stop.")
        for turn in range(max(1, conversation_turns)):
            self.terminal_event("LISTENING FOR COMMAND", f"turn={turn + 1}/{conversation_turns}")
            try:
                command = self.listen_once(analyzer, model, command_seconds, device, "direct")
            except Exception as error:
                self.terminal_event("AUDIO WARNING", str(error))
                continue
            reply = self.answer_voice_command(command)
            if reply.action == "stop":
                self.terminal_event("STOP", "End phrase received")
                return 0
        self.terminal_event("STOP", "conversation turn limit reached")
        self.voice.speak("Conversation window ended.")
        return 0

    def run_after_wake(
        self,
        model: Path,
        wake_seconds: int = 4,
        command_seconds: int = 6,
        cycles: int = 20,
        conversation_turns: int = 20,
        forever: bool = False,
        device: str = ":0",
        capture_photo: Optional[bool] = None,
    ) -> int:
        self.permissions.require("microphone")
        self.terminal_event(
            "START",
            f"wake='{self.config.wake.word}', end='{self.config.wake.end_phrase}', forever={forever}",
        )
        lock_path = self.config.resolved_data_dir / "assistant.lock"
        if lock_path.exists():
            try:
                existing_pid = int(lock_path.read_text(encoding="utf-8").strip())
                os.kill(existing_pid, 0)
                raise RuntimeError(f"Assistant is already running as process {existing_pid}")
            except ProcessLookupError:
                lock_path.unlink()
            except ValueError:
                lock_path.unlink()
        lock_path.write_text(str(os.getpid()), encoding="utf-8")
        self.terminal_event("LOCK", f"pid={os.getpid()}")
        analyzer = MediaAnalyzer(self.config.resolved_data_dir / "media" / "assistant_audio")
        wake = WakeAssistant(self.config, self.agent.memory)
        try:
            while True:
                woke = False
                for cycle in range(max(1, cycles)):
                    self.terminal_event("LISTENING FOR WAKE", f"cycle={cycle + 1}/{cycles}")
                    try:
                        transcript = self.listen_once(analyzer, model, wake_seconds, device, "wake")
                    except Exception as error:
                        self.terminal_event("AUDIO WARNING", str(error))
                        time.sleep(1)
                        continue
                    self.terminal_event("HEARD WAKE", transcript or "[empty]")
                    result = wake.respond(transcript, capture_photo=capture_photo)
                    if not result.activated:
                        self.terminal_event("WAKE NOT MATCHED")
                        time.sleep(0.5)
                        continue
                    woke = True
                    self.terminal_event("WAKE MATCHED", transcript or "[empty]")
                    break
                if not woke:
                    self.terminal_event("STOP", "Wake word not detected.")
                    return 2
                self.terminal_event("SPEAKING", "I am listening. Say End Game to stop.")
                self.voice.speak("I am listening. Say End Game to stop.")
                for turn in range(max(1, conversation_turns)):
                    self.terminal_event("LISTENING FOR COMMAND", f"turn={turn + 1}/{conversation_turns}")
                    try:
                        command = self.listen_once(analyzer, model, command_seconds, device, "command")
                    except Exception as error:
                        command = ""
                        self.terminal_event("AUDIO WARNING", str(error))
                    reply = self.answer_voice_command(command)
                    if reply.action == "stop":
                        if forever:
                            self.terminal_event("SESSION ENDED", "returning to wake listening")
                            self.voice.speak("Waiting for Gima.")
                            break
                        self.terminal_event("STOP", "End phrase received")
                        return 0
                else:
                    self.terminal_event("SESSION ENDED", "conversation turn limit reached")
                    self.voice.speak("Conversation window ended. I am going back to sleep.")
                    if not forever:
                        return 0
                if not forever:
                    return 0
        finally:
            if lock_path.exists() and lock_path.read_text(encoding="utf-8").strip() == str(os.getpid()):
                lock_path.unlink()
                self.terminal_event("UNLOCK", str(lock_path))
