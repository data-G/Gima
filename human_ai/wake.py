from __future__ import annotations

import re
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .config import Config
from .memory import MemoryStore, Record
from .permissions import PermissionManager
from .readers import read_file
from .scene import LocalPersonDetector, SceneObservation, save_observation
from .services import MediaCapture, Voice


def normalize_speech(text: str) -> str:
    """Normalize transcripts from any Unicode script without losing letters."""
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return " ".join(re.findall(r"[^\W_]+", normalized, flags=re.UNICODE))


def contains_wake_word(transcript: str, word: str = "Gima", aliases: Optional[List[str]] = None) -> bool:
    spoken = normalize_speech(transcript).split()
    accepted = {normalize_speech(value) for value in [word] + list(aliases or [])}
    return any(token in accepted for token in spoken)


@dataclass
class WakeResult:
    activated: bool
    message: str
    photo_path: Optional[Path] = None
    observation: Optional[SceneObservation] = None


class WakeAssistant:
    """Handle a detected wake word without uploading biometric images."""

    def __init__(self, config: Config, memory: MemoryStore):
        self.config = config
        self.memory = memory
        self.session_id = f"wake_{uuid.uuid4().hex}"

    def respond(self, transcript: str, capture_photo: Optional[bool] = None) -> WakeResult:
        wake = self.config.wake
        self.memory.append_conversation(self.session_id, "user", transcript, category="voice")
        if not contains_wake_word(transcript, wake.word, wake.aliases):
            return WakeResult(False, "Wake word not detected.")

        should_capture = wake.camera_on_wake if capture_photo is None else capture_photo
        photo_path: Optional[Path] = None
        observation: Optional[SceneObservation] = None
        if should_capture:
            PermissionManager(self.config, self.memory).require("camera")
            timestamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
            capture = MediaCapture(self.config.resolved_data_dir / "media" / "wake")
            photo_path = capture.camera(f"wake_{timestamp}.jpg", self.config.vision.camera_device)
            self.memory.add_many(read_file(photo_path))
            if self.config.vision.detect_people_on_wake:
                observation = LocalPersonDetector(self.config).detect(photo_path)
                save_observation(self.memory, observation)

        message = self._greeting(observation)
        if wake.speak_on_wake:
            Voice().speak(message)
        self.memory.append_conversation(self.session_id, "assistant", message, category="voice")
        self.memory.audit(
            "wake",
            wake.word,
            f"Activated; local_photo={photo_path or 'disabled'}",
            "ok",
        )
        self.memory.add(
            Record(
                category="events",
                subcategory="wake",
                kind="wake_event",
                title=f"Wake word: {wake.word}",
                content=message,
                media_path=str(photo_path or ""),
                confidence="1.00",
            )
        )
        return WakeResult(True, message, photo_path, observation)

    def _greeting(self, observation: Optional[SceneObservation] = None) -> str:
        profile = self.config.wake
        message = f"Hi {profile.profile_name}."
        if profile.profile_about:
            message += f" {profile.profile_about}"
        else:
            message += " Your local profile does not contain a description yet."
        if profile.profile_sources:
            message += f" Your profile has {len(profile.profile_sources)} approved web source(s)."
        if observation:
            message += f" {observation.summary} I do not infer anyone's identity from the image."
        return message
