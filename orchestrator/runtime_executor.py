"""Runtime execution for generated projects."""

from __future__ import annotations

import logging
import os
import re
import shutil
import select
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

STARTUP_PATTERNS = (
    "running on",
    "uvicorn running on",
    "application startup complete",
    "serving http on",
)


def execute_project(
    project_dir: str,
    startup_timeout: int = 20,
    command_timeout: int = 180,
) -> dict:
    project_path = Path(project_dir)
    logs = []
    errors = []
    log_entries = []

    venv_dir = project_path / ".venv"
    python_bin = _create_venv(venv_dir, logs, errors)

    requirements_path = project_path / "requirements.txt"
    if python_bin and requirements_path.exists() and requirements_path.read_text().strip():
        _run_command(
            [str(python_bin), "-m", "pip", "install", "-r", str(requirements_path)],
            cwd=project_path,
            logs=logs,
            errors=errors,
            timeout=command_timeout,
            log_entries=log_entries,
        )

    backend_entrypoint = _find_backend_entrypoint(project_path)
    backend_ok = True
    if python_bin and backend_entrypoint:
        backend_ok = _run_server_command(
            [str(python_bin), backend_entrypoint.name],
            cwd=backend_entrypoint.parent,
            logs=logs,
            errors=errors,
            startup_timeout=startup_timeout,
            command_timeout=command_timeout,
            log_entries=log_entries,
        )
    elif python_bin and (project_path / "backend").exists():
        backend_ok = False
        errors.append("No backend entrypoint detected")

    frontend_ok = True
    package_json = project_path / "package.json"
    npm_bin = shutil.which("npm")
    if package_json.exists():
        if not npm_bin:
            errors.append("npm is not available for frontend execution")
            frontend_ok = False
        else:
            _run_command(
                [npm_bin, "install"],
                cwd=project_path,
                logs=logs,
                errors=errors,
                timeout=command_timeout,
                log_entries=log_entries,
            )
            frontend_ok = _run_command(
                [npm_bin, "run", "build"],
                cwd=project_path,
                logs=logs,
                errors=errors,
                timeout=command_timeout,
                log_entries=log_entries,
            )

    success = not errors and backend_ok and frontend_ok
    result = {
        "success": success,
        "logs": "\n".join(logs),
        "errors": errors,
        "log_entries": log_entries,
        "entrypoint": str(backend_entrypoint) if backend_entrypoint else None,
    }
    logger.info("Runtime execution complete for %s: success=%s", project_dir, success)
    return result


