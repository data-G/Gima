from __future__ import annotations

import html
import ipaddress
import json
import os
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
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
        if "result__a" in css_class and href:
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
        encoded = urllib.parse.urlencode({"q": query})
        url = f"https://duckduckgo.com/html/?{encoded}"
        request = urllib.request.Request(url, headers={"User-Agent": "human-ai-local/0.1"})
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

    def complete(self, messages: List[Dict[str, str]]) -> str:
        if not self.config.enabled:
            raise RuntimeError("Local model is disabled in the configuration")
        payload = json.dumps(
            {
                "model": self.config.model,
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": self.config.max_tokens,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.config.base_url.rstrip('/')}/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
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
        return False

    def ask(self, provider: str, prompt: str) -> str:
        provider = provider.casefold().strip()
        if provider in {"chatgpt", "openai"}:
            return self._ask_openai(prompt)
        if provider == "gemini":
            return self._ask_gemini(prompt)
        raise ValueError("Provider must be chatgpt, openai, or gemini")

    def _ask_openai(self, prompt: str) -> str:
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        payload = json.dumps(
            {
                "model": self.config.openai_model,
                "input": prompt,
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
        with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
        if body.get("output_text"):
            return body["output_text"].strip()
        parts: List[str] = []
        for item in body.get("output", []):
            for content in item.get("content", []):
                text = content.get("text")
                if text:
                    parts.append(text)
        return "\n".join(parts).strip()

    def _ask_gemini(self, prompt: str) -> str:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        model = urllib.parse.quote(self.config.gemini_model, safe="")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
        request = urllib.request.Request(
            f"{url}?key={urllib.parse.quote(api_key)}",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
        parts: List[str] = []
        for candidate in body.get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                text = part.get("text")
                if text:
                    parts.append(text)
        return "\n".join(parts).strip()


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


@dataclass
class MusicVideoProject:
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
        manifest = {
            "audio": str(audio_path),
            "face": str(face_path),
            "prompt": prompt,
            "audio_metadata": self._media_metadata(audio_path),
            "face_metadata": self._media_metadata(face_path),
            "output_hint": str(project_dir / "output_lip_sync.mp4"),
            "status": "planned",
            "next_step": (
                "Install or configure a consent-safe lip-sync generator, then use this manifest as input."
            ),
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return LipSyncProject(project_dir, manifest_path, prompt_path, safety_path)

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
        if style not in self.STYLES:
            raise ValueError(f"Unknown local music video style: {style}")

        project_dir = self.output_dir / f"music_video_{uuid.uuid4().hex[:12]}"
        project_dir.mkdir(parents=True, exist_ok=True)
        output_path = project_dir / "output_music_video.mp4"
        manifest_path = project_dir / "manifest.json"
        prompt_path = project_dir / "prompt.txt"
        prompt_path.write_text(prompt.strip() + "\n", encoding="utf-8")
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
            "status": "rendered",
            "audio_metadata": LipSyncPlanner(project_dir)._media_metadata(audio_path),
            "output_metadata": LipSyncPlanner(project_dir)._media_metadata(output_path),
            "safety": [
                "Use only audio you own or have permission to use.",
                "Label generated media as AI-assisted or locally rendered when shared.",
            ],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return MusicVideoProject(project_dir, output_path, manifest_path, prompt_path)


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
