from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .brain_index import rebuild_brain_csv
from .config import Config
from .memory import MemoryStore, Record
from .services import dependency_report


@dataclass(frozen=True)
class HardwareProfile:
    os: str
    machine: str
    cpu: str
    cpu_cores: int
    memory_gb: float
    local_ai_tier: str
    recommended_model: str
    strategy: str


def build_hardware_profile() -> HardwareProfile:
    memory_bytes = _sysctl_int("hw.memsize")
    cpu_cores = _sysctl_int("hw.ncpu") or _safe_int(platform.processor()) or 0
    cpu_name = _sysctl_text("machdep.cpu.brand_string") or platform.processor() or platform.machine()
    memory_gb = round(memory_bytes / (1024**3), 1) if memory_bytes else 0.0
    tier = _local_ai_tier(memory_gb, cpu_cores, platform.machine())
    return HardwareProfile(
        os=f"{platform.system()} {platform.release()}",
        machine=platform.machine(),
        cpu=cpu_name.strip(),
        cpu_cores=cpu_cores,
        memory_gb=memory_gb,
        local_ai_tier=tier,
        recommended_model=_recommended_model(tier),
        strategy=_recommended_strategy(tier),
    )


def build_doctor_report(config: Config, brain_status: dict[str, Any] | None = None) -> dict[str, Any]:
    hardware = build_hardware_profile()
    deps = dependency_report()
    brain = brain_status or {}
    checks = _doctor_checks(config, deps, brain, hardware)
    next_actions = [check["fix"] for check in checks if check["status"] != "ok"][:8]
    active_level = getattr(config.model, "active_level", "")
    active_model = getattr(config.model, "model", "")
    effective_strategy = _effective_model_strategy(active_level, active_model, hardware.strategy)
    readiness_score = round(
        100 * sum(1 for check in checks if check["status"] == "ok") / max(1, len(checks))
    )
    return {
        "hardware": hardware.__dict__,
        "readiness_score": readiness_score,
        "mode": hardware.local_ai_tier,
        "strategy": effective_strategy,
        "recommended_model": hardware.recommended_model,
        "active_model": active_model,
        "active_level": active_level,
        "dependencies": deps,
        "checks": checks,
        "next_actions": next_actions,
        "improvement_plan": _improvement_plan(config, hardware, deps, brain),
        "growth_plan": _growth_plan(hardware),
        "hardware_upgrade_plan": _hardware_upgrade_plan(hardware),
        "legal_earning_plan": _legal_earning_plan(),
        "master_ai_director_plan": _master_ai_director_plan(hardware, effective_strategy),
        "autonomy_boundaries": _autonomy_boundaries(),
        "criticism_defense_matrix": _criticism_defense_matrix(),
        "daily_improvement_plan": build_daily_improvement_plan(config, brain),
        "ai_era_requirements": build_ai_era_requirements(config, brain),
        "own_model_plan": build_own_model_plan(config, brain),
    }


def build_daily_improvement_plan(config: Config, brain_status: dict[str, Any] | None = None) -> dict[str, Any]:
    hardware = build_hardware_profile()
    brain = brain_status or {}
    today = datetime.now().astimezone().date().isoformat()
    return {
        "kind": "gima_daily_improvement_plan",
        "date": today,
        "north_star": "Become a world-class local-first AI by improving one measured capability every day.",
        "pc_strategy": hardware.strategy,
        "success_rule": "Learn one useful thing, build one real artifact, test it, log it, and choose tomorrow's improvement.",
        "daily_actions": [
            {
                "track": "Reliability",
                "action": "Run doctor/status, verify brain readiness, memory rows, API bindings, downloads, and outputs.",
                "done_when": "Doctor report is saved and no critical startup/tool error is hidden.",
            },
            {
                "track": "Knowledge",
                "action": "Learn one source-backed AI/business/media lesson and rebuild brain.csv.",
                "done_when": "New learning has source, timestamp, review status, and appears in brain search.",
            },
            {
                "track": "Artifact",
                "action": "Create one real file bundle: Excel/PDF/JPG report, media draft, code plan, or research dossier.",
                "done_when": "Files exist in hands/out, open correctly, and include assumptions/provenance.",
            },
            {
                "track": "Legal earning",
                "action": "Prepare one legal earning asset: quote, LinkedIn draft, AI influencer post plan, portfolio sample, or client proposal.",
                "done_when": "Asset is truthful, rights-safe, saved locally, and waits for user approval before posting/contact.",
            },
            {
                "track": "Evaluation",
                "action": "Run focused tests or a live smoke check for the feature touched today.",
                "done_when": "Pass/fail result is saved in continuous logs and failures become tomorrow's P0 task.",
            },
            {
                "track": "Safe self-improvement",
                "action": "Pick one small code or workflow improvement, use backup/copy/test/review, and never silently modify live code.",
                "done_when": "Diff, tests, and rollback path are visible before sync or GitHub push.",
            },
        ],
        "world_class_metrics": [
            "startup reliability",
            "truth with citations",
            "artifact quality",
            "legal earning usefulness",
            "media consent/provenance",
            "test coverage",
            "recovery readiness",
            "user approval boundaries",
        ],
        "today_priority": _today_priority(config, brain),
        "approval_required": [
            "public posts/messages",
            "money movement or purchases",
            "hardware orders",
            "client commitments",
            "code sync/push/deploy",
            "use of a person's likeness, voice, private data, or copyrighted assets",
        ],
    }


