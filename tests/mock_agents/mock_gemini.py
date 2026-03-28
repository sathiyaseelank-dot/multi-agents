#!/usr/bin/env python3
"""Mock Gemini frontend agent — returns canned JSX code.

Mimics: gemini -p "<prompt>"
Supports: MOCK_EXIT_CODE, MOCK_DELAY, MOCK_ERROR_TEXT
"""

import os
import sys
import time

exit_code = int(os.environ.get("MOCK_EXIT_CODE", "0"))
delay = float(os.environ.get("MOCK_DELAY", "0"))
error_text = os.environ.get("MOCK_ERROR_TEXT", "")

# Gemini CLI uses -p flag for non-interactive mode — consume it if present
args = sys.argv[1:]
if args and args[0] == "-p":
    args = args[1:]  # strip -p, the prompt is the next arg

if delay:
    time.sleep(delay)

if exit_code != 0:
    print(
        error_text or f"Error: mock failure (MOCK_EXIT_CODE={exit_code})",
        file=sys.stderr,
    )
    sys.exit(exit_code)

print("Here is the frontend component:")
print("")
print("```jsx")
print("// Mock UI component")
print("import React from 'react';")
print("")
print("export function MockComponent({ data }) {")
print("  return (")
print("    <div className=\"container\">")
print("      <h1>Mock Component</h1>")
print("      <pre>{JSON.stringify(data, null, 2)}</pre>")
print("    </div>")
print("  );")
print("}")
print("```")
