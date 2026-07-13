#!/usr/bin/env python3
from __future__ import annotations

import sys
import fcntl
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parent.parent
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

from human_ai.brain import BrainServer
from human_ai.config import load_config
from human_ai.memory import MemoryStore
from human_ai.system_doctor import run_ai_era_requirements_agent


def main() -> int:
    config_path = WORKSPACE / "config.local.json"
    config = load_config(str(config_path))
    lock_dir = config.resolved_data_dir / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    with (lock_dir / "ai_era_agent_minute.lock").open("w", encoding="utf-8") as lock_file:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("AI-era brain update skipped: previous run still active")
            return 0
        memory = MemoryStore(config.resolved_data_dir)
        brain = BrainServer(config, memory)
        report = run_ai_era_requirements_agent(config, brain.status())
        print(f"AI-era brain update: {report['updated_at']} | {report['next_update']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
