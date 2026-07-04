from __future__ import annotations

import json
import os
import signal
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Optional

from .config import Config
from .memory import MemoryStore


class BrainServer:
    def __init__(self, config: Config, memory: MemoryStore):
        self.config = config
        self.memory = memory
        self.pid_path = config.resolved_data_dir / "brain.pid"
        self.log_path = config.resolved_data_dir / "brain.log"

    def status(self) -> dict:
        pid = self._pid()
        if not pid:
            models = self._models()
            if models is not None and self._models_match_config(models):
                return {"running": True, "ready": True, "state": "running", "pid": None, "models": models}
            return {"running": False, "ready": False, "state": "stopped", "pid": None, "models": None}
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            self.pid_path.unlink(missing_ok=True)
            return {"running": False, "ready": False, "state": "stopped", "pid": None, "models": None}
        except PermissionError:
            # Restricted launch/test environments may forbid signal probes even
            # when the local server is healthy; endpoint health remains authoritative.
            pass
        if not self._pid_matches_brain(pid):
            self.pid_path.unlink(missing_ok=True)
            models = self._models()
            if models is not None and self._models_match_config(models):
                return {"running": True, "ready": True, "state": "running", "pid": None, "models": models}
            return {"running": False, "ready": False, "state": "stopped", "pid": None, "models": None}
        models = self._models()
        ready = models is not None
        return {"running": True, "ready": ready, "state": "running" if ready else "starting", "pid": pid, "models": models}

    def start(self) -> int:
        current = self.status()
        if current["running"]:
            return int(current["pid"] or 0)
        model_path = Path(self.config.model.model_path).expanduser().resolve()
        if not model_path.exists():
            raise FileNotFoundError(f"Brain model not found: {model_path}")
        executable = shutil.which("llama-server")
        if not executable:
            local_executable = Path("~/.local/bin/llama-server").expanduser()
            if local_executable.exists():
                executable = str(local_executable)
        if not executable:
            raise RuntimeError("Brain server requires llama-server from llama.cpp")
        command = [
            executable,
            "--model",
            str(model_path),
            "--host",
            self.config.model.host,
            "--port",
            str(self.config.model.port),
            "--ctx-size",
            str(self.config.model.context_size),
            "--parallel",
            "1",
            "--cache-ram",
            "512",
            "--device",
            self.config.model.device,
            "--gpu-layers",
            str(self.config.model.gpu_layers),
            "--jinja",
        ]
        if not self.config.model.warmup:
            command.append("--no-warmup")
        self.config.resolved_data_dir.mkdir(parents=True, exist_ok=True)
        log = self.log_path.open("a", encoding="utf-8")
        process = subprocess.Popen(
            command,
            cwd=str(self.config.resolved_workspace),
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        self.pid_path.write_text(str(process.pid), encoding="utf-8")
        self.memory.audit("brain_start", str(model_path), f"pid={process.pid}", "ok")
        self._wait_until_ready(process)
        return process.pid

    def stop(self) -> None:
        pid = self._pid()
        if not pid:
            return
        try:
            os.kill(pid, signal.SIGTERM)
            for _ in range(20):
                time.sleep(0.2)
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    break
            else:
                os.kill(pid, signal.SIGKILL)
        finally:
            self.pid_path.unlink(missing_ok=True)
            self.memory.audit("brain_stop", str(pid), "server stopped", "ok")

    def _pid(self) -> Optional[int]:
        if not self.pid_path.exists():
            return None
        try:
            return int(self.pid_path.read_text(encoding="utf-8").strip())
        except ValueError:
            self.pid_path.unlink(missing_ok=True)
            return None

    def _models(self) -> dict | None:
        try:
            with urllib.request.urlopen(
                f"http://{self.config.model.host}:{self.config.model.port}/v1/models",
                timeout=3,
            ) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception:
            return None

    def _models_match_config(self, models: dict) -> bool:
        configured = {
            str(getattr(self.config.model, "model", "") or "").casefold(),
            Path(str(getattr(self.config.model, "model_path", "") or "")).expanduser().name.casefold(),
        }
        configured.discard("")
        for row in (models.get("data") or []) + (models.get("models") or []):
            names = {
                str(row.get("id", "")).casefold(),
                str(row.get("name", "")).casefold(),
                str(row.get("model", "")).casefold(),
            }
            if configured & names:
                return True
        return False

    def _pid_matches_brain(self, pid: int) -> bool:
        if os.name == "nt":
            return True
        try:
            result = subprocess.run(
                ["/bin/ps", "-p", str(pid), "-o", "command="],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return True
        command = result.stdout.strip()
        if result.returncode != 0 or not command:
            return True
        return "llama-server" in command and str(Path(self.config.model.model_path).expanduser()) in command

    def _wait_until_ready(self, process: subprocess.Popen) -> None:
        url = f"http://{self.config.model.host}:{self.config.model.port}/v1/models"
        for _ in range(300):
            if process.poll() is not None:
                self.pid_path.unlink(missing_ok=True)
                raise RuntimeError(
                    f"Brain server exited with code {process.returncode}. See {self.log_path}"
                )
            try:
                with urllib.request.urlopen(url, timeout=2):
                    return
            except Exception:
                time.sleep(1)
        raise RuntimeError(f"Brain server did not become ready. See {self.log_path}")
