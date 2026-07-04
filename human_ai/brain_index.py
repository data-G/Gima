from __future__ import annotations

import csv
import mimetypes
from pathlib import Path
from typing import Iterable, Sequence

from .memory import RECORD_FIELDS


BRAIN_INDEX_FIELDS = [
    "source_type",
    "category",
    "subcategory",
    "kind",
    "title",
    "path",
    "media_path",
    "size_bytes",
    "content_type",
    "status",
    "confidence",
    "updated_at",
    "summary",
    "content",
]


def rebuild_brain_csv(data_dir: Path, extra_roots: Sequence[Path] | None = None) -> Path:
    brain_dir = data_dir / "brain"
    brain_dir.mkdir(parents=True, exist_ok=True)
    target = brain_dir / "brain.csv"
    rows = list(_knowledge_rows(data_dir / "csv" / "knowledge.csv"))
    for root in extra_roots or []:
        rows.extend(_file_rows(root, data_dir))
    _write_rows(target, rows)
    return target


def ensure_brain_csv(data_dir: Path, extra_roots: Sequence[Path] | None = None) -> Path:
    target = data_dir / "brain" / "brain.csv"
    if not target.exists():
        return rebuild_brain_csv(data_dir, extra_roots)
    return target


def _knowledge_rows(path: Path) -> Iterable[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        reader = csv.DictReader(handle)
        if not set(reader.fieldnames or []).issubset(set(RECORD_FIELDS)):
            return []
        for row in reader:
            content = row.get("content", "").replace("\n", " ").strip()
            raw_content = row.get("content", "").strip()
            yield {
                "source_type": "knowledge",
                "category": row.get("category", ""),
                "subcategory": row.get("subcategory", ""),
                "kind": row.get("kind", ""),
                "title": row.get("title", ""),
                "path": row.get("source", ""),
                "media_path": row.get("media_path", ""),
                "size_bytes": "",
                "content_type": "",
                "status": row.get("status", ""),
                "confidence": row.get("confidence", ""),
                "updated_at": row.get("updated_at", ""),
                "summary": content[:500],
                "content": raw_content,
            }


def _file_rows(root: Path, data_dir: Path) -> Iterable[dict[str, str]]:
    if not root.exists():
        return []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.name == "brain.csv":
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        relative = _safe_relative(path, data_dir)
        content = _file_preview(path)
        yield {
            "source_type": "file",
            "category": relative.parts[0] if relative.parts else "file",
            "subcategory": relative.parts[1] if len(relative.parts) > 1 else "",
            "kind": "local_file",
            "title": path.name,
            "path": str(path),
            "media_path": str(path) if _is_media(path) else "",
            "size_bytes": str(stat.st_size),
            "content_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
            "status": "active",
            "confidence": "1.00",
            "updated_at": "",
            "summary": f"Local file indexed from {relative}",
            "content": content,
        }


def _write_rows(path: Path, rows: Iterable[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=BRAIN_INDEX_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in BRAIN_INDEX_FIELDS})


def _safe_relative(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return Path(path.name)


def _is_media(path: Path) -> bool:
    return path.suffix.casefold() in {".mp3", ".wav", ".m4a", ".mp4", ".mov", ".jpg", ".jpeg", ".png", ".webp"}


def _file_preview(path: Path) -> str:
    if path.suffix.casefold() not in {".txt", ".md", ".csv", ".json", ".py", ".html", ".css", ".js", ".log"}:
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:4000]
    except OSError:
        return ""
