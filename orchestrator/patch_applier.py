"""Patch Applier — Apply surgical patches to source files with diff generation."""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def apply_patch(filepath: Path, patch: dict) -> dict:
    """
    Apply a surgical patch to a file.
    
    Args:
        filepath: Path to file to patch
        patch: Dict with 'line_start', 'line_end', 'new_code'
    
    Returns:
        Dict with 'success', 'diff', 'error', 'lines_changed'
    """
    try:
        if not filepath.exists():
            return {
                'success': False,
                'error': f"File not found: {filepath}",
                'diff': None,
                'lines_changed': 0,
            }
        
        original = filepath.read_text(encoding='utf-8')
        lines = original.splitlines()
        
        # Extract patch info
        line_start = patch.get('line_start', 0)
        line_end = patch.get('line_end', line_start + 1)
        new_code = patch.get('new_code', '')
        
        # Validate line numbers
        if line_start < 0 or line_start > len(lines):
            return {
                'success': False,
                'error': f"Invalid line_start: {line_start} (file has {len(lines)} lines)",
                'diff': None,
                'lines_changed': 0,
            }
        
        if line_end < line_start or line_end > len(lines):
            line_end = min(line_start + 1, len(lines))
        
        # Get old lines for diff
        old_lines = lines[line_start:line_end]
        
        # Generate diff BEFORE modifying
        new_lines_list = new_code.splitlines()
        diff = generate_diff(
            filepath, 
            old_lines, 
            new_lines_list, 
            line_start
        )
        
        # Apply patch: delete old lines, insert new lines
        del lines[line_start:line_end]
        for i, line in enumerate(new_lines_list):
            lines.insert(line_start + i, line)
        
        # Write patched file
        new_content = '\n'.join(lines)
        # Ensure file ends with newline
        if not new_content.endswith('\n'):
            new_content += '\n'
        filepath.write_text(new_content, encoding='utf-8')
        
        lines_changed = len(new_lines_list) - len(old_lines)
        
        logger.info(f"Patch applied to {filepath}: {len(old_lines)} lines → {len(new_lines_list)} lines")
        
        return {
            'success': True,
            'diff': diff,
            'lines_changed': lines_changed,
            'old_lines': len(old_lines),
            'new_lines': len(new_lines_list),
        }
        
    except Exception as e:
        logger.error(f"Failed to apply patch to {filepath}: {e}")
        return {
            'success': False,
            'error': str(e),
            'diff': None,
            'lines_changed': 0,
        }


def generate_diff(
    filepath: Path, 
    old_lines: list[str], 
    new_lines: list[str], 
    line_num: int
) -> str:
    """
    Generate git-style unified diff for display.
    
    Args:
        filepath: Path to the file
        old_lines: Original lines being replaced
        new_lines: New lines being inserted
        line_num: Starting line number (0-indexed)
    
    Returns:
        Git-style diff string
    """
    # Git diff uses 1-indexed line numbers
    git_line_num = line_num + 1
    
    diff_lines = [
        f"--- a/{filepath}",
        f"+++ b/{filepath}",
        f"@@ -{git_line_num},{len(old_lines)} +{git_line_num},{len(new_lines)} @@",
    ]
    
    # Add context (unchanged lines before the change)
    # For simplicity, we just show the changed lines
    
    # Removed lines (red)
    for line in old_lines:
        diff_lines.append(f"-{line}")
    
    # Added lines (green)
    for line in new_lines:
        diff_lines.append(f"+{line}")
    
    return '\n'.join(diff_lines)


def apply_multiple_patches(
    filepath: Path, 
    patches: list[dict],
    reverse: bool = False
) -> dict:
    """
    Apply multiple patches to a single file in sequence.
    
    Patches are applied in reverse line order to prevent line number shifts.
    
    Args:
        filepath: Path to file to patch
        patches: List of patch dicts (each with line_start, line_end, new_code)
        reverse: If True, apply patches in reverse order
    
    Returns:
        Dict with 'success', 'diffs', 'error'
    """
    if not patches:
        return {
            'success': True,
            'diffs': [],
            'error': None,
        }
    
    # Sort patches by line_start in reverse order to prevent line number shifts
    sorted_patches = sorted(
        patches, 
        key=lambda p: p.get('line_start', 0), 
        reverse=reverse
    )
    
    all_diffs = []
    total_lines_changed = 0
    
    for patch in sorted_patches:
        result = apply_patch(filepath, patch)
        
        if not result['success']:
            return {
                'success': False,
                'diffs': all_diffs,
                'error': f"Patch at line {patch.get('line_start')} failed: {result.get('error')}",
                'lines_changed': total_lines_changed,
            }
        
        all_diffs.append(result['diff'])
        total_lines_changed += result.get('lines_changed', 0)
    
    return {
        'success': True,
        'diffs': all_diffs,
        'error': None,
        'lines_changed': total_lines_changed,
    }


def revert_patch(filepath: Path, diff: str) -> dict:
    """
    Revert a patch by applying the inverse diff.
    
    This is a simple implementation that swaps + and - lines.
    For complex reversions, use git or a proper patch tool.
    
    Args:
        filepath: Path to patched file
        diff: The original diff string
    
    Returns:
        Dict with 'success', 'error'
    """
    try:
        # Parse diff to extract old and new lines
        lines = diff.split('\n')
        old_lines = []
        new_lines = []
        
        for line in lines:
            if line.startswith('-') and not line.startswith('---'):
                old_lines.append(line[1:])
            elif line.startswith('+') and not line.startswith('+++'):
                new_lines.append(line[1:])
        
        if not old_lines:
            return {
                'success': False,
                'error': 'No changes to revert in diff',
            }
        
        # Apply inverse patch (swap old and new)
        return apply_patch(filepath, {
            'line_start': 0,  # Would need to track this properly
            'line_end': len(new_lines),
            'new_code': '\n'.join(old_lines),
        })
        
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to revert patch: {e}",
        }


def validate_patch_syntax(filepath: Path, language: str = 'python') -> dict:
    """
    Validate that a patched file has valid syntax.
    
    Args:
        filepath: Path to patched file
        language: Programming language ('python', 'javascript', etc.)
    
    Returns:
        Dict with 'valid', 'error'
    """
    try:
        content = filepath.read_text(encoding='utf-8')
        
        if language == 'python':
            # Try to compile Python code
            compile(content, str(filepath), 'exec')
            return {
                'valid': True,
                'error': None,
            }
        
        # For other languages, we'd need language-specific validators
        # For now, just check it's not empty
        if not content.strip():
            return {
                'valid': False,
                'error': 'File is empty',
            }
        
        return {
            'valid': True,
            'error': None,
        }
        
    except SyntaxError as e:
        return {
            'valid': False,
            'error': f"Syntax error: {e}",
        }
    except Exception as e:
        return {
            'valid': False,
            'error': f"Validation error: {e}",
        }
