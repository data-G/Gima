from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .brain_index import rebuild_brain_csv
from .memory import Record, now_iso


FRONTIER_FEATURE_FIELDS = [
    "provider",
    "system",
    "feature_family",
    "feature",
    "public_technical_detail",
    "gima_local_status",
    "gima_implementation",
    "needed_components",
    "evaluation",
    "safety_review",
    "public_sources",
    "last_checked",
]


FRONTIER_FEATURE_ROWS: list[dict[str, str]] = [
    {
        "provider": "OpenAI",
        "system": "ChatGPT",
        "feature_family": "conversation_memory",
        "feature": "Editable memory, memory summary, temporary chats, personalized context",
        "public_technical_detail": "Maintain user-approved memory records; expose sources/summary; allow deletion, correction, disabling, and temporary sessions.",
        "gima_local_status": "started",
        "gima_implementation": "Use memory.py conversations, brain.csv, source review rows, and UI controls for memory search and deletion/correction roadmap.",
        "needed_components": "memory source viewer, delete/correct UI, temporary session flag, stale-memory detector",
        "evaluation": "Ask repeated preference/context questions, verify answers cite current memory row and ignore temporary chats.",
        "safety_review": "User control over personalization; no hidden memory; sensitive facts require review.",
        "public_sources": "https://help.openai.com/en/articles/6825453-chatgpt-release-notes",
    },
    {
        "provider": "OpenAI",
        "system": "ChatGPT",
        "feature_family": "files_artifacts",
        "feature": "File library, document work, spreadsheets, charts, generated downloads",
        "public_technical_detail": "Store uploaded and generated files; answer over prior files; create downloadable docs/tables/charts with clear loading states.",
        "gima_local_status": "started",
        "gima_implementation": "Use hands/in, hands/out, stomach inventory, artifact engine, file cards, and download endpoint.",
        "needed_components": "file previews, document/table renderers, chart generation, file search ranking",
        "evaluation": "Upload a file, ask for a table/PDF/chart, confirm artifact exists and download link works.",
        "safety_review": "Keep local-only by default; block unsafe path traversal; record provenance.",
        "public_sources": "https://help.openai.com/en/articles/6825453-chatgpt-release-notes | https://platform.openai.com/docs/guides/retrieval",
    },
    {
        "provider": "OpenAI",
        "system": "Codex",
        "feature_family": "coding_agent",
        "feature": "Repo-aware coding, AGENTS.md instructions, terminal/browser testing, diffs, pull requests",
        "public_technical_detail": "Inspect files, apply patches, run tests, use project instructions, control browser/devtools, summarize changes, and continue toward goal criteria.",
        "gima_local_status": "started",
        "gima_implementation": "Use VibeCodingAgent, self_update copies, continuous CSV logs, web UI coding split, and local test runners.",
        "needed_components": "diff viewer, task plan UI, safe command allowlist, AGENTS.md importer, browser/devtools bridge",
        "evaluation": "Give a bug/feature, verify candidate files, patch skeleton, tests run, and rollback path.",
        "safety_review": "Back up before edits; never overwrite user changes; require approval for destructive commands.",
        "public_sources": "https://help.openai.com/en/articles/6825453-chatgpt-release-notes | https://developers.openai.com/codex/",
    },
    {
        "provider": "OpenAI",
        "system": "OpenAI API / Agents",
        "feature_family": "tool_orchestration",
        "feature": "Responses/Agents patterns, web search, file search, code execution, computer use, structured outputs",
        "public_technical_detail": "Route model turns through typed tools, schemas, retrieval, web search, code execution, and computer-use loops with observable results.",
        "gima_local_status": "started",
        "gima_implementation": "Use tool-style web endpoints, brain search, artifact generator, media planners, and structured JSON outputs.",
        "needed_components": "formal tool registry, schemas, tool permission scopes, streaming event log",
        "evaluation": "Run tool-routing evals and verify each action has input, output, status, and source row.",
        "safety_review": "Permission-gated tools; network and file access must be visible and logged.",
        "public_sources": "https://platform.openai.com/docs/guides/agents | https://platform.openai.com/docs/guides/tools-web-search | https://platform.openai.com/docs/guides/retrieval",
    },
    {
        "provider": "Google",
        "system": "Gemini API",
        "feature_family": "multimodal_long_context",
        "feature": "Text, image, video, documents, audio, long context, structured outputs, function calling",
        "public_technical_detail": "Gemini docs list multimodal inputs, million-token long context, structured JSON, function calling, document understanding, and tool use.",
        "gima_local_status": "started",
        "gima_implementation": "Use file ingestion, brain.csv, media metadata extraction, local model fallback, and optional Gemini teacher adapter.",
        "needed_components": "local VLM, video frame captioner, PDF/page citations, JSON schema validation",
        "evaluation": "Run multimodal fixture set: image, PDF, audio, video, table, long document.",
        "safety_review": "Respect media rights and private document handling; mark online teacher claims as review.",
        "public_sources": "https://ai.google.dev/gemini-api/docs",
    },
    {
        "provider": "Google",
        "system": "Gemini / Veo / Imagen / Lyria",
        "feature_family": "creative_generation",
        "feature": "Image generation/editing, video generation, speech/music/live voice capabilities",
        "public_technical_detail": "Gemini developer docs expose image models, Veo video generation, Lyria audio models, TTS, Live API, and voice agents.",
        "gima_local_status": "planned",
        "gima_implementation": "Keep local visualizers and prompt plans now; bind approved free/local generators when available.",
        "needed_components": "renderer adapter interface, consent/provenance log, prompt ladder, media quality evals",
        "evaluation": "Prompt adherence, temporal consistency, audio/video sync, resolution, artifacts, user review.",
        "safety_review": "Require rights/consent for people, voices, music, and copyrighted media.",
        "public_sources": "https://ai.google.dev/gemini-api/docs | https://deepmind.google/technologies/veo/",
    },
    {
        "provider": "Google",
        "system": "Antigravity",
        "feature_family": "agentic_development_platform",
        "feature": "Agent-first software development workspace with coding agents and browser/app feedback",
        "public_technical_detail": "Public Google material describes Antigravity as an agentic development platform around Gemini models, coding agents, environments, and deep research agents.",
        "gima_local_status": "planned",
        "gima_implementation": "Represent as Gima coding workspace: task plan, file tree, terminal, browser preview, test results, deployment notes.",
        "needed_components": "workspace panel, agent run queue, environment manager, browser preview, deployment connector",
        "evaluation": "Build a small app from prompt, run tests, preview UI, report deploy readiness.",
        "safety_review": "Human approval before sync/deploy; secrets never shown in browser.",
        "public_sources": "https://ai.google.dev/gemini-api/docs | https://developers.googleblog.com/en/introducing-google-antigravity-a-new-agentic-development-platform/",
    },
    {
        "provider": "Anthropic",
        "system": "Claude",
        "feature_family": "reasoning_context_tools",
        "feature": "Extended/adaptive thinking, citations, streaming, prompt caching, context editing, structured outputs",
        "public_technical_detail": "Claude docs list thinking controls, citations, streaming, tool use, prompt caching, context management, and structured outputs.",
        "gima_local_status": "started",
        "gima_implementation": "Use reasoning quality modes, source citations in brain answers, continuous logs, and CSV/JSON schemas.",
        "needed_components": "context compaction, citation renderer, cache diagnostics, reasoning-mode selector",
        "evaluation": "Long task benchmark with compaction, citations, tool calls, and answer consistency checks.",
        "safety_review": "Show assumptions; avoid unverifiable claims; keep tool traces reviewable.",
        "public_sources": "https://platform.claude.com/docs/en/build-with-claude/overview",
    },
    {
        "provider": "Anthropic",
        "system": "Claude Code",
        "feature_family": "coding_agent",
        "feature": "Terminal coding assistant, bash/text-editor/computer tools, MCP, skills, repo workflows",
        "public_technical_detail": "Claude Code docs describe agentic coding workflows with tools, MCP, files, terminal-like development, and enterprise controls.",
        "gima_local_status": "started",
        "gima_implementation": "Use VibeCodingAgent and self_update for local/offline code planning; add MCP-style tool registry.",
        "needed_components": "MCP server registry, editable file diff viewer, shell tool policies, coding eval suite",
        "evaluation": "SWE-style fixtures: locate bug, patch, test, summarize, no unrelated edits.",
        "safety_review": "Scoped file access, backups, and explicit sync approval.",
        "public_sources": "https://code.claude.com/docs/en/overview | https://platform.claude.com/docs/en/build-with-claude/overview",
    },
    {
        "provider": "Anthropic",
        "system": "Claude API",
        "feature_family": "computer_tool_use",
        "feature": "Computer use, web fetch/search, code execution, memory, bash/text-editor tools",
        "public_technical_detail": "Claude platform docs list server and client tools including web search/fetch, code execution, computer use, memory, bash, and text editor.",
        "gima_local_status": "planned",
        "gima_implementation": "Map to Gima tool registry with permission scopes and continuous logs.",
        "needed_components": "screen observe/click/type layer, web fetch importer, code sandbox, memory tool API",
        "evaluation": "GUI automation tasks with screenshots, successful action trace, and rollback.",
        "safety_review": "Never grant unrestricted machine control; require visible scoped approval.",
        "public_sources": "https://platform.claude.com/docs/en/build-with-claude/overview",
    },
    {
        "provider": "xAI",
        "system": "Grok / xAI API",
        "feature_family": "models_api",
        "feature": "Grok models with API access, tool/function style integration, image/text model endpoints",
        "public_technical_detail": "xAI docs publish model/API access, SDK/API reference, and developer endpoints for Grok-family models.",
        "gima_local_status": "planned",
        "gima_implementation": "Add xAI as optional teacher provider; cache answers in teacher_answer_cache.csv and brain review.",
        "needed_components": "xAI secret key field, client adapter, quota fallback, provider eval row",
        "evaluation": "Ask same prompt across providers; compare factuality, latency, cost, source quality.",
        "safety_review": "Store only human-language summaries; do not store private keys or hidden prompts.",
        "public_sources": "https://docs.x.ai/overview | https://docs.x.ai/developers/models",
    },
    {
        "provider": "All",
        "system": "Gima synthesis",
        "feature_family": "frontier_synthesis",
        "feature": "Unified local-first multi-provider brain",
        "public_technical_detail": "Common frontier pattern: multimodal model, retrieval memory, tool calling, coding agent, browser/computer use, artifacts, evals, source review, and user control.",
        "gima_local_status": "started",
        "gima_implementation": "Use brain.csv as local source of truth, hands folders for files/artifacts, teacher APIs as optional reviewers, and evals before claiming capability.",
        "needed_components": "provider router, capability eval dashboard, model benchmark table, daily public-source refresh",
        "evaluation": "Daily frontier checklist: chat, memory, files, web, code, audio, video, UI, safety, deploy.",
        "safety_review": "No private model theft; no hidden bypass; public sources and user-approved integrations only.",
        "public_sources": "https://help.openai.com/en/articles/6825453-chatgpt-release-notes | https://ai.google.dev/gemini-api/docs | https://platform.claude.com/docs/en/build-with-claude/overview | https://docs.x.ai/overview",
    },
]


