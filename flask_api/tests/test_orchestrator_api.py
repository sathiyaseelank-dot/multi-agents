import os
import sys
import unittest
from unittest.mock import patch

from flask import Flask

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from routes import orchestrator_api


class OrchestratorAPITestCase(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.register_blueprint(orchestrator_api.bp)
        self.client = self.app.test_client()
        orchestrator_api.running_sessions.clear()
        orchestrator_api.completed_sessions.clear()

    def tearDown(self):
        orchestrator_api.running_sessions.clear()
        orchestrator_api.completed_sessions.clear()

    def test_run_orchestrator_async_uses_api_session_id(self):
        captured = {}

        class FakeOrchestrator:
            def __init__(self, **kwargs):
                captured.update(kwargs)

            async def run(self, task_description):
                return {
                    "status": "completed",
                    "session_id": captured["session_id"],
                    "plan": {"epic": task_description},
                }

        session_id = "session-123"
        orchestrator_api.running_sessions[session_id] = {
            "task": "Build analytics dashboard",
            "started_at": "2026-03-28T00:00:00",
        }

        with patch.object(orchestrator_api, "Orchestrator", FakeOrchestrator):
            orchestrator_api.run_orchestrator_async(
                "Build analytics dashboard",
                session_id,
                "/tmp/orchestrator-memory",
            )

        self.assertEqual(captured["session_id"], session_id)
        self.assertEqual(
            orchestrator_api.completed_sessions[session_id]["result"]["session_id"],
            session_id,
        )

    def test_status_includes_persisted_phase_and_agent_data(self):
        session_id = "session-456"
        emitter = orchestrator_api.SessionEventEmitter(session_id)
        orchestrator_api.running_sessions[session_id] = {
            "task": "Build analytics dashboard",
            "started_at": "2026-03-28T00:00:00",
            "status": "running",
            "emitter": emitter,
        }

        with patch.object(
            orchestrator_api,
            "_load_session_artifacts",
            return_value={
                "plan": {"epic": "Build analytics dashboard"},
                "phases": [{"phase": 1, "task_ids": ["task-001"], "parallel": False}],
                "execution_summary": "Phase 1 (sequential): [task-001] via opencode",
                "disabled_agents": [
                    {"agent": "gemini", "reason": "configured model was not found"}
                ],
            },
        ):
            response = self.client.get(f"/api/orchestrator/status/{session_id}")

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["session_id"], session_id)
        self.assertEqual(data["phases"][0]["task_ids"], ["task-001"])
        self.assertIn("Phase 1", data["execution_summary"])
        self.assertEqual(data["disabled_agents"][0]["agent"], "gemini")


if __name__ == "__main__":
    unittest.main()
