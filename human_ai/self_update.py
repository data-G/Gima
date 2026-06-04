from __future__ import annotations

import json
import shutil
import subprocess
import tarfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List


IGNORED_DIRS = {".git", ".human-ai", "__pycache__", ".venv", "node_modules"}
IGNORED_FILES = {"config.local.json", ".DS_Store"}


def now_id() -> str:
    stamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")
    return f"update_{stamp}_{uuid.uuid4().hex[:8]}"


@dataclass(frozen=True)
class SelfUpdateRequest:
    update_id: str
    feature: str
    request_dir: Path
    working_copy: Path
    backup_path: Path
    plan_path: Path
    manifest_path: Path
    status: str


class SelfUpdateManager:
    def __init__(self, workspace: Path, data_dir: Path):
        self.workspace = workspace.expanduser().resolve()
        self.root = data_dir.expanduser().resolve() / "self_updates"
        self.requests_dir = self.root / "requests"
        self.backups_dir = self.root / "backups"

    def prepare(self, feature: str) -> SelfUpdateRequest:
        feature = " ".join(feature.strip().split())
        if not feature:
            raise ValueError("Feature description is required")
        self.requests_dir.mkdir(parents=True, exist_ok=True)
        self.backups_dir.mkdir(parents=True, exist_ok=True)
        update_id = now_id()
        request_dir = self.requests_dir / update_id
        working_copy = request_dir / "working_copy"
        request_dir.mkdir(parents=True, exist_ok=False)
        backup_path = self._backup_current(update_id)
        self._copy_current_to(working_copy)
        plan_path = request_dir / "plan.md"
        manifest_path = request_dir / "manifest.json"
        plan_path.write_text(self._plan_text(update_id, feature, backup_path, working_copy), encoding="utf-8")
        manifest = {
            "id": update_id,
            "feature": feature,
            "status": "prepared",
            "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "workspace": str(self.workspace),
            "working_copy": str(working_copy),
            "backup_path": str(backup_path),
            "plan_path": str(plan_path),
            "ready_notes": "",
            "approved_by": "",
            "approved_at": "",
        }
        self._write_manifest(manifest_path, manifest)
        return SelfUpdateRequest(
            update_id,
            feature,
            request_dir,
            working_copy,
            backup_path,
            plan_path,
            manifest_path,
            "prepared",
        )

    def list_requests(self) -> List[dict[str, str]]:
        if not self.requests_dir.exists():
            return []
        rows: List[dict[str, str]] = []
        for path in sorted(self.requests_dir.glob("update_*/manifest.json"), reverse=True):
            rows.append(self._read_manifest(path))
        return rows

    def mark_ready(self, update_id: str, notes: str = "") -> dict[str, str]:
        manifest_path = self._manifest_path(update_id)
        manifest = self._read_manifest(manifest_path)
        manifest["status"] = "ready_for_parent_approval"
        manifest["ready_notes"] = notes
        self._write_manifest(manifest_path, manifest)
        return manifest

    def sync(self, update_id: str, reviewer: str, force: bool = False) -> dict[str, str]:
        manifest_path = self._manifest_path(update_id)
        manifest = self._read_manifest(manifest_path)
        if manifest.get("status") != "ready_for_parent_approval":
            raise PermissionError("Self-update must be marked ready before sync")
        if self._has_live_changes() and not force:
            raise PermissionError("Live workspace has uncommitted changes. Review them or pass --force.")
        backup_path = self._backup_current(f"{update_id}_pre_sync")
        working_copy = Path(manifest["working_copy"])
        if not working_copy.exists():
            raise FileNotFoundError(f"Working copy is missing: {working_copy}")
        self._copy_update_to_workspace(working_copy)
        manifest["status"] = "synced"
        manifest["approved_by"] = reviewer
        manifest["approved_at"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        manifest["sync_backup_path"] = str(backup_path)
        self._write_manifest(manifest_path, manifest)
        return manifest

    def _manifest_path(self, update_id: str) -> Path:
        if "/" in update_id or update_id.startswith("."):
            raise ValueError("Invalid update id")
        path = self.requests_dir / update_id / "manifest.json"
        if not path.exists():
            raise FileNotFoundError(f"Unknown self-update id: {update_id}")
        return path

    def _backup_current(self, label: str) -> Path:
        target = self.backups_dir / f"{label}.tar.gz"
        paths = list(self._source_paths())
        with tarfile.open(target, "w:gz") as archive:
            for path in paths:
                archive.add(path, arcname=str(path.relative_to(self.workspace)))
        return target

    def _copy_current_to(self, target: Path) -> None:
        target.mkdir(parents=True, exist_ok=True)
        for source in self._source_paths():
            relative = source.relative_to(self.workspace)
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

    def _copy_update_to_workspace(self, working_copy: Path) -> None:
        for source in self._walk_files(working_copy):
            relative = source.relative_to(working_copy)
            destination = self.workspace / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

    def _source_paths(self) -> Iterable[Path]:
        tracked = self._git_tracked_paths()
        if tracked:
            return tracked
        return list(self._walk_files(self.workspace))

    def _git_tracked_paths(self) -> List[Path]:
        if not (self.workspace / ".git").exists():
            return []
        result = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=str(self.workspace),
            capture_output=True,
            check=True,
        )
        names = [name for name in result.stdout.decode("utf-8").split("\0") if name]
        return [self.workspace / name for name in names if (self.workspace / name).is_file()]

    def _walk_files(self, root: Path) -> Iterable[Path]:
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(root)
            if any(part in IGNORED_DIRS for part in relative.parts):
                continue
            if path.name in IGNORED_FILES:
                continue
            yield path

    def _has_live_changes(self) -> bool:
        if not (self.workspace / ".git").exists():
            return False
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=str(self.workspace),
            capture_output=True,
            text=True,
            check=True,
        )
        return bool(result.stdout.strip())

    def _plan_text(self, update_id: str, feature: str, backup_path: Path, working_copy: Path) -> str:
        return "\n".join(
            [
                f"# Gima Self-Update Plan: {update_id}",
                "",
                f"Feature request: {feature}",
                "",
                f"Backup created before work: {backup_path}",
                f"Working copy: {working_copy}",
                "",
                "Workflow:",
                "1. Think through the feature and edit only the working copy.",
                "2. Run tests from the working copy.",
                "3. Mark the update ready for parent approval.",
                "4. Sync only after parent approval.",
                "5. Restart Gima after sync if the running process needs the new code.",
                "",
                "Safety rules:",
                "- Do not edit the live workspace during prepare.",
                "- Do not sync without parent approval.",
                "- Always keep the backup path above.",
                "- Keep Gima heart policies active in the new version.",
                "",
            ]
        )

    def _read_manifest(self, path: Path) -> dict[str, str]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_manifest(self, path: Path, manifest: dict[str, str]) -> None:
        path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
