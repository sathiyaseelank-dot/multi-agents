"""Unit tests for the validation engine."""

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator.validation_engine import validate_project


class TestValidationEngine:
    def setup_method(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        (self.temp_dir / "backend").mkdir()

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_detects_python_syntax_error(self):
        (self.temp_dir / "backend" / "app.py").write_text("def broken(:\n    pass\n")

        result = validate_project(str(self.temp_dir))

        assert result["success"] is False
        assert any(error["kind"] == "syntax" for error in result["errors"])

    def test_detects_missing_relative_import(self):
        (self.temp_dir / "backend" / "__init__.py").write_text("")
        (self.temp_dir / "backend" / "app.py").write_text("from .missing import value\n")

        result = validate_project(str(self.temp_dir))

        assert result["success"] is False
        assert any("Relative import could not be resolved" in error["message"] for error in result["errors"])

    def test_reloads_changed_module_after_repair(self):
        (self.temp_dir / "backend" / "helper.py").write_text("VALUE = 1\n")
        app_path = self.temp_dir / "backend" / "app.py"
        app_path.write_text("import helper\n")

        first = validate_project(str(self.temp_dir))
        assert first["success"] is True

        (self.temp_dir / "backend" / "helper.py").write_text("def broken(:\n    pass\n")
        second = validate_project(str(self.temp_dir))

        assert second["success"] is False
        assert any(error["kind"] == "import" for error in second["errors"])
