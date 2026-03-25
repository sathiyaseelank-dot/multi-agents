"""Project Builder — deterministically assemble task manifests into a project tree."""

import logging
import os
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Map task types to directory names
TYPE_TO_DIR = {
    "backend": "backend",
    "frontend": "frontend",
    "testing": "tests",
}

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

# Keywords to infer meaningful filenames from code content
# Patterns are used with re.search(), so special chars need escaping
KEYWORD_TO_FILENAME = {
    # Backend patterns
    r"class\s+\w+\s*\(\s*.*Model": "models.py",
    r"def\s+login": "auth.py",
    r"def\s+register": "auth.py",
    r"def\s+authenticate": "auth.py",
    r"from\s+flask\s+import\s+Flask": "app.py",
    r"@app\.route": "routes.py",
    r"Blueprint": "routes.py",
    r"sqlalchemy": "models.py",
    # Frontend patterns
    r"import\s+React": "App.jsx",
    r"export\s+default\s+function": "index.js",
    r"export\s+default\s+class": "index.js",
    r"ReactDOM": "index.js",
    # Test patterns
    r"def\s+test_": "test_file.py",
    r"import\s+pytest": "test_file.py",
    r"describe\s*\(": "test_file.js",
    r"it\s*\(": "test_file.js",
}


def create_structure(project_dir: str) -> dict[str, Path]:
    """Create the basic project directory structure.

    Args:
        project_dir: Root directory for the project.

    Returns:
        Dictionary mapping directory names to their Path objects.
    """
    project_path = Path(project_dir)
    project_path.mkdir(parents=True, exist_ok=True)

    dirs = {}
    for dir_name in TYPE_TO_DIR.values():
        dir_path = project_path / dir_name
        dir_path.mkdir(parents=True, exist_ok=True)
        dirs[dir_name] = dir_path
        logger.debug(f"Created directory: {dir_path}")

    logger.info(f"Created project structure in {project_dir}/")
    return dirs


def _slugify(text: str) -> str:
    """Convert text to a safe filename slug."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower())
    return slug.strip("-")[:40]


def _infer_filename(code: str, task_type: str, task_title: str) -> str:
    """Infer a meaningful filename from code content.

    Args:
        code: The code content to analyze.
        task_type: The type of task (backend/frontend/testing).
        task_title: The task title as fallback.

    Returns:
        A suggested filename.
    """
    code_lower = code.lower()

    # Check for test files first
    if task_type == "testing":
        if "def test_" in code_lower or "import pytest" in code_lower:
            # Try to extract what's being tested from the title
            title_slug = _slugify(task_title)
            if "test" not in title_slug:
                return f"test_{title_slug}.py"
            return f"{title_slug}.py"

    # Check keyword patterns (use IGNORECASE for case-insensitive matching)
    for pattern, filename in KEYWORD_TO_FILENAME.items():
        if re.search(pattern, code, re.IGNORECASE):
            # For test files, ensure test_ prefix
            if task_type == "testing" and filename.startswith("test_"):
                return filename
            if task_type == "testing" and not filename.startswith("test_"):
                # Convert to test filename
                base = filename.replace(".py", "").replace(".js", "")
                return f"test_{base}.py"
            return filename

    # Fallback to task title-based naming
    if task_title:
        title_slug = _slugify(task_title)
        return f"{title_slug}.py"
    return "code.py"


def _get_extension(language: str, task_type: str) -> str:
    """Get the file extension for a language, with task-type-specific defaults."""
    ext = LANG_TO_EXT.get(language.lower(), None)
    if ext:
        return ext

    # Default extensions by task type
    if task_type == "backend":
        return ".py"
    elif task_type == "frontend":
        return ".js"
    elif task_type == "testing":
        return ".py"
    return ".txt"


def write_files(
    task_results: dict,
    project_dirs: dict[str, Path],
) -> list[str]:
    """Write manifest files to the project tree in deterministic order."""
    created_files = []
    project_root = next(iter(project_dirs.values())).parent if project_dirs else Path(".")
    manifest_entries = []

    for task_id, info in task_results.items():
        manifest_entries.extend(_normalize_task_result(task_id, info))

    for entry in sorted(manifest_entries, key=lambda item: item["path"]):
        rel_path = _safe_relative_path(entry["path"])
        filepath = project_root / rel_path
        filepath.parent.mkdir(parents=True, exist_ok=True)
        content = entry.get("content", "")
        filepath.write_text(content if content.endswith("\n") else content + "\n")
        created_files.append(str(filepath))
        logger.info("Wrote artifact: %s", filepath)

    return created_files


def create_entrypoint(project_dirs: dict[str, Path], created_files: list[str]) -> Optional[str]:
    """Create a minimal Flask entrypoint if backend code exists.

    Args:
        project_dirs: Dictionary mapping directory names to Paths.
        created_files: List of files that were created.

    Returns:
        Path to created entrypoint, or None if not created.
    """
    backend_dir = project_dirs.get("backend")
    if not backend_dir:
        return None

    # Check if we have Python backend files
    backend_files = [f for f in created_files if "/backend/" in f and f.endswith(".py")]

    if not backend_files:
        return None
    if any(Path(path).name == "app.py" for path in backend_files):
        return str(backend_dir / "app.py")

    # Find module names to import (excluding app.py itself)
    modules_to_import = []
    for filepath in backend_files:
        filename = Path(filepath).name
        if filename != "app.py" and filename.endswith(".py"):
            module_name = filename[:-3]  # Remove .py
            # Skip if it looks like a routes/models file we'll import
            if module_name not in ("app", "main", "wsgi"):
                modules_to_import.append(module_name)

    # Generate Flask app.py content
    app_content = _generate_flask_app(modules_to_import)
    app_path = backend_dir / "app.py"
    app_path.write_text(app_content)

    logger.info(f"Created Flask entrypoint: {app_path}")
    return str(app_path)


def _generate_flask_app(modules: list[str]) -> str:
    """Generate a minimal Flask application.

    Args:
        modules: List of module names to import.

    Returns:
        Flask app.py content.
    """
    # Build import statements
    imports = ["from flask import Flask"]
    for module in modules[:5]:  # Limit imports to avoid clutter
        imports.append(f"import {module}")

    imports_str = "\n".join(imports)

    # Build app initialization
    app_init = "app = Flask(__name__)"

    # Build a basic route
    basic_route = '''
@app.route("/")
def index():
    return {"status": "ok", "message": "Multi-Agent Orchestrator API"}
'''

    # Build main block
    main_block = '''
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
'''

    return f'''"""Auto-generated Flask application entrypoint.

