from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FreeLlmProvider:
    name: str
    provider_id: str
    category: str
    free_models: str
    rpm: str
    daily_limit: str
    context_window: str
    openai_compatible: str
    credit_card: str
    data_training: str
    strengths: tuple[str, ...]
    risks: tuple[str, ...]
    best_for: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "provider_id": self.provider_id,
            "category": self.category,
            "free_models": self.free_models,
            "rpm": self.rpm,
            "daily_limit": self.daily_limit,
            "context_window": self.context_window,
            "openai_compatible": self.openai_compatible,
            "credit_card": self.credit_card,
            "data_training": self.data_training,
            "strengths": list(self.strengths),
            "risks": list(self.risks),
            "best_for": list(self.best_for),
        }


FREE_LLM_PROVIDERS: tuple[FreeLlmProvider, ...] = (
    FreeLlmProvider(
        name="OpenRouter",
        provider_id="openrouter",
        category="permanent_free",
        free_models="20+ multi-provider free models",
        rpm="20",
        daily_limit="50/day, 1,000/day with small top-up",
        context_window="Up to 1M depending on routed model",
        openai_compatible="Yes",
        credit_card="No",
        data_training="No",
        strengths=("model variety", "single key", "OpenAI-compatible routing", "failover"),
        risks=("router free-tier request caps", "native provider features may not all be exposed"),
        best_for=("model variety", "experimentation", "failover", "general chat", "coding"),
    ),
    FreeLlmProvider(
        name="Google AI Studio",
        provider_id="gemini",
        category="permanent_free",
        free_models="Gemini/Gemma variants",
        rpm="5-15",
        daily_limit="20-1,500/day depending on model",
        context_window="Up to 1M",
        openai_compatible="Partial",
        credit_card="No",
        data_training="Yes outside EU/UK/EEA on free tier",
        strengths=("long context", "multimodal input", "file/RAG features via native SDK"),
        risks=("data-training policy risk", "lower request volume", "native SDK needed for advanced features"),
        best_for=("long context", "research", "large documents", "multimodal", "rag"),
    ),
    FreeLlmProvider(
        name="Groq",
        provider_id="groq",
        category="permanent_free",
        free_models="Llama 3.3 70B, Mixtral, others",
        rpm="30",
        daily_limit="~1,000/day",
        context_window="128K",
        openai_compatible="Yes",
        credit_card="No",
        data_training="No",
        strengths=("very low latency", "high tokens per second", "OpenAI-compatible"),
        risks=("provider-specific quota", "model lineup narrower than routers"),
        best_for=("speed", "voice", "real-time chat", "latency"),
    ),
    FreeLlmProvider(
        name="Mistral Experiment",
        provider_id="mistral",
        category="permanent_free",
        free_models="Codestral, Mistral Small/Large",
        rpm="Variable",
        daily_limit="~1B tokens/month",
        context_window="32K-256K",
        openai_compatible="Yes",
        credit_card="No",
        data_training="Yes on Experiment tier",
        strengths=("large free monthly token budget", "strong coding models"),
        risks=("requires training opt-in", "privacy-sensitive work should use paid/no-training tier or local"),
        best_for=("coding", "volume", "refactoring", "developer tools"),
    ),
    FreeLlmProvider(
        name="Cerebras",
        provider_id="cerebras",
        category="permanent_free",
        free_models="Llama 3.3 70B, others",
        rpm="30",
        daily_limit="~1M tokens/day",
        context_window="Up to 1M",
        openai_compatible="Yes",
        credit_card="No",
        data_training="No",
        strengths=("throughput", "batch processing", "large-context options"),
        risks=("provider-specific quota and availability",),
        best_for=("batch", "throughput", "summarization", "data cleaning"),
    ),
    FreeLlmProvider(
        name="GitHub Models",
        provider_id="github_models",
        category="permanent_free",
        free_models="GPT-4o, Claude, Llama, Phi through GitHub/Azure",
        rpm="15",
        daily_limit="150-1,000/day",
        context_window="8K-128K",
        openai_compatible="Yes",
        credit_card="No",
        data_training="No",
        strengths=("frontier model testing", "GitHub account workflow", "playground"),
        risks=("GitHub/Azure account dependency", "daily request caps"),
        best_for=("frontier evaluation", "developer experiments", "coding"),
    ),
    FreeLlmProvider(
        name="Cloudflare Workers AI",
        provider_id="cloudflare_workers_ai",
        category="permanent_free",
        free_models="20+ edge-hosted models",
        rpm="High",
        daily_limit="~10K neurons/day",
        context_window="2K-8K",
        openai_compatible="Partial",
        credit_card="No",
        data_training="No",
        strengths=("edge deployment", "serverless app integration"),
        risks=("smaller context windows", "Cloudflare platform coupling"),
        best_for=("edge", "small tasks", "serverless", "classification"),
    ),
    FreeLlmProvider(
        name="Cohere Trial",
        provider_id="cohere",
        category="permanent_free",
        free_models="Command R+ trial API",
        rpm="10-20",
        daily_limit="~100/day",
        context_window="128K",
        openai_compatible="Partial",
        credit_card="No",
        data_training="No, non-commercial trial terms",
        strengths=("rag", "retrieval", "long context", "enterprise search"),
        risks=("non-commercial trial limits", "lower daily request budget"),
        best_for=("rag", "retrieval", "search", "long context"),
    ),
    FreeLlmProvider(
        name="Hugging Face",
        provider_id="huggingface",
        category="permanent_free",
        free_models="Large open-source model ecosystem",
        rpm="Variable",
        daily_limit="Community/rate-limited",
        context_window="Model dependent",
        openai_compatible="Partial",
        credit_card="No",
        data_training="No",
        strengths=("open-source model exploration", "specialized models"),
        risks=("variable reliability", "cold starts and model-specific APIs"),
        best_for=("open source", "specialized models", "experimentation"),
    ),
    FreeLlmProvider(
        name="NVIDIA NIM",
        provider_id="nvidia_nim",
        category="permanent_free",
        free_models="Nemotron, Llama variants",
        rpm="High",
        daily_limit="~1,000/day",
        context_window="128K",
        openai_compatible="Partial",
        credit_card="No",
        data_training="No",
        strengths=("hosted open models", "GPU inference", "developer evaluation"),
        risks=("NVIDIA account/platform dependency", "free-tier limits can change"),
        best_for=("open source", "evaluation", "gpu inference", "developer experiments"),
    ),
    FreeLlmProvider(
        name="Chutes",
        provider_id="chutes",
        category="permanent_free",
        free_models="Various OSS models",
        rpm="Variable",
        daily_limit="Community tier",
        context_window="Model dependent",
        openai_compatible="Yes",
        credit_card="No",
        data_training="No",
        strengths=("open-source hosting", "OpenAI-compatible", "model experimentation"),
        risks=("community-tier reliability", "provider and model availability may change"),
        best_for=("open source", "experimentation", "model variety"),
    ),
    FreeLlmProvider(
        name="SambaNova Trial",
        provider_id="sambanova",
        category="trial_credit",
        free_models="Llama 3.1 405B",
        rpm="Variable",
        daily_limit="$5 trial credit",
        context_window="128K",
        openai_compatible="Yes",
        credit_card="Yes",
        data_training="No",
        strengths=("large open-weight model", "frontier-scale open model evaluation"),
        risks=("trial credit, not a permanent free tier", "credit card required"),
        best_for=("large model evaluation", "reasoning", "open source"),
    ),
    FreeLlmProvider(
        name="Vercel AI Gateway",
        provider_id="vercel_ai_gateway",
        category="byok_gateway",
        free_models="Multi-provider gateway with BYOK",
        rpm="Variable",
        daily_limit="Depends on backend provider",
        context_window="Varies by backend",
        openai_compatible="Yes",
        credit_card="No",
        data_training="Depends on backend provider",
        strengths=("app integration", "provider abstraction", "frontend/serverless workflow"),
        risks=("not a standalone free model pool", "privacy and cost depend on connected provider keys"),
        best_for=("app integration", "serverless", "failover", "developer tools"),
    ),
    FreeLlmProvider(
        name="DeepSeek Trial",
        provider_id="deepseek",
        category="trial_credit",
        free_models="DeepSeek R1/chat trial allocation",
        rpm="Variable",
        daily_limit="Trial tokens/credits",
        context_window="Model dependent",
        openai_compatible="Yes",
        credit_card="Varies",
        data_training="Check current terms",
        strengths=("reasoning", "math", "multi-step analysis"),
        risks=("trial is not permanent", "terms and limits can change"),
        best_for=("reasoning", "math", "logic", "evaluation"),
    ),
)


