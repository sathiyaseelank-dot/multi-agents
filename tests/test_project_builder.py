"""Unit tests for the project_builder module."""

import pytest
import tempfile
import shutil
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator.project_builder import (
    create_structure,
    write_files,
    create_entrypoint,
    generate_requirements,
    build_project,
    _slugify,
    _infer_filename,
    _get_extension,
    TYPE_TO_DIR,
    LANG_TO_EXT,
)


class TestConstants:
    """Tests for module constants."""

    def test_type_to_dir_mapping(self):
        """Test task type to directory mapping."""
        assert TYPE_TO_DIR["backend"] == "backend"
        assert TYPE_TO_DIR["frontend"] == "frontend"
        assert TYPE_TO_DIR["testing"] == "tests"

    def test_lang_to_ext_mapping(self):
        """Test language to extension mapping."""
        assert LANG_TO_EXT["python"] == ".py"
        assert LANG_TO_EXT["javascript"] == ".js"
        assert LANG_TO_EXT["typescript"] == ".ts"


class TestSlugify:
    """Tests for _slugify helper function."""

    def test_slugify_simple_text(self):
        """Test slugifying simple text."""
        assert _slugify("Hello World") == "hello-world"

    def test_slugify_special_chars(self):
        """Test slugifying text with special characters."""
        assert _slugify("Hello! @#$ World%") == "hello-world"

    def test_slugify_truncates_long_text(self):
        """Test that long text is truncated to 40 chars."""
        long_text = "This is a very long task title that should be truncated to forty characters"
        result = _slugify(long_text)
        assert len(result) <= 40

    def test_slugify_preserves_alphanumeric(self):
        """Test that alphanumeric characters are preserved."""
        assert _slugify("Task-001-API-v2") == "task-001-api-v2"


class TestInferFilename:
    """Tests for _infer_filename function."""

    def test_infer_auth_file_from_login_function(self):
        """Test inferring auth.py from login function."""
        code = "def login(username, password):\n    pass"
        assert _infer_filename(code, "backend", "Implement auth") == "auth.py"

    def test_infer_models_file_from_class(self):
        """Test inferring models.py from class definition."""
        code = "class User(db.Model):\n    pass"
        assert _infer_filename(code, "backend", "Create models") == "models.py"

    def test_infer_routes_file_from_blueprint(self):
        """Test inferring routes.py from Blueprint."""
        code = "from flask import Blueprint\napi = Blueprint('api', __name__)"
        # Blueprint pattern matches, returns routes.py
        filename = _infer_filename(code, "backend", "API routes")
        assert filename == "routes.py"

    def test_infer_app_file_from_flask(self):
        """Test inferring app.py from Flask import."""
        code = "from flask import Flask\napp = Flask(__name__)"
        assert _infer_filename(code, "backend", "Main app") == "app.py"

    def test_infer_test_file_from_test_function(self):
        """Test inferring test filename from test function."""
        code = "def test_login():\n    assert True"
        filename = _infer_filename(code, "testing", "Test auth")
        assert "test" in filename

    def test_fallback_to_task_title(self):
        """Test fallback to task title when no pattern matches."""
        code = "x = 1\ny = 2"
        filename = _infer_filename(code, "backend", "Custom Task Title")
        assert "custom-task-title.py" == filename

    def test_infer_frontend_react_file(self):
        """Test inferring React component filename."""
        code = "import React from 'react';\nexport default function App() {}"
        filename = _infer_filename(code, "frontend", "Main component")
        assert filename in ("App.jsx", "index.js")


class TestGetExtension:
    """Tests for _get_extension function."""

    def test_get_python_extension(self):
        """Test getting Python extension."""
        assert _get_extension("python", "backend") == ".py"

    def test_get_javascript_extension(self):
        """Test getting JavaScript extension."""
        assert _get_extension("javascript", "frontend") == ".js"

    def test_get_default_backend_extension(self):
        """Test default extension for unknown backend language."""
        assert _get_extension("unknown", "backend") == ".py"

    def test_get_default_frontend_extension(self):
        """Test default extension for unknown frontend language."""
        assert _get_extension("unknown", "frontend") == ".js"

    def test_get_default_testing_extension(self):
        """Test default extension for unknown testing language."""
        assert _get_extension("unknown", "testing") == ".py"


