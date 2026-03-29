# Multi-Agent Orchestrator CLI

Enhanced command-line interface for the Multi-Agent Orchestrator system.

---

## Quick Start

### Installation

```bash
# Run the interactive installer
./install-cli.sh

# Or manually add alias to your shell config
echo 'alias multi="$PWD/multi-cli"' >> ~/.bashrc
source ~/.bashrc
```

### Verify Installation

```bash
multi --help
multi info
multi agents
```

---

## Commands

### `run` - Execute a Task

Run a new orchestration task with full options.

```bash
# Basic usage
multi run "Build a REST API with user authentication"

# With self-healing
multi run "Build a login system" --self-heal --max-repairs 3

# Dry run (no API calls)
multi run "Build a todo app" --dry-run

# Plan only
multi run "Build a chat application" --plan-only

# Verbose logging
multi run "Build X" --verbose

# Orchestration healing (monitor for hangs)
multi run "Build X" --orchestration-heal --health-timeout 60
```

**Options:**
| Flag | Description |
|------|-------------|
| `--file`, `-f` | Read task from file |
| `--verbose`, `-v` | Enable DEBUG logging |
| `--dry-run` | Show plan without API calls |
| `--plan-only` | Run planner only, no workers |
| `--self-heal` | Enable auto-repair on errors |
| `--max-repairs` | Max self-heal attempts (default: 5) |
| `--orchestration-heal` | Monitor orchestrator for hangs |
| `--health-timeout` | Seconds before considered stuck (default: 60) |
| `--max-orch-heals` | Max orchestration heals (default: 3) |
| `--json` | Output result as JSON |

---

### `resume` - Resume Session

Resume an interrupted orchestration session.

```bash
# Interactive - shows available sessions
multi resume

# Specific session
multi resume 20260329-101850
```

---

### `list` - List Sessions

List previous orchestration sessions.

```bash
# List all sessions
multi list

# Filter by status
multi list --status completed
multi list --status incomplete

# Limit results
multi list --limit 10
```

**Output example:**
```
Previous Sessions (5):
  ----------------------------------------------------------------------
  20260329-101850    2026-03-29T10:18:50  ✓ COMPLETED
    └─ Build a REST API with user authentication (6 tasks)
  
  20260328-143022    2026-03-28T14:30:22  ○ INCOMPLETE [RESUMABLE]
    └─ Build a login system (4 tasks)
```

---

### `status` - Session Details

Show detailed status of a specific session.

```bash
multi status 20260329-101850
```

**Output example:**
```
Session: 20260329-101850
============================================================

Task: Build a REST API with user authentication
Created: 2026-03-29T10:18:50
Status: ✓ COMPLETED

Tasks (6):
  [✓ COMPLETED] task-001: Set up Flask application (opencode)
  [✓ COMPLETED] task-002: Create database models (opencode)
  [✓ COMPLETED] task-003: Implement auth endpoints (opencode)
  [✓ COMPLETED] task-004: Build login UI (gemini)
  [✓ COMPLETED] task-005: Write unit tests (kilo)
  [✓ COMPLETED] task-006: Integration tests (kilo)

Results:
  Project: /path/to/project/20260329-101850
  Validation: ✓ PASSED
  Runtime: ✓ PASSED
```

---

### `clean` - Cleanup

Remove old sessions and temporary files.

```bash
# Clean files older than 7 days
multi clean --days 7

# Clean everything
multi clean --all
```

---

### `agents` - Check Agents

Check which AI agents are available.

```bash
multi agents
```

**Output:**
```
Agent Availability:
========================================
  ✓ codex - Available
  ✓ opencode - Available
  ✓ gemini - Available
  ✓ kilo - Available

4/4 agents available
```

---

### `quick` - Quick Presets

Run with common preset configurations.

```bash
# Plan only
multi quick plan "Build a REST API"

# Test run (dry run + verbose)
multi quick test "Build a login system"

# Full run with self-healing
multi quick heal "Build a chat application"

# Standard full execution
multi quick full "Build a todo app"
```

**Presets:**
| Preset | Flags |
|--------|-------|
| `plan` | `--plan-only` |
| `test` | `--dry-run --verbose` |
| `heal` | `--self-heal --max-repairs 3` |
| `full` | (none) |

---

### `search` - Search Sessions

Search across sessions using ripgrep.

```bash
# Search in memory files
multi search "authentication" --memory

# Search in logs
multi search "ERROR" --logs

# Search in output files
multi search "def login" --output

# Search everywhere
multi search "user_id" --memory --logs --output

# JSON only
multi search "task-001" --json-only
```

**Requires:** `ripgrep` (`sudo apt install ripgrep`)

---

### `info` - Project Info

Show project information and statistics.

```bash
multi info
```

**Output:**
```
Multi-Agent Orchestrator v0.3.0 (Phase 3 — Parallel DAG Execution)
============================================================

Location: /home/abirami/Desktop/sathi/multi/multi-agents
Version: 0.3.0
Python files: 156
Test files: 25

Directories:
  memory       28 files
  logs         9 files
  output       0 files
  project      1 files

Agents:
  ✓ codex
  ✓ opencode
  ✓ gemini
  ✓ kilo
```

---

## Usage Examples

### Workflow 1: Plan First, Then Execute

```bash
# Review the plan first
multi quick plan "Build a Flask REST API with CRUD endpoints"

# If plan looks good, execute
multi run "Build a Flask REST API with CRUD endpoints"
```

### Workflow 2: Debug Failed Session

```bash
# List sessions
multi list --status incomplete

# Check status
multi status 20260329-101850

# Search logs for errors
multi search "ERROR" --logs

# Resume with self-healing
multi resume 20260329-101850
```

### Workflow 3: Monitor Agent Health

```bash
# Check agents before running
multi agents

# Run task
multi run "Build a login system"

# Check results
multi list --limit 5
```

### Workflow 4: Cleanup Old Sessions

```bash
# See what you have
multi list

# Clean old sessions (older than 30 days)
multi clean --days 30

# Verify
multi list
```

---

## Shell Completion (Optional)

Add tab completion for bash:

```bash
# Add to ~/.bashrc
_multi_cli_completion() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    COMPREPLY=( $(compgen -W "run resume list status clean agents quick info search" -- "$cur") )
}
complete -F _multi_cli_completion multi
```

---

## Integration with Navigation Tools

Combine with `zoxide`, `fzf`, and `ripgrep` for enhanced workflow:

```bash
# Jump to memory and search
z memory && multi search "authentication" --json-only

# Fuzzy find session
multi list | fzf | awk '{print $1}' | xargs multi status

# Search logs with context
multi search "FAILED" --logs | rg -C 3 "task-"
```

---

## Troubleshooting

### Command Not Found

```bash
# If using alias, ensure shell config is sourced
source ~/.bashrc

# If using symlink, ensure ~/bin is in PATH
export PATH="$HOME/bin:$PATH"
```

### Permission Denied

```bash
chmod +x multi-cli
```

### Python Import Errors

```bash
# Ensure you're in the project directory
cd /path/to/multi-agents

# Or set PYTHONPATH
export PYTHONPATH="$PWD:$PYTHONPATH"
```

### Ripgrep Not Found

```bash
# Install ripgrep
sudo apt install ripgrep
# or
brew install ripgrep
```

---

## Version

**CLI Version:** 1.0.0
**Orchestrator Version:** 0.3.0

---

## License

MIT License - same as the main project.
