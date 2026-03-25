"""Unit tests for the repair engine."""

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator.repair_engine import (
    build_repair_prompt,
    choose_repair_agent,
    classify_error,
    collect_relevant_files,
)


class TestRepairEngine:
    def setup_method(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        (self.temp_dir / "backend").mkdir()
        (self.temp_dir / "backend" / "app.py").write_text("print('hi')\n")

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_classify_error(self):
        assert classify_error("Syntax error at line 1") == "syntax"
        assert classify_error("No module named flask") == "import"
        assert classify_error("pip install failed") == "dependency"
        assert classify_error("connection refused") == "runtime"

    def test_choose_repair_agent(self):
        assert choose_repair_agent("frontend/App.jsx", "runtime") == "gemini"
        assert choose_repair_agent("tests/test_app.py", "runtime") == "kilo"
        assert choose_repair_agent("backend/app.py", "syntax") == "opencode"

    def test_build_prompt_includes_relevant_files(self):
        files = collect_relevant_files(str(self.temp_dir), "backend/app.py")
        prompt = build_repair_prompt(
            project_dir=str(self.temp_dir),
            error_message="Syntax error",
            error_type="syntax",
            relevant_files=files,
            expected_behavior="App should run",
            target_file="backend/app.py",
        )
        assert "backend/app.py" in prompt
        assert "Expected behavior: App should run" in prompt
