from __future__ import annotations

import html
import base64
import csv
import hashlib
import hmac
import importlib
import mimetypes
import ipaddress
import json
import math
import os
import re
import shutil
import socket
import subprocess
import sys
import wave
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from array import array
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .config import Config
from .memory import MemoryStore
from .permissions import PermissionManager


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: List[str] = []
        self.ignored = 0

    def handle_starttag(self, tag: str, attrs: List[tuple]) -> None:
        if tag in {"script", "style", "noscript"}:
            self.ignored += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self.ignored:
            self.ignored -= 1

    def handle_data(self, data: str) -> None:
        if not self.ignored and data.strip():
            self.parts.append(data.strip())


class _SearchResultExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[tuple]) -> None:
        if tag != "a":
            return
        values = dict(attrs)
        href = values.get("href", "")
        css_class = values.get("class", "")
        if href and ("result__a" in css_class or "uddg=" in href):
            self.links.append(href)


def _is_public_host(hostname: str) -> bool:
    try:
        addresses = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return False
    return bool(addresses)


def cloud_allowed() -> bool:
    return os.environ.get("CLOUD_ALLOWED", "").strip().casefold() in {"1", "true", "yes", "on"}


def require_cloud_allowed(action: str = "cloud AI request") -> None:
    if not cloud_allowed():
        raise PermissionError(
            f"{action} is blocked because CLOUD_ALLOWED is not true. "
            "Set CLOUD_ALLOWED=true only when you intentionally allow Gima to send this request to cloud APIs."
        )


def _http_header_value(value: str) -> str:
    return str(value).encode("latin-1", errors="ignore").decode("latin-1")


class WebImporter:
    def __init__(self, allowed_domains: Iterable[str]):
        self.allowed_domains = {domain.lower().lstrip(".") for domain in allowed_domains}

    def fetch(self, url: str) -> str:
        parsed = urllib.parse.urlparse(url)
        hostname = (parsed.hostname or "").lower()
        if parsed.scheme not in {"http", "https"} or not hostname:
            raise ValueError("Only public http(s) URLs are supported")
        if self.allowed_domains and not any(
            hostname == domain or hostname.endswith(f".{domain}") for domain in self.allowed_domains
        ):
            raise PermissionError(f"Domain is not approved: {hostname}")
        if not _is_public_host(hostname):
            raise PermissionError("Private, local, and reserved network addresses are blocked")
        request = urllib.request.Request(url, headers={"User-Agent": "human-ai-local/0.1"})
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read(2_000_000)
            content_type = response.headers.get_content_type()
        text = raw.decode("utf-8", errors="replace")
        if content_type == "text/html":
            parser = _TextExtractor()
            parser.feed(text)
            text = "\n".join(parser.parts)
        return html.unescape(text).strip()

    def search(self, query: str, limit: int = 5) -> List[str]:
        urls = self._duckduckgo_search(query, limit)
        if not urls:
            urls = self._wikipedia_search(query, limit)
        return urls[:limit]

    def _duckduckgo_search(self, query: str, limit: int) -> List[str]:
        for endpoint in ("https://duckduckgo.com/html/?", "https://lite.duckduckgo.com/lite/?"):
            urls = self._duckduckgo_endpoint_search(endpoint, query, limit)
            if urls:
                return urls
        return []

    def _duckduckgo_endpoint_search(self, endpoint: str, query: str, limit: int) -> List[str]:
        encoded = urllib.parse.urlencode({"q": query})
        url = f"{endpoint}{encoded}"
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 human-ai-local/0.1"})
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                raw = response.read(1_000_000)
        except Exception:
            return []
        text = raw.decode("utf-8", errors="replace")
        if "anomaly-modal" in text or "Unfortunately, bots use DuckDuckGo too" in text:
            return []
        parser = _SearchResultExtractor()
        parser.feed(text)
        urls: List[str] = []
        for href in parser.links:
            parsed = urllib.parse.urlparse(html.unescape(href))
            if parsed.path == "/l/":
                target = urllib.parse.parse_qs(parsed.query).get("uddg", [""])[0]
            else:
                target = urllib.parse.urljoin(url, href)
            target = target.strip()
            if target.startswith(("http://", "https://")) and target not in urls:
                urls.append(target)
            if len(urls) >= limit:
                break
        return urls

    def _wikipedia_search(self, query: str, limit: int) -> List[str]:
        params = urllib.parse.urlencode(
            {
                "action": "opensearch",
                "search": query,
                "limit": str(limit),
                "namespace": "0",
                "format": "json",
            }
        )
        url = f"https://en.wikipedia.org/w/api.php?{params}"
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "human-ai-local/0.1 (local personal assistant)"},
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                body = json.loads(response.read().decode("utf-8"))
        except Exception:
            return []
        if not isinstance(body, list) or len(body) < 4:
            return []
        return [url for url in body[3] if isinstance(url, str) and url.startswith("https://")]


