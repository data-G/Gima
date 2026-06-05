from __future__ import annotations

import csv
import os
import platform
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List

from .config import Config
from .memory import now_iso
from .services import dependency_report


SCALE_REPORT_FIELDS = [
    "timestamp",
    "platform",
    "machine",
    "processor",
    "model_path",
    "model_size_mb",
    "data_size_mb",
    "free_disk_gb",
    "knowledge_rows",
    "conversation_rows",
    "eval_results",
    "missing_tools",
    "recommendation",
]


@dataclass(frozen=True)
class ScaleReport:
    path: Path
    recommendation: str
    data_size_mb: float
    free_disk_gb: float
    knowledge_rows: int
    conversation_rows: int
    eval_results: int


class ScaleReporter:
    def __init__(self, config: Config):
        self.config = config
        self.root = config.resolved_data_dir / "scale"
        self.report_path = self.root / "scale_reports.csv"

    def initialize(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        if not self.report_path.exists():
            with self.report_path.open("w", newline="", encoding="utf-8") as handle:
                csv.DictWriter(handle, fieldnames=SCALE_REPORT_FIELDS).writeheader()

    def collect(self) -> ScaleReport:
        self.initialize()
        data_size_mb = round(_dir_size(self.config.resolved_data_dir) / 1_000_000, 2)
        usage = shutil.disk_usage(self.config.resolved_workspace)
        free_disk_gb = round(usage.free / 1_000_000_000, 2)
        knowledge_rows = _count_csv_rows(self.config.resolved_data_dir / "csv" / "knowledge.csv")
        conversation_rows = _count_csv_rows(self.config.resolved_data_dir / "csv" / "conversations.csv")
        eval_results = _count_csv_rows(self.config.resolved_data_dir / "evals" / "results.csv")
        model_path = Path(self.config.model.model_path).expanduser()
        model_size_mb = round(model_path.stat().st_size / 1_000_000, 2) if model_path.exists() else 0.0
        missing_tools = [name for name, ok in dependency_report().items() if not ok]
        recommendation = _recommendation(
            model_size_mb=model_size_mb,
            data_size_mb=data_size_mb,
            free_disk_gb=free_disk_gb,
            eval_results=eval_results,
            missing_tools=missing_tools,
        )
        row = {
            "timestamp": now_iso(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "model_path": str(model_path),
            "model_size_mb": f"{model_size_mb:.2f}",
            "data_size_mb": f"{data_size_mb:.2f}",
            "free_disk_gb": f"{free_disk_gb:.2f}",
            "knowledge_rows": str(knowledge_rows),
            "conversation_rows": str(conversation_rows),
            "eval_results": str(eval_results),
            "missing_tools": ", ".join(missing_tools),
            "recommendation": recommendation,
        }
        with self.report_path.open("a", newline="", encoding="utf-8") as handle:
            csv.DictWriter(handle, fieldnames=SCALE_REPORT_FIELDS).writerow(row)
        return ScaleReport(
            self.report_path,
            recommendation,
            data_size_mb,
            free_disk_gb,
            knowledge_rows,
            conversation_rows,
            eval_results,
        )


def _dir_size(path: Path) -> int:
    total = 0
    if not path.exists():
        return total
    for root, _, files in os.walk(path):
        for name in files:
            try:
                total += (Path(root) / name).stat().st_size
            except OSError:
                pass
    return total


def _count_csv_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(newline="", encoding="utf-8") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def _recommendation(
    model_size_mb: float,
    data_size_mb: float,
    free_disk_gb: float,
    eval_results: int,
    missing_tools: List[str],
) -> str:
    if missing_tools:
        return "Install missing optional tools before chasing larger models."
    if eval_results == 0:
        return "Run eval-run before scaling so improvements have a baseline."
    if free_disk_gb < 20:
        return "Free disk space before adding larger models or video datasets."
    if model_size_mb and model_size_mb < 2_000:
        return "Current model is small; next scale step is benchmarking a larger GGUF model that this Mac can run."
    if data_size_mb > 5_000:
        return "Data is growing; next scale step is retrieval pruning and category-specific indexes."
    return "Scale baseline looks healthy; next step is latency benchmarking and stronger retrieval ranking."
