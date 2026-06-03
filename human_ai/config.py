from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class ModelConfig:
    enabled: bool = False
    base_url: str = "http://127.0.0.1:8080/v1"
    model: str = "local-model"
    timeout_seconds: int = 90


@dataclass
class WebConfig:
    allowed_domains: List[str] = field(default_factory=list)


@dataclass
class ToolConfig:
    enabled: bool = False
    allowed_commands: List[str] = field(
        default_factory=lambda: [
            "git",
            "python3",
            "sqlite3",
            "mlr",
            "csvcut",
            "csvgrep",
            "ffmpeg",
            "ffprobe",
            "tesseract",
        ]
    )


@dataclass
class WakeConfig:
    word: str = "Gima"
    aliases: List[str] = field(default_factory=lambda: ["jima", "gimma", "geema"])
    camera_on_wake: bool = False
    speak_on_wake: bool = True
    profile_name: str = "Gima"
    profile_about: str = ""
    profile_sources: List[str] = field(default_factory=list)


@dataclass
class VisionConfig:
    camera_id: str = "webcam"
    camera_device: str = "0"
    detect_people_on_wake: bool = False
    detector_command: List[str] = field(default_factory=list)
    minimum_confidence: float = 0.50


@dataclass
class PermissionConfig:
    require_scoped_grants: bool = True
    maximum_minutes: int = 30


@dataclass
class Config:
    name: str = "Gima"
    workspace: Path = Path(".")
    data_dir: Path = Path(".human-ai")
    model: ModelConfig = field(default_factory=ModelConfig)
    web: WebConfig = field(default_factory=WebConfig)
    tools: ToolConfig = field(default_factory=ToolConfig)
    wake: WakeConfig = field(default_factory=WakeConfig)
    vision: VisionConfig = field(default_factory=VisionConfig)
    permissions: PermissionConfig = field(default_factory=PermissionConfig)

    @property
    def resolved_workspace(self) -> Path:
        return self.workspace.expanduser().resolve()

    @property
    def resolved_data_dir(self) -> Path:
        path = self.data_dir.expanduser()
        if not path.is_absolute():
            path = self.resolved_workspace / path
        return path.resolve()


def _merge_dataclass(instance: Any, values: Dict[str, Any]) -> Any:
    for key, value in values.items():
        if not hasattr(instance, key):
            continue
        current = getattr(instance, key)
        if hasattr(current, "__dataclass_fields__") and isinstance(value, dict):
            _merge_dataclass(current, value)
        elif key in {"workspace", "data_dir"}:
            setattr(instance, key, Path(value))
        else:
            setattr(instance, key, value)
    return instance


def load_config(path: str | None = None) -> Config:
    config = Config()
    if path:
        raw = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
        _merge_dataclass(config, raw)
    return config
