from __future__ import annotations

import csv
import hashlib
import time
import uuid
from pathlib import Path


TEACHER_CACHE_FIELDS = [
    "id",
    "question_hash",
    "question",
    "provider",
    "answer",
    "created_at",
    "last_used_at",
    "use_count",
    "status",
]


class TeacherAnswerCache:
    def __init__(self, data_dir: Path):
        self.path = data_dir / "csv" / "teacher_answer_cache.csv"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_csv()

    def get(self, question: str, providers: list[str] | None = None, limit: int = 6) -> list[dict[str, str]]:
        question_hash = question_fingerprint(question)
        allowed = {provider.casefold().strip() for provider in providers or []}
        rows = []
        for row in self._rows():
            if row["question_hash"] != question_hash or row["status"] != "active":
                continue
            if allowed and row["provider"] not in allowed:
                continue
            rows.append(row)
        rows.sort(key=lambda row: row.get("created_at", ""), reverse=True)
        selected = rows[: max(1, limit)]
        if selected:
            self._record_use({row["id"] for row in selected})
        return selected

    def add(self, question: str, provider: str, answer: str) -> str:
        question_hash = question_fingerprint(question)
        provider = provider.casefold().strip()
        rows = self._rows()
        for row in rows:
            if row["question_hash"] == question_hash and row["provider"] == provider and row["status"] == "active":
                row["answer"] = answer
                row["last_used_at"] = _now()
                row["use_count"] = str(int(row.get("use_count") or "0") + 1)
                self._write_rows(rows)
                return row["id"]
        cache_id = f"tc_{uuid.uuid4().hex}"
        rows.append(
            {
                "id": cache_id,
                "question_hash": question_hash,
                "question": question,
                "provider": provider,
                "answer": answer,
                "created_at": _now(),
                "last_used_at": _now(),
                "use_count": "1",
                "status": "active",
            }
        )
        self._write_rows(rows)
        return cache_id

    def _record_use(self, ids: set[str]) -> None:
        rows = self._rows()
        for row in rows:
            if row["id"] in ids:
                row["last_used_at"] = _now()
                row["use_count"] = str(int(row.get("use_count") or "0") + 1)
        self._write_rows(rows)

    def _ensure_csv(self) -> None:
        if self.path.exists():
            return
        with self.path.open("w", newline="", encoding="utf-8") as handle:
            csv.DictWriter(handle, fieldnames=TEACHER_CACHE_FIELDS).writeheader()

    def _rows(self) -> list[dict[str, str]]:
        self._ensure_csv()
        with self.path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    def _write_rows(self, rows: list[dict[str, str]]) -> None:
        with self.path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=TEACHER_CACHE_FIELDS)
            writer.writeheader()
            writer.writerows(rows)


def question_fingerprint(question: str) -> str:
    normalized = " ".join(question.casefold().strip().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")
