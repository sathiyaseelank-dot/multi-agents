"""Deprecated output writer compatibility layer."""

import logging
from pathlib import Path
import warnings
from typing import Optional

from .project_builder import LANG_TO_EXT, _slugify

logger = logging.getLogger(__name__)


def write_task_output(
    task_id: str,
    task_title: str,
    result: Optional[dict],
    output_dir: str = "output",
) -> list[str]:
    """Write a task's output using the manifest-aware project builder."""
    warnings.warn(
        "orchestrator.output_writer is deprecated; use orchestrator.project_builder instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    if not result:
        return []

    out_path = Path(output_dir)
    structure = {"backend": out_path, "frontend": out_path, "tests": out_path}
    compat_result = dict(result)
    if not compat_result.get("files"):
        compat_result["files"] = []
        for i, block in enumerate(result.get("code_blocks", []), 1):
            lang = block.get("language", "text")
            code = block.get("code", "")
            if not code.strip():
                continue
            ext = LANG_TO_EXT.get(lang.lower(), ".txt")
            slug = _slugify(task_title)
            filename = f"{task_id}-{slug}{ext}" if len(result.get("code_blocks", [])) == 1 else f"{task_id}-{slug}-{i}{ext}"
            compat_result["files"].append({"path": filename, "content": code, "operation": "create"})
        if result.get("raw_text") and not compat_result["files"]:
            compat_result["files"].append({"path": f"{task_id}-{_slugify(task_title)}.txt", "content": result["raw_text"], "operation": "create"})
    created_files = []
    out_path.mkdir(parents=True, exist_ok=True)
    for item in compat_result["files"]:
        filepath = out_path / item["path"]
        filepath.parent.mkdir(parents=True, exist_ok=True)
        content = item.get("content", "")
        filepath.write_text(content if content.endswith("\n") else content + "\n")
        created_files.append(str(filepath))
    return created_files


def write_all_outputs(
    task_results: dict,
    output_dir: str = "output",
) -> dict[str, list[str]]:
    """Write all task outputs to files. Returns {task_id: [file_paths]}."""
    all_files = {}
    for task_id, info in task_results.items():
        title = info.get("title", task_id)
        result = info  # The result dict itself contains code_blocks
        files = write_task_output(task_id, title, result, output_dir)
        if files:
            all_files[task_id] = files
    return all_files
