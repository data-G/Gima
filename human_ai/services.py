from __future__ import annotations

import html
import ipaddress
import json
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
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
            {"model": self.config.model, "messages": messages, "temperature": 0.2}
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
