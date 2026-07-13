from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import Config
from .services import OpenRouterCatalog


USE_CASES = [
    {
        "area": "Main powerful brain",
        "paid_model_type": "GPT / Claude / Gemini flagship models",
        "need": "Deep reasoning, business planning, CVs, research, complex documents",
        "preferred": ("openai", "anthropic", "google"),
        "keywords": ("gpt", "claude", "gemini", "opus", "sonnet", "pro"),
        "local_fallback": "Qwen 7B Q4 in LM Studio/Ollama",
        "notes": "Use paid only for important tasks.",
    },
    {
        "area": "Cheap daily assistant",
        "paid_model_type": "DeepSeek / Qwen / Mistral / GLM models",
        "need": "Normal chat, summaries, translations, Sinhala/English/Japanese writing",
        "preferred": ("deepseek", "qwen", "mistral", "z-ai", "glm"),
        "keywords": ("deepseek", "qwen", "mistral", "glm", "flash", "mini", "small"),
        "local_fallback": "Qwen 3B/7B",
        "notes": "Best cost-saving layer.",
    },
    {
        "area": "Coding agent",
        "paid_model_type": "Claude / GPT / DeepSeek / GLM / Qwen Coder",
        "need": "Codex-style app building, debugging, refactoring",
        "preferred": ("anthropic", "openai", "deepseek", "qwen", "z-ai"),
        "keywords": ("coder", "code", "claude", "gpt", "deepseek", "qwen", "glm", "mimo", "minimax"),
        "local_fallback": "Qwen Coder 3B/7B",
        "notes": "OpenRouter coding rankings change; compare developer-usage collections before pinning. Watch models such as Mimo, Minimax, GLM, DeepSeek, Qwen Coder, and Claude Opus/Sonnet classes.",
    },
    {
        "area": "Web research/report writing",
        "paid_model_type": "GPT / Gemini / Claude with web/search if supported",
        "need": "People/company/article research, reports, market research",
        "preferred": ("openai", "google", "anthropic", "perplexity"),
        "keywords": ("gpt", "gemini", "claude", "sonar", "search", "research"),
        "local_fallback": "Local model + manual browser",
        "notes": "Web search usually costs extra or needs a search tool/API. Cite sources and separate facts from inference.",
    },
    {
        "area": "Long documents",
        "paid_model_type": "Gemini / Claude long-context models",
        "need": "Long PDFs, whitepapers, contracts, CV packs",
        "preferred": ("google", "anthropic", "openai", "qwen"),
        "keywords": ("gemini", "claude", "long", "context", "qwen"),
        "local_fallback": "Open WebUI RAG with small chunks",
        "notes": "Use when local 16GB RAM is not enough.",
    },
    {
        "area": "Vision/image understanding",
        "paid_model_type": "GPT/Gemini/Claude vision models",
        "need": "Screenshots, receipts, diagrams, product photos",
        "preferred": ("openai", "google", "anthropic", "qwen"),
        "keywords": ("gpt", "gemini", "claude", "vision", "vl", "qwen"),
        "local_fallback": "Limited local vision model",
        "notes": "Best for image-based tasks, screenshots, UI debugging, product analysis, and diagrams.",
    },
    {
        "area": "Image generation",
        "paid_model_type": "OpenRouter image models if available, or direct image API",
        "need": "Covers, posters, product images",
        "preferred": ("openai", "google", "black-forest-labs", "stability"),
        "keywords": ("image", "imagen", "flux", "dall", "sdxl"),
        "local_fallback": "ComfyUI/Fooocus if GPU exists",
        "notes": "This laptop is weak for local image generation; prefer cloud only with consent and budget caps.",
    },
    {
        "area": "Video generation",
        "paid_model_type": "OpenRouter video endpoint/models if available, or external video APIs",
        "need": "AI music videos, scene clips, TikTok videos",
        "preferred": ("google", "minimax", "runway", "luma"),
        "keywords": ("veo", "video", "hailuo", "runway", "luma"),
        "local_fallback": "Local not practical; use local planning plus CapCut/DaVinci editing",
        "notes": "Use submit, poll status, and download flow for video APIs. Require rights-safe prompts/assets and explicit credit-spend consent.",
    },
    {
        "area": "Speech/audio",
        "paid_model_type": "Dedicated speech APIs or local Whisper",
        "need": "Voice assistant, transcription, subtitles, speech output",
        "preferred": ("openai", "microsoft", "elevenlabs", "mistralai"),
        "keywords": ("whisper", "tts", "speech", "audio", "voice", "mai"),
        "local_fallback": "whisper.cpp + Piper",
        "notes": "Use local Whisper first to save cost; use paid speech for high quality voices or hard languages.",
    },
    {
        "area": "Embeddings/RAG",
        "paid_model_type": "Cheap embedding models",
        "need": "Search files, memory, knowledge base",
        "preferred": ("openai", "cohere", "jina", "voyage"),
        "keywords": ("embedding", "embed", "rerank", "jina", "voyage", "cohere"),
        "local_fallback": "Local embeddings",
        "notes": "Use cheap embeddings plus paid LLM only for the final answer when needed.",
    },
    {
        "area": "Agent/tool calling",
        "paid_model_type": "Models with tool/function calling",
        "need": "Gima agents, file tools, search tools, app actions",
        "preferred": ("openai", "anthropic", "google", "qwen"),
        "keywords": ("tool", "function", "gpt", "claude", "gemini", "qwen"),
        "local_fallback": "Ollama local tools",
        "notes": "OpenRouter can pass tools when the underlying model supports tool/function calling. Keep actions review-gated and reversible.",
    },
]


