# Multi-Agent Orchestration System

## Production-Ready AI Dev Team OS — v0.3.0

**Status:** Fully implemented and tested (Phases 0–4 complete)
**Location:** `/home/inkyank-01/multi-agent-orchestrator/`
**Date:** 2026-03-24
**Tests:** 75 passing

---

## Project Vision

A terminal-based system where multiple AI agents (Codex, OpenCode, Gemini, Kilo) collaborate as an autonomous development team, orchestrated by a central Python engine.

**Core Philosophy:**
- **Codex** = Brain (Decision Maker & Planner)
- **Python Orchestrator** = Hands (Executor & Controller)
- **CLI Agents** = Workers (OpenCode, Gemini, Kilo)

```
User Input -> Orchestrator -> Codex (Plans) -> JSON -> Orchestrator -> Workers -> Code Files
```

---

## Architecture

```
+---------------------------------------------------------------+
|                         CLI Interface                          |
|       python3 orchestrator/main.py "Build login system"       |
+-------------------------------+-------------------------------+
                                |
                                v
+---------------------------------------------------------------+
|                    ORCHESTRATOR (Python)                       |
|  +---------------+  +---------------+  +--------------------+ |
|  | State Machine |  | Task Manager  |  | Context            | |
|  | (6 states)    |  | (DAG-aware)   |  | Accumulator        | |
|  +---------------+  +---------------+  +--------------------+ |
|                                                               |
|  +---------------+  +---------------+  +--------------------+ |
|  | Task Router   |  | Output Writer |  | Logger             | |
|  | (topo sort +  |  | (code->files) |  | (structured logs)  | |
|  |  fallback)    |  |               |  |                    | |
|  +---------------+  +---------------+  +--------------------+ |
+-------------------------------+-------------------------------+
                                |
                                v
+---------------------------------------------------------------+
|                         AGENT POOL                            |
|  +----------+  +----------+  +----------+  +-----------+     |
|  |  Codex   |  | OpenCode |  |  Gemini  |  |   Kilo    |     |
|  | (Plan)   |  | (Backend)|  | (Frontend)|  | (Testing) |     |
|  | codex    |  | opencode |  | gemini   |  | kilo      |     |
|  | exec     |  | run      |  | -p       |  | run --auto|     |
|  +----------+  +----------+  +----------+  +-----------+     |
+-------------------------------+-------------------------------+
                                |
                                v
+---------------------------------------------------------------+
|                    OUTPUT & PERSISTENCE                        |
|  +----------+  +----------+  +----------+  +-----------+     |
|  |  output/ |  |  memory/ |  |   logs/  |  | research/ |     |
|  | .py .js  |  | plans    |  | session  |  | CLI docs  |     |
|  | .sql .ts |  | checks   |  | per-agent|  | samples   |     |
|  |          |  | results  |  |          |  |           |     |
|  +----------+  +----------+  +----------+  +-----------+     |
+---------------------------------------------------------------+
```

---

## Project Structure

