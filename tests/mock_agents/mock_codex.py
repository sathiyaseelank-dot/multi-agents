#!/usr/bin/env python3
"""Mock Codex planner — returns a canned JSON task plan.

Mimics: codex exec "<prompt>"
Supports: MOCK_EXIT_CODE=1 to simulate failure
          MOCK_DELAY=<seconds> to simulate slow response
"""

import json
import os
import sys
import time

exit_code = int(os.environ.get("MOCK_EXIT_CODE", "0"))
delay = float(os.environ.get("MOCK_DELAY", "0"))

if delay:
    time.sleep(delay)

if exit_code != 0:
    print(f"Error: mock failure (MOCK_EXIT_CODE={exit_code})", file=sys.stderr)
    sys.exit(exit_code)

# Print minimal header (no prompt echo — avoids polluting the JSON extractor)
print("OpenAI Codex v0.115.0 (mock)")
print("--------")
print("codex")

# Return canned plan
plan = {
    "epic": "Mock task from test",
    "tasks": [
        {
            "id": "task-001",
            "type": "backend",
            "agent": "opencode",
            "title": "Implement core logic",
            "description": "Write the core business logic module",
            "dependencies": [],
        },
        {
            "id": "task-002",
            "type": "frontend",
            "agent": "gemini",
            "title": "Build UI component",
            "description": "Create the user interface component",
            "dependencies": [],
        },
        {
            "id": "task-003",
            "type": "testing",
            "agent": "kilo",
            "title": "Write tests",
            "description": "Write unit and integration tests",
            "dependencies": ["task-001", "task-002"],
        },
    ],
    "phases": [
        {
            "phase": 1,
            "description": "Implement core logic and UI in parallel",
            "parallel": True,
            "task_ids": ["task-001", "task-002"],
        },
        {
            "phase": 2,
            "description": "Test the implementation",
            "parallel": False,
            "task_ids": ["task-003"],
        },
    ],
}

print("```json")
print(json.dumps(plan, indent=2))
print("```")
