"""Line Finder — Intelligently find which lines need fixing in source code."""

import logging
import re
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def find_lines_to_fix(file_content: str, error_message: str) -> Tuple[int, int]:
    """
    Find the line range that needs fixing based on error message analysis.
    
    Uses multiple strategies:
    1. Parse line number from error message
    2. Find function/class mentioned in error
    3. Search for error pattern in code
    4. Fallback to full file
    
    Args:
        file_content: Full content of the file
        error_message: Error message from validation/runtime
    
    Returns:
        Tuple of (line_start, line_end) - 0-indexed, exclusive end
    """
    lines = file_content.splitlines()
    
    # Strategy 1: Parse explicit line number from error
    line_num = extract_line_number(error_message)
    if line_num is not None:
        # Return context: 2 lines before, 8 lines after (enough for most fixes)
        start = max(0, line_num - 3)  # Convert to 0-indexed, add context
        end = min(len(lines), line_num + 7)
        logger.debug(f"Found line number {line_num} in error, using lines {start}-{end}")
        return start, end
    
    # Strategy 2: Find function mentioned in error
    func_name = extract_function_name(error_message)
    if func_name:
        bounds = find_function_bounds(file_content, func_name)
        if bounds:
            logger.debug(f"Found function '{func_name}' at lines {bounds[0]}-{bounds[1]}")
            return bounds
    
    # Strategy 3: Search for common error patterns
    pattern_bounds = find_by_error_pattern(file_content, error_message)
    if pattern_bounds:
        logger.debug(f"Found pattern match at lines {pattern_bounds[0]}-{pattern_bounds[1]}")
        return pattern_bounds
    
    # Strategy 4: Fallback - return entire file (will trigger full rewrite)
    logger.warning(f"Could not locate specific lines for error, using full file")
    return 0, len(lines)


def extract_line_number(error_message: str) -> Optional[int]:
    """
    Extract line number from error message.
    
    Handles formats like:
    - "line 42"
    - "Line 42"
    - "at line 42"
    - "on line 42"
    - "SyntaxError: ... (line 42)"
    """
    patterns = [
        r'line\s+(\d+)',
        r'Line\s+(\d+)',
        r'\(line\s+(\d+)\)',
        r':(\d+):\d+',  # Python format: file.py:42:10
        r'at\s+line\s+(\d+)',
        r'on\s+line\s+(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, error_message, re.IGNORECASE)
        if match:
            return int(match.group(1))
    
    return None


def extract_function_name(error_message: str) -> Optional[str]:
    """
    Extract function name from error message.
    
    Handles formats like:
    - "NameError: name 'calculate' is not defined"
    - "TypeError in divide()"
    - "function multiply"
    - "'add'"
    """
    patterns = [
        r"name\s+'(\w+)'\s+is\s+not\s+defined",
        r"in\s+(\w+)\(\)",
        r"function\s+(\w+)",
        r"'(\w+)'\s+failed",
        r"undefined\s+(?:function|method)\s+'?(\w+)'?",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, error_message, re.IGNORECASE)
        if match:
            return match.group(1)
    
    # Look for quoted identifiers (might be function names)
    quoted = re.findall(r"'(\w+)'", error_message)
    if quoted:
        # Return the most likely candidate (not common words)
        common_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been'}
        for name in quoted:
            if name.lower() not in common_words and len(name) > 2:
                return name
    
    return None


def find_function_bounds(content: str, func_name: str) -> Optional[Tuple[int, int]]:
    """
    Find start and end line numbers of a function.
    
    Args:
        content: Full file content
        func_name: Name of the function to find
    
    Returns:
        Tuple of (start_line, end_line) or None if not found
    """
    lines = content.splitlines()
    
    # Patterns for different languages
    patterns = [
        rf'def\s+{re.escape(func_name)}\s*\(',  # Python
        rf'function\s+{re.escape(func_name)}\s*\(',  # JavaScript
        rf'(?:public|private|protected)?\s*(?:static)?\s*\w+\s+{re.escape(func_name)}\s*\(',  # Java/C#
        rf'const\s+{re.escape(func_name)}\s*=\s*(?:async)?\s*\(',  # Arrow function
        rf'def\s+{re.escape(func_name)}',  # Python (no parens)
    ]
    
    # Find function start
    start_line = None
    for i, line in enumerate(lines):
        for pattern in patterns:
            if re.search(pattern, line):
                start_line = i
                break
        if start_line is not None:
            break
    
    if start_line is None:
        return None
    
    # Find function end
    # Look for next function/class definition or end of file
    # Use indentation to detect end of function (Python-style)
    base_indent = len(lines[start_line]) - len(lines[start_line].lstrip())
    
    for i in range(start_line + 1, len(lines)):
        line = lines[i]
        
        # Skip empty lines and comments
        if not line.strip() or line.strip().startswith('#'):
            continue
        
        # Check if we hit another definition at same or lower indentation
        current_indent = len(line) - len(line.lstrip())
        
        # Check for new definition
        is_definition = any([
            re.match(r'def\s+\w+', line),
            re.match(r'function\s+\w+', line),
            re.match(r'class\s+\w+', line),
            re.match(r'(?:public|private|protected)\s+\w+\s+\w+', line),
        ])
        
        if is_definition or (current_indent <= base_indent and line.strip()):
            return start_line, i
    
    # Function goes to end of file
    return start_line, len(lines)


def find_by_error_pattern(content: str, error_message: str) -> Optional[Tuple[int, int]]:
    """
    Find code section based on error pattern keywords.
    
    Args:
        content: Full file content
        error_message: Error message to analyze
    
    Returns:
        Tuple of (start_line, end_line) or None
    """
    lines = content.splitlines()
    error_lower = error_message.lower()
    
    # Map error keywords to code patterns
    patterns = {
        'divide': (r'def\s+divide', r'/'),
        'multiply': (r'def\s+multiply', r'\*'),
        'subtract': (r'def\s+subtract', r'-'),
        'add': (r'def\s+add', r'\+'),
        'zero': (r'if\s+\w+\s*==\s*0', r'ZeroDivisionError'),
        'null': (r'if\s+\w+\s+is\s+None', r'NoneType'),
        'type': (r'def\s+\w+', r'TypeError'),
        'syntax': (r'def\s+\w+', r'SyntaxError'),
        'import': (r'^import\s+', r'ModuleNotFoundError'),
        'name': (r'def\s+\w+', r'NameError'),
    }
    
    for keyword, (code_pattern, _) in patterns.items():
        if keyword in error_lower:
            # Find lines matching the code pattern
            for i, line in enumerate(lines):
                if re.search(code_pattern, line, re.IGNORECASE):
                    # Return function/context around this line
                    start = max(0, i - 1)
                    end = min(len(lines), i + 10)
                    return start, end
    
    return None


def get_context_around_line(
    content: str, 
    line_num: int, 
    context_lines: int = 5
) -> Tuple[str, int, int]:
    """
    Get code context around a specific line.
    
    Args:
        content: Full file content
        line_num: Target line number (0-indexed)
        context_lines: Number of lines before and after
    
    Returns:
        Tuple of (context_string, start_line, end_line)
    """
    lines = content.splitlines()
    
    start = max(0, line_num - context_lines)
    end = min(len(lines), line_num + context_lines + 1)
    
    context = '\n'.join(lines[start:end])
    
    return context, start, end


def count_lines(content: str) -> int:
    """Count non-empty lines in content."""
    return len([line for line in content.splitlines() if line.strip()])