FUTURE_HORIZON_ROWS: list[dict[str, str]] = [
    {
        "provider": "Research consensus",
        "system": "Deep research agents",
        "feature_family": "long_horizon_research",
        "feature": "Plan, browse, compare, cite, backtrack, pause, resume, and produce verifiable research artifacts",
        "public_technical_detail": "Modern research agents combine multi-step planning, browsers, code tools, files, citations, progress updates, and user interruption.",
        "gima_local_status": "started",
        "gima_implementation": "Extend WebImporter and ResearchReasoner with resumable plans, trusted-domain filters, claim-source mapping, and progress events.",
        "needed_components": "research job store, source-quality ranking, claim verifier, progress UI, interrupt/resume",
        "evaluation": "Research benchmark with source authority, citation coverage, contradiction detection, and reproducible artifacts.",
        "safety_review": "Never equate many sources with truth; flag uncertainty and high-stakes professional review.",
        "public_sources": "https://openai.com/index/introducing-deep-research/ | https://hai.stanford.edu/ai-index/2025-ai-index-report",
    },
    {
        "provider": "Research consensus",
        "system": "Long-horizon agents",
        "feature_family": "durable_agents",
        "feature": "Execute multi-hour or multi-day goals through checkpoints, retries, recovery, and completion tests",
        "public_technical_detail": "Agent evaluations increasingly measure tool use, long tasks, browser work, coding, and human intervention rather than one-turn answers.",
        "gima_local_status": "started",
        "gima_implementation": "Build on continuous CSVs, snapshots, quotas, copied workspaces, tests, and approval-gated synchronization.",
        "needed_components": "durable task state, milestone budgets, retry policy, completion oracle, notification controls",
        "evaluation": "Interrupt, reboot, resume, verify goal criteria, and confirm no duplicate or unauthorized actions.",
        "safety_review": "Use least privilege, bounded budgets, visible progress, cancellation, and rollback.",
        "public_sources": "https://hai.stanford.edu/assets/files/hai_ai_index_report_2025.pdf | https://www.nist.gov/itl/ai-risk-management-framework",
    },
    {
        "provider": "Research consensus",
        "system": "Collaborative specialist agents",
        "feature_family": "multi_agent_collaboration",
        "feature": "Planner, researcher, builder, critic, and verifier roles sharing evidence and challenging mistakes",
        "public_technical_detail": "Specialization can improve coverage, but coordination cost and correlated errors require explicit evaluation.",
        "gima_local_status": "planned",
        "gima_implementation": "Use typed roles over one shared task ledger; require a verifier to check artifacts and sources before completion.",
        "needed_components": "role registry, shared trace IDs, conflict resolution, token budgets, verifier protocol",
        "evaluation": "Compare single-agent and multi-agent quality, latency, cost, disagreement handling, and error correlation.",
        "safety_review": "Agents do not grant one another new permissions; user approval remains the authority boundary.",
        "public_sources": "https://hai.stanford.edu/assets/files/hai_ai_index_report_2025.pdf",
    },
    {
        "provider": "OpenAI",
        "system": "Computer-using agents",
        "feature_family": "computer_use",
        "feature": "Perceive interfaces, click, type, scroll, recover from UI changes, and hand control back",
        "public_technical_detail": "Computer-using agents combine screenshots, multimodal reasoning, and mouse/keyboard actions, but remain imperfect on full OS tasks.",
        "gima_local_status": "planned",
        "gima_implementation": "Start with browser-only observation and approved actions, screenshots, action traces, and explicit takeover points.",
        "needed_components": "browser controller, screenshot grounding, action confirmation, domain allowlist, replayable trace",
        "evaluation": "WebArena-style tasks, changed-layout recovery, sensitive-action confirmation, and deterministic stop tests.",
        "safety_review": "Block payments, credentials, deletion, publishing, and identity actions without fresh confirmation.",
        "public_sources": "https://openai.com/index/computer-using-agent/ | https://openai.com/index/introducing-operator/",
    },
    {
        "provider": "Research consensus",
        "system": "AI for scientific discovery",
        "feature_family": "scientific_discovery",
        "feature": "Literature synthesis, hypothesis generation, simulation, experiment planning, and reproducible analysis",
        "public_technical_detail": "AI is increasingly used in biology, materials, weather, mathematics, and scientific workflows, while validation remains domain dependent.",
        "gima_local_status": "planned",
        "gima_implementation": "Create cited research notebooks, data manifests, statistical checks, replication tasks, and expert-review states.",
        "needed_components": "dataset registry, notebook runner, statistics library, replication workflow, domain reviewer",
        "evaluation": "Reproduce known results before proposing novel ones; measure calibration, leakage, and experimental validity.",
        "safety_review": "No autonomous wet-lab, medical, chemical, or biological execution; apply domain risk review.",
        "public_sources": "https://hai.stanford.edu/ai-index/2025-ai-index-report",
    },
    {
        "provider": "Google DeepMind",
        "system": "Gemini Robotics",
        "feature_family": "embodied_robotics",
        "feature": "Multimodal embodied reasoning with physical actions as an output modality",
        "public_technical_detail": "Vision-language-action models connect perception and language reasoning to robot control in the physical world.",
        "gima_local_status": "planned",
        "gima_implementation": "Research and simulate only until a supervised robot adapter, action schema, workspace boundary, and emergency stop exist.",
        "needed_components": "robot simulator, typed actions, collision checks, emergency stop, human supervisor",
        "evaluation": "Simulation success, intervention rate, collision avoidance, out-of-distribution detection, and safe shutdown.",
        "safety_review": "No unsupervised physical control; hard limits must be outside the model.",
        "public_sources": "https://deepmind.google/discover/blog/gemini-robotics-brings-ai-into-the-physical-world",
    },
    {
        "provider": "Research consensus",
        "system": "Spatial and world models",
        "feature_family": "spatial_intelligence",
        "feature": "Persistent 3D scenes, temporal identity, simulation, camera reasoning, and editable environments",
        "public_technical_detail": "Future multimodal systems are expected to reason over spatial layouts and time rather than isolated frames.",
        "gima_local_status": "planned",
        "gima_implementation": "Extend video storyboards into scene graphs, camera geometry, object identity tracks, and consistency reports.",
        "needed_components": "depth/pose estimation, scene graph, temporal tracker, simulator, 3D viewer",
        "evaluation": "Object permanence, geometry, navigation, temporal consistency, and controllable scene editing.",
        "safety_review": "Protect location privacy, identities, and private environmental imagery.",
        "public_sources": "https://hai.stanford.edu/assets/files/hai_ai_index_report_2025.pdf",
    },
    {
        "provider": "NIST",
        "system": "Trustworthy autonomy",
        "feature_family": "governance_and_assurance",
        "feature": "Risk-tiered tools, evaluation, monitoring, incident response, provenance, and human control",
        "public_technical_detail": "Trustworthy AI requires lifecycle governance and measurement rather than relying on prompts or model intent.",
        "gima_local_status": "started",
        "gima_implementation": "Extend permission scopes, audit CSVs, review states, backups, evals, and approval gates into per-action risk budgets.",
        "needed_components": "risk classifier, signed audit chain, incident workflow, policy tests, independent red team",
        "evaluation": "Prompt injection, excessive agency, privacy, rollback, audit integrity, accessibility, and human override tests.",
        "safety_review": "Capabilities remain planned until their risks, permissions, tests, and rollback are implemented.",
        "public_sources": "https://www.nist.gov/itl/ai-risk-management-framework | https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf",
    },
]

