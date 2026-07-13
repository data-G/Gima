from __future__ import annotations

import csv
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import Config
from .services import OpenRouterCatalog


TASK_CATEGORIES = {
    "GENERAL_CHAT",
    "FAST_CHAT",
    "DEEP_REASONING",
    "CODING",
    "DEBUGGING",
    "DATA_ANALYSIS",
    "DATA_SCIENCE",
    "RESEARCH",
    "LONG_DOCUMENT",
    "VISION",
    "IMAGE_PROMPT",
    "CREATIVE_WRITING",
    "TRANSLATION",
    "SUMMARIZATION",
    "AGENT_PLANNING",
    "TOOL_USE",
    "PRIVATE_LOCAL_TASK",
}

ROUTING_MODES = {
    "AUTO",
    "LOCAL_ONLY",
    "CLOUD_ONLY",
    "FAST",
    "BALANCED",
    "BEST_QUALITY",
    "LOWEST_COST",
    "MANUAL",
}


MODEL_PROFILES: dict[str, dict[str, Any]] = {
    "fast": {
        "primary": "openrouter/auto",
        "fallbacks": ["openrouter/free"],
        "tags": ["fast", "low_cost"],
    },
    "balanced": {
        "primary": "openrouter/auto",
        "fallbacks": ["openrouter/free"],
        "tags": ["balanced"],
    },
    "reasoning": {
        "primary": "openrouter/auto",
        "fallbacks": ["openrouter/free"],
        "tags": ["reasoning"],
    },
    "coding": {
        "primary": "openrouter/auto",
        "fallbacks": ["openrouter/free"],
        "tags": ["coding", "tool_use"],
    },
    "vision": {
        "primary": "openrouter/auto",
        "fallbacks": ["openrouter/free"],
        "tags": ["vision"],
    },
    "long_context": {
        "primary": "openrouter/auto",
        "fallbacks": ["openrouter/free"],
        "tags": ["long_context"],
    },
    "creative": {
        "primary": "openrouter/auto",
        "fallbacks": ["openrouter/free"],
        "tags": ["creative"],
    },
}


@dataclass(frozen=True)
class RoutingRequest:
    message: str
    mode: str = "AUTO"
    manual_model: str = ""
    quality: str = "balanced"
    speed: str = "balanced"
    budget: str = "balanced"
    privacy: str = "normal"
    has_images: bool = False
    context_tokens: int = 0
    tool_use: bool = False


@dataclass(frozen=True)
class RoutingDecision:
    request_id: str
    provider: str
    model: str
    task_category: str
    mode: str
    fallbacks: list[str]
    reason: str
    cloud_allowed: bool
    estimated_prompt_tokens: int
    estimated_cost_usd: float


