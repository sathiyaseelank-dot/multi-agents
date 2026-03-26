"""Orchestrator API routes for the Multi-Agent Orchestrator.

Provides REST API endpoints to:
- Run orchestration tasks
- Check execution status
- Get results and logs
- List session history
"""

import asyncio
import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path

from flask import Blueprint, jsonify, request

# Add project root to path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from orchestrator.orchestrator import Orchestrator
from orchestrator.events import EventEmitter, EventType

logger = logging.getLogger(__name__)

bp = Blueprint("orchestrator", __name__, url_prefix="/api/orchestrator")

# Store for running orchestrations
running_sessions = {}
completed_sessions = {}


def _load_session_artifacts(session_id: str, memory_dir: Path) -> dict:
    """Load any persisted plan or partial results for a session."""
    artifacts: dict = {}

    plan_file = memory_dir / f"plan-{session_id}.json"
    results_file = memory_dir / f"results-{session_id}.json"

    if plan_file.exists():
        try:
            with open(plan_file) as f:
                plan_data = json.load(f)
            artifacts["plan"] = plan_data.get("plan")
            artifacts["planning_trace"] = plan_data.get("planning_trace")
            artifacts["review_iterations"] = plan_data.get("review_iterations")
            artifacts["final_review"] = plan_data.get("final_review")
        except Exception:
            logger.exception("Failed to read plan artifact for %s", session_id)

    if results_file.exists():
        try:
            with open(results_file) as f:
                results_data = json.load(f)
            artifacts["summary"] = results_data.get("summary")
            artifacts["result"] = results_data
        except Exception:
            logger.exception("Failed to read results artifact for %s", session_id)

    return artifacts


class SessionEventEmitter(EventEmitter):
    """Event emitter that stores events for a session."""

    def __init__(self, session_id: str, **kwargs):
        super().__init__(session_id=session_id, **kwargs)
        self.events_list = []
        self.status = "pending"
        self.result = None

    def emit(self, event_type: EventType | str, data: dict | None = None):
        event = super().emit(event_type, data)
        self.events_list.append(
            {
                "type": event.type,
                "timestamp": event.timestamp,
                "data": event.data,
            }
        )

        # Track status
        if event_type == EventType.RUN_STARTED:
            self.status = "running"
        elif event_type == EventType.RUN_COMPLETED:
            self.status = "completed"
            self.result = data
        elif event_type == EventType.ERROR:
            self.status = "failed"

        return event


def run_orchestrator_async(task_description: str, session_id: str, memory_dir: str):
    """Run orchestrator in a separate thread."""
    import asyncio

    emitter = SessionEventEmitter(session_id)

    def update_events_loop():
        """Update running_sessions with events periodically."""
        import time

        while session_id in running_sessions:
            if session_id in completed_sessions:
                break
            running_sessions[session_id]["events"] = list(emitter.events_list)
            running_sessions[session_id]["status"] = emitter.status
            time.sleep(1)

    async def run():
        orchestrator = Orchestrator(
            memory_dir=memory_dir,
            events=emitter,
        )

        try:
            result = await orchestrator.run(task_description)
            emitter.result = result
            completed_sessions[session_id] = {
                "status": "completed",
                "result": result,
                "events": emitter.events_list,
                "completed_at": datetime.now().isoformat(),
            }
        except Exception as e:
            completed_sessions[session_id] = {
                "status": "failed",
                "error": str(e),
                "events": emitter.events_list,
                "completed_at": datetime.now().isoformat(),
            }
        finally:
            if session_id in running_sessions:
                del running_sessions[session_id]

    event_thread = threading.Thread(target=update_events_loop, daemon=True)
    event_thread.start()

    asyncio.run(run())


