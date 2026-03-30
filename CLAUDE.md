# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-Agent Orchestrator (v0.3.0) — an AI Development Team OS that coordinates multiple AI agent CLIs (Codex, OpenCode, Gemini, Kilo) to complete complex software development tasks via DAG-based parallel execution with checkpoint/resume, agent fallback, and self-learning.

## Commands

### Setup
```bash
./setup.sh                    # Install deps, check agents, create dirs, run tests
pip install -r requirements.txt  # Install Python deps only
```

### Run Orchestrator
```bash
python3 orchestrator/main.py "Build a REST API with auth"
python3 orchestrator/main.py --file task.txt
python3 orchestrator/main.py "task" --plan-only     # Planning phase only
python3 orchestrator/main.py "task" --dry-run        # No agent calls
python3 orchestrator/main.py --resume SESSION_ID     # Resume interrupted session
python3 orchestrator/main.py --verbose               # DEBUG logging
```

### Tests
```bash
python3 -m pytest tests/ -v                          # All tests
python3 -m pytest tests/test_task_manager.py -v      # Single test file
python3 -m pytest tests/ --cov=. --cov-report=html   # Coverage report
```

Tests use mock agents in `tests/mock_agents/` for offline testing without real CLI tools.

### Web Interface
```bash
./start_web.sh                    # Flask API on :5000, then manually start frontend
cd flask_api && python3 app.py    # Flask API only
cd frontend && npm run dev        # Vite dev server on :5173
cd frontend && npm run build      # Production build
```

## Architecture

The system is a **state machine** driving a **DAG-based task executor**:

```
User Input → orchestrator/main.py (CLI entry)
  → orchestrator/orchestrator.py (main engine, ~2150 LOC)
    → State Machine: INIT → PLANNING → PRE_VALIDATING → EXECUTING
        → REPLANNING → BUILDING → VALIDATING → RUNNING → REPAIRING → COMPLETED/FAILED
    → Task Router: topological sort into parallel phases, fallback agent assignment
    → Context Accumulator: passes results between dependent tasks
    → Agent Pool (agents/): subprocess calls to external CLIs
    → Output Writer: extracts code blocks, writes to output/
```

### Core Engine (`orchestrator/`)

- **`orchestrator.py`** — Central workflow engine. Drives the state machine, dispatches tasks to agents, handles replanning and repair loops. The largest and most critical file.
- **`state_machine.py`** — Strict state transition enforcement (10 states).
- **`task_manager.py`** — Task lifecycle (pending/running/done/failed/skipped), checkpoints to `memory/`.
- **`task_router.py`** — Topological sort of task DAG into execution phases; assigns fallback agents on failure.
- **`context_accumulator.py`** — Collects and passes output from completed tasks to downstream dependents.
- **`dependency_resolver.py`** — Infers task dependencies from the plan.
- **`config_loader.py`** — Parses `config/agents.yaml`.

### Agent Layer (`agents/`)

All agents extend `base_agent.py` (async subprocess execution with retry logic). Each wraps a specific CLI:
- **`planner.py`** — Codex (`codex exec "..."`) for planning/review
- **`backend.py`** — OpenCode (`opencode run "..."`) for backend code
- **`frontend.py`** — Gemini (`gemini -p "..."`) for frontend code
- **`tester.py`** — Kilo (`kilo run "..."`) for test generation

Agent configuration lives in `config/agents.yaml` (timeouts, retry counts, parsing strategies, models).

### Output Pipeline (`parsing/`)

- **`extractor.py`** — Extracts JSON and code blocks from agent markdown output
- **`sanitizer.py`** — Strips ANSI codes, normalizes text
- **`validator.py`** — Schema validation for plans and results

### Self-Learning System

- **`pattern_learner.py`** — Extracts architecture/failure/success patterns from history
- **`strategy_scorer.py`** — Ranks strategies by effectiveness
- **`self_improver.py`** — Analyzes failures, improves prompts
- **`meta_controller.py`** — Balances exploration vs exploitation (epsilon-greedy)

### Repair & Validation

- **`validation_engine.py`** — Syntax and import checking of generated code
- **`pre_validation.py`** — Architecture risk prediction before execution
- **`repair_engine.py`** — Classifies errors and repairs broken code
- **`runtime_executor.py`** — Executes generated projects, captures output
- **`project_builder.py`** — Assembles generated code into project directory structure

### Web Interface

- **`flask_api/`** — Flask + Flask-SocketIO backend with blueprints (`routes/`), SQLAlchemy models, JWT auth
- **`frontend/`** — React 18 + Vite SPA with Dashboard, TaskCards, StatusPanel, EventList components

### Persistence

- **`memory/`** — Plan, checkpoint, and result JSON files keyed by session ID; meta-controller state
- **`logs/`** — Per-session and per-agent log files
- **`output/`** — Generated code files
- **`project/{SESSION_ID}/`** — Assembled project workspaces (backend/, frontend/, tests/)

## Key Design Patterns

- **Task execution is phase-based**: the dependency resolver computes topological phases; all tasks in a phase run in parallel, each phase waits for the prior phase to complete.
- **Agent fallback chain**: if an agent fails, the task router tries alternate agents (e.g., OpenCode fails → try Gemini → try Kilo).
- **Checkpoint/resume**: state is checkpointed at every state machine transition; `--resume SESSION_ID` recovers from any interruption.
- **All agent interaction is via subprocess**: agents are external CLIs invoked with `asyncio.create_subprocess_exec`, not library calls.
