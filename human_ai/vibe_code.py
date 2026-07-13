from __future__ import annotations

import json
import difflib
import hashlib
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from .memory import MemoryStore, Record, now_iso
from .self_update import SelfUpdateManager, SelfUpdateRequest


TEXT_SUFFIXES = {
    ".csv",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}

IGNORE_PARTS = {".git", ".human-ai", "__pycache__", ".venv", "node_modules"}


@dataclass(frozen=True)
class VibeCodeFile:
    path: str
    score: int
    reason: str
    line_count: int


@dataclass(frozen=True)
class VibeCodePlan:
    update_request: SelfUpdateRequest
    plan_path: Path
    patch_skeleton_path: Path
    snapshot_path: Path
    candidate_files: List[VibeCodeFile]
    record_id: str


@dataclass(frozen=True)
class VibeCodeExecution:
    plan: VibeCodePlan
    status: str
    changed_files: List[str]
    patch_path: Path
    coding_log_path: Path
    test_log_path: Path
    tests_passed: bool


class VibeCodingAgent:
    """Offline coding planner that works only inside a self-update copy."""

    def __init__(self, workspace: Path, data_dir: Path, memory: MemoryStore):
        self.workspace = workspace.expanduser().resolve()
        self.data_dir = data_dir.expanduser().resolve()
        self.memory = memory
        self.self_updates = SelfUpdateManager(self.workspace, self.data_dir)

    def plan(self, feature: str, max_files: int = 10) -> VibeCodePlan:
        feature = " ".join(feature.strip().split())
        if not feature:
            raise ValueError("Feature description is required")
        update_request = self.self_updates.prepare(feature)
        candidate_files = self._rank_files(update_request.working_copy, feature, max_files)
        plan_path = update_request.request_dir / "vibe_code_plan.md"
        patch_skeleton_path = update_request.request_dir / "offline_patch_skeleton.patch"
        snapshot_path = update_request.request_dir / "repo_snapshot.json"

        plan_path.write_text(
            self._plan_text(update_request, feature, candidate_files, patch_skeleton_path),
            encoding="utf-8",
        )
        patch_skeleton_path.write_text(
            self._patch_skeleton_text(feature, candidate_files),
            encoding="utf-8",
        )
        snapshot_path.write_text(
            json.dumps(
                {
                    "kind": "offline_vibe_coding_snapshot",
                    "created_at": now_iso(),
                    "feature": feature,
                    "workspace": str(self.workspace),
                    "working_copy": str(update_request.working_copy),
                    "candidate_files": [file.__dict__ for file in candidate_files],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        self._update_manifest(
            update_request.manifest_path,
            {
                "agent_kind": "offline_vibe_coding",
                "vibe_code_plan_path": str(plan_path),
                "patch_skeleton_path": str(patch_skeleton_path),
                "repo_snapshot_path": str(snapshot_path),
                "candidate_file_count": str(len(candidate_files)),
            },
        )
        record_id = self.memory.add(
            Record(
                category="code",
                subcategory="vibe_agent",
                kind="self_update_plan",
                title=f"Vibe code plan: {feature[:80]}",
                content=plan_path.read_text(encoding="utf-8"),
                keywords="offline coding agent self-update patch plan approval",
                source=str(plan_path),
                status="review",
            )
        )
        return VibeCodePlan(
            update_request,
            plan_path,
            patch_skeleton_path,
            snapshot_path,
            candidate_files,
            record_id,
        )

    def implement(self, feature: str, max_files: int = 10, timeout_seconds: int = 900) -> VibeCodeExecution:
        codex = shutil.which("codex")
        if not codex:
            raise RuntimeError("Codex CLI is required for self-coding but was not found")
        plan = self.plan(feature, max_files=max_files)
        root = plan.update_request.working_copy
        before = self._file_snapshot(root)
        coding_log_path = plan.update_request.request_dir / "coding.log"
        test_log_path = plan.update_request.request_dir / "tests.log"
        patch_path = plan.update_request.request_dir / "implemented.patch"
        prompt = self._implementation_prompt(feature, plan.candidate_files)
        command = [
            codex,
            "exec",
            "--ephemeral",
            "--skip-git-repo-check",
            "--sandbox",
            "workspace-write",
            "--cd",
            str(root),
            prompt,
        ]
        try:
            result = subprocess.run(command, cwd=str(root), capture_output=True, text=True, timeout=timeout_seconds)
            coding_output = result.stdout + ("\n" + result.stderr if result.stderr else "")
        except subprocess.TimeoutExpired as error:
            coding_output = (error.stdout or "") + "\nSelf-coding timed out."
            coding_log_path.write_text(coding_output, encoding="utf-8")
            self._update_manifest(plan.update_request.manifest_path, {"status": "implementation_failed", "coding_error": "timeout"})
            raise TimeoutError("Self-coding timed out inside the isolated working copy") from error
        coding_log_path.write_text(coding_output, encoding="utf-8")
        after = self._file_snapshot(root)
        changed_files = sorted(path for path in set(before) | set(after) if before.get(path) != after.get(path))
        patch_path.write_text(self._patch_text(root, before, changed_files), encoding="utf-8")
        tests_passed, test_output = self._run_tests(root, timeout_seconds=min(timeout_seconds, 600))
        test_log_path.write_text(test_output, encoding="utf-8")
        status = "implemented_pending_review" if result.returncode == 0 and changed_files and tests_passed else "implementation_failed"
        self._update_manifest(
            plan.update_request.manifest_path,
            {
                "status": status,
                "coding_engine": "codex",
                "coding_return_code": str(result.returncode),
                "coding_log_path": str(coding_log_path),
                "implemented_patch_path": str(patch_path),
                "test_log_path": str(test_log_path),
                "tests_passed": str(tests_passed).lower(),
                "changed_files": changed_files,
            },
        )
        return VibeCodeExecution(plan, status, changed_files, patch_path, coding_log_path, test_log_path, tests_passed)

    def _implementation_prompt(self, feature: str, candidate_files: List[VibeCodeFile]) -> str:
        candidates = ", ".join(file.path for file in candidate_files) or "inspect the repository"
        return (
            "Implement this feature in the current copied workspace: " + feature + "\n\n"
            "Candidate files: " + candidates + "\n"
            "Inspect the code first, make the smallest complete change, and add focused tests. "
            "Do not access or edit files outside the current workspace. Do not commit, push, deploy, "
            "change credentials, weaken approval checks, or modify heart policies. Run relevant tests before finishing."
        )

    def _file_snapshot(self, root: Path) -> dict[str, tuple[str, str]]:
        snapshot: dict[str, tuple[str, str]] = {}
        for path in self._walk_text_files(root):
            relative = path.relative_to(root).as_posix()
            text = self._read_text(path)
            snapshot[relative] = (hashlib.sha256(text.encode("utf-8")).hexdigest(), text)
        return snapshot

    def _patch_text(self, root: Path, before: dict[str, tuple[str, str]], changed_files: List[str]) -> str:
        chunks: List[str] = []
        for relative in changed_files:
            old_text = before.get(relative, ("", ""))[1]
            path = root / relative
            new_text = self._read_text(path) if path.exists() else ""
            chunks.extend(
                difflib.unified_diff(
                    old_text.splitlines(keepends=True),
                    new_text.splitlines(keepends=True),
                    fromfile=f"a/{relative}",
                    tofile=f"b/{relative}",
                )
            )
        return "".join(chunks)

    def _run_tests(self, root: Path, timeout_seconds: int) -> tuple[bool, str]:
        if (root / "tests").is_dir():
            command = ["python3", "-m", "unittest", "discover", "-s", "tests"]
        else:
            return True, "No tests directory found; no automatic test command was run.\n"
        try:
            result = subprocess.run(command, cwd=str(root), capture_output=True, text=True, timeout=timeout_seconds)
        except subprocess.TimeoutExpired as error:
            return False, (error.stdout or "") + "\nTests timed out.\n"
        output = result.stdout + ("\n" + result.stderr if result.stderr else "")
        return result.returncode == 0, output

    def _rank_files(self, root: Path, feature: str, max_files: int) -> List[VibeCodeFile]:
        terms = self._terms(feature)
        ranked: List[VibeCodeFile] = []
        for path in self._walk_text_files(root):
            relative = path.relative_to(root).as_posix()
            text = self._read_text(path)
            haystack = f"{relative}\n{text}".casefold()
            score = sum(haystack.count(term) for term in terms)
            if "test" in terms and ("tests/" in relative or relative.startswith("test_")):
                score += 3
            if any(term in relative.casefold() for term in terms):
                score += 5
            if score <= 0:
                continue
            line_count = text.count("\n") + (1 if text else 0)
            ranked.append(
                VibeCodeFile(
                    path=relative,
                    score=score,
                    reason=self._reason(relative, terms),
                    line_count=line_count,
                )
            )
        ranked.sort(key=lambda row: (-row.score, row.path))
        if ranked:
            return ranked[: max(1, max_files)]
        fallback = [
            VibeCodeFile(path=path.relative_to(root).as_posix(), score=0, reason="fallback text file", line_count=0)
            for path in self._walk_text_files(root)
        ]
        return fallback[: max(1, max_files)]

    def _walk_text_files(self, root: Path) -> Iterable[Path]:
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(root)
            if any(part in IGNORE_PARTS for part in relative.parts):
                continue
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            yield path

    def _terms(self, feature: str) -> List[str]:
        raw = re.findall(r"[a-zA-Z0-9_]{3,}", feature.casefold())
        extras: List[str] = []
        if "vibe" in raw or "coding" in raw or "code" in raw:
            extras.extend(["self_update", "gima", "cli", "test"])
        return sorted(set(raw + extras))

    def _read_text(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    def _reason(self, relative: str, terms: List[str]) -> str:
        matches = [term for term in terms if term in relative.casefold()]
        if matches:
            return "path matches " + ", ".join(matches[:4])
        return "content matches request terms"

    def _plan_text(
        self,
        request: SelfUpdateRequest,
        feature: str,
        candidate_files: List[VibeCodeFile],
        patch_skeleton_path: Path,
    ) -> str:
        lines = [
            f"# Offline Vibe Coding Plan: {request.update_id}",
            "",
            f"Feature request: {feature}",
            "",
            "Mode: offline copied-workspace coding.",
            "",
            f"Working copy: {request.working_copy}",
            f"Backup: {request.backup_path}",
            f"Patch skeleton: {patch_skeleton_path}",
            "",
            "Candidate files:",
        ]
        for file in candidate_files:
            lines.append(f"- `{file.path}` score={file.score} lines={file.line_count} reason={file.reason}")
        lines.extend(
            [
                "",
                "Suggested workflow:",
                "1. Edit only the working copy.",
                "2. Keep changes small and tied to the feature request.",
                "3. Add or update focused tests in the working copy.",
                "4. Run the relevant tests from the working copy.",
                "5. Mark ready with `self-update-ready` only after tests pass.",
                "6. Sync to live Gima only after parent approval.",
                "",
                "Safety notes:",
                "- This plan does not modify the live workspace.",
                "- This agent must not bypass Gima heart policies or scoped permissions.",
                "- Store reasoning as human-language notes, not hidden machine instructions.",
                "",
            ]
        )
        return "\n".join(lines)

    def _patch_skeleton_text(self, feature: str, candidate_files: List[VibeCodeFile]) -> str:
        lines = [
            "# Offline patch skeleton for Gima vibe coding",
            f"# Feature: {feature}",
            "# Fill this in inside the working copy, then run tests before approval.",
            "",
        ]
        for file in candidate_files:
            lines.extend(
                [
                    f"## {file.path}",
                    f"- Why this file: {file.reason}",
                    "- Intended change:",
                    "- Tests to run:",
                    "",
                ]
            )
        return "\n".join(lines)

    def _update_manifest(self, path: Path, values: dict[str, str]) -> None:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest.update(values)
        path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
