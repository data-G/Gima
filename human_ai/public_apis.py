from __future__ import annotations

import json
import re
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import Config


@dataclass
class PublicApiEntry:
    name: str
    url: str
    description: str
    auth: str
    https: str
    cors: str
    category: str

    def as_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "url": self.url,
            "description": self.description,
            "auth": self.auth,
            "https": self.https,
            "cors": self.cors,
            "category": self.category,
        }


class PublicApiCatalogStore:
    """Local searchable cache for public-apis/public-apis."""

    source_url = "https://raw.githubusercontent.com/public-apis/public-apis/master/README.md"
    repo_url = "https://github.com/public-apis/public-apis"

    def __init__(self, config: Config):
        self.config = config
        self.cache_dir = config.resolved_data_dir / "public_apis"
        self.cache_path = self.cache_dir / "catalog.json"

    def search(
        self,
        *,
        query: str = "",
        category: str = "",
        auth: str = "",
        https_only: bool = False,
        no_auth_only: bool = False,
        refresh: bool = False,
        limit: int = 50,
    ) -> dict[str, Any]:
        catalog = self.refresh() if refresh or not self.cache_path.exists() else self._read_cache()
        entries = catalog.get("entries", [])
        if not isinstance(entries, list):
            entries = []
        rows = [row for row in entries if isinstance(row, dict)]
        query = query.strip().casefold()
        category = category.strip().casefold()
        auth = auth.strip().casefold()
        if category:
            rows = [row for row in rows if category in str(row.get("category", "")).casefold()]
        if auth:
            rows = [row for row in rows if auth in str(row.get("auth", "")).casefold()]
        if https_only:
            rows = [row for row in rows if str(row.get("https", "")).casefold() == "yes"]
        if no_auth_only:
            rows = [row for row in rows if str(row.get("auth", "")).casefold() == "no"]
        if query:
            rows = [row for row in rows if self._matches(row, query)]
            rows.sort(key=lambda row: self._score(row, query), reverse=True)
        else:
            rows.sort(key=lambda row: (str(row.get("category", "")), str(row.get("name", ""))))
        max_rows = max(1, min(int(limit), 200))
        return {
            "source": catalog.get("source", self.repo_url),
            "license": catalog.get("license", "MIT"),
            "cached_at": catalog.get("cached_at", ""),
            "count": len(rows),
            "returned": min(len(rows), max_rows),
            "entries": rows[:max_rows],
            "categories": catalog.get("categories", []),
            "safety": [
                "This is a discovery catalog only. Review each API's official documentation and terms before use.",
                "Gima must not send private data or API keys to newly discovered APIs without explicit user approval.",
                "Prefer HTTPS and documented authentication flows.",
            ],
        }

    def refresh(self) -> dict[str, Any]:
        request = urllib.request.Request(self.source_url, headers={"User-Agent": "Gima local assistant/0.1"})
        with urllib.request.urlopen(request, timeout=30) as response:
            readme = response.read().decode("utf-8", errors="replace")
        entries = [entry.as_dict() for entry in parse_public_apis_readme(readme)]
        categories = sorted({entry["category"] for entry in entries})
        payload = {
            "source": self.repo_url,
            "source_readme": self.source_url,
            "license": "MIT",
            "cached_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "entry_count": len(entries),
            "categories": categories,
            "entries": entries,
        }
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return payload

    def _read_cache(self) -> dict[str, Any]:
        return json.loads(self.cache_path.read_text(encoding="utf-8"))

    def _matches(self, row: dict[str, Any], query: str) -> bool:
        haystack = " ".join(
            str(row.get(key, "")) for key in ["name", "description", "category", "auth", "url"]
        ).casefold()
        return all(term in haystack for term in query.split())

    def _score(self, row: dict[str, Any], query: str) -> int:
        score = 0
        name = str(row.get("name", "")).casefold()
        description = str(row.get("description", "")).casefold()
        category = str(row.get("category", "")).casefold()
        for term in query.split():
            if term in name:
                score += 8
            if term in category:
                score += 4
            if term in description:
                score += 2
        if str(row.get("https", "")).casefold() == "yes":
            score += 1
        if str(row.get("auth", "")).casefold() == "no":
            score += 1
        return score


def parse_public_apis_readme(readme: str) -> list[PublicApiEntry]:
    entries: list[PublicApiEntry] = []
    category = ""
    in_api_table = False
    for raw_line in readme.splitlines():
        line = raw_line.strip()
        heading = re.match(r"^###\s+(.+?)\s*$", line)
        if heading:
            category = _strip_inline_markdown(heading.group(1))
            in_api_table = False
            continue
        if line.startswith("API | Description | Auth | HTTPS | CORS") or line.startswith("| API | Description | Auth | HTTPS | CORS"):
            in_api_table = True
            continue
        if not in_api_table or not category:
            continue
        if not line.startswith("|") or set(line.replace("|", "").replace(":", "").strip()) <= {"-"}:
            continue
        cells = _split_markdown_row(line)
        if len(cells) < 5:
            continue
        name, url = _extract_link(cells[0])
        if not name or not url:
            continue
        entries.append(
            PublicApiEntry(
                name=name,
                url=url,
                description=_strip_inline_markdown(cells[1]),
                auth=_strip_inline_markdown(cells[2]),
                https=_strip_inline_markdown(cells[3]),
                cors=_strip_inline_markdown(cells[4]),
                category=category,
            )
        )
    return entries


def _split_markdown_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _extract_link(value: str) -> tuple[str, str]:
    match = re.search(r"\[([^\]]+)\]\(([^)]+)\)", value)
    if not match:
        return _strip_inline_markdown(value), ""
    return _strip_inline_markdown(match.group(1)), match.group(2).strip()


def _strip_inline_markdown(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value)
    value = value.replace("`", "")
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    return " ".join(value.split())
