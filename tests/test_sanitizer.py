"""Unit tests for the parsing sanitizer module."""
import pytest

from parsing.sanitizer import strip_ansi, normalize_whitespace, strip_progress_lines, clean_output


class TestStripAnsi:
    """Tests for strip_ansi function."""

    def test_strip_color_codes(self):
        """Test removing ANSI color codes."""
        raw = "\x1b[31mRed text\x1b[0m and \x1b[32mGreen text\x1b[0m"
        result = strip_ansi(raw)
        assert result == "Red text and Green text"

    def test_strip_cursor_movement(self):
        """Test removing cursor movement codes."""
        raw = "Text\x1b[2J\x1b[HMore text"
        result = strip_ansi(raw)
        assert result == "TextMore text"

    def test_strip_bold_italic(self):
        """Test removing bold/italic formatting."""
        raw = "\x1b[1mBold\x1b[0m and \x1b[3mItalic\x1b[0m"
        result = strip_ansi(raw)
        assert result == "Bold and Italic"

    def test_strip_hyperlink(self):
        """Test removing hyperlink codes."""
        raw = "Click \x1b]8;;https://example.com\x07here\x1b]8;;\x07"
        result = strip_ansi(raw)
        assert result == "Click here"

    def test_no_ansi_codes(self):
        """Test text without ANSI codes passes through."""
        raw = "Plain text without any codes"
        result = strip_ansi(raw)
        assert result == raw

    def test_empty_string(self):
        """Test handling empty string."""
        result = strip_ansi("")
        assert result == ""

    def test_only_ansi_codes(self):
        """Test string with only ANSI codes."""
        raw = "\x1b[31m\x1b[1m\x1b[0m"
        result = strip_ansi(raw)
        assert result == ""

    def test_complex_ansi_sequence(self):
        """Test complex ANSI sequences."""
        raw = "\x1b[38;5;196mExtended color\x1b[0m"
        result = strip_ansi(raw)
        assert result == "Extended color"


class TestNormalizeWhitespace:
    """Tests for normalize_whitespace function."""

    def test_collapse_blank_lines(self):
        """Test collapsing excessive blank lines."""
        raw = "Line 1\n\n\n\n\nLine 2"
        result = normalize_whitespace(raw)
        assert result == "Line 1\n\n\nLine 2"

    def test_trim_trailing_whitespace(self):
        """Test trimming trailing whitespace from lines."""
        raw = "Line 1   \nLine 2\t\t\nLine 3  "
        result = normalize_whitespace(raw)
        assert result == "Line 1\nLine 2\nLine 3"

    def test_trim_leading_trailing_blank_lines(self):
        """Test trimming leading and trailing blank lines."""
        raw = "\n\n\nContent here\n\n\n"
        result = normalize_whitespace(raw)
        assert result == "Content here"

    def test_preserve_single_blank_lines(self):
        """Test that single blank lines are preserved."""
        raw = "Para 1\n\nPara 2"
        result = normalize_whitespace(raw)
        assert result == "Para 1\n\nPara 2"

    def test_empty_string(self):
        """Test handling empty string."""
        result = normalize_whitespace("")
        assert result == ""

    def test_whitespace_only_string(self):
        """Test string with only whitespace."""
        result = normalize_whitespace("   \n\n\n   ")
        assert result == ""

    def test_preserve_internal_spacing(self):
        """Test that internal spacing within lines is preserved."""
        raw = "  Indented line  \n    More indent  "
        result = normalize_whitespace(raw)
        # Trailing stripped, leading preserved
        assert result == "Indented line\n    More indent"


class TestStripProgressLines:
    """Tests for strip_progress_lines function."""

    def test_strip_spinner_lines(self):
        """Test removing spinner character lines."""
        raw = """Starting...
⠋
Processing...
⠙
Done!"""
        result = strip_progress_lines(raw)
        assert "Starting..." in result
        assert "Processing..." in result
        assert "Done!" in result
        assert "⠋" not in result
        assert "⠙" not in result

    def test_strip_progress_bar_lines(self):
        """Test removing progress indicator lines."""
        raw = """Loading...
|
Loading...
/
Complete"""
        result = strip_progress_lines(raw)
        assert "Loading..." in result
        assert "Complete" in result

    def test_preserve_content_lines(self):
        """Test that content lines are preserved."""
        raw = """Step 1: Initialize
⠋
Step 2: Process data
⠙
Step 3: Complete"""
        result = strip_progress_lines(raw)
        lines = result.split('\n')
        content_lines = [l for l in lines if l.strip()]
        assert "Step 1: Initialize" in content_lines
        assert "Step 2: Process data" in content_lines
        assert "Step 3: Complete" in content_lines

    def test_empty_string(self):
        """Test handling empty string."""
        result = strip_progress_lines("")
        assert result == ""

    def test_no_progress_lines(self):
        """Test text without progress lines passes through."""
        raw = "Regular content\nNo spinner here"
        result = strip_progress_lines(raw)
        assert result == raw


class TestCleanOutput:
    """Tests for clean_output function (full pipeline)."""

    def test_full_pipeline(self):
        """Test complete sanitization pipeline."""
        raw = "\x1b[31mError:\x1b[0m Something went wrong\x1b[0m\n⠋\n\n\n\nRetrying..."
        result = clean_output(raw)
        assert "Error:" in result
        assert "Something went wrong" in result
        assert "Retrying..." in result
        assert "\x1b" not in result
        assert "⠋" not in result

    def test_clean_code_block_output(self):
        """Test cleaning typical code generation output."""
        raw = """\x1b[32mGenerating code...\x1b[0m
⠋
\x1b[32mDone!\x1b[0m

```python
def hello():
    print("Hello")
```

\x1b[90mCompleted in 2.3s\x1b[0m"""
        result = clean_output(raw)
        assert "Generating code..." in result
        assert "Done!" in result
        assert "```python" in result
        assert "def hello():" in result
        assert "Completed in 2.3s" in result
        assert "\x1b" not in result

    def test_empty_string(self):
        """Test handling empty string."""
        result = clean_output("")
        assert result == ""

    def test_clean_output_already_clean(self):
        """Test that clean input passes through with minimal changes."""
        raw = "Clean text without any issues"
        result = clean_output(raw)
        assert result == raw

    def test_clean_output_preserves_code_blocks(self):
        """Test that code blocks are preserved during cleaning."""
        raw = """Here is the code:
```python
x = 1
y = 2
```
Done."""
        result = clean_output(raw)
        assert "```python" in result
        assert "x = 1" in result
        assert "y = 2" in result