@bp.route("/run", methods=["POST"])
def run_task():
    """Run an orchestration task.

    Request JSON:
    {
        "task": "Build a REST API with user authentication",
        "options": {
            "plan_only": false,
            "verbose": true
        }
    }

    Response:
    {
        "session_id": "20260325-101850",
        "status": "started",
        "message": "Task queued for execution"
    }
    """
    data = request.get_json() or {}
    task = data.get("task", "")

    if not task:
        return jsonify({"error": "task is required"}), 400

    session_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    memory_dir = str(Path(__file__).parent.parent.parent / "memory")

    # Store session info
    running_sessions[session_id] = {
        "task": task,
        "started_at": datetime.now().isoformat(),
        "status": "starting",
        "events": [],
    }

    # Run in background thread
    thread = threading.Thread(
        target=run_orchestrator_async,
        args=(task, session_id, memory_dir),
        daemon=True,
    )
    thread.start()

    return jsonify(
        {
            "session_id": session_id,
            "status": "started",
            "message": "Task queued for execution",
            "estimated_time": "2-5 minutes",
        }
    ), 202


@bp.route("/status/<session_id>", methods=["GET"])
def get_status(session_id):
    """Get execution status for a session.

    Response:
    {
        "session_id": "20260325-101850",
        "status": "running|completed|failed",
        "task": "Build a REST API...",
        "progress": {
            "current_phase": "EXECUTING",
            "completed_tasks": 2,
            "total_tasks": 5
        },
        "events": [...]
    }
    """
    # Check completed sessions
    if session_id in completed_sessions:
        session = completed_sessions[session_id]
        return jsonify(
            {
                "session_id": session_id,
                "status": session["status"],
                "result": session.get("result"),
                "error": session.get("error"),
                "events": session.get("events", []),
                "completed_at": session.get("completed_at"),
            }
        )

    # Check running sessions
    if session_id in running_sessions:
        session = running_sessions[session_id]
        memory_dir = Path(__file__).parent.parent.parent / "memory"
        artifacts = _load_session_artifacts(session_id, memory_dir)
        return jsonify(
            {
                "session_id": session_id,
                "status": "running",
                "task": session.get("task"),
                "started_at": session.get("started_at"),
                "events": session.get("events", []),
                "plan": artifacts.get("plan"),
                "planning_trace": artifacts.get("planning_trace"),
                "summary": artifacts.get("summary"),
                "result": artifacts.get("result"),
                "review_iterations": artifacts.get("review_iterations"),
                "final_review": artifacts.get("final_review"),
            }
        )

    # Check memory files
    memory_dir = Path(__file__).parent.parent.parent / "memory"
    plan_file = memory_dir / f"plan-{session_id}.json"
    results_file = memory_dir / f"results-{session_id}.json"

    if plan_file.exists():
        try:
            with open(plan_file) as f:
                data = json.load(f)
            task_summary = data.get("summary", {})
            tasks = task_summary.get("tasks", [])
            completed_tasks = len([t for t in tasks if t.get("status") == "completed"])
            return jsonify(
                {
                    "session_id": session_id,
                    "status": "completed" if results_file.exists() else "incomplete",
                    "task": data.get("plan", {}).get("epic"),
                    "started_at": data.get("timestamp"),
                    "completed_at": data.get("timestamp")
                    if results_file.exists()
                    else None,
                    "progress": {
                        "completed_tasks": completed_tasks,
                        "total_tasks": len(tasks),
                    },
                }
            )
        except Exception:
            pass

    return jsonify({"error": "Session not found"}), 404


@bp.route("/results/<session_id>", methods=["GET"])
def get_results(session_id):
    """Get full results for a completed session.

    Response:
    {
        "session_id": "...",
        "status": "completed",
        "result": {
            "project_dir": "/path/to/project",
            "build_result": {...},
            "validation_result": {...},
            "runtime_result": {...},
            "evaluation_result": {...}
        },
        "meta_decisions": [...],
        "events": [...]
    }
    """
    if session_id in completed_sessions:
        session = completed_sessions[session_id]
        return jsonify(
            {
                "session_id": session_id,
                "status": session["status"],
                "result": session.get("result", {}),
                "events": session.get("events", []),
            }
        )

    if session_id in running_sessions:
        return jsonify(
            {
                "error": "Session still running",
                "status": "running",
            }
        ), 202

    memory_dir = Path(__file__).parent.parent.parent / "memory"
    results_file = memory_dir / f"results-{session_id}.json"
    if results_file.exists():
        try:
            with open(results_file) as f:
                data = json.load(f)
            return jsonify(
                {
                    "session_id": session_id,
                    "status": "completed",
                    "result": data,
                    "events": [],
                }
            )
        except Exception as e:
            return jsonify({"error": f"Failed to read results: {str(e)}"}), 500

    return jsonify({"error": "Session not found"}), 404


