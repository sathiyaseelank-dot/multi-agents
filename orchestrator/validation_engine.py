"""Validation engine for generated project artifacts."""

from __future__ import annotations

import ast
import importlib
import logging
import sys
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)


def validate_project(project_dir: str, expected_files: list[str] | None = None) -> dict:
    project_path = Path(project_dir)
    errors = []
    checked_files = []

    for expected in expected_files or []:
        path = Path(expected)
        if not path.exists():
            errors.append({
                "path": str(path.relative_to(project_path)),
                "message": "Expected file was not created",
                "kind": "missing_file",
            })

    for path in sorted(project_path.rglob("*")):
        if path.is_dir():
            continue
        if any(part in {".venv", "__pycache__", "node_modules"} for part in path.parts):
            continue
        rel_path = str(path.relative_to(project_path))
        checked_files.append(rel_path)

        content = path.read_text(errors="replace")
        if not content.strip():
            errors.append({"path": rel_path, "message": "File is empty", "kind": "empty_file"})
            continue

        if path.suffix == ".py":
            syntax_error = _validate_python_syntax(path, content)
            if syntax_error:
                errors.append({"path": rel_path, "message": syntax_error, "kind": "syntax"})
                continue

            import_errors = _validate_local_imports(project_path, path, content)
            errors.extend(import_errors)

    result = {
        "success": not errors,
        "errors": errors,
        "checked_files": checked_files,
    }
    logger.info("Validation complete for %s: success=%s errors=%s", project_dir, result["success"], len(errors))
    return result


def _validate_python_syntax(path: Path, content: str) -> str | None:
    try:
        compile(content, str(path), "exec")
    except SyntaxError as exc:
        return f"Syntax error at line {exc.lineno}: {exc.msg}"
    return None


def _validate_local_imports(project_dir: Path, path: Path, content: str) -> list[dict]:
    errors = []
    try:
        tree = ast.parse(content, filename=str(path))
    except SyntaxError:
        return errors

    with _project_on_syspath(project_dir):
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name.split(".")[0]
                    if _is_local_module(project_dir, name):
                        try:
                            _import_module_fresh(name)
                        except Exception as exc:
                            errors.append({
                                "path": str(path.relative_to(project_dir)),
                                "message": f"Import failed for local module '{name}': {exc}",
                                "kind": "import",
                            })
            elif isinstance(node, ast.ImportFrom):
                if node.level > 0:
                    module_name = _resolve_relative_import(project_dir, path, node.module, node.level)
                    if module_name:
                        try:
                            _import_module_fresh(module_name)
                        except Exception as exc:
                            errors.append({
                                "path": str(path.relative_to(project_dir)),
                                "message": f"Import failed for local module '{module_name}': {exc}",
                                "kind": "import",
                            })
                    else:
                        errors.append({
                            "path": str(path.relative_to(project_dir)),
                            "message": f"Relative import could not be resolved: from {'.' * node.level}{node.module or ''} import ...",
                            "kind": "import",
                        })
                    continue

                module_name = (node.module or "").split(".")[0]
                if module_name and _is_local_module(project_dir, module_name):
                    try:
                        _import_module_fresh(module_name)
                    except Exception as exc:
                        errors.append({
                            "path": str(path.relative_to(project_dir)),
                            "message": f"Import failed for local module '{module_name}': {exc}",
                            "kind": "import",
                        })
    return errors


def _is_local_module(project_dir: Path, module_name: str) -> bool:
    return (
        (project_dir / f"{module_name}.py").exists()
        or (project_dir / module_name / "__init__.py").exists()
        or (project_dir / "backend" / f"{module_name}.py").exists()
        or (project_dir / "tests" / f"{module_name}.py").exists()
    )


def _resolve_relative_import(project_dir: Path, path: Path, module: str | None, level: int) -> str | None:
    rel_parent = path.relative_to(project_dir).parent
    base_parts = list(rel_parent.parts)
    if len(base_parts) < level - 1:
        return None
    anchor_parts = base_parts[:len(base_parts) - (level - 1)]
    module_parts = [part for part in (module or "").split(".") if part]
    resolved_parts = anchor_parts + module_parts
    if not resolved_parts:
        return None
    candidate = project_dir.joinpath(*resolved_parts)
    if candidate.with_suffix(".py").exists() or (candidate / "__init__.py").exists():
        return ".".join(resolved_parts)
    return None


def _import_module_fresh(module_name: str):
    importlib.invalidate_caches()
    sys.modules.pop(module_name, None)
    for loaded_name in list(sys.modules):
        if loaded_name.startswith(f"{module_name}."):
            sys.modules.pop(loaded_name, None)
    return importlib.import_module(module_name)


@contextmanager
def _project_on_syspath(project_dir: Path):
    original = list(sys.path)
    sys.path.insert(0, str(project_dir))
    sys.path.insert(0, str(project_dir / "backend"))
    sys.path.insert(0, str(project_dir / "tests"))
    try:
        yield
    finally:
        sys.path[:] = original
