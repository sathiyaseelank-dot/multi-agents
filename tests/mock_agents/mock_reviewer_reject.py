#!/usr/bin/env python3
"""Mock reviewer that always rejects."""

import json

payload = {
    "issues": ["invalid architecture"],
    "suggestions": ["separate concerns more clearly"],
    "approval": False,
    "confidence": 0.7,
}

print("```json")
print(json.dumps(payload, indent=2))
print("```")
