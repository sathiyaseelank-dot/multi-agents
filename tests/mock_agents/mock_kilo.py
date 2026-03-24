#!/usr/bin/env python3
"""Mock Kilo testing agent — returns canned pytest code.

Mimics: kilo run --auto "<prompt>"
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

print("Here are the tests:")
print("")
print("```python")
print("# Mock test suite")
print("import pytest")
print("")
print("def test_process_valid_data():")
print('    from implementation import process')
print('    result = process({"key": "value"})')
print('    assert result["status"] == "ok"')
print("")
print("def test_validate_empty_data():")
print('    from implementation import validate')
print('    assert validate({}) == False')
print("```")
