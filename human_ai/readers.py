from __future__ import annotations

import csv
import json
import mimetypes
import shutil
import subprocess
from pathlib import Path
from typing import Iterable, List

from .memory import Record


TEXT_SUFFIXES = {
    ".txt",
    ".md",
    ".rst",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".java",
    ".c",
    ".h",
    ".cpp",
    ".go",
    ".rs",
    ".sh",
    ".html",
    ".css",
    ".sql",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
AUDIO_SUFFIXES = {".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg"}


def _chunks(text: str, size: int = 3500, overlap: int = 250) -> Iterable[str]:
    cleaned = text.replace("\x00", "").strip()
    if not cleaned:
        return
    position = 0
    while position < len(cleaned):
        yield cleaned[position : position + size]
        position += max(1, size - overlap)


def _command_output(command: List[str]) -> str:
    result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    return (result.stdout or result.stderr).strip()


def _category(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return "vision"
    if suffix in VIDEO_SUFFIXES:
        return "video"
    if suffix in AUDIO_SUFFIXES:
        return "audio"
    if suffix in {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".c", ".cpp", ".go", ".rs"}:
        return "code"
    return "files"


def read_file(path: Path) -> List[Record]:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    suffix = path.suffix.lower()
    source = str(path)
    records: List[Record] = []

    if suffix in TEXT_SUFFIXES:
        text = path.read_text(encoding="utf-8", errors="replace")
    elif suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        text = json.dumps(data, ensure_ascii=True, indent=2)
    elif suffix == ".csv":
        with path.open(newline="", encoding="utf-8", errors="replace") as handle:
            reader = csv.reader(handle)
            rows = []
            for index, row in enumerate(reader):
                rows.append(", ".join(row))
                if index >= 200:
                    rows.append("[sample truncated after 200 rows]")
                    break
        text = "\n".join(rows)
    elif suffix == ".pdf" and shutil.which("pdftotext"):
        text = _command_output(["pdftotext", str(path), "-"])
    elif suffix in IMAGE_SUFFIXES:
        details = [f"Image file: {path.name}", f"MIME type: {mimetypes.guess_type(path.name)[0]}"]
        if shutil.which("tesseract"):
            ocr = _command_output(["tesseract", str(path), "stdout"])
            if ocr:
                details.append(f"OCR text:\n{ocr}")
        text = "\n".join(details)
    elif suffix in VIDEO_SUFFIXES | AUDIO_SUFFIXES:
        details = [f"Media file: {path.name}", f"MIME type: {mimetypes.guess_type(path.name)[0]}"]
        if shutil.which("ffprobe"):
            details.append(
                _command_output(
                    [
                        "ffprobe",
                        "-v",
                        "error",
                        "-show_entries",
                        "format=duration,size,bit_rate:stream=codec_name,width,height",
                        "-of",
                        "default=noprint_wrappers=1",
                        str(path),
                    ]
                )
            )
        text = "\n".join(details)
    else:
        text = f"Binary or unsupported file: {path.name}\nSize: {path.stat().st_size} bytes"

    for index, chunk in enumerate(_chunks(text), start=1):
        records.append(
            Record(
                category=_category(path),
                subcategory=suffix.lstrip(".") or "unknown",
                kind="file_chunk",
                title=f"{path.name} [chunk {index}]",
                content=chunk,
                keywords=f"{path.name} {suffix.lstrip('.')}",
                source=source,
                media_path=source if suffix in IMAGE_SUFFIXES | VIDEO_SUFFIXES | AUDIO_SUFFIXES else "",
            )
        )
    return records


def iter_files(path: Path) -> Iterable[Path]:
    path = path.expanduser().resolve()
    if path.is_file():
        yield path
        return
    for candidate in path.rglob("*"):
        if candidate.is_file() and ".git" not in candidate.parts and ".human-ai" not in candidate.parts:
            yield candidate

