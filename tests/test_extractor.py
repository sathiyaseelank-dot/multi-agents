"""Unit tests for the parsing extractor module."""
import pytest

from parsing.extractor import extract_json, extract_code_blocks, extract_first_code_block


class TestExtractJson:
    """Tests for extract_json function."""

    def test_extract_json_from_markdown_block(self):
        """Test extracting JSON from ```json ... ``` blocks."""
        raw = """Here is the plan:
```json
{
  "epic": "Build a login system",
  "tasks": [
    {"id": "task-001", "title": "Set up database"}
  ]
}
```
"""
        result = extract_json(raw)
        assert result is not None
        assert result["epic"] == "Build a login system"
        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["id"] == "task-001"

    def test_extract_json_uppercase_marker(self):
        """Test extracting JSON from ```JSON ... ``` blocks (uppercase)."""
        raw = """```JSON
{"status": "success", "count": 42}
```"""
        result = extract_json(raw)
        assert result is not None
        assert result["status"] == "success"
        assert result["count"] == 42

    def test_extract_json_pure_json_input(self):
        """Test parsing when entire output is JSON."""
        raw = '{"name": "test", "value": 123}'
        result = extract_json(raw)
        assert result is not None
        assert result["name"] == "test"
        assert result["value"] == 123

    def test_extract_json_from_text_with_inline_json(self):
        """Test extracting JSON embedded in text using regex fallback."""
        raw = """The result is {"status": "ok", "data": [1, 2, 3]} as shown above."""
        result = extract_json(raw)
        assert result is not None
        assert result["status"] == "ok"
        assert result["data"] == [1, 2, 3]

    def test_extract_json_array(self):
        """Test extracting JSON array."""
        raw = """```json
[
  {"id": 1, "name": "first"},
  {"id": 2, "name": "second"}
]
```"""
        result = extract_json(raw)
        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["id"] == 1

    def test_extract_json_nested_objects(self):
        """Test extracting JSON with nested objects."""
        raw = """```json
{
  "outer": {
    "inner": {
      "deep": "value"
    }
  }
}
```"""
        result = extract_json(raw)
        assert result is not None
        assert result["outer"]["inner"]["deep"] == "value"

    def test_extract_json_with_whitespace(self):
        """Test extracting JSON with various whitespace."""
        raw = """
        ```json
        {
            "key": "value"
        }
        ```
        """
        result = extract_json(raw)
        assert result is not None
        assert result["key"] == "value"

    def test_extract_json_invalid_json_in_block(self):
        """Test that invalid JSON in blocks falls through to next strategy."""
        raw = """```json
{invalid json here}
```
{"fallback": "works"}"""
        result = extract_json(raw)
        # Should fall back to parsing the second JSON object
        assert result is not None
        assert result["fallback"] == "works"

    def test_extract_json_no_json_found(self):
        """Test returning None when no JSON is found."""
        raw = "This is just plain text with no JSON"
        result = extract_json(raw)
        assert result is None

    def test_extract_json_empty_string(self):
        """Test handling empty string."""
        result = extract_json("")
        assert result is None

    def test_extract_json_multiple_blocks_returns_first(self):
        """Test that first valid JSON block is returned."""
        raw = """```json
{"first": true}
```
Some text
```json
{"second": false}
```"""
        result = extract_json(raw)
        assert result is not None
        assert result["first"] is True


class TestExtractCodeBlocks:
    """Tests for extract_code_blocks function."""

    def test_extract_single_code_block(self):
        """Test extracting a single code block."""
        raw = """Here's the code:
```python
def hello():
    print("Hello, World!")
```
"""
        blocks = extract_code_blocks(raw)
        assert len(blocks) == 1
        assert blocks[0]["language"] == "python"
        assert 'def hello():' in blocks[0]["code"]

    def test_extract_multiple_code_blocks(self):
        """Test extracting multiple code blocks."""
        raw = """First file:
```python
x = 1
```

Second file:
```javascript
const y = 2;
```
"""
        blocks = extract_code_blocks(raw)
        assert len(blocks) == 2
        assert blocks[0]["language"] == "python"
        assert blocks[1]["language"] == "javascript"

    def test_extract_code_block_no_language(self):
        """Test code block without language tag defaults to 'text'."""
        raw = """```
plain text content
```"""
        blocks = extract_code_blocks(raw)
        assert len(blocks) == 1
        assert blocks[0]["language"] == "text"
        assert blocks[0]["code"] == "plain text content"

    def test_extract_code_block_strips_whitespace(self):
        """Test that code content is stripped of leading/trailing whitespace."""
        raw = """```python
    def indented():
        pass
    
```"""
        blocks = extract_code_blocks(raw)
        assert len(blocks) == 1
        # Leading/trailing whitespace should be stripped
        assert blocks[0]["code"].startswith("def indented():")

    def test_extract_code_block_various_languages(self):
        """Test extracting code blocks with various language tags."""
        raw = """```rust
fn main() {}
```
```go
package main
```
```sql
SELECT * FROM users;
```
```css
body { margin: 0; }
```"""
        blocks = extract_code_blocks(raw)
        assert len(blocks) == 4
        languages = [b["language"] for b in blocks]
        assert "rust" in languages
        assert "go" in languages
        assert "sql" in languages
        assert "css" in languages

    def test_extract_code_blocks_empty_string(self):
        """Test handling empty string."""
        blocks = extract_code_blocks("")
        assert blocks == []

    def test_extract_code_blocks_no_blocks(self):
        """Test when no code blocks present."""
        raw = "Just plain text without any code blocks"
        blocks = extract_code_blocks(raw)
        assert blocks == []

    def test_extract_code_block_with_special_chars(self):
        """Test code blocks containing special characters."""
        raw = """```python
import re
pattern = r'\\d+'  # Raw string with backslash
text = "Hello\nWorld"  # Newline in string
```"""
        blocks = extract_code_blocks(raw)
        assert len(blocks) == 1
        assert r'\d+' in blocks[0]["code"]


class TestExtractFirstCodeBlock:
    """Tests for extract_first_code_block function."""

    def test_extract_first_block(self):
        """Test extracting the first code block."""
        raw = """```python
first()
```
```javascript
second()
```"""
        result = extract_first_code_block(raw)
        assert result is not None
        assert "first()" in result

    def test_extract_first_block_with_language_filter(self):
        """Test filtering by language."""
        raw = """```python
python_code()
```
```javascript
javascript_code()
```"""
        result = extract_first_code_block(raw, language="javascript")
        assert result is not None
        assert "javascript_code()" in result
        assert "python_code()" not in result

    def test_extract_first_block_language_not_found(self):
        """Test when requested language doesn't exist."""
        raw = """```python
python_code()
```"""
        result = extract_first_code_block(raw, language="rust")
        assert result is None

    def test_extract_first_block_no_blocks(self):
        """Test when no code blocks exist."""
        result = extract_first_code_block("No code here")
        assert result is None

    def test_extract_first_block_empty_string(self):
        """Test handling empty string."""
        result = extract_first_code_block("")
        assert result is None
