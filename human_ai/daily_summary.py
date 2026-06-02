from __future__ import annotations

import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

from .memory import MemoryStore


@dataclass
class DailySummary:
    report_path: Path
    attachment_path: Path
    file_count: int


def _git(workspace: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=str(workspace),
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    return result.stdout.strip()


def _tracked_source_files(workspace: Path) -> List[Path]:
    files = []
    for value in _git(workspace, "ls-files").splitlines():
        path = (workspace / value).resolve()
        if path.is_file():
            files.append(path)
    return files


class DailySummaryService:
    """Package tracked source and a Git summary without including private runtime data."""

    def __init__(self, workspace: Path, data_dir: Path, memory: MemoryStore):
        self.workspace = workspace.resolve()
        self.output_dir = data_dir.resolve() / "daily_summaries"
        self.memory = memory

    def generate(self, since: str = "midnight") -> DailySummary:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().astimezone().strftime("%Y-%m-%d")
        report_path = self.output_dir / f"gima_daily_summary_{stamp}.txt"
        attachment_path = self.output_dir / f"gima_source_snapshot_{stamp}.zip"
        source_files = _tracked_source_files(self.workspace)
        commit_summary = _git(self.workspace, "log", f"--since={since}", "--stat", "--oneline", "--decorate")
        status = _git(self.workspace, "status", "--short")
        report = (
            f"Gima daily source summary for {stamp}\n"
            f"Workspace: {self.workspace}\n"
            f"Tracked files attached: {len(source_files)}\n\n"
            "Git commits since midnight:\n"
            f"{commit_summary or '[no commits]'}\n\n"
            "Current uncommitted changes:\n"
            f"{status or '[clean working tree]'}\n\n"
            "Privacy note: runtime CSV memory, conversations, media, and local configuration "
            "under .human-ai are intentionally excluded.\n"
        )
        report_path.write_text(report, encoding="utf-8")
        with zipfile.ZipFile(attachment_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(report_path, report_path.name)
            for path in source_files:
                archive.write(path, path.relative_to(self.workspace))
        self.memory.audit(
            "daily_summary",
            str(attachment_path),
            f"Packaged {len(source_files)} tracked source files",
            "ok",
        )
        return DailySummary(report_path, attachment_path, len(source_files))

    def send_with_apple_mail(self, recipient: str, summary: DailySummary) -> None:
        if not shutil.which("osascript"):
            raise RuntimeError("Apple Mail delivery requires osascript on macOS")
        script = """
on run argv
    set recipientAddress to item 1 of argv
    set attachmentPath to item 2 of argv
    set reportPath to item 3 of argv
    set reportBody to read POSIX file reportPath
    tell application "Mail"
        set outgoingMessage to make new outgoing message with properties {subject:"Gima daily source summary", content:reportBody & return & return, visible:false}
        tell outgoingMessage
            make new to recipient at end of to recipients with properties {address:recipientAddress}
            make new attachment with properties {file name:POSIX file attachmentPath} at after the last paragraph
            send
        end tell
    end tell
end run
"""
        subprocess.run(
            ["osascript", "-e", script, recipient, str(summary.attachment_path), str(summary.report_path)],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.memory.audit("daily_summary_email", recipient, str(summary.attachment_path), "ok")