def free_llm_plan(task: str = "", *, privacy: str = "balanced", limit: int = 6) -> dict[str, Any]:
    task = " ".join(task.strip().split())
    privacy = privacy.strip().casefold() or "balanced"
    scored = []
    for provider in FREE_LLM_PROVIDERS:
        score, reasons = _score_provider(provider, task, privacy)
        scored.append((score, provider, reasons))
    scored.sort(key=lambda item: (item[0], item[1].name), reverse=True)
    max_rows = max(1, min(int(limit), len(scored)))
    recommendations = [
        {
            **provider.as_dict(),
            "score": score,
            "reasons": reasons,
        }
        for score, provider, reasons in scored[:max_rows]
    ]
    return {
        "task": task,
        "privacy": privacy,
        "source": "OpenRouter blog pasted by user: Free LLM APIs Compared, 2026-06-15",
        "recommendations": recommendations,
        "rules": [
            "Use local inference for private files, customer data, secrets, and proprietary code unless CLOUD_ALLOWED=true and the user approves.",
            "Prefer no-training providers for sensitive work: local, OpenRouter, Groq, Cerebras, or paid no-training tiers.",
            "Use routers for variety/failover; use direct providers when native features or full native quota matter.",
            "Treat trial credits as evaluation budget, not production capacity.",
        ],
    }


