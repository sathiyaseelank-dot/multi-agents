# Changelog

All notable changes to the Multi-Agent Orchestrator project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `.gitignore` file to exclude build artifacts, virtual environments, and runtime files
- Comprehensive README.md with installation, usage, and architecture documentation
- CHANGELOG.md for tracking version history
- `__version__.py` module for centralized version management
- `.env.example` template for environment variable configuration

### Fixed
- `tests/test_calculator.py` now properly imports from `calculator.py` instead of redefining functions
- Removed `users.db` from git tracking (security fix)

### Changed
- Improved test structure to follow pytest best practices

---

## [0.3.0] - 2026-03-20

### Added
- **Parallel DAG Execution** — Tasks execute in parallel within phases based on dependency
- **Checkpoint/Resume** — Recover from interruptions; tasks stuck in RUNNING reset to PENDING
- **Agent Fallback** — Automatic failover to alternate agents when primary fails
- **State Machine** — Strict state transitions (INIT → PLANNING → EXECUTING → AGGREGATING → COMPLETED/FAILED)
- **Output Writer** — Automatic code block extraction and file generation
- **Context Accumulator** — Pass results from completed tasks to downstream dependencies
- **Task Router** — DAG-aware task routing with fallback agent selection
- **Plan-Only Mode** — `--plan-only` flag to show execution plan without running workers
- **Dry Run Mode** — `--dry-run` flag for testing without API calls
- **Resume Session** — `--resume SESSION_ID` to continue interrupted sessions

### Changed
- Orchestrator now computes execution phases from task dependencies using topological sort
- Task manager saves checkpoints after each phase
- Improved error handling and logging throughout

---

## [0.2.0] - 2026-03-19

### Added
- **Multi-Agent Support** — Codex (planner), OpenCode (backend), Gemini (frontend), Kilo (tester)
- **Base Agent Class** — Abstract base class with retry logic and timeout handling
- **Parsing Pipeline** — JSON extraction, code block extraction, ANSI sanitization
- **Agent Configuration** — YAML configuration for agent CLI parameters
- **Memory System** — JSON-based state persistence for plans and results

### Changed
- Agent discovery and CLI interface testing completed (Phase 0)
- Structured logging implemented

---

## [0.1.0] - 2026-03-19

### Added
- Initial project structure
- Basic orchestrator skeleton
- Agent integration stubs
- Flask API component

---

## Version History Summary

| Version | Codename | Key Feature |
|---------|----------|-------------|
| 0.1.0 | Foundation | Initial structure |
| 0.2.0 | Multi-Agent | Agent integration |
| 0.3.0 | Parallel DAG | Parallel execution with dependencies |
| Unreleased | Polish | Documentation and testing improvements |

---

## Upcoming (Planned)

### Version 0.4.0 — Enhanced Testing
- [ ] Mock agent framework for integration testing
- [ ] Unit tests for all parsing modules
- [ ] Code coverage reporting
- [ ] CI/CD pipeline integration

### Version 0.5.0 — Configuration Management
- [ ] Load agent configuration from YAML
- [ ] Environment variable overrides
- [ ] Profile support for different setups

### Version 0.6.0 — Advanced Features
- [ ] Web search integration for agents
- [ ] Session continuation across restarts
- [ ] Progress reporting and ETA estimation
- [ ] Cost tracking per task/agent

### Version 1.0.0 — Production Release
- [ ] Stable API
- [ ] Comprehensive documentation
- [ ] Performance optimizations
- [ ] Security hardening
