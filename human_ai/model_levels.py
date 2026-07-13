from __future__ import annotations

import json
import shutil
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from .config import Config


DEFAULT_MODEL_DIR = Path("~/.local/share/gima/models").expanduser()

DEFAULT_MODEL_LEVELS: Dict[str, Dict[str, Any]] = {
    "tiny": {
        "name": "Gima Tiny",
        "model": "gima-local-llama3.2-1b-fast",
        "model_path": str(Path("~/.qvac/models/f2bade0bc5cd4a8c_Llama-3.2-1B-Instruct-Q4_0.gguf").expanduser()),
        "context_size": 1024,
        "max_tokens": 64,
        "device": "none",
        "gpu_layers": 0,
        "warmup": False,
        "description": "Smallest local chat model for fast answers on this PC.",
        "source": "local QVAC model",
        "files": [],
    },
    "fast": {
        "name": "Gima Fast",
        "model": "gima-local-qwen2.5-1.5b",
        "model_path": str(DEFAULT_MODEL_DIR / "qwen2.5-1.5b-instruct-q4_k_m.gguf"),
        "context_size": 4096,
        "max_tokens": 384,
        "device": "none",
        "gpu_layers": 0,
        "warmup": False,
        "description": "Small fast local model for quick voice and terminal replies.",
        "source": "local",
        "files": [],
    },
    "strong": {
        "name": "Gima Strong",
        "model": "gima-local-qwen2.5-7b",
        "model_path": str(DEFAULT_MODEL_DIR / "qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf"),
        "context_size": 4096,
        "max_tokens": 256,
        "device": "none",
        "gpu_layers": 0,
        "warmup": False,
        "description": "Larger 7B Q4 model for better reasoning, coding, and conversation on 16 GB RAM.",
        "source": "https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF",
        "files": [
            {
                "name": "qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf",
                "url": "https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf",
                "size_mb": 3993.20,
            },
            {
                "name": "qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf",
                "url": "https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf",
                "size_mb": 689.87,
            },
        ],
    },
    "gemma4_12b": {
        "name": "Gemma 4 12B QAT Q4",
        "model": "google-gemma-4-12b-it-qat-q4_0",
        "model_path": str(DEFAULT_MODEL_DIR / "gemma-4-12b-it-qat-q4_0.gguf"),
        "context_size": 1024,
        "max_tokens": 32,
        "timeout_seconds": 75,
        "device": "none",
        "gpu_layers": 0,
        "warmup": False,
        "description": "Official Google Gemma 4 12B instruction-tuned QAT Q4 GGUF. Better reasoning and multimodal-ready, but heavy for this 16 GB RAM Mac.",
        "source": "https://huggingface.co/google/gemma-4-12B-it-qat-q4_0-gguf",
        "files": [
            {
                "name": "gemma-4-12b-it-qat-q4_0.gguf",
                "url": "https://huggingface.co/google/gemma-4-12B-it-qat-q4_0-gguf/resolve/main/gemma-4-12b-it-qat-q4_0.gguf",
                "size_mb": 6975.88,
            },
            {
                "name": "mmproj-gemma-4-12b-it-qat-q4_0.gguf",
                "url": "https://huggingface.co/google/gemma-4-12B-it-qat-q4_0-gguf/resolve/main/mmproj-gemma-4-12b-it-qat-q4_0.gguf",
                "size_mb": 175.12,
            },
        ],
    },
}


@dataclass(frozen=True)
class ModelLevel:
    level: str
    name: str
    model: str
    model_path: Path
    context_size: int
    available: bool
    status: str
    description: str
    source: str
    files: List[Dict[str, Any]]


