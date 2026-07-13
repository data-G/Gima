from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import Config
from .memory import MemoryStore, Record
from .self_update import SelfUpdateManager


AGENT_TEMPLATES: dict[str, dict[str, Any]] = {
    "self_update": {
        "name": "Safe Self-Update Agent",
        "purpose": "Prepare review-gated Gima improvements in an isolated working copy.",
        "allowed_actions": [
            "create source backup",
            "create isolated working copy",
            "write implementation plan",
            "rank likely files",
            "run tests in copy when explicitly triggered",
            "mark ready for approval",
        ],
        "blocked_actions": [
            "edit live workspace directly",
            "sync without approval",
            "delete user data",
            "expose API keys",
            "send private data to cloud unless CLOUD_ALLOWED=true",
        ],
        "requires_approval": True,
        "route_mode": "LOCAL_ONLY",
    },
    "research": {
        "name": "Research Agent",
        "purpose": "Collect source-backed public research and save notes for review.",
        "allowed_actions": [
            "search allowed public sources",
            "summarize pages",
            "save citations",
            "write contradiction notes",
        ],
        "blocked_actions": [
            "scrape private/restricted content",
            "bypass login or rate limits",
            "publish without user approval",
        ],
        "requires_approval": False,
        "route_mode": "AUTO",
    },
    "artifact": {
        "name": "Artifact Agent",
        "purpose": "Create structured local outputs such as tables, reports, prompt packs, and manifests.",
        "allowed_actions": [
            "create files in hands/out",
            "validate generated artifacts",
            "write manifests",
            "suggest repair steps",
        ],
        "blocked_actions": [
            "overwrite unrelated user files",
            "claim fake generation quality",
            "use unlicensed media",
        ],
        "requires_approval": False,
        "route_mode": "AUTO",
    },
}


@dataclass(frozen=True)
class CreatedAgent:
    agent_id: str
    name: str
    template: str
    goal: str
    manifest_path: Path
    status: str
    self_update_id: str = ""
    working_copy: str = ""
    plan_path: str = ""


class AgentRegistry:
    def __init__(self, config: Config):
        self.config = config
        self.root = config.resolved_data_dir / "agents"
        self.registry_path = self.root / "registry.json"

    def templates(self) -> list[dict[str, Any]]:
        return [
            {
                "template": key,
                **value,
            }
            for key, value in AGENT_TEMPLATES.items()
        ]

    def list_agents(self) -> list[dict[str, Any]]:
        agents = self._read_registry()
        return sorted(agents, key=lambda row: row.get("created_at", ""), reverse=True)

    def create(self, *, name: str, template: str, goal: str, memory: MemoryStore | None = None) -> CreatedAgent:
        clean_name = _clean_text(name, limit=80) or AGENT_TEMPLATES.get(template, AGENT_TEMPLATES["artifact"])["name"]
        clean_goal = _clean_text(goal, limit=1000)
        if not clean_goal:
            raise ValueError("Agent goal is required")
        template_key = template.strip().casefold() or "artifact"
        if template_key not in AGENT_TEMPLATES:
            raise ValueError(f"Unknown agent template: {template}")
        spec = AGENT_TEMPLATES[template_key]
        self.root.mkdir(parents=True, exist_ok=True)
        agent_id = f"agent_{datetime.now(timezone.utc).astimezone().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        agent_dir = self.root / agent_id
        agent_dir.mkdir(parents=True, exist_ok=False)

        manifest: dict[str, Any] = {
            "id": agent_id,
            "name": clean_name,
            "template": template_key,
            "goal": clean_goal,
            "status": "created",
            "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "purpose": spec["purpose"],
            "allowed_actions": spec["allowed_actions"],
            "blocked_actions": spec["blocked_actions"],
            "requires_approval": spec["requires_approval"],
            "route_mode": spec["route_mode"],
            "manifest_path": str(agent_dir / "manifest.json"),
            "notes_path": str(agent_dir / "instructions.md"),
        }

        if template_key == "self_update":
            update = SelfUpdateManager(self.config.resolved_workspace, self.config.resolved_data_dir).prepare(clean_goal)
            manifest.update(
                {
                    "status": "self_update_prepared",
                    "self_update_id": update.update_id,
                    "working_copy": str(update.working_copy),
                    "self_update_plan_path": str(update.plan_path),
                    "backup_path": str(update.backup_path),
                }
            )

        manifest_path = agent_dir / "manifest.json"
        manifest["manifest_path"] = str(manifest_path)
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (agent_dir / "instructions.md").write_text(self._instructions(manifest), encoding="utf-8")
        self._append_registry(manifest)
        if memory:
            memory.add(
                Record(
                    category="agent",
                    subcategory=template_key,
                    kind="agent_manifest",
                    title=clean_name,
                    content=f"{spec['purpose']}\n\nGoal: {clean_goal}\n\nManifest: {manifest_path}",
                    keywords=f"gima agent {template_key} self update research artifact",
                    source=str(manifest_path),
                    confidence="0.80",
                    status="active",
                )
            )
            memory.audit("agent_create", clean_name, f"Created {agent_id} from {template_key}", "ok")
        return CreatedAgent(
            agent_id=agent_id,
            name=clean_name,
            template=template_key,
            goal=clean_goal,
            manifest_path=manifest_path,
            status=str(manifest["status"]),
            self_update_id=str(manifest.get("self_update_id", "")),
            working_copy=str(manifest.get("working_copy", "")),
            plan_path=str(manifest.get("self_update_plan_path", "")),
        )

    def _instructions(self, manifest: dict[str, Any]) -> str:
        lines = [
            f"# {manifest['name']}",
            "",
            f"Template: `{manifest['template']}`",
            f"Status: `{manifest['status']}`",
            "",
            "## Goal",
            manifest["goal"],
            "",
            "## Allowed Actions",
        ]
        lines.extend(f"- {item}" for item in manifest["allowed_actions"])
        lines.extend(["", "## Blocked Actions"])
        lines.extend(f"- {item}" for item in manifest["blocked_actions"])
        lines.extend(["", "## Approval Gate"])
        lines.append("Approval is required before syncing or publishing." if manifest["requires_approval"] else "No sync/publish action is allowed without explicit user instruction.")
        if manifest.get("self_update_id"):
            lines.extend(
                [
                    "",
                    "## Self-Update Workspace",
                    f"- Update ID: `{manifest['self_update_id']}`",
                    f"- Working copy: `{manifest['working_copy']}`",
                    f"- Plan: `{manifest['self_update_plan_path']}`",
                    f"- Backup: `{manifest['backup_path']}`",
                ]
            )
        lines.append("")
        return "\n".join(lines)

    def _read_registry(self) -> list[dict[str, Any]]:
        if not self.registry_path.exists():
            return []
        try:
            rows = json.loads(self.registry_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        return rows if isinstance(rows, list) else []

    def _append_registry(self, manifest: dict[str, Any]) -> None:
        rows = self._read_registry()
        rows.append(
            {
                "id": manifest["id"],
                "name": manifest["name"],
                "template": manifest["template"],
                "goal": manifest["goal"],
                "status": manifest["status"],
                "created_at": manifest["created_at"],
                "manifest_path": manifest["manifest_path"],
                "self_update_id": manifest.get("self_update_id", ""),
                "working_copy": manifest.get("working_copy", ""),
            }
        )
        self.registry_path.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _clean_text(value: str, *, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit]
