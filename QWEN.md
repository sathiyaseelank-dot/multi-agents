# Multi-Agent Orchestrator - Project Context

## Project Overview

The **Multi-Agent Orchestrator** is a sophisticated task orchestration system that coordinates multiple AI agents to complete software development tasks autonomously. It functions as an "AI Development Team OS" where different AI agents specialize in different roles (planning, backend, frontend, testing) and work together under the coordination of a central Python orchestrator.

**Current Version:** 0.3.0 (Phase 3 — Parallel DAG Execution)
**Location:** `/home/abirami/Desktop/sathi/multi/multi-agents/`
**Python Version:** 3.12+
**License:** MIT

### Core Architecture

```
User Input → Orchestrator → Codex (Plans) → JSON Plan → Workers → Code Files
```

The system uses a **DAG-based parallel execution** model where tasks are executed in phases based on dependencies:
- **Phase 1:** Tasks with no dependencies run in parallel
- **Phase 2+:** Tasks run when all dependencies are satisfied
- **Fallback:** Failed tasks retry with alternate agents
- **Skip:** Tasks with failed dependencies are skipped

### AI Agents

| Agent | Role | CLI Command | Output Format |
|-------|------|-------------|---------------|
| **Codex** | Planner | `codex exec "..."` | JSON |
| **OpenCode** | Backend | `opencode run "..."` | Code blocks |
| **Gemini** | Frontend | `gemini -p "..."` | JSON/Code blocks |
| **Kilo** | Testing | `kilo run "..."` | Code blocks |

## Directory Structure

```
multi-agents/
├── orchestrator/          # Core orchestration engine (~2000+ lines)
│   ├── main.py            # CLI entry point
│   ├── orchestrator.py    # Main workflow engine
│   ├── state_machine.py   # 10-state workflow (INIT→COMPLETED/FAILED)
│   ├── task_manager.py    # Task lifecycle & checkpoints
│   ├── task_router.py     # DAG topological sort + fallback routing
│   ├── context_accumulator.py  # Pass results between dependent tasks
│   ├── output_writer.py   # Write code blocks to files
│   ├── logger.py          # Structured logging
│   ├── project_builder.py # Build project structure
│   ├── validation_engine.py # Validate generated code
│   ├── runtime_executor.py # Execute generated code
│   ├── repair_engine.py   # Self-healing repairs
│   ├── goal_analyzer.py   # Analyze task goals
│   ├── memory_store.py    # Persistent memory storage
│   ├── pattern_learner.py # Learn from patterns
│   ├── meta_controller.py # Meta-level control
│   └── ... (more modules)
│
├── agents/                # Agent integrations
│   ├── base_agent.py      # Abstract base class with retry logic
│   ├── planner.py         # Codex integration
│   ├── backend.py         # OpenCode integration
│   ├── frontend.py        # Gemini integration
│   ├── tester.py          # Kilo integration
│   └── evaluator.py       # Evaluator agent
│
├── parsing/               # Output parsing pipeline
│   ├── extractor.py       # JSON & code block extraction
│   ├── sanitizer.py       # ANSI code stripping, normalization
│   └── validator.py       # Schema validation
│
├── flask_api/             # Flask REST API component
│   ├── app.py             # Flask application
│   ├── backend/           # Backend implementation
│   ├── routes/            # API routes (auth, chat, messages)
│   └── tests/             # API tests
│
├── frontend/              # React + Vite web dashboard
│   ├── src/               # React components
│   ├── index.html
│   └── package.json
│
├── tests/                 # Test suite (75+ tests)
│   ├── mock_agents/       # Fake CLI tools for offline testing
│   ├── test_*.py          # Test files for each module
│   └── test_integration.py # End-to-end tests
│
├── config/
│   └── agents.yaml        # Agent CLI configuration
│
├── memory/                # Runtime: plans, checkpoints, results (generated)
├── output/                # Generated code files (generated)
├── logs/                  # Session & per-agent logs (generated)
├── project/               # Generated projects (generated)
└── research/              # Phase 0 agent discovery docs
```

## Building and Running

### Prerequisites