```
~/multi-agent-orchestrator/
|
+-- orchestrator/                    # Core engine (1,188 lines)
|   +-- __init__.py
|   +-- main.py                      # CLI entry point (142 lines)
|   +-- orchestrator.py              # Workflow engine: plan->execute->aggregate (498 lines)
|   +-- state_machine.py             # INIT->PLANNING->EXECUTING->AGGREGATING->COMPLETED (74 lines)
|   +-- task_manager.py              # Task lifecycle, checkpoints, resume (181 lines)
|   +-- task_router.py               # DAG topological sort + fallback routing (89 lines)
|   +-- context_accumulator.py       # Pass results between dependent tasks (44 lines)
|   +-- output_writer.py             # Write code blocks to files (102 lines)
|   +-- logger.py                    # Structured logging to file + console (57 lines)
|
+-- agents/                          # CLI agent integrations (534 lines)
|   +-- __init__.py
|   +-- base_agent.py                # Abstract base: async subprocess + retry (161 lines)
|   +-- planner.py                   # Codex integration (125 lines)
|   +-- backend.py                   # OpenCode integration (82 lines)
|   +-- frontend.py                  # Gemini integration (81 lines)
|   +-- tester.py                    # Kilo integration (84 lines)
|
+-- parsing/                         # Output extraction pipeline (209 lines)
|   +-- __init__.py
|   +-- extractor.py                 # JSON + code block extraction from CLI output (82 lines)
|   +-- sanitizer.py                 # Strip ANSI codes, progress lines, normalize (51 lines)
|   +-- validator.py                 # Schema validation for plans + worker results (73 lines)
|
+-- tests/                           # Test suite — 75 tests (1,027 lines)
|   +-- test_extractor.py            # Parsing pipeline tests (123 lines)
|   +-- test_state_machine.py        # State transition tests (76 lines)
|   +-- test_task_manager.py         # Task lifecycle + checkpoint tests (102 lines)
|   +-- test_task_router.py          # DAG computation + fallback tests (74 lines)
|   +-- test_output_writer.py        # File writing tests (51 lines)
|   +-- test_integration.py          # End-to-end: pipeline, fallback, resume (213 lines)
|   +-- test_calculator.py           # Calculator demo tests (202 lines)
|   +-- mock_agents/                 # Fake CLI tools for offline testing
|       +-- mock_codex.py            # Returns canned JSON plan
|       +-- mock_opencode.py         # Returns Python code blocks
|       +-- mock_gemini.py           # Returns JSX code blocks
|       +-- mock_kilo.py             # Returns pytest code blocks
|
+-- config/
|   +-- agents.yaml                  # Verified CLI patterns from Phase 0 research
|
+-- research/                        # Phase 0 agent discovery
|   +-- AGENT_DISCOVERY.md           # Full CLI research report
|   +-- codex_samples/               # Real Codex output samples
|   +-- opencode_samples/            # Real OpenCode output samples
|   +-- gemini_samples/              # Real Gemini output samples
|
+-- memory/                          # Runtime: plans, checkpoints, results (JSON)
+-- output/                          # Generated code files from agent runs
+-- logs/                            # Session + per-agent log files
+-- requirements.txt                 # pytest, pytest-asyncio, pyyaml
```

**Total: ~2,960 lines of Python across 28 source files**

---

## Agent CLI Interfaces (Verified)

All four agents are installed and their CLI interfaces were tested in Phase 0.

| Agent | Role | CLI Command | Non-Interactive Mode | Output Format |
|-------|------|-------------|---------------------|---------------|
| **Codex** | Planner | `codex exec "<prompt>"` | `exec` subcommand | JSON in markdown fenced blocks |
| **OpenCode** | Backend | `opencode run "<prompt>"` | `run` subcommand | Markdown with code blocks; `--format json` available |
| **Gemini** | Frontend | `gemini -p "<prompt>"` | `-p` flag | Code blocks; `--output-format json` available |
| **Kilo** | Testing | `kilo run --auto "<prompt>"` | `run` subcommand | Markdown with code blocks; `--format json` available |

### Model Override (Environment Variables)

```bash
OPENCODE_MODEL="opencode/mimo-v2-pro-free"   # Default: qwen/qwen3-32b (has TPM limits)
GEMINI_MODEL="gemini-2.0-flash"              # Optional
KILO_MODEL="kilo/kilo/auto-free"             # Recommended: avoids shared quota issues
```

### Known Constraints

- **OpenCode** default model (`qwen/qwen3-32b`) has a 6,000 TPM limit on free tier — use `OPENCODE_MODEL` to switch
- **Gemini** may hit quota exhaustion on testing credentials — retries handle this
- **Codex** requires a git repository context — add `--skip-git-repo-check` if needed
- **Kilo** shares quota tier with OpenCode on some providers

---

## State Machine

```
+---------+
|  INIT   | <-- Entry point
+----+----+
     | start
     v
+-----------+
| PLANNING  | <-- Codex analyzes task, returns JSON subtask plan
+-----+-----+
      | plan ready
      v
+-----------+
| EXECUTING | <-- Workers run in DAG-aware phases
+-----+-----+     Phase 1 (parallel): backend + frontend
      |            Phase 2 (sequential): testing
      v
+-------------+
| AGGREGATING | <-- Collect results, write output files
+------+------+
       | done
       v
+-----------+
| COMPLETED | <-- All tasks finished
+-----------+

Any state --> FAILED (on unrecoverable error)
```

