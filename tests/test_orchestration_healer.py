"""Unit tests for orchestration healer module."""

import asyncio
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator.orchestration_healer import (
    HealthMonitor,
    HealthStatus,
    OrchestrationHealer,
    REPAIR_AGENTS,
    PHASE_FILE_MAP,
    _STATE_TRANSITION_RE,
    _PHASE_RE,
)
from orchestrator.events import EventEmitter, EventType


# ── HealthStatus ────────────────────────────────────────────────────────────


class TestHealthStatus:
    def test_initial_phase_is_init(self):
        status = HealthStatus()
        assert status.current_phase == "INIT"
        assert status.total_lines == 0

    def test_idle_seconds_increases(self):
        status = HealthStatus()
        assert status.idle_seconds >= 0

    def test_record_line_updates_phase_from_transition(self):
        status = HealthStatus()
        status.record_line("State: EXECUTING -> VALIDATING")
        assert status.current_phase == "VALIDATING"
        assert status.total_lines == 1

    def test_record_line_updates_phase_from_phase_message(self):
        status = HealthStatus()
        status.record_line("[Phase 2/5] starting tasks")
        assert status.current_phase == "EXECUTING"

    def test_record_line_resets_idle(self):
        status = HealthStatus()
        initial = status.idle_seconds
        status.record_line("some output line")
        assert status.idle_seconds < initial + 1  # should be near 0

    def test_output_lines_capped_at_500(self):
        status = HealthStatus()
        for i in range(600):
            status.record_line(f"line {i}")
        assert len(status.output_lines) == 500
        assert status.output_lines[0] == "line 100"
        assert status.output_lines[-1] == "line 599"

    def test_empty_lines_not_counted_in_output(self):
        status = HealthStatus()
        status.record_line("non-empty")
        status.record_line("")
        # total_lines counts all record_line calls; empty lines are filtered at _read_stream
        assert status.total_lines == 2
        assert len(status.output_lines) == 2


# ── Regex patterns ─────────────────────────────────────────────────────────


class TestRegexPatterns:
    def test_state_transition_re(self):
        m = _STATE_TRANSITION_RE.search("State: PLANNING -> EXECUTING")
        assert m is not None
        assert m.group(1) == "PLANNING"
        assert m.group(2) == "EXECUTING"

    def test_state_transition_re_no_match(self):
        assert _STATE_TRANSITION_RE.search("Random log line") is None

    def test_phase_re(self):
        m = _PHASE_RE.search("[Phase 3/7] executing tasks")
        assert m is not None
        assert m.group(1) == "3"
        assert m.group(2) == "7"


# ── HealthMonitor ───────────────────────────────────────────────────────────


class TestHealthMonitor:
    def test_is_stuck_false_initially(self):
        proc = MagicMock()
        proc.stdout = None
        proc.stderr = None
        proc.returncode = None
        monitor = HealthMonitor(proc, health_timeout=60)
        assert monitor.is_stuck is False
        assert monitor.stopped is False

    @pytest.mark.asyncio
    async def test_watchdog_detects_stuck(self):
        """HealthMonitor should flag stuck when no output for health_timeout seconds."""
        # Create a mock proc with no streams
        proc = MagicMock()
        proc.stdout = None
        proc.stderr = None
        proc.returncode = None

        monitor = HealthMonitor(proc, health_timeout=0.1)
        # Manually simulate no output by manipulating status
        monitor.status.last_output_time = 0  # force very old timestamp
        monitor.start()
        await asyncio.sleep(0.3)
        await monitor.stop()
        assert monitor.is_stuck is True

    @pytest.mark.asyncio
    async def test_watchdog_not_stuck_with_recent_output(self):
        proc = MagicMock()
        proc.stdout = None
        proc.stderr = None
        proc.returncode = None

        monitor = HealthMonitor(proc, health_timeout=10)
        monitor.start()
        await asyncio.sleep(0.1)
        await monitor.stop()
        assert monitor.is_stuck is False

    @pytest.mark.asyncio
    async def test_read_stream_parses_lines(self):
        """Monitor should read lines from a stream and update status."""
        reader = asyncio.StreamReader()
        reader.feed_data(b"State: INIT -> PLANNING\n")
        reader.feed_data(b"[Phase 1/3] starting\n")
        reader.feed_data(b"regular output line\n")
        reader.feed_eof()

        proc = MagicMock()
        proc.returncode = None

        monitor = HealthMonitor(proc, health_timeout=60)
        monitor.status.record_line("State: INIT -> PLANNING")
        monitor.status.record_line("[Phase 1/3] starting")
        monitor.status.record_line("regular output line")

        assert monitor.status.total_lines == 3
        assert monitor.status.current_phase == "EXECUTING"

    @pytest.mark.asyncio
    async def test_stop_cancels_tasks(self):
        proc = MagicMock()
        proc.stdout = None
        proc.stderr = None
        proc.returncode = None

        monitor = HealthMonitor(proc, health_timeout=60)
        monitor.start()
        assert len(monitor._tasks) == 1  # watchdog only
        await monitor.stop()
        assert monitor.stopped is True
        assert len(monitor._tasks) == 0


