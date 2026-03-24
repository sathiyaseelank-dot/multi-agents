"""Minimal FastAPI backend for running orchestrations and retrieving event history."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from fastapi import FastAPI, HTTPException, Request

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from orchestrator.logger import setup_logging
from orchestrator.orchestrator import Orchestrator

app = FastAPI(title="Multi-Agent Orchestrator UI Backend")

DEFAULT_LOG_DIR = str(ROOT_DIR / "logs")
DEFAULT_MEMORY_DIR = str(ROOT_DIR / "memory")
DEFAULT_OUTPUT_DIR = str(ROOT_DIR / "output")

sessions: dict[str, dict[str, Any]] = {}


def _noop_writer(_: str) -> None:
    """Suppress console writes from the emitter in API mode."""


async def _extract_task(request: Request) -> str:
    """Accept task input from JSON or x-www-form-urlencoded bodies."""
    content_type = request.headers.get("content-type", "")
    body = await request.body()

    try:
        if "application/json" in content_type:
            payload = json.loads(body.decode() or "{}")
            task = payload.get("task", "").strip()
        else:
            form_data = parse_qs(body.decode())
            task = (form_data.get("task", [""])[0]).strip()
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid request body") from exc

    if not task:
        raise HTTPException(status_code=400, detail="Field 'task' is required")

    return task


@app.on_event("startup")
async def startup() -> None:
    setup_logging(log_dir=DEFAULT_LOG_DIR)


@app.post("/run")
async def run_task(request: Request) -> dict[str, Any]:
    """Start a new orchestration task in the background and return immediately."""
    task = await _extract_task(request)
    orch = Orchestrator(
        log_dir=DEFAULT_LOG_DIR,
        memory_dir=DEFAULT_MEMORY_DIR,
        output_dir=DEFAULT_OUTPUT_DIR,
        summary_only=True,
    )
    orch.events._writer = _noop_writer
    session_id = orch.session_id
    sessions[session_id] = {
        "events": orch.events,
        "status": "running",
        "result": None,
    }

    async def run_background() -> None:
        result = await orch.run(task)
        sessions[session_id]["result"] = result
        sessions[session_id]["status"] = result["status"]

    asyncio.create_task(run_background())

    return {
        "session_id": session_id,
        "status": "started",
    }


@app.get("/events/{session_id}")
async def get_events(session_id: str) -> list[dict[str, Any]]:
    """Return the structured event history for a previous session."""
    session = sessions.get(session_id)
    if not session:
        return []
    return session["events"].get_history()


@app.get("/sessions/{session_id}")
async def get_session(session_id: str) -> dict[str, Any]:
    """Return the current status and final result for a session."""
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "status": session["status"],
        "result": session["result"],
    }