Valid transitions:
- INIT -> PLANNING, FAILED
- PLANNING -> EXECUTING, COMPLETED (plan-only mode), FAILED
- EXECUTING -> AGGREGATING, FAILED
- AGGREGATING -> COMPLETED, EXECUTING (loop back), FAILED

---

## CLI Usage

```bash
# Full pipeline: plan + execute all agents + write output files
python3 orchestrator/main.py "Build a login system"

# Read task from file
python3 orchestrator/main.py --file task.txt

# Plan only — calls Codex, shows plan, does not run workers
python3 orchestrator/main.py --plan-only "Build a REST API"

# Dry run — same as plan-only with explicit banner
python3 orchestrator/main.py --dry-run "Build a REST API"

# Resume a crashed/interrupted session
python3 orchestrator/main.py --resume 20260320-101850

# Custom directories
python3 orchestrator/main.py --output-dir ./gen --memory-dir ./state "Build X"

# JSON output (for piping)
python3 orchestrator/main.py --json "Build X"

# Verbose logging
python3 orchestrator/main.py -v "Build X"

# Version
python3 orchestrator/main.py --version
```

### All CLI Flags

| Flag | Description |
|------|-------------|
| `"task"` | Task description (positional argument) |
| `--file`, `-f` | Read task from a file instead |
| `--plan-only` | Run Codex planner only, don't execute workers |
| `--dry-run` | Show plan without executing workers (no code gen) |
| `--resume SESSION_ID` | Resume from checkpoint after crash |
| `--output-dir DIR` | Directory for generated code (default: `output/`) |
| `--memory-dir DIR` | Directory for plans/checkpoints (default: `memory/`) |
| `--log-dir DIR` | Directory for log files (default: `logs/`) |
| `--json` | Output full result as JSON |
| `-v`, `--verbose` | Enable DEBUG-level logging |
| `--version` | Show version |

---

## Execution Flow (Detailed)

### 1. Planning Phase

The orchestrator sends the task to Codex with a structured prompt that requests JSON output:

```
codex exec "You are a task planner... Break down: <user task>
Return JSON: { epic, tasks: [{id, type, agent, title, description, dependencies}], phases }"
```

Codex returns a JSON plan in a markdown fenced block. The parsing pipeline:
1. Strips ANSI codes from raw output
2. Finds ` ```json ... ``` ` blocks via regex
3. Tries `json.loads()` on each match (skipping invalid ones)
4. Falls back to raw JSON parsing or regex extraction
5. Validates the plan structure (tasks exist, agents are valid, no duplicate IDs)
6. Normalizes `subtasks` -> `tasks` (Codex sometimes uses either key)

### 2. DAG Execution Phase

Tasks are loaded into the TaskManager and phases computed via topological sort:

```python
# compute_phases() in task_router.py
# Input:  [task-001(no deps), task-002(no deps), task-003(deps: 001, 002)]
# Output: [[task-001, task-002], [task-003]]
#         Phase 1 (parallel)    Phase 2 (sequential)
```

For each phase:
- **Parallel tasks** run via `asyncio.gather()` (truly concurrent subprocesses)
- **Sequential tasks** run one at a time
- Each agent gets context from completed dependency tasks (via `ContextAccumulator`)
- Failed tasks trigger fallback routing to an alternate agent
- Checkpoint written to disk after each phase

### 3. Fallback Routing

If an agent fails (timeout, rate limit, CLI error), the orchestrator tries an alternate:

```python
FALLBACK_MAP = {
    "opencode": ["kilo", "gemini"],
    "gemini": ["opencode", "kilo"],
    "kilo": ["opencode", "gemini"],
}
```

The fallback agent receives the same prompt and context. If it also fails, the task is marked FAILED and downstream dependents are SKIPPED.

### 4. Output & Aggregation

- Code blocks extracted from agent output are written to `output/` with correct file extensions
- Language detection from fenced block tags (` ```python `, ` ```javascript `, etc.)
- Results JSON saved to `memory/results-<session>.json`
- Checkpoint saved to `memory/checkpoint-<session>.json`
- Console displays summary: task statuses, code block counts, file paths

---

## Crash Recovery

The orchestrator writes checkpoints after every execution phase. To resume:

```bash
python3 orchestrator/main.py --resume 20260320-101850
```

