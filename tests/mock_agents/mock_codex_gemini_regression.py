#!/usr/bin/env python3
"""Planner fixture with multiple Gemini-assigned tasks across phases."""

import json

plan = {
    "epic": "Gemini regression test",
    "tasks": [
        {
            "id": "task-001",
            "type": "backend",
            "agent": "opencode",
            "title": "Build API",
            "description": "Create the analytics API",
            "dependencies": [],
        },
        {
            "id": "task-002",
            "type": "frontend",
            "agent": "gemini",
            "title": "Build dashboard shell",
            "description": "Create the dashboard shell",
            "dependencies": [],
        },
        {
            "id": "task-003",
            "type": "frontend",
            "agent": "gemini",
            "title": "Add dashboard details",
            "description": "Add the dashboard detail view",
            "dependencies": ["task-001"],
        },
        {
            "id": "task-004",
            "type": "testing",
            "agent": "kilo",
            "title": "Write coverage",
            "description": "Write regression coverage",
            "dependencies": ["task-002", "task-003"],
        },
    ],
    "phases": [
        {
            "phase": 1,
            "description": "Initial implementation",
            "parallel": True,
            "task_ids": ["task-001", "task-002"],
        },
        {
            "phase": 2,
            "description": "Continue frontend work",
            "parallel": False,
            "task_ids": ["task-003"],
        },
        {
            "phase": 3,
            "description": "Finish coverage",
            "parallel": False,
            "task_ids": ["task-004"],
        },
    ],
}

print("OpenAI Codex v0.115.0 (mock)")
print("--------")
print("codex")
print("```json")
print(json.dumps(plan, indent=2))
print("```")