class ModelLevelManager:
    def __init__(self, config: Config, config_path: str | None = None):
        self.config = config
        self.config_path = Path(config_path).expanduser().resolve() if config_path else None

    def levels(self) -> List[ModelLevel]:
        return [self.level(name) for name in self._profiles()]

    def level(self, name: str) -> ModelLevel:
        key = name.casefold().strip()
        profiles = self._profiles()
        if key not in profiles:
            raise ValueError(f"Unknown model level: {name}")
        profile = profiles[key]
        model_path = Path(profile["model_path"]).expanduser()
        return ModelLevel(
            level=key,
            name=str(profile.get("name", key)),
            model=str(profile.get("model", key)),
            model_path=model_path,
            context_size=int(profile.get("context_size", self.config.model.context_size)),
            available=self._profile_available(profile),
            status=self._profile_status(profile),
            description=str(profile.get("description", "")),
            source=str(profile.get("source", "")),
            files=list(profile.get("files", [])),
        )

    def download(self, name: str) -> List[Path]:
        profile = self._profiles()[name.casefold().strip()]
        files = list(profile.get("files", []))
        if not files:
            path = Path(profile["model_path"]).expanduser()
            if path.exists():
                return [path]
            raise RuntimeError(f"No download source is configured for {name}")
        target_dir = Path(profile["model_path"]).expanduser().parent
        target_dir.mkdir(parents=True, exist_ok=True)
        downloaded: List[Path] = []
        for file_info in files:
            target = target_dir / str(file_info["name"])
            if self._file_ready(target, file_info):
                downloaded.append(target)
                continue
            temp = target.with_suffix(target.suffix + ".part")
            with urllib.request.urlopen(str(file_info["url"]), timeout=120) as response:
                with temp.open("wb") as handle:
                    shutil.copyfileobj(response, handle)
            temp.replace(target)
            downloaded.append(target)
        return downloaded

    def apply_level(self, name: str) -> Dict[str, Any]:
        profile = self._profiles()[name.casefold().strip()]
        if not self._profile_available(profile):
            raise FileNotFoundError(
                f"Model level {name} is {self._profile_status(profile)}. Run `python3 -m human_ai.gima model-download {name}`."
            )
        values = self._config_model_values(profile, name.casefold().strip())
        if self.config_path:
            self._write_config_model(values)
        for key, value in values.items():
            if hasattr(self.config.model, key):
                setattr(self.config.model, key, value)
        return values

    def _profiles(self) -> Dict[str, Dict[str, Any]]:
        profiles = {key: dict(value) for key, value in DEFAULT_MODEL_LEVELS.items()}
        for key, value in (self.config.model.profiles or {}).items():
            merged = dict(profiles.get(key, {}))
            merged.update(value)
            profiles[key] = merged
        return profiles

    @staticmethod
    def _profile_available(profile: Dict[str, Any]) -> bool:
        return ModelLevelManager._profile_status(profile) == "ready"

    @staticmethod
    def _profile_status(profile: Dict[str, Any]) -> str:
        files = list(profile.get("files", []))
        if files:
            base = Path(profile["model_path"]).expanduser().parent
            statuses = [ModelLevelManager._file_status(base / str(file_info["name"]), file_info) for file_info in files]
            if all(status == "ready" for status in statuses):
                return "ready"
            if any(status == "incomplete" for status in statuses):
                return "incomplete"
            return "missing"
        return "ready" if Path(profile["model_path"]).expanduser().exists() else "missing"

    @staticmethod
    def _file_ready(path: Path, file_info: Dict[str, Any]) -> bool:
        return ModelLevelManager._file_status(path, file_info) == "ready"

    @staticmethod
    def _file_status(path: Path, file_info: Dict[str, Any]) -> str:
        if not path.exists() or path.stat().st_size <= 0:
            return "missing"
        expected_mb = file_info.get("size_mb")
        if expected_mb is None:
            return "ready"
        expected_bytes = int(float(expected_mb) * 1_000_000)
        # Hugging Face reports may vary slightly, but multi-GB truncation must not be treated as ready.
        tolerance = max(1_000_000, int(expected_bytes * 0.01))
        if path.stat().st_size + tolerance < expected_bytes:
            return "incomplete"
        return "ready"

    @staticmethod
    def _config_model_values(profile: Dict[str, Any], level: str) -> Dict[str, Any]:
        values = {
            "enabled": True,
            "active_level": level,
            "model": str(profile["model"]),
            "model_path": str(profile["model_path"]),
            "context_size": int(profile.get("context_size", 4096)),
            "max_tokens": int(profile.get("max_tokens", 384)),
            "device": str(profile.get("device", "none")),
            "gpu_layers": int(profile.get("gpu_layers", 0)),
            "warmup": bool(profile.get("warmup", False)),
        }
        if "timeout_seconds" in profile:
            values["timeout_seconds"] = int(profile["timeout_seconds"])
        return values

    def _write_config_model(self, values: Dict[str, Any]) -> None:
        if not self.config_path:
            return
        raw: Dict[str, Any] = {}
        if self.config_path.exists():
            raw = json.loads(self.config_path.read_text(encoding="utf-8"))
        raw.setdefault("model", {})
        raw["model"].update(values)
        self.config_path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