This file was created by the Project Builder module.
Run with: python app.py
"""

{imports_str}

{app_init}
{basic_route}
{main_block}
'''


def generate_requirements(
    project_dirs: dict[str, Path],
    has_backend: bool,
    has_tests: bool,
) -> Optional[str]:
    """Generate requirements.txt for the backend.

    Args:
        project_dirs: Dictionary mapping directory names to Paths.
        has_backend: Whether backend code exists.
        has_tests: Whether test code exists.

    Returns:
        Path to created requirements.txt, or None if not created.
    """
    backend_dir = project_dirs.get("backend")
    if not backend_dir:
        return None

    if not has_backend:
        return None

    requirements = []

    # Always add Flask for backend
    if has_backend:
        requirements.append("flask>=2.3.0")

    # Add pytest if tests exist
    if has_tests:
        requirements.append("pytest>=7.4.0")

    # Add common extensions that might be needed
    requirements.append("python-dotenv>=1.0.0")

    requirements_path = backend_dir / "requirements.txt"
    requirements_path.write_text("\n".join(requirements) + "\n")

    logger.info(f"Created requirements.txt: {requirements_path}")
    return str(requirements_path)


def build_project(
    task_results: dict,
    project_dir: str = "project",
) -> dict:
    """Build a structured project from task results."""
    logger.info(f"Building project in {project_dir}/")

    # Step 1: Create directory structure
    structure = create_structure(project_dir)

    # Step 2: Write files to appropriate directories
    created_files = write_files(task_results, structure)

    # Step 3: Create Flask entrypoint if backend exists
    has_backend = any(
        info.get("type") == "backend" and _normalize_task_result(task_id, info)
        for task_id, info in task_results.items()
    )
    entrypoint = None
    if has_backend:
        entrypoint = create_entrypoint(structure, created_files)

    result = {
        "project_dir": project_dir,
        "files_created": created_files,
        "entrypoint": entrypoint,
        "requirements": None,
        "structure": {k: str(v) for k, v in structure.items()},
    }

    logger.info(f"Project built: {len(created_files)} files created")
    if entrypoint:
        logger.info(f"Entrypoint: {entrypoint}")

    return result


def _normalize_task_result(task_id: str, info: dict) -> list[dict]:
    task_type = info.get("type", "backend")
    task_title = info.get("title", task_id)

    manifest_files = info.get("files") or []
    normalized = []
    for item in manifest_files:
        path = item.get("path", "")
        content = item.get("content", "")
        if path and str(content).strip():
            normalized.append({
                "path": path,
                "content": content,
                "operation": item.get("operation", "create"),
            })

    if normalized:
        return normalized

    code_blocks = info.get("code_blocks", [])
    target_dir_name = TYPE_TO_DIR.get(task_type, "backend")
    for i, block in enumerate(code_blocks):
        lang = block.get("language", "text")
        code = block.get("code", "")
        if not code.strip():
            continue

        ext = _get_extension(lang, task_type)
        filename = _infer_filename(code, task_type, task_title)
        if len(code_blocks) > 1:
            name_parts = filename.rsplit(".", 1)
            if len(name_parts) == 2:
                filename = f"{name_parts[0]}-{i + 1}.{name_parts[1]}"
            else:
                filename = f"{filename}-{i + 1}"
        if task_type == "testing" and not filename.startswith("test_"):
            filename = f"test_{filename}"
        if not os.path.splitext(filename)[1]:
            filename = f"{filename}{ext}"
        normalized.append({
            "path": f"{target_dir_name}/{filename}",
            "content": code,
            "operation": "create",
        })

    if normalized:
        return normalized

    raw = info.get("raw_text", "")
    if raw:
        return [{
            "path": f"{target_dir_name}/{_slugify(task_title)}.txt",
            "content": raw,
            "operation": "create",
        }]
    return []


def _safe_relative_path(path: str) -> Path:
    rel_path = Path(path)
    if rel_path.is_absolute():
        raise ValueError(f"Artifact paths must be relative: {path}")
    parts = [part for part in rel_path.parts if part not in ("", ".")]
    if any(part == ".." for part in parts):
        raise ValueError(f"Artifact path escapes project root: {path}")
    return Path(*parts)
