from __future__ import annotations

import csv
import json
import re
import time
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import Config
from .memory import MemoryStore, Record
from .services import WebImporter


HF_HOSTS = {"huggingface.co", "www.huggingface.co"}


@dataclass
class HuggingFaceLearningResult:
    repo_id: str
    repo_type: str
    source_url: str
    summary: str
    recommendations: list[str]
    files: list[dict[str, Any]]
    record_id: str
    review_id: str


def extract_huggingface_url(text: str) -> str:
    for match in re.finditer(r"https?://[^\s<>()]+", text):
        url = match.group(0).rstrip(".,;")
        parsed = urllib.parse.urlparse(url)
        if (parsed.hostname or "").casefold() in HF_HOSTS:
            return url
    return ""


def is_huggingface_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    return parsed.scheme in {"http", "https"} and (parsed.hostname or "").casefold() in HF_HOSTS


class HuggingFaceLearner:
    """Import public Hugging Face repo facts as reviewable Gima knowledge."""

    def __init__(self, config: Config, memory: MemoryStore):
        self.config = config
        self.memory = memory
        self.importer = WebImporter(config.web.allowed_domains)
        self.output_root = config.resolved_hands_out_dir / "huggingface_learning"

    def learn(self, url: str) -> HuggingFaceLearningResult:
        if not is_huggingface_url(url):
            raise ValueError("Only public huggingface.co URLs are supported")
        repo_type, repo_id = self._parse_repo(url)
        metadata_url = self._metadata_url(repo_type, repo_id)
        metadata = self._fetch_json(metadata_url)
        card_url = f"https://huggingface.co/{repo_id}/raw/main/README.md"
        card_text = self._fetch_optional_text(card_url)
        summary = self._summary(repo_type, repo_id, metadata, card_text)
        recommendations = self._recommendations(repo_type, repo_id, metadata, card_text)

        project = self.output_root / f"{time.strftime('%Y%m%d_%H%M%S')}_{_slug(repo_id)}"
        project.mkdir(parents=True, exist_ok=True)
        metadata_path = project / "huggingface_metadata.json"
        csv_path = project / "huggingface_analysis.csv"
        md_path = project / "huggingface_learning_report.md"
        metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
        _write_csv(
            csv_path,
            [
                {
                    "repo_id": repo_id,
                    "repo_type": repo_type,
                    "source_url": url,
                    "metadata_url": metadata_url,
                    "license": _as_text(metadata.get("license") or (metadata.get("cardData") or {}).get("license")),
                    "pipeline_tag": _as_text(metadata.get("pipeline_tag")),
                    "library_name": _as_text(metadata.get("library_name")),
                    "tags": ", ".join(_string_list(metadata.get("tags"))[:24]),
                    "siblings_count": str(len(metadata.get("siblings") or [])),
                    "recommendations": " | ".join(recommendations),
                }
            ],
        )
        md_path.write_text(
            "\n".join(
                [
                    f"# Hugging Face Learning Report: {repo_id}",
                    "",
                    f"Source: {url}",
                    f"Metadata: {metadata_url}",
                    f"Type: {repo_type}",
                    "",
                    "## Summary",
                    "",
                    summary,
                    "",
                    "## Useful Improvements For Gima",
                    "",
                    *[f"- {item}" for item in recommendations],
                    "",
                    "## Safety Boundary",
                    "",
                    "- Imported only public metadata and model/card text.",
                    "- Did not copy private data, hidden prompts, restricted datasets, or credentials.",
                    "- Recommendations are saved for review before code/model changes.",
                    "",
                    "## Card Excerpt",
                    "",
                    _trim(card_text, 5000) or "No README/model card text was available from the public raw URL.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        content = "\n\n".join(
            [
                summary,
                "Useful improvements for Gima:",
                "\n".join(f"- {item}" for item in recommendations),
                f"Metadata stored at: {metadata_path}",
                f"Report stored at: {md_path}",
            ]
        )
        record_id = self.memory.add(
            Record(
                category="research",
                subcategory="huggingface",
                kind="huggingface_repo_learning",
                title=f"Hugging Face learning: {repo_id}",
                content=content[:100000],
                keywords=f"huggingface model space repo {repo_id} local ai gima improvement",
                source=url,
                media_path=str(md_path),
                confidence="0.70",
                status="review",
            )
        )
        review_id = self.memory.add_source_review(
            record_id,
            f"Hugging Face source: {repo_id}",
            url,
            "research",
            "huggingface",
            summary,
            internet_status="public_metadata_imported",
        )
        self.memory.audit("huggingface_learn", repo_id, f"Stored as {record_id}; report={md_path}", "ok")
        return HuggingFaceLearningResult(
            repo_id=repo_id,
            repo_type=repo_type,
            source_url=url,
            summary=summary,
            recommendations=recommendations,
            files=[_file_info(metadata_path), _file_info(csv_path), _file_info(md_path)],
            record_id=record_id,
            review_id=review_id,
        )

    def _parse_repo(self, url: str) -> tuple[str, str]:
        parsed = urllib.parse.urlparse(url)
        parts = [part for part in parsed.path.split("/") if part]
        if not parts:
            raise ValueError("Hugging Face URL does not include a repository id")
        if parts[0] == "spaces":
            if len(parts) < 3:
                raise ValueError("Hugging Face Space URL must look like /spaces/owner/name")
            return "space", f"{parts[1]}/{parts[2]}"
        if parts[0] in {"datasets", "models"}:
            if len(parts) < 3:
                raise ValueError("Hugging Face repo URL must include owner/name")
            return "dataset" if parts[0] == "datasets" else "model", f"{parts[1]}/{parts[2]}"
        if len(parts) == 1:
            return "model", parts[0]
        return "model", f"{parts[0]}/{parts[1]}"

    def _metadata_url(self, repo_type: str, repo_id: str) -> str:
        if repo_type == "space":
            return f"https://huggingface.co/api/spaces/{repo_id}"
        if repo_type == "dataset":
            return f"https://huggingface.co/api/datasets/{repo_id}"
        return f"https://huggingface.co/api/models/{repo_id}"

    def _fetch_json(self, url: str) -> dict[str, Any]:
        text = self.importer.fetch(url)
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as error:
            raise RuntimeError(f"Hugging Face metadata did not return JSON: {error}") from error
        if not isinstance(payload, dict):
            raise RuntimeError("Hugging Face metadata response was not an object")
        return payload

    def _fetch_optional_text(self, url: str) -> str:
        try:
            return self.importer.fetch(url)
        except Exception as error:
            self.memory.audit("huggingface_card_fetch", url, str(error), "warning")
            return ""

    def _summary(self, repo_type: str, repo_id: str, metadata: dict[str, Any], card_text: str) -> str:
        tags = ", ".join(_string_list(metadata.get("tags"))[:10]) or "no public tags listed"
        pipeline = _as_text(metadata.get("pipeline_tag")) or "not specified"
        library = _as_text(metadata.get("library_name")) or "not specified"
        license_name = _as_text(metadata.get("license") or (metadata.get("cardData") or {}).get("license")) or "not specified"
        siblings = metadata.get("siblings") or []
        return (
            f"{repo_id} is a public Hugging Face {repo_type}. "
            f"Pipeline/task: {pipeline}. Library: {library}. License: {license_name}. "
            f"Public tags: {tags}. Files listed: {len(siblings)}. "
            f"Model/card text imported: {'yes' if card_text else 'no'}."
        )

    def _recommendations(self, repo_type: str, repo_id: str, metadata: dict[str, Any], card_text: str) -> list[str]:
        recommendations: list[str] = []
        tags = {tag.casefold() for tag in _string_list(metadata.get("tags"))}
        siblings = [str((row or {}).get("rfilename", "")) for row in (metadata.get("siblings") or []) if isinstance(row, dict)]
        all_text = " ".join([repo_id, " ".join(tags), " ".join(siblings), card_text[:8000]]).casefold()
        if any(name.endswith(".gguf") for name in siblings) or "gguf" in tags or "gguf" in all_text:
            recommendations.append("Add this repo to Gima's local model candidate list and prefer quantized GGUF files that fit available RAM.")
        if "vision" in tags or "image" in tags or "multimodal" in all_text:
            recommendations.append("Mark as a possible vision/multimodal teacher candidate, but test screenshot understanding before enabling it in routing.")
        if "text-generation" in tags or "conversational" in tags or "chat" in all_text:
            recommendations.append("Evaluate on Gima conversation, memory, and coding prompts before using it as a chat fallback.")
        if "spaces" in repo_type or repo_type == "space" or "gradio" in all_text:
            recommendations.append("If this is a Space/API demo, integrate only through documented public endpoints with explicit consent and quota controls.")
        if "license" not in metadata and not (metadata.get("cardData") or {}).get("license"):
            recommendations.append("Do not use commercially until the license is verified from the model card or repository files.")
        if "eval" in all_text or "benchmark" in all_text:
            recommendations.append("Extract benchmark claims into Gima's evaluation backlog and verify them with local tests.")
        if not recommendations:
            recommendations.append("Save as public research memory first; decide later whether it improves model routing, media tools, or documentation.")
        recommendations.append("Keep this learning as reviewable notes; do not silently replace Gima's active model or code.")
        return recommendations


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else ["empty"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _as_text(value).replace("\x00", "") for key, value in row.items()})


def _file_info(path: Path) -> dict[str, Any]:
    return {
        "name": path.name,
        "path": str(path),
        "size": path.stat().st_size,
        "download_url": f"/api/download?path={urllib.parse.quote(str(path))}",
    }


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str):
        return [value]
    return []


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _trim(text: str, limit: int) -> str:
    clean = re.sub(r"\x00", "", text or "").strip()
    return clean[:limit] + ("..." if len(clean) > limit else "")


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")[:80] or "repo"
