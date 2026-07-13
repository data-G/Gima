from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import Config


HARDWARE_PROFILE = {
    "cpu": "Intel Core i7-7700HQ @ 2.80GHz",
    "ram_gb": 16,
    "gpu_assumption": "Unknown; treat as CPU-first unless a dedicated NVIDIA GPU is confirmed.",
    "strategy": "Use 1B-7B quantized local models for unlimited private work; use cloud only for heavy video/frontier reasoning with consent.",
}


TOOLS_TABLE = [
    {
        "area": "Main AI chat",
        "tool": "LM Studio",
        "models": "Qwen 2.5 7B Q4 / Llama 3.2 3B",
        "update_possible": "Yes",
        "works_on_laptop": "Yes",
        "fit": "Yes",
        "speed": "Good for 3B, medium/slow for 7B",
        "notes": "Best easy local AI app. LM Studio has a built-in model downloader and can download supported models from Hugging Face. It can also run offline after models are downloaded.",
    },
    {
        "area": "AI backend/API",
        "tool": "Ollama",
        "models": "qwen2.5:7b, llama3.2:3b, mistral:7b",
        "update_possible": "Yes",
        "works_on_laptop": "Yes",
        "fit": "Yes",
        "speed": "Good to slow depending on model",
        "notes": "Best for building your own Gima-like local AI system. Ollama needs space for model files, which can become many GB.",
    },
    {
        "area": "ChatGPT-style local workspace",
        "tool": "Open WebUI + Ollama",
        "models": "Connect to Ollama",
        "update_possible": "Yes",
        "works_on_laptop": "Yes",
        "fit": "Yes",
        "speed": "Depends on model",
        "notes": "Best local web UI for many models, documents, tools, and workspace style usage.",
    },
    {
        "area": "Coding assistant",
        "tool": "Continue + Ollama",
        "models": "Qwen Coder 3B / 7B",
        "update_possible": "Yes",
        "works_on_laptop": "Yes",
        "fit": "Yes",
        "speed": "3B good, 7B slower",
        "notes": "Best local coding helper for VS Code/JetBrains style work.",
    },
    {
        "area": "Terminal coding agent",
        "tool": "Aider / OpenHands / Goose with Ollama",
        "models": "Qwen Coder 3B/7B, DeepSeek Coder small, Llama 3.2 3B for simple edits",
        "update_possible": "Yes",
        "works_on_laptop": "Yes",
        "fit": "Yes",
        "speed": "Good for small repos; use 3B for speed and 7B for better fixes",
        "notes": "Good for conversational coding: inspect files, propose patches, run tests, and explain changes. Keep destructive actions review-gated.",
    },
    {
        "area": "Code search and repo memory",
        "tool": "ripgrep + tree-sitter + local embeddings",
        "models": "nomic-embed-text / bge-small / all-MiniLM local embeddings",
        "update_possible": "Yes",
        "works_on_laptop": "Yes",
        "fit": "Yes",
        "speed": "Fast",
        "notes": "Lets Gima find functions, understand repo structure, remember decisions, and answer coding questions with file references.",
    },
    {
        "area": "PDF / document Q&A",
        "tool": "Open WebUI RAG or AnythingLLM",
        "models": "Qwen 7B + small embedding model",
        "update_possible": "Yes",
        "works_on_laptop": "Yes",
        "fit": "Yes",
        "speed": "Medium",
        "notes": "Good for your CVs, whitepapers, study PDFs, and job documents. Keep documents chunked and verify answers against sources.",
    },
    {
        "area": "Voice to text",
        "tool": "Whisper.cpp",
        "models": "Whisper base / small",
        "update_possible": "Yes",
        "works_on_laptop": "Yes",
        "fit": "Yes",
        "speed": "Base/small practical on CPU",
        "notes": "Use for voice notes, subtitles, Sinhala/English/Japanese transcription trials.",
    },
    {
        "area": "Live conversation AI",
        "tool": "Whisper.cpp + Ollama + Piper TTS",
        "models": "Whisper base/small + Llama 3.2 3B or Qwen 2.5 3B + Piper voice",
        "update_possible": "Yes",
        "works_on_laptop": "Yes",
        "fit": "Yes",
        "speed": "Good if short context and 3B model are used",
        "notes": "Best local speaking Gima path: listen, transcribe, answer with local chat model, speak response, and save transcript to memory.",
    },
    {
        "area": "Wake word / push-to-talk",
        "tool": "OpenWakeWord / push-to-talk hotkey",
        "models": "Small wake-word model or keyboard trigger",
        "update_possible": "Yes",
        "works_on_laptop": "Yes",
        "fit": "Yes",
        "speed": "Fast",
        "notes": "Use push-to-talk first for reliability. Add wake word later when false activations are tested.",
    },
    {
        "area": "Text to speech",
        "tool": "Piper TTS",
        "models": "Local voice models",
        "update_possible": "Yes",
        "works_on_laptop": "Yes",
        "fit": "Yes",
        "speed": "Good",
        "notes": "Local voice output without cloud credits.",
    },
    {
        "area": "Voice conversation UI",
        "tool": "Open WebUI voice mode / custom Gima browser microphone controls",
        "models": "Browser mic + Whisper.cpp + Piper + Ollama",
        "update_possible": "Yes",
        "works_on_laptop": "Yes",
        "fit": "Yes",
        "speed": "Good for turn-by-turn conversation",
        "notes": "Gives Gima a talking assistant experience: record, transcribe, chat, speak, store memory, and show code/output in the same interface.",
    },
    {
        "area": "Meeting and call assistant",
        "tool": "Whisper.cpp + diarization later",
        "models": "Whisper base/small; pyannote-style diarization only if resources allow",
        "update_possible": "Yes",
        "works_on_laptop": "Mostly",
        "fit": "Maybe",
        "speed": "Transcription practical; diarization can be heavy",
        "notes": "Useful for meeting notes, subtitles, action items, and conversation summaries. Keep private audio local by default.",
    },
    {
        "area": "Image generation",
        "tool": "ComfyUI or Fooocus",
        "models": "SD 1.5, SDXL if GPU exists",
        "update_possible": "Yes",
        "works_on_laptop": "Maybe",
        "fit": "Maybe",
        "speed": "CPU is very slow",
        "notes": "ComfyUI supports many workflows, but image/video generation is much better with GPU. Use cloud or low settings unless NVIDIA GPU is confirmed.",
    },
    {
        "area": "Video generation",
        "tool": "ComfyUI video workflows",
        "models": "AnimateDiff / LTX / Wan small",
        "update_possible": "Yes",
        "works_on_laptop": "Not practical without GPU",
        "fit": "No",
        "speed": "Very slow without GPU",
        "notes": "Your CPU + 16GB RAM is too weak for serious local video. Best path: local scene planning plus cloud/open video backend for renders.",
    },
    {
        "area": "Editing video",
        "tool": "CapCut / DaVinci Resolve",
        "models": "Normal editor",
        "update_possible": "Yes",
        "works_on_laptop": "Yes",
        "fit": "Yes",
        "speed": "Good for normal editing",
        "notes": "Best for TikTok/music videos after generating clips elsewhere.",
    },
    {
        "area": "Local knowledge base",
        "tool": "Obsidian + Ollama/Open WebUI",
        "models": "Markdown notes + local AI",
        "update_possible": "Yes",
        "works_on_laptop": "Yes",
        "fit": "Yes",
        "speed": "Good",
        "notes": "Good for building your Gima memory/knowledge system.",
    },
    {
        "area": "Automation and app control",
        "tool": "Python subprocess + AppleScript/Shortcuts + browser automation",
        "models": "Local planner model with review-gated tool calls",
        "update_possible": "Yes",
        "works_on_laptop": "Yes",
        "fit": "Yes",
        "speed": "Fast for simple actions",
        "notes": "Lets Gima open folders, run safe scripts, create files, and operate local apps after permission checks.",
    },
]