def write_daily_improvement_plan(config: Config, brain_status: dict[str, Any] | None = None) -> Path:
    plan = build_daily_improvement_plan(config, brain_status)
    output_dir = config.resolved_continuous_dir / "daily_plans"
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"gima_daily_improvement_plan_{plan['date']}.json"
    path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    md_path = path.with_suffix(".md")
    md_path.write_text(_daily_plan_markdown(plan), encoding="utf-8")
    return path


def run_daily_improvement_agent(config: Config, brain_status: dict[str, Any] | None = None) -> dict[str, Any]:
    plan_path = write_daily_improvement_plan(config, brain_status)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    output_dir = config.resolved_continuous_dir / "daily_agents"
    output_dir.mkdir(parents=True, exist_ok=True)
    run_path = output_dir / f"daily_agent_{stamp}.json"
    run = {
        "kind": "gima_daily_improvement_agent_run",
        "agent": "Daily Improvement Agent",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "planned",
        "plan_path": str(plan_path),
        "plan_markdown_path": str(plan_path.with_suffix(".md")),
        "today_priority": plan["today_priority"],
        "actions": plan["daily_actions"],
        "next_command": _next_daily_agent_command(plan),
        "approval_required": plan["approval_required"],
        "blocked_autonomy": [
            "No public posting, client contact, purchases, money movement, deployment, or code sync without explicit approval.",
            "No use of private data, copyrighted assets, likeness, or voice without rights or consent.",
        ],
        "run_path": str(run_path),
    }
    run_path.write_text(json.dumps(run, indent=2), encoding="utf-8")
    md_path = run_path.with_suffix(".md")
    md_path.write_text(_daily_agent_markdown(run), encoding="utf-8")
    return run


