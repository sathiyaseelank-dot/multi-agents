"""Unit tests for the orchestrator output_writer module."""
import pytest
import tempfile
import shutil
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator.output_writer import write_task_output, write_all_outputs, _slugify, LANG_TO_EXT


class TestSlugify:
    """Tests for _slugify helper function."""

    def test_slugify_simple_text(self):
        """Test slugifying simple text."""
        assert _slugify("Hello World") == "hello-world"

    def test_slugify_special_chars(self):
        """Test slugifying text with special characters."""
        assert _slugify("Hello! @#$ World%") == "hello-world"

    def test_slugify_multiple_spaces(self):
        """Test slugifying text with multiple spaces."""
        assert _slugify("Hello   World") == "hello-world"

    def test_slugify_truncates_long_text(self):
        """Test that long text is truncated to 40 chars."""
        long_text = "This is a very long task title that should be truncated to forty characters"
        result = _slugify(long_text)
        assert len(result) <= 40

    def test_slugify_removes_leading_trailing_dashes(self):
        """Test that leading/trailing dashes are removed."""
        assert _slugify("---Hello World---") == "hello-world"

    def test_slugify_lowercase(self):
        """Test that output is lowercase."""
        assert _slugify("HELLO WORLD") == "hello-world"

    def test_slugify_preserves_alphanumeric(self):
        """Test that alphanumeric characters are preserved."""
        assert _slugify("Task-001-API-v2") == "task-001-api-v2"


class TestLangToExt:
    """Tests for LANG_TO_EXT mapping."""

    def test_python_extensions(self):
        """Test Python language mappings."""
        assert LANG_TO_EXT["python"] == ".py"
        assert LANG_TO_EXT["py"] == ".py"

    def test_javascript_extensions(self):
        """Test JavaScript language mappings."""
        assert LANG_TO_EXT["javascript"] == ".js"
        assert LANG_TO_EXT["js"] == ".js"

    def test_typescript_extensions(self):
        """Test TypeScript language mappings."""
        assert LANG_TO_EXT["typescript"] == ".ts"
        assert LANG_TO_EXT["ts"] == ".ts"
        assert LANG_TO_EXT["jsx"] == ".jsx"
        assert LANG_TO_EXT["tsx"] == ".tsx"

    def test_other_languages(self):
        """Test other language mappings."""
        assert LANG_TO_EXT["html"] == ".html"
        assert LANG_TO_EXT["css"] == ".css"
        assert LANG_TO_EXT["sql"] == ".sql"
        assert LANG_TO_EXT["rust"] == ".rs"
        assert LANG_TO_EXT["go"] == ".go"

    def test_unknown_language_defaults_to_txt(self):
        """Test that unknown languages default to .txt."""
        assert LANG_TO_EXT.get("unknown", ".txt") == ".txt"


