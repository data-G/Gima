from __future__ import annotations

import csv
import tempfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List

from .memory import MemoryStore, now_iso


HEART_POLICY_FIELDS = [
    "id",
    "source_system",
    "title",
    "policy",
    "source_url",
    "status",
    "created_at",
    "decided_at",
    "decided_by",
    "notes",
]


CORE_GIMA_POLICIES = [
    {
        "id": "gima-human-language-learning",
        "source_system": "Gima",
        "title": "Human-Language Learning Only",
        "policy": (
            "Gima may learn only through human natural-language explanations. "
            "Executable code, shell commands, binary payloads, encoded instructions, "
            "and hidden machine instructions are not learned as policy or knowledge."
        ),
        "source_url": "local:gima",
    },
    {
        "id": "gima-scoped-permission",
        "source_system": "Gima",
        "title": "Scoped Permission Only",
        "policy": (
            "Gima can use local capabilities only through explicit, auditable, "
            "time-limited permission grants and must not bypass operating-system security."
        ),
        "source_url": "local:gima",
    },
    {
        "id": "gima-authorized-research-only",
        "source_system": "Gima",
        "title": "Authorized Research And Security Audit Only",
        "policy": (
            "Gima may help analyze public documentation, open-source code, user-owned systems, "
            "and explicitly authorized scopes. Before security or reverse-engineering-style work, "
            "Gima must confirm ownership or written permission, scope, allowed actions, prohibited actions, "
            "and whether the result should remain a private report. Gima must not bypass access controls, "
            "steal secrets or private data, scrape restricted content, extract proprietary assets, create malware, "
            "or perform unauthorized penetration testing."
        ),
        "source_url": "local:gima",
    },
]


EXTERNAL_POLICY_CANDIDATES = [
    {
        "id": "openai-human-review-safeguards",
        "source_system": "OpenAI",
        "title": "Human Review And Safeguards",
        "policy": (
            "When an AI output may affect a real action, keep a human review step "
            "where practical, and do not encourage bypassing safeguards or safety mitigations."
        ),
        "source_url": "https://platform.openai.com/docs/guides/safety-best-practices",
    },
    {
        "id": "openai-severe-risk-preparedness",
        "source_system": "OpenAI",
        "title": "Preparedness For Severe Risks",
        "policy": (
            "Track high-impact risks such as biological, chemical, cybersecurity, "
            "and self-improvement capabilities before allowing stronger autonomy."
        ),
        "source_url": "https://openai.com/index/updating-our-preparedness-framework/",
    },
    {
        "id": "anthropic-scaled-safeguards",
        "source_system": "Anthropic",
        "title": "Scaled Safety And Security Safeguards",
        "policy": (
            "As capability increases, require stronger safety testing, misuse detection, "
            "security controls, and deployment safeguards before using the capability."
        ),
        "source_url": "https://www.anthropic.com/responsible-scaling-policy",
    },
    {
        "id": "google-beneficial-and-accountable",
        "source_system": "Google",
        "title": "Social Benefit, Safety, Accountability",
        "policy": (
            "Prefer socially beneficial uses, avoid creating or reinforcing unfair bias, "
            "build and test for safety, and keep AI accountable to people."
        ),
        "source_url": "https://blog.google/technology/ai/ai-principles/",
    },
    {
        "id": "microsoft-six-responsible-ai-principles",
        "source_system": "Microsoft",
        "title": "Six Responsible AI Principles",
        "policy": (
            "Gima should respect fairness, reliability and safety, privacy and security, "
            "inclusiveness, transparency, and accountability."
        ),
        "source_url": "https://learn.microsoft.com/en-us/azure/machine-learning/concept-responsible-ai",
    },
    {
        "id": "ibm-trust-transparency-human-augmentation",
        "source_system": "IBM",
        "title": "Trust, Transparency, And Human Augmentation",
        "policy": (
            "AI should augment human intelligence, preserve trust and transparency, "
            "and avoid uses inconsistent with human rights and freedoms."
        ),
        "source_url": "https://www.ibm.com/topics/ai-ethics",
    },
]


