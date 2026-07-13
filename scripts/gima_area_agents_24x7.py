#!/usr/bin/env python3
from __future__ import annotations

import fcntl
import sys
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parent.parent
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

from human_ai.brain import BrainServer
from human_ai.config import load_config
from human_ai.memory import MemoryStore
from human_ai.system_doctor import run_area_agent_supervisor


def main() -> int:
    config = load_config(str(WORKSPACE / "config.local.json"))
    lock_dir = config.resolved_data_dir / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    with (lock_dir / "area_agents_24x7.lock").open("w", encoding="utf-8") as lock_file:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Area agents skipped: previous run still active")
            return 0
        memory = MemoryStore(config.resolved_data_dir)
        brain = BrainServer(config, memory)
        report = run_area_agent_supervisor(config, brain.status())
        print(
            "Area agents update: "
            f"{report['updated_at']} | areas={report['area_count']} "
            f"| needs_attention={report['needs_attention_count']} | next={report['next_action']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
