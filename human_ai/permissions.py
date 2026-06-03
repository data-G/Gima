from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, List

from .config import Config
from .memory import MemoryStore, now_iso


ALLOWED_SCOPES = {"camera", "files", "microphone", "tools", "web"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class PermissionGrant:
    scopes: List[str]
    created_at: str
    expires_at: str


class PermissionManager:
    """Store short-lived local capability grants without bypassing OS controls."""

    def __init__(self, config: Config, memory: MemoryStore):
        self.config = config
        self.memory = memory
        self.path = config.resolved_data_dir / "permission_session.json"

    def grant(self, scopes: Iterable[str], minutes: int) -> PermissionGrant:
        selected = sorted(set(scopes))
        unknown = set(selected) - ALLOWED_SCOPES
        if not selected:
            raise ValueError("At least one permission scope is required")
        if unknown:
            raise ValueError(f"Unknown permission scope(s): {', '.join(sorted(unknown))}")
        duration = max(1, min(minutes, self.config.permissions.maximum_minutes))
        grant = PermissionGrant(
            scopes=selected,
            created_at=now_iso(),
            expires_at=(_now() + timedelta(minutes=duration)).isoformat(timespec="seconds"),
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(asdict(grant), indent=2), encoding="utf-8")
        os.chmod(self.path, 0o600)
        self.memory.audit("permission_grant", ",".join(selected), f"Expires {grant.expires_at}", "ok")
        return grant

    def revoke(self) -> None:
        if self.path.exists():
            self.path.unlink()
        self.memory.audit("permission_revoke", "all", "Scoped permission session removed", "ok")

    def current(self) -> PermissionGrant | None:
        if not self.path.exists():
            return None
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        grant = PermissionGrant(**raw)
        if datetime.fromisoformat(grant.expires_at) <= _now().astimezone():
            self.path.unlink()
            return None
        return grant

    def require(self, scope: str) -> None:
        if not self.config.permissions.require_scoped_grants:
            return
        grant = self.current()
        if not grant or scope not in grant.scopes:
            raise PermissionError(
                f"Permission scope '{scope}' is not active. "
                f"Run permission-grant from the terminal for a short local session."
            )

    def verify_parent_password(self, password: str) -> bool:
        expected = self.config.parent_approval.password_sha256
        if not expected:
            raise PermissionError("Parent approval password hash is not configured")
        actual = hashlib.sha256(password.encode("utf-8")).hexdigest()
        ok = actual == expected
        self.memory.append_parent_approval(
            "password_check",
            "parent_approval",
            "ok" if ok else "failed",
            "local parent approval check",
        )
        return ok