MODEL_SIZE_TABLE = [
    {"model_size": "1B-3B Q4", "fit": "Best", "use": "Fast drafts, routing, simple chat, privacy checks"},
    {"model_size": "4B Q4", "fit": "Good", "use": "Better daily local answers"},
    {"model_size": "7B Q4", "fit": "Usable", "use": "Best quality/speed balance for this 16GB laptop"},
    {"model_size": "9B Q4", "fit": "Maybe slow", "use": "Creative/careful writing if memory allows"},
    {"model_size": "14B Q4", "fit": "Possible but uncomfortable", "use": "Occasional slow reasoning only"},
    {"model_size": "30B+", "fit": "No", "use": "Use cloud or stronger hardware"},
]


INSTALL_ORDER = [
    {"priority": 1, "tool": "LM Studio", "purpose": "Easiest unlimited local chat and model testing"},
    {"priority": 2, "tool": "Ollama", "purpose": "Local model backend/API for Gima"},
    {"priority": 3, "tool": "Open WebUI", "purpose": "Local ChatGPT-style dashboard"},
    {"priority": 4, "tool": "Continue", "purpose": "Coding assistant"},
    {"priority": 5, "tool": "whisper.cpp", "purpose": "Audio/video transcription"},
    {"priority": 6, "tool": "Piper TTS", "purpose": "Local voice replies"},
    {"priority": 7, "tool": "OpenWakeWord or push-to-talk", "purpose": "Hands-free or reliable voice activation"},
    {"priority": 8, "tool": "Aider / OpenHands / Goose", "purpose": "Conversational coding agent with tests"},
    {"priority": 9, "tool": "ComfyUI", "purpose": "Image/video workflows only if GPU is confirmed"},
]


