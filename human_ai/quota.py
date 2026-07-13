from __future__ import annotations

import csv
import time
from pathlib import Path
from typing import Mapping


QUOTA_FIELDS = ["date", "provider", "requests", "last_used_at"]


class FreeQuotaTracker:
    def __init__(self, usage_dir: Path, daily_limits: Mapping[str, int]):
        self.usage_dir = usage_dir
        self.path = usage_dir / "free_quota_usage.csv"
        self.daily_limits = {key.casefold().strip(): max(0, int(value)) for key, value in daily_limits.items()}
        self.usage_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_csv()

    def allowed(self, provider: str) -> tuple[bool, str]:
        provider = _canonical(provider)
        limit = self.daily_limits.get(provider, 0)
        if limit <= 0:
            return False, f"{provider} has no configured free quota"
        used = self.used_today(provider)
        if used >= limit:
            return False, f"{provider} free quota reached ({used}/{limit} today)"
        return True, f"{provider} free quota available ({used}/{limit} used today)"

    def record(self, provider: str) -> None:
        provider = _canonical(provider)
        today = _today()
        rows = self._rows()
        found = False
        for row in rows:
            if row["date"] == today and row["provider"] == provider:
                row["requests"] = str(int(row.get("requests") or "0") + 1)
                row["last_used_at"] = _now()
                found = True
                break
        if not found:
            rows.append({"date": today, "provider": provider, "requests": "1", "last_used_at": _now()})
        self._write_rows(rows)

    def mark_exhausted(self, provider: str) -> None:
        provider = _canonical(provider)
        limit = self.daily_limits.get(provider, 0)
        if limit <= 0:
            return
        today = _today()
        rows = [row for row in self._rows() if not (row["date"] == today and row["provider"] == provider)]
        rows.append({"date": today, "provider": provider, "requests": str(limit), "last_used_at": _now()})
        self._write_rows(rows)

    def used_today(self, provider: str) -> int:
        provider = _canonical(provider)
        today = _today()
        total = 0
        for row in self._rows():
            if row["date"] == today and row["provider"] == provider:
                total += int(row.get("requests") or "0")
        return total

    def status(self) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for provider, limit in sorted(self.daily_limits.items()):
            used = self.used_today(provider)
            rows.append(
                {
                    "provider": provider,
                    "limit": str(limit),
                    "used": str(used),
                    "remaining": str(max(0, limit - used)),
                    "available": "yes" if limit > 0 and used < limit else "no",
                }
            )
        return rows

    def _ensure_csv(self) -> None:
        if self.path.exists():
            return
        with self.path.open("w", newline="", encoding="utf-8") as handle:
            csv.DictWriter(handle, fieldnames=QUOTA_FIELDS).writeheader()

    def _rows(self) -> list[dict[str, str]]:
        self._ensure_csv()
        with self.path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    def _write_rows(self, rows: list[dict[str, str]]) -> None:
        with self.path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=QUOTA_FIELDS)
            writer.writeheader()
            writer.writerows(rows)


def _canonical(provider: str) -> str:
    key = provider.casefold().strip()
    if key in {"openai", "chatgpt"}:
        return "chatgpt"
    if key in {"google", "gemini"}:
        return "gemini"
    if key in {"claude", "anthropic"}:
        return "anthropic"
    if key in {"grok", "xai"}:
        return "xai"
    return key


def _today() -> str:
    return time.strftime("%Y-%m-%d")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")