Resume behavior:
1. Loads `memory/plan-<session>.json` to restore the original plan
2. Loads `memory/checkpoint-<session>.json` to restore task states
3. Tasks stuck in `RUNNING` (in-progress when crash happened) are reset to `PENDING`
4. Already-completed tasks are skipped — only pending tasks re-execute
5. Context from completed tasks is rebuilt from saved results
6. Execution continues from where it left off

Example: if a 3-task pipeline crashed during task-003 (testing), resume will:
- Skip task-001 (completed) and task-002 (completed)
- Jump to Phase 3 and re-run only task-003
- Aggregate all results (including previously completed ones)

---

## Context Passing Between Tasks

When tasks have dependencies, the `ContextAccumulator` injects completed results into downstream prompts:

```python
# After task-001 (backend) completes:
context = {
    "epic": "Build a login system",
    "completed_tasks": [
        {"title": "Implement auth API", "summary": "Generated 3 code blocks",
         "code_blocks": [{"language": "python", "code": "def login()..."}]}
    ],
    "files_created": ["auth.py", "models.py"]
}

# This context is injected into the prompt for task-003 (testing):
# "Write tests for: ... Context: Code to test: - Implement auth API: Generated 3 code blocks"
```

This allows the testing agent to write tests that reference the actual code structure the backend agent produced.

---

## Output File Writing

Generated code blocks are saved to the `output/` directory with:
- Filename: `{task-id}-{slugified-title}.{ext}` (e.g., `task-001-implement-auth-api.py`)
- Multiple blocks per task get numbered suffixes: `-1.py`, `-2.sql`, `-3.py`
- Extension mapping: `python`->`.py`, `javascript`->`.js`, `sql`->`.sql`, `jsx`->`.jsx`, etc.
- Raw text fallback: if no code blocks found, output saved as `.txt`

---

## Parsing Pipeline

The `parsing/` package handles the messy reality of CLI agent output:

```
Raw CLI stdout
    |
    v
sanitizer.strip_ansi()       -- Remove ANSI color/cursor escape sequences
    |
    v
sanitizer.strip_progress()   -- Remove spinner chars (braille dots, |/-\)
    |
    v
sanitizer.normalize()        -- Collapse blank lines, trim whitespace
    |
    v
extractor.extract_json()     -- Strategy 1: ```json blocks
                              -- Strategy 2: raw JSON parse
                              -- Strategy 3: regex for {...} or [...]
    |
    v
extractor.extract_code_blocks()  -- Find all ```<lang>..``` blocks
    |
    v