OLLAMA_COMMANDS = [
    "ollama pull llama3.2:3b",
    "ollama pull qwen2.5:3b",
    "ollama pull qwen2.5:7b",
    "ollama pull qwen2.5-coder:3b",
    "ollama pull qwen2.5-coder:7b",
    "ollama pull mistral:7b",
    "ollama pull nomic-embed-text",
]


SOURCES = [
    {
        "name": "LM Studio offline operation",
        "url": "https://lmstudio.ai/docs/app/offline",
        "note": "LM Studio says core functions can operate offline after model files are downloaded.",
    },
    {
        "name": "Ollama hardware support",
        "url": "https://docs.ollama.com/gpu",
        "note": "Ollama documents GPU support details; CPU use is possible but slower.",
    },
    {
        "name": "ComfyUI",
        "url": "https://github.com/comfy-org/ComfyUI",
        "note": "ComfyUI is a modular AI creation engine for image/video/audio workflows.",
    },
    {
        "name": "whisper.cpp",
        "url": "https://github.com/ggml-org/whisper.cpp",
        "note": "whisper.cpp is a lightweight C/C++ Whisper implementation for local transcription.",
    },
    {
        "name": "Piper TTS",
        "url": "https://github.com/rhasspy/piper",
        "note": "Piper is a fast local neural text-to-speech system.",
    },
    {
        "name": "OpenWakeWord",
        "url": "https://github.com/dscripka/openWakeWord",
        "note": "OpenWakeWord provides local wake-word detection for voice assistants.",
    },
    {
        "name": "Continue",
        "url": "https://github.com/continuedev/continue",
        "note": "Continue connects local or cloud models to coding workflows.",
    },
]


def local_ai_stack_payload(config: Config, *, write_files: bool = True) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "hardware": HARDWARE_PROFILE,
        "tools": TOOLS_TABLE,
        "model_sizes": MODEL_SIZE_TABLE,
        "install_order": INSTALL_ORDER,
        "ollama_commands": OLLAMA_COMMANDS,
        "sources": SOURCES,
        "truth": [
            "Unlimited free usage is realistic only for local/offline tools after download.",
            "This laptop should prioritize 1B-7B quantized models.",
            "A real local conversation AI needs a pipeline: microphone, STT, local chat model, memory write, TTS, and user-visible transcript.",
            "Conversational coding must be review-gated: inspect, patch, run tests, show diff, then ask before risky commands.",
            "Local video generation is not realistic without a suitable GPU; use local planning plus cloud/open backends for final renders.",
            "Current web facts and model availability should be rechecked before installing large downloads.",
        ],
    }
    if write_files:
        payload["files"] = _write_artifacts(config, payload)
    return payload


def _write_artifacts(config: Config, payload: dict[str, Any]) -> dict[str, str]:
    out_dir = config.resolved_hands_out_dir / "local_ai_stack"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "gima_local_ai_stack_i7_7700hq_16gb.csv"
    md_path = out_dir / "gima_local_ai_stack_i7_7700hq_16gb.md"
    json_path = out_dir / "gima_local_ai_stack_i7_7700hq_16gb.json"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["area", "tool", "update_possible", "models", "works_on_laptop", "fit", "speed", "notes"])
        writer.writeheader()
        writer.writerows(TOOLS_TABLE)
    md_path.write_text(_markdown(payload), encoding="utf-8")
    json_path.write_text(json.dumps({k: v for k, v in payload.items() if k != "files"}, indent=2), encoding="utf-8")
    return {"csv": str(csv_path), "markdown": str(md_path), "json": str(json_path)}


def _markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Gima Local AI Stack for i7-7700HQ / 16GB RAM",
        "",
        f"CPU: {HARDWARE_PROFILE['cpu']}",
        f"RAM: {HARDWARE_PROFILE['ram_gb']} GB",
        f"Strategy: {HARDWARE_PROFILE['strategy']}",
        "",
        "## Best Local Systems",
        "",
        "| Area | Best system | Update possible? | Best model/tool for your laptop | Works on your laptop? | Notes |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in TOOLS_TABLE:
        lines.append(f"| {row['area']} | {row['tool']} | {row['update_possible']} | {row['models']} | {row['works_on_laptop']} | {row['notes']} |")
    lines.extend(["", "## Model Size Reality", "", "| Model Size | Fit | Use |", "| --- | --- | --- |"])
    for row in MODEL_SIZE_TABLE:
        lines.append(f"| {row['model_size']} | {row['fit']} | {row['use']} |")
    lines.extend(["", "## Install Order", "", "| Priority | Tool | Purpose |", "| --- | --- | --- |"])
    for row in INSTALL_ORDER:
        lines.append(f"| {row['priority']} | {row['tool']} | {row['purpose']} |")
    lines.extend(["", "## Ollama Commands", "", "```bash", *OLLAMA_COMMANDS, "```", "", "## Sources"])
    for source in SOURCES:
        lines.append(f"- [{source['name']}]({source['url']}): {source['note']}")
    return "\n".join(lines) + "\n"