def paid_openrouter_plan(config: Config, *, refresh: bool = False, write_files: bool = True) -> dict[str, Any]:
    catalog = OpenRouterCatalog(config)
    try:
        model_payload = catalog.models(refresh=refresh, limit=1000)
        source = model_payload.get("source", "cache")
        models = model_payload.get("models", [])
    except Exception as error:
        source = f"planner_static_after_catalog_error: {error}"
        models = []
    rows = [_recommend_for_case(use_case, models) for use_case in USE_CASES]
    payload: dict[str, Any] = {
        "source": source,
        "catalog_count": len(models),
        "architecture": [
            {"layer": "Free local daily AI", "tool": "Ollama + Open WebUI + LM Studio", "purpose": "Unlimited/private daily work"},
            {"layer": "Cheap OpenRouter", "tool": "DeepSeek/Qwen/Mistral/GLM class models", "purpose": "Low-cost cloud help when local answer is weak"},
            {"layer": "Premium OpenRouter", "tool": "GPT/Claude/Gemini class models", "purpose": "Hard reasoning, coding, long docs, vision"},
            {"layer": "Media APIs", "tool": "OpenRouter video/speech/image routes or approved providers", "purpose": "Heavy creative generation"},
        ],
        "recommendations": rows,
        "cost_controls": [
            "Start with $10-$20 credits.",
            "Use separate OpenRouter keys for testing, Gima, and coding.",
            "Set key limits/budgets so a bug cannot spend all credits.",
            "Use local first, cheap paid second, premium paid only for hard tasks.",
            "Pin exact model IDs for important workflows.",
            "Keep provider data_collection=deny where possible.",
            "Log model, cost, latency, and output path for every paid call.",
        ],
        "rules": [
            "Do not send private files to cloud unless CLOUD_ALLOWED=true and the user approves.",
            "Use local fallback for drafts, privacy checks, and unlimited cheap work.",
            "Use OpenRouter model catalog refresh before relying on pricing or availability.",
            "Video/image/speech can spend credits; require explicit consent before generation.",
        ],
        "source_notes": [
            "OpenRouter public models endpoint: https://openrouter.ai/api/v1/models",
            "OpenRouter docs index: https://openrouter.ai/docs/llms.txt",
            "OpenRouter routing docs: https://openrouter.ai/docs/guides/routing/routers/auto-router",
        ],
    }
    if write_files:
        payload["files"] = _write_artifacts(config, payload)
    return payload


def _recommend_for_case(use_case: dict[str, Any], models: list[dict[str, Any]]) -> dict[str, Any]:
    scored = []
    for model in models:
        if model.get("free"):
            continue
        score, reasons = _score_model(use_case, model)
        if score > 0:
            scored.append((score, model, reasons))
    scored.sort(key=lambda item: (item[0], -_price_score(item[1]), str(item[1].get("id", ""))), reverse=True)
    top = [
        {
            "model": item[1].get("id", ""),
            "name": item[1].get("name", ""),
            "provider": item[1].get("provider", ""),
            "context_length": item[1].get("context_length", 0),
            "input_modalities": item[1].get("input_modalities", []),
            "output_modalities": item[1].get("output_modalities", []),
            "pricing_prompt": item[1].get("pricing_prompt", ""),
            "pricing_completion": item[1].get("pricing_completion", ""),
            "score": item[0],
            "reasons": item[2],
        }
        for item in scored[:5]
    ]
    return {
        "area": use_case["area"],
        "paid_model_type": use_case["paid_model_type"],
        "need": use_case["need"],
        "top_models": top,
        "first_choice": top[0]["model"] if top else "openrouter/auto",
        "cheap_choice": _cheap_choice(use_case, scored),
        "local_fallback": use_case["local_fallback"],
        "note": use_case["notes"],
        "freshness_warning": "Refresh OpenRouter catalog before purchase; model prices and availability can change.",
    }


