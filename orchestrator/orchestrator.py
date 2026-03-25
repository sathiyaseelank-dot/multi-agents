"""Main orchestration engine — coordinates planning and execution."""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from .events import EventEmitter, EventType
from .state_machine import State, StateMachine
from .task_manager import TaskManager, TaskStatus
from .task_router import compute_phases, get_fallback_agent, compute_execution_summary
from .context_accumulator import ContextAccumulator
from .project_builder import build_project
from .repair_engine import (
    build_repair_prompt,
    choose_repair_agent,
    classify_error,
    collect_relevant_files,
)
from .goal_analyzer import analyze_goal
from .memory_store import MemoryStore
from .pre_validation import infer_architecture_signals, predict_plan_risks
from .validation_engine import validate_project
from .dependency_resolver import resolve_dependencies
from .runtime_executor import execute_project
from .config_loader import load_agent_configs
from agents.planner import PlannerAgent
from agents.backend import BackendAgent
from agents.frontend import FrontendAgent
from agents.tester import TesterAgent
from agents.evaluator import EvaluatorAgent
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
        summary_only: bool = False,
        events: Optional[EventEmitter] = None,
    ):
        self.state_machine = StateMachine(on_transition=self._on_state_change)
        self.task_manager = TaskManager(memory_dir=memory_dir)
        initial_session_id = resume_session_id or datetime.now().strftime("%Y%m%d-%H%M%S")
        self.context = ContextAccumulator(workspace_root=str(Path("project") / initial_session_id))
        self.log_dir = log_dir
        self.memory_dir = memory_dir
        self.output_dir = output_dir
        self.plan_only = plan_only
        self.resume_session_id = resume_session_id
        self.session_id = initial_session_id
        self.plan: Optional[dict] = None
        self._agents: dict = {}
        self._output_files: dict[str, list[str]] = {}
        self._project_build_result: dict = {}
        self._dependency_result: dict = {}
        self._validation_result: dict = {}
        self._runtime_result: dict = {}
        self._repair_history: list[dict] = []
        self._evaluation_result: dict = {}
        self._optimization_history: list[dict] = []
        self._replan_history: list[dict] = []
        self._task_candidates: dict[str, list[dict]] = {}
        self._goal_analysis: dict = {}
        self._planning_memories: list[dict] = []
        self._prevalidation_result: dict = {}
        self._memory_record: dict = {}
        self._original_prompt: str = ""
        self._refined_prompt: str = ""
        self.summary_only = summary_only
        self.events = events or EventEmitter(
            session_id=self.session_id,
            summary_only=summary_only,
        )
        self._agent_configs = load_agent_configs()
        self.memory_store = MemoryStore(memory_dir=memory_dir)
        self.planner = self._build_planner()
        self.evaluator = self._build_evaluator()
        self.project_dir = str(Path("project") / self.session_id)
        self.context.set_workspace_root(self.project_dir)
        self.session_log_dir = Path(self.log_dir) / self.session_id
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

    def _build_evaluator(self) -> EvaluatorAgent:
        """Build the evaluator from loaded config."""
        cfg = self._agent_configs.get("codex")
        if cfg:
            return EvaluatorAgent(config=AgentConfig(
                name=cfg["name"], role="evaluator",
                command=cfg["command"], subcommand=cfg.get("subcommand"),
                args=cfg.get("args", []),
                timeout_seconds=cfg.get("timeout_seconds", 120),
                retry_count=cfg.get("retry_count", 2),
                retry_backoff_seconds=cfg.get("retry_backoff_seconds", 2),
                env_vars=cfg.get("env_vars", {}),
            ))
        return EvaluatorAgent()

    def _ensure_dirs(self):
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)
        Path(self.memory_dir).mkdir(parents=True, exist_ok=True)
        self.session_log_dir.mkdir(parents=True, exist_ok=True)

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

        # Load plan
        plan_file = Path(self.memory_dir) / f"plan-{sid}.json"
        if not plan_file.exists():
            message = f"Plan file not found for session {sid}"
            self.events.emit(EventType.ERROR, {"message": message})
            self.state_machine.fail(message)
            self.events.emit(
                EventType.RUN_COMPLETED,
                self._build_run_completed_payload("failed", error=message),
            )
            return {"status": "failed", "error": message}
        saved = json.loads(plan_file.read_text())
        self.plan = saved["plan"]

        # Load checkpoint (task states)
        ok = self.task_manager.load_checkpoint(sid)
        if not ok:
            message = f"Checkpoint not found for session {sid}"
            self.events.emit(EventType.ERROR, {"message": message})
            self.state_machine.fail(message)
            self.events.emit(
                EventType.RUN_COMPLETED,
                self._build_run_completed_payload("failed", error=message),
            )
            return {"status": "failed", "error": message}

        self.context.epic = self.plan.get("epic", "")
        self._original_prompt = self.plan.get("epic", "")
        self._refined_prompt = self.plan.get("epic", "")

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
        self.events.emit(
            EventType.RUN_RESUMED,
            {
                "session_id": sid,
                "completed": len(completed),
                "pending": len(pending),
                "tasks": self._resume_tasks_payload(),
            },
        )

        tasks = list(self.task_manager.tasks.values())
        phases = compute_phases(tasks)

        try:
            # Must pass through PLANNING to reach EXECUTING
            self.state_machine.transition(State.PLANNING)
            self.state_machine.transition(State.PRE_VALIDATING)
            self._prevalidation_result = predict_plan_risks(self.plan, self._refined_prompt)
            self._write_session_artifact("prevalidation", self._prevalidation_result)
            self.state_machine.transition(State.EXECUTING)
            await self._execute_phases(phases)
            await self._replan_if_needed()
            self.state_machine.transition(State.BUILDING)
            summary = self._build_project()
            self.state_machine.transition(State.VALIDATING)
            self._validation_result = await self._validate_with_repairs()
            if not self._validation_result.get("success", False):
                raise RuntimeError("Validation failed after 3 repair attempts")
            self.state_machine.transition(State.RUNNING)
            self._runtime_result = await self._run_with_repairs()
            if not self._runtime_result.get("success", False):
                raise RuntimeError("Runtime execution failed after 3 repair attempts")
            self._evaluation_result = await self._evaluate_project(summary)
            self.state_machine.transition(State.COMPLETED)
            self._store_run_memory()
            self.events.emit(
                EventType.RUN_COMPLETED,
                self._build_run_completed_payload("completed", summary),
            )
            return self._build_result("completed", plan=self.plan, summary=summary)
        except Exception as e:
            logger.error(f"Resume failed: {e}")
            self.state_machine.fail(str(e))
            self.events.emit(EventType.ERROR, {"message": str(e)})
            self._store_run_memory()
            self.events.emit(
                EventType.RUN_COMPLETED,
                self._build_run_completed_payload("failed", error=str(e)),
            )
            return self._build_result("failed", error=str(e))

    def _resume_tasks_payload(self) -> list[dict]:
        """Build task status payload for resume rendering."""
        payload = []
        for task in self.task_manager.tasks.values():
            icon = {
                "success": "OK",
                "failed": "FAIL",
                "skipped": "SKIP",
                "pending": "...",
                "running": "->>",
            }.get(task.status.value, "?")
            payload.append({"icon": icon, "task_id": task.id, "title": task.title})
        return payload

    async def run(self, task_description: str) -> dict:
        """Run the full orchestration workflow for a given task."""
        logger.info(f"Session {self.session_id} started")
        logger.info(f"Task: {task_description}")
        self._original_prompt = task_description

        self.events.emit(EventType.RUN_STARTED, {"task": task_description})

        # Health check
        unavailable = self._check_agents()
        if unavailable:
            self.events.emit(
                EventType.WARNING,
                {
                    "message": f"Unavailable agents: {', '.join(unavailable)}",
                    "detail": "(tasks for these agents will use fallback routing)",
                },
            )

        try:
            # Phase: Planning
            self.state_machine.transition(State.PLANNING)
            self.plan = await self._plan(task_description)

            if self.plan is None:
                self.state_machine.fail("Planner returned no valid plan")
                self.events.emit(
                    EventType.RUN_COMPLETED,
                    self._build_run_completed_payload("failed", error="Planning failed"),
                )
                return self._build_result("failed", error="Planning failed")

            self._save_plan(self.plan)

            # Load tasks into manager
            self.task_manager.load_from_plan(self.plan)
            self.context.epic = self.plan.get("epic", self._refined_prompt or task_description)

            # Compute and display execution phases from DAG
            tasks = list(self.task_manager.tasks.values())
            phases = compute_phases(tasks)
            self.events.emit(
                EventType.PLAN_CREATED,
                {
                    "plan": self.plan,
                    "epic": self.plan.get("epic", task_description),
                    "task_count": len(self.plan.get("tasks", [])),
                    "phase_count": len(phases),
                    "execution_summary": compute_execution_summary(phases),
                },
            )

            self.state_machine.transition(State.PRE_VALIDATING)
            self._prevalidation_result = predict_plan_risks(
                self.plan,
                self._refined_prompt or task_description,
                self._planning_memories,
            )
            self._write_session_artifact("prevalidation", self._prevalidation_result)
            self._persist_session_results()
            predicted = self._prevalidation_result.get("predictions", [])
            for warning in predicted:
                self.events.emit(EventType.WARNING, {"message": warning.get("message", "")})

            if self.plan_only:
                self.state_machine.transition(State.COMPLETED)
                self._store_run_memory()
                logger.info("Plan-only mode — skipping execution")
                self.events.emit(
                    EventType.RUN_COMPLETED,
                    self._build_run_completed_payload(
                        "completed",
                        {"total": 0, "counts": {}},
                    ),
                )
                return self._build_result("completed", plan=self.plan)

            # Phase: Executing
            self.state_machine.transition(State.EXECUTING)
            await self._execute_phases(phases)
            await self._replan_if_needed()

            # Phase: Building
            self.state_machine.transition(State.BUILDING)
            summary = self._build_project()
            self.state_machine.transition(State.VALIDATING)
            self._validation_result = await self._validate_with_repairs()
            if not self._validation_result.get("success", False):
                raise RuntimeError("Validation failed after 3 repair attempts")
            self.state_machine.transition(State.RUNNING)
            self._runtime_result = await self._run_with_repairs()
            if not self._runtime_result.get("success", False):
                raise RuntimeError("Runtime execution failed after 3 repair attempts")
            self._evaluation_result = await self._evaluate_project(summary)

            self.state_machine.transition(State.COMPLETED)
            self._store_run_memory()
            self.events.emit(
                EventType.RUN_COMPLETED,
                self._build_run_completed_payload("completed", summary),
            )
            return self._build_result("completed", plan=self.plan, summary=summary)

        except Exception as e:
            logger.error(f"Orchestration failed: {e}")
            self.state_machine.fail(str(e))
            self.events.emit(EventType.ERROR, {"message": str(e)})
            self._store_run_memory()
            self.events.emit(
                EventType.RUN_COMPLETED,
                self._build_run_completed_payload("failed", error=str(e)),
            )
            return self._build_result("failed", error=str(e))

    async def _plan(self, task_description: str) -> Optional[dict]:
        """Send task to Codex planner and get structured subtask breakdown."""
        self.events.emit(EventType.INFO, {"message": "[Planner] Sending task to Codex..."})

        if not self.planner.is_available():
            logger.error("Codex CLI not found in PATH")
            self.events.emit(EventType.ERROR, {"message": "codex command not found. Is it installed?"})
            return None

        self._planning_memories = self.memory_store.find_similar_runs(task_description)
        self._goal_analysis = analyze_goal(task_description, self._planning_memories)
        self._refined_prompt = self._goal_analysis.get("refined_goal", task_description)

        prompt = self.planner.build_prompt(
            self._refined_prompt,
            context={
                "goal_analysis": self._goal_analysis,
                "similar_runs": self._planning_memories,
            },
        )
        result = await self.planner.execute(prompt)

        if result.status != "success":
            logger.error(f"Planner failed: {result.error}")
            self.events.emit(EventType.ERROR, {"message": f"Planner failed: {result.error}"})
            return None

        plan = result.parsed_output
        if plan is None:
            logger.error("Could not parse planner output")
            logger.debug(f"Raw output:\n{result.raw_output[:1000]}")
            self.events.emit(
                EventType.ERROR,
                {"message": "Could not parse structured plan from Codex output"},
            )
            return None

        issues = self.planner.validate_plan(plan)
        if issues:
            logger.warning(f"Plan validation issues: {issues}")
            self.events.emit(
                EventType.WARNING,
                {"message": f"Plan has issues: {', '.join(issues)}"},
            )

        self.events.emit(
            EventType.INFO,
            {"message": f"[Planner] Received {len(plan.get('tasks', []))} subtasks"},
        )
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
            task_ids = [t.id for t in pending]
            self.events.emit(
                EventType.PHASE_STARTED,
                {
                    "phase": phase_num,
                    "total_phases": len(phases),
                    "mode": mode.lower(),
                    "task_ids": task_ids,
                    "task_count": len(pending),
                },
            )

            if parallel:
                results = await asyncio.gather(
                    *(self._execute_task_with_fallback(task) for task in pending),
                    return_exceptions=True,
                )
                for task, result in zip(pending, results):
                    if isinstance(result, Exception):
                        self.task_manager.fail_task(task.id, str(result))
                        self.events.emit(
                            EventType.TASK_FAILED,
                            {
                                "task_id": task.id,
                                "title": task.title,
                                "agent": task.agent,
                                "execution_time": task.execution_time,
                                "error": str(result),
                            },
                        )
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
            self.events.emit(
                EventType.PHASE_COMPLETED,
                {
                    "phase": phase_num,
                    "total_phases": len(phases),
                    "counts": self._phase_counts(phase_tasks),
                },
            )

    async def _execute_task_with_fallback(self, task):
        """Execute a task, falling back to an alternate agent on failure."""
        success = await self._execute_task(task)
        if success:
            fallback = get_fallback_agent(task.agent, task.type)
            if fallback:
                await self._execute_candidate(task, fallback, optimize_only=True)
                best_candidate = self._select_best_candidate(task.id)
                if task.result != best_candidate["result"]:
                    task.agent = best_candidate["agent"]
                    task.result = best_candidate["result"]
                    task.execution_time = best_candidate["execution_time"]
                    self.context.add_result(task.id, task.title, best_candidate["result"])
            return

        # Try fallback agent
        fallback = get_fallback_agent(task.agent, task.type)
        if fallback:
            logger.info(f"Falling back from {task.agent} to {fallback} for {task.id}")
            self.events.emit(
                EventType.AGENT_RETRY,
                {
                    "task_id": task.id,
                    "original_agent": task.agent,
                    "fallback_agent": fallback,
                    "reason": task.error or "Primary agent failed",
                },
            )

            # Reset task status to pending for retry
            task.status = TaskStatus.PENDING
            task.error = None
            original_agent = task.agent
            task.agent = fallback

            success = await self._execute_task(task)
            if not success:
                task.agent = original_agent  # restore for reporting

    async def _execute_candidate(self, task, agent_name: str, optimize_only: bool = False) -> Optional[dict]:
        try:
            agent = self._get_agent(agent_name)
        except ValueError:
            return None

        if not agent.is_available():
            return None

        context = self.context.build_context(task.dependencies)
        prompt = agent.build_prompt(task.description, context=context)
        result = await agent.execute(prompt)
        if result.status != "success" or not result.parsed_output:
            return None

        candidate = {
            "agent": agent_name,
            "result": result.parsed_output,
            "execution_time": result.execution_time,
            "score": self._score_task_candidate(result.parsed_output),
            "optimize_only": optimize_only,
        }
        self._task_candidates.setdefault(task.id, []).append(candidate)
        return candidate

    async def _execute_task(self, task) -> bool:
        """Execute a single task with its assigned agent. Returns True on success."""
        self.task_manager.start_task(task.id)
        self.events.emit(
            EventType.TASK_STARTED,
            {
                "task_id": task.id,
                "title": task.title,
                "agent": task.agent,
                "task_type": task.type,
            },
        )

        try:
            self._get_agent(task.agent)
        except ValueError as e:
            self.task_manager.fail_task(task.id, str(e))
            self.events.emit(
                EventType.TASK_FAILED,
                {
                    "task_id": task.id,
                    "title": task.title,
                    "agent": task.agent,
                    "execution_time": task.execution_time,
                    "error": str(e),
                },
            )
            return False

        if not self._get_agent(task.agent).is_available():
            error = f"{task.agent} CLI not found in PATH"
            self.task_manager.fail_task(task.id, error)
            self.events.emit(
                EventType.TASK_FAILED,
                {
                    "task_id": task.id,
                    "title": task.title,
                    "agent": task.agent,
                    "execution_time": task.execution_time,
                    "error": error,
                },
            )
            return False

        candidate = await self._execute_candidate(task, task.agent)
        if candidate:
            best_candidate = self._select_best_candidate(task.id)
            parsed_output = best_candidate["result"]
            self.task_manager.complete_task(
                task.id,
                result=parsed_output or {},
                execution_time=best_candidate["execution_time"],
            )
            self.context.add_result(task.id, task.title, parsed_output)

            summary = ""
            if parsed_output:
                summary = parsed_output.get("summary", "done")
            self.events.emit(
                EventType.TASK_COMPLETED,
                {
                    "task_id": task.id,
                    "title": task.title,
                    "agent": best_candidate["agent"],
                    "execution_time": best_candidate["execution_time"],
                    "summary": summary,
                },
            )
            return True

        self.task_manager.fail_task(
            task.id,
            error="Unknown error",
            execution_time=0.0,
        )
        self.events.emit(
            EventType.TASK_FAILED,
            {
                "task_id": task.id,
                "title": task.title,
                "agent": task.agent,
                "execution_time": 0.0,
                "error": "Unknown error",
            },
        )
        return False

    async def _replan_if_needed(self, max_attempts: int = 1) -> None:
        for attempt in range(1, max_attempts + 1):
            failed_or_skipped = [
                task for task in self.task_manager.tasks.values()
                if task.status in {TaskStatus.FAILED, TaskStatus.SKIPPED}
            ]
            if not failed_or_skipped:
                return

            self.state_machine.transition(State.REPLANNING)
            replanned = await self._replan_failed_work(failed_or_skipped, attempt)
            if not replanned:
                return

            self.state_machine.transition(State.EXECUTING)
            await self._execute_phases(compute_phases(list(self.task_manager.tasks.values())))

    async def _replan_failed_work(self, failed_tasks: list, attempt: int) -> bool:
        if not self.planner.is_available():
            return False

        failure_feedback = {
            "attempt": attempt,
            "failed_tasks": [
                {
                    "id": task.id,
                    "title": task.title,
                    "type": task.type,
                    "agent": task.agent,
                    "error": task.error,
                    "dependencies": task.dependencies,
                }
                for task in failed_tasks
            ],
            "prevalidation": self._prevalidation_result,
        }
        result = await self.planner.execute(
            self.planner.build_prompt(
                self._refined_prompt or self._original_prompt,
                context={
                    "goal_analysis": self._goal_analysis,
                    "similar_runs": self._planning_memories,
                    "failure_feedback": failure_feedback,
                },
            )
        )
        if result.status != "success" or not result.parsed_output:
            return False

        issues = self.planner.validate_plan(result.parsed_output)
        if issues:
            logger.warning("Replan validation issues: %s", issues)

        updated = self.task_manager.apply_replan(result.parsed_output)
        if not updated:
            return False

        self.plan = self._merge_plan(self.plan or {}, result.parsed_output)
        replan_record = {
            "attempt": attempt,
            "failed_task_ids": [task.id for task in failed_tasks],
            "updated_task_ids": [task.id for task in updated],
        }
        self._replan_history.append(replan_record)
        self._write_session_artifact("replan", replan_record, append=True)
        self._save_plan(self.plan)
        return True

    def _build_project(self) -> dict:
        """Aggregate task results and materialize the session-scoped project."""
        summary = self.task_manager.summary()
        results = self.context.get_all_results()

        total_blocks = 0
        total_lines = 0
        task_summaries = []
        for task_id, task in self.task_manager.tasks.items():
            status_icon = {
                TaskStatus.SUCCESS: "OK",
                TaskStatus.FAILED: "FAIL",
                TaskStatus.SKIPPED: "SKIP",
            }.get(task.status, "?")
            code_block_summaries = []
            if task.result and task.result.get("code_blocks"):
                blocks = task.result["code_blocks"]
                for block in blocks:
                    lang = block.get("language", "?")
                    lines = len(block.get("code", "").splitlines())
                    total_blocks += 1
                    total_lines += lines
                    code_block_summaries.append({"language": lang, "lines": lines})
            task_summaries.append(
                {
                    "task_id": task.id,
                    "title": task.title,
                    "execution_time": task.execution_time,
                    "status_icon": status_icon,
                    "code_blocks": code_block_summaries,
                }
            )

        task_results_for_builder = {}
        for task_id, task in self.task_manager.tasks.items():
            if task.result:
                task_results_for_builder[task_id] = {
                    "type": task.type,
                    "title": task.title,
                    "files": task.result.get("files", []),
                    "code_blocks": task.result.get("code_blocks", []),
                    "raw_text": task.result.get("raw_text", ""),
                }

        build_result = build_project(task_results_for_builder, self.project_dir)

        self.events.emit(EventType.PROJECT_BUILT, {
            "project_path": self.project_dir,
            "file_count": len(build_result.get("files_created", [])),
            "entrypoint": build_result.get("entrypoint"),
            "requirements": build_result.get("requirements"),
        })

        self._output_files = {
            "project_files": build_result.get("files_created", [])
        }
        self._project_build_result = build_result
        self._latest_project_dir = self.project_dir
        self._latest_task_summaries = task_summaries
        self._latest_totals = {"blocks": total_blocks, "lines": total_lines}
        self._persist_session_results(summary, results)

        return summary

    async def _validate_with_repairs(self, max_attempts: int = 3) -> dict:
        expected_files = self._project_build_result.get("files_created", [])
        for attempt in range(1, max_attempts + 1):
            result = validate_project(self.project_dir, expected_files=expected_files)
            result["attempt"] = attempt
            self._validation_result = result
            self._write_session_artifact("validation", result)
            self._persist_session_results()
            if result.get("success"):
                return result

            if attempt == max_attempts:
                return result

            error = result["errors"][0]
            self.state_machine.transition(State.REPAIRING)
            repaired = await self._request_repair(
                phase="validation",
                error_message=error.get("message", "Unknown validation error"),
                file_path=error.get("path"),
                expected_behavior="The project should validate cleanly with no syntax, import, or structural errors.",
            )
            if not repaired:
                return result
            self.state_machine.transition(State.VALIDATING)

        return self._validation_result

    async def _run_with_repairs(self, max_attempts: int = 3) -> dict:
        for attempt in range(1, max_attempts + 1):
            self._dependency_result = resolve_dependencies(self.project_dir)
            self._write_session_artifact("dependencies", self._dependency_result)
            result = execute_project(self.project_dir)
            result["attempt"] = attempt
            self._runtime_result = result
            self._write_session_artifact("runtime", result)
            self._persist_session_results()
            if result.get("success"):
                return result

            if attempt == max_attempts:
                return result

            self.state_machine.transition(State.REPAIRING)
            repaired = await self._request_repair(
                phase="runtime",
                error_message="\n".join(result.get("errors") or [result.get("logs", "Unknown runtime error")]),
                file_path=self._infer_runtime_target_file(result),
                expected_behavior="The project should start successfully and expose its intended runtime behavior.",
            )
            if not repaired:
                return result

            self.state_machine.transition(State.VALIDATING)
            validation_result = await self._validate_with_repairs(max_attempts=1)
            if not validation_result.get("success"):
                return validation_result
            self.state_machine.transition(State.RUNNING)

        return self._runtime_result

    async def _request_repair(
        self,
        phase: str,
        error_message: str,
        file_path: Optional[str] = None,
        expected_behavior: str = "The project should satisfy the original request.",
    ) -> bool:
        context = self.context.build_context([])
        error_type = classify_error(error_message, phase=phase)
        agent_name = choose_repair_agent(file_path, error_type)
        agent = self._get_agent(agent_name)
        if not agent.is_available():
            logger.warning("Repair agent %s is unavailable", agent_name)
            return False

        relative_path = file_path or self._default_repair_path(agent_name)
        prompt = build_repair_prompt(
            project_dir=self.project_dir,
            error_message=error_message,
            error_type=error_type,
            relevant_files=collect_relevant_files(
                self.project_dir,
                file_path=relative_path,
                workspace_files=context.get("workspace_files", []),
            ),
            expected_behavior=expected_behavior,
            target_file=relative_path,
        )

        result = await agent.execute(prompt)
        if result.status != "success" or not result.parsed_output:
            logger.warning("Repair attempt failed: %s", result.error)
            return False

        patch_result = build_project(
            {"repair": {"type": self._agent_type_from_name(agent_name), "files": result.parsed_output.get("files", [])}},
            self.project_dir,
        )
        repair_record = {
            "phase": phase,
            "error_type": error_type,
            "agent": agent_name,
            "file_path": relative_path,
            "error": error_message,
            "files_applied": patch_result.get("files_created", []),
            "summary": result.parsed_output.get("summary", ""),
        }
        self._repair_history.append(repair_record)
        self._write_session_artifact("repair", repair_record, append=True)
        return True

    def _default_repair_path(self, agent_name: str) -> str:
        mapping = {
            "opencode": "backend/app.py",
            "gemini": "frontend/App.jsx",
            "kilo": "tests/test_generated.py",
        }
        return mapping.get(agent_name, "backend/app.py")

    def _agent_type_from_name(self, agent_name: str) -> str:
        return {
            "opencode": "backend",
            "gemini": "frontend",
            "kilo": "testing",
        }.get(agent_name, "backend")

    def _infer_runtime_target_file(self, runtime_result: dict) -> Optional[str]:
        for known in ("backend/app.py", "frontend/App.jsx", "tests/test_generated.py"):
            if (Path(self.project_dir) / known).exists():
                return known
        return self._project_build_result.get("entrypoint") and str(Path(self._project_build_result["entrypoint"]).relative_to(self.project_dir))

    def _write_session_artifact(self, name: str, payload: dict, append: bool = False) -> None:
        path = self.session_log_dir / f"{name}.json"
        if append and path.exists():
            existing = json.loads(path.read_text())
            if not isinstance(existing, list):
                existing = [existing]
            existing.append(_safe_serialize(payload))
            path.write_text(json.dumps(existing, indent=2))
            return
        path.write_text(json.dumps(_safe_serialize(payload), indent=2))

    def _persist_session_results(
        self,
        summary: Optional[dict] = None,
        results: Optional[dict] = None,
    ) -> None:
        results_file = Path(self.memory_dir) / f"results-{self.session_id}.json"
        save_data = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "summary": summary or self.task_manager.summary(),
            "results": {k: _safe_serialize(v) for k, v in (results or self.context.get_all_results()).items()},
            "output_files": self._output_files,
            "goal_analysis": _safe_serialize(self._goal_analysis),
            "planning_memories": _safe_serialize(self._planning_memories),
            "prevalidation": _safe_serialize(self._prevalidation_result),
            "project_build": _safe_serialize(self._project_build_result),
            "validation": _safe_serialize(self._validation_result),
            "dependencies": _safe_serialize(self._dependency_result),
            "runtime": _safe_serialize(self._runtime_result),
            "repairs": _safe_serialize(self._repair_history),
            "evaluation": _safe_serialize(self._evaluation_result),
            "optimization": _safe_serialize(self._optimization_history),
            "replans": _safe_serialize(self._replan_history),
            "memory_record": _safe_serialize(self._memory_record),
        }
        results_file.write_text(json.dumps(save_data, indent=2, default=str))
        logger.info(f"Results saved to {results_file}")
        self._latest_results_file = str(results_file)

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
        confidence = self._compute_confidence()
        return {
            "session_id": self.session_id,
            "status": status,
            "state": self.state_machine.state.value,
            "state_history": [
                (s1.value, s2.value) for s1, s2 in self.state_machine.history
            ],
            "project_dir": getattr(self, "_latest_project_dir", None),
            "build_result": getattr(self, "_project_build_result", {}),
            "goal_analysis": getattr(self, "_goal_analysis", {}),
            "planning_memories": getattr(self, "_planning_memories", []),
            "prevalidation_result": getattr(self, "_prevalidation_result", {}),
            "validation_result": getattr(self, "_validation_result", {}),
            "runtime_result": getattr(self, "_runtime_result", {}),
            "evaluation_result": getattr(self, "_evaluation_result", {}),
            "confidence": confidence,
            "issues_remaining": self._collect_issues_remaining(),
            "logs": getattr(self, "_runtime_result", {}).get("logs", ""),
            **kwargs,
        }

    def _score_task_candidate(self, parsed_output: dict) -> int:
        files = parsed_output.get("files", [])
        score = len(files) * 20
        score += sum(10 for item in files if item.get("content", "").strip())
        score -= len(parsed_output.get("errors", [])) * 25
        return score

    def _select_best_candidate(self, task_id: str) -> dict:
        candidates = self._task_candidates.get(task_id, [])
        if not candidates:
            raise ValueError(f"No candidates available for task {task_id}")
        best = max(candidates, key=lambda item: item["score"])
        if len(candidates) > 1:
            self._optimization_history.append({
                "task_id": task_id,
                "selected_agent": best["agent"],
                "candidates": [
                    {"agent": item["agent"], "score": item["score"]}
                    for item in candidates
                ],
            })
        return best

    async def _evaluate_project(self, summary: dict) -> dict:
        project_summary = json.dumps({
            "project_dir": self.project_dir,
            "summary": summary,
            "goal_analysis": self._goal_analysis,
            "prevalidation": self._prevalidation_result,
            "validation": self._validation_result,
            "runtime": self._runtime_result,
            "directory_tree": self.context.build_context([]).get("directory_tree", ""),
            "architecture_signals": infer_architecture_signals(self.project_dir),
        }, indent=2)

        if self.evaluator.is_available():
            result = await self.evaluator.execute(self.evaluator.build_prompt(project_summary))
            if result.status == "success" and result.parsed_output:
                self._write_session_artifact("evaluation", result.parsed_output)
                self._persist_session_results()
                return result.parsed_output

        fallback = self._heuristic_evaluation()
        self._write_session_artifact("evaluation", fallback)
        self._persist_session_results()
        return fallback

    def _heuristic_evaluation(self) -> dict:
        score = 50
        strengths = []
        weaknesses = []
        architectural_issues = []
        suggestions = []
        if self._validation_result.get("success"):
            score += 20
            strengths.append("Validation completed successfully.")
        else:
            weaknesses.extend(error.get("message", "") for error in self._validation_result.get("errors", []))
        if self._runtime_result.get("success"):
            score += 20
            strengths.append("Runtime execution completed successfully.")
        else:
            weaknesses.extend(self._runtime_result.get("errors", []))
        if self._repair_history:
            score -= min(15, len(self._repair_history) * 5)
            suggestions.append("Reduce repair loop iterations by improving first-pass task outputs.")
        if not self._project_build_result.get("files_created"):
            score -= 20
            weaknesses.append("Project builder produced no files.")
        predictions = self._prevalidation_result.get("predictions", [])
        if predictions:
            architectural_issues.extend(item.get("message", "") for item in predictions if item.get("type") == "bad_architecture")
            suggestions.append("Address pre-validation warnings during planning to reduce downstream failures.")
        return {
            "score": max(0, min(100, score)),
            "strengths": _dedupe_strings(strengths),
            "weaknesses": _dedupe_strings(weaknesses),
            "architectural_issues": _dedupe_strings(architectural_issues),
            "suggestions": _dedupe_strings(suggestions),
        }

    def _collect_issues_remaining(self) -> list[str]:
        issues = []
        issues.extend(error.get("message", "") for error in self._validation_result.get("errors", []))
        issues.extend(self._runtime_result.get("errors", []))
        issues.extend(self._evaluation_result.get("weaknesses", []))
        issues.extend(self._evaluation_result.get("architectural_issues", []))
        issues.extend(item.get("message", "") for item in self._prevalidation_result.get("predictions", []))
        return _dedupe_strings(issues)

    def _compute_confidence(self) -> int:
        base = self._evaluation_result.get("score", 50)
        if self._validation_result.get("success"):
            base += 10
        if self._runtime_result.get("success"):
            base += 10
        base -= min(10, len(self._prevalidation_result.get("predictions", [])) * 2)
        base -= min(20, len(self._repair_history) * 5)
        return max(0, min(100, base))

    def _store_run_memory(self) -> None:
        prompt = self._original_prompt or self.plan and self.plan.get("epic", "") or ""
        if not prompt:
            return
        self._memory_record = self.memory_store.add_run(
            session_id=self.session_id,
            prompt=prompt,
            refined_goal=self._refined_prompt or prompt,
            errors=self._collect_issues_remaining(),
            fixes_applied=self._repair_history,
            final_score=int(self._evaluation_result.get("score", 0)),
        )
        self._persist_session_results()

    @staticmethod
    def _merge_plan(current_plan: dict, replanned: dict) -> dict:
        current_tasks = {task["id"]: task for task in current_plan.get("tasks", []) if task.get("id")}
        for task in replanned.get("tasks", []):
            if task.get("id"):
                current_tasks[task["id"]] = task
        merged_phases = replanned.get("phases") or current_plan.get("phases", [])
        return {
            "epic": replanned.get("epic") or current_plan.get("epic", ""),
            "tasks": list(current_tasks.values()),
            "phases": merged_phases,
        }

    def _phase_counts(self, phase_tasks: list) -> dict:
        counts = {"success": 0, "failed": 0, "skipped": 0}
        for task in phase_tasks:
            if task.status == TaskStatus.SUCCESS:
                counts["success"] += 1
            elif task.status == TaskStatus.FAILED:
                counts["failed"] += 1
            elif task.status == TaskStatus.SKIPPED:
                counts["skipped"] += 1
        return counts

    def _build_run_completed_payload(
        self,
        status: str,
        summary: Optional[dict] = None,
        error: Optional[str] = None,
    ) -> dict:
        return {
            "status": status,
            "summary": summary or {"total": 0, "counts": {}},
            "tasks": getattr(self, "_latest_task_summaries", []),
            "total_blocks": getattr(self, "_latest_totals", {}).get("blocks", 0),
            "total_lines": getattr(self, "_latest_totals", {}).get("lines", 0),
            "build_result": getattr(self, "_project_build_result", {}),
            "validation_result": getattr(self, "_validation_result", {}),
            "runtime_result": getattr(self, "_runtime_result", {}),
            "evaluation_result": getattr(self, "_evaluation_result", {}),
            "prevalidation_result": getattr(self, "_prevalidation_result", {}),
            "goal_analysis": getattr(self, "_goal_analysis", {}),
            "project_dir": getattr(self, "_latest_project_dir", None),
            "results_file": getattr(self, "_latest_results_file", None),
            "error": error,
        }


def _safe_serialize(obj):
    """Make an object JSON-serializable."""
    if isinstance(obj, dict):
        return {k: _safe_serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_safe_serialize(v) for v in obj]
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    return str(obj)


def _dedupe_strings(items: list[str]) -> list[str]:
    deduped = []
    for item in items:
        if item and item not in deduped:
            deduped.append(item)
    return deduped
