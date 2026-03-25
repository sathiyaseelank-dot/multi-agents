#!/usr/bin/env python3
"""Mock planner for debate-loop tests."""

import json
import os
import sys


def initial_plan() -> dict:
    return {
        "epic": "Debate test task",
        "tasks": [
            {
                "id": "task-001",
                "type": "backend",
                "agent": "opencode",
                "title": "Implement core logic",
                "description": "Build the backend module",
                "dependencies": [],
            },
            {
                "id": "task-002",
                "type": "frontend",
                "agent": "gemini",
                "title": "Build interface",
                "description": "Create the frontend UI",
                "dependencies": ["task-001"],
            },
        ],
        "phases": [
            {
                "phase": 1,
                "description": "Implement application layers",
                "parallel": False,
                "task_ids": ["task-001", "task-002"],
            }
        ],
    }


def revised_plan() -> dict:
    return {
        "epic": "Debate test task",
        "tasks": [
            {
                "id": "task-001",
                "type": "backend",
                "agent": "opencode",
                "title": "Implement core logic",
                "description": "Build the backend module",
                "dependencies": [],
            },
            {
                "id": "task-002",
                "type": "frontend",
                "agent": "gemini",
                "title": "Build interface",
                "description": "Create the frontend UI",
                "dependencies": ["task-001"],
            },
            {
                "id": "task-003",
                "type": "testing",
                "agent": "kilo",
                "title": "Write tests",
                "description": "Add tests covering backend and frontend",
                "dependencies": ["task-001", "task-002"],
            },
        ],
        "phases": [
            {
                "phase": 1,
                "description": "Build core implementation",
                "parallel": False,
                "task_ids": ["task-001", "task-002"],
            },
            {
                "phase": 2,
                "description": "Validate with tests",
                "parallel": False,
                "task_ids": ["task-003"],
            },
        ],
    }


if int(os.environ.get("MOCK_EXIT_CODE", "0")) != 0:
    print("planner failed", file=sys.stderr)
    sys.exit(1)

prompt = sys.argv[-1] if len(sys.argv) > 1 else ""
plan = revised_plan() if "Reviewer feedback:" in prompt else initial_plan()

print("```json")
print(json.dumps(plan, indent=2))
print("```")