class TestWriteTaskOutput:
    """Tests for write_task_output function."""

    def setup_method(self):
        """Create temporary output directory for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = Path(self.temp_dir) / "output"

    def teardown_method(self):
        """Clean up temporary directory after each test."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_write_single_code_block(self):
        """Test writing a single code block."""
        result = {
            "code_blocks": [
                {"language": "python", "code": "def hello():\n    pass"}
            ]
        }
        files = write_task_output("task-001", "Test task", result, str(self.output_dir))
        
        assert len(files) == 1
        assert files[0].endswith("task-001-test-task.py")
        assert self.output_dir.exists()
        
        content = Path(files[0]).read_text()
        assert "def hello():" in content

    def test_write_multiple_code_blocks(self):
        """Test writing multiple code blocks."""
        result = {
            "code_blocks": [
                {"language": "python", "code": "x = 1"},
                {"language": "python", "code": "y = 2"},
                {"language": "python", "code": "z = 3"}
            ]
        }
        files = write_task_output("task-002", "Multi block", result, str(self.output_dir))
        
        assert len(files) == 3
        assert files[0].endswith("task-002-multi-block-1.py")
        assert files[1].endswith("task-002-multi-block-2.py")
        assert files[2].endswith("task-002-multi-block-3.py")

    def test_write_different_languages(self):
        """Test writing code blocks with different languages."""
        result = {
            "code_blocks": [
                {"language": "python", "code": "print('hi')"},
                {"language": "javascript", "code": "console.log('hi')"},
                {"language": "sql", "code": "SELECT 1"}
            ]
        }
        files = write_task_output("task-003", "Polyglot", result, str(self.output_dir))
        
        assert len(files) == 3
        assert files[0].endswith(".py")
        assert files[1].endswith(".js")
        assert files[2].endswith(".sql")

    def test_write_no_code_blocks_writes_raw_text(self):
        """Test that raw text is written when no code blocks."""
        result = {
            "raw_text": "This is plain text output without code blocks"
        }
        files = write_task_output("task-004", "Text only", result, str(self.output_dir))
        
        assert len(files) == 1
        assert files[0].endswith(".txt")
        content = Path(files[0]).read_text()
        assert "plain text output" in content

    def test_write_empty_result(self):
        """Test handling empty result."""
        files = write_task_output("task-005", "Empty", None, str(self.output_dir))
        assert files == []
        
        files = write_task_output("task-005", "Empty", {}, str(self.output_dir))
        assert files == []

    def test_write_creates_output_directory(self):
        """Test that output directory is created if it doesn't exist."""
        nested_dir = self.output_dir / "nested" / "path"
        result = {"code_blocks": [{"language": "python", "code": "x = 1"}]}
        files = write_task_output("task-006", "Test", result, str(nested_dir))
        
        assert nested_dir.exists()
        assert len(files) == 1

    def test_write_code_block_appends_newline(self):
        """Test that code blocks have newline appended."""
        result = {
            "code_blocks": [{"language": "python", "code": "x = 1"}]
        }
        files = write_task_output("task-007", "Newline test", result, str(self.output_dir))
        
        content = Path(files[0]).read_text()
        assert content.endswith("\n")

    def test_write_empty_code_block_skipped(self):
        """Test that empty code blocks are skipped."""
        result = {
            "code_blocks": [
                {"language": "python", "code": "valid code"},
                {"language": "python", "code": "   "},  # Whitespace only
                {"language": "python", "code": ""}  # Empty
            ]
        }
        files = write_task_output("task-008", "Skip empty", result, str(self.output_dir))
        
        assert len(files) == 1  # Only the valid block

    def test_write_unknown_language_defaults_to_txt(self):
        """Test that unknown language defaults to .txt extension."""
        result = {
            "code_blocks": [{"language": "unknown_lang", "code": "some code"}]
        }
        files = write_task_output("task-009", "Unknown lang", result, str(self.output_dir))
        
        assert files[0].endswith(".txt")


class TestWriteAllOutputs:
    """Tests for write_all_outputs function."""

    def setup_method(self):
        """Create temporary output directory for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = Path(self.temp_dir) / "output"

    def teardown_method(self):
        """Clean up temporary directory after each test."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_write_all_outputs_multiple_tasks(self):
        """Test writing outputs for multiple tasks."""
        task_results = {
            "task-001": {
                "title": "First task",
                "code_blocks": [{"language": "python", "code": "x = 1"}]
            },
            "task-002": {
                "title": "Second task",
                "code_blocks": [{"language": "python", "code": "y = 2"}]
            }
        }
        all_files = write_all_outputs(task_results, str(self.output_dir))
        
        assert len(all_files) == 2
        assert "task-001" in all_files
        assert "task-002" in all_files
        assert len(all_files["task-001"]) == 1
        assert len(all_files["task-002"]) == 1

    def test_write_all_outputs_empty(self):
        """Test writing empty task results."""
        all_files = write_all_outputs({}, str(self.output_dir))
        assert all_files == {}

    def test_write_all_outputs_no_code_blocks(self):
        """Test tasks without code blocks are skipped."""
        task_results = {
            "task-001": {
                "title": "No code",
                "code_blocks": []
            }
        }
        all_files = write_all_outputs(task_results, str(self.output_dir))
        assert all_files == {}
