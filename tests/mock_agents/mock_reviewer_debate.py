#!/usr/bin/env python3
"""Mock reviewer that requests one revision, then approves."""

import json
import sys

prompt = sys.argv[-1] if len(sys.argv) > 1 else ""
has_testing_task = '"type": "testing"' in prompt and '"task-003"' in prompt

if has_testing_task:
    payload = {
        "issues": [],
        "suggestions": [],
        "approval": True,
        "confidence": 0.88,
    }
else:
    payload = {
        "issues": ["missing core testing task"],
        "suggestions": ["add a testing task that depends on backend and frontend work"],
        "approval": False,
        "confidence": 0.55,
    }

print("```json")
print(json.dumps(payload, indent=2))
print("```")
