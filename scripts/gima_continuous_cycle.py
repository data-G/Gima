#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parent.parent
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

from human_ai.agent import Agent
from human_ai.brain_index import rebuild_brain_csv
from human_ai.config import load_config
from human_ai.daily_summary import DailySummaryService
from human_ai.secrets import load_secret_env
from human_ai.self_update import SelfUpdateManager


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Gima's bounded learn, backup, and evaluation cycle")
    parser.add_argument("--workspace", default=str(WORKSPACE))
    parser.add_argument("--config", default=str(WORKSPACE / "config.local.json"))
    parser.add_argument("--provider", default="gemini", choices=["gemini", "chatgpt", "anthropic", "local"])
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--retention", type=int, default=14)
    parser.add_argument("--skip-learning", action="store_true")
    parser.add_argument("--skip-tests", action="store_true")
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_state_snapshot(data_dir: Path, output_dir: Path, stamp: str) -> tuple[Path, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"gima_continuity_{stamp}.zip"
    roots = [data_dir / "brain", data_dir / "csv", data_dir / "continuous"]
    files = sorted(path for root in roots if root.exists() for path in root.rglob("*") if path.is_file())
    manifest = {
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "kind": "gima_knowledge_and_continuity_snapshot",
        "private_secrets_included": False,
        "files": [
            {"path": str(path.relative_to(data_dir)), "bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in files
        ],
    }
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("snapshot_manifest.json", json.dumps(manifest, indent=2))
        for path in files:
            archive.write(path, path.relative_to(data_dir))
    return target, len(files)


def prune(directory: Path, pattern: str, keep: int) -> list[str]:
    paths = sorted(directory.glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True)
    removed = []
    for path in paths[max(1, keep):]:
        path.unlink(missing_ok=True)
        removed.append(str(path))
    return removed


def main() -> int:
    args = parse_args()
    workspace = Path(args.workspace).expanduser().resolve()
    config = load_config(args.config)
    load_secret_env(workspace)
    data_dir = config.resolved_data_dir
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    started = time.time()
    agent = Agent(config)
    learning = []
    learning_error = ""

    if not args.skip_learning:
        topic = (
            "Review Gima as a local personal AI and propose one low-risk, testable improvement. "
            "Explain it in natural language for human review; do not modify code or hide instructions."
        )
        try:
            learning = agent.daily_teacher_learning(
                minutes=10,
                providers=[args.provider],
                topic=topic,
                pause_seconds=0,
                max_rounds=max(1, args.rounds),
            )
        except Exception as error:
            learning_error = str(error)

    brain_csv = rebuild_brain_csv(
        data_dir,
        [data_dir / "brain", config.resolved_hands_dir, config.resolved_downloads_dir],
    )
    source_backup = SelfUpdateManager(workspace, data_dir).create_backup(f"continuity_{stamp}")
    state_dir = data_dir / "continuity_snapshots"
    state_snapshot, state_files = create_state_snapshot(data_dir, state_dir, stamp)
    summary = DailySummaryService(workspace, data_dir, agent.memory).generate("midnight")

    tests_passed = True
    test_output = "tests skipped"
    if not args.skip_tests:
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "tests.test_memory", "tests.test_artifacts"],
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=240,
            check=False,
        )
        tests_passed = result.returncode == 0
        test_output = (result.stdout + "\n" + result.stderr)[-6000:]

    removed_state = prune(state_dir, "gima_continuity_*.zip", args.retention)
    backup_dir = data_dir / "self_updates" / "backups"
    removed_source = prune(backup_dir, "continuity_*.tar.gz", args.retention)
    report = {
        "kind": "gima_continuous_cycle",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "elapsed_seconds": round(time.time() - started, 3),
        "provider": args.provider,
        "learning_results": len(learning),
        "learning_error": learning_error,
        "brain_csv": str(brain_csv),
        "source_backup": str(source_backup),
        "state_snapshot": str(state_snapshot),
        "state_files": state_files,
        "daily_summary": str(summary.report_path),
        "tests_passed": tests_passed,
        "test_output": test_output,
        "removed_old_state_snapshots": removed_state,
        "removed_old_source_backups": removed_source,
        "live_code_modified": False,
        "upgrade_policy": "Teacher improvements are stored for review. Code changes require isolated self-code tests and explicit parent-approved sync.",
    }
    report_dir = data_dir / "continuous" / "cycles"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"cycle_{stamp}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    agent.memory.audit("continuous_cycle", str(report_path), f"learning={len(learning)} tests={tests_passed}", "ok" if tests_passed else "error")
    print(json.dumps({key: value for key, value in report.items() if key != "test_output"}, indent=2))
    return 0 if tests_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
