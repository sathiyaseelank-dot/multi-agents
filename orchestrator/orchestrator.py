"""Main orchestration engine — coordinates planning and execution."""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from .state_machine import State, StateMachine
from .task_manager import TaskManager, TaskStatus
from .task_router import compute_phases, get_fallback_agent, compute_execution_summary
from .context_accumulator import ContextAccumulator
from .output_writer import write_task_output
from .project_builder import build_project
from .config_loader import load_agent_configs
from agents.planner import PlannerAgent
from agents.backend import BackendAgent
from agents.frontend import FrontendAgent
from agents.tester import TesterAgent
from agents.base_agent import AgentConfig
from __version__ import VERSION_DESCRIPTION

logger = logging.getLogger(__name__)

# Map agent names to their classes
AGENT_REGISTRY = {
    "opencode": BackendAgent,
    "gemini": FrontendAgent,
    "kilo": TesterAgent,
}


class Orchestrator:
    def __init__(
        self,
        log_dir: str = "logs",
        memory_dir: str = "memory",
        output_dir: str = "output",
        plan_only: bool = False,
        resume_session_id: Optional[str] = None,
    ):
        self.state_machine = StateMachine(on_transition=self._on_state_change)
        self.task_manager = TaskManager(memory_dir=memory_dir)
        self.context = ContextAccumulator()
        self.log_dir = log_dir
        self.memory_dir = memory_dir
        self.output_dir = output_dir
        self.plan_only = plan_only
        self.resume_session_id = resume_session_id
        self.session_id = resume_session_id or datetime.now().strftime("%Y%m%d-%H%M%S")
        self.plan: Optional[dict] = None
        self._agents: dict = {}
        self._output_files: dict[str, list[str]] = {}
        self._agent_configs = load_agent_configs()
        self.planner = self._build_planner()
        self._ensure_dirs()

    def _build_planner(self) -> PlannerAgent:
        """Build the planner from loaded config."""
        cfg = self._agent_configs.get("codex")
        if cfg:
            return PlannerAgent(config=AgentConfig(
                name=cfg["name"], role=cfg["role"],
                command=cfg["command"], subcommand=cfg.get("subcommand"),
                args=cfg.get("args", []),
                timeout_seconds=cfg.get("timeout_seconds", 120),
                retry_count=cfg.get("retry_count", 3),
                retry_backoff_seconds=cfg.get("retry_backoff_seconds", 2),
                env_vars=cfg.get("env_vars", {}),
            ))
        return PlannerAgent()

    def _ensure_dirs(self):
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)
        Path(self.memory_dir).mkdir(parents=True, exist_ok=True)

    def _on_state_change(self, old_state: State, new_state: State):
        logger.info(f"State transition: {old_state.value} -> {new_state.value}")

    def _get_agent(self, agent_name: str):
        """Get or create an agent instance by name, using loaded config."""
        if agent_name not in self._agents:
            cls = AGENT_REGISTRY.get(agent_name)
            if cls is None:
                raise ValueError(f"Unknown agent: {agent_name}")
            cfg = self._agent_configs.get(agent_name)
            if cfg:
                config = AgentConfig(
                    name=cfg["name"], role=cfg["role"],
                    command=cfg["command"], subcommand=cfg.get("subcommand"),
                    args=cfg.get("args", []),
                    timeout_seconds=cfg.get("timeout_seconds", 120),
                    retry_count=cfg.get("retry_count", 2),
                    retry_backoff_seconds=cfg.get("retry_backoff_seconds", 5),
                    env_vars=cfg.get("env_vars", {}),
                )
                self._agents[agent_name] = cls(config=config)
            else:
                self._agents[agent_name] = cls()
        return self._agents[agent_name]

    def _check_agents(self) -> list[str]:
        """Check which agents are available. Returns list of unavailable agent names."""
        unavailable = []
        for name in AGENT_REGISTRY:
            try:
                agent = self._get_agent(name)
                if not agent.is_available():
                    unavailable.append(name)
            except Exception:
                unavailable.append(name)
        return unavailable

    async def resume(self) -> dict:
        """Resume a previously interrupted session from checkpoint."""
        sid = self.resume_session_id
        logger.info(f"Resuming session {sid}")
        self._print_banner()
        print(f"\n  Resuming session: {sid}\n")

        # Load plan
        plan_file = Path(self.memory_dir) / f"plan-{sid}.json"
        if not plan_file.exists():
            return {"status": "failed", "error": f"Plan file not found for session {sid}"}
        saved = json.loads(plan_file.read_text())
        self.plan = saved["plan"]

        # Load checkpoint (task states)
        ok = self.task_manager.load_checkpoint(sid)
        if not ok:
            return {"status": "failed", "error": f"Checkpoint not found for session {sid}"}

        self.context.epic = self.plan.get("epic", "")

        # Rebuild context from saved results of already-completed tasks
        results_file = Path(self.memory_dir) / f"results-{sid}.json"
        if results_file.exists():
            saved_results = json.loads(results_file.read_text())
            for task_id, result_data in saved_results.get("results", {}).items():
                task = self.task_manager.get_task(task_id)
                if task and task.status.value == "success":
                    self.context.add_result(task_id, task.title, result_data)
                    logger.debug(f"Restored context for completed task {task_id}")

        # Report what we're resuming from
        pending = self.task_manager.get_tasks_by_status(TaskStatus.PENDING)
        completed = self.task_manager.get_tasks_by_status(TaskStatus.SUCCESS)
        print(f"  Checkpoint: {len(completed)} completed, {len(pending)} pending\n")

        tasks = list(self.task_manager.tasks.values())
        phases = compute_phases(tasks)

        # Display current state
        self._display_resume_state()

        try:
            # Must pass through PLANNING to reach EXECUTING
            self.state_machine.transition(State.PLANNING)
            self.state_machine.transition(State.EXECUTING)
            await self._execute_phases(phases)
            self.state_machine.transition(State.AGGREGATING)
            summary = self._aggregate()
            self.state_machine.transition(State.COMPLETED)
            return self._build_result("completed", plan=self.plan, summary=summary)
        except Exception as e:
            logger.error(f"Resume failed: {e}")
            self.state_machine.fail(str(e))
            return self._build_result("failed", error=str(e))

    def _display_resume_state(self):
        """Show which tasks are done and which will run."""
        print("  Task status:")
        print("  " + "-" * 40)
        for task in self.task_manager.tasks.values():
            icon = {"success": "OK", "failed": "FAIL", "skipped": "SKIP",
                    "pending": "...", "running": "->>"}.get(task.status.value, "?")
            print(f"    [{icon}] {task.id}: {task.title}")
        print()

    async def run(self, task_description: str) -> dict:
        """Run the full orchestration workflow for a given task."""
        logger.info(f"Session {self.session_id} started")
        logger.info(f"Task: {task_description}")

        self._print_banner()
        print(f"\n  Task: \"{task_description}\"\n")

        # Health check
        unavailable = self._check_agents()
        if unavailable:
            print(f"  [WARNING] Unavailable agents: {', '.join(unavailable)}")
            print(f"  (tasks for these agents will use fallback routing)\n")

        try:
            # Phase: Planning
            self.state_machine.transition(State.PLANNING)
            self.plan = await self._plan(task_description)

            if self.plan is None:
                self.state_machine.fail("Planner returned no valid plan")
                return self._build_result("failed", error="Planning failed")

            self._display_plan(self.plan)
            self._save_plan(self.plan)

            # Load tasks into manager
            self.task_manager.load_from_plan(self.plan)
            self.context.epic = self.plan.get("epic", task_description)

            # Compute and display execution phases from DAG
            tasks = list(self.task_manager.tasks.values())
            phases = compute_phases(tasks)
            print(f"\n  Computed execution order ({len(phases)} phases):")
            print(compute_execution_summary(phases))

            if self.plan_only:
                self.state_machine.transition(State.COMPLETED)
                logger.info("Plan-only mode — skipping execution")
                return self._build_result("completed", plan=self.plan)

            # Phase: Executing
            self.state_machine.transition(State.EXECUTING)
            await self._execute_phases(phases)

            # Phase: Aggregating
            self.state_machine.transition(State.AGGREGATING)
            summary = self._aggregate()

            self.state_machine.transition(State.COMPLETED)
            return self._build_result("completed", plan=self.plan, summary=summary)

        except Exception as e:
            logger.error(f"Orchestration failed: {e}")
            self.state_machine.fail(str(e))
            return self._build_result("failed", error=str(e))

    async def _plan(self, task_description: str) -> Optional[dict]:
        """Send task to Codex planner and get structured subtask breakdown."""
        print("  [Planner] Sending task to Codex...")

        if not self.planner.is_available():
            logger.error("Codex CLI not found in PATH")
            print("  [ERROR] codex command not found. Is it installed?")
            return None

        prompt = self.planner.build_prompt(task_description)
        result = await self.planner.execute(prompt)

        if result.status != "success":
            logger.error(f"Planner failed: {result.error}")
            print(f"  [ERROR] Planner failed: {result.error}")
            return None

        plan = result.parsed_output
        if plan is None:
            logger.error("Could not parse planner output")
            logger.debug(f"Raw output:\n{result.raw_output[:1000]}")
            print("  [ERROR] Could not parse structured plan from Codex output")
            return None

        issues = self.planner.validate_plan(plan)
        if issues:
            logger.warning(f"Plan validation issues: {issues}")
            print(f"  [WARNING] Plan has issues: {', '.join(issues)}")

        print(f"  [Planner] Received {len(plan.get('tasks', []))} subtasks")
        return plan

    async def _execute_phases(self, phases: list[list]):
        """Execute tasks phase by phase — parallel within each phase."""
        for phase_num, phase_tasks in enumerate(phases, 1):
            # Skip tasks that are already done (shouldn't happen, but be safe)
            pending = [t for t in phase_tasks if t.status == TaskStatus.PENDING]
            if not pending:
                continue

            parallel = len(pending) > 1
            mode = "PARALLEL" if parallel else "SEQUENTIAL"
            task_ids = ", ".join(t.id for t in pending)
            print(f"\n  [Phase {phase_num}/{len(phases)}] [{mode}] {len(pending)} task(s): {task_ids}")
            print("  " + "-" * 56)

            if parallel:
                results = await asyncio.gather(
                    *(self._execute_task_with_fallback(task) for task in pending),
                    return_exceptions=True,
                )
                for task, result in zip(pending, results):
                    if isinstance(result, Exception):
                        self.task_manager.fail_task(task.id, str(result))
                        print(f"    [{task.id}] EXCEPTION: {result}")
            else:
                for task in pending:
                    await self._execute_task_with_fallback(task)

            # Save checkpoint after each phase
            self.task_manager.save_checkpoint(self.session_id)

            # Check if any tasks failed — skip downstream dependents
            failed = self.task_manager.get_tasks_by_status(TaskStatus.FAILED)
            if failed:
                failed_ids = {t.id for t in failed}
                for remaining_phase in phases[phase_num:]:
                    for task in remaining_phase:
                        if task.status == TaskStatus.PENDING:
                            deps = set(task.dependencies)
                            if deps & failed_ids:
                                self.task_manager.skip_task(
                                    task.id,
                                    f"Dependency failed: {deps & failed_ids}",
                                )

    async def _execute_task_with_fallback(self, task):
        """Execute a task, falling back to an alternate agent on failure."""
        success = await self._execute_task(task)
        if success:
            return

        # Try fallback agent
        fallback = get_fallback_agent(task.agent, task.type)
        if fallback:
            print(f"    [{task.id}] Trying fallback agent: {fallback}")
            logger.info(f"Falling back from {task.agent} to {fallback} for {task.id}")

            # Reset task status to pending for retry
            task.status = TaskStatus.PENDING
            task.error = None
            original_agent = task.agent
            task.agent = fallback

            success = await self._execute_task(task)
            if not success:
                task.agent = original_agent  # restore for reporting

    async def _execute_task(self, task) -> bool:
        """Execute a single task with its assigned agent. Returns True on success."""
        self.task_manager.start_task(task.id)
        print(f"    [{task.id}] Starting: {task.title} (agent: {task.agent})")

        try:
            agent = self._get_agent(task.agent)
        except ValueError as e:
            self.task_manager.fail_task(task.id, str(e))
            print(f"    [{task.id}] FAILED: {e}")
            return False

        if not agent.is_available():
            error = f"{task.agent} CLI not found in PATH"
            self.task_manager.fail_task(task.id, error)
            print(f"    [{task.id}] FAILED: {error}")
            return False

        # Build context from dependencies
        context = self.context.build_context(task.dependencies)
        prompt = agent.build_prompt(task.description, context=context)

        result = await agent.execute(prompt)

        if result.status == "success":
            self.task_manager.complete_task(
                task.id,
                result=result.parsed_output or {},
                execution_time=result.execution_time,
            )
            # Accumulate for downstream tasks
            self.context.add_result(task.id, task.title, result.parsed_output)

            # Note: File writing is deferred to _aggregate() which calls project_builder
            # to create a structured project instead of flat files

            summary = ""
            if result.parsed_output:
                summary = result.parsed_output.get("summary", "done")
            print(f"    [{task.id}] SUCCESS ({result.execution_time:.1f}s): {summary}")
            return True
        else:
            self.task_manager.fail_task(
                task.id,
                error=result.error or "Unknown error",
                execution_time=result.execution_time,
            )
            print(f"    [{task.id}] FAILED ({result.execution_time:.1f}s): {result.error}")
            return False

    def _aggregate(self) -> dict:
        """Aggregate results from all completed tasks and build structured project."""
        summary = self.task_manager.summary()
        results = self.context.get_all_results()

        print(f"\n" + "=" * 60)
        print("  RESULTS")
        print("=" * 60)

        total_blocks = 0
        total_lines = 0
        for task_id, task in self.task_manager.tasks.items():
            status_icon = {
                TaskStatus.SUCCESS: "OK",
                TaskStatus.FAILED: "FAIL",
                TaskStatus.SKIPPED: "SKIP",
            }.get(task.status, "?")

            print(f"    [{status_icon}] {task.id}: {task.title} ({task.execution_time:.1f}s)")

            if task.result and task.result.get("code_blocks"):
                blocks = task.result["code_blocks"]
                total_blocks += len(blocks)
                for block in blocks:
                    lang = block.get("language", "?")
                    lines = len(block.get("code", "").splitlines())
                    total_lines += lines
                    print(f"           {lang}: {lines} lines")

        counts = summary["counts"]
        print(f"\n  Total: {summary['total']} tasks | "
              f"Success: {counts.get('success', 0)} | "
              f"Failed: {counts.get('failed', 0)} | "
              f"Skipped: {counts.get('skipped', 0)}")
        if total_blocks:
            print(f"  Code: {total_blocks} blocks, {total_lines} lines")
        print("=" * 60)

        # Build structured project from task results
        # Convert task results to format expected by project_builder
        task_results_for_builder = {}
        for task_id, task in self.task_manager.tasks.items():
            if task.result:
                task_results_for_builder[task_id] = {
                    "type": task.type,
                    "title": task.title,
                    "code_blocks": task.result.get("code_blocks", []),
                }

        # Build the project
        project_dir = Path(self.output_dir).parent / "project"
        build_result = build_project(task_results_for_builder, str(project_dir))

        self._output_files = {
            "project_files": build_result.get("files_created", [])
        }
        self._project_build_result = build_result

        if build_result.get("files_created"):
            print(f"\n  Project built: {len(build_result['files_created'])} files created")
            print(f"  Location: {project_dir}/")
            if build_result.get("entrypoint"):
                print(f"  Entrypoint: {build_result['entrypoint']}")
            if build_result.get("requirements"):
                print(f"  Requirements: {build_result['requirements']}")

            # Print file structure
            print("\n  Project structure:")
            for dir_name, dir_path in build_result.get("structure", {}).items():
                print(f"    {dir_name}/")
                # List files in each directory
                dir_files = [
                    f for f in build_result.get("files_created", [])
                    if f.startswith(dir_path)
                ]
                for f in dir_files:
                    print(f"      - {Path(f).name}")

        # Save full results
        results_file = Path(self.memory_dir) / f"results-{self.session_id}.json"
        save_data = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "summary": summary,
            "results": {k: _safe_serialize(v) for k, v in results.items()},
            "output_files": self._output_files,
            "project_build": _safe_serialize(build_result),
        }
        results_file.write_text(json.dumps(save_data, indent=2, default=str))
        logger.info(f"Results saved to {results_file}")
        print(f"\n  Results saved to: {results_file}")

        return summary

    def _display_plan(self, plan: dict):
        """Pretty-print the plan to console."""
        tasks = plan.get("tasks", [])
        phases = plan.get("phases", [])

        print("\n" + "=" * 60)
        print("  EXECUTION PLAN")
        print("=" * 60)

        if plan.get("epic"):
            print(f"\n  Epic: {plan['epic']}")

        print(f"\n  Tasks ({len(tasks)}):")
        print("  " + "-" * 56)

        for task in tasks:
            tid = task.get("id", "?")
            title = task.get("title", "Untitled")
            agent = task.get("agent", "?")
            task_type = task.get("type", "?")
            deps = task.get("dependencies", [])
            dep_str = f" (depends on: {', '.join(deps)})" if deps else ""

            print(f"    [{tid}] {title}")
            print(f"           Agent: {agent} | Type: {task_type}{dep_str}")

        if phases:
            print(f"\n  Phases ({len(phases)}):")
            print("  " + "-" * 56)
            for phase in phases:
                pnum = phase.get("phase", "?")
                desc = phase.get("description", "")
                parallel = "parallel" if phase.get("parallel") else "sequential"
                task_ids = phase.get("task_ids", [])
                print(f"    Phase {pnum} ({parallel}): {desc}")
                print(f"           Tasks: {', '.join(task_ids)}")

        print("\n" + "=" * 60)

    def _save_plan(self, plan: dict):
        plan_file = Path(self.memory_dir) / f"plan-{self.session_id}.json"
        data = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "plan": plan,
        }
        plan_file.write_text(json.dumps(data, indent=2))
        logger.info(f"Plan saved to {plan_file}")

    def _build_result(self, status: str, **kwargs) -> dict:
        return {
            "session_id": self.session_id,
            "status": status,
            "state": self.state_machine.state.value,
            "state_history": [
                (s1.value, s2.value) for s1, s2 in self.state_machine.history
            ],
            **kwargs,
        }

    @staticmethod
    def _print_banner():
        print()
        print("=" * 60)
        print(f"   {VERSION_DESCRIPTION}")
        print("   AI Development Team OS")
        print("=" * 60)


def _safe_serialize(obj):
    """Make an object JSON-serializable."""
    if isinstance(obj, dict):
        return {k: _safe_serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_safe_serialize(v) for v in obj]
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    return str(obj)
