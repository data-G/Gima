from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .memory import MemoryStore


@dataclass
class ViolationReport:
    report_path: Path
    recipient: str
    sent: bool


class ViolationReporter:
    def __init__(self, data_dir: Path, memory: MemoryStore):
        self.output_dir = data_dir.resolve() / "violations"
        self.memory = memory

    def create_report(self, reason: str, request: str, source: str = "gima") -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
        report_path = self.output_dir / f"heart_violation_{stamp}.txt"
        report = (
            "Gima heart policy violation report\n"
            f"Time: {datetime.now().astimezone().isoformat(timespec='seconds')}\n"
            f"Source: {source}\n"
            f"Reason: {reason}\n\n"
            "Request or event:\n"
            f"{request}\n\n"
            "Action taken:\n"
            "Gima did not perform the violating action. The event was logged for parent review.\n"
        )
        report_path.write_text(report, encoding="utf-8")
        self.memory.audit("heart_violation", source, f"{reason}; report={report_path}", "blocked")
        return report_path

    def send_with_apple_mail(self, recipient: str, report_path: Path) -> None:
        if not shutil.which("osascript"):
            raise RuntimeError("Apple Mail delivery requires osascript on macOS")
        script = """
on run argv
    set recipientAddress to item 1 of argv
    set reportPath to item 2 of argv
    set reportBody to read POSIX file reportPath
    tell application "Mail"
        set outgoingMessage to make new outgoing message with properties {subject:"Gima heart policy violation", content:reportBody & return & return, visible:false}
        tell outgoingMessage
            make new to recipient at end of to recipients with properties {address:recipientAddress}
            make new attachment with properties {file name:POSIX file reportPath} at after the last paragraph
            send
        end tell
    end tell
end run
"""
        subprocess.run(
            ["osascript", "-e", script, recipient, str(report_path)],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.memory.audit("heart_violation_email", recipient, str(report_path), "ok")

    def report(self, recipient: str, reason: str, request: str, source: str = "gima") -> ViolationReport:
        report_path = self.create_report(reason, request, source)
        self.send_with_apple_mail(recipient, report_path)
        return ViolationReport(report_path=report_path, recipient=recipient, sent=True)
