"""Unit tests for the dependency resolver."""

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator.dependency_resolver import resolve_dependencies


class TestDependencyResolver:
    def setup_method(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        (self.temp_dir / "backend").mkdir()

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_infers_flask_dependency_from_backend_app(self):
        (self.temp_dir / "backend" / "app.py").write_text("from flask import Flask\napp = Flask(__name__)\n")

        result = resolve_dependencies(str(self.temp_dir))

        assert "flask>=2.3.0" in result["python_dependencies"]
        requirements = (self.temp_dir / "requirements.txt").read_text()
        assert "flask>=2.3.0" in requirements
