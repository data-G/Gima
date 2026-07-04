#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import csv
import http.client
import json
import re
import tempfile
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


@dataclass
class ButtonResult:
    name: str
    status: str
    elapsed_seconds: float
    detail: str
    evidence: dict[str, Any]


class ButtonParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.buttons: list[dict[str, Any]] = []
        self._current: dict[str, Any] | None = None
        self._depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "button":
            self._current = {"attrs": {key: value or "" for key, value in attrs}, "label": ""}
            self._depth = 1
        elif self._current is not None:
            self._depth += 1

    def handle_endtag(self, tag: str) -> None:
        if self._current is None:
            return
        self._depth -= 1
        if tag == "button" and self._depth <= 0:
            self._current["label"] = " ".join(str(self._current["label"]).split())
            self.buttons.append(self._current)
            self._current = None

    def handle_data(self, data: str) -> None:
        if self._current is not None:
            self._current["label"] += data


class GimaButtonTester:
    def __init__(self, base_url: str, workspace: Path, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("base URL must start with http:// or https://")
        self.host = parsed.hostname or "127.0.0.1"
        self.port = parsed.port or 80
        self.timeout = timeout
        self.workspace = workspace
        self.report_dir = workspace / ".human-ai" / "hands" / "out" / "test_reports"
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.results: list[ButtonResult] = []
        self.html = ""

    def run(self) -> list[ButtonResult]:
        checks = [
            self.check_home_and_button_wiring,
            self.check_chat_send_button,
            self.check_prompt_buttons,
            self.check_search_button,
            self.check_upload_and_attach_buttons,
            self.check_media_buttons,
            self.check_plan_and_code_buttons,
            self.check_status_dashboard_buttons,
            self.check_copy_button_rendering,
        ]
        for check in checks:
            started = time.time()
            try:
                detail, evidence = check()
                self.results.append(ButtonResult(check.__name__, "PASS", time.time() - started, detail, evidence))
            except Exception as error:  # noqa: BLE001 - button audit should report every failure.
                self.results.append(ButtonResult(check.__name__, "FAIL", time.time() - started, str(error), {}))
        return self.results

    def check_home_and_button_wiring(self) -> tuple[str, dict[str, Any]]:
        status, _, body = self.request("GET", "/")
        self.require(status == 200, f"home returned {status}")
        self.html = body
        parser = ButtonParser()
        parser.feed(body)
        buttons = parser.buttons
        ids = set(re.findall(r'id="([^"]+)"', body))
        handled_ids = set(re.findall(r"getElementById\('([^']+)'\)\.addEventListener\('click'", body))
        handled_ids.update(re.findall(r'getElementById\("([^"]+)"\)\.addEventListener\("click"', body))
        variable_ids = dict(re.findall(r"const\s+([A-Za-z_$][\w$]*)\s*=\s*document\.getElementById\('([^']+)'\)", body))
        variable_ids.update(re.findall(r'const\s+([A-Za-z_$][\w$]*)\s*=\s*document\.getElementById\("([^"]+)"\)', body))
        for variable, element_id in variable_ids.items():
            if re.search(rf"\b{re.escape(variable)}\.addEventListener\(['\"]click['\"]", body):
                handled_ids.add(element_id)
        missing_focus = []
        dead_buttons = []
        for index, button in enumerate(buttons, start=1):
            attrs = button["attrs"]
            focus = attrs.get("data-focus")
            if focus and focus not in ids:
                missing_focus.append({"button": button["label"], "focus": focus})
            if self._button_is_wired(attrs, handled_ids):
                continue
            dead_buttons.append({"index": index, "label": button["label"], "attrs": attrs})
        self.require(not missing_focus, f"buttons point at missing focus targets: {missing_focus}")
        self.require(not dead_buttons, f"unwired buttons found: {dead_buttons}")
        return "Every static button has a UI handler or declarative action.", {
            "button_count": len(buttons),
            "handled_id_count": len(handled_ids),
        }

    def check_chat_send_button(self) -> tuple[str, dict[str, Any]]:
        data, elapsed = self.post_json("/api/chat", {"message": "hi"})
        self.require(data.get("reply") == "Hi. I am here and ready.", f"hi reply mismatch: {data}")
        return "Send button backend path replies to hi.", {"elapsed": elapsed, "reply": data.get("reply")}

    def check_prompt_buttons(self) -> tuple[str, dict[str, Any]]:
        prompts = [
            "use brain: What does Gima know right now?",
            "make a table of fastest cars",
        ]
        evidence = {}
        for prompt in prompts:
            data, elapsed = self.post_json("/api/chat", {"message": prompt})
            self.require(data.get("reply"), f"prompt returned no reply: {prompt}")
            evidence[prompt] = {"elapsed": elapsed, "files": len(data.get("files", []))}
        return "Prompt shortcut buttons route through chat.", evidence

    def check_search_button(self) -> tuple[str, dict[str, Any]]:
        data, elapsed = self.get_json("/api/memory/search?q=gima&limit=5")
        self.require("results" in data, "memory search did not return results key")
        brain, brain_elapsed = self.get_json("/api/brain/search?q=gima&limit=5")
        self.require("results" in brain, "brain search did not return results key")
        return "Search buttons have live search endpoints.", {
            "memory_elapsed": elapsed,
            "brain_elapsed": brain_elapsed,
            "memory_results": len(data.get("results", [])),
            "brain_results": len(brain.get("results", [])),
        }

    def check_upload_and_attach_buttons(self) -> tuple[str, dict[str, Any]]:
        payload = b"gima button audit upload"
        upload = self.upload_file("button_audit.txt", payload, "text/plain")
        uploaded = upload["files"][0]
        status, _, downloaded = self.request("GET", "/api/download?path=" + quote(uploaded["path"]), decode=False)
        self.require(status == 200, f"download returned {status}")
        self.require(downloaded == payload, "downloaded upload content mismatch")
        files, elapsed = self.get_json("/api/files")
        self.require(any(item.get("name") == "button_audit.txt" for item in files.get("files", [])), "uploaded file missing from file list")
        return "Attach/upload/download buttons work.", {"uploaded": uploaded, "files_elapsed": elapsed}

    def check_media_buttons(self) -> tuple[str, dict[str, Any]]:
        song, song_elapsed = self.post_json(
            "/api/media/song-local",
            {"prompt": "button audit short tone", "duration_seconds": 4},
            timeout=60,
        )
        audio_path = song.get("output")
        self.require(audio_path and Path(audio_path).exists(), f"song output missing: {song}")

        video, video_elapsed = self.post_json(
            "/api/media/music-video-local",
            {"audio_path": audio_path, "prompt": "button audit waveform video", "style": "waveform", "consent": True},
            timeout=180,
        )
        self.require(Path(video.get("output", "")).exists(), f"video output missing: {video}")

        image_path = self.workspace / ".human-ai" / "hands" / "in" / "button_audit.png"
        image_path.parent.mkdir(parents=True, exist_ok=True)
        image_path.write_bytes(PNG_1X1)
        image_video, image_video_elapsed = self.post_json(
            "/api/media/image-music-video-local",
            {
                "audio_path": audio_path,
                "image_paths": [str(image_path)],
                "prompt": "button audit image music video",
                "aspect": "16:9",
                "max_duration_seconds": 4,
                "consent": True,
            },
            timeout=180,
        )
        self.require(Path(image_video.get("output", "")).exists(), f"image video output missing: {image_video}")
        return "Song/video/image-video buttons generate files.", {
            "song_elapsed": song_elapsed,
            "video_elapsed": video_elapsed,
            "image_video_elapsed": image_video_elapsed,
            "audio": audio_path,
            "video": video.get("output"),
            "image_video": image_video.get("output"),
            "image": str(image_path),
        }

    def check_plan_and_code_buttons(self) -> tuple[str, dict[str, Any]]:
        audio_path = self._latest_audio_path()
        face_path = self.workspace / ".human-ai" / "hands" / "in" / "button_audit.png"
        if not face_path.exists():
            face_path.parent.mkdir(parents=True, exist_ok=True)
            face_path.write_bytes(PNG_1X1)
        director, director_elapsed = self.post_json(
            "/api/media/music-video-director",
            {
                "audio_path": audio_path,
                "prompt": "button audit director plan",
                "mode": "story",
                "style": "cinematic",
                "aspect": "16:9",
                "lyrics": "button audit",
            },
        )
        self.require(Path(director.get("storyboard", "")).exists(), f"director storyboard missing: {director}")
        lip, lip_elapsed = self.post_json(
            "/api/media/lip-sync-plan",
            {
                "audio_path": audio_path,
                "face_path": str(face_path),
                "prompt": "button audit lip sync plan",
                "consent": True,
            },
        )
        self.require(Path(lip.get("manifest", "")).exists(), f"lip sync manifest missing: {lip}")
        code, code_elapsed = self.post_json(
            "/api/code/vibe-plan",
            {"feature": "button audit verify coding button wiring", "max_files": 4},
        )
        self.require(Path(code.get("plan", "")).exists(), f"code plan missing: {code}")
        return "Director/lip-sync/coding buttons create plans.", {
            "director_elapsed": director_elapsed,
            "lip_elapsed": lip_elapsed,
            "code_elapsed": code_elapsed,
            "storyboard": director.get("storyboard"),
            "lip_manifest": lip.get("manifest"),
            "code_plan": code.get("plan"),
        }

    def check_status_dashboard_buttons(self) -> tuple[str, dict[str, Any]]:
        endpoints = [
            "/api/status",
            "/api/bindings",
            "/api/free-quotas",
            "/api/folders",
            "/api/capabilities",
            "/api/apps",
            "/api/codex-mode",
            "/api/ai-task-map",
            "/api/deployments",
            "/api/agents",
            "/api/outputs",
        ]
        evidence = {}
        for endpoint in endpoints:
            data, elapsed = self.get_json(endpoint)
            self.require(data, f"{endpoint} returned empty payload")
            evidence[endpoint] = {"elapsed": elapsed, "keys": list(data)[:8]}
        return "Dashboard/tool buttons have live data endpoints.", evidence

    def check_copy_button_rendering(self) -> tuple[str, dict[str, Any]]:
        data, elapsed = self.post_json("/api/chat", {"message": "make a table of fastest cars"})
        self.require(data.get("files"), "artifact reply did not return downloadable files")
        self.require("| rank | car |" in data.get("reply", ""), "artifact markdown table missing")
        return "Copy/download buttons have generated answer content and files to act on.", {
            "elapsed": elapsed,
            "file_count": len(data.get("files", [])),
        }

    def write_reports(self) -> tuple[Path, Path, Path]:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        json_path = self.report_dir / f"gima_button_test_{timestamp}.json"
        md_path = self.report_dir / f"gima_button_test_{timestamp}.md"
        csv_path = self.report_dir / f"gima_button_test_{timestamp}.csv"
        payload = {
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "base_url": self.base_url,
            "summary": self.summary(),
            "results": [result.__dict__ for result in self.results],
        }
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["name", "status", "elapsed_seconds", "detail"])
            writer.writeheader()
            for result in self.results:
                writer.writerow(
                    {
                        "name": result.name,
                        "status": result.status,
                        "elapsed_seconds": f"{result.elapsed_seconds:.3f}",
                        "detail": result.detail,
                    }
                )
        md_path.write_text(self._markdown_report(json_path, csv_path), encoding="utf-8")
        return json_path, md_path, csv_path

    def summary(self) -> dict[str, Any]:
        total = len(self.results)
        passed = sum(1 for result in self.results if result.status == "PASS")
        failed = total - passed
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "score_percent": round((passed / total) * 100, 2) if total else 0,
            "all_passed": failed == 0,
        }

    def request(
        self,
        method: str,
        path: str,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
        decode: bool = True,
        timeout: float | None = None,
    ) -> tuple[int, float, Any]:
        connection = http.client.HTTPConnection(self.host, self.port, timeout=timeout or self.timeout)
        started = time.time()
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        raw = response.read()
        elapsed = time.time() - started
        connection.close()
        if decode:
            return response.status, elapsed, raw.decode("utf-8", errors="replace")
        return response.status, elapsed, raw

    def get_json(self, path: str) -> tuple[dict[str, Any], float]:
        status, elapsed, body = self.request("GET", path)
        self.require(status < 400, f"{path} returned {status}: {body[:300]}")
        return json.loads(body), elapsed

    def post_json(self, path: str, payload: dict[str, Any], timeout: float | None = None) -> tuple[dict[str, Any], float]:
        status, elapsed, body = self.request(
            "POST",
            path,
            body=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            timeout=timeout,
        )
        self.require(status < 400, f"{path} returned {status}: {body[:300]}")
        data = json.loads(body)
        self.require(not data.get("error"), f"{path} returned error: {data.get('error')}")
        return data, elapsed

    def upload_file(self, filename: str, content: bytes, content_type: str) -> dict[str, Any]:
        boundary = "----gima-button-test-boundary"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="files"; filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode("utf-8") + content + f"\r\n--{boundary}--\r\n".encode("utf-8")
        status, _, raw = self.request(
            "POST",
            "/api/files/upload",
            body=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        self.require(status < 400, f"upload returned {status}: {raw[:300]}")
        data = json.loads(raw)
        self.require(data.get("files"), f"upload returned no files: {data}")
        return data

    def _latest_audio_path(self) -> str:
        paths = sorted((self.workspace / ".human-ai" / "hands" / "out" / "song_sketch").glob("**/*.wav"))
        if paths:
            return str(paths[-1])
        data, _ = self.post_json(
            "/api/media/song-local",
            {"prompt": "button audit fallback tone", "duration_seconds": 4},
            timeout=60,
        )
        return str(data["output"])

    def _button_is_wired(self, attrs: dict[str, str], handled_ids: set[str]) -> bool:
        if attrs.get("id") in handled_ids:
            return True
        if attrs.get("type") == "submit":
            return True
        if attrs.get("onclick"):
            return True
        data_keys = {
            "data-prompt",
            "data-open-panel",
            "data-action",
            "data-file-category",
            "data-copy-kind",
            "data-code-copy",
        }
        return any(key in attrs for key in data_keys)

    def _markdown_report(self, json_path: Path, csv_path: Path) -> str:
        summary = self.summary()
        lines = [
            "# Gima Button Test Report",
            "",
            f"- Base URL: `{self.base_url}`",
            f"- Score: `{summary['score_percent']}%`",
            f"- Passed: `{summary['passed']}/{summary['total']}`",
            f"- Failed: `{summary['failed']}`",
            f"- JSON: `{json_path}`",
            f"- CSV: `{csv_path}`",
            "",
            "## Results",
            "",
        ]
        for result in self.results:
            lines.append(f"- **{result.status}** `{result.name}` ({result.elapsed_seconds:.3f}s): {result.detail}")
        lines.extend(
            [
                "",
                "## Notes",
                "",
                "- Browser-native install prompts and clipboard writes are verified as wired UI actions, not clicked through OS dialogs.",
                "- API key saving is verified by unit tests in a temporary workspace to avoid overwriting private live keys.",
                "- File picker buttons are verified by wiring plus live upload/download endpoint tests.",
            ]
        )
        return "\n".join(lines) + "\n"

    @staticmethod
    def require(condition: bool, message: str) -> None:
        if not condition:
            raise AssertionError(message)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a live button audit against Gima Web UI.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8787")
    parser.add_argument("--workspace", default=str(Path.cwd()))
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()
    tester = GimaButtonTester(args.base_url, Path(args.workspace).resolve(), timeout=args.timeout)
    tester.run()
    json_path, md_path, csv_path = tester.write_reports()
    summary = tester.summary()
    print(json.dumps({"summary": summary, "json": str(json_path), "markdown": str(md_path), "csv": str(csv_path)}, indent=2))
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
