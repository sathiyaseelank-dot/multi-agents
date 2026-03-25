"""Unit tests for the runtime executor."""

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import orchestrator.runtime_executor as runtime_executor


class TestRuntimeExecutor:
    def setup_method(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        (self.temp_dir / "backend").mkdir()

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_runtime_fails_on_wrong_entrypoint(self, monkeypatch):
        (self.temp_dir / "backend" / "app.py").write_text("print('done')\n")
        (self.temp_dir / "backend" / "service.py").write_text("from flask import Flask\napp = Flask(__name__)\n")
        monkeypatch.setattr(runtime_executor, "_create_venv", lambda *args, **kwargs: Path(sys.executable))
        monkeypatch.setattr(runtime_executor, "_run_command", lambda *args, **kwargs: True)

        result = runtime_executor.execute_project(str(self.temp_dir), startup_timeout=2, command_timeout=5)

        assert result["success"] is False
        assert result["entrypoint"].endswith("backend/app.py")

    def test_runtime_succeeds_on_correct_http_app(self, monkeypatch):
        app_code = """
from http.server import BaseHTTPRequestHandler, HTTPServer

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

server = HTTPServer(("127.0.0.1", 5000), Handler)
print("Running on http://127.0.0.1:5000", flush=True)
server.serve_forever()
"""
        (self.temp_dir / "backend" / "app.py").write_text(app_code)
        monkeypatch.setattr(runtime_executor, "_create_venv", lambda *args, **kwargs: Path(sys.executable))
        monkeypatch.setattr(runtime_executor, "_run_command", lambda *args, **kwargs: True)

        result = runtime_executor.execute_project(str(self.temp_dir), startup_timeout=5, command_timeout=10)

        assert result["success"] is True
        assert result["entrypoint"].endswith("backend/app.py")

    def test_dependency_install_uses_venv_python(self, monkeypatch):
        fake_python = self.temp_dir / ".venv" / "bin" / "python"
        fake_python.parent.mkdir(parents=True)
        fake_python.write_text("")
        (self.temp_dir / "requirements.txt").write_text("flask>=2.3.0\n")
        (self.temp_dir / "backend" / "app.py").write_text("print('done')\n")

        commands = []

        def fake_run_command(command, **kwargs):
            commands.append(command)
            return True

        monkeypatch.setattr(runtime_executor, "_create_venv", lambda *args, **kwargs: fake_python)
        monkeypatch.setattr(runtime_executor, "_run_command", fake_run_command)
        monkeypatch.setattr(runtime_executor, "_run_server_command", lambda *args, **kwargs: False)

        runtime_executor.execute_project(str(self.temp_dir), startup_timeout=1, command_timeout=5)

        assert commands
        assert commands[0][:3] == [str(fake_python), "-m", "pip"]
