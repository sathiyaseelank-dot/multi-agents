#!/usr/bin/env python3
"""Mock reviewer that always approves."""

import json

payload = {
    "issues": [],
    "suggestions": [],
    "approval": True,
    "confidence": 0.92,
}

print("```json")
print(json.dumps(payload, indent=2))
print("```")
