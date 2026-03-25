"""Accumulate results from completed tasks and inject into downstream prompts."""

import difflib
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ContextAccumulator:
    def __init__(self, epic: str = "", workspace_root: str = ""):
        self.epic = epic
        self.workspace_root = Path(workspace_root) if workspace_root else None
        self._completed: dict[str, dict] = {}  # task_id -> result summary
        self._workspace_files: dict[str, str] = {}
        self._recent_changes: dict[str, dict] = {}

    def set_workspace_root(self, workspace_root: str) -> None:
        self.workspace_root = Path(workspace_root)

    def add_result(self, task_id: str, title: str, result: Optional[dict]) -> None:
        """Record a completed task's result for downstream context."""
        summary_entry = {
            "title": title,
            "summary": "",
            "code_blocks": [],
            "files_created": [],
            "workspace_files": [],
            "changed_files": [],
        }

        if result:
            summary_entry["summary"] = result.get("summary", "completed")
            summary_entry["code_blocks"] = result.get("code_blocks", [])
            summary_entry["files_created"] = result.get("files_created", [])
            summary_entry["workspace_files"] = self._extract_workspace_files(result)
            summary_entry["changed_files"] = self._record_changes(summary_entry["workspace_files"])

        self._completed[task_id] = summary_entry
        logger.debug(f"Context accumulated for {task_id}: {title}")

    def build_context(self, dependency_ids: list[str]) -> dict:
        """Build context dict from completed dependency tasks."""
        completed_tasks = []
        all_files = []
        changed_files = []
        workspace_files = []

        for dep_id in dependency_ids:
            if dep_id in self._completed:
                entry = self._completed[dep_id]
                completed_tasks.append(entry)
                all_files.extend(entry.get("files_created", []))
                changed_files.extend(entry.get("changed_files", []))
                workspace_files.extend(entry.get("workspace_files", []))

        return {
            "epic": self.epic,
            "completed_tasks": completed_tasks,
            "files_created": list(set(all_files)),
            "changed_files": self._dedupe_changes(changed_files),
            "workspace_files": self._dedupe_workspace_files(workspace_files),
            "directory_tree": self._build_directory_tree(),
        }

    def get_all_results(self) -> dict[str, dict]:
        return dict(self._completed)

    def _extract_workspace_files(self, result: dict) -> list[dict]:
        workspace_files = []
        for item in result.get("files", []):
            path = item.get("path", "")
            content = item.get("content", "")
            if path and str(content).strip():
                workspace_files.append({
                    "path": path,
                    "content": content,
                    "operation": item.get("operation", "create"),
                })
        if workspace_files:
            return workspace_files

        code_blocks = result.get("code_blocks", [])
        for index, path in enumerate(result.get("files_created", []), 1):
            block = code_blocks[index - 1] if index - 1 < len(code_blocks) else {}
            workspace_files.append({
                "path": path,
                "content": block.get("code", ""),
                "operation": "create",
            })
        return workspace_files

    def _record_changes(self, workspace_files: list[dict]) -> list[dict]:
        changed_files = []
        for item in workspace_files:
            path = item["path"]
            content = item["content"]
            previous = self._workspace_files.get(path, "")
            diff = "\n".join(
                difflib.unified_diff(
                    previous.splitlines(),
                    content.splitlines(),
                    fromfile=f"{path}:before",
                    tofile=f"{path}:after",
                    lineterm="",
                )
            )
            change_record = {
                "path": path,
                "content": content,
                "previous_content": previous,
                "diff": diff,
                "operation": item.get("operation", "create"),
            }
            self._workspace_files[path] = content
            self._recent_changes[path] = change_record
            changed_files.append(change_record)
        return changed_files

    def _build_directory_tree(self) -> str:
        paths = set(self._workspace_files)
        if self.workspace_root and self.workspace_root.exists():
            for path in self.workspace_root.rglob("*"):
                if any(part in {".venv", "__pycache__", "node_modules"} for part in path.parts):
                    continue
                if path.is_file():
                    paths.add(str(path.relative_to(self.workspace_root)))
        if not paths:
            return ""

        tree_lines = []
        for rel_path in sorted(paths):
            depth = len(Path(rel_path).parts) - 1
            tree_lines.append(f"{'  ' * depth}- {Path(rel_path).name}")
        return "\n".join(tree_lines)

    @staticmethod
    def _dedupe_changes(changed_files: list[dict]) -> list[dict]:
        deduped = {}
        for item in changed_files:
            deduped[item["path"]] = item
        return list(deduped.values())

    @staticmethod
    def _dedupe_workspace_files(workspace_files: list[dict]) -> list[dict]:
        deduped = {}
        for item in workspace_files:
            deduped[item["path"]] = item
        return list(deduped.values())