@bp.route("/sessions", methods=["GET"])
def list_sessions():
    """List all orchestration sessions.

    Query params:
    - limit: Max results (default: 20)
    - status: Filter by status (running/completed/failed)

    Response:
    {
        "sessions": [
            {
                "session_id": "...",
                "task": "...",
                "status": "completed",
                "started_at": "...",
                "completed_at": "..."
            }
        ],
        "total": 50
    }
    """
    limit = int(request.args.get("limit", 20))
    status_filter = request.args.get("status")

    sessions = []

    # Add running sessions
    for sid, data in running_sessions.items():
        if status_filter and status_filter != "running":
            continue
        sessions.append(
            {
                "session_id": sid,
                "task": data.get("task"),
                "status": "running",
                "started_at": data.get("started_at"),
                "completed_at": None,
            }
        )

    # Add completed sessions (sorted by completed_at)
    completed = []
    for sid, data in completed_sessions.items():
        if status_filter and status_filter != data.get("status"):
            continue
        completed.append(
            {
                "session_id": sid,
                "task": data.get("result", {}).get("plan", {}).get("epic", "Unknown"),
                "status": data.get("status"),
                "started_at": data.get("started_at"),
                "completed_at": data.get("completed_at"),
            }
        )

    completed.sort(key=lambda x: x.get("completed_at", ""), reverse=True)
    sessions.extend(completed[:limit])

    # Also load historical sessions from memory
    memory_dir = Path(__file__).parent.parent.parent / "memory"
    if memory_dir.exists():
        plan_files = sorted(memory_dir.glob("plan-*.json"), reverse=True)[:limit]
        for plan_file in plan_files:
            try:
                data = json.loads(plan_file.read_text())
                sid = data.get("session_id")

                # Skip if already in list
                if any(s["session_id"] == sid for s in sessions):
                    continue

                # Check if results exist
                results_file = memory_dir / f"results-{sid}.json"
                status = "completed" if results_file.exists() else "incomplete"

                if status_filter and status_filter != status:
                    continue

                sessions.append(
                    {
                        "session_id": sid,
                        "task": data.get("plan", {}).get("epic", "Unknown"),
                        "status": status,
                        "started_at": data.get("timestamp"),
                        "completed_at": data.get("timestamp")
                        if results_file.exists()
                        else None,
                    }
                )
            except Exception:
                continue

    return jsonify(
        {
            "sessions": sessions[:limit],
            "total": len(sessions),
            "running": len(running_sessions),
            "completed": len(completed_sessions),
        }
    )


@bp.route("/cancel/<session_id>", methods=["POST"])
def cancel_session(session_id):
    """Cancel a running session.

    Note: This is a soft cancel - marks session for cancellation.
    The orchestrator will check and stop gracefully.
    """
    if session_id in running_sessions:
        running_sessions[session_id]["status"] = "cancelling"
        return jsonify(
            {
                "session_id": session_id,
                "status": "cancelling",
                "message": "Session marked for cancellation",
            }
        )

    return jsonify({"error": "Session not found or already completed"}), 404


@bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint.

    Response:
    {
        "status": "healthy",
        "running_sessions": 2,
        "completed_sessions": 15,
        "timestamp": "2026-03-25T10:18:50"
    }
    """
    return jsonify(
        {
            "status": "healthy",
            "running_sessions": len(running_sessions),
            "completed_sessions": len(completed_sessions),
            "timestamp": datetime.now().isoformat(),
        }
    )
