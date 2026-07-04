#!/usr/bin/env python3
from __future__ import annotations

import plistlib
import subprocess
import sys
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parent.parent
DATA_DIR = WORKSPACE / ".human-ai"
LABEL = "com.gima.continuous-cycle"
OLD_LABEL = "com.gima.daily-ai-learning"


def main() -> int:
    launch_dir = Path.home() / "Library" / "LaunchAgents"
    launch_dir.mkdir(parents=True, exist_ok=True)
    plist_path = launch_dir / f"{LABEL}.plist"
    log_dir = DATA_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    plist = {
        "Label": LABEL,
        "ProgramArguments": [
            sys.executable,
            str(WORKSPACE / "scripts" / "gima_continuous_cycle.py"),
            "--workspace", str(WORKSPACE),
            "--config", str(WORKSPACE / "config.local.json"),
            "--provider", "gemini",
            "--rounds", "1",
            "--retention", "14",
        ],
        "StartCalendarInterval": {"Hour": 2, "Minute": 0},
        "WorkingDirectory": str(WORKSPACE),
        "StandardOutPath": str(log_dir / "continuous_cycle.out.log"),
        "StandardErrorPath": str(log_dir / "continuous_cycle.err.log"),
        "ProcessType": "Background",
    }
    with plist_path.open("wb") as handle:
        plistlib.dump(plist, handle)
    old_path = launch_dir / f"{OLD_LABEL}.plist"
    subprocess.run(["launchctl", "unload", "-w", str(old_path)], capture_output=True, check=False)
    subprocess.run(["launchctl", "unload", "-w", str(plist_path)], capture_output=True, check=False)
    subprocess.run(["launchctl", "load", "-w", str(plist_path)], check=True)
    print(plist_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
