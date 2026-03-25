"""Main orchestration engine — coordinates planning and execution.

Extended with self-learning capabilities for continuous improvement.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from time import monotonic
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
from .goal_analyzer import analyze_goal, analyze_goal_with_learning
from .memory_store import MemoryStore
from .pre_validation import infer_architecture_signals, predict_plan_risks, predict_plan_risks_with_learning
from .validation_engine import validate_project
from .dependency_resolver import resolve_dependencies
from .runtime_executor import execute_project
from .config_loader import load_agent_configs
from parsing.validator import validate_review_feedback
from .pattern_learner import PatternLearner
from .learning_injector import LearningInjector, build_learning_context, augment_planner_prompt
from .strategy_scorer import StrategyScorer
from .self_improver import SelfImprover
from .meta_controller import MetaController, MetaControllerContext
from agents.planner import PlanReviewerAgent, PlannerAgent
from agents.backend import BackendAgent
from agents.frontend import FrontendAgent
from agents.tester import TesterAgent
from agents.evaluator import EvaluatorAgent
from agents.base_agent import AgentConfig
from __version__ import VERSION_DESCRIPTION

logger = logging.getLogger(__name__)

MAX_PLAN_REVIEW_ITERATIONS = 2
STRONG_REJECTION_CONFIDENCE = 0.8
REVISION_ALLOWED_CONFIDENCE = 0.6

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
        enable_learning: bool = True,
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
        self._planning_trace: dict = {}
        self._final_review: dict = {}
        self._review_iterations: int = 0
        self._goal_analysis: dict = {}
        self._planning_memories: list[dict] = []
        self._prevalidation_result: dict = {}
        self._memory_record: dict = {}
        self._original_prompt: str = ""
        self._refined_prompt: str = ""
        self.enable_learning = enable_learning
        self.summary_only = summary_only
        self.events = events or EventEmitter(
            session_id=self.session_id,
            summary_only=summary_only,
        )
        self._agent_configs = load_agent_configs()
        
        # Initialize learning components
        self.memory_store = MemoryStore(memory_dir=memory_dir)
        self.pattern_learner = PatternLearner(memory_dir=memory_dir) if enable_learning else None
        self.strategy_scorer = StrategyScorer(memory_dir=memory_dir) if enable_learning else None
        self.learning_injector = LearningInjector(self.pattern_learner) if self.pattern_learner else None
        self.self_improver = SelfImprover(
            self.pattern_learner,
            self.strategy_scorer,
            memory_dir=memory_dir,
        ) if enable_learning and self.pattern_learner else None
        
        # Initialize meta-controller for governing learning decisions
        self.meta_controller = MetaController(memory_dir=memory_dir) if enable_learning else None
        self.meta_context = MetaControllerContext(self.meta_controller) if self.meta_controller else None
        self._meta_decisions: list[dict] = []

        self.planner = self._build_planner()
        self.reviewer = self._build_reviewer()
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

    def _build_reviewer(self) -> PlanReviewerAgent:
        """Build the reviewer from loaded config."""
        cfg = self._agent_configs.get("codex_reviewer") or self._agent_configs.get("codex")
        if cfg:
            return PlanReviewerAgent(config=AgentConfig(
                name=cfg["name"],
                role=cfg.get("role", "reviewer"),
                command=cfg["command"],
                subcommand=cfg.get("subcommand"),
                args=cfg.get("args", []),
                timeout_seconds=cfg.get("timeout_seconds", 90),
                retry_count=cfg.get("retry_count", 2),
                retry_backoff_seconds=cfg.get("retry_backoff_seconds", 2),
                env_vars=cfg.get("env_vars", {}),
            ))
        return PlanReviewerAgent()

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
        self._planning_trace = saved.get("planning_trace", {})
        self._review_iterations = saved.get("review_iterations", 0)
        self._final_review = saved.get("final_review", {})

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
        """Send task to Codex planner and get structured subtask breakdown.
        
        Extended with learning injection for improved planning.
        """
        self.events.emit(EventType.INFO, {"message": "[Planner] Sending task to Codex..."})

        if not self.planner.is_available():
            logger.error("Codex CLI not found in PATH")
            self.events.emit(EventType.ERROR, {"message": "codex command not found. Is it installed?"})
            return None
        if not self.reviewer.is_available():
            logger.error("Reviewer agent not found in PATH")
            self.events.emit(EventType.ERROR, {"message": "reviewer command not found. Is it installed?"})
            return None

        # PHASE 1: Retrieve similar runs from memory
        self._planning_memories = self.memory_store.find_similar_runs(task_description)

        # PHASE 2: Get learning context if enabled
        learning_context = {}
        if self.enable_learning and self.learning_injector:
            learning_context = self.learning_injector.prepare_for_planning(task_description)

            # Emit learning recommendations
            if learning_context.get("recommended_frameworks"):
                self.events.emit(
                    EventType.INFO,
                    {"message": f"Learning recommends frameworks: {', '.join(learning_context['recommended_frameworks'][:3])}"}
                )
            if learning_context.get("failure_warnings"):
                for warning in learning_context["failure_warnings"][:2]:
                    self.events.emit(
                        EventType.WARNING,
                        {"message": f"Learning warning: {warning.get('warning', '')}"}
                    )

        # PHASE 2.5: Meta-controller strategy selection
        meta_context = {}
        if self.enable_learning and self.meta_controller and self.strategy_scorer:
            # Get strategy rankings
            strategy_rankings = {
                "frameworks": self.strategy_scorer.get_ranking_with_confidence("frameworks"),
                "architectures": self.strategy_scorer.get_ranking_with_confidence("architectures"),
                "tools": self.strategy_scorer.get_ranking_with_confidence("tools"),
            }
            
            # Get meta-controller decisions
            meta_context = self.meta_context.build_planning_context(strategy_rankings)
            self._meta_decisions = meta_context.get("meta_decisions", [])
            
            # Emit meta-controller guidance
            if meta_context.get("selected_strategies"):
                strategies_str = ", ".join(
                    f"{k}:{v}" for k, v in meta_context["selected_strategies"].items()
                )
                self.events.emit(
                    EventType.INFO,
                    {"message": f"Meta-controller selected: {strategies_str}"}
                )
            if meta_context.get("exploration_mode"):
                self.events.emit(
                    EventType.INFO,
                    {"message": "System in EXPLORATION mode - trying alternative strategies"}
                )

        # PHASE 3: Analyze goal with learning integration
        if self.enable_learning and self.pattern_learner and self.strategy_scorer:
            self._goal_analysis = analyze_goal_with_learning(
                task_description,
                self.pattern_learner,
                self.strategy_scorer,
                similar_runs=self._planning_memories,
            )
        else:
            self._goal_analysis = analyze_goal(
                task_description,
                similar_runs=self._planning_memories,
            )
        
        self._refined_prompt = self._goal_analysis.get("refined_goal", task_description)
        planning_context = {
            "goal_analysis": self._goal_analysis,
            "similar_runs": self._planning_memories,
        }
        if self.enable_learning and learning_context:
            planning_context["learning_context"] = learning_context
        if self.enable_learning and meta_context:
            planning_context["meta_context"] = meta_context

        self._planning_trace = {
            "initial_plan": None,
            "review_1": None,
            "revised_plan": None,
            "review_2": None,
        }
        self._final_review = {}
        self._review_iterations = 0

        try:
            async with asyncio.timeout(self._planning_time_budget_seconds()):
                initial_result = await self._generate_plan_candidate(
                    self._refined_prompt,
                    planning_context,
                )
                if initial_result is None:
                    return None

                initial_plan = initial_result.parsed_output
                self._planning_trace["initial_plan"] = initial_plan

                review_1 = await self._review_candidate_plan(
                    self._refined_prompt,
                    initial_plan,
                    planning_context,
                    iteration=1,
                )
                if review_1 is None:
                    return None

                self._planning_trace["review_1"] = review_1
                self._final_review = review_1
                self._review_iterations = 1

                if review_1["approval"]:
                    self.events.emit(
                        EventType.PLAN_APPROVED,
                        {"review_iterations": self._review_iterations},
                    )
                    self._write_session_artifact("planning_trace", self._planning_trace)
                    return initial_plan

                if review_1["confidence"] > STRONG_REJECTION_CONFIDENCE:
                    self.events.emit(
                        EventType.PLAN_REJECTED,
                        {"review_iterations": self._review_iterations},
                    )
                    self._write_session_artifact("planning_trace", self._planning_trace)
                    return None

                revision_result = await self._revise_plan_candidate(
                    self._refined_prompt,
                    initial_plan,
                    review_1,
                    planning_context,
                )
                if revision_result is None:
                    return None

                revised_plan = revision_result.parsed_output
                self._planning_trace["revised_plan"] = revised_plan
                self.events.emit(EventType.PLAN_REVISED, {"iteration": 1})

                review_2 = await self._review_candidate_plan(
                    self._refined_prompt,
                    revised_plan,
                    planning_context,
                    iteration=2,
                )
                if review_2 is None:
                    return None

                self._planning_trace["review_2"] = review_2
                self._final_review = review_2
                self._review_iterations = 2
                self._write_session_artifact("planning_trace", self._planning_trace)

                if review_2["approval"]:
                    self.events.emit(
                        EventType.PLAN_APPROVED,
                        {"review_iterations": self._review_iterations},
                    )
                    return revised_plan

                self.events.emit(
                    EventType.PLAN_REJECTED,
                    {"review_iterations": self._review_iterations},
                )
                return None
        except TimeoutError:
            logger.error("Planning debate timed out")
            self.events.emit(EventType.ERROR, {"message": "Planning debate exceeded time budget"})
            return None

    def _planning_time_budget_seconds(self) -> int:
        """Budget planner + reviewer debate with a bounded upper limit."""
        planner_timeout = getattr(self.planner.config, "timeout_seconds", 120)
        reviewer_timeout = getattr(self.reviewer.config, "timeout_seconds", 90)
        return max(planner_timeout + reviewer_timeout + planner_timeout + reviewer_timeout, 60)

    async def _generate_plan_candidate(self, task_description: str, planning_context: dict):
        base_context = {
            "goal_analysis": planning_context.get("goal_analysis", {}),
            "similar_runs": planning_context.get("similar_runs", []),
        }
        prompt = self.planner.build_prompt(task_description, context=base_context)
        if self.enable_learning and planning_context.get("learning_context"):
            prompt = augment_planner_prompt(prompt, planning_context["learning_context"])
        result = await self.planner.execute(prompt)
        if result.status != "success":
            logger.error("Planner failed: %s", result.error)
            self.events.emit(EventType.ERROR, {"message": f"Planner failed: {result.error}"})
            return None
        if not result.parsed_output:
            logger.error("Could not parse structured plan from planner output")
            self.events.emit(
                EventType.ERROR,
                {"message": "Could not parse structured plan from Codex output"},
            )
            return None
        issues = self.planner.validate_plan(result.parsed_output)
        if issues:
            logger.warning("Plan validation issues: %s", issues)
            self.events.emit(
                EventType.WARNING,
                {"message": f"Plan has issues: {', '.join(issues)}"},
            )
        self.events.emit(
            EventType.INFO,
            {"message": f"[Planner] Received {len(result.parsed_output.get('tasks', []))} subtasks"},
        )
        return result

    async def _revise_plan_candidate(
        self,
        task_description: str,
        prior_plan: dict,
        review_feedback: dict,
        planning_context: dict,
    ):
        revision_context = {
            "goal_analysis": planning_context.get("goal_analysis", {}),
            "similar_runs": planning_context.get("similar_runs", []),
            "learning_context": planning_context.get("learning_context", {}),
        }
        prompt = self.planner.build_revision_prompt(
            task_description,
            prior_plan,
            review_feedback,
            context=revision_context,
        )
        result = await self.planner.execute(prompt)
        if result.status != "success":
            logger.error("Planner revision failed: %s", result.error)
            self.events.emit(EventType.ERROR, {"message": f"Planner revision failed: {result.error}"})
            return None
        if not result.parsed_output:
            self.events.emit(
                EventType.ERROR,
                {"message": "Could not parse structured revised plan from Codex output"},
            )
            return None
        issues = self.planner.validate_plan(result.parsed_output)
        if issues:
            logger.warning("Revised plan validation issues: %s", issues)
            self.events.emit(
                EventType.WARNING,
                {"message": f"Revised plan has issues: {', '.join(issues)}"},
            )
        return result

    async def _review_candidate_plan(
        self,
        task_description: str,
        candidate_plan: dict,
        planning_context: dict,
        iteration: int,
    ) -> Optional[dict]:
        self.events.emit(EventType.PLAN_REVIEW_STARTED, {"iteration": iteration})
        review_context = {
            "goal_analysis": planning_context.get("goal_analysis", {}),
            "similar_runs": planning_context.get("similar_runs", []),
            "learning_context": planning_context.get("learning_context", {}),
            "critical_issue_policy": {
                "critical_issues": [
                    "missing core task",
                    "broken dependencies",
                    "invalid architecture",
                    "execution impossible",
                ],
                "approve_if_no_critical_issues": True,
            },
        }
        started = monotonic()
        result = await self.reviewer.review_plan(
            task_description,
            candidate_plan,
            context=review_context,
        )
        elapsed = monotonic() - started
        if result.status != "success":
            logger.error("Reviewer failed: %s", result.error)
            self.events.emit(EventType.ERROR, {"message": f"Reviewer failed: {result.error}"})
            return None
        if result.parsed_output is None:
            self.events.emit(EventType.ERROR, {"message": "Reviewer returned malformed output"})
            return None

        issues = validate_review_feedback(result.parsed_output)
        if issues:
            logger.error("Reviewer output invalid: %s", issues)
            self.events.emit(
                EventType.ERROR,
                {"message": f"Reviewer output invalid: {', '.join(issues)}"},
            )
            return None

        review = dict(result.parsed_output)
        review["iteration"] = iteration
        review["execution_time"] = round(elapsed, 3)
        self.events.emit(
            EventType.PLAN_REVIEW_COMPLETED,
            {
                "iteration": iteration,
                "approval": review["approval"],
                "confidence": review["confidence"],
            },
        )
        return review

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
            "planning_trace": _safe_serialize(self._planning_trace),
            "review_iterations": self._review_iterations,
            "final_review": _safe_serialize(self._final_review),
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
            "planning_trace": _safe_serialize(self._planning_trace),
            "review_iterations": self._review_iterations,
            "final_review": _safe_serialize(self._final_review),
        }
        plan_file.write_text(json.dumps(data, indent=2))
        logger.info(f"Plan saved to {plan_file}")

    def _build_result(self, status: str, **kwargs) -> dict:
        confidence = self._compute_confidence()
        
        # Get meta-controller summary if available
        meta_summary = {}
        if self.enable_learning and self.meta_controller:
            meta_summary = self.meta_controller.get_recommendations()
        
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
            "planning_trace": getattr(self, "_planning_trace", {}),
            "review_iterations": getattr(self, "_review_iterations", 0),
            "final_review": getattr(self, "_final_review", {}),
            "prevalidation_result": getattr(self, "_prevalidation_result", {}),
            "validation_result": getattr(self, "_validation_result", {}),
            "runtime_result": getattr(self, "_runtime_result", {}),
            "evaluation_result": getattr(self, "_evaluation_result", {}),
            "meta_decisions": getattr(self, "_meta_decisions", []),
            "meta_summary": meta_summary,
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
        """Store run data in memory for future learning.
        
        Extended to store full learning artifacts and update strategy scores.
        """
        prompt = self._original_prompt or self.plan and self.plan.get("epic", "") or ""
        if not prompt:
            return
        
        # Store using the new artifact-based method
        self._memory_record = self.memory_store.add_run_from_artifacts(
            session_id=self.session_id,
            prompt=prompt,
            refined_goal=self._refined_prompt or prompt,
            project_build=getattr(self, "_project_build_result", {}),
            validation=getattr(self, "_validation_result", {}),
            runtime=getattr(self, "_runtime_result", {}),
            repairs=getattr(self, "_repair_history", []),
            evaluation=getattr(self, "_evaluation_result", {}),
        )
        
        # PHASE: Update strategy scores from this run
        if self.enable_learning and self.strategy_scorer:
            self._update_strategy_scores()
        
        # PHASE: Record patterns in pattern learner
        if self.enable_learning and self.pattern_learner:
            self._record_learning_patterns()
        
        self._persist_session_results()
        logger.info("Stored run memory and updated learning for session %s", self.session_id)
    
    def _update_strategy_scores(self):
        """Update strategy scores based on run outcome."""
        success = (
            self._validation_result.get("success", False) and
            self._runtime_result.get("success", False)
        )
        score = self._evaluation_result.get("score", 50) if self._evaluation_result else 50
        repair_count = len(getattr(self, "_repair_history", []))

        # Extract frameworks from project build
        build_result = getattr(self, "_project_build_result", {})
        framework_choices = self.memory_store._extract_frameworks(build_result)
        architecture = self.memory_store._extract_architecture(build_result)

        # Update framework scores with repair tracking
        for framework in framework_choices:
            self.strategy_scorer.record_outcome_with_repairs(
                strategy_key=framework,
                category="frameworks",
                success=success,
                score=score,
                repair_count=repair_count,
            )

        # Update architecture scores
        arch_type = architecture.get("type", "")
        if arch_type and arch_type != "unknown":
            self.strategy_scorer.record_outcome_with_repairs(
                strategy_key=arch_type,
                category="architectures",
                success=success,
                score=score,
                repair_count=repair_count,
            )

        # Update tool scores
        tool_choices = self.memory_store._extract_tools(build_result)
        for tool in tool_choices:
            self.strategy_scorer.record_outcome_with_repairs(
                strategy_key=tool,
                category="tools",
                success=success,
                score=score,
                repair_count=repair_count,
            )

        # Record meta-controller outcomes
        if self.enable_learning and self.meta_controller:
            self._record_meta_outcomes(success, score, repair_count)
    
    def _record_meta_outcomes(self, success: bool, score: float, repair_count: int):
        """Record outcomes for meta-controller decisions.
        
        Args:
            success: Whether the run was successful.
            score: Evaluation score.
            repair_count: Number of repairs needed.
        """
        for decision_data in self._meta_decisions:
            # Create a StrategyDecision from the stored data
            from .meta_controller import StrategyDecision
            decision = StrategyDecision(
                category=decision_data.get("category", "unknown"),
                strategy=decision_data.get("strategy", "unknown"),
                mode=decision_data.get("mode", "unknown"),
                score=decision_data.get("score", 0),
                confidence=decision_data.get("confidence", 0),
                exploration_rate=decision_data.get("exploration_rate", 0),
            )
            
            # Record outcome
            self.meta_controller.record_outcome(
                decision=decision,
                success=success,
                score=score,
                repair_count=repair_count,
            )
        
        logger.info(
            "Recorded %d meta-controller outcomes: success=%s, score=%.1f, repairs=%d",
            len(self._meta_decisions), success, score, repair_count
        )
    
    def _record_learning_patterns(self):
        """Record patterns from this run for future learning."""
        run_record = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "project_build": getattr(self, "_project_build_result", {}),
            "validation": getattr(self, "_validation_result", {}),
            "runtime": getattr(self, "_runtime_result", {}),
            "repairs": getattr(self, "_repair_history", []),
            "evaluation": getattr(self, "_evaluation_result", {}),
        }
        self.pattern_learner.record_run(run_record)

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
            "planning_trace": getattr(self, "_planning_trace", {}),
            "review_iterations": getattr(self, "_review_iterations", 0),
            "final_review": getattr(self, "_final_review", {}),
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
