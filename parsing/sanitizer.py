"""Strip ANSI escape codes and normalize CLI output."""

import re

# Matches all ANSI escape sequences (colors, cursor movement, etc.)
_ANSI_RE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]|\x1b\].*?\x07|\x1b\[.*?[@-~]')

# Common spinner/progress characters
_SPINNER_CHARS = set('⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏|/-\\')


def strip_ansi(text: str) -> str:
    """Remove all ANSI escape sequences from text."""
    return _ANSI_RE.sub('', text)


def normalize_whitespace(text: str) -> str:
    """Collapse excessive blank lines and trim trailing whitespace."""
    lines = text.splitlines()
    result = []
    blank_count = 0
    for line in lines:
        stripped = line.rstrip()
        if not stripped:
            blank_count += 1
            if blank_count <= 2:
                result.append('')
        else:
            blank_count = 0
            result.append(stripped)
    return '\n'.join(result).strip()


def strip_progress_lines(text: str) -> str:
    """Remove lines that are purely spinner/progress output."""
    lines = text.splitlines()
    result = []
    for line in lines:
        clean = strip_ansi(line).strip()
        # Skip lines that are just spinner chars or very short progress indicators
        if clean and not all(c in _SPINNER_CHARS or c == ' ' for c in clean):
            result.append(line)
    return '\n'.join(result)


def clean_output(text: str) -> str:
    """Full sanitization pipeline: strip ANSI, progress lines, normalize."""
    text = strip_ansi(text)
    text = strip_progress_lines(text)
    text = normalize_whitespace(text)
    return text