- Python 3.12+
- AI agent CLIs installed and authenticated:
  - [Codex CLI](https://github.com/openai/codex)
  - [OpenCode CLI](https://github.com/opencode-ai/opencode)
  - [Gemini CLI](https://github.com/google/gemini-cli)
  - [Kilo CLI](https://github.com/kilo-ai/kilo)

### Installation

```bash
# Navigate to project directory
cd /home/abirami/Desktop/sathi/multi/multi-agents

# Create virtual environment (if not exists)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Orchestrator

```bash
# Basic usage - run with task description
python3 orchestrator/main.py "Build a REST API with user authentication"

# Read task from file
python3 orchestrator/main.py --file task.txt

# Plan only (don't execute workers)
python3 orchestrator/main.py "Build a login system" --plan-only

# Dry run (show plan without calling agents)
python3 orchestrator/main.py "Build a todo app" --dry-run

# Resume interrupted session
python3 orchestrator/main.py --resume 20260320-101850

# List previous sessions
python3 orchestrator/main.py --list

# Verbose logging
python3 orchestrator/main.py -v "Build a chat application"

# Self-healing mode (auto-repair on errors)
python3 orchestrator/main.py "Build X" --self-heal --max-repairs 3

# Orchestration healing (monitor for hangs)
python3 orchestrator/main.py "Build X" --orchestration-heal --health-timeout 60

# Heal existing project
python3 orchestrator/main.py --heal-project project/20260327-123456

# JSON output (for piping)
python3 orchestrator/main.py --json "Build X"
```

### CLI Options

| Flag | Description |
|------|-------------|
| `task` | Task description (positional) |
| `--file`, `-f` | Read task from file |
| `--verbose`, `-v` | Enable DEBUG logging |
| `--log-dir` | Log directory (default: `logs`) |
| `--memory-dir` | Memory/state directory (default: `memory`) |
| `--output-dir` | Output directory (default: `output`) |
| `--json` | Output result as JSON |
| `--resume SESSION_ID` | Resume interrupted session |
| `--list` | List previous sessions |
| `--plan-only` | Run planner only, no workers |
| `--dry-run` | Show plan without API calls |
| `--self-heal` | Enable auto-repair on errors |
| `--orchestration-heal` | Monitor orchestrator for hangs |
| `--heal-project` | Heal existing project directory |
| `--max-repairs` | Max self-heal attempts (default: 5) |
| `--health-timeout` | Seconds before considered stuck (default: 60) |
| `--max-orch-heals` | Max orchestration heals (default: 3) |
| `--version` | Show version info |

### Running Tests

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run specific test file
python3 -m pytest tests/test_state_machine.py -v

# Run with coverage
python3 -m pytest tests/ --cov=. --cov-report=html

# Run mock agent tests (offline)
python3 -m pytest tests/test_integration.py -v
```

### Running the Flask API

```bash
cd flask_api
python3 app.py
# API runs on http://localhost:5000
```

### Running the Web Dashboard

```bash
# Option 1: Use startup script
./start_web.sh

# Option 2: Start components separately
# Terminal 1 - Flask API
cd flask_api && python3 app.py

# Terminal 2 - Frontend
cd frontend && npm install && npm run dev
# Frontend runs on http://localhost:5173
```

## Configuration

### Environment Variables

Create `.env` from `.env.example`:

```bash
# Backend Agent (OpenCode)
OPENCODE_MODEL=claude/claude-3.5-sonnet

# Frontend Agent (Gemini)
GEMINI_MODEL=gemini-2.0-flash

# Testing Agent (Kilo)
KILO_MODEL=claude/claude-3.5-sonnet

# Flask API
FLASK_ENV=development
SECRET_KEY=your-secret-key
```

### Agent Configuration

Agent settings are in `config/agents.yaml`. Key configurations:
- CLI command templates
- Timeouts and retry counts
- Output format specifications
- Parsing strategies

## State Machine

The orchestrator follows a strict state machine:

```
INIT → PLANNING → PRE_VALIDATING → EXECUTING → BUILDING → VALIDATING → RUNNING → COMPLETED
                                      ↓              ↓           ↓
                                   REPLANNING    REPAIRING   REPAIRING
                                      ↓              ↓           ↓
                                   FAILED ←──────────────────────┘
```

**Valid Transitions:**
- `INIT` → `PLANNING`, `FAILED`
- `PLANNING` → `PRE_VALIDATING`, `EXECUTING`, `COMPLETED`, `FAILED`
- `EXECUTING` → `REPLANNING`, `BUILDING`, `FAILED`
- `BUILDING` → `VALIDATING`, `FAILED`
- `VALIDATING` → `RUNNING`, `REPAIRING`, `FAILED`
- `RUNNING` → `COMPLETED`, `REPAIRING`, `FAILED`
- `REPAIRING` → `VALIDATING`, `RUNNING`, `FAILED`
- `COMPLETED`, `FAILED` → (terminal states)

## Key Features

### 1. DAG-Based Parallel Execution
Tasks are analyzed for dependencies and executed in phases:
- Independent tasks run in parallel via `asyncio.gather()`
- Dependent tasks wait for prerequisites
- Topological sort determines execution order

### 2. Checkpoint/Resume
- Checkpoints saved after each execution phase
- Interrupted sessions can resume with `--resume SESSION_ID`
- Completed tasks are skipped on resume
- Running tasks reset to PENDING

### 3. Agent Fallback
If an agent fails, fallback routing tries alternates:
```python
FALLBACK_MAP = {
    "opencode": ["kilo", "gemini"],
    "gemini": ["opencode", "kilo"],
    "kilo": ["opencode", "gemini"],
}
```

### 4. Self-Healing
- `--self-heal`: Auto-repairs code errors via Kilo agent
- `--orchestration-heal`: Monitors orchestrator for hangs, auto-repairs
- Configurable max repair attempts

### 5. Context Passing
Completed task results are passed to dependent tasks:
```python
context = {
    "epic": "Build login system",
    "completed_tasks": [...],
    "files_created": ["auth.py", "models.py"]
}
```

### 6. Output File Writing
Code blocks extracted and written with correct extensions:
- Filename: `{task-id}-{slugified-title}.{ext}`
- Multi-block tasks: `-1.py`, `-2.sql`, etc.
- Language detection from code fence tags

## Development Conventions

### Code Style
- Python 3.12+ with type hints
- Async/await for I/O operations
- Modular architecture with single-responsibility modules
- Comprehensive logging at all levels

### Testing Practices
- Unit tests for each module
- Mock agents for offline integration testing
- 75+ tests covering all major functionality
- pytest with async support

### File Naming
- Modules: `snake_case.py`
- Test files: `test_*.py`
- Classes: `PascalCase`
- Constants: `UPPER_CASE`

### Logging
```python
import logging
logger = logging.getLogger(__name__)

logger.debug("Detailed info")
logger.info("Normal operation")
logger.warning("Potential issue")
logger.error("Error occurred")
```

## Output Artifacts

### Memory Directory (`memory/`)
- `plan-{session_id}.json` - Execution plan from Codex
- `checkpoint-{session_id}.json` - Task states for resume
- `results-{session_id}.json` - Aggregated results

### Output Directory (`output/`)
- Generated code files with task-based naming
- Multiple files per task numbered sequentially

### Logs Directory (`logs/`)
- Session logs with timestamps
- Per-agent execution logs

### Project Directory (`project/{session_id}/`)
- Complete generated project structure
- Ready-to-run code with dependencies

## API Endpoints (Flask API)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/orchestrator/run` | POST | Start new task |
| `/api/orchestrator/status/{session_id}` | GET | Check execution status |
| `/api/orchestrator/results/{session_id}` | GET | Get results |
| `/api/orchestrator/sessions` | GET | List sessions |
| `/api/orchestrator/health` | GET | Health check |

## Troubleshooting

### Agent Not Available
```
[WARNING] Unavailable agents: gemini
```
- Install the missing CLI tool
- Tasks for unavailable agents use fallback routing

### Rate Limits
If hitting rate limits on free-tier models:
```bash
export OPENCODE_MODEL="opencode/mimo-v2-pro-free"
export KILO_MODEL="kilo/kilo/auto-free"
```

### Session Resume
Find session ID from `memory/plan-*.json` files or use `--list`:
```bash
python3 orchestrator/main.py --list
python3 orchestrator/main.py --resume 20260320-101850
```

## Version History

| Version | Codename | Key Feature |
|---------|----------|-------------|
| 0.1.0 | Foundation | Initial structure |
| 0.2.0 | Multi-Agent | Agent integration |
| 0.3.0 | Parallel DAG | Parallel execution with dependencies |

## Related Documentation

- `README.md` - User-facing documentation
- `CHANGELOG.md` - Version history
- `plan.md` - Detailed implementation plan
- `WEB_INTERFACE.md` - Web dashboard documentation
- `config/agents.yaml` - Agent configuration reference
