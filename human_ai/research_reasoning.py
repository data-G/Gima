from __future__ import annotations

import csv
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


RESEARCH_METHOD_REFERENCES = [
    {
        "paper": "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
        "url": "https://arxiv.org/abs/2005.11401",
        "applied_as": "Use explicit non-parametric memory with provenance instead of relying only on model parameters.",
    },
    {
        "paper": "Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection",
        "url": "https://arxiv.org/abs/2310.11511",
        "applied_as": "Retrieve adaptively, score passage relevance, and add a self-check about evidence and gaps.",
    },
    {
        "paper": "ReAct: Synergizing Reasoning and Acting in Language Models",
        "url": "https://arxiv.org/abs/2210.03629",
        "applied_as": "Record an inspectable reasoning/action trace for retrieval and answer construction.",
    },
    {
        "paper": "Reflexion: Language Agents with Verbal Reinforcement Learning",
        "url": "https://arxiv.org/abs/2303.11366",
        "applied_as": "Save reflective notes about weak evidence so future answers can improve without model fine-tuning.",
    },
]

TRACE_FIELDS = [
    "timestamp",
    "trace_id",
    "question",
    "retrieve_decision",
    "expanded_query",
    "selected_record_ids",
    "self_check",
    "method_refs",
]


@dataclass
class ResearchAnswer:
    text: str
    selected: list[dict[str, str]]
    self_check: str
    trace_id: str


class ResearchReasoner:
    """Paper-inspired local reasoning over Gima's CSV memory.

    This is not model training. It applies RAG/Self-RAG/ReAct/Reflexion ideas as a
    deterministic controller around Gima's existing CSV memory.
    """

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.trace_path = data_dir / "csv" / "research_traces.csv"
        self.methods_dir = data_dir / "brain" / "research_methods"
        self.methods_path = self.methods_dir / "advanced_rag_methods.md"
        self._ensure_files()

    def answer_from_memory(self, question: str, rows: list[dict[str, str]], limit: int = 5) -> ResearchAnswer | None:
        if not rows:
            return None
        expanded_terms = expand_query_terms(question)
        ranked = self.rerank(question, rows, expanded_terms)[: max(1, limit)]
        if not ranked:
            return None
        selected = [row for _, row in ranked]
        evidence_lines = []
        for index, row in enumerate(selected, start=1):
            title = row.get("title", "Untitled")
            content = _best_excerpt(question, row.get("content", ""), expanded_terms)
            evidence_lines.append(f"{index}. {title}: {content}")
        sources = []
        for index, row in enumerate(selected, start=1):
            source = row.get("source") or row.get("media_path") or "Gima memory CSV"
            sources.append(f"[{index}] {source}")
        self_check = self._self_check(question, selected, expanded_terms)
        trace_id = self._record_trace(question, expanded_terms, selected, self_check)
        text = "\n".join(
            [
                "Research-backed answer from Gima memory.",
                "",
                "What I found:",
                *evidence_lines,
                "",
                "Sources:",
                *sources,
                "",
                "Self-check:",
                self_check,
                "",
                f"Trace: {trace_id}",
            ]
        )
        return ResearchAnswer(text=text, selected=selected, self_check=self_check, trace_id=trace_id)

    def rerank(
        self,
        question: str,
        rows: list[dict[str, str]],
        expanded_terms: list[str] | None = None,
    ) -> list[tuple[float, dict[str, str]]]:
        terms = expanded_terms or expand_query_terms(question)
        scored: list[tuple[float, dict[str, str]]] = []
        for row in rows:
            text = " ".join([row.get("title", ""), row.get("keywords", ""), row.get("content", "")]).casefold()
            score = 0.0
            for term in terms:
                if term in text:
                    score += 1.0
                if re.search(rf"\b{re.escape(term)}\b", text):
                    score += 0.5
            if row.get("source"):
                score += 0.25
            if row.get("status") == "active":
                score += 0.25
            if row.get("confidence"):
                try:
                    score += min(1.0, max(0.0, float(row["confidence"]))) * 0.25
                except ValueError:
                    pass
            if score > 0:
                scored.append((score, row))
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored

    def _self_check(self, question: str, selected: list[dict[str, str]], expanded_terms: list[str]) -> str:
        covered_terms = set()
        combined = " ".join(row.get("content", "") for row in selected).casefold()
        for term in expanded_terms:
            if term in combined:
                covered_terms.add(term)
        coverage = len(covered_terms) / max(1, len(set(expanded_terms)))
        if len(selected) >= 3 and coverage >= 0.45:
            quality = "good"
        elif selected:
            quality = "partial"
        else:
            quality = "weak"
        gap = "Verify with internet/teacher models if the question needs current facts." if quality != "good" else "Evidence is local-memory based; still verify high-stakes facts."
        return f"evidence_quality={quality}; passages={len(selected)}; query_term_coverage={coverage:.2f}; {gap}"

    def _record_trace(
        self,
        question: str,
        expanded_terms: list[str],
        selected: list[dict[str, str]],
        self_check: str,
    ) -> str:
        trace_id = f"trace_{uuid.uuid4().hex}"
        self.trace_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.trace_path.exists():
            with self.trace_path.open("w", newline="", encoding="utf-8") as handle:
                csv.DictWriter(handle, fieldnames=TRACE_FIELDS).writeheader()
        with self.trace_path.open("a", newline="", encoding="utf-8") as handle:
            csv.DictWriter(handle, fieldnames=TRACE_FIELDS).writerow(
                {
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "trace_id": trace_id,
                    "question": question,
                    "retrieve_decision": "retrieve_from_csv_memory",
                    "expanded_query": " ".join(expanded_terms),
                    "selected_record_ids": ",".join(row.get("id", "") for row in selected),
                    "self_check": self_check,
                    "method_refs": "; ".join(item["paper"] for item in RESEARCH_METHOD_REFERENCES),
                }
            )
        return trace_id

    def _ensure_files(self) -> None:
        self.methods_dir.mkdir(parents=True, exist_ok=True)
        if not self.methods_path.exists():
            self.methods_path.write_text(_methods_markdown(), encoding="utf-8")
        self.trace_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.trace_path.exists():
            with self.trace_path.open("w", newline="", encoding="utf-8") as handle:
                csv.DictWriter(handle, fieldnames=TRACE_FIELDS).writeheader()