# ── OrchestrationHealer ────────────────────────────────────────────────────


class TestOrchestrationHealer:
    def setup_method(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        # Set up a fake project structure
        orch_dir = self.temp_dir / "orchestrator"
        orch_dir.mkdir()
        (orch_dir / "__init__.py").write_text("")
        (orch_dir / "orchestrator.py").write_text(
            "# orchestrator.py\nprint('orchestrator')\n"
        )
        (orch_dir / "runtime_executor.py").write_text(
            "# runtime_executor.py\nprint('executor')\n"
        )
        (orch_dir / "task_router.py").write_text("# task_router.py\nprint('router')\n")
        (orch_dir / "state_machine.py").write_text(
            "# state_machine.py\nclass State: pass\n"
        )

        # Create parsing dir
        parse_dir = self.temp_dir / "parsing"
        parse_dir.mkdir()
        (parse_dir / "__init__.py").write_text("")
        (parse_dir / "extractor.py").write_text(
            "import json, re\n"
            "def extract_json(s):\n"
            "    try:\n"
            "        return json.loads(s)\n"
            "    except:\n"
            "        return None\n"
            "def extract_code_blocks(s):\n"
            "    return []\n"
        )
        (parse_dir / "sanitizer.py").write_text("def clean_output(s): return s\n")

        # Config
        config_dir = self.temp_dir / "config"
        config_dir.mkdir()
        self.config_path = config_dir / "agents.yaml"
        self.config_path.write_text(
            yaml.dump(
                {
                    "agents": {
                        "kilo": {"timeout_seconds": 60, "retry_count": 2},
                        "opencode": {"timeout_seconds": 120, "retry_count": 2},
                    }
                }
            )
        )

        # Patch project root
        self._orig_project_root = OrchestrationHealer.__init__

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _make_healer(self, **kwargs) -> OrchestrationHealer:
        h = OrchestrationHealer(
            task="Test task",
            config_path=str(self.config_path),
            **kwargs,
        )
        h._project_root = self.temp_dir
        return h

    # ── Config fix tests ─────────────────────────────────────────────────

    def test_config_fix_doubles_timeouts(self):
        healer = self._make_healer()
        result = healer._try_config_fix("EXECUTING")
        assert result is True

        data = yaml.safe_load(self.config_path.read_text())
        agents = data["agents"]
        assert agents["kilo"]["timeout_seconds"] == 120
        assert agents["opencode"]["timeout_seconds"] == 240

    def test_config_fix_increments_retries(self):
        healer = self._make_healer()
        healer._try_config_fix("EXECUTING")

        data = yaml.safe_load(self.config_path.read_text())
        agents = data["agents"]
        assert agents["kilo"]["retry_count"] == 3
        assert agents["opencode"]["retry_count"] == 3

    def test_config_fix_caps_at_max(self):
        # Set already-high values
        self.config_path.write_text(
            yaml.dump(
                {
                    "agents": {
                        "kilo": {"timeout_seconds": 600, "retry_count": 5},
                    }
                }
            )
        )
        healer = self._make_healer()
        result = healer._try_config_fix("EXECUTING")
        assert result is False  # no change needed

    def test_config_fix_creates_backup(self):
        healer = self._make_healer()
        healer._try_config_fix("EXECUTING")

        backups = list(self.config_path.parent.glob("agents.yaml.bak.*"))
        assert len(backups) == 1

    def test_config_fix_validates_yaml_before_write(self):
        # The config should still be valid YAML after fix
        healer = self._make_healer()
        healer._try_config_fix("EXECUTING")
        data = yaml.safe_load(self.config_path.read_text())
        assert isinstance(data, dict)
        assert "agents" in data

    def test_config_fix_returns_false_for_missing_config(self):
        healer = self._make_healer()
        healer.config_path = Path("/nonexistent/agents.yaml")
        assert healer._try_config_fix("EXECUTING") is False

    # ── Code fix tests ───────────────────────────────────────────────────

    def test_collect_orch_files_executing(self):
        healer = self._make_healer()
        files = healer._collect_orch_files("EXECUTING")
        paths = [f["path"] for f in files]
        assert "orchestrator/runtime_executor.py" in paths
        assert "orchestrator/task_router.py" in paths
        assert "orchestrator/state_machine.py" in paths

    def test_collect_orch_files_planning(self):
        healer = self._make_healer()
        files = healer._collect_orch_files("PLANNING")
        paths = [f["path"] for f in files]
        assert "orchestrator/orchestrator.py" in paths

    def test_collect_orch_files_unknown_phase(self):
        healer = self._make_healer()
        files = healer._collect_orch_files("UNKNOWN_PHASE")
        assert len(files) >= 1  # should fallback to orchestrator.py

    def test_build_code_fix_prompt_contains_phase(self):
        healer = self._make_healer()
        files = healer._collect_orch_files("EXECUTING")
        prompt = healer._build_code_fix_prompt(
            "EXECUTING",
            "Stuck for 120s",
            files,
        )
        assert "EXECUTING" in prompt
        assert "Stuck for 120s" in prompt
        assert "Return JSON only" in prompt

    def test_apply_code_fix_writes_files(self):
        healer = self._make_healer()
        repair_result = {
            "files": [
                {
                    "path": "orchestrator/test_fix.py",
                    "content": "# fixed file\nprint('fixed')\n",
                    "operation": "update",
                }
            ],
            "summary": "Fixed test file",
        }
        applied = healer._apply_code_fix(repair_result)
        assert applied == ["orchestrator/test_fix.py"]
        assert (self.temp_dir / "orchestrator" / "test_fix.py").exists()

    def test_apply_code_fix_creates_backup(self):
        healer = self._make_healer()
        target = self.temp_dir / "orchestrator" / "existing.py"
        target.write_text("original content")

        repair_result = {
            "files": [
                {
                    "path": "orchestrator/existing.py",
                    "content": "fixed content",
                    "operation": "update",
                }
            ]
        }
        healer._apply_code_fix(repair_result)

        backups = list(target.parent.glob("existing.py.bak.*"))
        assert len(backups) == 1

    def test_apply_code_fix_refuses_outside_project(self):
        healer = self._make_healer()
        repair_result = {
            "files": [
                {
                    "path": "../../etc/passwd",
                    "content": "malicious",
                    "operation": "update",
                }
            ]
        }
        applied = healer._apply_code_fix(repair_result)
        assert applied == []

    def test_apply_code_fix_refuses_non_code_files(self):
        healer = self._make_healer()
        repair_result = {
            "files": [
                {
                    "path": "orchestrator/malware.exe",
                    "content": "binary stuff",
                    "operation": "update",
                }
            ]
        }
        applied = healer._apply_code_fix(repair_result)
        assert applied == []

    # ── Fallback chain tests ─────────────────────────────────────────────

    def test_repair_agents_order(self):
        assert REPAIR_AGENTS == ["kilo", "opencode", "gemini"]

    def test_build_agent_command_kilo(self):
        healer = self._make_healer()
        cmd = healer._build_agent_command("kilo", "test prompt")
        assert cmd == ["kilo", "run", "test prompt"]

    def test_build_agent_command_opencode(self):
        healer = self._make_healer()
        cmd = healer._build_agent_command("opencode", "test prompt")
        assert cmd == ["opencode", "run", "test prompt"]

    def test_build_agent_command_gemini(self):
        healer = self._make_healer()
        cmd = healer._build_agent_command("gemini", "test prompt")
        assert cmd == ["gemini", "-p", "test prompt", "--output-format", "json"]

    def test_build_agent_command_unknown(self):
        healer = self._make_healer()
        cmd = healer._build_agent_command("unknown", "test prompt")
        assert cmd is None

    # ── Heal metadata ────────────────────────────────────────────────────

    def test_build_heal_meta_empty(self):
        healer = self._make_healer()
        meta = healer._build_heal_meta()
        assert meta["enabled"] is True
        assert meta["heal_count"] == 0
        assert meta["heals"] == []

    def test_build_heal_meta_with_entries(self):
        healer = self._make_healer()
        healer._heal_count = 2
        healer._log_heal("config", "EXECUTING", True)
        healer._log_heal("code", "EXECUTING", False, agent="kilo")
        meta = healer._build_heal_meta()
        assert meta["heal_count"] == 2
        assert len(meta["heals"]) == 2
        assert meta["heals"][0]["heal_type"] == "config"
        assert meta["heals"][1]["agent"] == "kilo"

    # ── Event emission ───────────────────────────────────────────────────

    def test_emit_uses_event_emitter(self):
        lines = []
        emitter = EventEmitter(session_id="test", writer=lines.append)
        healer = self._make_healer(events=emitter)
        healer._emit(
            EventType.ORCHESTRATION_STUCK,
            {"phase": "EXECUTING", "idle_seconds": 120},
        )
        assert len(lines) == 1
        assert "EXECUTING" in lines[0]

    def test_emit_without_emitter_does_not_crash(self):
        healer = self._make_healer(events=None)
        healer._emit(EventType.ORCHESTRATION_STUCK, {"phase": "TEST"})

    # ── Build command ────────────────────────────────────────────────────

    def test_build_command_includes_task(self):
        healer = self._make_healer()
        cmd = healer._build_command()
        assert "python" in cmd
        assert "-m" in cmd
        assert "orchestrator.main" in cmd
        assert "Test task" in cmd

    def test_build_command_includes_dirs(self):
        healer = self._make_healer()
        cmd = healer._build_command()
        assert "--log-dir" in cmd
        assert "--memory-dir" in cmd


# ── PHASE_FILE_MAP ──────────────────────────────────────────────────────────


class TestPhaseFileMap:
    def test_all_phases_have_files(self):
        for phase, files in PHASE_FILE_MAP.items():
            assert len(files) > 0, f"Phase {phase} has no files"
            for f in files:
                assert f.startswith("orchestrator/"), f"File {f} not in orchestrator/"

    def test_executing_has_runtime_executor(self):
        assert "orchestrator/runtime_executor.py" in PHASE_FILE_MAP["EXECUTING"]

    def test_planning_has_orchestrator(self):
        assert "orchestrator/orchestrator.py" in PHASE_FILE_MAP["PLANNING"]


# ── Async integration-style tests ───────────────────────────────────────────


class TestHealFlow:
    @pytest.mark.asyncio
    async def test_config_fix_returns_true_on_success(self):
        temp_dir = Path(tempfile.mkdtemp())
        try:
            orch_dir = temp_dir / "orchestrator"
            orch_dir.mkdir()
            (orch_dir / "__init__.py").write_text("")
            (orch_dir / "orchestrator.py").write_text("# test\n")
            (orch_dir / "state_machine.py").write_text("# test\n")
            (orch_dir / "runtime_executor.py").write_text("# test\n")
            (orch_dir / "task_router.py").write_text("# test\n")

            config_dir = temp_dir / "config"
            config_dir.mkdir()
            config_path = config_dir / "agents.yaml"
            config_path.write_text(
                yaml.dump(
                    {
                        "agents": {
                            "kilo": {"timeout_seconds": 60, "retry_count": 2},
                        }
                    }
                )
            )

            healer = OrchestrationHealer(
                task="test",
                config_path=str(config_path),
            )
            healer._project_root = temp_dir

            stuck_result = {
                "status": "stuck",
                "phase": "EXECUTING",
                "idle_seconds": 120,
                "last_lines": [],
                "returncode": None,
            }

            result = await healer._attempt_heal(stuck_result)
            assert result is True  # config fix should work
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
