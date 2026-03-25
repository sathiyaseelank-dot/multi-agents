"""Persistence and retrieval for past orchestration runs.

Extended with architecture tracking and strategy score integration.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-zA-Z0-9_]+", text.lower()) if len(token) > 2}


@dataclass
class MemoryRecord:
    session_id: str
    prompt: str
    refined_goal: str
    errors: list[str]
    fixes_applied: list[dict]
    final_score: int
    created_at: str
    # New fields for self-learning
    architecture_decisions: dict = field(default_factory=dict)
    framework_choices: list[str] = field(default_factory=list)
    tool_choices: list[str] = field(default_factory=list)
    repair_count: int = 0
    validation_passed: bool = False
    runtime_passed: bool = False

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "prompt": self.prompt,
            "refined_goal": self.refined_goal,
            "errors": self.errors,
            "fixes_applied": self.fixes_applied,
            "final_score": self.final_score,
            "created_at": self.created_at,
            "architecture_decisions": self.architecture_decisions,
            "framework_choices": self.framework_choices,
            "tool_choices": self.tool_choices,
            "repair_count": self.repair_count,
            "validation_passed": self.validation_passed,
            "runtime_passed": self.runtime_passed,
        }


class MemoryStore:
    """Stores prior runs and retrieves similar histories for planning.
    
    Extended with architecture tracking and strategy learning.
    """

    def __init__(self, memory_dir: str = "memory"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.memory_dir / "run-memory.json"
        self.strategy_path = self.memory_dir / "strategy_scores.json"

    def add_run(
        self,
        session_id: str,
        prompt: str,
        refined_goal: str,
        errors: list[str],
        fixes_applied: list[dict],
        final_score: int,
        architecture_decisions: Optional[dict] = None,
        framework_choices: Optional[list[str]] = None,
        tool_choices: Optional[list[str]] = None,
        repair_count: int = 0,
        validation_passed: bool = False,
        runtime_passed: bool = False,
    ) -> dict:
        """Store a run record with full learning data.
        
        Args:
            session_id: Unique session identifier.
            prompt: Original user prompt.
            refined_goal: Refined goal after analysis.
            errors: List of errors encountered.
            fixes_applied: List of fixes applied.
            final_score: Final evaluation score.
            architecture_decisions: Architecture choices made.
            framework_choices: Frameworks used.
            tool_choices: Tools used.
            repair_count: Number of repairs needed.
            validation_passed: Whether validation passed.
            runtime_passed: Whether runtime execution passed.
        """
        records = self._load_all()
        record = MemoryRecord(
            session_id=session_id,
            prompt=prompt,
            refined_goal=refined_goal,
            errors=errors,
            fixes_applied=fixes_applied,
            final_score=final_score,
            created_at=datetime.now().isoformat(),
            architecture_decisions=architecture_decisions or {},
            framework_choices=framework_choices or [],
            tool_choices=tool_choices or [],
            repair_count=repair_count,
            validation_passed=validation_passed,
            runtime_passed=runtime_passed,
        )
        records.append(record.to_dict())
        self.path.write_text(json.dumps(records[-100:], indent=2))
        logger.info("Stored run memory for session %s", session_id)
        return record.to_dict()

    def add_run_from_artifacts(
        self,
        session_id: str,
        prompt: str,
        refined_goal: str,
        project_build: dict,
        validation: dict,
        runtime: dict,
        repairs: list[dict],
        evaluation: dict,
    ) -> dict:
        """Store a run record extracted from orchestrator artifacts.
        
        Args:
            session_id: Unique session identifier.
            prompt: Original user prompt.
            refined_goal: Refined goal.
            project_build: Project build result.
            validation: Validation result.
            runtime: Runtime execution result.
            repairs: Repair history.
            evaluation: Evaluation result.
            
        Returns:
            Stored record dictionary.
        """
        # Extract framework choices from project build
        framework_choices = self._extract_frameworks(project_build)
        
        # Extract architecture decisions
        architecture_decisions = self._extract_architecture(project_build)
        
        # Extract tool choices
        tool_choices = self._extract_tools(project_build)
        
        # Compute final score from evaluation
        final_score = evaluation.get("score", 50) if evaluation else 50
        
        return self.add_run(
            session_id=session_id,
            prompt=prompt,
            refined_goal=refined_goal,
            errors=validation.get("errors", []) + runtime.get("errors", []),
            fixes_applied=repairs,
            final_score=final_score,
            architecture_decisions=architecture_decisions,
            framework_choices=framework_choices,
            tool_choices=tool_choices,
            repair_count=len(repairs),
            validation_passed=validation.get("success", False),
            runtime_passed=runtime.get("success", False),
        )

    def _extract_frameworks(self, project_build: dict) -> list[str]:
        """Extract framework choices from project build result."""
        frameworks = []
        files_created = project_build.get("files_created", [])
        project_dir = project_build.get("project_dir", "")
        
        if not project_dir:
            return frameworks
        
        # Check requirements.txt
        req_path = Path(project_dir) / "requirements.txt"
        if req_path.exists():
            content = req_path.read_text().lower()
            for fw in ["flask", "fastapi", "django", "sqlalchemy", "pytest"]:
                if fw in content:
                    frameworks.append(fw)
        
        # Check package.json
        pkg_path = Path(project_dir) / "package.json"
        if pkg_path.exists():
            content = pkg_path.read_text().lower()
            for fw in ["react", "vue", "angular"]:
                if fw in content:
                    frameworks.append(fw)
        
        return frameworks

    def _extract_architecture(self, project_build: dict) -> dict:
        """Extract architecture decisions from project build result."""
        project_dir = project_build.get("project_dir", "")
        if not project_dir:
            return {}
        
        root = Path(project_dir)
        architecture = {
            "type": "unknown",
            "has_backend": (root / "backend").exists(),
            "has_frontend": (root / "frontend").exists(),
            "has_tests": (root / "tests").exists(),
        }
        
        # Detect architecture type
        if architecture["has_backend"] and architecture["has_frontend"] and architecture["has_tests"]:
            architecture["type"] = "layered"
        elif architecture["has_backend"]:
            architecture["type"] = "backend_only"
        elif architecture["has_frontend"]:
            architecture["type"] = "frontend_only"
        
        return architecture

    def _extract_tools(self, project_build: dict) -> list[str]:
        """Extract tool choices from project build result."""
        tools = []
        files_created = project_build.get("files_created", [])
        
        if any("test" in f.lower() for f in files_created):
            tools.append("testing")
        if any("requirements.txt" in f for f in files_created):
            tools.append("pip")
        if any("package.json" in f for f in files_created):
            tools.append("npm")
        if any(".env" in f for f in files_created):
            tools.append("dotenv")
        
        return tools

    def find_similar_runs(self, prompt: str, limit: int = 3) -> list[dict]:
        """Find similar historical runs.
        
        Args:
            prompt: Current task prompt.
            limit: Maximum results to return.
            
        Returns:
            List of similar run records.
        """
        prompt_tokens = _tokenize(prompt)
        if not prompt_tokens:
            return []

        scored = []
        for record in self._load_all():
            text = " ".join([
                record.get("prompt", ""),
                record.get("refined_goal", ""),
                " ".join(record.get("framework_choices", [])),
            ])
            overlap = prompt_tokens & _tokenize(text)
            if not overlap:
                continue
            # Boost score for successful runs
            success_bonus = 0
            if record.get("validation_passed") and record.get("runtime_passed"):
                success_bonus = 20
            score = len(overlap) + int(record.get("final_score", 0) / 25) + success_bonus
            scored.append((score, record))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [record for _, record in scored[:limit]]

    def get_successful_patterns(self, framework: Optional[str] = None) -> list[dict]:
        """Get patterns from successful runs, optionally filtered by framework.
        
        Args:
            framework: Optional framework to filter by.
            
        Returns:
            List of successful run patterns.
        """
        patterns = []
        for record in self._load_all():
            if not (record.get("validation_passed") and record.get("runtime_passed")):
                continue
            if framework and framework not in record.get("framework_choices", []):
                continue
            patterns.append({
                "session_id": record.get("session_id"),
                "prompt": record.get("prompt"),
                "refined_goal": record.get("refined_goal"),
                "framework_choices": record.get("framework_choices", []),
                "architecture_decisions": record.get("architecture_decisions", {}),
                "final_score": record.get("final_score", 0),
                "repair_count": record.get("repair_count", 0),
            })
        return patterns

    def get_failure_patterns(self, error_type: Optional[str] = None) -> list[dict]:
        """Get patterns from failed runs.
        
        Args:
            error_type: Optional error type to filter by.
            
        Returns:
            List of failed run patterns.
        """
        patterns = []
        for record in self._load_all():
            if record.get("validation_passed") and record.get("runtime_passed"):
                continue
            
            errors = record.get("errors", [])
            if error_type:
                if not any(error_type.lower() in e.lower() for e in errors):
                    continue
            
            patterns.append({
                "session_id": record.get("session_id"),
                "prompt": record.get("prompt"),
                "errors": errors,
                "fixes_applied": record.get("fixes_applied", []),
                "repair_count": record.get("repair_count", 0),
            })
        return patterns

    def get_framework_success_rate(self, framework: str) -> dict:
        """Get success rate for a specific framework.
        
        Args:
            framework: Framework name.
            
        Returns:
            Success rate statistics.
        """
        total = 0
        successes = 0
        scores = []
        
        for record in self._load_all():
            if framework in record.get("framework_choices", []):
                total += 1
                if record.get("validation_passed") and record.get("runtime_passed"):
                    successes += 1
                scores.append(record.get("final_score", 50))
        
        if total == 0:
            return {"total": 0, "successes": 0, "success_rate": 0, "avg_score": 0}
        
        return {
            "total": total,
            "successes": successes,
            "success_rate": successes / total,
            "avg_score": sum(scores) / len(scores) if scores else 0,
        }

    def _load_all(self) -> list[dict]:
        """Load all run records from disk."""
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text())
        except json.JSONDecodeError:
            logger.warning("Run memory is corrupt, ignoring %s", self.path)
            return []
        return data if isinstance(data, list) else []

    def get_learning_data_for_strategy(self, strategy_key: str) -> dict:
        """Get learning data for strategy scoring.
        
        Args:
            strategy_key: Strategy identifier (e.g., "flask", "layered").
            
        Returns:
            Dictionary with successes, failures, and scores.
        """
        successes = 0
        failures = 0
        scores = []
        
        for record in self._load_all():
            # Check if strategy is in framework choices
            framework_choices = record.get("framework_choices", [])
            architecture = record.get("architecture_decisions", {}).get("type", "")
            
            if strategy_key not in framework_choices and strategy_key != architecture:
                continue
            
            if record.get("validation_passed") and record.get("runtime_passed"):
                successes += 1
            else:
                failures += 1
            
            scores.append(record.get("final_score", 50))
        
        return {
            "successes": successes,
            "failures": failures,
            "scores": scores,
            "total": successes + failures,
        }
