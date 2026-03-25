"""Repair analysis and prompt construction."""

from __future__ import annotations

import re
from pathlib import Path


def classify_error(error_message: str, phase: str = "") -> str:
    message = f"{phase}\n{error_message}".lower()
    if "syntax" in message or "indent" in message:
        return "syntax"
    if "import" in message or "module not found" in message or "no module named" in message:
        return "import"
    if "pip install" in message or "dependency" in message or "requirements" in message:
        return "dependency"
    return "runtime"


def choose_repair_agent(file_path: str | None, error_type: str) -> str:
    path = (file_path or "").replace("\\", "/")
    if error_type == "dependency":
        return "opencode"
    if path.startswith("frontend/"):
        return "gemini"
    if path.startswith("tests/"):
        return "kilo"
    return "opencode"


def collect_relevant_files(
    project_dir: str,
    file_path: str | None = None,
    workspace_files: list[dict] | None = None,
    limit: int = 4,
) -> list[dict]:
    selected = []
    project_path = Path(project_dir)

    if file_path:
        candidate = project_path / file_path
        if candidate.exists():
            selected.append({"path": file_path, "content": candidate.read_text(errors="replace")})

    for item in workspace_files or []:
        if len(selected) >= limit:
            break
        if item["path"] == file_path:
            continue
        selected.append({"path": item["path"], "content": item.get("content", "")})

    if not selected:
        for candidate in sorted(project_path.rglob("*")):
            if len(selected) >= limit:
                break
            if candidate.is_file() and not any(part in {".venv", "__pycache__", "node_modules"} for part in candidate.parts):
                selected.append({
                    "path": str(candidate.relative_to(project_path)),
                    "content": candidate.read_text(errors="replace"),
                })
    return selected


def build_repair_prompt(
    project_dir: str,
    error_message: str,
    error_type: str,
    relevant_files: list[dict],
    expected_behavior: str,
    target_file: str | None = None,
) -> str:
    file_sections = []
    for item in relevant_files:
        file_sections.append(
            f"File: {item['path']}\n```text\n{item.get('content', '')}\n```"
        )

    target_path = target_file or (relevant_files[0]["path"] if relevant_files else "backend/app.py")
    return (
        f"You are fixing a {error_type} issue in a generated software project.\n"
        f"Project root: {project_dir}\n"
        f"Target file: {target_path}\n"
        f"Expected behavior: {expected_behavior}\n"
        f"Observed error:\n{error_message}\n\n"
        "Relevant workspace files:\n"
        f"{chr(10).join(file_sections)}\n\n"
        "Return JSON only:\n"
        "{\n"
        '  "files": [\n'
        "    {\n"
        f'      "path": "{target_path}",\n'
        '      "content": "<full file content>",\n'
        '      "operation": "update"\n'
        "    }\n"
        "  ],\n"
        '  "summary": "<short repair summary>",\n'
        '  "errors": []\n'
        "}\n"
    )