validator.validate_plan()        -- Verify task IDs, agent names, dependencies
validator.validate_worker_result()  -- Verify code/summary fields
```

---

## Testing

### Run All Tests

```bash
cd ~/multi-agent-orchestrator
python3 -m pytest tests/ -v
```

### Test Suite Breakdown (75 tests)

| File | Tests | What It Covers |
|------|-------|----------------|
| `test_extractor.py` | 12 | ANSI stripping, JSON extraction from markdown, code block parsing |
| `test_state_machine.py` | 9 | Valid/invalid transitions, terminal states, history tracking |
| `test_task_manager.py` | 9 | Load from plan, dependency resolution, checkpoints |
| `test_task_router.py` | 8 | Topological sort, diamond deps, parallel groups, fallback agents |
| `test_output_writer.py` | 5 | Code block writing, multi-block, raw text fallback |
| `test_integration.py` | 7 | Full pipeline with mocks, fallback routing, resume, plan-only |
| `test_calculator.py` | 25 | Calculator demo (generated by agents in Phase 2 live test) |

### Mock Agents

The `tests/mock_agents/` directory contains fake CLI scripts that mimic real agent behavior:
- Return canned JSON/code blocks on stdout
- Support `MOCK_EXIT_CODE=1` to simulate failure
- Support `MOCK_DELAY=<seconds>` to simulate slow response
- Callable as real subprocesses (identical interface to actual agents)

This allows the full integration test suite to run offline without API calls.

---

## Live Test Results

### Test 1: Calculator (Phase 2)

```bash
OPENCODE_MODEL="opencode/mimo-v2-pro-free" \
KILO_MODEL="kilo/kilo/auto-free" \
python3 orchestrator/main.py "Build a simple Python calculator with add, subtract, multiply, divide"
```

**Result:** 3 tasks, 3 success, 2 code blocks, ~13s total
- Codex planned 3 tasks (core functions -> CLI -> tests)
- OpenCode generated calculator functions (21s)
- Gemini built CLI interface (100s, retried once on timeout)
- Kilo wrote test plan (90s)

### Test 2: REST API (Phase 3)

```bash
python3 orchestrator/main.py "Build a REST API with user CRUD endpoints using Flask and SQLite"
```

**Result:** 3 tasks, 3 success, 13 code blocks, 343 lines, 13 output files
- Phase 1: Flask + SQLite setup (76s, 7 files)
- Phase 2: CRUD endpoints (132s, 5 files, retried once)
- Phase 3: API tests (131s, 1 file)

### Test 3: Crash Recovery (Phase 4)

Simulated crash mid-testing, resumed with `--resume`:
- Skipped 2 completed tasks
- Re-ran only the interrupted task (2.8s vs original 131s)
- All 3 tasks completed successfully

---

## Reliability Features

### Timeout Handling

Per-agent configurable timeouts with `asyncio.wait_for()`:

| Agent | Timeout | Reason |
|-------|---------|--------|
| Codex | 120s | Planning is fast (5–15s typical) |
| OpenCode | 180s | Code gen can be slow on free models |
| Gemini | 300s | Observed 273s on first run; needs headroom |
| Kilo | 180s | Test gen comparable to code gen |

### Retry with Exponential Backoff

```python
# retry_count attempts, doubling wait time each retry
# Attempt 1: immediate
# Attempt 2: wait 5s (backoff * 2^0)
# Attempt 3: wait 10s (backoff * 2^1)
```

### Agent Health Checks

At startup, the orchestrator verifies each agent CLI is installed:
```
[WARNING] Unavailable agents: gemini
(tasks for these agents will use fallback routing)
```

### Loop Prevention

- Maximum 20 execution rounds (safety limit)
- Circular dependencies detected by topological sort (unresolved tasks logged as warning)
- Tasks with failed dependencies are automatically SKIPPED

---

## Environment Variables

```bash
# Model overrides (avoid rate limits on free tiers)
OPENCODE_MODEL="opencode/mimo-v2-pro-free"
GEMINI_MODEL="gemini-2.0-flash"
KILO_MODEL="kilo/kilo/auto-free"

# Mock control (for testing)
MOCK_EXIT_CODE=1                    # Simulate agent failure
MOCK_DELAY=5                        # Simulate slow agent response
```

---

## Implementation Phases (Completed)

### Phase 0: Agent CLI Research
Tested all 4 CLI tools, documented working invocation patterns, discovered free models and rate limits. Results in `research/AGENT_DISCOVERY.md` and `config/agents.yaml`.

### Phase 1: Core Orchestrator + Planner (MVP)
Built `main.py`, `state_machine.py`, `orchestrator.py`, `logger.py`, `base_agent.py`, `planner.py`, and the full `parsing/` pipeline. Live-tested against Codex — returned structured 6-task plan in 13s.

### Phase 2: Single Worker Execution
Added `task_manager.py`, `context_accumulator.py`, `backend.py`, `frontend.py`, `tester.py`, `validator.py`. Extended orchestrator for EXECUTING and AGGREGATING states. Live-tested full pipeline — all 3 tasks succeeded with generated code.

### Phase 3: Parallel DAG Execution
Added `task_router.py` (topological sort), `output_writer.py`, fallback routing, agent health checks. Live-tested with Flask CRUD API — 13 output files, 343 lines of code.

### Phase 4: Reliability & Polish
Added crash recovery with `--resume`, mock agents for offline testing, integration test suite (7 tests covering pipeline, fallback, resume, plan-only). Total: 75 tests passing.

---

## Future Enhancements

1. **Session listing** — `--list` flag to browse previous sessions
2. **Real-time streaming** — Stream agent output as it arrives (instead of waiting for completion)
3. **Web dashboard** — Flask/FastAPI UI showing execution progress
4. **Plugin architecture** — Custom agent registration via YAML
5. **Cost tracking** — Token usage / API cost per task
6. **Code assembly** — Merge generated code blocks into a working project structure
7. **Diff review** — Show diffs before writing output files
8. **Parallel model comparison** — Run same task on multiple models, pick best result

---

**Version:** 0.3.0
**Python:** 3.12+
**License:** MIT