class TestCreateStructure:
    """Tests for create_structure function."""

    def setup_method(self):
        """Create temporary directory for each test."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up temporary directory after each test."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_structure_creates_all_dirs(self):
        """Test that all required directories are created."""
        project_dir = Path(self.temp_dir) / "test_project"
        structure = create_structure(str(project_dir))

        assert "backend" in structure
        assert "frontend" in structure
        assert "tests" in structure
        assert structure["backend"].exists()
        assert structure["frontend"].exists()
        assert structure["tests"].exists()

    def test_create_structure_creates_parent_dirs(self):
        """Test that parent directories are created if needed."""
        project_dir = Path(self.temp_dir) / "nested" / "path" / "project"
        structure = create_structure(str(project_dir))

        assert project_dir.exists()
        assert structure["backend"].exists()


class TestWriteFiles:
    """Tests for write_files function."""

    def setup_method(self):
        """Create temporary directory and structure for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = Path(self.temp_dir) / "test_project"
        self.structure = create_structure(str(self.project_dir))

    def teardown_method(self):
        """Clean up temporary directory after each test."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_write_backend_files(self):
        """Test writing backend files to backend directory."""
        task_results = {
            "task-001": {
                "type": "backend",
                "title": "Implement auth",
                "code_blocks": [
                    {"language": "python", "code": "def login():\n    pass"}
                ]
            }
        }
        files = write_files(task_results, self.structure)

        assert len(files) == 1
        assert "/backend/" in files[0]
        assert files[0].endswith(".py")

    def test_write_frontend_files(self):
        """Test writing frontend files to frontend directory."""
        task_results = {
            "task-001": {
                "type": "frontend",
                "title": "Create component",
                "code_blocks": [
                    {"language": "javascript", "code": "console.log('hello')"}
                ]
            }
        }
        files = write_files(task_results, self.structure)

        assert len(files) == 1
        assert "/frontend/" in files[0]

    def test_write_test_files(self):
        """Test writing test files to tests directory."""
        task_results = {
            "task-001": {
                "type": "testing",
                "title": "Test auth",
                "code_blocks": [
                    {"language": "python", "code": "def test_login():\n    assert True"}
                ]
            }
        }
        files = write_files(task_results, self.structure)

        assert len(files) == 1
        assert "/tests/" in files[0]
        assert Path(files[0]).name.startswith("test_")

    def test_write_multiple_code_blocks(self):
        """Test writing multiple code blocks with numbered suffixes."""
        task_results = {
            "task-001": {
                "type": "backend",
                "title": "Multiple files",
                "code_blocks": [
                    {"language": "python", "code": "x = 1"},
                    {"language": "python", "code": "y = 2"},
                    {"language": "python", "code": "z = 3"}
                ]
            }
        }
        files = write_files(task_results, self.structure)

        assert len(files) == 3
        # Check that files have numbered suffixes
        filenames = [Path(f).name for f in files]
        assert any("-1" in f for f in filenames)

    def test_write_no_code_blocks_skips(self):
        """Test that tasks without code blocks are skipped."""
        task_results = {
            "task-001": {
                "type": "backend",
                "title": "No code",
                "code_blocks": []
            }
        }
        files = write_files(task_results, self.structure)
        assert files == []

    def test_write_empty_code_block_skipped(self):
        """Test that empty code blocks are skipped."""
        task_results = {
            "task-001": {
                "type": "backend",
                "title": "Empty blocks",
                "code_blocks": [
                    {"language": "python", "code": "valid code"},
                    {"language": "python", "code": "   "},
                    {"language": "python", "code": ""}
                ]
            }
        }
        files = write_files(task_results, self.structure)
        assert len(files) == 1

    def test_write_creates_file_with_newline(self):
        """Test that files have newline appended."""
        task_results = {
            "task-001": {
                "type": "backend",
                "title": "Newline test",
                "code_blocks": [
                    {"language": "python", "code": "x = 1"}
                ]
            }
        }
        files = write_files(task_results, self.structure)
        content = Path(files[0]).read_text()
        assert content.endswith("\n")


class TestCreateEntrypoint:
    """Tests for create_entrypoint function."""

    def setup_method(self):
        """Create temporary directory and structure for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = Path(self.temp_dir) / "test_project"
        self.structure = create_structure(str(self.project_dir))

    def teardown_method(self):
        """Clean up temporary directory after each test."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_entrypoint_with_backend_files(self):
        """Test creating Flask entrypoint when backend files exist."""
        # First create a backend file
        backend_file = self.structure["backend"] / "auth.py"
        backend_file.write_text("def login(): pass\n")

        entrypoint = create_entrypoint(self.structure, [str(backend_file)])

        assert entrypoint is not None
        assert entrypoint.endswith("app.py")
        assert Path(entrypoint).exists()

    def test_create_entrypoint_content(self):
        """Test that entrypoint has correct Flask structure."""
        backend_file = self.structure["backend"] / "auth.py"
        backend_file.write_text("def login(): pass\n")

        entrypoint = create_entrypoint(self.structure, [str(backend_file)])
        content = Path(entrypoint).read_text()

        assert "from flask import Flask" in content
        assert "app = Flask(__name__)" in content
        assert '@app.route("/")' in content
        assert 'if __name__ == "__main__":' in content

    def test_create_entrypoint_no_backend_files(self):
        """Test that no entrypoint is created without backend files."""
        frontend_file = self.structure["frontend"] / "app.js"
        frontend_file.write_text("console.log('hello')\n")

        entrypoint = create_entrypoint(self.structure, [str(frontend_file)])
        assert entrypoint is None

    def test_create_entrypoint_imports_modules(self):
        """Test that entrypoint imports generated modules."""
        auth_file = self.structure["backend"] / "auth.py"
        auth_file.write_text("def login(): pass\n")
        models_file = self.structure["backend"] / "models.py"
        models_file.write_text("class User: pass\n")

        entrypoint = create_entrypoint(
            self.structure,
            [str(auth_file), str(models_file)]
        )
        content = Path(entrypoint).read_text()

        assert "import auth" in content
        assert "import models" in content


class TestGenerateRequirements:
    """Tests for generate_requirements function."""

    def setup_method(self):
        """Create temporary directory and structure for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = Path(self.temp_dir) / "test_project"
        self.structure = create_structure(str(self.project_dir))

    def teardown_method(self):
        """Clean up temporary directory after each test."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generate_requirements_with_backend(self):
        """Test generating requirements.txt with backend."""
        req_path = generate_requirements(self.structure, has_backend=True, has_tests=False)

        assert req_path is not None
        assert req_path.endswith("requirements.txt")
        content = Path(req_path).read_text()
        assert "flask" in content

    def test_generate_requirements_with_tests(self):
        """Test generating requirements.txt with tests."""
        req_path = generate_requirements(self.structure, has_backend=True, has_tests=True)

        assert req_path is not None
        content = Path(req_path).read_text()
        assert "pytest" in content

    def test_generate_requirements_no_backend(self):
        """Test that no requirements.txt without backend."""
        req_path = generate_requirements(self.structure, has_backend=False, has_tests=False)
        assert req_path is None

    def test_generate_requirements_content(self):
        """Test requirements.txt has expected packages."""
        req_path = generate_requirements(self.structure, has_backend=True, has_tests=True)
        content = Path(req_path).read_text()

        assert "flask>=2.3.0" in content
        assert "pytest>=7.4.0" in content
        assert "python-dotenv>=1.0.0" in content


class TestBuildProject:
    """Tests for build_project main function."""

    def setup_method(self):
        """Create temporary directory for each test."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up temporary directory after each test."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_build_project_full_structure(self):
        """Test building a complete project structure."""
        task_results = {
            "task-001": {
                "type": "backend",
                "title": "Implement auth",
                "code_blocks": [
                    {"language": "python", "code": "def login():\n    pass"}
                ]
            },
            "task-002": {
                "type": "frontend",
                "title": "Create UI",
                "code_blocks": [
                    {"language": "javascript", "code": "console.log('UI')"}
                ]
            },
            "task-003": {
                "type": "testing",
                "title": "Test auth",
                "code_blocks": [
                    {"language": "python", "code": "def test_login():\n    assert True"}
                ]
            }
        }

        project_dir = Path(self.temp_dir) / "built_project"
        result = build_project(task_results, str(project_dir))

        # Check result structure
        assert result["project_dir"] == str(project_dir)
        assert "files_created" in result
        assert "entrypoint" in result
        assert "requirements" in result
        assert "structure" in result

        # Check directories exist
        assert (project_dir / "backend").exists()
        assert (project_dir / "frontend").exists()
        assert (project_dir / "tests").exists()

        # Check files created
        assert len(result["files_created"]) >= 3
        assert result["entrypoint"] is not None
        assert result["requirements"] is None

    def test_build_project_empty_results(self):
        """Test building project with empty task results."""
        project_dir = Path(self.temp_dir) / "empty_project"
        result = build_project({}, str(project_dir))

        assert result["project_dir"] == str(project_dir)
        assert result["files_created"] == []
        assert result["entrypoint"] is None
        assert result["requirements"] is None

    def test_build_project_backend_only(self):
        """Test building project with only backend tasks."""
        task_results = {
            "task-001": {
                "type": "backend",
                "title": "Backend only",
                "code_blocks": [
                    {"language": "python", "code": "x = 1"}
                ]
            }
        }

        project_dir = Path(self.temp_dir) / "backend_only"
        result = build_project(task_results, str(project_dir))

        assert result["entrypoint"] is not None
        assert result["requirements"] is None
        # Tests directory still created but no test files
        assert (project_dir / "tests").exists()

    def test_build_project_files_in_correct_dirs(self):
        """Test that files are written to correct directories."""
        task_results = {
            "task-001": {
                "type": "backend",
                "title": "Backend task",
                "code_blocks": [{"language": "python", "code": "x = 1"}]
            },
            "task-002": {
                "type": "frontend",
                "title": "Frontend task",
                "code_blocks": [{"language": "javascript", "code": "y = 2"}]
            },
            "task-003": {
                "type": "testing",
                "title": "Test task",
                "code_blocks": [{"language": "python", "code": "def test_x(): pass"}]
            }
        }

        project_dir = Path(self.temp_dir) / "organized_project"
        result = build_project(task_results, str(project_dir))

        # Check files are in correct directories based on task type
        backend_files = [f for f in result["files_created"] if "/backend/" in f]
        frontend_files = [f for f in result["files_created"] if "/frontend/" in f]
        tests_files = [f for f in result["files_created"] if "/tests/" in f]

        assert len(backend_files) >= 1
        assert len(frontend_files) >= 1
        assert len(tests_files) >= 1

        # Verify test files have test_ prefix
        for f in tests_files:
            assert "test" in Path(f).name