def _create_venv(venv_dir: Path, logs: list[str], errors: list[str]) -> Path | None:
    python_bin = _venv_python(venv_dir)
    try:
        subprocess.run(
            [sys.executable, "-m", "venv", str(venv_dir)],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        if python_bin.exists():
            logs.append(f"Virtual environment created with warnings: {exc.stderr.strip()}")
            return python_bin
        errors.append(f"Failed to create virtual environment: {exc.stderr.strip()}")
        return None
    logs.append(f"Created virtual environment at {venv_dir}")
    return python_bin


def _find_backend_entrypoint(project_path: Path) -> Path | None:
    backend_dir = project_path / "backend"
    priority_candidates = [
        backend_dir / "app.py",
        backend_dir / "main.py",
    ]
    for candidate in priority_candidates:
        if candidate.exists():
            return candidate

    if not backend_dir.exists():
        return None

    for candidate in sorted(backend_dir.glob("*.py")):
        if _contains_web_app(candidate):
            return candidate
    return None


def _run_command(
    command: list[str],
    cwd: Path,
    logs: list[str],
    errors: list[str],
    timeout: int,
    log_entries: list[dict] | None = None,
) -> bool:
    try:
        proc = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        errors.append(f"Command timed out: {' '.join(command)}")
        return False
    logs.append(f"$ {' '.join(command)}")
    if proc.stdout:
        logs.append(proc.stdout.strip())
        _append_log_entries(log_entries, "stdout", proc.stdout)
    if proc.stderr:
        logs.append(proc.stderr.strip())
        _append_log_entries(log_entries, "stderr", proc.stderr)
    if proc.returncode != 0:
        errors.append(f"Command failed ({proc.returncode}): {' '.join(command)}")
        return False
    return True


def _run_server_command(
    command: list[str],
    cwd: Path,
    logs: list[str],
    errors: list[str],
    startup_timeout: int,
    command_timeout: int,
    log_entries: list[dict] | None = None,
) -> bool:
    logs.append(f"$ {' '.join(command)}")
    proc = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    startup_detected = False
    deadline = time.monotonic() + startup_timeout
    hard_deadline = time.monotonic() + command_timeout
    try:
        while time.monotonic() < hard_deadline:
            if proc.poll() is not None:
                _drain_process_output(proc, logs, log_entries)
                if startup_detected or _probe_http_server(_extract_candidate_urls(logs)):
                    return proc.returncode == 0
                errors.append(f"Runtime exited with code {proc.returncode} before startup completed")
                return False

            if time.monotonic() > deadline and not startup_detected:
                if _probe_http_server(_extract_candidate_urls(logs)):
                    startup_detected = True
                    break
                errors.append("No startup signal detected before timeout")
                return False

            ready, _, _ = select.select([proc.stdout, proc.stderr], [], [], 0.2)
            for stream in ready:
                line = stream.readline()
                if not line:
                    continue
                line = line.rstrip()
                if not line:
                    continue
                logs.append(line)
                _append_log_entries(log_entries, "stdout" if stream is proc.stdout else "stderr", line)
                if any(pattern in line.lower() for pattern in STARTUP_PATTERNS):
                    startup_detected = True
                    if _probe_http_server(_extract_candidate_urls(logs)):
                        return True
        if startup_detected or _probe_http_server(_extract_candidate_urls(logs)):
            return True
        errors.append("Runtime command exceeded timeout without confirming startup")
        return False
    finally:
        _terminate_process(proc, logs, log_entries)


def _contains_web_app(path: Path) -> bool:
    content = path.read_text(errors="replace")
    patterns = (
        r"\bapp\s*=\s*Flask\(",
        r"\bapp\s*=\s*FastAPI\(",
        r"\bapplication\s*=\s*Flask\(",
        r"\bapplication\s*=\s*FastAPI\(",
    )
    return any(re.search(pattern, content) for pattern in patterns)


def _probe_http_server(urls: list[str]) -> bool:
    for url in urls:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status < 500:
                    return True
        except (urllib.error.URLError, TimeoutError, ValueError):
            continue
    return False


def _extract_candidate_urls(logs: list[str]) -> list[str]:
    urls = []
    for line in logs:
        for match in re.findall(r"http://[^\s'\"]+", line):
            urls.append(match.rstrip("/"))
    urls.extend(["http://127.0.0.1:5000", "http://localhost:5000"])
    deduped = []
    for url in urls:
        if url not in deduped:
            deduped.append(url)
    return deduped


def _terminate_process(proc: subprocess.Popen, logs: list[str], log_entries: list[dict] | None = None) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        stdout, stderr = proc.communicate(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
    if stdout:
        logs.append(stdout.strip())
        _append_log_entries(log_entries, "stdout", stdout)
    if stderr:
        logs.append(stderr.strip())
        _append_log_entries(log_entries, "stderr", stderr)


def _drain_process_output(proc: subprocess.Popen, logs: list[str], log_entries: list[dict] | None = None) -> None:
    stdout = proc.stdout.read() if proc.stdout else ""
    stderr = proc.stderr.read() if proc.stderr else ""
    if stdout:
        logs.append(stdout.strip())
        _append_log_entries(log_entries, "stdout", stdout)
    if stderr:
        logs.append(stderr.strip())
        _append_log_entries(log_entries, "stderr", stderr)


def _append_log_entries(log_entries: list[dict] | None, stream: str, text: str) -> None:
    if log_entries is None:
        return
    for line in text.splitlines():
        if not line.strip():
            continue
        log_entries.append({
            "stream": stream,
            "message": line,
            "timestamp": time.time(),
        })


def _venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return (venv_dir / "Scripts" / "python.exe").resolve()
    return (venv_dir / "bin" / "python").resolve()