def _score_model(use_case: dict[str, Any], model: dict[str, Any]) -> tuple[int, list[str]]:
    model_id = str(model.get("id", "")).casefold()
    name = str(model.get("name", "")).casefold()
    provider = str(model.get("provider", "")).casefold()
    blob = f"{model_id} {name} {provider}"
    inputs = {str(item).casefold() for item in model.get("input_modalities", [])}
    outputs = {str(item).casefold() for item in model.get("output_modalities", [])}
    score = 0
    reasons: list[str] = []
    if provider in use_case["preferred"]:
        score += 6
        reasons.append(f"preferred provider: {provider}")
    for keyword in use_case["keywords"]:
        if keyword in blob:
            score += 3
            reasons.append(f"matches keyword: {keyword}")
            break
    area = use_case["area"].casefold()
    if "vision" in area and "image" in inputs:
        score += 8
        reasons.append("supports image input")
    if "image generation" in area and "image" in outputs:
        score += 8
        reasons.append("supports image output")
    if "video generation" in area and "video" in outputs:
        score += 10
        reasons.append("supports video output")
    if "speech" in area and ("audio" in inputs or "speech" in outputs or "transcription" in outputs):
        score += 8
        reasons.append("matches audio/speech modality")
    if "long documents" in area and int(model.get("context_length") or 0) >= 100_000:
        score += 7
        reasons.append("large context window")
    if "coding" in area and any(term in blob for term in ["code", "coder", "claude", "deepseek", "qwen", "glm"]):
        score += 4
        reasons.append("coding-oriented model name/provider")
    if "cheap" in area:
        price = _price_score(model)
        if 0 < price <= 1.5:
            score += 6
            reasons.append("low listed token price")
    if int(model.get("context_length") or 0) >= 32_000:
        score += 1
    return score, reasons[:5]


def _price_score(model: dict[str, Any]) -> float:
    try:
        prompt = float(model.get("pricing_prompt") or 0)
        completion = float(model.get("pricing_completion") or 0)
        return (prompt + completion) * 1_000_000
    except (TypeError, ValueError):
        return 999999.0


def _cheap_choice(use_case: dict[str, Any], scored: list[tuple[int, dict[str, Any], list[str]]]) -> str:
    affordable = [
        item for item in scored if 0 < _price_score(item[1]) <= 2.0 and any(key in str(item[1].get("id", "")).casefold() for key in ["deepseek", "qwen", "mistral", "glm", "gemini"])
    ]
    if affordable:
        affordable.sort(key=lambda item: (_price_score(item[1]), -item[0]))
        return str(affordable[0][1].get("id", ""))
    return "Use local fallback first, then openrouter/auto with a budget cap"


def _write_artifacts(config: Config, payload: dict[str, Any]) -> dict[str, str]:
    out_dir = config.resolved_hands_out_dir / "openrouter_paid_planner"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "gima_openrouter_paid_model_plan.csv"
    md_path = out_dir / "gima_openrouter_paid_model_plan.md"
    json_path = out_dir / "gima_openrouter_paid_model_plan.json"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["area", "paid_model_type", "need", "first_choice", "cheap_choice", "local_fallback", "notes", "top_models"])
        writer.writeheader()
        for row in payload["recommendations"]:
            writer.writerow(
                {
                    "area": row["area"],
                    "paid_model_type": row["paid_model_type"],
                    "need": row["need"],
                    "first_choice": row["first_choice"],
                    "cheap_choice": row["cheap_choice"],
                    "local_fallback": row["local_fallback"],
                    "notes": row["note"],
                    "top_models": ", ".join(model["model"] for model in row["top_models"]),
                }
            )
    md_path.write_text(_markdown(payload), encoding="utf-8")
    json_path.write_text(json.dumps({k: v for k, v in payload.items() if k != "files"}, indent=2), encoding="utf-8")
    return {"csv": str(csv_path), "markdown": str(md_path), "json": str(json_path)}


def _markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Gima OpenRouter Paid Model Plan",
        "",
        f"Catalog source: {payload['source']}",
        f"Catalog models considered: {payload['catalog_count']}",
        "",
        "## Recommended Architecture",
        "",
        "| Layer | Tool | Purpose |",
        "| --- | --- | --- |",
    ]
    for row in payload["architecture"]:
        lines.append(f"| {row['layer']} | {row['tool']} | {row['purpose']} |")
    lines.extend(["", "## Model Routing Table", "", "| Area | Best paid API model type | Use in Gima | First choice | Cheap choice | Local fallback | Notes |", "| --- | --- | --- | --- | --- | --- | --- |"])
    for row in payload["recommendations"]:
        lines.append(f"| {row['area']} | {row['paid_model_type']} | {row['need']} | {row['first_choice']} | {row['cheap_choice']} | {row['local_fallback']} | {row['note']} |")
    lines.extend(["", "## Cost Controls", ""])
    lines.extend(f"- {item}" for item in payload["cost_controls"])
    lines.extend(["", "## Rules", ""])
    lines.extend(f"- {item}" for item in payload["rules"])
    return "\n".join(lines) + "\n"