def expand_query_terms(question: str) -> list[str]:
    base_terms = [term for term in re.findall(r"[a-zA-Z0-9][a-zA-Z0-9_-]{2,}", question.casefold()) if term not in STOPWORDS]
    expansions = {
        "rag": ["retrieval", "augmented", "generation", "provenance", "memory"],
        "retrieve": ["retrieval", "search", "memory", "source"],
        "retrieval": ["rag", "source", "memory", "provenance"],
        "reason": ["reasoning", "plan", "trace", "react"],
        "reasoning": ["reason", "plan", "trace", "react"],
        "reflect": ["reflection", "critique", "self-check", "reflexion"],
        "reflection": ["reflect", "critique", "self-check", "reflexion"],
        "agent": ["action", "tool", "plan", "react"],
        "ai": ["model", "assistant", "agent"],
        "model": ["llm", "assistant", "ai"],
    }
    terms: list[str] = []
    for term in base_terms:
        if term not in terms:
            terms.append(term)
        for extra in expansions.get(term, []):
            if extra not in terms:
                terms.append(extra)
    return terms[:24]


def _best_excerpt(question: str, content: str, terms: list[str], max_chars: int = 360) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", " ".join(content.split()))
    scored: list[tuple[int, int, str]] = []
    for index, sentence in enumerate(sentences):
        lowered = sentence.casefold()
        score = sum(1 for term in terms if term in lowered)
        if score:
            scored.append((score, -index, sentence))
    if scored:
        excerpt = sorted(scored, reverse=True)[0][2]
    else:
        excerpt = content.strip().replace("\n", " ")
    if len(excerpt) > max_chars:
        excerpt = excerpt[: max_chars - 3].rstrip() + "..."
    return excerpt or "[empty memory row]"


def _methods_markdown() -> str:
    lines = [
        "# Advanced AI Research Methods Applied To Gima",
        "",
        "These are implementation notes for local, CSV-based Gima. They summarize how research ideas are applied without claiming full model training.",
        "",
    ]
    for item in RESEARCH_METHOD_REFERENCES:
        lines.extend(
            [
                f"## {item['paper']}",
                f"Source: {item['url']}",
                f"Applied in Gima: {item['applied_as']}",
                "",
            ]
        )
    return "\n".join(lines)


STOPWORDS = {
    "about",
    "again",
    "answer",
    "asked",
    "because",
    "could",
    "from",
    "give",
    "gima",
    "have",
    "into",
    "make",
    "need",
    "please",
    "question",
    "should",
    "that",
    "the",
    "them",
    "then",
    "this",
    "what",
    "when",
    "with",
    "would",
}
