"""Write generated code blocks to files in the output directory."""

import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Map language tags to file extensions
LANG_TO_EXT = {
    "python": ".py",
    "py": ".py",
    "javascript": ".js",
    "js": ".js",
    "typescript": ".ts",
    "ts": ".ts",
    "jsx": ".jsx",
    "tsx": ".tsx",
    "html": ".html",
    "css": ".css",
    "json": ".json",
    "yaml": ".yaml",
    "yml": ".yml",
    "sql": ".sql",
    "bash": ".sh",
    "sh": ".sh",
    "rust": ".rs",
    "go": ".go",
    "java": ".java",
    "text": ".txt",
}


def write_task_output(
    task_id: str,
    task_title: str,
    result: Optional[dict],
    output_dir: str = "output",
) -> list[str]:
    """Write a task's code blocks to files. Returns list of created file paths."""
    if not result:
        return []

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    created_files = []
    code_blocks = result.get("code_blocks", [])

    if not code_blocks:
        # No code blocks — write raw text if present
        raw = result.get("raw_text", "")
        if raw:
            slug = _slugify(task_title)
            filepath = out_path / f"{task_id}-{slug}.txt"
            filepath.write_text(raw)
            created_files.append(str(filepath))
            logger.info(f"Wrote raw output: {filepath}")
        return created_files

    for i, block in enumerate(code_blocks):
        lang = block.get("language", "text")
        code = block.get("code", "")
        if not code.strip():
            continue

        ext = LANG_TO_EXT.get(lang.lower(), ".txt")
        slug = _slugify(task_title)

        if len(code_blocks) == 1:
            filename = f"{task_id}-{slug}{ext}"
        else:
            filename = f"{task_id}-{slug}-{i + 1}{ext}"

        filepath = out_path / filename
        filepath.write_text(code + "\n")
        created_files.append(str(filepath))
        logger.info(f"Wrote {lang} code: {filepath} ({len(code.splitlines())} lines)")

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


def _slugify(text: str) -> str:
    """Convert text to a safe filename slug."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower())
    return slug.strip("-")[:40]