class OpenRouterCatalog:
    endpoint = "https://openrouter.ai/api/v1/models"
    default_routing = {
        "routing_sort": "latency",
        "data_collection": "deny",
        "fallback_models": ["openrouter/auto", "openrouter/free"],
        "auxiliary_models": {
            "title": "openrouter/auto",
            "vision": "openrouter/auto",
            "compression": "openrouter/auto",
            "web_summary": "openrouter/auto",
        },
        "pareto_min_coding_score": 0.65,
        "human_in_loop": True,
    }

    def __init__(self, config: Config):
        self.config = config
        self.cache_dir = config.resolved_data_dir / "openrouter"
        self.cache_path = self.cache_dir / "models_catalog.json"
        self.selected_path = self.cache_dir / "selected_model.txt"
        self.routing_path = self.cache_dir / "routing_config.json"

    def models(
        self,
        *,
        refresh: bool = False,
        output_modalities: str = "all",
        limit: int = 500,
        query: str = "",
    ) -> dict:
        payload: dict[str, Any]
        source = "cache"
        if refresh or not self.cache_path.exists():
            try:
                payload = self._fetch(output_modalities=output_modalities)
                source = "openrouter"
            except Exception:
                if not self.cache_path.exists():
                    raise
                payload = self._read_cache()
                source = "cache_after_fetch_error"
        else:
            payload = self._read_cache()

        rows = [self._normalize_model(row) for row in payload.get("data", []) if isinstance(row, dict)]
        if query.strip():
            needle = query.casefold().strip()
            rows = [
                row
                for row in rows
                if needle in row["id"].casefold()
                or needle in row["name"].casefold()
                or needle in row["provider"].casefold()
                or needle in " ".join(row["output_modalities"]).casefold()
            ]
        rows.sort(key=lambda row: (not row["free"], row["provider"], row["id"]))
        selected = self.selected_model()
        return {
            "source": source,
            "cached": source.startswith("cache"),
            "cache_path": str(self.cache_path),
            "selected_model": selected,
            "count": len(rows),
            "returned": min(max(0, limit), len(rows)),
            "models": rows[: max(0, limit)],
        }

    def select_model(self, model_id: str) -> str:
        model_id = model_id.strip()
        if not model_id or "/" not in model_id:
            raise ValueError("OpenRouter model id is required, for example openai/gpt-4o")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.selected_path.write_text(model_id, encoding="utf-8")
        return model_id

    def routing_config(self) -> dict:
        config = json.loads(json.dumps(self.default_routing))
        if self.routing_path.exists():
            try:
                saved = json.loads(self.routing_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                saved = {}
            if isinstance(saved, dict):
                for key, value in saved.items():
                    if key == "auxiliary_models" and isinstance(value, dict):
                        config[key].update({str(k): str(v).strip() for k, v in value.items() if str(v).strip()})
                    elif key == "fallback_models" and isinstance(value, list):
                        config[key] = [str(item).strip() for item in value if str(item).strip()]
                    elif key in config:
                        config[key] = value
        config["selected_model"] = self.selected_model()
        config["routing_path"] = str(self.routing_path)
        return config

    def save_routing_config(self, payload: dict) -> dict:
        current = self.routing_config()
        sort = str(payload.get("routing_sort", current["routing_sort"])).strip().casefold()
        if sort not in {"price", "throughput", "latency"}:
            raise ValueError("routing_sort must be price, throughput, or latency")
        data_collection = str(payload.get("data_collection", current["data_collection"])).strip().casefold()
        if data_collection not in {"deny", "allow"}:
            raise ValueError("data_collection must be deny or allow")
        fallbacks = payload.get("fallback_models", current["fallback_models"])
        if isinstance(fallbacks, str):
            fallbacks = [item.strip() for item in re.split(r"[\n,]+", fallbacks) if item.strip()]
        if not isinstance(fallbacks, list):
            raise ValueError("fallback_models must be a list or comma-separated string")
        auxiliary = payload.get("auxiliary_models", current["auxiliary_models"])
        if not isinstance(auxiliary, dict):
            raise ValueError("auxiliary_models must be an object")
        saved = {
            "routing_sort": sort,
            "data_collection": data_collection,
            "fallback_models": [str(item).strip() for item in fallbacks if str(item).strip()],
            "auxiliary_models": {str(k): str(v).strip() for k, v in auxiliary.items() if str(v).strip()},
            "pareto_min_coding_score": float(payload.get("pareto_min_coding_score", current["pareto_min_coding_score"])),
            "human_in_loop": payload.get("human_in_loop", current["human_in_loop"]) is not False,
        }
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.routing_path.write_text(json.dumps(saved, indent=2, sort_keys=True), encoding="utf-8")
        saved["selected_model"] = self.selected_model()
        saved["routing_path"] = str(self.routing_path)
        return saved

    def selected_model(self) -> str:
        env_model = os.environ.get("GIMA_OPENROUTER_MODEL", "").strip()
        if env_model:
            return env_model
        if self.selected_path.exists():
            return self.selected_path.read_text(encoding="utf-8", errors="replace").strip()
        return ""

    def _fetch(self, *, output_modalities: str) -> dict:
        params = urllib.parse.urlencode({"output_modalities": output_modalities or "all"})
        headers = {
            "Accept": "application/json",
            "User-Agent": "Gima local assistant/0.1",
        }
        api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        request = urllib.request.Request(f"{self.endpoint}?{params}", headers=headers)
        with urllib.request.urlopen(request, timeout=25) as response:
            payload = json.loads(response.read().decode("utf-8"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return payload

    def _read_cache(self) -> dict:
        return json.loads(self.cache_path.read_text(encoding="utf-8"))

    def _normalize_model(self, row: dict) -> dict:
        model_id = str(row.get("id") or row.get("canonical_slug") or "").strip()
        pricing = row.get("pricing") if isinstance(row.get("pricing"), dict) else {}
        architecture = row.get("architecture") if isinstance(row.get("architecture"), dict) else {}
        top_provider = row.get("top_provider") if isinstance(row.get("top_provider"), dict) else {}
        input_modalities = self._string_list(
            row.get("input_modalities") or architecture.get("input_modalities") or []
        )
        output_modalities = self._string_list(
            row.get("output_modalities") or architecture.get("output_modalities") or []
        )
        supported_parameters = self._string_list(row.get("supported_parameters") or [])
        prompt_price = str(pricing.get("prompt", ""))
        completion_price = str(pricing.get("completion", ""))
        return {
            "id": model_id,
            "name": str(row.get("name") or model_id),
            "provider": model_id.split("/", 1)[0] if "/" in model_id else "",
            "canonical_slug": str(row.get("canonical_slug") or model_id),
            "context_length": row.get("context_length") or top_provider.get("context_length") or 0,
            "modality": str(row.get("modality") or ""),
            "input_modalities": input_modalities,
            "output_modalities": output_modalities,
            "supported_parameters": supported_parameters,
            "pricing_prompt": prompt_price,
            "pricing_completion": completion_price,
            "pricing_image": str(pricing.get("image", "")),
            "pricing_request": str(pricing.get("request", "")),
            "created": row.get("created"),
            "free": model_id.endswith(":free") or self._looks_free(prompt_price, completion_price),
        }

    def _looks_free(self, *prices: str) -> bool:
        values = [price for price in prices if price not in {"", "None", None}]
        if not values:
            return False
        try:
            return all(float(price) == 0 for price in values)
        except ValueError:
            return False

    def _string_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if item is not None]


class LocalModel:
    def __init__(self, config: Config):
        self.config = config.model

    @staticmethod
    def _clean_llama_channel_content(content: str) -> str:
        text = content.strip()
        if "<|channel>" not in text and "<channel|>" not in text:
            return text

        final_marker = "<|channel>final"
        if final_marker in text:
            text = text.rsplit(final_marker, 1)[-1]
        elif "<channel|>" in text:
            text = text.rsplit("<channel|>", 1)[-1]

        text = re.sub(r"<\\|channel\\>\\w+\\s*", "", text)
        text = text.replace("<channel|>", "")
        return text.strip()

    def complete(
        self,
        messages: List[Dict[str, str]],
        *,
        timeout_seconds: int | None = None,
        max_tokens: int | None = None,
    ) -> str:
        if not self.config.enabled:
            raise RuntimeError("Local model is disabled in the configuration")
        payload = json.dumps(
            {
                "model": self.config.model,
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": max_tokens if max_tokens is not None else self.config.max_tokens,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.config.base_url.rstrip('/')}/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        timeout = timeout_seconds if timeout_seconds is not None else self.config.timeout_seconds
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
        content = body["choices"][0]["message"].get("content", "")
        if not isinstance(content, str):
            return ""
        return self._clean_llama_channel_content(content)


class TeacherModelClient:
    def __init__(self, config: Config):
        self.root_config = config
        self.config = config.teacher_models

    def available(self, provider: str) -> bool:
        provider = provider.casefold().strip()
        if provider in {"chatgpt", "openai"}:
            return bool(os.environ.get("OPENAI_API_KEY", ""))
        if provider == "gemini":
            return bool(os.environ.get("GEMINI_API_KEY", ""))
        if provider in {"anthropic", "claude"}:
            return bool(os.environ.get("ANTHROPIC_API_KEY", ""))
        if provider in {"xai", "grok"}:
            return bool(os.environ.get("XAI_API_KEY", ""))
        if provider == "deepseek":
            return bool(os.environ.get("DEEPSEEK_API_KEY", ""))
        if provider == "openrouter":
            return bool(os.environ.get("OPENROUTER_API_KEY", ""))
        return False

    def ask(self, provider: str, prompt: str) -> str:
        provider = provider.casefold().strip()
        if provider not in {"chatgpt", "openai", "gemini", "anthropic", "claude", "xai", "grok", "deepseek", "openrouter"}:
            raise ValueError("Provider must be local, chatgpt, openai, gemini, anthropic, xai, deepseek, or openrouter")
        require_cloud_allowed(f"{provider} teacher model request")
        if provider in {"chatgpt", "openai"}:
            return self._ask_openai(prompt)
        if provider == "gemini":
            return self._ask_gemini(prompt)
        if provider in {"anthropic", "claude"}:
            return self._ask_anthropic(prompt)
        if provider in {"xai", "grok"}:
            return self._ask_openai_compatible(
                "https://api.x.ai/v1/chat/completions",
                os.environ.get("XAI_API_KEY", ""),
                self.config.xai_model,
                prompt,
            )
        if provider == "deepseek":
            return self._ask_openai_compatible(
                "https://api.deepseek.com/chat/completions",
                os.environ.get("DEEPSEEK_API_KEY", ""),
                self.config.deepseek_model,
                prompt,
            )
        if provider == "openrouter":
            return self._ask_openrouter(prompt)
        raise ValueError("Provider must be local, chatgpt, openai, gemini, anthropic, xai, deepseek, or openrouter")

    def _ask_openai(self, prompt: str) -> str:
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        models = self._openai_model_candidates()
        failures: List[str] = []
        body: dict | None = None
        used_model = ""
        for model in models:
            payload = json.dumps(
                {
                    "model": model,
                    "input": prompt,
                    "max_output_tokens": 600,
                }
            ).encode("utf-8")
            request = urllib.request.Request(
                "https://api.openai.com/v1/responses",
                data=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=min(60, self.config.timeout_seconds)) as response:
                    body = json.loads(response.read().decode("utf-8"))
                used_model = model
                break
            except urllib.error.HTTPError as error:
                detail = error.read().decode("utf-8", errors="replace")[:500]
                failures.append(f"{model}: HTTP {error.code} {detail}")
                if error.code == 429 and "insufficient_quota" in detail:
                    break
                if error.code not in {400, 403, 404, 429}:
                    break
            except Exception as error:
                failures.append(f"{model}: {error}")
                break
        if body is None:
            raise RuntimeError("OpenAI did not answer. " + "; ".join(failures))
        if used_model != self.config.openai_model:
            body["_gima_used_model"] = used_model
        if body.get("output_text"):
            return self._with_model_note(body["output_text"].strip(), used_model)
        parts: List[str] = []
        for item in body.get("output", []):
            for content in item.get("content", []):
                text = content.get("text")
                if text:
                    parts.append(text)
        return self._with_model_note("\n".join(parts).strip(), used_model)

    def _openai_model_candidates(self) -> List[str]:
        configured = [part.strip() for part in self.config.openai_model.split(",") if part.strip()]
        fallbacks = ["gpt-5.5", "gpt-5.1", "gpt-5", "gpt-4.1", "gpt-4o"]
        models: List[str] = []
        for model in configured + fallbacks:
            if model not in models:
                models.append(model)
        return models

    def _with_model_note(self, text: str, used_model: str) -> str:
        if not used_model or used_model == self.config.openai_model:
            return text
        return f"{text}\n\n[OpenAI model used: {used_model}]"

    def _ask_openrouter(self, prompt: str) -> str:
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        models = self._openrouter_model_candidates()
        extra_body = self._openrouter_extra_body()
        failures: List[str] = []
        for model in models:
            try:
                answer = self._ask_openai_compatible(
                    "https://openrouter.ai/api/v1/chat/completions",
                    api_key,
                    model,
                    prompt,
                    extra_headers={
                        "HTTP-Referer": "http://127.0.0.1:8787",
                        "X-Title": "Gima local assistant",
                    },
                    extra_body=extra_body,
                )
                return answer if model == self.config.openrouter_model else f"{answer}\n\n[OpenRouter model used: {model}]"
            except urllib.error.HTTPError as error:
                detail = error.read().decode("utf-8", errors="replace")[:500]
                failures.append(f"{model}: HTTP {error.code} {detail}")
                if error.code == 401:
                    break
                if error.code not in {400, 403, 404, 429}:
                    break
            except Exception as error:
                failures.append(f"{model}: {error}")
                break
        raise RuntimeError("OpenRouter did not answer. " + "; ".join(failures))

    def _openrouter_model_candidates(self) -> List[str]:
        selected = self._selected_openrouter_model()
        configured = [part.strip() for part in self.config.openrouter_model.split(",") if part.strip()]
        routing = OpenRouterCatalog(self.root_config).routing_config()
        fallbacks = [str(item).strip() for item in routing.get("fallback_models", []) if str(item).strip()]
        fallbacks += ["openrouter/free", "openai/gpt-5.5", "openai/gpt-4o", "openai/gpt-4.1"]
        models: List[str] = []
        for model in ([selected] if selected else []) + configured + fallbacks:
            if model not in models:
                models.append(model)
        return models

    def _selected_openrouter_model(self) -> str:
        return OpenRouterCatalog(self.root_config).selected_model()

    def _openrouter_extra_body(self) -> dict:
        routing = OpenRouterCatalog(self.root_config).routing_config()
        body: dict[str, Any] = {
            "provider": {
                "sort": routing.get("routing_sort", "latency"),
                "data_collection": routing.get("data_collection", "deny"),
            }
        }
        if any(model == "openrouter/pareto-code" for model in self._openrouter_model_candidates()):
            body["plugins"] = [
                {
                    "id": "pareto-code",
                    "min_coding_score": float(routing.get("pareto_min_coding_score", 0.65)),
                }
            ]
        return body

    def _ask_gemini(self, prompt: str) -> str:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        model = urllib.parse.quote(self.config.gemini_model, safe="")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        payload = json.dumps(
            {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": 600, "temperature": 0.2},
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{url}?key={urllib.parse.quote(api_key)}",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=min(40, self.config.timeout_seconds)) as response:
            body = json.loads(response.read().decode("utf-8"))
        parts: List[str] = []
        for candidate in body.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                text = part.get("text")
                if text:
                    parts.append(text)
        return "\n".join(parts).strip()

    def _ask_anthropic(self, prompt: str) -> str:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        payload = json.dumps(
            {
                "model": self.config.anthropic_model,
                "max_tokens": 600,
                "messages": [{"role": "user", "content": prompt}],
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=min(40, self.config.timeout_seconds)) as response:
            body = json.loads(response.read().decode("utf-8"))
        parts: List[str] = []
        for item in body.get("content", []):
            text = item.get("text")
            if text:
                parts.append(text)
        return "\n".join(parts).strip()

    def _ask_openai_compatible(
        self,
        url: str,
        api_key: str,
        model: str,
        prompt: str,
        *,
        extra_headers: Dict[str, str] | None = None,
        extra_body: Dict[str, Any] | None = None,
    ) -> str:
        if not api_key:
            raise RuntimeError(f"API key is not set for {url}")
        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 600,
        }
        if extra_body:
            body.update(extra_body)
        payload = json.dumps(
            body
        ).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        if extra_headers:
            headers.update({key: _http_header_value(value) for key, value in extra_headers.items()})
        request = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(request, timeout=min(40, self.config.timeout_seconds)) as response:
            body = json.loads(response.read().decode("utf-8"))
        choices = body.get("choices") or []
        if choices:
            message = choices[0].get("message", {})
            content = message.get("content", "")
            if isinstance(content, str):
                return content.strip()
        return json.dumps(body, ensure_ascii=False)[:4000]


class Voice:
    def speak(self, text: str) -> None:
        if not shutil.which("say"):
            raise RuntimeError("Speech output requires the macOS 'say' command")
        subprocess.run(["say", text], check=True)


class MediaCapture:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def screen(self, output_name: str = "screen.png") -> Path:
        if not shutil.which("screencapture"):
            raise RuntimeError("Screen capture is unavailable on this system")
        target = (self.output_dir / output_name).resolve()
        subprocess.run(["screencapture", "-x", str(target)], check=True)
        return target

    def camera(self, output_name: str = "camera.jpg", device: str = "0") -> Path:
        target = (self.output_dir / output_name).resolve()
        if shutil.which("imagesnap"):
            try:
                subprocess.run(["imagesnap", "-w", "1", str(target)], check=True, timeout=20)
                return target
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                if target.exists():
                    target.unlink()
        if shutil.which("ffmpeg"):
            subprocess.run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-f",
                    "avfoundation",
                    "-framerate",
                    "1",
                    "-pixel_format",
                    "nv12",
                    "-i",
                    device,
                    "-frames:v",
                    "1",
                    str(target),
                ],
                check=True,
                timeout=20,
            )
            return target
        raise RuntimeError("Camera capture requires imagesnap or FFmpeg")


class MediaAnalyzer:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def video_keyframes(self, source: Path, seconds: int = 10) -> List[Path]:
        if not shutil.which("ffmpeg"):
            raise RuntimeError("Video keyframe extraction requires FFmpeg")
        target_dir = self.output_dir / f"{source.stem}_frames"
        target_dir.mkdir(parents=True, exist_ok=True)
        pattern = target_dir / "frame_%05d.jpg"
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(source.expanduser().resolve()),
                "-vf",
                f"fps=1/{max(1, seconds)}",
                "-q:v",
                "3",
                str(pattern),
            ],
            check=True,
        )
        return sorted(target_dir.glob("frame_*.jpg"))

    def transcribe(self, source: Path, model_path: Path) -> str:
        executable = shutil.which("whisper-cli") or shutil.which("whisper-cpp")
        if not executable:
            raise RuntimeError("Transcription requires whisper.cpp's whisper-cli")
        result = subprocess.run(
            [
                executable,
                "--no-gpu",
                "--language",
                "auto",
                "--no-timestamps",
                "--no-prints",
                "-m",
                str(model_path.expanduser()),
                "-f",
                str(source.expanduser()),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=3600,
        )
        return result.stdout.strip()

    def record_microphone(self, output_name: str, seconds: int = 4, device: str = ":0") -> Path:
        if not shutil.which("ffmpeg"):
            raise RuntimeError("Microphone capture requires FFmpeg")
        target = (self.output_dir / output_name).resolve()
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "avfoundation",
                "-i",
                device,
                "-t",
                str(max(1, seconds)),
                "-ar",
                "16000",
                "-ac",
                "1",
                "-y",
                str(target),
            ],
            check=True,
            timeout=max(20, seconds + 15),
        )
        return target


@dataclass
class LipSyncProject:
    project_dir: Path
    manifest_path: Path
    prompt_path: Path
    safety_path: Path
    timing_path: Path | None = None
    backend_path: Path | None = None
    eval_path: Path | None = None


@dataclass
class MusicVideoProject:
    project_dir: Path
    output_path: Path
    manifest_path: Path
    prompt_path: Path
    script_path: Path | None = None
    prompt_pack_path: Path | None = None


@dataclass
class ImageMusicVideoProject:
    project_dir: Path
    output_path: Path
    manifest_path: Path
    prompt_path: Path


@dataclass
class AdvancedVideoSongProject:
    project_dir: Path
    output_path: Path
    manifest_path: Path
    storyboard_path: Path
    audio_analysis_path: Path
    prompt_pack_path: Path


@dataclass
class OpenSourceVideoApiProject:
    project_dir: Path
    output_path: Path
    manifest_path: Path
    workflow_path: Path
    prompt_path: Path


@dataclass(frozen=True)
class OpenSourceVideoApiTarget:
    provider_id: str
    name: str
    backend: str
    source_url: str
    base_url: str
    auth_env: str
    requires_cloud_allowed: bool
    requires_explicit_consent: bool
    purpose: str
    safety_notes: List[str]


@dataclass
class NeuralLipSyncProject:
    project_dir: Path
    output_path: Path
    manifest_path: Path
    log_path: Path


@dataclass
class MusicVideoDirectorPlan:
    project_dir: Path
    storyboard_path: Path
    manifest_path: Path


@dataclass
class FrontierVideoPlan:
    project_dir: Path
    manifest_path: Path
    prompt_ladder_path: Path
    backend_report_path: Path
    eval_rubric_path: Path


@dataclass
class SongSketchProject:
    project_dir: Path
    output_path: Path
    manifest_path: Path
    prompt_path: Path


@dataclass
class ExternalMusicApiProject:
    project_dir: Path
    output_path: Path
    manifest_path: Path
    prompt_path: Path


@dataclass
class VideoEvalResult:
    video_path: Path
    report_path: Path
    score: float


class LipSyncPlanner:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_project(
        self,
        audio: Path,
        face: Path,
        prompt: str,
        consent: bool = False,
    ) -> LipSyncProject:
        audio_path = audio.expanduser().resolve()
        face_path = face.expanduser().resolve()
        if not consent:
            raise PermissionError("Lip sync planning requires --consent for the face/person and audio rights")
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file does not exist: {audio_path}")
        if not face_path.exists():
            raise FileNotFoundError(f"Face image/video does not exist: {face_path}")
        if audio_path.suffix.casefold() not in {".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg"}:
            raise ValueError("Audio must be an MP3 or another supported audio file")
        if face_path.suffix.casefold() not in {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".m4v"}:
            raise ValueError("Face source must be an image or video file")

        project_dir = self.output_dir / f"lip_sync_{uuid.uuid4().hex[:12]}"
        project_dir.mkdir(parents=True, exist_ok=True)
        prompt_path = project_dir / "prompt.txt"
        safety_path = project_dir / "safety.txt"
        timing_path = project_dir / "timing_plan.md"
        backend_path = project_dir / "backend_plan.md"
        eval_path = project_dir / "accuracy_rubric.md"
        manifest_path = project_dir / "manifest.json"
        prompt_path.write_text(prompt.strip() + "\n", encoding="utf-8")
        safety_path.write_text(
            "\n".join(
                [
                    "Lip-sync safety rules",
                    "",
                    "- Use only faces/voices/audio you own or have permission to use.",
                    "- Do not impersonate a real person without clear consent.",
                    "- Label generated media as AI-assisted or synthetic when shared.",
                    "- Do not use this workflow for harassment, fraud, sexual content, or deception.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        audio_metadata = self._media_metadata(audio_path)
        face_metadata = self._media_metadata(face_path)
        timing_path.write_text(self._timing_plan(audio_path, face_path, prompt, audio_metadata), encoding="utf-8")
        backend_path.write_text(self._backend_plan(audio_path, face_path), encoding="utf-8")
        eval_path.write_text(self._accuracy_rubric(), encoding="utf-8")
        manifest = {
            "kind": "lip_sync_plan",
            "audio": str(audio_path),
            "face": str(face_path),
            "prompt": prompt,
            "audio_metadata": audio_metadata,
            "face_metadata": face_metadata,
            "output_hint": str(project_dir / "output_lip_sync.mp4"),
            "timing_plan": str(timing_path),
            "backend_plan": str(backend_path),
            "accuracy_rubric": str(eval_path),
            "status": "planned",
            "accuracy_truth": "100% lip-sync accuracy cannot be guaranteed; use short renders, viseme checks, and human review.",
            "next_step": (
                "Install or configure a consent-safe local lip-sync generator such as Wav2Lip/SadTalker-class tooling, "
                "then use this manifest, timing plan, and eval rubric as input."
            ),
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return LipSyncProject(project_dir, manifest_path, prompt_path, safety_path, timing_path, backend_path, eval_path)

    def _timing_plan(self, audio_path: Path, face_path: Path, prompt: str, metadata: Dict[str, object]) -> str:
        try:
            duration = float((metadata.get("format") or {}).get("duration") or 0)
        except (TypeError, ValueError):
            duration = 0.0
        segment_count = max(1, math.ceil((duration or 8.0) / 8))
        segment_length = (duration or 8.0) / segment_count
        lines = [
            "# Lip-Sync Timing Plan",
            "",
            f"Audio: {audio_path}",
            f"Face source: {face_path}",
            f"Creative prompt: {prompt.strip()}",
            f"Estimated duration: {duration:.2f}s" if duration else "Estimated duration: unknown",
            "",
            "## Accuracy Rules",
            "",
            "- Split long songs into short sections before neural rendering.",
            "- Align mouth open/close to syllable peaks, not only beat peaks.",
            "- Preserve face identity and head pose; avoid excessive camera motion during fast lyrics.",
            "- Review plosive sounds such as p/b/m and open vowels manually.",
            "",
            "## Segments",
        ]
        for index in range(segment_count):
            start = index * segment_length
            end = duration if duration and index == segment_count - 1 else (index + 1) * segment_length
            lines.extend(
                [
                    "",
                    f"### Segment {index + 1}: {start:.2f}s-{end:.2f}s",
                    "- Render/check target: mouth closure, vowel openness, jaw timing, face stability.",
                    "- If drift appears, rerender this segment only and crossfade back into the full video.",
                ]
            )
        return "\n".join(lines) + "\n"

    def _backend_plan(self, audio_path: Path, face_path: Path) -> str:
        deps = dependency_report()
        return "\n".join(
            [
                "# Local Lip-Sync Backend Plan",
                "",
                "## Current Inputs",
                "",
                f"- Audio: `{audio_path}`",
                f"- Face source: `{face_path}`",
                "",
                "## Local Tool Status",
                "",
                f"- ffmpeg: {'ready' if deps.get('ffmpeg') else 'missing'}",
                f"- ffprobe: {'ready' if deps.get('ffprobe') else 'missing'}",
                f"- Python: ready",
                "",
                "## Free Local Backend Candidates",
                "",
                "### Wav2Lip-class pipeline",
                "- Best for direct audio-to-mouth synchronization on a consented face video/image.",
                "- Needs model weights, face detection, aligned crop, and post-merge with original audio.",
                "",
                "### SadTalker / talking-head-class pipeline",
                "- Better for still portraits with head motion, but may be less exact for fast singing.",
                "- Needs checkpoint weights and careful face/reference preparation.",
                "",
                "### Manual professional fallback",
                "- Use generated music video plus non-face visuals when consent/quality is not enough.",
                "- This avoids bad mouth artifacts while still producing a polished video.",
                "",
                "## Target Workflow",
                "",
                "1. Prepare 720p or 1080p face source with clear mouth visibility.",
                "2. Normalize audio, split into short sections, render each section.",
                "3. Merge sections with ffmpeg, preserve original AAC audio.",
                "4. Run accuracy rubric and human review before publishing.",
            ]
        ) + "\n"

    def _accuracy_rubric(self) -> str:
        rows = [
            ("mouth_timing", "Do mouth open/close moments match syllable timing?"),
            ("phoneme_shape", "Do p/b/m closures and open vowels look plausible?"),
            ("identity_stability", "Does the face remain stable without melting or drift?"),
            ("head_motion", "Is head motion natural and not fighting the mouth animation?"),
            ("audio_integrity", "Is the original audio preserved and synchronized after export?"),
            ("consent_provenance", "Are rights/consent and AI-assisted labeling recorded?"),
        ]
        lines = ["# Lip-Sync Accuracy Rubric", "", "Score each item from 0.0 to 1.0. 100% is a target, not a guarantee.", ""]
        for name, question in rows:
            lines.extend([f"## {name}", "", f"- Question: {question}", "- Score:", "- Notes:", ""])
        return "\n".join(lines)

    def _media_metadata(self, path: Path) -> Dict[str, object]:
        if not shutil.which("ffprobe"):
            return {"path": str(path), "ffprobe": "unavailable"}
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration,format_name,size",
                    "-of",
                    "json",
                    str(path),
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return json.loads(result.stdout or "{}")
        except Exception as error:
            return {"path": str(path), "error": str(error)}


class LocalMusicVideoRenderer:
    AUDIO_SUFFIXES = {".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg"}
    STYLES = {
        "waveform": "showwaves=s=1280x720:mode=line:colors=cyan,format=yuv420p",
        "spectrum": "showspectrum=s=1280x720:mode=combined:color=intensity:slide=scroll,format=yuv420p",
    }
    PROFESSIONAL_STYLE = "professional"

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def render(
        self,
        audio: Path,
        prompt: str,
        style: str = "waveform",
        consent: bool = False,
    ) -> MusicVideoProject:
        if not consent:
            raise PermissionError("Local music video rendering requires --consent for the audio rights")
        if not shutil.which("ffmpeg"):
            raise RuntimeError("Local music video rendering requires ffmpeg")
        audio_path = audio.expanduser().resolve()
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file does not exist: {audio_path}")
        if audio_path.suffix.casefold() not in self.AUDIO_SUFFIXES:
            raise ValueError("Audio must be an MP3 or another supported audio file")
        if style not in {*self.STYLES, self.PROFESSIONAL_STYLE}:
            raise ValueError(f"Unknown local music video style: {style}")

        project_dir = self.output_dir / f"music_video_{uuid.uuid4().hex[:12]}"
        project_dir.mkdir(parents=True, exist_ok=True)
        output_path = project_dir / "output_music_video.mp4"
        manifest_path = project_dir / "manifest.json"
        prompt_path = project_dir / "prompt.txt"
        script_path = project_dir / "video_script.md"
        prompt_pack_path = project_dir / "prompt_pack.md"
        prompt_path.write_text(prompt.strip() + "\n", encoding="utf-8")
        metadata = LipSyncPlanner(project_dir)._media_metadata(audio_path)
        duration = self._duration(metadata)
        script_path.write_text(self._script_text(audio_path, prompt, style, duration), encoding="utf-8")
        prompt_pack_path.write_text(self._prompt_pack_text(audio_path, prompt, style, duration), encoding="utf-8")
        if style == self.PROFESSIONAL_STYLE:
            command = self._professional_command(audio_path, output_path, project_dir, duration)
        else:
            command = [
                "ffmpeg",
                "-hide_banner",
                "-y",
                "-i",
                str(audio_path),
                "-filter_complex",
                f"[0:a]{self.STYLES[style]}[v]",
                "-map",
                "[v]",
                "-map",
                "0:a",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-c:a",
                "aac",
                "-shortest",
                str(output_path),
            ]
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=900)
        manifest = {
            "kind": "local_music_video",
            "audio": str(audio_path),
            "prompt": prompt,
            "style": style,
            "renderer": "ffmpeg",
            "output": str(output_path),
            "script": str(script_path),
            "prompt_pack": str(prompt_pack_path),
            "status": "rendered",
            "audio_metadata": metadata,
            "output_metadata": LipSyncPlanner(project_dir)._media_metadata(output_path),
            "safety": [
                "Use only audio you own or have permission to use.",
                "Label generated media as AI-assisted or locally rendered when shared.",
            ],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return MusicVideoProject(project_dir, output_path, manifest_path, prompt_path, script_path, prompt_pack_path)

    def _duration(self, metadata: Dict[str, object]) -> float:
        try:
            return max(4.0, float((metadata.get("format") or {}).get("duration") or 30.0))
        except (TypeError, ValueError):
            return 30.0

    def _professional_command(self, audio_path: Path, output_path: Path, project_dir: Path, duration: float) -> List[str]:
        cover_path = self._extract_cover(audio_path, project_dir)
        if cover_path:
            return [
                "ffmpeg",
                "-hide_banner",
                "-y",
                "-loop",
                "1",
                "-i",
                str(cover_path),
                "-i",
                str(audio_path),
                "-filter_complex",
                (
                    "[0:v]scale=1280:720:force_original_aspect_ratio=increase,"
                    "crop=1280:720,boxblur=18:1,eq=brightness=-0.10:saturation=1.25[bg];"
                    "[1:a]showspectrum=s=1280x320:mode=combined:color=fire:slide=scroll,"
                    "format=rgba,colorchannelmixer=aa=0.62[spec];"
                    "[1:a]showwaves=s=1280x150:mode=line:colors=white,"
                    "format=rgba,colorchannelmixer=aa=0.88[wave];"
                    "[bg][spec]overlay=0:360[tmp];[tmp][wave]overlay=0:555,format=yuv420p[v]"
                ),
                "-map",
                "[v]",
                "-map",
                "1:a",
                "-t",
                f"{duration:.3f}",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-c:a",
                "aac",
                "-shortest",
                str(output_path),
            ]
        return [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=0x080b16:s=1280x720:r=30:d={duration:.3f}",
            "-i",
            str(audio_path),
            "-filter_complex",
            (
                "[0:v]format=rgba[bg];"
                "[1:a]showspectrum=s=1280x390:mode=combined:color=fire:slide=scroll,"
                "format=rgba,colorchannelmixer=aa=0.72[spec];"
                "[1:a]showwaves=s=1280x160:mode=line:colors=white,"
                "format=rgba,colorchannelmixer=aa=0.90[wave];"
                "[bg][spec]overlay=0:255[tmp];[tmp][wave]overlay=0:535,format=yuv420p[v]"
            ),
            "-map",
            "[v]",
            "-map",
            "1:a",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-c:a",
            "aac",
            "-shortest",
            str(output_path),
        ]

    def _extract_cover(self, audio_path: Path, project_dir: Path) -> Path | None:
        cover_path = project_dir / "cover_art.jpg"
        command = [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-i",
            str(audio_path),
            "-map",
            "0:v:0",
            "-frames:v",
            "1",
            str(cover_path),
        ]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True, timeout=60)
        except subprocess.CalledProcessError:
            return None
        return cover_path if cover_path.exists() and cover_path.stat().st_size else None

    def _script_text(self, audio_path: Path, prompt: str, style: str, duration: float) -> str:
        scene_count = max(4, min(12, math.ceil(duration / 24)))
        scene_length = duration / scene_count
        lines = [
            "# Professional Local Music Video Script",
            "",
            f"Audio: {audio_path}",
            f"Duration: {duration:.2f}s",
            f"Style: {style}",
            f"Creative direction: {prompt.strip()}",
            "",
            "## Production Intent",
            "",
            "Create a clean music-first video with cover-art atmosphere, audio-reactive movement, cinematic pacing, and export-ready MP4 delivery.",
            "",
            "## Timeline",
        ]
        for index in range(scene_count):
            start = index * scene_length
            end = duration if index == scene_count - 1 else (index + 1) * scene_length
            energy = "intro" if index == 0 else "final lift" if index == scene_count - 1 else "build"
            lines.extend(
                [
                    "",
                    f"### Scene {index + 1}: {start:.1f}s-{end:.1f}s",
                    f"- Energy: {energy}",
                    "- Visual: blurred cover-art mood, warm spectrum motion, white waveform accents.",
                    "- Edit note: keep motion synced to the vocal rhythm and strongest beats.",
                    f"- Prompt: {prompt.strip()} | {energy} section | polished music-video visualizer.",
                ]
            )
        return "\n".join(lines) + "\n"

    def _prompt_pack_text(self, audio_path: Path, prompt: str, style: str, duration: float) -> str:
        return "\n".join(
            [
                "# Built Prompt Pack",
                "",
                "## Master Prompt",
                "",
                (
                    f"Generate a professional music video for `{audio_path.name}`. "
                    f"Use this direction: {prompt.strip()}. "
                    "Keep the result emotional, clean, cinematic, audio-reactive, and respectful to the original song."
                ),
                "",
                "## Local FFmpeg Render Prompt",
                "",
                (
                    "Use the song audio as the timing source. Build a 1280x720 MP4 with blurred cover-art background, "
                    "audio spectrum, waveform overlay, AAC audio, H.264 video, and traceable manifest."
                ),
                "",
                "## Future Neural Video Prompt",
                "",
                (
                    "Image-to-video music clip, cinematic lighting, gentle camera drift, emotional Sinhala song mood, "
                    "soft highlights, premium color grade, beat-synced edits, no face identity claims, no copyrighted imitation."
                ),
                "",
                "## Export Targets",
                "",
                f"- Duration: {duration:.2f}s",
                f"- Style: {style}",
                "- Format: MP4, H.264 + AAC",
            ]
        ) + "\n"


class LocalImageMusicVideoRenderer:
    AUDIO_SUFFIXES = LocalMusicVideoRenderer.AUDIO_SUFFIXES
    IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def render(
        self,
        audio: Path,
        images: List[Path],
        prompt: str,
        aspect: str = "16:9",
        max_duration_seconds: int = 45,
        consent: bool = False,
    ) -> ImageMusicVideoProject:
        if not consent:
            raise PermissionError("Image music video rendering requires consent/rights for audio and images")
        if not shutil.which("ffmpeg"):
            raise RuntimeError("Image music video rendering requires ffmpeg")
        audio_path = audio.expanduser().resolve()
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file does not exist: {audio_path}")
        if audio_path.suffix.casefold() not in self.AUDIO_SUFFIXES:
            raise ValueError("Audio must be an MP3 or another supported audio file")
        image_paths = [image.expanduser().resolve() for image in images]
        if not image_paths:
            raise ValueError("At least one image is required")
        for image_path in image_paths:
            if not image_path.exists():
                raise FileNotFoundError(f"Image file does not exist: {image_path}")
            if image_path.suffix.casefold() not in self.IMAGE_SUFFIXES:
                raise ValueError("Images must be jpg, jpeg, png, or webp files")
        width, height = self._resolution(aspect)
        audio_duration = self._duration(audio_path)
        render_duration = min(audio_duration, max(4.0, float(max_duration_seconds)))
        per_image = max(2.0, render_duration / len(image_paths))
        project_dir = self.output_dir / f"image_music_video_{uuid.uuid4().hex[:12]}"
        project_dir.mkdir(parents=True, exist_ok=True)
        output_path = project_dir / "output_image_music_video.mp4"
        manifest_path = project_dir / "manifest.json"
        prompt_path = project_dir / "prompt.txt"
        prompt_path.write_text(prompt.strip() + "\n", encoding="utf-8")

        command = ["ffmpeg", "-hide_banner", "-y"]
        for image_path in image_paths:
            command.extend(["-loop", "1", "-t", f"{per_image:.3f}", "-i", str(image_path)])
        command.extend(["-t", f"{render_duration:.3f}", "-i", str(audio_path)])
        filters = []
        for index in range(len(image_paths)):
            filters.append(
                f"[{index}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p[v{index}]"
            )
        concat_inputs = "".join(f"[v{index}]" for index in range(len(image_paths)))
        filters.append(f"{concat_inputs}concat=n={len(image_paths)}:v=1:a=0[v]")
        command.extend(
            [
                "-filter_complex",
                ";".join(filters),
                "-map",
                "[v]",
                "-map",
                f"{len(image_paths)}:a",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-c:a",
                "aac",
                "-shortest",
                str(output_path),
            ]
        )
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=900)
        manifest = {
            "kind": "local_image_music_video",
            "audio": str(audio_path),
            "images": [str(path) for path in image_paths],
            "prompt": prompt,
            "aspect": aspect,
            "resolution": f"{width}x{height}",
            "audio_duration_seconds": audio_duration,
            "render_duration_seconds": render_duration,
            "seconds_per_image": per_image,
            "renderer": "ffmpeg",
            "output": str(output_path),
            "status": "rendered",
            "audio_metadata": LipSyncPlanner(project_dir)._media_metadata(audio_path),
            "output_metadata": LipSyncPlanner(project_dir)._media_metadata(output_path),
            "safety": [
                "Use only audio and images you own or have permission to use.",
                "Label generated media as AI-assisted or locally rendered when shared.",
            ],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return ImageMusicVideoProject(project_dir, output_path, manifest_path, prompt_path)

    def _duration(self, audio_path: Path) -> float:
        metadata = LipSyncPlanner(self.output_dir)._media_metadata(audio_path)
        try:
            return max(2.0, float((metadata.get("format") or {}).get("duration") or 8.0))
        except (TypeError, ValueError):
            return 8.0

    def _resolution(self, aspect: str) -> tuple[int, int]:
        if aspect == "9:16":
            return 720, 1280
        if aspect == "1:1":
            return 1080, 1080
        return 1280, 720


class OpenAIImageGenerator:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        prompt: str,
        *,
        model: str = "gpt-image-2",
        size: str = "1024x1024",
        quality: str = "auto",
        consent: bool = False,
    ) -> dict[str, str]:
        prompt = prompt.strip()
        if not consent:
            raise PermissionError("OpenAI image generation requires confirmation that you have rights/consent for the request")
        require_cloud_allowed("OpenAI image generation")
        if not prompt:
            raise ValueError("Image prompt is required")
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set. Save ChatGPT / OpenAI in API Bindings first.")
        project_dir = self.output_dir / f"openai_image_{uuid.uuid4().hex[:12]}"
        project_dir.mkdir(parents=True, exist_ok=True)
        output_path = project_dir / "generated_image.png"
        manifest_path = project_dir / "manifest.json"
        prompt_path = project_dir / "prompt.txt"
        prompt_path.write_text(prompt + "\n", encoding="utf-8")
        payload = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "quality": quality,
            "n": 1,
        }
        request = urllib.request.Request(
            "https://api.openai.com/v1/images/generations",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=180) as response:
            body = json.loads(response.read().decode("utf-8"))
        image_rows = body.get("data") or []
        if not image_rows:
            raise RuntimeError("OpenAI image generation returned no image data")
        first = image_rows[0]
        revised_prompt = str(first.get("revised_prompt") or "")
        if first.get("b64_json"):
            output_path.write_bytes(base64.b64decode(first["b64_json"]))
        elif first.get("url"):
            image_request = urllib.request.Request(first["url"], headers={"User-Agent": "Gima local assistant/0.1"})
            with urllib.request.urlopen(image_request, timeout=120) as image_response:
                output_path.write_bytes(image_response.read())
        else:
            raise RuntimeError("OpenAI image generation returned neither b64_json nor url")
        manifest = {
            "provider": "openai",
            "api": "images.generations",
            "model": model,
            "size": size,
            "quality": quality,
            "prompt": prompt,
            "revised_prompt": revised_prompt,
            "output_path": str(output_path),
            "prompt_path": str(prompt_path),
            "rights_note": "Generated only after user confirmation of rights/consent.",
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        return {
            "output_path": str(output_path),
            "manifest_path": str(manifest_path),
            "prompt_path": str(prompt_path),
            "model": model,
            "size": size,
            "quality": quality,
            "revised_prompt": revised_prompt,
        }


class HuggingFaceImageGenerator:
    """Hugging Face InferenceClient text-to-image adapter."""

    def __init__(self, output_dir: Path | str):
        self.output_dir = Path(output_dir).expanduser().resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.output_dir / "whatsapp_messages.jsonl"
        self.index_path = self.output_dir / "whatsapp_messages.jsonl"

    def status(self) -> dict[str, object]:
        return {
            "provider": "huggingface",
            "backend": "huggingface_hub.InferenceClient.text_to_image",
            "ready": bool(self._hf_token()),
            "cloud_allowed": cloud_allowed(),
            "default_provider": os.environ.get("GIMA_HF_IMAGE_PROVIDER", "wavespeed"),
            "default_model": os.environ.get("GIMA_HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-dev"),
            "env": ["HF_TOKEN or HUGGINGFACE_API_KEY", "CLOUD_ALLOWED=true"],
            "safety": [
                "Requires explicit consent because provider inference may spend credits.",
                "Use only prompts, images, likenesses, and references you own or have permission to use.",
                "Gima stores output and manifest locally; it never exposes the token to the browser.",
            ],
        }

    def generate(
        self,
        prompt: str,
        *,
        model: str = "black-forest-labs/FLUX.1-dev",
        provider: str = "wavespeed",
        consent: bool = False,
    ) -> dict[str, object]:
        prompt = " ".join(prompt.strip().split())
        if not consent:
            raise PermissionError("Hugging Face image generation can spend credits and requires explicit consent")
        require_cloud_allowed("Hugging Face text-to-image generation")
        if not prompt:
            raise ValueError("Image prompt is required")
        token = self._hf_token()
        if not token:
            raise RuntimeError("HF_TOKEN or HUGGINGFACE_API_KEY is not set")
        project_dir = self.output_dir / f"huggingface_image_{uuid.uuid4().hex[:12]}"
        project_dir.mkdir(parents=True, exist_ok=True)
        output_path = project_dir / "output_huggingface_image.png"
        prompt_path = project_dir / "prompt.txt"
        manifest_path = project_dir / "manifest.json"
        prompt_path.write_text(prompt + "\n", encoding="utf-8")
        try:
            hub = importlib.import_module("huggingface_hub")
        except ImportError as error:
            raise RuntimeError("Install huggingface_hub to use Hugging Face image generation: pip install huggingface_hub") from error
        client = hub.InferenceClient(provider=provider, api_key=token)
        image = client.text_to_image(prompt, model=model)
        self._write_image_result(image, output_path)
        manifest = {
            "kind": "huggingface_text_to_image",
            "status": "generated",
            "provider": "huggingface",
            "inference_provider": provider,
            "model": model,
            "prompt": prompt,
            "output": str(output_path),
            "prompt_path": str(prompt_path),
            "response_type": type(image).__name__,
            "safety": [
                "This cloud image job can spend Hugging Face/provider credits.",
                "Use only prompts, likenesses, images, and references you own or have permission to use.",
                "Label generated or AI-assisted images when sharing.",
            ],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        return {
            "status": "generated",
            "provider": "huggingface",
            "inference_provider": provider,
            "model": model,
            "output_path": str(output_path),
            "manifest_path": str(manifest_path),
            "prompt_path": str(prompt_path),
        }

    def _write_image_result(self, image: object, output_path: Path) -> None:
        if isinstance(image, bytes):
            output_path.write_bytes(image)
            return
        if isinstance(image, bytearray):
            output_path.write_bytes(bytes(image))
            return
        if hasattr(image, "save"):
            image.save(output_path)
            return
        if hasattr(image, "read"):
            data = image.read()
            if isinstance(data, str):
                data = data.encode("utf-8")
            output_path.write_bytes(bytes(data))
            return
        if isinstance(image, (str, Path)):
            value = str(image)
            if value.startswith(("https://", "http://")):
                request = urllib.request.Request(value, headers={"User-Agent": "Gima local assistant/0.1"})
                with urllib.request.urlopen(request, timeout=180) as response:
                    output_path.write_bytes(response.read())
                return
            source = Path(value).expanduser().resolve()
            if source.exists() and source.is_file():
                shutil.copy2(source, output_path)
                return
        if isinstance(image, dict):
            for key in ("image", "image_base64", "png", "data"):
                value = image.get(key)
                if isinstance(value, str) and value.strip():
                    text = value.strip()
                    if text.startswith("data:") and "," in text:
                        text = text.split(",", 1)[1]
                    try:
                        output_path.write_bytes(base64.b64decode(text))
                        return
                    except Exception:
                        pass
            for key in ("url", "image_url", "download_url", "file"):
                value = image.get(key)
                if isinstance(value, str) and value.startswith(("https://", "http://")):
                    request = urllib.request.Request(value, headers={"User-Agent": "Gima local assistant/0.1"})
                    with urllib.request.urlopen(request, timeout=180) as response:
                        output_path.write_bytes(response.read())
                    return
        raise RuntimeError(f"Hugging Face text_to_image returned unsupported type: {type(image).__name__}")

    def _hf_token(self) -> str:
        return os.environ.get("HF_TOKEN", "").strip() or os.environ.get("HUGGINGFACE_API_KEY", "").strip()


class HuggingFaceFeatureExtractor:
    """Hugging Face InferenceClient feature-extraction adapter."""

    def __init__(self, output_dir: Path | str):
        self.output_dir = Path(output_dir).expanduser().resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def status(self) -> dict[str, object]:
        return {
            "provider": "huggingface",
            "backend": "huggingface_hub.InferenceClient.feature_extraction",
            "ready": bool(self._hf_token()),
            "cloud_allowed": cloud_allowed(),
            "default_provider": os.environ.get("GIMA_HF_FEATURE_PROVIDER", "hf-inference"),
            "default_model": os.environ.get("GIMA_HF_FEATURE_MODEL", "microsoft/harrier-oss-v1-0.6b"),
            "env": ["HF_TOKEN or HUGGINGFACE_API_KEY", "CLOUD_ALLOWED=true"],
            "safety": [
                "Requires explicit consent because text is sent to Hugging Face/provider inference.",
                "Use for public or approved text only unless you intentionally allow cloud processing.",
                "Gima stores feature vectors locally; it never exposes the token to the browser.",
            ],
        }

    def extract(
        self,
        text: str,
        *,
        model: str = "microsoft/harrier-oss-v1-0.6b",
        provider: str = "hf-inference",
        consent: bool = False,
    ) -> dict[str, object]:
        clean_text = " ".join(text.strip().split())
        if not consent:
            raise PermissionError("Hugging Face feature extraction requires explicit consent")
        require_cloud_allowed("Hugging Face feature extraction")
        if not clean_text:
            raise ValueError("Feature extraction text is required")
        token = self._hf_token()
        if not token:
            raise RuntimeError("HF_TOKEN or HUGGINGFACE_API_KEY is not set")
        project_dir = self.output_dir / f"huggingface_features_{uuid.uuid4().hex[:12]}"
        project_dir.mkdir(parents=True, exist_ok=True)
        input_path = project_dir / "input.txt"
        features_path = project_dir / "features.json"
        csv_path = project_dir / "features.csv"
        manifest_path = project_dir / "manifest.json"
        input_path.write_text(clean_text + "\n", encoding="utf-8")
        try:
            hub = importlib.import_module("huggingface_hub")
        except ImportError as error:
            raise RuntimeError("Install huggingface_hub to use Hugging Face feature extraction: pip install huggingface_hub") from error
        client = hub.InferenceClient(provider=provider, api_key=token)
        result = client.feature_extraction(clean_text, model=model)
        serializable = self._to_serializable(result)
        features_path.write_text(json.dumps(serializable, indent=2, ensure_ascii=False), encoding="utf-8")
        stats = self._write_feature_csv(csv_path, serializable)
        manifest = {
            "kind": "huggingface_feature_extraction",
            "status": "generated",
            "provider": "huggingface",
            "inference_provider": provider,
            "model": model,
            "input_path": str(input_path),
            "features_path": str(features_path),
            "csv_path": str(csv_path),
            "stats": stats,
            "safety": [
                "This cloud feature-extraction job can spend Hugging Face/provider credits.",
                "Do not send private text unless CLOUD_ALLOWED=true was set intentionally.",
                "Feature vectors are saved locally for review before being connected to Gima retrieval.",
            ],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        return {
            "status": "generated",
            "provider": "huggingface",
            "inference_provider": provider,
            "model": model,
            "input_path": str(input_path),
            "features_path": str(features_path),
            "csv_path": str(csv_path),
            "manifest_path": str(manifest_path),
            "stats": stats,
        }

    def _to_serializable(self, value: object) -> object:
        if hasattr(value, "tolist"):
            return value.tolist()
        if isinstance(value, tuple):
            return [self._to_serializable(item) for item in value]
        if isinstance(value, list):
            return [self._to_serializable(item) for item in value]
        if isinstance(value, dict):
            return {str(key): self._to_serializable(item) for key, item in value.items()}
        if isinstance(value, (int, float, str, bool)) or value is None:
            return value
        return str(value)

    def _write_feature_csv(self, path: Path, value: object) -> dict[str, object]:
        numbers: list[float] = []
        self._collect_numbers(value, numbers)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["index", "value"])
            writer.writeheader()
            for index, number in enumerate(numbers[:4096]):
                writer.writerow({"index": index, "value": number})
        if not numbers:
            return {"count": 0, "preview_count": 0}
        return {
            "count": len(numbers),
            "preview_count": min(len(numbers), 4096),
            "min": min(numbers),
            "max": max(numbers),
            "mean": sum(numbers) / len(numbers),
        }

    def _collect_numbers(self, value: object, output: list[float]) -> None:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            output.append(float(value))
        elif isinstance(value, list):
            for item in value:
                self._collect_numbers(item, output)
        elif isinstance(value, dict):
            for item in value.values():
                self._collect_numbers(item, output)

    def _hf_token(self) -> str:
        return os.environ.get("HF_TOKEN", "").strip() or os.environ.get("HUGGINGFACE_API_KEY", "").strip()


class TransformersTextGenerator:
    """Local Hugging Face Transformers text-generation adapter."""

    def __init__(self, output_dir: Path | str):
        self.output_dir = Path(output_dir).expanduser().resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def status(self) -> dict[str, object]:
        installed = importlib.util.find_spec("transformers") is not None and importlib.util.find_spec("torch") is not None
        return {
            "provider": "local",
            "backend": "transformers.pipeline(text-generation)",
            "installed": installed,
            "ready": installed,
            "default_model": os.environ.get("GIMA_TRANSFORMERS_MODEL", "google/gemma-2-2b-it"),
            "default_device": os.environ.get("GIMA_TRANSFORMERS_DEVICE", "auto"),
            "local_files_only_default": self._env_bool("GIMA_TRANSFORMERS_LOCAL_FILES_ONLY", True),
            "env": [
                "Optional: GIMA_TRANSFORMERS_MODEL=google/gemma-2-2b-it",
                "Optional: GIMA_TRANSFORMERS_DEVICE=auto|mps|cuda|cpu",
                "Optional: GIMA_TRANSFORMERS_LOCAL_FILES_ONLY=false to allow first-time model download",
            ],
            "safety": [
                "Runs the model locally after it is available in the Transformers cache.",
                "Model download can be large; Gima requires explicit consent before loading or downloading.",
                "Use local_files_only=true when you do not want network access.",
            ],
        }

    def generate(
        self,
        prompt: str,
        *,
        model: str = "google/gemma-2-2b-it",
        device: str = "auto",
        max_new_tokens: int = 256,
        local_files_only: bool = True,
        consent: bool = False,
    ) -> dict[str, object]:
        clean_prompt = " ".join(prompt.strip().split())
        if not consent:
            raise PermissionError("Local Transformers generation requires consent because model loading can be slow or download large files")
        if not clean_prompt:
            raise ValueError("Prompt is required")
        model = (model or "google/gemma-2-2b-it").strip()
        device = (device or "auto").strip().lower()
        max_new_tokens = max(1, min(int(max_new_tokens or 256), 2048))
        project_dir = self.output_dir / f"transformers_text_{uuid.uuid4().hex[:12]}"
        project_dir.mkdir(parents=True, exist_ok=True)
        prompt_path = project_dir / "prompt.txt"
        response_path = project_dir / "response.txt"
        manifest_path = project_dir / "manifest.json"
        prompt_path.write_text(clean_prompt + "\n", encoding="utf-8")
        try:
            torch = importlib.import_module("torch")
            transformers = importlib.import_module("transformers")
        except ImportError as error:
            raise RuntimeError("Install torch and transformers to use local Transformers chat: pip install torch transformers") from error

        selected_device = self._select_device(torch, device)
        dtype = self._select_dtype(torch, selected_device)
        model_kwargs: dict[str, object] = {"local_files_only": bool(local_files_only)}
        if dtype is not None:
            model_kwargs["torch_dtype"] = dtype
        pipe = transformers.pipeline(
            "text-generation",
            model=model,
            model_kwargs=model_kwargs,
            device=selected_device,
        )
        messages = [{"role": "user", "content": clean_prompt}]
        outputs = pipe(messages, max_new_tokens=max_new_tokens)
        answer = self._extract_answer(outputs)
        response_path.write_text(answer + "\n", encoding="utf-8")
        manifest = {
            "kind": "local_transformers_text_generation",
            "status": "generated",
            "provider": "local",
            "backend": "transformers.pipeline",
            "model": model,
            "device": selected_device,
            "max_new_tokens": max_new_tokens,
            "local_files_only": bool(local_files_only),
            "prompt_path": str(prompt_path),
            "response_path": str(response_path),
            "response_preview": answer[:500],
            "safety": [
                "Model runs locally after files are present in the local cache.",
                "If local_files_only=false, Transformers may download model files from Hugging Face.",
                "Large models can be slow on CPU and may require more RAM than this Mac has available.",
            ],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        return {
            "status": "generated",
            "provider": "local",
            "model": model,
            "device": selected_device,
            "answer": answer,
            "prompt_path": str(prompt_path),
            "response_path": str(response_path),
            "manifest_path": str(manifest_path),
            "local_files_only": bool(local_files_only),
        }

    def _select_device(self, torch: object, requested: str) -> str:
        if requested and requested != "auto":
            return requested
        cuda = getattr(torch, "cuda", None)
        if cuda is not None and callable(getattr(cuda, "is_available", None)) and cuda.is_available():
            return "cuda"
        backends = getattr(torch, "backends", None)
        mps = getattr(backends, "mps", None) if backends is not None else None
        if mps is not None and callable(getattr(mps, "is_available", None)) and mps.is_available():
            return "mps"
        return "cpu"

    def _select_dtype(self, torch: object, device: str) -> object | None:
        if device in {"cuda", "mps"}:
            return getattr(torch, "bfloat16", None)
        return None

    def _extract_answer(self, outputs: object) -> str:
        try:
            first = outputs[0]  # type: ignore[index]
            generated = first.get("generated_text") if isinstance(first, dict) else first
            if isinstance(generated, list) and generated:
                last = generated[-1]
                if isinstance(last, dict):
                    return str(last.get("content", "")).strip()
                return str(last).strip()
            if isinstance(generated, str):
                return generated.strip()
        except Exception:
            pass
        return str(outputs).strip()

    def _env_bool(self, name: str, default: bool) -> bool:
        value = os.environ.get(name)
        if value is None:
            return default
        return value.strip().casefold() in {"1", "true", "yes", "on"}


class WhatsAppMessenger:
    """Official WhatsApp Cloud API helper plus local wa.me draft links."""

    graph_base_url = "https://graph.facebook.com/v20.0"

    def __init__(self, output_dir: Path | str):
        self.output_dir = Path(output_dir).expanduser().resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.output_dir / "whatsapp_messages.jsonl"

    def status(self) -> dict[str, object]:
        return {
            "provider": "whatsapp",
            "backend": "Meta WhatsApp Cloud API",
            "ready": bool(self._token() and self._phone_number_id()),
            "cloud_allowed": cloud_allowed(),
            "draft_links_available": True,
            "inbox_count": len(self.search_messages(limit=10000)["messages"]),
            "webhook_verify_configured": bool(self._webhook_verify_token()),
            "webhook_signature_configured": bool(self._app_secret()),
            "env": [
                "WHATSAPP_CLOUD_TOKEN",
                "WHATSAPP_PHONE_NUMBER_ID",
                "WHATSAPP_WEBHOOK_VERIFY_TOKEN for Meta webhook setup",
                "Optional: WHATSAPP_APP_SECRET for webhook signature verification",
                "CLOUD_ALLOWED=true for sending",
            ],
            "safety": [
                "Draft links are local and open WhatsApp/WhatsApp Web for user review.",
                "Direct sending uses only the official WhatsApp Cloud API.",
                "Inbound retrieval uses official webhook events saved locally by Gima.",
                "Gima requires explicit consent and will not spam or bypass WhatsApp limits.",
            ],
        }

    def draft_link(self, to: str, message: str) -> dict[str, object]:
        recipient = self._normalize_recipient(to)
        clean_message = self._clean_message(message)
        link = f"https://wa.me/{recipient}?text={urllib.parse.quote(clean_message)}"
        project_dir = self.output_dir / f"whatsapp_draft_{uuid.uuid4().hex[:12]}"
        project_dir.mkdir(parents=True, exist_ok=True)
        message_path = project_dir / "message.txt"
        manifest_path = project_dir / "manifest.json"
        message_path.write_text(clean_message + "\n", encoding="utf-8")
        manifest = {
            "kind": "whatsapp_message_draft",
            "status": "drafted",
            "provider": "whatsapp",
            "recipient": recipient,
            "message_path": str(message_path),
            "wa_me_link": link,
            "safety": [
                "Draft link requires the user to review and send in WhatsApp.",
                "Use only with contacts who expect your message.",
            ],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        self._record_message(
            direction="draft",
            contact=recipient,
            text=clean_message,
            source="wa.me",
            manifest_path=manifest_path,
            message_path=message_path,
            metadata={"wa_me_link": link},
        )
        return {
            "status": "drafted",
            "provider": "whatsapp",
            "recipient": recipient,
            "message": clean_message,
            "wa_me_link": link,
            "message_path": str(message_path),
            "manifest_path": str(manifest_path),
        }

    def send_text(self, to: str, message: str, *, consent: bool = False) -> dict[str, object]:
        if not consent:
            raise PermissionError("WhatsApp sending requires explicit consent")
        require_cloud_allowed("WhatsApp Cloud API message sending")
        recipient = self._normalize_recipient(to)
        clean_message = self._clean_message(message)
        token = self._token()
        phone_number_id = self._phone_number_id()
        if not token or not phone_number_id:
            raise RuntimeError("WHATSAPP_CLOUD_TOKEN and WHATSAPP_PHONE_NUMBER_ID are required for direct sending")
        project_dir = self.output_dir / f"whatsapp_sent_{uuid.uuid4().hex[:12]}"
        project_dir.mkdir(parents=True, exist_ok=True)
        message_path = project_dir / "message.txt"
        response_path = project_dir / "response.json"
        manifest_path = project_dir / "manifest.json"
        message_path.write_text(clean_message + "\n", encoding="utf-8")
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": clean_message},
        }
        request = urllib.request.Request(
            f"{self.graph_base_url}/{urllib.parse.quote(phone_number_id)}/messages",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
        response_path.write_text(json.dumps(body, indent=2, sort_keys=True), encoding="utf-8")
        manifest = {
            "kind": "whatsapp_cloud_text_message",
            "status": "sent",
            "provider": "whatsapp",
            "recipient": recipient,
            "phone_number_id": phone_number_id,
            "message_path": str(message_path),
            "response_path": str(response_path),
            "safety": [
                "Sent through the official WhatsApp Cloud API after explicit user consent.",
                "Do not use for spam, harassment, credential requests, or messages to people who did not expect contact.",
            ],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        self._record_message(
            direction="outbound",
            contact=recipient,
            text=clean_message,
            source="whatsapp_cloud_api",
            manifest_path=manifest_path,
            message_path=message_path,
            metadata={"api_response": body, "response_path": str(response_path)},
        )
        return {
            "status": "sent",
            "provider": "whatsapp",
            "recipient": recipient,
            "message_path": str(message_path),
            "response_path": str(response_path),
            "manifest_path": str(manifest_path),
            "api_response": body,
        }

    def record_webhook(self, payload: dict[str, object], *, signature: str = "", raw_body: bytes = b"") -> dict[str, object]:
        if self._app_secret() and not self.verify_signature(raw_body, signature):
            raise PermissionError("WhatsApp webhook signature verification failed")
        project_dir = self.output_dir / f"whatsapp_webhook_{uuid.uuid4().hex[:12]}"
        project_dir.mkdir(parents=True, exist_ok=True)
        webhook_path = project_dir / "webhook.json"
        webhook_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        messages = self._extract_webhook_messages(payload)
        recorded: list[dict[str, object]] = []
        for message in messages:
            message_path = project_dir / f"message_{len(recorded) + 1}.txt"
            text = str(message.get("text", "")).strip()
            message_path.write_text(text + "\n", encoding="utf-8")
            manifest_path = project_dir / f"manifest_{len(recorded) + 1}.json"
            manifest = {
                "kind": "whatsapp_inbound_message",
                "status": "received",
                "provider": "whatsapp",
                "direction": "inbound",
                "contact": message.get("from", ""),
                "message_id": message.get("message_id", ""),
                "timestamp": message.get("timestamp", ""),
                "message_type": message.get("message_type", ""),
                "text": text,
                "message_path": str(message_path),
                "webhook_path": str(webhook_path),
            }
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
            row = self._record_message(
                direction="inbound",
                contact=str(message.get("from", "")),
                text=text,
                source="whatsapp_webhook",
                manifest_path=manifest_path,
                message_path=message_path,
                metadata=manifest,
            )
            recorded.append(row)
        return {
            "status": "received",
            "provider": "whatsapp",
            "webhook_path": str(webhook_path),
            "received_count": len(recorded),
            "messages": recorded,
        }

    def search_messages(self, query: str = "", *, limit: int = 20, direction: str = "all") -> dict[str, object]:
        limit = max(1, min(int(limit or 20), 200))
        direction = (direction or "all").strip().casefold()
        query = " ".join(str(query or "").casefold().split())
        rows = self._read_index()
        filtered: list[dict[str, object]] = []
        for row in reversed(rows):
            if direction != "all" and str(row.get("direction", "")).casefold() != direction:
                continue
            haystack = " ".join(
                str(row.get(key, ""))
                for key in ("direction", "contact", "text", "source", "message_id", "timestamp")
            ).casefold()
            if query and query not in haystack:
                continue
            filtered.append(row)
            if len(filtered) >= limit:
                break
        return {
            "status": "ok",
            "provider": "whatsapp",
            "count": len(filtered),
            "messages": filtered,
            "index_path": str(self.index_path),
        }

    def verify_signature(self, raw_body: bytes, signature: str) -> bool:
        secret = self._app_secret()
        if not secret:
            return True
        if not signature.startswith("sha256="):
            return False
        expected = "sha256=" + hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def _normalize_recipient(self, to: str) -> str:
        recipient = re.sub(r"[^\d+]", "", str(to).strip())
        if recipient.startswith("+"):
            recipient = recipient[1:]
        if not re.fullmatch(r"\d{8,15}", recipient):
            raise ValueError("WhatsApp recipient must be an international phone number, for example +94771234567")
        return recipient

    def _clean_message(self, message: str) -> str:
        clean_message = str(message).strip()
        if not clean_message:
            raise ValueError("WhatsApp message is required")
        if len(clean_message) > 4096:
            raise ValueError("WhatsApp message is too long; keep it under 4096 characters")
        return clean_message

    def _extract_webhook_messages(self, payload: dict[str, object]) -> list[dict[str, object]]:
        found: list[dict[str, object]] = []
        entries = payload.get("entry", [])
        if not isinstance(entries, list):
            return found
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            changes = entry.get("changes", [])
            if not isinstance(changes, list):
                continue
            for change in changes:
                if not isinstance(change, dict):
                    continue
                value = change.get("value", {})
                if not isinstance(value, dict):
                    continue
                messages = value.get("messages", [])
                if not isinstance(messages, list):
                    continue
                for item in messages:
                    if not isinstance(item, dict):
                        continue
                    message_type = str(item.get("type", "unknown"))
                    text = ""
                    if message_type == "text" and isinstance(item.get("text"), dict):
                        text = str(item["text"].get("body", ""))
                    else:
                        text = f"[{message_type} message received]"
                    found.append(
                        {
                            "from": str(item.get("from", "")),
                            "message_id": str(item.get("id", "")),
                            "timestamp": str(item.get("timestamp", "")),
                            "message_type": message_type,
                            "text": text,
                        }
                    )
        return found

    def _record_message(
        self,
        *,
        direction: str,
        contact: str,
        text: str,
        source: str,
        manifest_path: Path,
        message_path: Path,
        metadata: dict[str, object] | None = None,
    ) -> dict[str, object]:
        row = {
            "id": uuid.uuid4().hex,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "provider": "whatsapp",
            "direction": direction,
            "contact": contact,
            "text": text,
            "source": source,
            "manifest_path": str(manifest_path),
            "message_path": str(message_path),
            "message_id": str((metadata or {}).get("message_id", "")),
            "timestamp": str((metadata or {}).get("timestamp", "")),
        }
        self.output_dir.mkdir(parents=True, exist_ok=True)
        with self.index_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        return row

    def _read_index(self) -> list[dict[str, object]]:
        if not self.index_path.exists():
            return []
        rows: list[dict[str, object]] = []
        for line in self.index_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
        return rows

    def _token(self) -> str:
        return os.environ.get("WHATSAPP_CLOUD_TOKEN", "").strip()

    def _phone_number_id(self) -> str:
        return os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "").strip()

    def _webhook_verify_token(self) -> str:
        return os.environ.get("WHATSAPP_WEBHOOK_VERIFY_TOKEN", "").strip()

    def _app_secret(self) -> str:
        return os.environ.get("WHATSAPP_APP_SECRET", "").strip()


class AdvancedVideoSongRenderer:
    """Render a cinematic, audio-directed video from supplied visual assets."""

    ASPECTS = {"16:9": (1280, 720), "9:16": (720, 1280), "1:1": (1080, 1080)}
    CAMERAS = (
        "slow_push",
        "pan_left_to_right",
        "slow_pull",
        "pan_right_to_left",
        "floating_drift",
        "tilt_up",
    )
    SHOTS = (
        "wide establishing shot",
        "medium performance shot",
        "intimate close-up",
        "profile detail shot",
        "low-angle hero shot",
        "overhead atmospheric detail",
    )

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir.expanduser().resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def render(
        self,
        audio: Path,
        images: List[Path],
        prompt: str,
        lyrics: str = "",
        aspect: str = "16:9",
        max_duration_seconds: int = 90,
        consent: bool = False,
    ) -> AdvancedVideoSongProject:
        if not consent:
            raise PermissionError("Advanced video rendering requires consent/rights for the audio, people, and images")
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            raise RuntimeError("Advanced video rendering requires ffmpeg and ffprobe")
        audio_path = audio.expanduser().resolve()
        if not audio_path.exists() or audio_path.suffix.casefold() not in LocalMusicVideoRenderer.AUDIO_SUFFIXES:
            raise ValueError("A supported local audio file is required")
        image_paths = [path.expanduser().resolve() for path in images]
        if not image_paths:
            raise ValueError("At least one scene image is required")
        for image_path in image_paths:
            if not image_path.exists():
                raise FileNotFoundError(f"Scene image does not exist: {image_path}")
            if image_path.suffix.casefold() not in LocalImageMusicVideoRenderer.IMAGE_SUFFIXES:
                raise ValueError("Scene images must be jpg, jpeg, png, or webp files")
        prompt = " ".join(prompt.strip().split())
        if not prompt:
            raise ValueError("A movie or music-video prompt is required")
        if aspect not in self.ASPECTS:
            raise ValueError(f"Aspect must be one of: {', '.join(sorted(self.ASPECTS))}")

        project_dir = self.output_dir / f"advanced_video_song_{uuid.uuid4().hex[:12]}"
        project_dir.mkdir(parents=True, exist_ok=True)
        output_path = project_dir / "output_advanced_video_song.mp4"
        manifest_path = project_dir / "manifest.json"
        storyboard_path = project_dir / "storyboard.md"
        audio_analysis_path = project_dir / "audio_analysis.json"
        prompt_pack_path = project_dir / "scene_prompt_pack.md"
        duration = min(self._duration(audio_path), max(4.0, min(float(max_duration_seconds), 900.0)))
        scene_count = max(3, min(48, math.ceil(duration / 6.0)))
        scene_length = duration / scene_count
        timeline = [
            {
                "index": index + 1,
                "start": round(index * scene_length, 3),
                "end": round(duration if index == scene_count - 1 else (index + 1) * scene_length, 3),
            }
            for index in range(scene_count)
        ]
        analysis = self._audio_analysis(audio_path, timeline)
        scenes = self._scene_plan(prompt, lyrics, image_paths, analysis)
        audio_analysis_path.write_text(json.dumps({"duration_seconds": duration, "segments": analysis}, indent=2), encoding="utf-8")
        storyboard_path.write_text(self._storyboard(prompt, aspect, scenes), encoding="utf-8")
        prompt_pack_path.write_text(self._prompt_pack(prompt, aspect, scenes), encoding="utf-8")
        self._render(audio_path, image_paths, scenes, output_path, aspect)
        manifest = {
            "kind": "advanced_local_video_song",
            "status": "rendered",
            "audio": str(audio_path),
            "images": [str(path) for path in image_paths],
            "prompt": prompt,
            "lyrics_supplied": bool(lyrics.strip()),
            "aspect": aspect,
            "resolution": f"{self.ASPECTS[aspect][0]}x{self.ASPECTS[aspect][1]}",
            "duration_seconds": duration,
            "scene_count": scene_count,
            "scenes": scenes,
            "audio_analysis": str(audio_analysis_path),
            "storyboard": str(storyboard_path),
            "scene_prompt_pack": str(prompt_pack_path),
            "output": str(output_path),
            "renderer": "ffmpeg_cinematic_scene_engine",
            "output_metadata": LipSyncPlanner(project_dir)._media_metadata(output_path),
            "capability_truth": {
                "camera_motion": "Rendered pan, tilt, push, pull, and drift from supplied assets.",
                "camera_angles": "Shot-angle prompts are generated, but a still image cannot reveal a genuinely new viewpoint.",
                "emotion": "Emotion directs pacing and color treatment; it does not alter a person's facial expression without a neural backend.",
                "pitch": "Pitch activity is a zero-crossing-rate proxy used for editing energy, not musical-note transcription.",
                "lip_sync": "Not applied by this renderer. Use the neural lip-sync endpoint with an installed SadTalker backend.",
            },
            "safety": [
                "Use only songs, faces, voices, and images you own or have permission to use.",
                "Label synthetic or AI-assisted performance footage when sharing it.",
            ],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return AdvancedVideoSongProject(
            project_dir,
            output_path,
            manifest_path,
            storyboard_path,
            audio_analysis_path,
            prompt_pack_path,
        )

    def _duration(self, audio_path: Path) -> float:
        metadata = LipSyncPlanner(self.output_dir)._media_metadata(audio_path)
        try:
            return max(4.0, float((metadata.get("format") or {}).get("duration") or 30.0))
        except (TypeError, ValueError):
            return 30.0

    def _audio_analysis(self, audio_path: Path, timeline: List[Dict[str, object]]) -> List[Dict[str, object]]:
        rows: List[Dict[str, object]] = []
        for segment in timeline:
            start = float(segment["start"])
            length = max(0.1, float(segment["end"]) - start)
            rms_db = -24.0
            peak_db = -10.0
            zero_crossing_rate = 0.04
            try:
                result = subprocess.run(
                    [
                        "ffmpeg", "-hide_banner", "-ss", f"{start:.3f}", "-t", f"{length:.3f}",
                        "-i", str(audio_path), "-af", "astats=metadata=0:reset=0", "-f", "null", "-",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=max(30, int(length) + 20),
                    check=False,
                )
                rms_values = re.findall(r"RMS level dB:\s*(-?[\d.]+)", result.stderr)
                peak_values = re.findall(r"Peak level dB:\s*(-?[\d.]+)", result.stderr)
                crossing_values = re.findall(r"Zero crossings rate:\s*([\d.]+)", result.stderr)
                if rms_values:
                    rms_db = float(rms_values[-1])
                if peak_values:
                    peak_db = float(peak_values[-1])
                if crossing_values:
                    zero_crossing_rate = float(crossing_values[-1])
            except (OSError, subprocess.SubprocessError, ValueError):
                pass
            energy = round(max(0.0, min(1.0, (rms_db + 42.0) / 36.0)), 3)
            pitch_activity = round(max(0.0, min(1.0, zero_crossing_rate / 0.12)), 3)
            rows.append(
                {
                    **segment,
                    "rms_db": round(rms_db, 3),
                    "peak_db": round(peak_db, 3),
                    "zero_crossing_rate": round(zero_crossing_rate, 6),
                    "energy": energy,
                    "pitch_activity": pitch_activity,
                }
            )
        return rows

    def _scene_plan(
        self,
        prompt: str,
        lyrics: str,
        images: List[Path],
        analysis: List[Dict[str, object]],
    ) -> List[Dict[str, object]]:
        lyric_lines = [line.strip() for line in lyrics.splitlines() if line.strip()]
        lower_prompt = prompt.casefold()
        if any(word in lower_prompt for word in {"romantic", "love", "tender"}):
            base_emotion = "romance"
        elif any(word in lower_prompt for word in {"sad", "loss", "lonely", "melancholy"}):
            base_emotion = "sadness"
        elif any(word in lower_prompt for word in {"dark", "danger", "thriller", "angry"}):
            base_emotion = "tension"
        elif any(word in lower_prompt for word in {"happy", "joy", "celebration", "dance"}):
            base_emotion = "joy"
        else:
            base_emotion = "cinematic"
        preferred_shot = self._prompt_shot(lower_prompt)
        preferred_camera = self._prompt_camera(lower_prompt)
        effects = self._prompt_effects(lower_prompt)
        scenes: List[Dict[str, object]] = []
        for index, audio_row in enumerate(analysis):
            energy = float(audio_row["energy"])
            pitch_activity = float(audio_row["pitch_activity"])
            emotion = "intensity" if energy >= 0.72 else "reflection" if energy <= 0.30 else base_emotion
            shot_index = (index + (2 if pitch_activity > 0.60 else 0)) % len(self.SHOTS)
            camera_index = (index + (1 if energy > 0.60 else 0)) % len(self.CAMERAS)
            lyric = lyric_lines[index % len(lyric_lines)] if lyric_lines else ""
            scene_effects = list(effects)
            if energy > 0.68 or pitch_activity > 0.68:
                scene_effects.append("beat_pulse")
            if index == 0:
                scene_effects.append("scene_title")
            if lyric:
                scene_effects.append("lyric_caption")
            scene = {
                **audio_row,
                "image": str(images[index % len(images)]),
                "emotion": emotion,
                "shot": preferred_shot or self.SHOTS[shot_index],
                "camera": preferred_camera or self.CAMERAS[camera_index],
                "edit_pace": "fast" if energy > 0.68 or pitch_activity > 0.68 else "slow" if energy < 0.35 else "medium",
                "lyric": lyric,
                "effects": sorted(set(scene_effects)),
                "overlay_text": lyric or f"Scene {audio_row['index']} - {emotion}",
            }
            scene["asset_prompt"] = (
                f"{prompt}, scene {scene['index']}, {scene['shot']}, {emotion} human emotion, "
                f"cinematic lighting, coherent character and wardrobe, realistic film still, no text, no watermark"
            )
            scenes.append(scene)
        return scenes

    def _render(self, audio: Path, images: List[Path], scenes: List[Dict[str, object]], output: Path, aspect: str) -> None:
        width, height = self.ASPECTS[aspect]
        clips_dir = output.parent / "scene_clips"
        clips_dir.mkdir(parents=True, exist_ok=True)
        clips: List[Path] = []
        for index, scene in enumerate(scenes):
            duration = max(0.5, float(scene["end"]) - float(scene["start"]))
            clip = clips_dir / f"scene_{index + 1:03d}.mp4"
            visual_filter = self._visual_filter(width, height, duration, scene)
            command = [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-loop", "1", "-framerate", "30",
                "-i", str(images[index % len(images)]), "-t", f"{duration:.3f}", "-vf", visual_filter,
                "-an", "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-pix_fmt", "yuv420p", str(clip),
            ]
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=max(180, int(duration * 20)),
            )
            if result.returncode != 0 and "drawtext" in visual_filter:
                command[command.index("-vf") + 1] = self._visual_filter(width, height, duration, scene, include_text=False)
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=max(180, int(duration * 20)),
                )
            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, command, result.stdout, result.stderr)
            clips.append(clip)
        concat_path = output.parent / "scene_clips.txt"
        concat_path.write_text("".join(f"file '{clip.as_posix()}'\n" for clip in clips), encoding="utf-8")
        visuals = output.parent / "visual_track.mp4"
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_path), "-c", "copy", str(visuals)],
            check=True,
            capture_output=True,
            text=True,
            timeout=900,
        )
        total_duration = float(scenes[-1]["end"])
        subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(visuals), "-i", str(audio),
                "-t", f"{total_duration:.3f}", "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(output),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=900,
        )

    def _visual_filter(self, width: int, height: int, duration: float, scene: Dict[str, object], include_text: bool = True) -> str:
        camera = str(scene["camera"])
        emotion = str(scene["emotion"])
        effects = set(str(effect) for effect in scene.get("effects", []))
        large_width = int(math.ceil(width * 1.18 / 2) * 2)
        large_height = int(math.ceil(height * 1.18 / 2) * 2)
        if camera == "slow_push":
            motion = (
                f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},"
                f"zoompan=z='min(1+on*0.0007,1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={width}x{height}:fps=30"
            )
        elif camera == "slow_pull":
            motion = (
                f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},"
                f"zoompan=z='max(1.12-on*0.0007,1.0)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={width}x{height}:fps=30"
            )
        else:
            if camera == "pan_left_to_right":
                x, y = f"(iw-ow)*t/{duration:.3f}", "(ih-oh)/2"
            elif camera == "pan_right_to_left":
                x, y = f"(iw-ow)*(1-t/{duration:.3f})", "(ih-oh)/2"
            elif camera == "tilt_up":
                x, y = "(iw-ow)/2", f"(ih-oh)*(1-t/{duration:.3f})"
            else:
                x, y = "(iw-ow)*(0.5+0.42*sin(t*0.35))", "(ih-oh)*(0.5+0.32*cos(t*0.27))"
            motion = (
                f"scale={large_width}:{large_height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height}:x='{x}':y='{y}'"
            )
        grade = {
            "joy": "eq=contrast=1.05:brightness=0.03:saturation=1.28",
            "romance": "eq=contrast=0.98:brightness=0.03:saturation=1.12,colorbalance=rs=0.05:bs=-0.03",
            "sadness": "eq=contrast=0.96:brightness=-0.04:saturation=0.70,colorbalance=bs=0.08",
            "tension": "eq=contrast=1.20:brightness=-0.05:saturation=0.92,colorbalance=rs=0.07",
            "intensity": "eq=contrast=1.16:brightness=-0.02:saturation=1.18",
            "reflection": "eq=contrast=0.94:brightness=-0.01:saturation=0.82",
        }.get(emotion, "eq=contrast=1.06:brightness=-0.01:saturation=1.05")
        fade_out = max(0.0, duration - 0.22)
        filters = [motion, grade, "vignette=PI/5"]
        if "film_grain" in effects:
            filters.append("noise=alls=9:allf=t+u")
        if "light_leak" in effects:
            filters.append(f"drawbox=x=0:y=0:w=iw:h=ih:color=orange@0.10:t=fill:enable='lt(t,{min(duration, 1.8):.3f})'")
            filters.append("drawbox=x='iw*0.70':y=0:w='iw*0.30':h=ih:color=white@0.08:t=fill")
        if "beat_pulse" in effects:
            filters.append("drawbox=x=0:y=0:w=iw:h=ih:color=white@0.10:t=fill:enable='lt(mod(t,0.55),0.08)'")
        if "cinematic_bars" in effects:
            bar = max(24, height // 12)
            filters.append(f"drawbox=x=0:y=0:w=iw:h={bar}:color=black@0.88:t=fill")
            filters.append(f"drawbox=x=0:y=ih-{bar}:w=iw:h={bar}:color=black@0.88:t=fill")
        if include_text and ("lyric_caption" in effects or "scene_title" in effects):
            text = self._ffmpeg_text(str(scene.get("overlay_text", ""))[:72])
            y = "h-th-46" if "lyric_caption" in effects else "44"
            filters.append(
                "drawtext="
                f"text='{text}':x=(w-text_w)/2:y={y}:fontsize={max(24, width // 34)}:"
                "fontcolor=white@0.92:box=1:boxcolor=black@0.45:boxborderw=18"
            )
        filters.extend([f"fade=t=in:st=0:d=0.18", f"fade=t=out:st={fade_out:.3f}:d=0.22", "format=yuv420p"])
        return ",".join(filters)

    def _prompt_shot(self, lower_prompt: str) -> str:
        if "close up" in lower_prompt or "close-up" in lower_prompt:
            return "intimate close-up"
        if "low angle" in lower_prompt or "hero" in lower_prompt:
            return "low-angle hero shot"
        if "overhead" in lower_prompt or "drone" in lower_prompt or "top shot" in lower_prompt:
            return "overhead atmospheric detail"
        if "profile" in lower_prompt or "side angle" in lower_prompt:
            return "profile detail shot"
        if "wide" in lower_prompt or "establishing" in lower_prompt:
            return "wide establishing shot"
        return ""

    def _prompt_camera(self, lower_prompt: str) -> str:
        if "zoom in" in lower_prompt or "push in" in lower_prompt or "slow push" in lower_prompt:
            return "slow_push"
        if "zoom out" in lower_prompt or "pull out" in lower_prompt or "slow pull" in lower_prompt:
            return "slow_pull"
        if "pan right" in lower_prompt:
            return "pan_left_to_right"
        if "pan left" in lower_prompt:
            return "pan_right_to_left"
        if "tilt up" in lower_prompt:
            return "tilt_up"
        if "float" in lower_prompt or "drift" in lower_prompt:
            return "floating_drift"
        return ""

    def _prompt_effects(self, lower_prompt: str) -> List[str]:
        effects = ["cinematic_bars"]
        if any(term in lower_prompt for term in {"film", "grain", "vintage", "movie", "cinematic"}):
            effects.append("film_grain")
        if any(term in lower_prompt for term in {"light leak", "dream", "romantic", "sunset", "glow"}):
            effects.append("light_leak")
        if any(term in lower_prompt for term in {"lyric", "caption", "karaoke", "song"}):
            effects.append("lyric_caption")
        return effects

    def _ffmpeg_text(self, text: str) -> str:
        return (
            text.replace("\\", "\\\\")
            .replace(":", "\\:")
            .replace(",", "\\,")
            .replace("'", "\\'")
            .replace("[", "\\[")
            .replace("]", "\\]")
        )

    def _storyboard(self, prompt: str, aspect: str, scenes: List[Dict[str, object]]) -> str:
        lines = ["# Advanced Video Song Storyboard", "", f"Creative direction: {prompt}", f"Aspect: {aspect}", ""]
        for scene in scenes:
            lines.extend(
                [
                    f"## Scene {scene['index']} ({scene['start']}s-{scene['end']}s)",
                    f"- Emotion: {scene['emotion']}",
                    f"- Shot: {scene['shot']}",
                    f"- Camera movement: {scene['camera']}",
                    f"- Edit pace: {scene['edit_pace']}",
                    f"- Energy: {scene['energy']}; pitch activity: {scene['pitch_activity']}",
                    f"- Lyric: {scene['lyric'] or '[not supplied]'}",
                    f"- Scene-generation prompt: {scene['asset_prompt']}",
                    "",
                ]
            )
        lines.extend(
            [
                "## Production Truth",
                "",
                "The local draft animates supplied stills with cinematic reframing and grading. True new viewpoints, actor performances, and facial emotion changes require generated or filmed scene assets.",
            ]
        )
        return "\n".join(lines) + "\n"

    def _prompt_pack(self, prompt: str, aspect: str, scenes: List[Dict[str, object]]) -> str:
        lines = ["# Scene Generation Prompt Pack", "", f"Continuity anchor: {prompt}", f"Delivery aspect: {aspect}", ""]
        for scene in scenes:
            lines.extend([f"## Scene {scene['index']}", "", str(scene["asset_prompt"]), ""])
        lines.extend(
            [
                "## Global Negative Prompt",
                "",
                "warped face, duplicate person, extra limbs, broken hands, inconsistent wardrobe, identity drift, flicker, unstable background, unreadable text, watermark",
                "",
            ]
        )
        return "\n".join(lines)


class OpenSourceVideoApiRenderer:
    """Adapter for open-source video generation APIs, starting with ComfyUI."""

    VIDEO_SUFFIXES = {".mp4", ".mov", ".webm", ".mkv", ".gif", ".webp"}

    @staticmethod
    def known_targets() -> List[OpenSourceVideoApiTarget]:
        return [
            OpenSourceVideoApiTarget(
                provider_id="comfyui_local",
                name="Local ComfyUI video workflow",
                backend="ComfyUI API",
                source_url="https://github.com/comfyanonymous/ComfyUI",
                base_url="http://127.0.0.1:8188",
                auth_env="",
                requires_cloud_allowed=False,
                requires_explicit_consent=True,
                purpose="Run local or user-hosted open video workflows such as Wan, HunyuanVideo, AnimateDiff, Mochi, or LTX.",
                safety_notes=[
                    "Use model checkpoints according to their licenses.",
                    "Use only images, likenesses, voices, and songs you own or have permission to use.",
                ],
            ),
            OpenSourceVideoApiTarget(
                provider_id="wan555_huggingface_space",
                name="WAN555 Hugging Face Space",
                backend="Gradio queue API",
                source_url="https://huggingface.co/spaces/kulkas2pintu/wan555/agents.md",
                base_url="https://kulkas2pintu-wan555.hf.space",
                auth_env="HF_TOKEN",
                requires_cloud_allowed=True,
                requires_explicit_consent=True,
                purpose="Generate animated video from a single image through an authorized Hugging Face Space endpoint.",
                safety_notes=[
                    "Do not upload private or sensitive images unless the user explicitly confirms cloud use.",
                    "Use official Gradio queue endpoints only; do not bypass login, quotas, CAPTCHA, or rate limits.",
                    "Treat uploaded files and generated outputs as third-party cloud processing.",
                ],
            ),
        ]

    def __init__(self, output_dir: Path | str, base_url: str = "http://127.0.0.1:8188"):
        self.output_dir = Path(output_dir).expanduser().resolve()
        self.base_url = base_url.rstrip("/")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def status(self) -> Dict[str, object]:
        discovered_workflows = self._discover_local_workflows()
        try:
            stats = self._json_get("/system_stats", timeout=5)
            objects = self._json_get("/object_info", timeout=10)
            return {
                "backend": "ComfyUI",
                "ready": True,
                "base_url": self.base_url,
                "system_stats": stats,
                "object_count": len(objects) if isinstance(objects, dict) else 0,
                "discovered_workflows": discovered_workflows,
                "notes": "Use an API-format ComfyUI workflow for Wan, Hunyuan, AnimateDiff, or another open video model.",
            }
        except Exception as error:
            return {
                "backend": "ComfyUI",
                "ready": False,
                "base_url": self.base_url,
                "error": str(error),
                "discovered_workflows": discovered_workflows,
                "install_hint": "Start ComfyUI with a video workflow backend, usually at http://127.0.0.1:8188.",
            }

    def _discover_local_workflows(self) -> List[str]:
        candidates: List[Path] = []
        roots = [
            self.output_dir,
            Path.home() / "Downloads",
        ]
        patterns = [
            "**/*ComfyUI*/example_workflows/*.json",
            "**/*comfy*/example_workflows/*.json",
            "**/*workflow*.json",
        ]
        seen: set[Path] = set()
        for root in roots:
            if not root.exists():
                continue
            for pattern in patterns:
                for path in root.glob(pattern):
                    if not path.is_file():
                        continue
                    resolved = path.expanduser().resolve()
                    if resolved in seen:
                        continue
                    seen.add(resolved)
                    candidates.append(resolved)
                    if len(candidates) >= 12:
                        return [str(item) for item in candidates]
        return [str(item) for item in candidates]

    def render(
        self,
        workflow: Path,
        prompt: str,
        image: Path | None = None,
        negative_prompt: str = "low quality, warped face, extra limbs, flicker, watermark, unreadable text",
        width: int = 832,
        height: int = 480,
        frames: int = 81,
        seed: int | None = None,
        timeout_seconds: int = 1800,
        consent: bool = False,
    ) -> OpenSourceVideoApiProject:
        if not consent:
            raise PermissionError("Open-source video API rendering requires consent/rights for prompts, people, images, and audio")
        workflow_path = workflow.expanduser().resolve()
        if not workflow_path.exists():
            raise FileNotFoundError(f"ComfyUI workflow JSON does not exist: {workflow_path}")
        prompt = " ".join(prompt.strip().split())
        if not prompt:
            raise ValueError("Prompt is required")
        project_dir = self.output_dir / f"open_video_api_{uuid.uuid4().hex[:12]}"
        project_dir.mkdir(parents=True, exist_ok=True)
        prompt_path = project_dir / "prompt.txt"
        copied_workflow_path = project_dir / "workflow_api.json"
        manifest_path = project_dir / "manifest.json"
        prompt_path.write_text(prompt + "\n", encoding="utf-8")
        workflow_data = json.loads(workflow_path.read_text(encoding="utf-8"))
        uploaded_image_name = ""
        if image is not None:
            image_path = image.expanduser().resolve()
            if not image_path.exists():
                raise FileNotFoundError(f"Input image does not exist: {image_path}")
            uploaded_image_name = self._upload_image(image_path)
        replacements = {
            "PROMPT": prompt,
            "POSITIVE_PROMPT": prompt,
            "NEGATIVE_PROMPT": negative_prompt,
            "IMAGE": uploaded_image_name,
            "IMAGE_NAME": uploaded_image_name,
            "WIDTH": int(width),
            "HEIGHT": int(height),
            "FRAMES": int(frames),
            "LENGTH": int(frames),
            "SEED": int(seed if seed is not None else time.time_ns() % 2_147_483_647),
        }
        patched_workflow = self._replace_placeholders(workflow_data, replacements)
        copied_workflow_path.write_text(json.dumps(patched_workflow, indent=2), encoding="utf-8")
        prompt_id = self._queue_prompt(patched_workflow)
        history = self._wait_for_history(prompt_id, timeout_seconds)
        output_ref = self._first_output_ref(history)
        if not output_ref:
            raise RuntimeError(f"ComfyUI finished but no video/image output was found for prompt {prompt_id}")
        suffix = Path(str(output_ref.get("filename", "output.mp4"))).suffix or ".mp4"
        output_path = project_dir / f"output_open_source_video{suffix}"
        output_path.write_bytes(self._view_output(output_ref))
        manifest = {
            "kind": "open_source_video_api",
            "status": "rendered",
            "backend": "ComfyUI",
            "base_url": self.base_url,
            "workflow": str(workflow_path),
            "patched_workflow": str(copied_workflow_path),
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "input_image_uploaded": uploaded_image_name,
            "width": width,
            "height": height,
            "frames": frames,
            "seed": replacements["SEED"],
            "prompt_id": prompt_id,
            "output_ref": output_ref,
            "output": str(output_path),
            "safety": [
                "Use open-source model checkpoints according to their license.",
                "Use only images, likenesses, voices, and songs you own or have permission to use.",
                "Label generated or AI-assisted video when sharing.",
            ],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return OpenSourceVideoApiProject(project_dir, output_path, manifest_path, copied_workflow_path, prompt_path)

    def _queue_prompt(self, workflow: dict) -> str:
        body = json.dumps({"prompt": workflow, "client_id": uuid.uuid4().hex}).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/prompt",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        prompt_id = payload.get("prompt_id")
        if not prompt_id:
            raise RuntimeError(f"ComfyUI did not return prompt_id: {payload}")
        return str(prompt_id)

    def _wait_for_history(self, prompt_id: str, timeout_seconds: int) -> dict:
        deadline = time.time() + max(10, timeout_seconds)
        while time.time() < deadline:
            history = self._json_get(f"/history/{urllib.parse.quote(prompt_id)}", timeout=20)
            if prompt_id in history:
                return history[prompt_id]
            time.sleep(2)
        raise TimeoutError(f"ComfyUI prompt did not finish within {timeout_seconds}s: {prompt_id}")

    def _first_output_ref(self, history: dict) -> dict | None:
        outputs = history.get("outputs", {}) if isinstance(history, dict) else {}
        for node_output in outputs.values():
            for key in ["videos", "gifs", "images"]:
                for item in node_output.get(key, []) if isinstance(node_output, dict) else []:
                    filename = item.get("filename", "")
                    if filename and (Path(filename).suffix.casefold() in self.VIDEO_SUFFIXES or key == "images"):
                        return {
                            "filename": filename,
                            "subfolder": item.get("subfolder", ""),
                            "type": item.get("type", "output"),
                            "kind": key,
                        }
        return None

    def _view_output(self, output_ref: dict) -> bytes:
        params = urllib.parse.urlencode(
            {
                "filename": output_ref.get("filename", ""),
                "subfolder": output_ref.get("subfolder", ""),
                "type": output_ref.get("type", "output"),
            }
        )
        with urllib.request.urlopen(f"{self.base_url}/view?{params}", timeout=120) as response:
            return response.read()

    def _json_get(self, path: str, timeout: int = 20) -> dict:
        with urllib.request.urlopen(f"{self.base_url}{path}", timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def _upload_image(self, image_path: Path) -> str:
        boundary = f"----gima{uuid.uuid4().hex}"
        filename = image_path.name
        mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        data = image_path.read_bytes()
        body = b"".join(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'.encode(),
                f"Content-Type: {mime}\r\n\r\n".encode(),
                data,
                b"\r\n",
                f"--{boundary}\r\n".encode(),
                b'Content-Disposition: form-data; name="type"\r\n\r\ninput\r\n',
                f"--{boundary}--\r\n".encode(),
            ]
        )
        request = urllib.request.Request(
            f"{self.base_url}/upload/image",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return str(payload.get("name") or payload.get("filename") or filename)

    def _replace_placeholders(self, value, replacements: Dict[str, object]):
        if isinstance(value, dict):
            return {key: self._replace_placeholders(item, replacements) for key, item in value.items()}
        if isinstance(value, list):
            return [self._replace_placeholders(item, replacements) for item in value]
        if isinstance(value, str):
            text = value
            for key, replacement in replacements.items():
                text = text.replace(f"{{{{{key}}}}}", str(replacement))
            return text
        return value


class OpenRouterVideoGenerator:
    """OpenRouter async video generation adapter, including Veo models."""

    endpoint = "https://openrouter.ai/api/v1"

    def __init__(self, output_dir: Path | str):
        self.output_dir = Path(output_dir).expanduser().resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def models(self) -> dict:
        request = urllib.request.Request(
            f"{self.endpoint}/videos/models",
            headers=self._headers(),
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        models = payload.get("data") if isinstance(payload, dict) else []
        if not isinstance(models, list):
            models = []
        return {
            "provider": "openrouter",
            "count": len(models),
            "models": models,
            "veo_models": [model for model in models if "veo" in str(model.get("id", "")).casefold()],
        }

    def generate(
        self,
        prompt: str,
        *,
        model: str = "google/veo-3.1",
        aspect_ratio: str = "16:9",
        duration: int = 8,
        resolution: str = "720p",
        generate_audio: bool = True,
        timeout_seconds: int = 900,
        consent: bool = False,
    ) -> dict[str, object]:
        prompt = " ".join(prompt.strip().split())
        if not consent:
            raise PermissionError("OpenRouter/Veo video generation may spend credits and requires explicit user confirmation")
        require_cloud_allowed("OpenRouter/Veo video generation")
        if not prompt:
            raise ValueError("Video prompt is required")
        project_dir = self.output_dir / f"openrouter_video_{uuid.uuid4().hex[:12]}"
        project_dir.mkdir(parents=True, exist_ok=True)
        prompt_path = project_dir / "prompt.txt"
        manifest_path = project_dir / "manifest.json"
        output_path = project_dir / "output_openrouter_video.mp4"
        prompt_path.write_text(prompt + "\n", encoding="utf-8")
        payload = {
            "model": model,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "duration": int(duration),
            "resolution": resolution,
            "generate_audio": bool(generate_audio),
        }
        submit = self._json_request("/videos", payload, timeout=60)
        job_id = str(submit.get("id") or "").strip()
        polling_url = str(submit.get("polling_url") or "").strip()
        if not job_id and polling_url:
            job_id = polling_url.rstrip("/").split("/")[-1]
        if not job_id:
            raise RuntimeError(f"OpenRouter did not return a video job id: {submit}")
        status_payload = self._poll_video_job(job_id, timeout_seconds)
        unsigned_urls = status_payload.get("unsigned_urls") or []
        if not unsigned_urls:
            raise RuntimeError(f"OpenRouter video job completed without a downloadable URL: {status_payload}")
        self._download_video(str(unsigned_urls[0]), output_path)
        manifest = {
            "kind": "openrouter_video_generation",
            "status": "rendered",
            "provider": "openrouter",
            "model": model,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "duration": int(duration),
            "resolution": resolution,
            "generate_audio": bool(generate_audio),
            "job": submit,
            "final_status": status_payload,
            "output": str(output_path),
            "prompt_path": str(prompt_path),
            "safety": [
                "This cloud video job can spend OpenRouter credits.",
                "Use only prompts, likenesses, voices, songs, images, and references you own or have permission to use.",
                "Label generated or AI-assisted video when sharing.",
            ],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        return {
            "output_path": str(output_path),
            "manifest_path": str(manifest_path),
            "prompt_path": str(prompt_path),
            "job_id": job_id,
            "generation_id": status_payload.get("generation_id") or submit.get("generation_id"),
            "model": model,
            "status": status_payload.get("status", "completed"),
            "usage": status_payload.get("usage", {}),
        }

    def _poll_video_job(self, job_id: str, timeout_seconds: int) -> dict:
        deadline = time.time() + max(30, timeout_seconds)
        last: dict = {}
        while time.time() < deadline:
            request = urllib.request.Request(
                f"{self.endpoint}/videos/{urllib.parse.quote(job_id)}",
                headers=self._headers(),
                method="GET",
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                last = json.loads(response.read().decode("utf-8"))
            status = str(last.get("status", "")).casefold()
            if status == "completed":
                return last
            if status in {"failed", "cancelled", "canceled", "error"}:
                raise RuntimeError(f"OpenRouter video job failed: {last}")
            time.sleep(5)
        raise TimeoutError(f"OpenRouter video job did not finish within {timeout_seconds}s: {job_id}. Last status: {last}")

    def _json_request(self, path: str, payload: dict, timeout: int) -> dict:
        request = urllib.request.Request(
            f"{self.endpoint}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(content_type=True),
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def _download_video(self, url: str, output_path: Path) -> None:
        request = urllib.request.Request(url, headers={"User-Agent": "Gima local assistant/0.1"})
        with urllib.request.urlopen(request, timeout=180) as response:
            output_path.write_bytes(response.read())

    def _headers(self, *, content_type: bool = False) -> dict[str, str]:
        api_key = os.environ.get("OPENROUTER_VIDEO_API_KEY", "").strip() or os.environ.get("OPENROUTER_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENROUTER_VIDEO_API_KEY or OPENROUTER_API_KEY is not set. Save the OpenRouter/Veo key in API Bindings first.")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "HTTP-Referer": "http://127.0.0.1:8787",
            "X-Title": "Gima local assistant",
        }
        if content_type:
            headers["Content-Type"] = "application/json"
        return headers


class HuggingFaceVideoGenerator:
    """Hugging Face InferenceClient text-to-video adapter."""

    def __init__(self, output_dir: Path | str):
        self.output_dir = Path(output_dir).expanduser().resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def status(self) -> dict[str, object]:
        return {
            "provider": "huggingface",
            "backend": "huggingface_hub.InferenceClient.text_to_video",
            "ready": bool(self._hf_token()),
            "cloud_allowed": cloud_allowed(),
            "default_provider": os.environ.get("GIMA_HF_VIDEO_PROVIDER", "replicate"),
            "default_model": os.environ.get("GIMA_HF_VIDEO_MODEL", "Wan-AI/Wan2.2-TI2V-5B"),
            "env": ["HF_TOKEN or HUGGINGFACE_API_KEY", "CLOUD_ALLOWED=true"],
            "safety": [
                "Requires explicit consent because provider inference may spend credits.",
                "Use only prompts, images, voices, songs, likenesses, and references you own or have permission to use.",
                "Gima stores output and manifest locally; it never exposes the token to the browser.",
            ],
        }

    def generate(
        self,
        prompt: str,
        *,
        model: str = "Wan-AI/Wan2.2-TI2V-5B",
        provider: str = "replicate",
        timeout_seconds: int = 900,
        consent: bool = False,
    ) -> dict[str, object]:
        prompt = " ".join(prompt.strip().split())
        if not consent:
            raise PermissionError("Hugging Face video generation can spend credits and requires explicit consent")
        require_cloud_allowed("Hugging Face text-to-video generation")
        if not prompt:
            raise ValueError("Video prompt is required")
        token = self._hf_token()
        if not token:
            raise RuntimeError("HF_TOKEN or HUGGINGFACE_API_KEY is not set")
        project_dir = self.output_dir / f"huggingface_video_{uuid.uuid4().hex[:12]}"
        project_dir.mkdir(parents=True, exist_ok=True)
        output_path = project_dir / "output_huggingface_video.mp4"
        prompt_path = project_dir / "prompt.txt"
        manifest_path = project_dir / "manifest.json"
        prompt_path.write_text(prompt + "\n", encoding="utf-8")

        try:
            hub = importlib.import_module("huggingface_hub")
        except ImportError as error:
            raise RuntimeError("Install huggingface_hub to use Hugging Face video generation: pip install huggingface_hub") from error
        client = hub.InferenceClient(provider=provider, api_key=token)
        video = client.text_to_video(prompt, model=model)
        self._write_video_result(video, output_path, timeout_seconds)
        manifest = {
            "kind": "huggingface_text_to_video",
            "status": "generated",
            "provider": "huggingface",
            "inference_provider": provider,
            "model": model,
            "prompt": prompt,
            "output": str(output_path),
            "prompt_path": str(prompt_path),
            "response_type": type(video).__name__,
            "safety": [
                "This cloud video job can spend Hugging Face/provider credits.",
                "Use only prompts, likenesses, voices, songs, images, and references you own or have permission to use.",
                "Label generated or AI-assisted video when sharing.",
            ],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        return {
            "status": "generated",
            "provider": "huggingface",
            "inference_provider": provider,
            "model": model,
            "output_path": str(output_path),
            "manifest_path": str(manifest_path),
            "prompt_path": str(prompt_path),
        }

    def _write_video_result(self, video: object, output_path: Path, timeout_seconds: int) -> None:
        if isinstance(video, bytes):
            output_path.write_bytes(video)
            return
        if isinstance(video, bytearray):
            output_path.write_bytes(bytes(video))
            return
        if hasattr(video, "read"):
            data = video.read()
            if isinstance(data, str):
                data = data.encode("utf-8")
            output_path.write_bytes(bytes(data))
            return
        if isinstance(video, (str, Path)):
            value = str(video)
            if value.startswith(("https://", "http://")):
                request = urllib.request.Request(value, headers={"User-Agent": "Gima local assistant/0.1"})
                with urllib.request.urlopen(request, timeout=max(30, timeout_seconds)) as response:
                    output_path.write_bytes(response.read())
                return
            source = Path(value).expanduser().resolve()
            if source.exists() and source.is_file():
                shutil.copy2(source, output_path)
                return
        if isinstance(video, dict):
            payload = video
            for key in ("video", "video_base64", "mp4", "data"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    text = value.strip()
                    if text.startswith("data:") and "," in text:
                        text = text.split(",", 1)[1]
                    try:
                        output_path.write_bytes(base64.b64decode(text))
                        return
                    except Exception:
                        pass
            for key in ("url", "video_url", "download_url", "file"):
                value = payload.get(key)
                if isinstance(value, str) and value.startswith(("https://", "http://")):
                    request = urllib.request.Request(value, headers={"User-Agent": "Gima local assistant/0.1"})
                    with urllib.request.urlopen(request, timeout=max(30, timeout_seconds)) as response:
                        output_path.write_bytes(response.read())
                    return
        raise RuntimeError(f"Hugging Face text_to_video returned unsupported type: {type(video).__name__}")

    def _hf_token(self) -> str:
        return os.environ.get("HF_TOKEN", "").strip() or os.environ.get("HUGGINGFACE_API_KEY", "").strip()


class OpenRouterSpeechGenerator:
    """OpenRouter text-to-speech adapter, including Microsoft MAI Voice 2."""

    endpoint = "https://openrouter.ai/api/v1/audio/speech"

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        text: str,
        *,
        model: str = "microsoft/mai-voice-2",
        voice: str = "en-US-Harper:MAI-Voice-2",
        response_format: str = "mp3",
        speed: float = 1.0,
        style: str = "cheerful",
        styledegree: float = 1.0,
        consent: bool = False,
    ) -> dict[str, Any]:
        clean_text = " ".join(text.strip().split())
        if not clean_text:
            raise ValueError("Speech text is required")
        if not consent:
            raise PermissionError("OpenRouter speech generation can spend credits and requires explicit user confirmation")
        require_cloud_allowed("OpenRouter text-to-speech generation")
        fmt = response_format.strip().casefold() or "mp3"
        if fmt not in {"mp3", "pcm"}:
            raise ValueError("response_format must be mp3 or pcm")
        project_dir = self.output_dir / f"openrouter_speech_{uuid.uuid4().hex[:12]}"
        project_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "model": model,
            "input": clean_text,
            "voice": voice,
            "response_format": fmt,
            "speed": max(0.5, min(float(speed), 2.0)),
            "provider": {
                "options": {
                    "azure": {
                        "style": style,
                        "styledegree": max(0.0, min(float(styledegree), 2.0)),
                    }
                }
            },
        }
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key()}",
                "Content-Type": "application/json",
                "Accept": "audio/mpeg, audio/pcm, application/json",
                "HTTP-Referer": "http://127.0.0.1:8787",
                "X-Title": "Gima local assistant",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            content_type = response.headers.get("Content-Type", "")
            generation_id = response.headers.get("X-Generation-Id", "")
            body = response.read()
        if not content_type.startswith("audio/"):
            detail = body.decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"OpenRouter speech did not return audio: {detail}")
        suffix = ".mp3" if fmt == "mp3" else ".pcm"
        output_path = project_dir / f"speech{suffix}"
        manifest_path = project_dir / "manifest.json"
        prompt_path = project_dir / "speech_text.txt"
        output_path.write_bytes(body)
        prompt_path.write_text(clean_text, encoding="utf-8")
        manifest = {
            "kind": "openrouter_text_to_speech",
            "provider": "openrouter",
            "model": model,
            "voice": voice,
            "response_format": fmt,
            "speed": payload["speed"],
            "style": style,
            "styledegree": payload["provider"]["options"]["azure"]["styledegree"],
            "output_path": str(output_path),
            "prompt_path": str(prompt_path),
            "generation_id": generation_id,
            "content_type": content_type,
            "safety": [
                "Cloud speech generation may spend OpenRouter credits.",
                "Do not synthesize speech impersonating a real private person without permission.",
                "Use only text you have rights to publish.",
            ],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return {
            "status": "generated",
            "output_path": str(output_path),
            "manifest_path": str(manifest_path),
            "prompt_path": str(prompt_path),
            "generation_id": generation_id,
            "model": model,
            "voice": voice,
            "content_type": content_type,
        }

    def _api_key(self) -> str:
        api_key = os.environ.get("OPENROUTER_SPEECH_API_KEY", "").strip() or os.environ.get("OPENROUTER_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENROUTER_SPEECH_API_KEY or OPENROUTER_API_KEY is not set. Save the OpenRouter/MAI key in API Bindings first.")
        return api_key


class ExternalMusicApiGenerator:
    """Cloud music adapter for approved APIs, with local-first safety gates."""

    AUDIO_SUFFIX_BY_MIME = {
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/mp4": ".m4a",
        "audio/aac": ".aac",
        "audio/ogg": ".ogg",
        "audio/flac": ".flac",
    }
    PROVIDERS = {
        "huggingface_musicgen": "Hugging Face / MusicGen endpoint",
        "suno_compatible": "Suno-compatible approved gateway",
        "waivepulse_local": "WAIvePulse local HeartMuLa server",
    }
    SECRET_KEYS = {"key", "token", "secret", "authorization", "api_key", "apikey", "access_token"}

    def __init__(self, output_dir: Path | str):
        self.output_dir = Path(output_dir).expanduser().resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def status(self) -> dict[str, object]:
        return {
            "providers": [
                {
                    "id": "huggingface_musicgen",
                    "label": self.PROVIDERS["huggingface_musicgen"],
                    "ready": bool(self._hf_token()),
                    "endpoint": self._musicgen_endpoint(),
                    "env": ["GIMA_MUSICGEN_ENDPOINT_URL", "HUGGINGFACE_API_KEY or HF_TOKEN"],
                },
                {
                    "id": "suno_compatible",
                    "label": self.PROVIDERS["suno_compatible"],
                    "ready": bool(os.environ.get("GIMA_SUNO_API_BASE_URL", "").strip() and self._suno_token()),
                    "endpoint": os.environ.get("GIMA_SUNO_API_BASE_URL", "").strip(),
                    "env": ["GIMA_SUNO_API_BASE_URL", "SUNO_API_KEY or GIMA_MUSIC_API_KEY"],
                    "safety": "Only use official/authorized gateways. Gima does not bypass login, CAPTCHA, payment, or rate limits.",
                },
                {
                    "id": "waivepulse_local",
                    "label": self.PROVIDERS["waivepulse_local"],
                    "ready": self._waivepulse_ready().get("ready", False),
                    "endpoint": self._waivepulse_url(),
                    "env": ["GIMA_WAIVEPULSE_URL"],
                    "safety": "Runs locally through WAIvePulse. HeartMuLa generation requires a CUDA NVIDIA GPU; macOS can use this only if the server runs elsewhere.",
                    "status": self._waivepulse_ready(),
                },
            ],
            "cloud_allowed": cloud_allowed(),
            "note": "Cloud providers require CLOUD_ALLOWED=true. WAIvePulse local only requires a running local/authorized backend and consent=true.",
        }

    def generate(
        self,
        prompt: str,
        *,
        provider: str = "huggingface_musicgen",
        lyrics: str = "",
        model: str = "",
        duration_seconds: int = 30,
        instrumental: bool = False,
        consent: bool = False,
        timeout_seconds: int = 300,
    ) -> ExternalMusicApiProject:
        provider = provider.strip().casefold()
        if provider not in self.PROVIDERS:
            raise ValueError(f"Unsupported music provider: {provider}")
        if not consent:
            raise PermissionError("External music generation can spend credits and requires explicit consent")
        if provider != "waivepulse_local":
            require_cloud_allowed("external music generation")
        prompt = " ".join(prompt.strip().split())
        if not prompt:
            raise ValueError("Music prompt is required")

        project_dir = self.output_dir / f"external_music_{uuid.uuid4().hex[:12]}"
        project_dir.mkdir(parents=True, exist_ok=True)
        prompt_path = project_dir / "prompt.txt"
        manifest_path = project_dir / "manifest.json"
        prompt_path.write_text(self._prompt_text(prompt, lyrics), encoding="utf-8")

        if provider == "huggingface_musicgen":
            response = self._call_huggingface_musicgen(prompt, lyrics, model, duration_seconds, instrumental, timeout_seconds)
        elif provider == "waivepulse_local":
            response = self._call_waivepulse_local(prompt, lyrics, model, duration_seconds, timeout_seconds)
        else:
            response = self._call_suno_compatible(prompt, lyrics, model, duration_seconds, instrumental, timeout_seconds)

        output_path = self._write_audio_response(project_dir, response)
        manifest = {
            "kind": "external_music_api",
            "status": "generated",
            "provider": provider,
            "provider_label": self.PROVIDERS[provider],
            "model": model,
            "prompt": prompt,
            "lyrics_provided": bool(lyrics.strip()),
            "duration_seconds": max(1, min(int(duration_seconds), 600)),
            "instrumental": bool(instrumental),
            "output": str(output_path),
            "prompt_path": str(prompt_path),
            "response_summary": self._safe_summary(response),
            "safety": [
                "Cloud music generation requires CLOUD_ALLOWED=true and explicit consent.",
                "Use only prompts, lyrics, melodies, voices, and styles you own or have permission to use.",
                "Suno-compatible mode is for official/authorized gateways only, not browser-token scraping or CAPTCHA bypass.",
            ],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        return ExternalMusicApiProject(project_dir, output_path, manifest_path, prompt_path)

    def _call_huggingface_musicgen(
        self,
        prompt: str,
        lyrics: str,
        model: str,
        duration_seconds: int,
        instrumental: bool,
        timeout_seconds: int,
    ) -> dict[str, object]:
        token = self._hf_token()
        if not token:
            raise RuntimeError("HUGGINGFACE_API_KEY or HF_TOKEN is not set")
        endpoint = self._musicgen_endpoint()
        payload = {
            "inputs": self._prompt_text(prompt, lyrics),
            "parameters": {
                "duration": max(1, min(int(duration_seconds), 600)),
                "model": model,
                "instrumental": bool(instrumental),
            },
        }
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "audio/wav, audio/mpeg, application/json",
                "User-Agent": "Gima local assistant/0.1",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=max(30, timeout_seconds)) as response:
            return {"content_type": self._content_type(response), "body": response.read(), "url": endpoint}

    def _call_suno_compatible(
        self,
        prompt: str,
        lyrics: str,
        model: str,
        duration_seconds: int,
        instrumental: bool,
        timeout_seconds: int,
    ) -> dict[str, object]:
        base_url = os.environ.get("GIMA_SUNO_API_BASE_URL", "").strip().rstrip("/")
        token = self._suno_token()
        if not base_url:
            raise RuntimeError("GIMA_SUNO_API_BASE_URL is not set")
        if not token:
            raise RuntimeError("SUNO_API_KEY or GIMA_MUSIC_API_KEY is not set")
        path = os.environ.get("GIMA_SUNO_GENERATE_PATH", "/api/generate").strip() or "/api/generate"
        if not path.startswith("/"):
            path = "/" + path
        payload = {
            "prompt": prompt,
            "lyrics": lyrics,
            "model": model,
            "duration_seconds": max(1, min(int(duration_seconds), 600)),
            "instrumental": bool(instrumental),
        }
        request = urllib.request.Request(
            base_url + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "audio/wav, audio/mpeg, application/json",
                "User-Agent": "Gima local assistant/0.1",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=max(30, timeout_seconds)) as response:
            return {"content_type": self._content_type(response), "body": response.read(), "url": base_url + path}

    def _call_waivepulse_local(
        self,
        prompt: str,
        lyrics: str,
        title: str,
        duration_seconds: int,
        timeout_seconds: int,
    ) -> dict[str, object]:
        lyrics = lyrics.strip()
        if not lyrics:
            raise ValueError("WAIvePulse requires lyrics with section markers, for example [Verse] and [Chorus]")
        base_url = self._waivepulse_url()
        status = self._waivepulse_ready()
        if not status.get("server_running", False):
            raise RuntimeError(f"WAIvePulse is not running at {base_url}. Start it first with its start.sh/start.bat.")
        if not status.get("ready", False):
            raise RuntimeError(f"WAIvePulse model is not ready: {status}")
        payload = {
            "lyrics": lyrics,
            "tags": prompt,
            "title": title.strip() or "Gima WAIvePulse Song",
            "artist": "Gima",
            "max_duration_sec": max(4, min(int(duration_seconds), 600)),
            "temperature": 1.0,
            "cfg_scale": 1.5,
            "topk": 50,
        }
        submit = self._json_post(f"{base_url}/generate", payload, timeout=30)
        job_id = str(submit.get("job_id") or "").strip()
        if not job_id:
            raise RuntimeError(f"WAIvePulse did not return a job id: {submit}")
        final = self._poll_waivepulse(base_url, job_id, timeout_seconds)
        file_url = str(final.get("file") or "").strip()
        if not file_url:
            raise RuntimeError(f"WAIvePulse finished without an output file: {final}")
        with urllib.request.urlopen(base_url + file_url, timeout=180) as response:
            body = response.read()
            content_type = self._content_type(response)
        return {
            "content_type": content_type if content_type != "application/octet-stream" else "audio/mpeg",
            "body": body,
            "url": base_url + file_url,
            "waivepulse_job": final,
        }

    def _poll_waivepulse(self, base_url: str, job_id: str, timeout_seconds: int) -> dict[str, object]:
        deadline = time.time() + max(30, timeout_seconds)
        last: dict[str, object] = {}
        while time.time() < deadline:
            with urllib.request.urlopen(f"{base_url}/status/{urllib.parse.quote(job_id)}", timeout=20) as response:
                last = json.loads(response.read().decode("utf-8"))
            status = str(last.get("status", "")).casefold()
            if status == "done":
                return last
            if status in {"error", "cancelled", "canceled"}:
                raise RuntimeError(f"WAIvePulse job failed: {last}")
            time.sleep(3)
        raise TimeoutError(f"WAIvePulse job did not finish within {timeout_seconds}s: {job_id}. Last status: {last}")

    def _write_audio_response(self, project_dir: Path, response: dict[str, object]) -> Path:
        content_type = str(response.get("content_type") or "application/octet-stream").split(";", 1)[0].strip().lower()
        body = response.get("body")
        if not isinstance(body, bytes):
            raise RuntimeError("Music API response did not include bytes")
        if content_type.startswith("audio/"):
            output_path = project_dir / f"generated_music{self.AUDIO_SUFFIX_BY_MIME.get(content_type, '.wav')}"
            output_path.write_bytes(body)
            return output_path

        payload = json.loads(body.decode("utf-8", errors="replace"))
        audio_bytes, suffix = self._audio_from_json(payload)
        output_path = project_dir / f"generated_music{suffix}"
        output_path.write_bytes(audio_bytes)
        return output_path

    def _audio_from_json(self, payload: object) -> tuple[bytes, str]:
        if not isinstance(payload, dict):
            raise RuntimeError("Music API JSON response must be an object")
        for key in ["audio_base64", "audio", "wav", "mp3", "data"]:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                text = value.strip()
                if text.startswith("data:") and "," in text:
                    header, encoded = text.split(",", 1)
                    suffix = ".mp3" if "mpeg" in header or "mp3" in header else ".wav"
                    return base64.b64decode(encoded), suffix
                try:
                    return base64.b64decode(text), ".mp3" if key == "mp3" else ".wav"
                except Exception:
                    pass
        for key in ["audio_url", "url", "download_url", "file"]:
            value = payload.get(key)
            if isinstance(value, str) and value.startswith(("https://", "http://")):
                with urllib.request.urlopen(value, timeout=180) as response:
                    content_type = self._content_type(response).split(";", 1)[0].lower()
                    suffix = self.AUDIO_SUFFIX_BY_MIME.get(content_type) or Path(urllib.parse.urlparse(value).path).suffix or ".mp3"
                    return response.read(), suffix
        raise RuntimeError("Music API response did not contain audio bytes, base64 audio, or a downloadable audio URL")

    def _prompt_text(self, prompt: str, lyrics: str) -> str:
        lyrics = lyrics.strip()
        if not lyrics:
            return prompt.strip() + "\n"
        return f"{prompt.strip()}\n\nLyrics:\n{lyrics}\n"

    def _safe_summary(self, response: dict[str, object]) -> dict[str, object]:
        summary: dict[str, object] = {"content_type": response.get("content_type", ""), "url": response.get("url", "")}
        if "waivepulse_job" in response:
            summary["waivepulse_job"] = self._redact(response["waivepulse_job"])
        body = response.get("body")
        if isinstance(body, bytes):
            summary["body_bytes"] = len(body)
            if str(response.get("content_type", "")).startswith("application/json"):
                try:
                    summary["json"] = self._redact(json.loads(body.decode("utf-8", errors="replace")))
                except Exception:
                    pass
        return summary

    def _redact(self, value: object) -> object:
        if isinstance(value, dict):
            return {
                key: "[redacted]" if any(secret in str(key).casefold() for secret in self.SECRET_KEYS) else self._redact(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [self._redact(item) for item in value[:20]]
        if isinstance(value, str) and len(value) > 240:
            return value[:240] + "...[truncated]"
        return value

    def _content_type(self, response: object) -> str:
        headers = getattr(response, "headers", None)
        if headers and hasattr(headers, "get_content_type"):
            return str(headers.get_content_type())
        if headers and hasattr(headers, "get"):
            return str(headers.get("Content-Type", "application/octet-stream")).split(";", 1)[0]
        return "application/octet-stream"

    def _musicgen_endpoint(self) -> str:
        return os.environ.get(
            "GIMA_MUSICGEN_ENDPOINT_URL",
            "https://api-inference.huggingface.co/models/facebook/musicgen-small",
        ).strip()

    def _hf_token(self) -> str:
        return os.environ.get("HUGGINGFACE_API_KEY", "").strip() or os.environ.get("HF_TOKEN", "").strip()

    def _suno_token(self) -> str:
        return os.environ.get("SUNO_API_KEY", "").strip() or os.environ.get("GIMA_MUSIC_API_KEY", "").strip()

    def _waivepulse_url(self) -> str:
        return os.environ.get("GIMA_WAIVEPULSE_URL", "http://127.0.0.1:7861").strip().rstrip("/")

    def _waivepulse_ready(self) -> dict[str, object]:
        base_url = self._waivepulse_url()
        try:
            with urllib.request.urlopen(f"{base_url}/model-status", timeout=2) as response:
                payload = json.loads(response.read().decode("utf-8"))
            payload["server_running"] = True
            return payload
        except Exception as error:
            return {"ready": False, "server_running": False, "error": str(error), "base_url": base_url}

    def _json_post(self, url: str, payload: dict[str, object], timeout: int) -> dict[str, object]:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))


class NeuralLipSyncRenderer:
    """Adapter for a locally installed SadTalker portrait-animation backend."""

    CRITICAL_WEIGHT_MIN_BYTES = {
        "gfpgan/weights/detection_Resnet50_Final.pth": 109_000_000,
        "gfpgan/weights/alignment_WFLW_4HG.pth": 193_000_000,
    }

    def __init__(self, output_dir: Path, backend_dir: Path, python_path: Path | None = None):
        self.output_dir = output_dir.expanduser().resolve()
        self.backend_dir = backend_dir.expanduser().resolve()
        default_python = self.backend_dir / ".venv" / "bin" / "python"
        selected_python = python_path or (default_python if default_python.exists() else Path(sys.executable))
        self.python_path = selected_python.expanduser().resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def status(self) -> Dict[str, object]:
        inference = self.backend_dir / "inference.py"
        packaged = list((self.backend_dir / "checkpoints").glob("SadTalker*.safetensors")) if (self.backend_dir / "checkpoints").exists() else []
        critical_weights = []
        corrupt_weights = []
        for relative, min_bytes in self.CRITICAL_WEIGHT_MIN_BYTES.items():
            path = self.backend_dir / relative
            size = path.stat().st_size if path.exists() else 0
            item = {"path": str(path), "size_bytes": size, "min_bytes": min_bytes, "ok": size >= min_bytes}
            critical_weights.append(item)
            if not item["ok"]:
                corrupt_weights.append(relative)
        ready = inference.exists() and bool(packaged) and self.python_path.exists() and not corrupt_weights
        return {
            "backend": "SadTalker",
            "ready": ready,
            "backend_dir": str(self.backend_dir),
            "python": str(self.python_path),
            "inference_script": str(inference),
            "checkpoint_count": len(packaged),
            "critical_weights": critical_weights,
            "missing": [
                label
                for label, present in {
                    "inference.py": inference.exists(),
                    "SadTalker checkpoint": bool(packaged),
                    "backend Python": self.python_path.exists(),
                    "complete face detection/alignment weights": not corrupt_weights,
                }.items()
                if not present
            ],
            "performance_note": "CPU rendering can take many minutes. Use 1-4 second previews, crop preprocessing, or a GPU/Open Video backend for faster work.",
            "install_source": "https://github.com/OpenTalker/SadTalker",
            "license": "Apache-2.0",
        }

    def render(
        self,
        audio: Path,
        face: Path,
        prompt: str,
        emotion: str = "cinematic",
        camera_motion: str = "subtle",
        max_duration_seconds: int = 30,
        preprocess: str = "crop",
        timeout_seconds: int = 1800,
        consent: bool = False,
    ) -> NeuralLipSyncProject:
        if not consent:
            raise PermissionError("Neural lip sync requires consent for the person, voice, face, and song")
        status = self.status()
        if not status["ready"]:
            raise RuntimeError(f"SadTalker backend is not ready. Missing: {', '.join(status['missing'])}. Install it at {self.backend_dir}")
        audio_path = audio.expanduser().resolve()
        face_path = face.expanduser().resolve()
        if not audio_path.exists() or not face_path.exists():
            raise FileNotFoundError("Audio and face source must exist")
        project_dir = self.output_dir / f"neural_lip_sync_{uuid.uuid4().hex[:12]}"
        generated_dir = project_dir / "generated"
        generated_dir.mkdir(parents=True, exist_ok=True)
        prepared_audio = project_dir / "prepared_audio.wav"
        output_path = project_dir / "output_neural_lip_sync.mp4"
        manifest_path = project_dir / "manifest.json"
        log_path = project_dir / "backend.log"
        if preprocess not in {"crop", "extcrop", "resize", "full", "extfull"}:
            raise ValueError("preprocess must be one of: crop, extcrop, resize, full, extfull")
        duration = max(1, min(int(max_duration_seconds), 300))
        timeout_seconds = max(60, min(int(timeout_seconds), 7200))
        subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(audio_path), "-t", str(duration),
                "-ar", "16000", "-ac", "1", str(prepared_audio),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=180,
        )
        expression_scale = {"calm": 0.8, "sad": 0.85, "happy": 1.15, "intense": 1.35}.get(emotion.casefold(), 1.0)
        command = [
            str(self.python_path), str(self.backend_dir / "inference.py"),
            "--driven_audio", str(prepared_audio), "--source_image", str(face_path),
            "--checkpoint_dir", str(self.backend_dir / "checkpoints"),
            "--result_dir", str(generated_dir), "--preprocess", preprocess, "--still", "--cpu", "--size", "256",
            "--expression_scale", str(expression_scale),
        ]
        if camera_motion == "cinematic":
            command.extend(["--input_yaw", "-8", "0", "8", "0", "--input_pitch", "2", "-3", "2"])
        result = subprocess.run(
            command,
            cwd=self.backend_dir,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        log_path.write_text((result.stdout or "") + "\n" + (result.stderr or ""), encoding="utf-8")
        if result.returncode != 0:
            raise RuntimeError(f"SadTalker failed with exit code {result.returncode}. See {log_path}")
        candidates = sorted(generated_dir.rglob("*.mp4"), key=lambda path: path.stat().st_mtime, reverse=True)
        if not candidates:
            raise RuntimeError(f"SadTalker finished without an MP4. See {log_path}")
        shutil.copy2(candidates[0], output_path)
        manifest = {
            "kind": "neural_lip_sync",
            "status": "rendered",
            "backend": status,
            "audio": str(audio_path),
            "face": str(face_path),
            "prompt": prompt,
            "emotion": emotion,
            "camera_motion": camera_motion,
            "preprocess": preprocess,
            "duration_limit_seconds": duration,
            "timeout_seconds": timeout_seconds,
            "output": str(output_path),
            "backend_log": str(log_path),
            "accuracy_truth": "Neural lip sync is generated, but frame-level phoneme accuracy still requires human review.",
            "safety": "AI-assisted portrait animation; share only with consent and clear synthetic-media labeling.",
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return NeuralLipSyncProject(project_dir, output_path, manifest_path, log_path)


class LocalMusicVideoDirector:
    """Freebeat-style local planning layer for music-first video workflows."""

    MODES = {"story", "stage", "lyrics", "visualizer"}
    ASPECTS = {"16:9", "9:16", "1:1"}

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def plan(
        self,
        audio: Path,
        prompt: str,
        mode: str = "story",
        style: str = "cinematic",
        aspect: str = "16:9",
        lyrics: str = "",
    ) -> MusicVideoDirectorPlan:
        audio_path = audio.expanduser().resolve()
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file does not exist: {audio_path}")
        mode = mode.casefold().strip() or "story"
        if mode not in self.MODES:
            raise ValueError(f"Mode must be one of: {', '.join(sorted(self.MODES))}")
        if aspect not in self.ASPECTS:
            raise ValueError(f"Aspect must be one of: {', '.join(sorted(self.ASPECTS))}")
        prompt = " ".join(prompt.strip().split())
        if not prompt:
            raise ValueError("Creative prompt is required")
        project_dir = self.output_dir / f"music_video_director_{uuid.uuid4().hex[:12]}"
        project_dir.mkdir(parents=True, exist_ok=True)
        metadata = LipSyncPlanner(project_dir)._media_metadata(audio_path)
        duration = self._duration(metadata)
        scenes = self._scenes(duration, prompt, mode, style, lyrics)
        storyboard_path = project_dir / "storyboard.md"
        manifest_path = project_dir / "manifest.json"
        storyboard_path.write_text(
            self._storyboard_text(audio_path, prompt, mode, style, aspect, scenes),
            encoding="utf-8",
        )
        manifest = {
            "kind": "freebeat_style_local_music_video_director",
            "audio": str(audio_path),
            "prompt": prompt,
            "mode": mode,
            "style": style,
            "aspect": aspect,
            "duration_seconds": duration,
            "lyrics": lyrics,
            "storyboard": str(storyboard_path),
            "scenes": scenes,
            "renderer_next_step": "Use music-video-local for waveform/spectrum render, or connect an approved local video model.",
            "limits": [
                "This is a local director/storyboard planner, not Freebeat.ai and not a full generative video backend.",
                "Use only songs, lyrics, images, and faces you own or have permission to use.",
            ],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return MusicVideoDirectorPlan(project_dir, storyboard_path, manifest_path)

    def _duration(self, metadata: Dict[str, object]) -> float:
        try:
            return max(8.0, float((metadata.get("format") or {}).get("duration") or 30.0))
        except (TypeError, ValueError):
            return 30.0

    def _scenes(self, duration: float, prompt: str, mode: str, style: str, lyrics: str) -> List[Dict[str, object]]:
        scene_count = max(3, min(12, math.ceil(duration / 8)))
        scene_length = duration / scene_count
        lyric_lines = [line.strip() for line in lyrics.splitlines() if line.strip()]
        scenes: List[Dict[str, object]] = []
        for index in range(scene_count):
            start = round(index * scene_length, 2)
            end = round(duration if index == scene_count - 1 else (index + 1) * scene_length, 2)
            energy = "intro" if index == 0 else "peak" if index == scene_count - 1 else "build"
            if mode == "stage":
                shot = "performer close-up, stage lights, crowd energy"
            elif mode == "lyrics":
                shot = "dynamic lyric caption focus with animated background"
            elif mode == "visualizer":
                shot = "audio-reactive shapes, waveform motion, beat-synced color"
            else:
                shot = "story scene with A-roll emotion and B-roll atmosphere"
            scenes.append(
                {
                    "index": index + 1,
                    "start": start,
                    "end": end,
                    "energy": energy,
                    "direction": f"{style} {shot}",
                    "prompt": f"{prompt}. Scene {index + 1}: {energy} section, {shot}.",
                    "lyric_hint": lyric_lines[index % len(lyric_lines)] if lyric_lines else "",
                }
            )
        return scenes

    def _storyboard_text(
        self,
        audio_path: Path,
        prompt: str,
        mode: str,
        style: str,
        aspect: str,
        scenes: List[Dict[str, object]],
    ) -> str:
        lines = [
            "# Local Music Video Director Plan",
            "",
            f"Audio: {audio_path}",
            f"Mode: {mode}",
            f"Style: {style}",
            f"Aspect: {aspect}",
            f"Creative prompt: {prompt}",
            "",
            "## Scenes",
        ]
        for scene in scenes:
            lines.extend(
                [
                    "",
                    f"### Scene {scene['index']} ({scene['start']}s-{scene['end']}s)",
                    f"- Energy: {scene['energy']}",
                    f"- Direction: {scene['direction']}",
                    f"- Prompt: {scene['prompt']}",
                    f"- Lyric hint: {scene['lyric_hint'] or '[none]'}",
                ]
            )
        lines.extend(
            [
                "",
                "## Next Local Steps",
                "",
                "1. Render a waveform/spectrum draft with `music-video-local`.",
                "2. Add lyric timing or scene images when available.",
                "3. Evaluate the MP4 with `video-eval-local`.",
            ]
        )
        return "\n".join(lines) + "\n"


class FrontierVideoPlanner:
    """Local planning layer for Seedance/Veo-style video work without claiming proprietary quality."""

    BACKENDS = [
        {
            "name": "ComfyUI + Wan/LTX-style workflow",
            "local_level": "best practical open local path",
            "needs": "Python, PyTorch/MPS or CUDA, model weights, workflow JSON, large disk/RAM.",
            "why": "Supports image/video nodes, prompt workflows, and can be upgraded model by model.",
        },
        {
            "name": "Wan / HunyuanVideo / Mochi / LTX-Video class open models",
            "local_level": "open model family to evaluate",
            "needs": "Model-specific install, strong GPU or optimized CPU fallback, VRAM-aware settings.",
            "why": "Closest free direction for text/image-to-video experiments.",
        },
        {
            "name": "Gima ffmpeg professional renderer",
            "local_level": "available now",
            "needs": "ffmpeg and source audio/images.",
            "why": "Reliable artifact generation, audio sync, manifests, and evaluation today.",
        },
    ]

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def plan(
        self,
        prompt: str,
        audio: Path | None = None,
        images: List[Path] | None = None,
        target: str = "veo_seedance",
        duration_seconds: int = 8,
    ) -> FrontierVideoPlan:
        clean_prompt = " ".join(prompt.strip().split())
        if not clean_prompt:
            raise ValueError("Frontier video prompt is required")
        target = target.casefold().strip() or "veo_seedance"
        duration = max(2, min(int(duration_seconds), 60))
        audio_path = audio.expanduser().resolve() if audio else None
        image_paths = [image.expanduser().resolve() for image in images or []]
        if audio_path and not audio_path.exists():
            raise FileNotFoundError(f"Audio file does not exist: {audio_path}")
        for image_path in image_paths:
            if not image_path.exists():
                raise FileNotFoundError(f"Image file does not exist: {image_path}")

        project_dir = self.output_dir / f"frontier_video_{uuid.uuid4().hex[:12]}"
        project_dir.mkdir(parents=True, exist_ok=True)
        prompt_ladder_path = project_dir / "prompt_ladder.md"
        backend_report_path = project_dir / "backend_report.md"
        eval_rubric_path = project_dir / "eval_rubric.md"
        manifest_path = project_dir / "manifest.json"
        prompt_ladder_path.write_text(
            self._prompt_ladder(clean_prompt, target, duration, audio_path, image_paths),
            encoding="utf-8",
        )
        backend_report_path.write_text(self._backend_report(), encoding="utf-8")
        eval_rubric_path.write_text(self._eval_rubric(target), encoding="utf-8")
        manifest = {
            "kind": "frontier_video_plan",
            "target": target,
            "prompt": clean_prompt,
            "duration_seconds": duration,
            "audio": str(audio_path) if audio_path else "",
            "images": [str(path) for path in image_paths],
            "prompt_ladder": str(prompt_ladder_path),
            "backend_report": str(backend_report_path),
            "eval_rubric": str(eval_rubric_path),
            "status": "planned",
            "truth": (
                "This prepares a Veo/Seedance-style local workflow, but it does not provide "
                "Google/ByteDance proprietary model quality by itself."
            ),
            "next_local_steps": [
                "Use the prompt ladder with a local open video backend such as ComfyUI plus an approved model.",
                "Render short 2-8 second candidates first, then upscale/extend only after passing eval checks.",
                "Store every output in hands/out and run video-eval-local or the eval rubric before sharing.",
            ],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return FrontierVideoPlan(project_dir, manifest_path, prompt_ladder_path, backend_report_path, eval_rubric_path)

    def _prompt_ladder(
        self,
        prompt: str,
        target: str,
        duration: int,
        audio_path: Path | None,
        image_paths: List[Path],
    ) -> str:
        conditioning = []
        if audio_path:
            conditioning.append(f"- Audio timing source: `{audio_path}`")
        if image_paths:
            conditioning.append("- Image references:\n" + "\n".join(f"  - `{path}`" for path in image_paths))
        if not conditioning:
            conditioning.append("- No media conditioning supplied; use text-to-video only.")
        return "\n".join(
            [
                "# Frontier Video Prompt Ladder",
                "",
                f"Target style: {target}",
                f"Duration target: {duration}s",
                "",
                "## Conditioning",
                "",
                *conditioning,
                "",
                "## Level 1: Director Brief",
                "",
                (
                    f"{prompt}. Make it cinematic, temporally stable, physically coherent, "
                    "clear subject motion, clean camera movement, realistic lighting, temporal consistency, and no flicker."
                ),
                "",
                "## Level 2: Shot Prompt",
                "",
                (
                    "Single continuous shot, strong subject-background separation, consistent identity across frames, "
                    "smooth motion, no warped hands/faces/text, no sudden scene jumps, no camera shake unless requested."
                ),
                "",
                "## Level 3: Negative Prompt",
                "",
                (
                    "low quality, blurry, flicker, jitter, broken anatomy, melted objects, unreadable text, "
                    "extra limbs, unstable face, distorted mouth, sudden cuts, inconsistent lighting, watermark."
                ),
                "",
                "## Level 4: Multi-Shot Expansion",
                "",
                "1. Establishing shot: environment and mood.",
                "2. Character/object motion shot: main action with stable camera.",
                "3. Detail shot: close-up texture or emotion.",
                "4. Closing shot: clean end frame for looping or extension.",
                "",
                "## Level 5: Audio/Beat Sync Notes",
                "",
                "Cut only on phrase boundaries, preserve beat timing, keep visual intensity rising with the music.",
            ]
        ) + "\n"

    def _backend_report(self) -> str:
        deps = dependency_report()
        lines = [
            "# Frontier Video Backend Report",
            "",
            "## Current Local Tools",
            "",
            f"- ffmpeg: {'ready' if deps.get('ffmpeg') else 'missing'}",
            f"- ffprobe: {'ready' if deps.get('ffprobe') else 'missing'}",
            f"- Python: ready",
            f"- llama-server: {'ready' if deps.get('llama-server') else 'missing'}",
            "",
            "## Backend Options",
        ]
        for backend in self.BACKENDS:
            lines.extend(
                [
                    "",
                    f"### {backend['name']}",
                    f"- Local level: {backend['local_level']}",
                    f"- Needs: {backend['needs']}",
                    f"- Why: {backend['why']}",
                ]
            )
        lines.extend(
            [
                "",
                "## Honest Gap To Veo/Seedance",
                "",
                (
                    "Frontier systems rely on very large proprietary training sets, distributed training, "
                    "reward/eval pipelines, and heavy inference infrastructure. Gima can imitate the workflow, "
                    "prompting discipline, artifact logging, and evaluation locally; matching raw quality requires "
                    "strong open models and much larger hardware."
                ),
            ]
        )
        return "\n".join(lines) + "\n"

    def _eval_rubric(self, target: str) -> str:
        rows = [
            ("prompt_adherence", "Does the video follow the requested subject, action, style, and aspect?"),
            ("temporal_consistency", "Are objects, faces, lighting, and scene layout stable across frames?"),
            ("motion_quality", "Is motion smooth and physically plausible without jitter/flicker?"),
            ("aesthetic_quality", "Is composition, color, focus, and lighting high quality?"),
            ("audio_sync", "If audio exists, do edits and intensity match beats/phrases?"),
            ("artifact_safety", "Is the output provenance logged and free from unwanted identity/copyright claims?"),
        ]
        lines = ["# Veo/Seedance-Style Local Eval Rubric", "", f"Target: {target}", ""]
        for name, question in rows:
            lines.extend([f"## {name}", "", f"- Question: {question}", "- Score: 0.0 to 1.0", "- Notes:", ""])
        return "\n".join(lines)


class LocalSongSketcher:
    """Tiny offline song sketch generator for rough local ideas."""

    SCALES = {
        "calm": [261.63, 293.66, 329.63, 392.00, 440.00],
        "happy": [261.63, 329.63, 392.00, 523.25, 659.25],
        "dark": [220.00, 261.63, 311.13, 392.00, 466.16],
        "default": [246.94, 293.66, 329.63, 369.99, 440.00],
    }

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def render(self, prompt: str, duration_seconds: int = 12) -> SongSketchProject:
        prompt = " ".join(prompt.strip().split())
        if not prompt:
            raise ValueError("Song prompt is required")
        duration = max(4, min(duration_seconds, 60))
        project_dir = self.output_dir / f"song_sketch_{uuid.uuid4().hex[:12]}"
        project_dir.mkdir(parents=True, exist_ok=True)
        output_path = project_dir / "song_sketch.wav"
        prompt_path = project_dir / "prompt.txt"
        manifest_path = project_dir / "manifest.json"
        prompt_path.write_text(prompt + "\n", encoding="utf-8")
        scale = self._scale(prompt)
        self._write_wav(output_path, prompt, scale, duration)
        manifest = {
            "kind": "local_song_sketch",
            "prompt": prompt,
            "duration_seconds": duration,
            "renderer": "python_wave_synth",
            "output": str(output_path),
            "scale": scale,
            "status": "rendered",
            "limits": [
                "This is a rough offline instrumental sketch, not a full Suno-style vocal song.",
                "Use it for local prototyping and prompts before connecting stronger approved generators.",
            ],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return SongSketchProject(project_dir, output_path, manifest_path, prompt_path)

    def _scale(self, prompt: str) -> List[float]:
        lower = prompt.casefold()
        if any(word in lower for word in {"calm", "soft", "sleep", "relax"}):
            return self.SCALES["calm"]
        if any(word in lower for word in {"happy", "bright", "dance", "pop"}):
            return self.SCALES["happy"]
        if any(word in lower for word in {"dark", "cinematic", "sad", "deep"}):
            return self.SCALES["dark"]
        return self.SCALES["default"]

    def _write_wav(self, path: Path, prompt: str, scale: List[float], duration: int) -> None:
        sample_rate = 44_100
        beat_seconds = 0.5
        amplitude = 12_000
        prompt_seed = sum(ord(char) for char in prompt)
        total_samples = sample_rate * duration
        with wave.open(str(path), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(sample_rate)
            frames = array("h")
            for sample in range(total_samples):
                beat = int(sample / (sample_rate * beat_seconds))
                frequency = scale[(beat + prompt_seed) % len(scale)]
                bass = scale[(beat // 2 + prompt_seed) % len(scale)] / 2
                t = sample / sample_rate
                envelope = min(1.0, (sample % int(sample_rate * beat_seconds)) / 2205)
                value = (
                    math.sin(2 * math.pi * frequency * t) * 0.72
                    + math.sin(2 * math.pi * bass * t) * 0.28
                )
                value *= envelope * amplitude
                frames.append(int(max(-32767, min(32767, value))))
            handle.writeframes(frames.tobytes())


class VideoQualityEvaluator:
    """Local, research-inspired checks for generated video artifacts."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def evaluate(self, video: Path, manifest: Path | None = None) -> VideoEvalResult:
        video_path = video.expanduser().resolve()
        manifest_path = manifest.expanduser().resolve() if manifest else None
        if not video_path.exists():
            raise FileNotFoundError(f"Video file does not exist: {video_path}")
        if video_path.suffix.casefold() not in {".mp4", ".mov", ".m4v", ".webm", ".mkv"}:
            raise ValueError("Video eval expects a local video file")
        metadata = self._probe(video_path)
        manifest_data = self._manifest(manifest_path)
        checks = self._checks(metadata, manifest_data)
        score = round(sum(item["score"] for item in checks) / len(checks), 2)
        report = {
            "kind": "veo_style_local_video_eval",
            "video": str(video_path),
            "manifest": str(manifest_path) if manifest_path else "",
            "score": score,
            "checks": checks,
            "metadata": metadata,
            "research_dimensions": [
                "audio-video presence",
                "duration reliability",
                "resolution readiness",
                "manifest/prompt traceability",
                "local provenance",
            ],
            "next_actions": [
                "Add beat detection and audio-video sync scoring.",
                "Add sampled-frame captioning for prompt adherence.",
                "Add temporal consistency checks across frames.",
                "Compare multiple renderer styles on the same audio.",
            ],
        }
        report_path = self.output_dir / f"video_eval_{uuid.uuid4().hex[:12]}.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return VideoEvalResult(video_path, report_path, score)

    def _probe(self, path: Path) -> Dict[str, object]:
        if not shutil.which("ffprobe"):
            raise RuntimeError("Video eval requires ffprobe")
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration,size:stream=codec_type,width,height,codec_name",
                "-of",
                "json",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return json.loads(result.stdout or "{}")

    @staticmethod
    def _manifest(path: Path | None) -> Dict[str, object]:
        if not path:
            return {}
        if not path.exists():
            raise FileNotFoundError(f"Manifest does not exist: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _checks(metadata: Dict[str, object], manifest: Dict[str, object]) -> List[Dict[str, object]]:
        streams = metadata.get("streams", [])
        if not isinstance(streams, list):
            streams = []
        has_video = any(stream.get("codec_type") == "video" for stream in streams if isinstance(stream, dict))
        has_audio = any(stream.get("codec_type") == "audio" for stream in streams if isinstance(stream, dict))
        video_streams = [stream for stream in streams if isinstance(stream, dict) and stream.get("codec_type") == "video"]
        width = int(video_streams[0].get("width") or 0) if video_streams else 0
        height = int(video_streams[0].get("height") or 0) if video_streams else 0
        duration = float((metadata.get("format") or {}).get("duration") or 0)
        prompt = str(manifest.get("prompt") or "").strip()
        renderer = str(manifest.get("renderer") or "").strip()
        return [
            {
                "name": "video_stream_present",
                "passed": has_video,
                "score": 1.0 if has_video else 0.0,
                "detail": "Generated artifact must contain a video stream.",
            },
            {
                "name": "audio_stream_present",
                "passed": has_audio,
                "score": 1.0 if has_audio else 0.0,
                "detail": "Veo-style systems should preserve or generate synchronized audio.",
            },
            {
                "name": "duration_nontrivial",
                "passed": duration >= 1.0,
                "score": 1.0 if duration >= 1.0 else 0.0,
                "detail": f"Duration is {duration:.2f} seconds.",
            },
            {
                "name": "resolution_720p_ready",
                "passed": width >= 1280 and height >= 720,
                "score": 1.0 if width >= 1280 and height >= 720 else 0.5 if width and height else 0.0,
                "detail": f"Resolution is {width}x{height}.",
            },
            {
                "name": "prompt_traceability",
                "passed": bool(prompt),
                "score": 1.0 if prompt else 0.0,
                "detail": "Manifest should preserve the user prompt for review.",
            },
            {
                "name": "renderer_provenance",
                "passed": bool(renderer),
                "score": 1.0 if renderer else 0.0,
                "detail": "Manifest should identify the generator/renderer.",
            },
        ]


def monitor_camera(
    capture: MediaCapture, interval_seconds: int, frames: int, device: str = "0"
) -> List[Path]:
    """Capture a bounded sequence. A future detector can discard unchanged frames."""
    paths: List[Path] = []
    for index in range(max(1, frames)):
        paths.append(capture.camera(f"camera_{index:05d}.jpg", device))
        if index + 1 < frames:
            time.sleep(max(1, interval_seconds))
    return paths


class SafeToolRunner:
    def __init__(self, config: Config, memory: MemoryStore):
        self.config = config
        self.permissions = PermissionManager(config, memory)

    def run(self, command: List[str]) -> subprocess.CompletedProcess:
        self.permissions.require("tools")
        if not self.config.tools.enabled:
            raise PermissionError("Tool execution is disabled in the configuration")
        if not command:
            raise ValueError("A command is required")
        executable = Path(command[0]).name
        if executable not in self.config.tools.allowed_commands:
            raise PermissionError(f"Command is not approved: {executable}")
        return subprocess.run(
            command,
            cwd=str(self.config.resolved_workspace),
            capture_output=True,
            text=True,
            timeout=120,
        )


@dataclass(frozen=True)
class CodeExecutionResult:
    language: str
    source_path: Path
    output_path: Path
    manifest_path: Path
    stdout: str
    stderr: str
    exit_code: int
    elapsed_seconds: float
    timed_out: bool


class SandboxedCodeRunner:
    """Run explicit user code without network or access to the user's home files."""

    LANGUAGES = {
        "python": ("python3", "main.py"),
        "javascript": ("node", "main.js"),
    }

    def __init__(self, output_dir: Path, protected_roots: Iterable[Path] = ()):
        self.output_dir = output_dir.expanduser().resolve()
        self.protected_roots = [path.expanduser().resolve() for path in protected_roots]

    def run(self, language: str, code: str, timeout_seconds: int = 10) -> CodeExecutionResult:
        language = language.casefold().strip()
        if language not in self.LANGUAGES:
            raise ValueError("Language must be python or javascript")
        if not code.strip():
            raise ValueError("Code is required")
        if len(code) > 50_000:
            raise ValueError("Code is limited to 50,000 characters")
        executable_name, filename = self.LANGUAGES[language]
        executable = shutil.which(executable_name)
        if not executable:
            raise RuntimeError(f"{executable_name} is not installed")
        run_id = f"run_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        run_dir = self.output_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        source_path = run_dir / filename
        output_path = run_dir / "output.txt"
        manifest_path = run_dir / "manifest.json"
        source_path.write_text(code, encoding="utf-8")
        timeout = max(1, min(30, int(timeout_seconds)))
        profile = self._sandbox_profile(run_dir)
        command = ["/usr/bin/sandbox-exec", "-p", profile, executable, str(source_path)]
        started = time.monotonic()
        timed_out = False
        try:
            completed = subprocess.run(
                command,
                cwd=str(run_dir),
                capture_output=True,
                text=True,
                timeout=timeout,
                env={
                    "PATH": "/usr/local/bin:/usr/bin:/bin",
                    "HOME": str(run_dir),
                    "TMPDIR": str(run_dir),
                    "PYTHONDONTWRITEBYTECODE": "1",
                },
            )
            stdout, stderr, exit_code = completed.stdout, completed.stderr, completed.returncode
        except subprocess.TimeoutExpired as error:
            timed_out = True
            stdout = error.stdout if isinstance(error.stdout, str) else ""
            stderr = error.stderr if isinstance(error.stderr, str) else ""
            stderr = (stderr + "\nExecution timed out.").strip()
            exit_code = 124
        elapsed = round(time.monotonic() - started, 3)
        combined = stdout + ("\n" + stderr if stderr else "")
        output_path.write_text(combined, encoding="utf-8")
        manifest_path.write_text(
            json.dumps(
                {
                    "id": run_id,
                    "language": language,
                    "source": str(source_path),
                    "output": str(output_path),
                    "exit_code": exit_code,
                    "elapsed_seconds": elapsed,
                    "timed_out": timed_out,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return CodeExecutionResult(
            language,
            source_path,
            output_path,
            manifest_path,
            stdout[-64_000:],
            stderr[-32_000:],
            exit_code,
            elapsed,
            timed_out,
        )

    def _sandbox_profile(self, run_dir: Path) -> str:
        home = str(Path.home().resolve()).replace('"', '\\"')
        allowed = str(run_dir.resolve()).replace('"', '\\"')
        denied = [home]
        denied.extend(str(path).replace('"', '\\"') for path in self.protected_roots if str(path) != home)
        deny_rules = "".join(f'(deny file-read* (subpath "{path}"))\n' for path in denied)
        return (
            "(version 1)\n"
            "(allow default)\n"
            "(deny network*)\n"
            f"{deny_rules}"
            f'(allow file-read* (subpath "{allowed}"))\n'
            "(deny file-write*)\n"
            f'(allow file-write* (subpath "{allowed}"))'
        )


def dependency_report() -> Dict[str, bool]:
    commands = [
        "sqlite3",
        "say",
        "screencapture",
        "ffmpeg",
        "ffprobe",
        "imagesnap",
        "tesseract",
        "pdftotext",
        "mlr",
        "csvcut",
        "whisper-cli",
        "llama-server",
    ]
    return {command: bool(shutil.which(command)) for command in commands}
