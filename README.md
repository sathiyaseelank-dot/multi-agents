# Multi-Agent Orchestrator

**AI Development Team OS** — Coordinate multiple AI agents to complete complex software development tasks.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

The Multi-Agent Orchestrator is a sophisticated task orchestration system that coordinates multiple AI agents to complete software development tasks. It features:

- **DAG-based parallel execution** — Tasks execute in phases with automatic dependency resolution
- **Checkpoint/resume capability** — Recover from interruptions without losing progress
- **Agent fallback mechanism** — Automatic failover to alternate agents on failure
- **Structured output generation** — Code blocks extracted and written to files automatically

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Orchestrator                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Planner   │  │ Task Manager│  │  Context Accumulator    │  │
│  │   (Codex)   │  │             │  │                         │  │
│  └──────┬──────┘  └──────┬──────┘  └────────────┬────────────┘  │
│         │                │                       │               │
│         ▼                ▼                       ▼               │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              State Machine (INIT→DONE)                   │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
         │                │                       │
         ▼                ▼                       ▼
   ┌──────────┐    ┌──────────┐           ┌──────────┐
   │ Backend  │    │ Frontend │           │  Tester  │
   │(OpenCode)│    │ (Gemini) │           │  (Kilo)  │
   └──────────┘    └──────────┘           └──────────┘
```

## Agents

| Agent | Role | CLI Command | Output Format |
|-------|------|-------------|---------------|
| **Codex** | Planner | `codex exec "..."` | JSON |
| **OpenCode** | Backend | `opencode run "..."` | Code blocks |
| **Gemini** | Frontend | `gemini -p "..."` | JSON/Code blocks |
| **Kilo** | Testing | `kilo run "..."` | Code blocks |

## Installation

### Prerequisites

- Python 3.12+
- AI agent CLIs installed and authenticated:
  - [Codex CLI](https://github.com/openai/codex)
  - [OpenCode CLI](https://github.com/opencode-ai/opencode)
  - [Gemini CLI](https://github.com/google/gemini-cli)
  - [Kilo CLI](https://github.com/kilo-ai/kilo)

### Setup

```bash
# Clone the repository
git clone https://github.com/your-org/multi-agent-orchestrator.git
cd multi-agent-orchestrator

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
# Run with a task description
python3 orchestrator/main.py "Build a REST API with user authentication"

# Read task from file
python3 orchestrator/main.py --file task.txt

# Plan only (don't execute workers)
python3 orchestrator/main.py "Build a login system" --plan-only

# Resume interrupted session
python3 orchestrator/main.py --resume 20260320-101850

# Dry run (show plan without executing)
python3 orchestrator/main.py "Build a todo app" --dry-run

# Verbose logging
python3 orchestrator/main.py "Build a chat application" --verbose
```

### Command Line Options

```
usage: main.py [-h] [--file FILE] [--verbose] [--log-dir LOG_DIR]
               [--memory-dir MEMORY_DIR] [--json] [--output-dir OUTPUT_DIR]
               [--resume SESSION_ID] [--plan-only] [--dry-run] [--version]
               [task]

Multi-Agent Orchestration System — AI Development Team OS

positional arguments:
  task                  Task description (e.g., 'Build a login system')

options:
  -h, --help            show this help message and exit
  --file, -f FILE       Read task description from a file
  --verbose, -v         Enable verbose (DEBUG) logging
  --log-dir LOG_DIR     Directory for log files (default: logs)
  --memory-dir MEMORY_DIR
                        Directory for memory/state files (default: memory)
  --json                Output result as JSON
  --output-dir OUTPUT_DIR
                        Directory for generated code output (default: output)
  --resume SESSION_ID   Resume a previously interrupted session
  --plan-only           Only run the planning phase (show plan, don't execute)
  --dry-run             Show execution plan without calling any agents
  --version             Show version information
```

### Output

Generated code is written to the `output/` directory:

```
output/
├── task-001-set-up-flask-application-1.py
├── task-001-set-up-flask-application-2.sql
├── task-002-implement-user-crud-api-1.py
└── task-003-add-api-tests-1.py
```

State and checkpoint files are stored in `memory/`:

```
memory/
├── plan-20260320-101850.json      # Execution plan
├── checkpoint-20260320-101850.json # Task states
└── results-20260320-101850.json    # Aggregated results
```

## Configuration

### Agent Configuration

Agent settings are documented in `config/agents.yaml`. Environment variables can override defaults:

```bash
# Backend agent model
export OPENCODE_MODEL="claude/claude-3.5-sonnet"

# Frontend agent model
export GEMINI_MODEL="gemini-2.0-flash"

# Testing agent model
export KILO_MODEL="claude/claude-3.5-sonnet"
```

### Directory Structure

```
multi-agent-orchestrator/
├── orchestrator/       # Core orchestration engine
├── agents/             # Agent implementations
├── parsing/            # Output parsing utilities
├── tests/              # Test suite
├── config/             # Configuration files
├── logs/               # Log files (generated)
├── memory/             # State checkpoints (generated)
└── output/             # Generated code (generated)
```

## State Machine

The orchestrator follows a strict state machine:

```
INIT → PLANNING → EXECUTING → AGGREGATING → COMPLETED
                              ↓
                           FAILED (from any state)
```

## Task Execution

Tasks are executed in **phases** based on dependencies:

1. **Phase 1**: Tasks with no dependencies run in parallel
2. **Phase 2+**: Tasks run when all dependencies are satisfied
3. **Fallback**: Failed tasks retry with alternate agents
4. **Skip**: Tasks with failed dependencies are skipped

## Testing

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run specific test file
python3 -m pytest tests/test_calculator.py -v

# Run integration tests
python3 -m pytest tests/test_integration.py -v

# Run with coverage
python3 -m pytest tests/ --cov=. --cov-report=html
```

## Flask API

A separate Flask API is included in `flask_api/`:

```bash
cd flask_api
python3 app.py
```

See `flask_api/README.md` for API documentation.

## Version

Current version: **0.3.0** (Phase 3 — Parallel DAG Execution)

## License

MIT License — see [LICENSE](LICENSE) for details.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Acknowledgments

- OpenAI Codex for planning capabilities
- Google Gemini for frontend generation
- OpenCode and Kilo for backend and testing
# multi-agents