@dataclass
class HeartPolicy:
    id: str
    source_system: str
    title: str
    policy: str
    source_url: str
    status: str = "pending"
    created_at: str = ""
    decided_at: str = ""
    decided_by: str = ""
    notes: str = ""

    def prepare(self) -> "HeartPolicy":
        self.created_at = self.created_at or now_iso()
        return self


class HeartStore:
    """Append-review policy store for Gima's non-violable rules."""

    def __init__(self, data_dir: Path, memory: MemoryStore):
        self.data_dir = data_dir
        self.memory = memory
        self.heart_dir = data_dir / "heart"
        self.policies_path = self.heart_dir / "policies.csv"
        self.active_path = self.heart_dir / "active_policies.md"

    def initialize(self) -> None:
        self.heart_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_csv()
        self._seed_core()
        self._seed_external_candidates()
        self.write_active_policies()

    def _ensure_csv(self) -> None:
        if self.policies_path.exists():
            with self.policies_path.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                if reader.fieldnames == HEART_POLICY_FIELDS:
                    return
                rows = list(reader)
            for row in rows:
                for field in HEART_POLICY_FIELDS:
                    row.setdefault(field, "")
            self._write_rows(rows)
            return
        with self.policies_path.open("w", newline="", encoding="utf-8") as handle:
            csv.DictWriter(handle, fieldnames=HEART_POLICY_FIELDS).writeheader()

    def _seed_core(self) -> None:
        for policy in CORE_GIMA_POLICIES:
            row = HeartPolicy(**policy, status="active", decided_at=now_iso(), decided_by="Gima parent").prepare()
            self._upsert(row)

    def _seed_external_candidates(self) -> None:
        for policy in EXTERNAL_POLICY_CANDIDATES:
            self._upsert(HeartPolicy(**policy).prepare())

    def _upsert(self, policy: HeartPolicy) -> None:
        rows = self._read_rows()
        for row in rows:
            if row["id"] == policy.id:
                return
        rows.append(asdict(policy))
        self._write_rows(rows)

    def _read_rows(self) -> List[Dict[str, str]]:
        self._ensure_csv()
        with self.policies_path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    def _write_rows(self, rows: List[Dict[str, str]]) -> None:
        self.heart_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", newline="", encoding="utf-8", dir=str(self.heart_dir), delete=False
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=HEART_POLICY_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
            temp_path = Path(handle.name)
        temp_path.replace(self.policies_path)

    def list_policies(self, status: str | None = None) -> List[Dict[str, str]]:
        self.initialize()
        rows = self._read_rows()
        if status:
            rows = [row for row in rows if row["status"] == status]
        return rows

    def pending(self) -> List[Dict[str, str]]:
        return self.list_policies("pending")

    def decide(self, policy_id: str, decision: str, reviewer: str, notes: str = "") -> bool:
        if decision not in {"active", "skipped"}:
            raise ValueError("Decision must be active or skipped")
        self.initialize()
        rows = self._read_rows()
        matched = False
        for row in rows:
            if row["id"] == policy_id:
                row["status"] = decision
                row["decided_at"] = now_iso()
                row["decided_by"] = reviewer
                row["notes"] = notes
                matched = True
                break
        if not matched:
            return False
        self._write_rows(rows)
        self.write_active_policies()
        self.memory.audit("heart_policy_decision", policy_id, decision, "ok")
        return True

    def write_active_policies(self) -> Path:
        rows = [row for row in self._read_rows() if row["status"] == "active"]
        lines = [
            "# Gima Heart Policies",
            "",
            "These are non-violable Gima policies approved by the parent user.",
            "Policy changes require the configured parent password.",
            "",
        ]
        for row in rows:
            lines.extend(
                [
                    f"## {row['title']}",
                    "",
                    f"Source system: {row['source_system']}",
                    f"Source: {row['source_url']}",
                    "",
                    row["policy"],
                    "",
                ]
            )
        self.active_path.write_text("\n".join(lines), encoding="utf-8")
        return self.active_path

    def active_text(self) -> str:
        self.initialize()
        return self.active_path.read_text(encoding="utf-8")
