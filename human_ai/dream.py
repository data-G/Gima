from __future__ import annotations

import csv
import tempfile
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List

from .memory import now_iso


DREAM_IDEA_FIELDS = [
    "id",
    "status",
    "title",
    "theory",
    "why_it_might_be_new",
    "possible_path",
    "evidence_needed",
    "risk_level",
    "parent_status",
    "created_at",
    "updated_at",
]

DREAM_EXPERIMENT_FIELDS = [
    "id",
    "idea_id",
    "status",
    "question",
    "method",
    "success_signal",
    "result_summary",
    "created_at",
    "updated_at",
]

DREAM_SOURCE_FIELDS = [
    "id",
    "idea_id",
    "source",
    "claim",
    "supports_or_refutes",
    "confidence",
    "review_status",
    "created_at",
]

DREAM_REVIEW_FIELDS = [
    "id",
    "idea_id",
    "decision",
    "reviewer",
    "notes",
    "created_at",
]

DREAM_QUESTION_FIELDS = [
    "id",
    "category",
    "question",
    "why_it_matters",
    "created_at",
]


SEED_QUESTIONS = [
    {
        "category": "memory",
        "question": "Can Gima build a personal memory map that updates from conversations, files, and source-reviewed web learning?",
        "why_it_matters": "A better memory map could make Gima feel more continuous and useful without retraining the model.",
    },
    {
        "category": "voice",
        "question": "Can Gima learn a user's speech habits and recover intent from imperfect transcripts?",
        "why_it_matters": "Human-like interaction needs robust understanding when microphones, accents, and noise are imperfect.",
    },
    {
        "category": "vision",
        "question": "Can Gima maintain a consent-based scene timeline from camera snapshots and screen context?",
        "why_it_matters": "A timeline would let Gima reason about what changed, not just what is visible right now.",
    },
    {
        "category": "self-improvement",
        "question": "Can Gima propose code updates in a copied workspace, test them, and ask for approval before syncing?",
        "why_it_matters": "This keeps self-improvement practical while preserving parent control and rollback.",
    },
    {
        "category": "invention",
        "question": "Can Gima combine research papers into new testable feature theories instead of only summarizing them?",
        "why_it_matters": "The Dream folder should turn learning into experiments that can produce original progress.",
    },
]


@dataclass
class DreamIdea:
    title: str
    theory: str
    why_it_might_be_new: str = ""
    possible_path: str = ""
    evidence_needed: str = ""
    risk_level: str = "medium"
    status: str = "theory"
    parent_status: str = "pending"
    id: str = ""
    created_at: str = ""
    updated_at: str = ""

    def prepare(self) -> "DreamIdea":
        self.id = self.id or f"dream_{uuid.uuid4().hex}"
        self.created_at = self.created_at or now_iso()
        self.updated_at = now_iso()
        return self


class DreamStore:
    def __init__(self, data_dir: Path):
        self.root = data_dir / "brain" / "Dream"
        self.ideas_path = self.root / "ideas.csv"
        self.experiments_path = self.root / "experiments.csv"
        self.sources_path = self.root / "sources.csv"
        self.reviews_path = self.root / "reviews.csv"
        self.questions_path = self.root / "daily_questions.csv"
        self.readme_path = self.root / "README.md"

    def initialize(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self._ensure_readme()
        self._ensure_csv(self.ideas_path, DREAM_IDEA_FIELDS)
        self._ensure_csv(self.experiments_path, DREAM_EXPERIMENT_FIELDS)
        self._ensure_csv(self.sources_path, DREAM_SOURCE_FIELDS)
        self._ensure_csv(self.reviews_path, DREAM_REVIEW_FIELDS)
        self._ensure_csv(self.questions_path, DREAM_QUESTION_FIELDS)
        self._seed_questions()

    def add_idea(self, idea: DreamIdea) -> str:
        self.initialize()
        idea.prepare()
        with self.ideas_path.open("a", newline="", encoding="utf-8") as handle:
            csv.DictWriter(handle, fieldnames=DREAM_IDEA_FIELDS).writerow(asdict(idea))
        return idea.id

    def list_ideas(self, limit: int = 20) -> List[Dict[str, str]]:
        self.initialize()
        with self.ideas_path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        return rows[-max(1, min(limit, 200)) :][::-1]

    def _ensure_readme(self) -> None:
        if self.readme_path.exists():
            return
        self.readme_path.write_text(
            "\n".join(
                [
                    "# Gima Dream Folder",
                    "",
                    "Dream is Gima's theory lab for ideas that may be possible but are not yet proven.",
                    "It should collect plain human-language theories, source evidence, experiments, and parent review decisions.",
                    "",
                    "Rules:",
                    "",
                    "- Keep ideas in human natural language.",
                    "- Treat every dream as unproven until evidence is recorded.",
                    "- Use sources and small experiments before calling an idea correct.",
                    "- Ask for approval before risky actions, machine access changes, or live system syncs.",
                    "- Prefer reversible tests in a copied workspace.",
                    "",
                    "Files:",
                    "",
                    "- ideas.csv: theories and possible paths.",
                    "- experiments.csv: tests for one idea.",
                    "- sources.csv: evidence that supports or refutes an idea.",
                    "- reviews.csv: parent decisions.",
                    "- daily_questions.csv: prompts for finding new things to try.",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    @staticmethod
    def _ensure_csv(path: Path, fields: List[str]) -> None:
        if not path.exists():
            with path.open("w", newline="", encoding="utf-8") as handle:
                csv.DictWriter(handle, fieldnames=fields).writeheader()
            return
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames == fields:
                return
            rows = list(reader)
        if not set(reader.fieldnames or []).issubset(fields):
            raise ValueError(f"CSV schema mismatch: {path}")
        for row in rows:
            for field in fields:
                row.setdefault(field, "")
        with tempfile.NamedTemporaryFile(
            "w", newline="", encoding="utf-8", dir=str(path.parent), delete=False
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
            temp_path = Path(handle.name)
        temp_path.replace(path)

    def _seed_questions(self) -> None:
        with self.questions_path.open(newline="", encoding="utf-8") as handle:
            if list(csv.DictReader(handle)):
                return
        with self.questions_path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=DREAM_QUESTION_FIELDS)
            for question in SEED_QUESTIONS:
                writer.writerow(
                    {
                        "id": f"dream_question_{uuid.uuid4().hex}",
                        "category": question["category"],
                        "question": question["question"],
                        "why_it_matters": question["why_it_matters"],
                        "created_at": now_iso(),
                    }
                )