FRONTIER_FEATURE_ROWS.extend(FUTURE_HORIZON_ROWS)


@dataclass(frozen=True)
class FrontierFeatureReport:
    csv_path: Path
    md_path: Path
    rows: int
    memory_record_id: str


class FrontierFeatureStore:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir.resolve()
        self.root = self.data_dir / "brain" / "frontier_features"
        self.csv_path = self.root / "frontier_ai_feature_map.csv"
        self.md_path = self.root / "frontier_ai_feature_map.md"

    def refresh(self, agent) -> FrontierFeatureReport:
        self.root.mkdir(parents=True, exist_ok=True)
        checked = now_iso()
        rows = [{**row, "last_checked": checked} for row in FRONTIER_FEATURE_ROWS]
        with self.csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FRONTIER_FEATURE_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        self.md_path.write_text(self._markdown(rows), encoding="utf-8")
        record_id = self._store_in_memory(agent, rows)
        rebuild_brain_csv(self.data_dir, extra_roots=[self.data_dir / "brain", self.data_dir / "hands"])
        agent.memory.audit(
            "frontier_features_refresh",
            str(self.csv_path),
            f"rows={len(rows)} md={self.md_path}",
            "ok",
        )
        return FrontierFeatureReport(self.csv_path, self.md_path, len(rows), record_id)

    def list_rows(self, *, provider: str | None = None, limit: int = 50) -> list[dict[str, str]]:
        if not self.csv_path.exists():
            return []
        with self.csv_path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        if provider:
            rows = [row for row in rows if provider.casefold() in row.get("provider", "").casefold()]
        return rows[:limit]

    def _store_in_memory(self, agent, rows: list[dict[str, str]]) -> str:
        content = self._markdown(rows)
        agent.memory.replace_source(
            str(self.csv_path),
            [
                Record(
                    category="research",
                    subcategory="frontier_features",
                    kind="provider_feature_map",
                    title="Frontier AI feature map for Gima",
                    content=content,
                    keywords="ChatGPT Gemini Claude Grok Codex Antigravity frontier AI features tools memory multimodal coding agents",
                    source=str(self.csv_path),
                    confidence="0.78",
                    status="active",
                )
            ],
        )
        matches = agent.memory.search("Frontier AI feature map for Gima", category="research", limit=1)
        return matches[0]["id"] if matches else ""

    @staticmethod
    def _markdown(rows: list[dict[str, str]]) -> str:
        lines = [
            "# Frontier AI Feature Map For Gima",
            "",
            "This file maps public, implementable ideas from ChatGPT, Gemini, Claude, Grok, Codex, and Antigravity-style systems into Gima.",
            "Boundary: use public documentation and papers only; do not copy private weights, hidden prompts, leaked credentials, or proprietary internals.",
            "",
            "| Provider | System | Feature | Gima status | Implementation |",
            "| --- | --- | --- | --- | --- |",
        ]
        for row in rows:
            lines.append(
                "| {provider} | {system} | {feature} | {gima_local_status} | {gima_implementation} |".format(
                    **{key: _md_cell(value) for key, value in row.items()}
                )
            )
        lines.extend(
            [
                "",
                "## Evaluation Rule",
                "",
                "A feature is not marked done until Gima has a local test, artifact path, source/provenance row, and user-review status.",
            ]
        )
        return "\n".join(lines)


def _md_cell(value: str) -> str:
    return str(value).replace("|", "/").replace("\n", " ").strip()
