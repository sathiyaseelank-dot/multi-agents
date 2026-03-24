#!/usr/bin/env python3
"""Mock OpenCode backend agent — returns canned Python code.

Mimics: opencode run "<prompt>"
Supports: MOCK_EXIT_CODE, MOCK_DELAY
"""

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

print("Here is the backend implementation:")
print("")
print("```python")
print("# Mock backend implementation")
print("def process(data: dict) -> dict:")
print('    """Process input data and return result."""')
print("    return {\"status\": \"ok\", \"data\": data}")
print("")
print("def validate(data: dict) -> bool:")
print('    """Validate input data."""')
print("    return bool(data)")
print("```")
