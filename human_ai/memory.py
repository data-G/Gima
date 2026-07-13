from __future__ import annotations

import csv
import fcntl
import hashlib
import io
import sqlite3
import tempfile
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional


RECORD_FIELDS = [
    "id",
    "category",
    "subcategory",
    "kind",
    "title",
    "content",
    "keywords",
    "source",
    "media_path",
    "created_at",
    "updated_at",
    "confidence",
    "status",
    "checksum",
]

CONVERSATION_FIELDS = [
    "id",
    "timestamp",
    "session_id",
    "role",
    "message",
    "category",
    "importance",
]

AUDIT_FIELDS = ["timestamp", "action", "target", "details", "status"]

SOURCE_REVIEW_FIELDS = [
    "id",
    "timestamp",
    "record_id",
    "title",
    "source",
    "category",
    "subcategory",
    "claim_summary",
    "internet_status",
    "user_status",
    "parent_status",
    "review_notes",
    "approved_by",
    "approved_at",
]

PARENT_APPROVAL_FIELDS = ["timestamp", "action", "target", "result", "notes"]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def checksum(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


@dataclass
class Record:
    category: str
    title: str
    content: str
    subcategory: str = ""
    kind: str = "fact"
    keywords: str = ""
    source: str = ""
    media_path: str = ""
    confidence: str = "0.80"
    status: str = "active"
    id: str = ""
    created_at: str = ""
    updated_at: str = ""
    checksum: str = ""

    def prepare(self) -> "Record":
        self.id = self.id or f"kb_{uuid.uuid4().hex}"
        self.created_at = self.created_at or now_iso()
        self.updated_at = now_iso()
        self.checksum = self.checksum or checksum(
            "|".join([self.title, self.content, self.source, self.media_path])
        )
        return self


class MemoryStore:
    """CSV source of truth with a disposable SQLite FTS5 retrieval cache."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.csv_dir = data_dir / "csv"
        self.db_path = data_dir / "index.sqlite3"
        self.knowledge_path = self.csv_dir / "knowledge.csv"
        self.conversations_path = self.csv_dir / "conversations.csv"
        self.audit_path = self.csv_dir / "audit.csv"
        self.source_reviews_path = self.csv_dir / "source_reviews.csv"
        self.parent_approvals_path = self.csv_dir / "parent_approvals.csv"
        self.lock_path = data_dir / "memory.lock"

    def initialize(self) -> None:
        self.csv_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_csv(self.knowledge_path, RECORD_FIELDS)
        self._ensure_csv(self.conversations_path, CONVERSATION_FIELDS)
        self._ensure_csv(self.audit_path, AUDIT_FIELDS)
        self._ensure_csv(self.source_reviews_path, SOURCE_REVIEW_FIELDS)
        self._ensure_csv(self.parent_approvals_path, PARENT_APPROVAL_FIELDS)
        if not self.db_path.exists():
            self.rebuild_index()

    @staticmethod
    def _ensure_csv(path: Path, fields: List[str]) -> None:
        if not path.exists():
            with path.open("w", newline="", encoding="utf-8") as handle:
                csv.DictWriter(handle, fieldnames=fields).writeheader()
            return
        fieldnames, rows = _read_csv_rows(path)
        if fieldnames == fields:
            return
        if not set(fieldnames or []).issubset(fields):
            raise ValueError(f"CSV schema mismatch: {path}")
        for row in rows:
            for field in fields:
                row.setdefault(field, "")
            if "id" in fields and not row["id"]:
                row["id"] = f"conv_{uuid.uuid4().hex}"
        with tempfile.NamedTemporaryFile(
            "w", newline="", encoding="utf-8", dir=str(path.parent), delete=False
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(_clean_row(row) for row in rows)
            temp_path = Path(handle.name)
        temp_path.replace(path)

    def add(self, record: Record) -> str:
        self.initialize()
        record.prepare()
        if self.find_by_checksum(record.checksum):
            return record.id
        with self.knowledge_path.open("a", newline="", encoding="utf-8") as handle:
            csv.DictWriter(handle, fieldnames=RECORD_FIELDS).writerow(_clean_row(asdict(record)))
        self._index_record(asdict(record))
        return record.id

    def add_many(self, records: Iterable[Record]) -> int:
        count = 0
        for record in records:
            before = len(self.find_by_checksum(record.prepare().checksum))
            self.add(record)
            if before == 0:
                count += 1
        return count

    def replace_source(self, source: str, records: Iterable[Record]) -> int:
        """Archive old chunks for one file and activate its current chunk set."""
        self.initialize()
        prepared = [record.prepare() for record in records]
        with self._write_lock():
            _, rows = _read_csv_rows(self.knowledge_path)
            known_checksums = {row["checksum"]: row for row in rows}
            for row in rows:
                if row["source"] == source and row["status"] == "active":
                    row["status"] = "archived"
                    row["updated_at"] = now_iso()
            added = 0
            for record in prepared:
                existing = known_checksums.get(record.checksum)
                if existing:
                    existing["status"] = "active"
                    existing["updated_at"] = now_iso()
                else:
                    rows.append(asdict(record))
                    known_checksums[record.checksum] = rows[-1]
                    added += 1
            with tempfile.NamedTemporaryFile(
                "w", newline="", encoding="utf-8", dir=str(self.csv_dir), delete=False
            ) as handle:
                writer = csv.DictWriter(handle, fieldnames=RECORD_FIELDS)
                writer.writeheader()
                writer.writerows(_clean_row(row) for row in rows)
                temp_path = Path(handle.name)
            temp_path.replace(self.knowledge_path)
            self.rebuild_index(locked=True)
            return added

    def find_by_checksum(self, value: str) -> List[Dict[str, str]]:
        self.initialize()
        _, rows = _read_csv_rows(self.knowledge_path)
        return [row for row in rows if row["checksum"] == value]

    def append_conversation(
        self,
        session_id: str,
        role: str,
        message: str,
        category: str = "conversation",
        importance: str = "0.50",
    ) -> None:
        self.initialize()
        row = {
            "id": f"conv_{uuid.uuid4().hex}",
            "timestamp": now_iso(),
            "session_id": session_id,
            "role": role,
            "message": message,
            "category": category,
            "importance": importance,
        }
        with self.conversations_path.open("a", newline="", encoding="utf-8") as handle:
            csv.DictWriter(handle, fieldnames=CONVERSATION_FIELDS).writerow(_clean_row(row))
        self._index_conversation(row)

    def search_conversations(
        self, query: str = "", session_id: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, str]]:
        self.initialize()
        tokens = [token for token in query.replace('"', " ").split() if token]
        with self._connect() as connection:
            self._create_schema(connection)
            if tokens:
                match = " OR ".join(f'"{token}"' for token in tokens[:16])
                sql = (
                    "SELECT c.*, bm25(conversations_fts) AS score "
                    "FROM conversations_fts JOIN conversations c ON c.id = conversations_fts.id "
                    "WHERE conversations_fts MATCH ? "
                )
                params: List[object] = [match]
            else:
                sql = "SELECT c.*, 0 AS score FROM conversations c WHERE 1 = 1 "
                params = []
            if session_id:
                sql += "AND c.session_id = ? "
                params.append(session_id)
            sql += "ORDER BY score, c.timestamp DESC LIMIT ?"
            params.append(max(1, min(limit, 500)))
            return [dict(row) for row in connection.execute(sql, params)]

    def audit(self, action: str, target: str, details: str, status: str) -> None:
        self.initialize()
        row = {
            "timestamp": now_iso(),
            "action": action,
            "target": target,
            "details": details,
            "status": status,
        }
        with self.audit_path.open("a", newline="", encoding="utf-8") as handle:
            csv.DictWriter(handle, fieldnames=AUDIT_FIELDS).writerow(_clean_row(row))

    def add_source_review(
        self,
        record_id: str,
        title: str,
        source: str,
        category: str,
        subcategory: str,
        claim_summary: str,
        internet_status: str = "imported",
        user_status: str = "pending",
        parent_status: str = "pending",
    ) -> str:
        self.initialize()
        row = {
            "id": f"review_{uuid.uuid4().hex}",
            "timestamp": now_iso(),
            "record_id": record_id,
            "title": title,
            "source": source,
            "category": category,
            "subcategory": subcategory,
            "claim_summary": claim_summary[:1000],
            "internet_status": internet_status,
            "user_status": user_status,
            "parent_status": parent_status,
            "review_notes": "",
            "approved_by": "",
            "approved_at": "",
        }
        with self.source_reviews_path.open("a", newline="", encoding="utf-8") as handle:
            csv.DictWriter(handle, fieldnames=SOURCE_REVIEW_FIELDS).writerow(_clean_row(row))
        self.audit("source_review_add", row["id"], source, "ok")
        return row["id"]

    def list_source_reviews(
        self, parent_status: str | None = None, limit: int = 50
    ) -> List[Dict[str, str]]:
        self.initialize()
        _, rows = _read_csv_rows(self.source_reviews_path)
        if parent_status:
            rows = [row for row in rows if row["parent_status"] == parent_status]
        return list(reversed(rows))[: max(1, min(limit, 500))]

    def parent_review_decision(
        self,
        review_id: str,
        decision: str,
        reviewer: str,
        notes: str = "",
    ) -> bool:
        if decision not in {"approved", "rejected"}:
            raise ValueError("Decision must be approved or rejected")
        self.initialize()
        _, rows = _read_csv_rows(self.source_reviews_path)
        matched: Dict[str, str] | None = None
        for row in rows:
            if row["id"] == review_id:
                row["parent_status"] = decision
                row["user_status"] = decision
                row["review_notes"] = notes
                row["approved_by"] = reviewer
                row["approved_at"] = now_iso()
                matched = row
                break
        if not matched:
            self.append_parent_approval("review_decision", review_id, "not_found", notes)
            return False
        with tempfile.NamedTemporaryFile(
            "w", newline="", encoding="utf-8", dir=str(self.csv_dir), delete=False
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=SOURCE_REVIEW_FIELDS)
            writer.writeheader()
            writer.writerows(_clean_row(row) for row in rows)
            temp_path = Path(handle.name)
        temp_path.replace(self.source_reviews_path)
        if matched["record_id"]:
            self.update_status(matched["record_id"], "active" if decision == "approved" else "archived")
        self.append_parent_approval("review_decision", review_id, decision, notes)
        return True

    def append_parent_approval(self, action: str, target: str, result: str, notes: str = "") -> None:
        self.initialize()
        row = {
            "timestamp": now_iso(),
            "action": action,
            "target": target,
            "result": result,
            "notes": notes,
        }
        with self.parent_approvals_path.open("a", newline="", encoding="utf-8") as handle:
            csv.DictWriter(handle, fieldnames=PARENT_APPROVAL_FIELDS).writerow(_clean_row(row))
        self.audit("parent_approval", target, f"{action}: {result}", "ok")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.db_path), timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=30000")
        return connection

    @contextmanager
    def _write_lock(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with self.lock_path.open("w", encoding="utf-8") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    @staticmethod
    def _create_schema(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS records (
                id TEXT PRIMARY KEY,
                category TEXT,
                subcategory TEXT,
                kind TEXT,
                title TEXT,
                content TEXT,
                keywords TEXT,
                source TEXT,
                media_path TEXT,
                created_at TEXT,
                updated_at TEXT,
                confidence TEXT,
                status TEXT,
                checksum TEXT
            );
            CREATE INDEX IF NOT EXISTS records_category_idx
                ON records(category, subcategory, kind, updated_at);
            CREATE INDEX IF NOT EXISTS records_checksum_idx ON records(checksum);
            CREATE VIRTUAL TABLE IF NOT EXISTS records_fts USING fts5(
                id UNINDEXED, title, content, keywords, category, subcategory
            );
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                timestamp TEXT,
                session_id TEXT,
                role TEXT,
                message TEXT,
                category TEXT,
                importance TEXT
            );
            CREATE INDEX IF NOT EXISTS conversations_session_idx
                ON conversations(session_id, timestamp);
            CREATE VIRTUAL TABLE IF NOT EXISTS conversations_fts USING fts5(
                id UNINDEXED, message, role, category, session_id
            );
            """
        )

    def _index_record(self, row: Dict[str, str]) -> None:
        with self._connect() as connection:
            self._create_schema(connection)
            inserted = connection.execute(
                f"INSERT OR IGNORE INTO records ({','.join(RECORD_FIELDS)}) "
                f"VALUES ({','.join('?' for _ in RECORD_FIELDS)})",
                [row[field] for field in RECORD_FIELDS],
            )
            if inserted.rowcount:
                connection.execute(
                    "INSERT INTO records_fts "
                    "(id, title, content, keywords, category, subcategory) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    [
                        row["id"],
                        row["title"],
                        row["content"],
                        row["keywords"],
                        row["category"],
                        row["subcategory"],
                    ],
                )

    def _index_conversation(self, row: Dict[str, str]) -> None:
        with self._connect() as connection:
            self._create_schema(connection)
            inserted = connection.execute(
                f"INSERT OR IGNORE INTO conversations ({','.join(CONVERSATION_FIELDS)}) "
                f"VALUES ({','.join('?' for _ in CONVERSATION_FIELDS)})",
                [row[field] for field in CONVERSATION_FIELDS],
            )
            if inserted.rowcount:
                connection.execute(
                    "INSERT INTO conversations_fts (id, message, role, category, session_id) "
                    "VALUES (?, ?, ?, ?, ?)",
                    [row["id"], row["message"], row["role"], row["category"], row["session_id"]],
                )

    def rebuild_index(self, locked: bool = False) -> int:
        if not locked:
            with self._write_lock():
                return self.rebuild_index(locked=True)
        self.csv_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_csv(self.knowledge_path, RECORD_FIELDS)
        self._ensure_csv(self.conversations_path, CONVERSATION_FIELDS)
        self._ensure_csv(self.source_reviews_path, SOURCE_REVIEW_FIELDS)
        self._ensure_csv(self.parent_approvals_path, PARENT_APPROVAL_FIELDS)
        for path in [self.db_path, self.db_path.with_name(f"{self.db_path.name}-wal"), self.db_path.with_name(f"{self.db_path.name}-shm")]:
            if path.exists():
                path.unlink()
        count = 0
        with self._connect() as connection:
            self._create_schema(connection)
            _, knowledge_rows = _read_csv_rows(self.knowledge_path)
            for row in knowledge_rows:
                connection.execute(
                    f"INSERT OR REPLACE INTO records ({','.join(RECORD_FIELDS)}) "
                    f"VALUES ({','.join('?' for _ in RECORD_FIELDS)})",
                    [row[field] for field in RECORD_FIELDS],
                )
                connection.execute(
                    "INSERT INTO records_fts "
                    "(id, title, content, keywords, category, subcategory) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    [
                        row["id"],
                        row["title"],
                        row["content"],
                        row["keywords"],
                        row["category"],
                        row["subcategory"],
                    ],
                )
                count += 1
            if self.conversations_path.exists():
                _, conversation_rows = _read_csv_rows(self.conversations_path)
                for row in conversation_rows:
                    if not row.get("id"):
                        row["id"] = f"conv_{uuid.uuid4().hex}"
                    connection.execute(
                        f"INSERT OR REPLACE INTO conversations ({','.join(CONVERSATION_FIELDS)}) "
                        f"VALUES ({','.join('?' for _ in CONVERSATION_FIELDS)})",
                        [row[field] for field in CONVERSATION_FIELDS],
                    )
                    connection.execute(
                        "INSERT INTO conversations_fts (id, message, role, category, session_id) "
                        "VALUES (?, ?, ?, ?, ?)",
                        [row["id"], row["message"], row["role"], row["category"], row["session_id"]],
                    )
        return count

    def search(
        self, query: str, category: Optional[str] = None, limit: int = 8
    ) -> List[Dict[str, str]]:
        self.initialize()
        tokens = [token for token in query.replace('"', " ").split() if token]
        with self._connect() as connection:
            self._create_schema(connection)
            if tokens:
                match = " OR ".join(f'"{token}"' for token in tokens[:16])
                sql = (
                    "SELECT r.*, bm25(records_fts) AS score "
                    "FROM records_fts JOIN records r ON r.id = records_fts.id "
                    "WHERE records_fts MATCH ? AND r.status = 'active' "
                )
                params: List[object] = [match]
            else:
                sql = "SELECT r.*, 0 AS score FROM records r WHERE r.status = 'active' "
                params = []
            if category:
                sql += "AND r.category = ? "
                params.append(category)
            sql += "ORDER BY score, r.updated_at DESC LIMIT ?"
            params.append(max(1, min(limit, 100)))
            return [dict(row) for row in connection.execute(sql, params)]

    def list_by_status(self, status: str, limit: int = 50) -> List[Dict[str, str]]:
        self.initialize()
        with self._connect() as connection:
            self._create_schema(connection)
            rows = connection.execute(
                "SELECT * FROM records WHERE status = ? ORDER BY updated_at DESC LIMIT ?",
                [status, max(1, min(limit, 500))],
            )
            return [dict(row) for row in rows]

    def update_status(self, record_id: str, status: str) -> bool:
        if status not in {"active", "review", "archived"}:
            raise ValueError("Status must be active, review, or archived")
        self.initialize()
        changed = False
        _, rows = _read_csv_rows(self.knowledge_path)
        for row in rows:
            if row["id"] == record_id:
                row["status"] = status
                row["updated_at"] = now_iso()
                changed = True
        if not changed:
            return False
        with tempfile.NamedTemporaryFile(
            "w", newline="", encoding="utf-8", dir=str(self.csv_dir), delete=False
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=RECORD_FIELDS)
            writer.writeheader()
            writer.writerows(_clean_row(row) for row in rows)
            temp_path = Path(handle.name)
        temp_path.replace(self.knowledge_path)
        self.rebuild_index()
        self.audit("memory_status", record_id, f"Changed status to {status}", "ok")
        return True


def _read_csv_rows(path: Path) -> tuple[list[str] | None, list[Dict[str, str]]]:
    text = path.read_text(encoding="utf-8", errors="replace").replace("\x00", "")
    reader = csv.DictReader(io.StringIO(text))
    rows = [_clean_row(row) for row in reader]
    return reader.fieldnames, rows


def _clean_row(row: Dict[str, object]) -> Dict[str, str]:
    return {str(key): _clean_cell(value) for key, value in row.items()}


def _clean_cell(value: object) -> str:
    return str(value or "").replace("\x00", "").replace("\r", " ").strip()
