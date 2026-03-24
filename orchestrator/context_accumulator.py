"""Accumulate results from completed tasks and inject into downstream prompts."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ContextAccumulator:
    def __init__(self, epic: str = ""):
        self.epic = epic
        self._completed: dict[str, dict] = {}  # task_id -> result summary

    def add_result(self, task_id: str, title: str, result: Optional[dict]) -> None:
        """Record a completed task's result for downstream context."""
        summary_entry = {"title": title, "summary": "", "code_blocks": [], "files_created": []}

        if result:
            summary_entry["summary"] = result.get("summary", "completed")
            summary_entry["code_blocks"] = result.get("code_blocks", [])
            summary_entry["files_created"] = result.get("files_created", [])

        self._completed[task_id] = summary_entry
        logger.debug(f"Context accumulated for {task_id}: {title}")

    def build_context(self, dependency_ids: list[str]) -> dict:
        """Build context dict from completed dependency tasks."""
        completed_tasks = []
        all_files = []

        for dep_id in dependency_ids:
            if dep_id in self._completed:
                entry = self._completed[dep_id]
                completed_tasks.append(entry)
                all_files.extend(entry.get("files_created", []))

        return {
            "epic": self.epic,
            "completed_tasks": completed_tasks,
            "files_created": list(set(all_files)),
        }

    def get_all_results(self) -> dict[str, dict]:
        return dict(self._completed)