class OpenRouterTaskRouter:
    def __init__(self, config: Config):
        self.config = config
        self.catalog = OpenRouterCatalog(config)

    def decide(self, request: RoutingRequest) -> RoutingDecision:
        mode = self._normalize_mode(request.mode)
        task = self.classify_task(request)
        cloud_allowed = os.environ.get("CLOUD_ALLOWED", "").strip().casefold() in {"1", "true", "yes", "on"}
        estimated_tokens = request.context_tokens or self.estimate_tokens(request.message)

        if mode == "LOCAL_ONLY" or request.privacy.casefold() == "high" or task == "PRIVATE_LOCAL_TASK":
            return self._decision(request, "local", self.config.model.active_level, task, mode, [], "privacy/local-only routing", cloud_allowed, estimated_tokens)

        if mode == "MANUAL" and request.manual_model.strip():
            return self._decision(request, "openrouter", request.manual_model.strip(), task, mode, self._routing_fallbacks(), "manual model selection", cloud_allowed, estimated_tokens)

        if mode == "CLOUD_ONLY" or cloud_allowed:
            profile_name = self._profile_for(task, mode, request)
            profile = self._model_profiles().get(profile_name, MODEL_PROFILES["balanced"])
            selected = str(profile.get("primary") or "openrouter/auto")
            fallbacks = [str(item) for item in profile.get("fallbacks", []) if str(item)]
            fallbacks.extend(model for model in self._routing_fallbacks() if model not in fallbacks)
            return self._decision(request, "openrouter", selected, task, mode, fallbacks, f"{profile_name} cloud routing", cloud_allowed, estimated_tokens)

        return self._decision(request, "local", self.config.model.active_level, task, mode, [], "cloud disabled; local-first fallback", cloud_allowed, estimated_tokens)

    def classify_task(self, request: RoutingRequest) -> str:
        text = request.message.casefold()
        if request.privacy.casefold() == "high" or any(term in text for term in ["api key", "password", "secret", "private document"]):
            return "PRIVATE_LOCAL_TASK"
        if request.has_images or any(term in text for term in ["image", "screenshot", "diagram", "vision"]):
            return "VISION"
        if any(term in text for term in ["debug", "traceback", "stack trace", "fix error"]):
            return "DEBUGGING"
        if any(term in text for term in ["code", "function", "class", "refactor", "typescript", "python"]):
            return "CODING"
        if any(term in text for term in ["research", "search", "sources", "compare", "market"]):
            return "RESEARCH"
        if any(term in text for term in ["csv", "excel", "table", "analysis", "costing", "estimate"]):
            return "DATA_ANALYSIS"
        if any(term in text for term in ["translate", "sinhala", "japanese", "english"]):
            return "TRANSLATION"
        if any(term in text for term in ["summarize", "summary", "shorten"]):
            return "SUMMARIZATION"
        if any(term in text for term in ["plan", "agent", "workflow", "automate"]):
            return "AGENT_PLANNING"
        if any(term in text for term in ["story", "song", "script", "creative", "caption"]):
            return "CREATIVE_WRITING"
        if request.context_tokens > 24000 or len(request.message) > 24000:
            return "LONG_DOCUMENT"
        if len(request.message.split()) <= 20:
            return "FAST_CHAT"
        if any(term in text for term in ["reason", "think", "why", "strategy", "architecture"]):
            return "DEEP_REASONING"
        return "GENERAL_CHAT"

    def estimate_tokens(self, text: str) -> int:
        return max(1, (len(text) + 3) // 4)

    def estimate_cost(self, model: str, prompt_tokens: int, completion_tokens: int = 512) -> float:
        rows = []
        try:
            rows = self.catalog.models(refresh=False, limit=2000).get("models", [])
        except Exception:
            rows = []
        match = next((row for row in rows if row.get("id") == model), None)
        if not match:
            return 0.0
        try:
            prompt_price = float(match.get("pricing_prompt") or 0)
            completion_price = float(match.get("pricing_completion") or 0)
        except (TypeError, ValueError):
            return 0.0
        return round(prompt_tokens * prompt_price + completion_tokens * completion_price, 8)

    def log_usage(
        self,
        *,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        estimated_cost_usd: float,
        latency_seconds: float,
        success: bool,
        fallback_used: str = "",
        request_id: str = "",
    ) -> Path:
        path = self.config.resolved_usage_dir / "ai_usage_logs.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        exists = path.exists()
        with path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "timestamp",
                    "request_id",
                    "provider",
                    "model",
                    "prompt_tokens",
                    "completion_tokens",
                    "total_tokens",
                    "estimated_cost_usd",
                    "latency_seconds",
                    "success",
                    "fallback_used",
                ],
            )
            if not exists:
                writer.writeheader()
            writer.writerow(
                {
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "request_id": request_id or f"or_{uuid.uuid4().hex[:12]}",
                    "provider": provider,
                    "model": model,
                    "prompt_tokens": int(prompt_tokens),
                    "completion_tokens": int(completion_tokens),
                    "total_tokens": int(prompt_tokens) + int(completion_tokens),
                    "estimated_cost_usd": f"{float(estimated_cost_usd):.8f}",
                    "latency_seconds": f"{float(latency_seconds):.3f}",
                    "success": "yes" if success else "no",
                    "fallback_used": fallback_used,
                }
            )
        return path

    def _decision(
        self,
        request: RoutingRequest,
        provider: str,
        model: str,
        task: str,
        mode: str,
        fallbacks: list[str],
        reason: str,
        cloud_allowed: bool,
        estimated_tokens: int,
    ) -> RoutingDecision:
        cost = self.estimate_cost(model, estimated_tokens) if provider == "openrouter" else 0.0
        return RoutingDecision(
            request_id=f"route_{uuid.uuid4().hex[:12]}",
            provider=provider,
            model=model,
            task_category=task,
            mode=mode,
            fallbacks=fallbacks,
            reason=reason,
            cloud_allowed=cloud_allowed,
            estimated_prompt_tokens=estimated_tokens,
            estimated_cost_usd=cost,
        )

    def _profile_for(self, task: str, mode: str, request: RoutingRequest) -> str:
        if mode == "FAST" or request.speed == "fast" or task == "FAST_CHAT":
            return "fast"
        if mode == "LOWEST_COST" or request.budget == "low":
            return "fast"
        if mode == "BEST_QUALITY":
            if task in {"CODING", "DEBUGGING", "TOOL_USE"}:
                return "coding"
            if task == "VISION":
                return "vision"
            return "reasoning"
        if task in {"CODING", "DEBUGGING", "TOOL_USE"}:
            return "coding"
        if task in {"DEEP_REASONING", "RESEARCH", "AGENT_PLANNING"}:
            return "reasoning"
        if task == "VISION":
            return "vision"
        if task == "LONG_DOCUMENT":
            return "long_context"
        if task == "CREATIVE_WRITING":
            return "creative"
        return "balanced"

    def _model_profiles(self) -> dict[str, dict[str, Any]]:
        routing = self.catalog.routing_config()
        profiles = {key: dict(value) for key, value in MODEL_PROFILES.items()}
        auxiliary = routing.get("auxiliary_models", {})
        if isinstance(auxiliary, dict):
            for key, model in auxiliary.items():
                normalized = key.replace("-", "_").casefold()
                if normalized in profiles and str(model).strip():
                    profiles[normalized]["primary"] = str(model).strip()
        selected = routing.get("selected_model", "")
        if selected:
            profiles["balanced"]["primary"] = str(selected)
        return profiles

    def _routing_fallbacks(self) -> list[str]:
        routing = self.catalog.routing_config()
        fallbacks = routing.get("fallback_models", [])
        if not isinstance(fallbacks, list):
            return ["openrouter/auto"]
        cleaned = [str(item).strip() for item in fallbacks if str(item).strip()]
        return cleaned or ["openrouter/auto"]

    def _normalize_mode(self, mode: str) -> str:
        normalized = str(mode or "AUTO").strip().upper()
        return normalized if normalized in ROUTING_MODES else "AUTO"
