from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import Config
from .services import OpenRouterCatalog


@dataclass(frozen=True)
class CouncilCandidate:
    name: str
    provider: str
    model: str
    modality: tuple[str, ...]
    location: str
    status: str
    strengths: tuple[str, ...]
    risks: tuple[str, ...]
    score: int = 0
    reasons: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "provider": self.provider,
            "model": self.model,
            "modality": list(self.modality),
            "location": self.location,
            "status": self.status,
            "strengths": list(self.strengths),
            "risks": list(self.risks),
            "score": self.score,
            "reasons": list(self.reasons),
        }


class ModelCouncil:
    """Local planner for choosing models before spending cloud calls."""

    QVAC_LLAMA_1B = Path("/Users/gimhangunarathne/.qvac/models/f2bade0bc5cd4a8c_Llama-3.2-1B-Instruct-Q4_0.gguf")
    QWYTHOS_URL = "https://huggingface.co/empero-ai/Qwythos-9B-Claude-Mythos-5-1M-GGUF"

    def __init__(self, config: Config):
        self.config = config

    def plan(self, request: str, *, attachments: list[str] | None = None, limit: int = 8) -> dict[str, Any]:
        request = " ".join(request.strip().split())
        attachment_list = [item for item in attachments or [] if item]
        needs = self._needs(request, attachment_list)
        scored = [self._score(candidate, needs) for candidate in self._candidates()]
        scored.sort(key=lambda row: (row.score, row.name), reverse=True)
        recommendations = scored[: max(1, min(limit, len(scored)))]
        winner = recommendations[0]
        return {
            "request": request,
            "attachments": attachment_list,
            "needs": needs,
            "winner": winner.as_dict(),
            "recommendations": [candidate.as_dict() for candidate in recommendations],
            "interaction_plan": self._interaction_plan(needs, recommendations),
            "safety": [
                "Local/private files stay on local models unless CLOUD_ALLOWED=true and the user approves cloud routing.",
                "Cloud model council calls should be bounded by provider quota and cost limits.",
                "Speech/video generation can spend credits and must require explicit consent.",
                "Do not store or print API keys in prompts, logs, or generated reports.",
            ],
        }

    def _candidates(self) -> list[CouncilCandidate]:
        local_path = Path(self.config.model.model_path).expanduser()
        current_status = "installed" if local_path.exists() else "configured_missing"
        qvac_status = "installed" if self.QVAC_LLAMA_1B.exists() else "missing"
        routing = OpenRouterCatalog(self.config).routing_config()
        selected = str(routing.get("selected_model", "") or self.config.teacher_models.openrouter_model)
        fallbacks = [str(item) for item in routing.get("fallback_models", []) if str(item).strip()]
        return [
            CouncilCandidate(
                name="Gima current local model",
                provider="local",
                model=self.config.model.model,
                modality=("text", "private"),
                location=str(local_path),
                status=current_status,
                strengths=("privacy", "offline fallback", "low cost"),
                risks=("small context", "lower reasoning quality than frontier models"),
            ),
            CouncilCandidate(
                name="QVAC Llama 3.2 1B local",
                provider="local",
                model="f2bade0bc5cd4a8c_Llama-3.2-1B-Instruct-Q4_0.gguf",
                modality=("text", "fast", "private"),
                location=str(self.QVAC_LLAMA_1B),
                status=qvac_status,
                strengths=("fast local draft", "private", "low memory use"),
                risks=("very small model", "needs council review for hard tasks"),
            ),
            CouncilCandidate(
                name="Qwythos 9B Claude Mythos GGUF",
                provider="local_candidate",
                model="empero-ai/Qwythos-9B-Claude-Mythos-5-1M-GGUF",
                modality=("text", "creative", "long_context_candidate"),
                location=self.QWYTHOS_URL,
                status="candidate_download_review_license",
                strengths=("creative writing", "larger local model candidate", "GGUF local-first path"),
                risks=("not installed here yet", "license and hardware fit must be reviewed"),
            ),
            CouncilCandidate(
                name="OpenRouter selected chat model",
                provider="openrouter",
                model=selected,
                modality=("text", "vision_possible", "routing"),
                location="https://openrouter.ai/api/v1/chat/completions",
                status="available_if_key_and_cloud_allowed",
                strengths=("stronger reasoning", "model fallback", "provider routing"),
                risks=("cloud privacy/cost", "requires key and CLOUD_ALLOWED=true"),
            ),
            CouncilCandidate(
                name="OpenRouter fallback pool",
                provider="openrouter",
                model=", ".join(fallbacks) or "openrouter/auto, openrouter/free",
                modality=("text", "fallback", "routing"),
                location=str(routing.get("routing_path", "")),
                status="configured",
                strengths=("several models can be tried", "failover", "cost/rate resilience"),
                risks=("quality varies by routed model", "cloud privacy/cost"),
            ),
            CouncilCandidate(
                name="Microsoft MAI Voice 2",
                provider="openrouter",
                model="microsoft/mai-voice-2",
                modality=("speech", "tts", "audio_output"),
                location="https://openrouter.ai/api/v1/audio/speech",
                status="available_if_key_and_cloud_allowed",
                strengths=("expressive TTS", "Azure voice style controls", "mp3 output"),
                risks=("cloud cost", "voice availability varies"),
            ),
            CouncilCandidate(
                name="OpenRouter STT",
                provider="openrouter",
                model="openai/whisper-large-v3",
                modality=("speech", "stt", "audio_input"),
                location="https://openrouter.ai/api/v1/audio/transcriptions",
                status="available_if_key_and_cloud_allowed",
                strengths=("audio transcription", "multipart or base64 input", "usage metadata"),
                risks=("cloud cost", "large audio should be split"),
            ),
            CouncilCandidate(
                name="OpenRouter multimodal/video route",
                provider="openrouter",
                model="openrouter/auto or chosen multimodal model",
                modality=("image", "pdf", "audio", "video", "multimodal"),
                location="https://openrouter.ai/models",
                status="planner_only_until_model_selected",
                strengths=("vision/PDF/audio/video-capable routing", "single gateway"),
                risks=("not all models support all modalities", "large files cost more"),
            ),
        ]

    def _needs(self, request: str, attachments: list[str]) -> dict[str, bool]:
        text = request.casefold()
        joined = " ".join(attachments).casefold()
        return {
            "private": any(word in text for word in ["private", "secret", "local", "own code", "company"]),
            "fast": any(word in text for word in ["fast", "quick", "small", "low latency", "voice chat"]),
            "reasoning": any(word in text for word in ["reason", "decide", "compare", "analyze", "better", "council"]),
            "creative": any(word in text for word in ["story", "song", "lyrics", "creative", "mythos"]),
            "speech_out": any(word in text for word in ["speak", "speech", "tts", "voice output", "mai voice"]),
            "speech_in": any(word in text for word in ["transcribe", "stt", "audio input"]) or any(joined.endswith(ext) for ext in [".mp3", ".wav", ".m4a"]),
            "vision": any(word in text for word in ["image", "vision", "photo", "ocr"]) or any(ext in joined for ext in [".png", ".jpg", ".jpeg"]),
            "video": any(word in text for word in ["video", "movie", "lip sync", "veo"]),
            "long_context": any(word in text for word in ["long", "1m", "pdf", "book", "large", "many files"]),
        }

    def _score(self, candidate: CouncilCandidate, needs: dict[str, bool]) -> CouncilCandidate:
        score = 0
        reasons: list[str] = []
        tags = set(candidate.modality) | set(candidate.strengths)
        if needs["private"] and candidate.provider == "local":
            score += 8
            reasons.append("private/local request favors local model")
        if needs["fast"] and ("fast" in tags or candidate.name.startswith("QVAC")):
            score += 6
            reasons.append("fast request favors small local model")
        if needs["reasoning"] and candidate.provider == "openrouter" and "text" in tags:
            score += 5
            reasons.append("reasoning/comparison favors stronger routed model")
        if needs["creative"] and ("creative" in tags or "Qwythos" in candidate.name):
            score += 5
            reasons.append("creative request matches creative/local candidate")
        if needs["speech_out"] and "tts" in tags:
            score += 10
            reasons.append("speech output request requires TTS model")
        if needs["speech_in"] and "stt" in tags:
            score += 10
            reasons.append("audio transcription request requires STT model")
        if needs["vision"] and ("vision_possible" in tags or "multimodal" in tags):
            score += 6
            reasons.append("image/vision request needs multimodal model")
        if needs["video"] and ("video" in tags or "multimodal" in tags):
            score += 5
            reasons.append("video request needs multimodal/video route")
        if needs["long_context"] and ("long_context_candidate" in tags or candidate.provider == "openrouter"):
            score += 4
            reasons.append("long-context request needs larger context")
        if candidate.status == "installed":
            score += 3
            reasons.append("installed now")
        if candidate.status.startswith("available_if"):
            score -= 1
            reasons.append("requires key, consent, and CLOUD_ALLOWED=true")
        if candidate.status.startswith("candidate"):
            score -= 3
            reasons.append("candidate only until installed/reviewed")
        return CouncilCandidate(
            **{**candidate.as_dict(), "modality": tuple(candidate.modality), "strengths": tuple(candidate.strengths), "risks": tuple(candidate.risks), "score": score, "reasons": tuple(reasons)}
        )

    def _interaction_plan(self, needs: dict[str, bool], recommendations: list[CouncilCandidate]) -> list[str]:
        names = [candidate.name for candidate in recommendations[:3]]
        steps = [
            f"1. Draft with {names[0]} because it scored highest for this request.",
            "2. If cloud is allowed, ask one stronger OpenRouter text model to critique or improve the draft.",
            "3. Let a lightweight local model check privacy, formatting, and whether the answer follows the user request.",
            "4. Choose the final answer by task score: correctness, speed, privacy, cost, and modality fit.",
        ]
        if needs["speech_out"]:
            steps.append("5. Use Microsoft MAI Voice 2 only after the text answer is approved for speech output.")
        if needs["speech_in"]:
            steps.append("5. Transcribe audio first, then send only the transcript to the text council when possible.")
        return steps