def free_llm_matrix() -> list[dict[str, Any]]:
    return [provider.as_dict() for provider in FREE_LLM_PROVIDERS]


def _score_provider(provider: FreeLlmProvider, task: str, privacy: str) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    text = task.casefold()
    if not text:
        if provider.provider_id == "openrouter":
            score += 8
            reasons.append("best default for model variety and one-key experiments")
        if provider.provider_id in {"groq", "cerebras"}:
            score += 4
            reasons.append("good no-training direct fallback")
    keyword_groups = {
        "long context": {"long", "context", "pdf", "book", "large", "document", "codebase", "rag", "research"},
        "speed": {"fast", "speed", "latency", "voice", "realtime", "real-time", "chat"},
        "coding": {"code", "coding", "refactor", "debug", "developer", "repo", "programming"},
        "reasoning": {"reason", "math", "logic", "deduction", "analysis"},
        "batch": {"batch", "bulk", "many", "summarize", "summarization", "data cleaning"},
        "edge": {"edge", "worker", "serverless", "cloudflare"},
        "open source": {"open", "oss", "local", "open-source", "model"},
    }
    provider_terms = set(provider.best_for) | set(provider.strengths)
    provider_blob = " ".join(provider_terms).casefold()
    for label, terms in keyword_groups.items():
        if any(term in text for term in terms) and label in provider_blob:
            score += 5
            reasons.append(f"matches {label} workload")
    if provider.openai_compatible == "Yes":
        score += 2
        reasons.append("OpenAI-compatible endpoint")
    if provider.credit_card == "No":
        score += 1
    if provider.data_training == "No":
        score += 3
        if privacy in {"strict", "private", "privacy"}:
            score += 5
            reasons.append("no-training policy is safer for privacy-sensitive work")
    elif "Yes" in provider.data_training:
        if privacy in {"strict", "private", "privacy"}:
            score -= 8
            reasons.append("privacy penalty: free tier may use prompts/responses for training")
        else:
            reasons.append("watch data-training terms before using private data")
    if provider.category == "trial_credit":
        score -= 2
        reasons.append("trial credit is useful for evaluation, not ongoing free use")
    if provider.provider_id == "openrouter":
        score += 2
        reasons.append("can route across multiple providers with failover")
    return score, reasons[:5]
