#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import http.client
import json
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class CheckResult:
    name: str
    status: str
    elapsed_seconds: float
    detail: str
    evidence: dict[str, Any]


class GimaWorldTester:
    def __init__(self, base_url: str, workspace: Path, timeout: float = 20.0):
        self.base_url = base_url.rstrip("/")
        self.host, self.port = self._parse_local_url(base_url)
        self.timeout = timeout
        self.workspace = workspace
        self.report_dir = workspace / ".human-ai" / "hands" / "out" / "test_reports"
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.results: list[CheckResult] = []

    def run(self) -> list[CheckResult]:
        checks = [
            self.check_home_html,
            self.check_status_contract,
            self.check_dashboards,
            self.check_brain_search,
            self.check_chat_greeting,
            self.check_brain_chat,
            self.check_artifact_generation,
            self.check_upload_download_cycle,
            self.check_security_download_guard,
            self.check_service_worker,
            self.check_performance_budget,
        ]
        for check in checks:
            start = time.time()
            try:
                detail, evidence = check()
                self.results.append(CheckResult(check.__name__, "PASS", time.time() - start, detail, evidence))
            except Exception as error:  # noqa: BLE001 - report every live product failure.
                self.results.append(CheckResult(check.__name__, "FAIL", time.time() - start, str(error), {}))
        return self.results

    def write_reports(self) -> tuple[Path, Path, Path]:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        json_path = self.report_dir / f"gima_world_test_{timestamp}.json"
        md_path = self.report_dir / f"gima_world_test_{timestamp}.md"
        csv_path = self.report_dir / f"gima_world_test_{timestamp}.csv"
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

    def check_home_html(self) -> tuple[str, dict[str, Any]]:
        status, _, body = self.request("GET", "/")
        self.require(status == 200, f"home returned {status}")
        required = [
            "Chat With Gima",
            "soft gray local AI workspace",
            "Human Folder Map",
            "Apps & Automation",
            "autoGrowMessage",
            "Copy code",
            "attach-inline",
            "Hello there",
            "action-tray",
            "modelChip",
            "drawer-backdrop",
            "nav-rail",
            "standard-shell",
            "Add to chat",
            "data-file-category",
        ]
        missing = [text for text in required if text not in body]
        self.require(not missing, f"missing UI markers: {missing}")
        return "Home UI contains smooth workspace markers.", {"required_markers": required}

    def check_status_contract(self) -> tuple[str, dict[str, Any]]:
        data, elapsed = self.get_json("/api/status")
        required = ["name", "workspace", "brain_csv", "brain_csv_rows", "memory_rows", "conversation_rows", "brain"]
        missing = [key for key in required if key not in data]
        self.require(not missing, f"missing status keys: {missing}")
        self.require(data["brain_csv_rows"] >= 1, "brain.csv has no rows")
        self.require(data["memory_rows"] >= 1, "memory has no rows")
        return "Status contract is healthy.", {"elapsed": elapsed, "brain_csv_rows": data["brain_csv_rows"]}

    def check_dashboards(self) -> tuple[str, dict[str, Any]]:
        endpoints = {
            "folders": "/api/folders",
            "apps": "/api/apps",
            "capabilities": "/api/capabilities",
            "codex": "/api/codex-mode",
            "task_map": "/api/ai-task-map",
            "deployments": "/api/deployments",
            "agents": "/api/agents",
            "outputs": "/api/outputs",
        }
        evidence = {}
        for name, path in endpoints.items():
            data, elapsed = self.get_json(path)
            self.require(data, f"{path} returned empty payload")
            evidence[name] = {"elapsed": elapsed, "keys": list(data.keys())}
        return "Dashboard endpoints are alive.", evidence

    def check_brain_search(self) -> tuple[str, dict[str, Any]]:
        data, elapsed = self.get_json("/api/brain/search?q=gima&limit=3")
        results = data.get("results", [])
        self.require(results, "brain search returned no results")
        self.require(data.get("path", "").endswith("brain.csv"), "brain search path is not brain.csv")
        return "Brain search returns indexed knowledge.", {"elapsed": elapsed, "result_count": len(results)}

    def check_chat_greeting(self) -> tuple[str, dict[str, Any]]:
        data, elapsed = self.post_json("/api/chat", {"message": "hi"})
        self.require("Hi. I am here and ready." in data.get("reply", ""), "greeting reply mismatch")
        self.require(elapsed < 3.0, f"greeting too slow: {elapsed:.3f}s")
        return "Chat greeting is fast.", {"elapsed": elapsed, "reply": data.get("reply", "")}

    def check_brain_chat(self) -> tuple[str, dict[str, Any]]:
        data, elapsed = self.post_json("/api/chat", {"message": "use brain: gima capabilities"})
        self.require(data.get("used_brain") is True, "brain chat did not report used_brain=true")
        self.require("Research-backed answer" in data.get("reply", ""), "brain chat did not use research answer")
        return "Brain-first chat works.", {"elapsed": elapsed, "brain_rows": len(data.get("brain_rows", []))}

    def check_artifact_generation(self) -> tuple[str, dict[str, Any]]:
        data, elapsed = self.post_json("/api/chat", {"message": "make a table of fastest cars"})
        files = data.get("files", [])
        self.require("| rank | car |" in data.get("reply", ""), "table markdown missing")
        self.require(any(file.get("path", "").endswith(".csv") for file in files), "CSV artifact missing")
        self.require(any(file.get("path", "").endswith(".pdf") for file in files), "PDF artifact missing")
        missing_files = [file["path"] for file in files if not Path(file.get("path", "")).exists()]
        self.require(not missing_files, f"artifact paths missing: {missing_files}")
        return "Artifact generation returns table, CSV, and PDF.", {"elapsed": elapsed, "files": files}

    def check_upload_download_cycle(self) -> tuple[str, dict[str, Any]]:
        content = b"gima world tester upload"
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=True) as temp:
            temp.write(content)
            temp.flush()
        boundary = "----gima-world-test-boundary"
        body = (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="files"; filename="world_test.txt"\r\n'
            "Content-Type: text/plain\r\n\r\n"
        ).encode("utf-8") + content + f"\r\n--{boundary}--\r\n".encode("utf-8")
        status, elapsed, raw = self.request(
            "POST",
            "/api/files/upload",
            body=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        self.require(status < 400, f"upload returned {status}: {raw[:200]}")
        data = json.loads(raw)
        file_path = data["files"][0]["path"]
        status, _, downloaded = self.request("GET", "/api/download?path=" + self.quote(file_path), decode=False)
        self.require(status == 200, f"download returned {status}")
        self.require(downloaded == content, "downloaded content mismatch")
        return "Upload and download cycle works.", {"elapsed": elapsed, "path": file_path}

    def check_security_download_guard(self) -> tuple[str, dict[str, Any]]:
        status, elapsed, body = self.request("GET", "/api/download?path=/etc/hosts")
        self.require(status == 403, f"/etc/hosts download was not blocked: {status}")
        return "Unsafe download path is blocked.", {"elapsed": elapsed, "body": body[:120]}

    def check_service_worker(self) -> tuple[str, dict[str, Any]]:
        status, elapsed, body = self.request("GET", "/service-worker.js")
        self.require(status == 200, f"service worker returned {status}")
        self.require("gima-local-app-v3" in body, "service worker cache version mismatch")
        return "Service worker serves latest cache version.", {"elapsed": elapsed}

    def check_performance_budget(self) -> tuple[str, dict[str, Any]]:
        checks = [
            ("/api/status", 1.0),
            ("/api/folders", 1.0),
            ("/api/apps", 1.0),
            ("/api/brain/search?q=gima&limit=2", 2.0),
        ]
        evidence = {}
        for path, budget in checks:
            _, elapsed = self.get_json(path)
            self.require(elapsed <= budget, f"{path} exceeded {budget}s: {elapsed:.3f}s")
            evidence[path] = elapsed
        return "Core endpoints meet performance budgets.", evidence

    def request(
        self,
        method: str,
        path: str,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
        decode: bool = True,
    ) -> tuple[int, float, Any]:
        connection = http.client.HTTPConnection(self.host, self.port, timeout=self.timeout)
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
        self.require(status < 400, f"{path} returned {status}: {body[:200]}")
        return json.loads(body), elapsed

    def post_json(self, path: str, payload: dict[str, Any]) -> tuple[dict[str, Any], float]:
        status, elapsed, body = self.request(
            "POST",
            path,
            body=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        self.require(status < 400, f"{path} returned {status}: {body[:200]}")
        return json.loads(body), elapsed

    @staticmethod
    def require(condition: bool, message: str) -> None:
        if not condition:
            raise AssertionError(message)

    @staticmethod
    def quote(value: str) -> str:
        from urllib.parse import quote

        return quote(value)

    @staticmethod
    def _parse_local_url(url: str) -> tuple[str, int]:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("base URL must start with http:// or https://")
        return parsed.hostname or "127.0.0.1", parsed.port or (443 if parsed.scheme == "https" else 80)

    def _markdown_report(self, json_path: Path, csv_path: Path) -> str:
        summary = self.summary()
        lines = [
            "# Gima World Test Report",
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
                "## Not Covered By This Live Audit",
                "",
                "- Real browser click testing with Safari/Chrome automation.",
                "- Real microphone, camera, and speech recognition reliability.",
                "- Real iOS/Android/Windows native install packaging.",
                "- Load testing with many simultaneous users.",
                "- Human evaluation of answer quality against frontier AI systems.",
            ]
        )
        return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a live world-class smoke audit against Gima Web UI.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8787")
    parser.add_argument("--workspace", default=str(Path.cwd()))
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()

    tester = GimaWorldTester(args.base_url, Path(args.workspace).resolve(), timeout=args.timeout)
    tester.run()
    json_path, md_path, csv_path = tester.write_reports()
    summary = tester.summary()
    print(json.dumps({"summary": summary, "json": str(json_path), "markdown": str(md_path), "csv": str(csv_path)}, indent=2))
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
