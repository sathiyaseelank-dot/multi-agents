"""Infer and write dependency manifests for generated projects."""

from __future__ import annotations

import ast
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

PYTHON_DEPENDENCY_MAP = {
    "flask": "flask>=2.3.0",
    "pytest": "pytest>=7.4.0",
    "requests": "requests>=2.31.0",
    "sqlalchemy": "sqlalchemy>=2.0.0",
    "dotenv": "python-dotenv>=1.0.0",
}


def resolve_dependencies(project_dir: str) -> dict:
    project_path = Path(project_dir)
    python_packages = _infer_python_dependencies(project_path)
    frontend_package = _infer_frontend_package(project_path)

    requirements_path = project_path / "requirements.txt"
    requirements_path.write_text("\n".join(sorted(python_packages)) + ("\n" if python_packages else ""))

    package_json_path = None
    if frontend_package:
        package_json_path = project_path / "package.json"
        package_json_path.write_text(json.dumps(frontend_package, indent=2) + "\n")

    result = {
        "requirements": str(requirements_path),
        "package_json": str(package_json_path) if package_json_path else None,
        "python_dependencies": sorted(python_packages),
        "frontend_dependencies": sorted(frontend_package.get("dependencies", {}).keys()) if frontend_package else [],
    }
    logger.info("Dependency resolution complete for %s", project_dir)
    return result


def _infer_python_dependencies(project_path: Path) -> set[str]:
    dependencies = set()
    for path in project_path.rglob("*.py"):
        if any(part in {".venv", "__pycache__", "node_modules"} for part in path.parts):
            continue
        content = path.read_text()
        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    package = alias.name.split(".")[0]
                    if package in PYTHON_DEPENDENCY_MAP:
                        dependencies.add(PYTHON_DEPENDENCY_MAP[package])
            elif isinstance(node, ast.ImportFrom) and node.module:
                package = node.module.split(".")[0]
                if package in PYTHON_DEPENDENCY_MAP:
                    dependencies.add(PYTHON_DEPENDENCY_MAP[package])
    return dependencies


def _infer_frontend_package(project_path: Path) -> dict | None:
    frontend_dir = project_path / "frontend"
    if not frontend_dir.exists():
        return None

    js_files = list(frontend_dir.rglob("*.js")) + list(frontend_dir.rglob("*.jsx")) + list(frontend_dir.rglob("*.tsx"))
    if not js_files:
        return None

    uses_react = False
    for path in js_files:
        content = path.read_text(errors="replace")
        if "react" in content.lower():
            uses_react = True
            break

    dependencies = {}
    dev_dependencies = {}
    scripts = {}
    if uses_react:
        dependencies["react"] = "^18.2.0"
        dependencies["react-dom"] = "^18.2.0"
        dev_dependencies["vite"] = "^5.4.0"
        scripts["build"] = "vite build"

    return {
        "name": project_path.name,
        "private": True,
        "version": "0.1.0",
        "scripts": scripts or {"build": "echo 'No frontend build configured'"},
        "dependencies": dependencies,
        "devDependencies": dev_dependencies,
    }