def latest_daily_improvement_agent(config: Config) -> dict[str, Any] | None:
    output_dir = config.resolved_continuous_dir / "daily_agents"
    runs = sorted(output_dir.glob("daily_agent_*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not runs:
        return None
    try:
        return json.loads(runs[0].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def build_ai_era_requirements(config: Config, brain_status: dict[str, Any] | None = None) -> dict[str, Any]:
    hardware = build_hardware_profile()
    brain = brain_status or {}
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    return {
        "kind": "gima_ai_era_requirements",
        "updated_at": now,
        "agent": "AI Era Requirements Agent",
        "cadence": "minute_local_check",
        "purpose": "Keep Gima aligned with modern AI-era requirements without unsafe autonomous actions.",
        "pc_mode": hardware.local_ai_tier,
        "requirements": [
            _requirement("reliability", "Startup, brain readiness, errors, recovery, and uptime must be visible.", "started" if brain.get("running") else "needs_attention"),
            _requirement("truth", "Current facts need sources, citations, uncertainty flags, and no placeholder tables.", "started"),
            _requirement("rag_validation", "Source-backed answers need contradiction notes, quote boundaries, and citation validation.", "started"),
            _requirement("memory", "Learning must be reviewable, deduplicated, source-backed, and searchable.", "started" if config.resolved_brain_csv_path.exists() else "needs_index"),
            _requirement("tools", "Files, spreadsheets, media, code, and web actions need structured inputs/outputs and logs.", "started"),
            _requirement("artifact_qa", "Generated files need open-file checks, visual QA, schema checks, and repair loops.", "started"),
            _requirement("multimodal", "Image, audio, video, OCR, captions, and manifests must respect rights and consent.", "started"),
            _requirement("benchmarks", "Architecture claims need benchmark prompts, metrics, samples, and failure cases.", "planned"),
            _requirement("local_security", "Local-first storage still needs encryption roadmap, permissions, secret scans, and backups.", "started"),
            _requirement("legal_growth", "Money-making workflows must be legal, truthful, rights-safe, and approval-gated.", "started"),
            _requirement("self_improvement", "Code improvements require backup, isolated work, tests, review, and explicit sync approval.", "started"),
            _requirement("hardware_fit", f"Use {hardware.recommended_model}; heavy generation should use tools or approved providers until hardware improves.", "started"),
        ],
        "minute_policy": [
            "Every minute: update local readiness, requirements, and next-action records.",
            "Hourly or daily: refresh public AI requirements and source-backed research.",
            "Never every minute: spend money, post publicly, contact clients, deploy code, or rewrite live source.",
        ],
        "next_update": _ai_era_next_update(config, brain),
    }


def run_ai_era_requirements_agent(config: Config, brain_status: dict[str, Any] | None = None) -> dict[str, Any]:
    report = build_ai_era_requirements(config, brain_status)
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    output_dir = config.resolved_continuous_dir / "ai_era_agent"
    output_dir.mkdir(parents=True, exist_ok=True)
    run_path = output_dir / f"ai_era_agent_{stamp}.json"
    md_path = run_path.with_suffix(".md")
    latest_path = output_dir / "latest.json"
    latest_md_path = output_dir / "latest.md"
    report["run_path"] = str(run_path)
    report["latest_path"] = str(latest_path)
    run_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    latest_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    markdown = _ai_era_markdown(report)
    md_path.write_text(markdown, encoding="utf-8")
    latest_md_path.write_text(markdown, encoding="utf-8")
    _update_world_brain_record(config, report, markdown)
    return report


def latest_ai_era_requirements_agent(config: Config) -> dict[str, Any] | None:
    latest_path = config.resolved_continuous_dir / "ai_era_agent" / "latest.json"
    if not latest_path.exists():
        return None
    try:
        return json.loads(latest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def run_area_agent_supervisor(config: Config, brain_status: dict[str, Any] | None = None) -> dict[str, Any]:
    report = build_area_agent_supervisor(config, brain_status)
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    output_dir = config.resolved_continuous_dir / "area_agents"
    output_dir.mkdir(parents=True, exist_ok=True)
    run_path = output_dir / f"area_agents_{stamp}.json"
    md_path = run_path.with_suffix(".md")
    latest_path = output_dir / "latest.json"
    latest_md_path = output_dir / "latest.md"
    report["run_path"] = str(run_path)
    report["latest_path"] = str(latest_path)
    run_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    latest_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    markdown = _area_agent_markdown(report)
    md_path.write_text(markdown, encoding="utf-8")
    latest_md_path.write_text(markdown, encoding="utf-8")
    _update_area_agent_brain_record(config, report, markdown)
    return report


def latest_area_agent_supervisor(config: Config) -> dict[str, Any] | None:
    latest_path = config.resolved_continuous_dir / "area_agents" / "latest.json"
    if not latest_path.exists():
        return None
    try:
        return json.loads(latest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def build_area_agent_supervisor(config: Config, brain_status: dict[str, Any] | None = None) -> dict[str, Any]:
    deps = dependency_report()
    brain = brain_status or {}
    hands_out = config.resolved_hands_out_dir
    continuous = config.resolved_continuous_dir
    areas = [
        _area("Reliability", "ok" if brain.get("running") and brain.get("ready", True) else "needs_attention", "Brain server, web UI, logs, restart state.", "Start Gima brain/web and keep doctor checks green."),
        _area("Memory and learning", "ok" if config.resolved_brain_csv_path.exists() else "needs_attention", "CSV memory, SQLite search index, source-backed review records.", "Rebuild brain.csv and keep source review records searchable."),
        _area("Model and routing", "started" if getattr(config.model, "model", "") else "needs_attention", f"Active model: {getattr(config.model, 'model', '')}", "Benchmark fast/strong local model and teacher routing."),
        _area("Artifacts and tables", "started" if hands_out.exists() else "needs_attention", "Reports, CSV/Excel/PDF/JPG-style output folders and manifests.", "Create one verified downloadable artifact and add a regression test."),
        _area("Video and media", "started" if deps.get("ffmpeg") and deps.get("ffprobe") else "needs_attention", "Image+audio MP4, advanced video-song renderer, lip-sync planning, director storyboard.", "Run a consented sample render and evaluate output metadata."),
        _area(
            "Image editing",
            "started" if os.environ.get("OPENAI_API_KEY") else "needs_attention",
            "ChatGPT/OpenAI image generation adapter writes PNG files and manifests to hands/out when an OpenAI key is linked.",
            "Save ChatGPT / OpenAI API key, generate one consented sample image, then add image-edit input support.",
        ),
        _area("Voice and audio", "started" if deps.get("ffmpeg") and deps.get("whisper-cli") else "needs_attention", "Speech-to-text, macOS TTS, audio capture/transcription hooks.", "Add voice latency and multilingual evals."),
        _area("Research and truth", "started", "Web import, research profiles, citations, self-checks, current-source caution.", "Add claim-to-source scoring and trusted-source refresh cadence."),
        _area("Safety and permissions", "started", "Consent gates, private-network block, parent approval, audit CSV, legal boundaries.", "Add per-tool risk tiers and incident review tests."),
        _area("Coding and self-update", "started", "Copied workspace self-update plans, tests, backup/sync path.", "Run changes in copied workspaces with focused tests before sync."),
        _area("GitHub and deployment", "started" if (config.resolved_workspace / ".git").exists() else "planned", "Git working tree, PR docs, Cloud Run deployment docs.", "Add status check for gh/GitHub auth and deploy readiness."),
        _area("Legal earning and AI influencer", "started", "Offer playbook, sample artifact plan, disclosure-first influencer workflows.", "Prepare one portfolio demo with clear rights and no income guarantees."),
        _area("Hardware and scaling", "started", "Hardware-aware 7B/4B strategy, model plan, upgrade fund logic.", "Use larger hardware only when evals prove paid-work improvement."),
    ]
    needs_attention = [area for area in areas if area["status"] == "needs_attention"]
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    return {
        "kind": "gima_area_agent_supervisor",
        "agent": "24/7 Area Agent Supervisor",
        "cadence": "continuous_background_loop",
        "updated_at": now,
        "areas": areas,
        "area_count": len(areas),
        "needs_attention_count": len(needs_attention),
        "next_action": needs_attention[0]["next_action"] if needs_attention else "Keep one measured improvement per area and avoid unsafe autonomous actions.",
        "rules": [
            "Agents may inspect, log, plan, and test.",
            "Agents must not spend money, post publicly, contact clients, deploy, or rewrite live code without approval.",
            "Media agents must require rights/consent and label AI-assisted output.",
            "Claims of 100% reliability require repeatable tests, not slogans.",
        ],
    }


def _area(name: str, status: str, detail: str, next_action: str) -> dict[str, str]:
    return {"name": name, "status": status, "detail": detail, "next_action": next_action}


def _update_area_agent_brain_record(config: Config, report: dict[str, Any], markdown: str) -> None:
    memory = MemoryStore(config.resolved_data_dir)
    memory.initialize()
    source = "gima://area-agent-supervisor/latest"
    record = Record(
        category="system",
        subcategory="area_agents",
        kind="continuous_supervisor_snapshot",
        title="24/7 area agent supervisor snapshot",
        content=markdown,
        keywords="24/7 area agents reliability memory video media artifacts safety github earning hardware self improvement",
        source=source,
        confidence="0.80",
        status="active",
    )
    memory.replace_source(source, [record])
    memory.audit(
        "area_agent_supervisor_update",
        source,
        f"updated_at={report.get('updated_at', '')} areas={len(report.get('areas', []))}",
        "ok",
    )
    rebuild_brain_csv(
        config.resolved_data_dir,
        [config.resolved_data_dir / "brain", config.resolved_hands_dir, config.resolved_downloads_dir],
    )


def _update_world_brain_record(config: Config, report: dict[str, Any], markdown: str) -> None:
    memory = MemoryStore(config.resolved_data_dir)
    memory.initialize()
    source = "gima://minute-world-ai-requirements/latest"
    record = Record(
        category="world_update",
        subcategory="ai_era_requirements",
        kind="minute_agent_snapshot",
        title="Minute AI-era world requirements snapshot",
        content=(
            markdown
            + "\nCoverage note: this is a local minute snapshot of priority AI-era requirements. "
            "It does not guarantee all world events are captured. Public web/current-source refreshes must remain rate-limited and source-backed.\n"
        ),
        keywords="ai era requirements world update current AI legal growth safety model hardware",
        source=source,
        confidence="0.70",
        status="active",
    )
    memory.replace_source(source, [record])
    memory.audit(
        "minute_world_brain_update",
        source,
        f"updated_at={report.get('updated_at', '')} requirements={len(report.get('requirements', []))}",
        "ok",
    )
    rebuild_brain_csv(
        config.resolved_data_dir,
        [config.resolved_data_dir / "brain", config.resolved_hands_dir, config.resolved_downloads_dir],
    )


def build_own_model_plan(config: Config, brain_status: dict[str, Any] | None = None) -> dict[str, Any]:
    brain = brain_status or {}
    active_level = getattr(config.model, "active_level", "")
    model_name = getattr(config.model, "model", "")
    return {
        "kind": "gima_own_model_plan",
        "status": "started",
        "active_model": model_name,
        "active_level": active_level,
        "realistic_strategy": "Use a stronger open GGUF model now; build Gima's own intelligence through memory, datasets, evals, routing, and later adapters/fine-tuning.",
        "why_not_from_scratch": "Training a frontier model from scratch needs huge datasets, GPUs, money, safety work, and evaluation. This PC should build a Gima-specific layer first.",
        "stages": [
            {
                "stage": "1. Strong base model",
                "status": "done" if active_level == "strong" or "7b" in model_name.casefold() else "started",
                "action": "Run the downloaded 7B quantized model for stronger local reasoning when latency is acceptable.",
            },
            {
                "stage": "2. Gima memory model",
                "status": "started" if config.resolved_brain_csv_path.exists() else "needs_index",
                "action": "Keep brain.csv, source reviews, conversations, outputs, and continuous logs as the local knowledge layer.",
            },
            {
                "stage": "3. Instruction dataset",
                "status": "planned",
                "action": "Export approved conversations, tool traces, artifact requests, and corrected answers into JSONL training/eval examples.",
            },
            {
                "stage": "4. Evals before tuning",
                "status": "planned",
                "action": "Create tests for Gima identity, truthful tables, legal earning boundaries, media consent, code safety, and local hardware routing.",
            },
            {
                "stage": "5. Adapter/fine-tune experiment",
                "status": "future",
                "action": "Use LoRA/QLoRA or another small adapter on suitable hardware or a rented GPU; merge/quantize only after evals improve.",
            },
            {
                "stage": "6. Model registry",
                "status": "planned",
                "action": "Track every model/adaptor with source, license, data used, eval score, safety notes, and rollback path.",
            },
        ],
        "blocked": [
            "Do not train on private/client/copyrighted data without permission.",
            "Do not claim Gima is a newly trained frontier model when it is using an open base model plus memory.",
            "Do not replace a working model until evals prove the new one is better.",
        ],
        "brain_running": bool(brain.get("running")),
    }


def write_own_model_plan(config: Config, brain_status: dict[str, Any] | None = None) -> Path:
    plan = build_own_model_plan(config, brain_status)
    output_dir = config.resolved_continuous_dir / "model_plans"
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "gima_own_model_plan.json"
    path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    path.with_suffix(".md").write_text(_own_model_markdown(plan), encoding="utf-8")
    return path


def _doctor_checks(
    config: Config,
    deps: dict[str, bool],
    brain: dict[str, Any],
    hardware: HardwareProfile,
) -> list[dict[str, str]]:
    brain_running = bool(brain.get("running"))
    brain_ready = bool(brain.get("ready")) if "ready" in brain else brain_running
    checks = [
        _check("Hardware fit", "ok", f"{hardware.local_ai_tier}: {hardware.strategy}", "Use the recommended model strategy."),
        _check(
            "Brain server",
            "ok" if brain_ready else ("warn" if brain_running else "missing"),
            "ready" if brain_ready else ("starting" if brain_running else "not running"),
            "Start Gima or wait for the local model to finish loading.",
        ),
        _check(
            "Local model binary",
            "ok" if deps.get("llama-server") else "missing",
            "llama-server found" if deps.get("llama-server") else "llama-server missing",
            "Install llama.cpp or keep using teacher APIs plus deterministic tools.",
        ),
        _check(
            "Media rendering",
            "ok" if deps.get("ffmpeg") and deps.get("ffprobe") else "missing",
            "ffmpeg/ffprobe ready" if deps.get("ffmpeg") and deps.get("ffprobe") else "ffmpeg or ffprobe missing",
            "Install ffmpeg for songs, video drafts, and media evaluation.",
        ),
        _check(
            "Document OCR",
            "ok" if deps.get("tesseract") and deps.get("pdftotext") else "warn",
            "OCR tools ready" if deps.get("tesseract") and deps.get("pdftotext") else "some OCR tools missing",
            "Install tesseract and poppler for stronger document/image reading.",
        ),
        _check(
            "Voice tools",
            "ok" if deps.get("whisper-cli") and deps.get("say") else "warn",
            "voice ready" if deps.get("whisper-cli") and deps.get("say") else "speech input/output partial",
            "Install whisper.cpp model/CLI for better local voice conversation.",
        ),
        _check(
            "Memory folders",
            "ok" if config.resolved_data_dir.exists() and config.resolved_hands_out_dir.exists() else "missing",
            f"{config.resolved_data_dir}",
            "Run `python3 -m human_ai.cli init` from the Gima workspace.",
        ),
        _check(
            "Brain index",
            "ok" if config.resolved_brain_csv_path.exists() else "warn",
            str(config.resolved_brain_csv_path),
            "Rebuild memory with `python3 -m human_ai.cli rebuild` or use Gima search once.",
        ),
    ]
    return checks


def _today_priority(config: Config, brain: dict[str, Any]) -> str:
    if not brain.get("running"):
        return "P0 Reliability: start and verify the local brain before feature work."
    if not config.resolved_brain_csv_path.exists():
        return "P0 Memory: rebuild brain.csv so answers can use local knowledge."
    return "P1 Output: create one useful legal earning or artifact demo and test it."


def _requirement(name: str, requirement: str, status: str) -> dict[str, str]:
    return {"name": name, "requirement": requirement, "status": status}


def _ai_era_next_update(config: Config, brain: dict[str, Any]) -> str:
    if not brain.get("running"):
        return "Start/verify brain server and record health before higher-level updates."
    if not config.resolved_brain_csv_path.exists():
        return "Rebuild brain.csv so requirements and answers can use local memory."
    return "Create or test one output that improves truth, artifact quality, legal growth, or self-improvement safety."


def _next_daily_agent_command(plan: dict[str, Any]) -> str:
    priority = plan.get("today_priority", "")
    if priority.startswith("P0 Reliability"):
        return "python3 -m human_ai.gima --config config.local.json status"
    if priority.startswith("P0 Memory"):
        return "python3 -m human_ai.cli --config config.local.json rebuild"
    return "python3 -m human_ai.gima --config config.local.json doctor"


def _improvement_plan(
    config: Config,
    hardware: HardwareProfile,
    deps: dict[str, bool],
    brain: dict[str, Any],
) -> list[dict[str, str]]:
    return [
        {
            "phase": "P0 Reliability Core",
            "status": "started" if brain.get("running") else "needs_start",
            "action": "Keep brain-first retrieval, clear readiness states, and short local-model responses for this PC.",
            "why": hardware.strategy,
        },
        {
            "phase": "P0 Real Artifact Engine",
            "status": "started",
            "action": "Use deterministic builders for costing, tables, source registers, Excel, JPG, and PDF.",
            "why": "Structured files are more reliable than asking a small model to invent them.",
        },
        {
            "phase": "P0 Memory and Learning",
            "status": "started" if config.resolved_brain_csv_path.exists() else "needs_index",
            "action": "Store source-backed lessons in review memory and rebuild brain.csv after learning.",
            "why": "Current knowledge should live in inspectable local files, not only in model weights.",
        },
        {
            "phase": "P1 Media Director",
            "status": "started" if deps.get("ffmpeg") else "missing_dependency",
            "action": "Render local video/song drafts with ffmpeg, then connect neural image/lip-sync backends only when installed and consented.",
            "why": "This hardware can render and plan; heavy generation should be optional/provider-backed.",
        },
        {
            "phase": "P2 Agent Workbench",
            "status": "planned",
            "action": "Use copied workspaces, tests, and approval gates for self-code instead of silent live edits.",
            "why": "Self-improvement must be recoverable and reviewable.",
        },
    ]


def _growth_plan(hardware: HardwareProfile) -> list[dict[str, str]]:
    return [
        {
            "phase": "Find useful paid work",
            "status": "allowed_with_review",
            "action": "Research local and online demand for costing sheets, menus, small-business reports, websites, automation scripts, image/video drafts, and AI setup support.",
            "approval_required": "Gima can prepare opportunities and messages, but you approve before contacting anyone or posting publicly.",
        },
        {
            "phase": "Create sellable proof",
            "status": "started",
            "action": "Use Gima to create sample Excel/PDF/JPG costing packs, LinkedIn posts, GitHub demos, short videos, and before/after reports.",
            "approval_required": "You approve final public files, prices, and claims before sharing.",
        },
        {
            "phase": "Track income and savings",
            "status": "planned",
            "action": "Maintain a local upgrade fund ledger with quotes, income ideas, expected margin, saved amount, and next purchase target.",
            "approval_required": "Gima records plans only; it does not move money, enter card details, or buy equipment.",
        },
        {
            "phase": "Choose hardware upgrade",
            "status": "planned",
            "action": f"Prioritize upgrades that improve {hardware.local_ai_tier}: RAM/Apple Silicon/NVIDIA GPU depending on budget and local availability.",
            "approval_required": "Gima can compare specs and prices; you approve vendor, payment, shipping, and installation.",
        },
    ]


def _hardware_upgrade_plan(hardware: HardwareProfile) -> list[dict[str, str]]:
    if hardware.local_ai_tier == "local_small":
        return [
            {
                "target": "Best low-risk path",
                "upgrade": "Keep this Mac for Gima tools; add cloud/teacher APIs for heavy generation until revenue is steady.",
                "benefit": "Lowest cost, works now, avoids buying hardware before Gima earns from useful outputs.",
            },
            {
                "target": "Next local AI jump",
                "upgrade": "Move to 32 GB+ unified memory Apple Silicon or a desktop with 12 GB+ NVIDIA VRAM.",
                "benefit": "Better 7B/14B local models, faster image/video experiments, larger context, smoother multitasking.",
            },
            {
                "target": "Production media",
                "upgrade": "Dedicated GPU workstation only after Gima has repeatable paid media/report workflows.",
                "benefit": "Useful for local image generation, lip-sync, video generation, and batch rendering.",
            },
        ]
    return [
        {
            "target": "Strengthen current setup",
            "upgrade": "Benchmark current model levels before buying hardware.",
            "benefit": "Prevents waste and shows which bottleneck actually matters.",
        },
        {
            "target": "Larger local models",
            "upgrade": "Add memory/VRAM only when evals prove the larger model improves paid workflows.",
            "benefit": "Hardware spend follows evidence, not hype.",
        },
    ]


def _master_ai_director_plan(hardware: HardwareProfile, effective_strategy: str) -> dict[str, Any]:
    return {
        "kind": "gima_master_ai_director_plan",
        "hardware_reality": (
            f"{hardware.cpu} with {hardware.memory_gb} GB RAM is a controller-class machine, not a frontier-model training box. "
            "Do not attempt to run or train GPT-4o/Sora/Midjourney-class models locally."
        ),
        "north_star": "Use the Mac as a lightweight director: index, plan, route, verify, store memory, and orchestrate approved tools.",
        "strategy": effective_strategy,
        "local_budget": {
            "cpu_role": "Run the web UI, file watchers, BM25/inverted-index search, small local chat, scripts, and QA tools.",
            "ram_rule": "Keep heavy model loading optional; preserve RAM for browser, file parsing, indexes, and artifact generation.",
            "best_local_models": "1B-4B quantized models for fast private responses; 7B only when latency is acceptable.",
        },
        "routing_rules": [
            {
                "task": "Any-file learning",
                "local_first": "Extract text/metadata with Python libraries, OCR/ffmpeg when installed, and BM25 search.",
                "cloud_when": "Only send snippets to teacher APIs when CLOUD_ALLOWED=true and the content is approved for cloud processing.",
                "output": "Source-backed summary, searchable brain row, and review status.",
            },
            {
                "task": "Deep reasoning and current research",
                "local_first": "Retrieve relevant memory, outline assumptions, and prepare a precise prompt.",
                "cloud_when": "Use OpenRouter/OpenAI/Gemini/Anthropic for high-value reasoning, web/current facts, or long context.",
                "output": "Teacher answer stored as review memory with provider and provenance.",
            },
            {
                "task": "Image/video/song generation",
                "local_first": "Create storyboards, prompts, scripts, subtitles, QA manifests, and lightweight FFmpeg drafts.",
                "cloud_when": "Use approved image/video/music APIs for actual frontier generation.",
                "output": "Director pack plus generated files and rights/safety notes.",
            },
            {
                "task": "Coding and self-improvement",
                "local_first": "Inspect repo, plan patches, run tests, and write upgrade reports.",
                "cloud_when": "Ask teacher models for architecture critique only after approval.",
                "output": "Small, tested, reviewable improvements with rollback notes.",
            },
        ],
        "agent_roles": [
            {
                "agent": "Thinker",
                "job": "Create the strategy, task decomposition, assumptions, and success criteria.",
            },
            {
                "agent": "Communicator",
                "job": "Challenge the plan, identify missing evidence, privacy risk, cost risk, and user-facing clarity gaps.",
            },
            {
                "agent": "Local Executive Controller",
                "job": "Run local tools, file indexing, tests, artifact generation, and final response assembly.",
            },
        ],
        "resource_policy": [
            "Do not load heavy local models by default on 16 GB RAM.",
            "Do not train frontier-scale models locally.",
            "Use BM25/inverted indexes and deterministic tools before embeddings or large models.",
            "Use cloud APIs only with explicit configuration, consent, and CLOUD_ALLOWED=true.",
            "Keep every learning/update as reviewable memory until verified.",
        ],
    }


def _legal_earning_plan() -> list[dict[str, str]]:
    return [
        {
            "offer": "Catering costing and quotation packs",
            "output": "Excel, PDF, JPG preview, source register, assumptions, and margin scenarios.",
            "legal_check": "Use truthful prices, clear assumptions, no fake supplier quotes, and user-approved final numbers.",
        },
        {
            "offer": "Small-business research reports",
            "output": "Cited table, PDF summary, charts, and LinkedIn-ready explanation.",
            "legal_check": "Use public/allowed sources, cite them, avoid professional legal/medical/financial advice claims.",
        },
        {
            "offer": "Spreadsheet/data cleanup service",
            "output": "Clean CSV/XLSX, formulas, dashboard, and change log.",
            "legal_check": "Protect client data, keep local copies private, and avoid using confidential files in public demos.",
        },
        {
            "offer": "AI workflow setup help",
            "output": "Local AI checklist, API setup notes, safe automation plan, and training handout.",
            "legal_check": "Do not promise guaranteed income, model consciousness, or impossible capabilities.",
        },
        {
            "offer": "Consented media drafts",
            "output": "Audio visualizer, storyboard, captioned draft, and manifest.",
            "legal_check": "Use only owned, licensed, public-domain, or consented images, music, voices, and likenesses.",
        },
        {
            "offer": "Transparent AI influencer studio",
            "output": "AI persona guide, content calendar, captions, scripts, short video drafts, disclosure text, media kit, and sponsor pitch.",
            "legal_check": "Disclose AI assistance where appropriate; no fake human identity, impersonation, fake engagement, hidden sponsorships, or unconsented likeness/voice.",
        },
    ]


def _autonomy_boundaries() -> list[dict[str, str]]:
    return [
        {
            "area": "Money",
            "allowed": "Research legal opportunities, build quotes, prepare budgets, compare prices, track income/expenses and upgrade fund.",
            "blocked_without_user": "No purchases, payments, credit applications, bank actions, crypto/trading, subscriptions, tax filings, or paid ads.",
        },
        {
            "area": "Public communication",
            "allowed": "Draft LinkedIn posts, emails, proposals, portfolio pages, and GitHub descriptions.",
            "blocked_without_user": "No posting, messaging, commenting, applying for jobs, contacting customers, fake reviews, misleading claims, fake followers, or hidden sponsorships.",
        },
        {
            "area": "Hardware",
            "allowed": "Recommend specs, compare stores, produce install checklist, and estimate performance gains.",
            "blocked_without_user": "No ordering parts, changing system settings, deleting files, or installing risky drivers without approval.",
        },
        {
            "area": "Rights and client data",
            "allowed": "Prepare work from owned, licensed, public, or consented materials and local/private client files.",
            "blocked_without_user": "No selling stolen media, unlicensed music, copied logos, private data, impersonation, or unclear-rights assets.",
        },
        {
            "area": "AI influencer identity",
            "allowed": "Create a transparent AI persona, style guide, content drafts, disclosure text, and analytics plan.",
            "blocked_without_user": "No pretending to be a real human, impersonating real people, faking lived experiences, or using unconsented face/voice/identity.",
        },
    ]


def _criticism_defense_matrix() -> list[dict[str, str]]:
    return [
        {
            "criticism": "Not fully autonomous",
            "why_it_matters": "Gima should not claim complete unsupervised autonomy.",
            "defense": "Frame autonomy as review-gated, scoped, logged, reversible, and blocked for spending/posting/deploying without approval.",
            "implementation": "Doctor autonomy boundaries, permission gates, approval prompts, continuous logs.",
        },
        {
            "criticism": "Evaluation still needed",
            "why_it_matters": "Architecture claims require benchmark evidence.",
            "defense": "Publish benchmark prompts, metrics, output samples, failure cases, and regression history.",
            "implementation": "AI task map evaluation methods, focused unit tests, doctor next actions.",
        },
        {
            "criticism": "Local storage can still leak",
            "why_it_matters": "Local-first does not automatically mean secure.",
            "defense": "Use encryption roadmap, permissioning, secret scanning, masked keys, backups, and Git hygiene.",
            "implementation": "Local secrets file, masked UI, scoped tool runner, Git sync secret checks.",
        },
        {
            "criticism": "RAG can still be wrong",
            "why_it_matters": "Source-backed answers can misread sources.",
            "defense": "Add contradiction notes, quote boundaries, citation validation, uncertainty flags, and source freshness checks.",
            "implementation": "Research artifact route, memory source rows, web-import limits, planned claim-to-source scoring.",
        },
        {
            "criticism": "Artifact tools can fail",
            "why_it_matters": "Files may generate with formatting, schema, formula, or rendering errors.",
            "defense": "Use open-file tests, visual QA, schema checks, file manifests, and repair loops.",
            "implementation": "Artifact tests, generated manifests, download/open-location links, render-and-verify roadmap.",
        },
        {
            "criticism": "Self-improvement can regress",
            "why_it_matters": "Code changes may break the system.",
            "defense": "Require backup, isolated copy, tests, diff review, rollback path, and release notes before sync.",
            "implementation": "Self-update manager, backup tarballs, patch previews, test outputs, GitHub PR workflow.",
        },
    ]


def _check(name: str, status: str, detail: str, fix: str) -> dict[str, str]:
    return {"name": name, "status": status, "detail": detail, "fix": fix}


def _daily_plan_markdown(plan: dict[str, Any]) -> str:
    lines = [
        "# Gima Daily Improvement Plan",
        "",
        f"Date: {plan['date']}",
        "",
        f"North star: {plan['north_star']}",
        "",
        f"PC strategy: {plan['pc_strategy']}",
        "",
        f"Today priority: {plan['today_priority']}",
        "",
        "## Actions",
        "",
    ]
    for item in plan["daily_actions"]:
        lines.append(f"- **{item['track']}**: {item['action']}")
        lines.append(f"  Done when: {item['done_when']}")
    lines.extend(["", "## World-Class Metrics", ""])
    lines.extend(f"- {metric}" for metric in plan["world_class_metrics"])
    lines.extend(["", "## Approval Required", ""])
    lines.extend(f"- {item}" for item in plan["approval_required"])
    lines.append("")
    return "\n".join(lines)


def _daily_agent_markdown(run: dict[str, Any]) -> str:
    lines = [
        "# Gima Daily Improvement Agent Run",
        "",
        f"Created: {run['created_at']}",
        f"Status: {run['status']}",
        f"Today priority: {run['today_priority']}",
        "",
        f"Plan: {run['plan_markdown_path']}",
        "",
        "## Actions",
        "",
    ]
    for action in run["actions"]:
        lines.append(f"- **{action['track']}**: {action['action']}")
        lines.append(f"  Done when: {action['done_when']}")
    lines.extend(["", "## Next Command", "", f"`{run['next_command']}`", "", "## Blocked Autonomy", ""])
    lines.extend(f"- {item}" for item in run["blocked_autonomy"])
    lines.append("")
    return "\n".join(lines)


def _ai_era_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Gima AI Era Requirements Agent",
        "",
        f"Updated: {report['updated_at']}",
        f"Cadence: {report['cadence']}",
        f"PC mode: {report['pc_mode']}",
        "",
        f"Purpose: {report['purpose']}",
        "",
        f"Next update: {report['next_update']}",
        "",
        "## Requirements",
        "",
    ]
    for row in report["requirements"]:
        lines.append(f"- **{row['name']}** [{row['status']}]: {row['requirement']}")
    lines.extend(["", "## Minute Policy", ""])
    lines.extend(f"- {item}" for item in report["minute_policy"])
    lines.append("")
    return "\n".join(lines)


def _area_agent_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Gima 24/7 Area Agent Supervisor",
        "",
        f"Updated: {report['updated_at']}",
        f"Cadence: {report['cadence']}",
        f"Areas: {report['area_count']}",
        f"Needs attention: {report['needs_attention_count']}",
        "",
        f"Next action: {report['next_action']}",
        "",
        "## Area Agents",
        "",
    ]
    for area in report["areas"]:
        lines.extend(
            [
                f"### {area['name']} [{area['status']}]",
                "",
                area["detail"],
                "",
                f"Next: {area['next_action']}",
                "",
            ]
        )
    lines.extend(["## Rules", ""])
    lines.extend(f"- {rule}" for rule in report["rules"])
    lines.append("")
    return "\n".join(lines)


def _own_model_markdown(plan: dict[str, Any]) -> str:
    lines = [
        "# Gima Own Model Plan",
        "",
        f"Status: {plan['status']}",
        f"Active model: {plan['active_model']}",
        f"Active level: {plan['active_level']}",
        "",
        f"Strategy: {plan['realistic_strategy']}",
        "",
        f"Why not from scratch: {plan['why_not_from_scratch']}",
        "",
        "## Stages",
        "",
    ]
    for stage in plan["stages"]:
        lines.append(f"- **{stage['stage']}** [{stage['status']}]: {stage['action']}")
    lines.extend(["", "## Blocked", ""])
    lines.extend(f"- {item}" for item in plan["blocked"])
    lines.append("")
    return "\n".join(lines)


def _local_ai_tier(memory_gb: float, cpu_cores: int, machine: str) -> str:
    machine_lower = machine.casefold()
    if "arm" in machine_lower or "aarch" in machine_lower:
        if memory_gb >= 32:
            return "local_strong"
        if memory_gb >= 16:
            return "local_balanced"
    if memory_gb >= 24 and cpu_cores >= 8:
        return "local_balanced"
    if memory_gb >= 12:
        return "local_small"
    return "tool_first"


def _recommended_model(tier: str) -> str:
    return {
        "local_strong": "7B to 14B quantized model for deeper local reasoning",
        "local_balanced": "7B quantized model for stronger local answers",
        "local_small": "3B to 4B quantized model, brain-first retrieval, short context",
        "tool_first": "2B to 3B local model plus deterministic tools and teacher APIs",
    }.get(tier, "3B to 4B quantized local model")


def _recommended_strategy(tier: str) -> str:
    return {
        "local_strong": "Run stronger local reasoning, still keep tools and citations for file work.",
        "local_balanced": "Use a 7B model when memory allows, otherwise route structured work to tools.",
        "local_small": "Use the 4B model as a private chat brain; let tools, memory, and teacher APIs do heavy lifting.",
        "tool_first": "Prefer deterministic tools, retrieval, and cloud teachers; keep local model responses short.",
    }.get(tier, "Use retrieval and deterministic tools before asking the local model.")


def _effective_model_strategy(active_level: str, active_model: str, hardware_strategy: str) -> str:
    active = f"{active_level} {active_model}".casefold()
    if "strong" in active or "7b" in active:
        return "Strong 7B local model is active. Use it for deeper local reasoning, but keep tools, citations, memory, and teacher APIs for heavy/current/multimodal work."
    return hardware_strategy


def _sysctl_text(name: str) -> str:
    if not shutil.which("sysctl"):
        return ""
    try:
        return subprocess.check_output(["sysctl", "-n", name], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


def _sysctl_int(name: str) -> int:
    text = _sysctl_text(name)
    try:
        return int(text)
    except ValueError:
        return 0


def _safe_int(value: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
