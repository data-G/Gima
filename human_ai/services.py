from __future__ import annotations

import html
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
from typing import Dict, Iterable, List

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


class LocalModel:
    def __init__(self, config: Config):
        self.config = config.model

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
        return body["choices"][0]["message"]["content"].strip()


class TeacherModelClient:
    def __init__(self, config: Config):
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
        configured = [part.strip() for part in self.config.openrouter_model.split(",") if part.strip()]
        fallbacks = ["openai/gpt-5.5", "openai/gpt-4o", "openai/gpt-4.1"]
        models: List[str] = []
        for model in configured + fallbacks:
            if model not in models:
                models.append(model)
        return models

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
    ) -> str:
        if not api_key:
            raise RuntimeError(f"API key is not set for {url}")
        payload = json.dumps(
            {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 600,
            }
        ).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)
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
