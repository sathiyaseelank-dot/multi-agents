"""Extract structured data (JSON, code blocks) from CLI agent output."""

import json
import re
from typing import Optional

from .sanitizer import clean_output

# Match ```json ... ``` blocks (with optional language tag variations)
_JSON_BLOCK_RE = re.compile(
    r'```(?:json|JSON)\s*\n(.*?)\n\s*```',
    re.DOTALL,
)

# Match any fenced code block: ```<lang>\n...\n```
_CODE_BLOCK_RE = re.compile(
    r'```(\w*)\s*\n(.*?)\n\s*```',
    re.DOTALL,
)

# Fallback: find top-level JSON objects or arrays in raw text
_RAW_JSON_RE = re.compile(
    r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}|\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\])',
    re.DOTALL,
)


def extract_json(raw_output: str) -> Optional[dict | list]:
    """Extract JSON from CLI output. Tries multiple strategies.

    Order:
    1. Find ```json ... ``` fenced blocks
    2. Try parsing the entire output as JSON
    3. Regex for top-level { } or [ ] structures
    """
    cleaned = clean_output(raw_output)

    # Strategy 1: Extract from ```json ... ``` blocks
    matches = _JSON_BLOCK_RE.findall(cleaned)
    for match in matches:
        try:
            return json.loads(match.strip())
        except json.JSONDecodeError:
            continue

    # Strategy 2: Try parsing entire output as JSON
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Strategy 3: Regex for JSON objects/arrays in the text
    for match in _RAW_JSON_RE.finditer(cleaned):
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            continue

    return None


def extract_code_blocks(raw_output: str) -> list[dict]:
    """Extract all fenced code blocks from output.

    Returns list of {"language": str, "code": str}.
    """
    cleaned = clean_output(raw_output)
    blocks = []
    for match in _CODE_BLOCK_RE.finditer(cleaned):
        language = match.group(1) or "text"
        code = match.group(2).strip()
        blocks.append({"language": language, "code": code})
    return blocks


def extract_first_code_block(raw_output: str, language: Optional[str] = None) -> Optional[str]:
    """Extract the first code block, optionally filtering by language."""
    blocks = extract_code_blocks(raw_output)
    for block in blocks:
        if language is None or block["language"] == language:
            return block["code"]
    return None
