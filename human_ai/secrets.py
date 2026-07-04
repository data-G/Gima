from __future__ import annotations

import getpass
import os
from pathlib import Path
from typing import Iterable


SECRET_ENV_KEYS = {
    "openai": "OPENAI_API_KEY",
    "chatgpt": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
    "xai": "XAI_API_KEY",
    "grok": "XAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}


def secrets_env_path(workspace: Path) -> Path:
    return workspace.expanduser().resolve() / ".human-ai" / "secrets.env"


def load_secret_env(workspace: Path) -> Path:
    path = secrets_env_path(workspace)
    if not path.exists():
        return path
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = _unquote(value.strip())
        if key and key not in os.environ:
            os.environ[key] = value
    return path


def configure_teacher_secrets(workspace: Path, providers: Iterable[str], force: bool = False) -> Path:
    path = secrets_env_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = _read_secret_rows(path)
    for provider in providers:
        env_key = SECRET_ENV_KEYS[provider]
        if existing.get(env_key) and not force:
            continue
        label = {
            "OPENAI_API_KEY": "OpenAI/ChatGPT",
            "GEMINI_API_KEY": "Google Gemini",
            "ANTHROPIC_API_KEY": "Anthropic/Claude",
            "XAI_API_KEY": "xAI/Grok",
            "DEEPSEEK_API_KEY": "DeepSeek",
            "OPENROUTER_API_KEY": "OpenRouter",
        }.get(env_key, env_key)
        value = getpass.getpass(f"{label} API key for {env_key}: ").strip()
        if value:
            existing[env_key] = value
    _write_secret_rows(path, existing)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    load_secret_env(workspace)
    return path


def save_teacher_secret(workspace: Path, provider: str, value: str) -> Path:
    provider = provider.casefold().strip()
    if provider == "chatgpt":
        provider = "openai"
    if provider not in SECRET_ENV_KEYS:
        raise ValueError(f"Unknown API provider: {provider}")
    secret = value.strip()
    if not secret:
        raise ValueError("API key is required")
    path = secrets_env_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = _read_secret_rows(path)
    env_key = SECRET_ENV_KEYS[provider]
    rows[env_key] = secret
    _write_secret_rows(path, rows)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    # A key replaced from the web UI must take effect in this running process.
    os.environ[env_key] = secret
    return path


def teacher_secret_status(workspace: Path) -> list[dict[str, str]]:
    path = secrets_env_path(workspace)
    rows = _read_secret_rows(path)
    seen: set[str] = set()
    status: list[dict[str, str]] = []
    for provider, env_key in SECRET_ENV_KEYS.items():
        if provider == "chatgpt" or env_key in seen:
            continue
        seen.add(env_key)
        value = rows.get(env_key) or os.environ.get(env_key, "")
        status.append(
            {
                "provider": provider,
                "env_key": env_key,
                "available": "yes" if value else "no",
                "masked": _mask(value),
            }
        )
    return status


def _read_secret_rows(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    rows: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        rows[key.strip()] = _unquote(value.strip())
    return rows


def _write_secret_rows(path: Path, rows: dict[str, str]) -> None:
    lines = [
        "# Private Gima teacher-model API keys.",
        "# This file is local runtime state and must not be committed.",
    ]
    for key in sorted(rows):
        lines.append(f"{key}={_quote(rows[key])}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return value[:4] + "..." + value[-4:]
