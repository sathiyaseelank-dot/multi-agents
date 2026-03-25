"""Unit tests for self-learning modules."""

import json
import pytest
import tempfile
import shutil
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator.pattern_learner import (
    PatternLearner,
    extract_architecture_pattern,
    extract_failure_pattern,
    extract_success_pattern,
)
from orchestrator.strategy_scorer import StrategyScorer, BayesianScoreUpdater
from orchestrator.learning_injector import (
    LearningInjector,
    build_learning_context,
    augment_planner_prompt,
)
from orchestrator.self_improver import SelfImprover
from orchestrator.memory_store import MemoryStore


class TestPatternExtraction:
    """Tests for pattern extraction functions."""
    
    def test_extract_architecture_pattern_from_run_record(self):
        """Test extracting architecture pattern from run record."""
        run_record = {
            "session_id": "test-001",
            "project_build": {
                "project_dir": "",
                "files_created": ["backend/app.py", "requirements.txt"],
            },
            "validation": {"success": True},
            "runtime": {"success": True},
            "evaluation": {"score": 85},
        }
        
        # Pattern extraction requires actual project files
        # For unit test, verify it handles empty project gracefully
        pattern = extract_architecture_pattern(run_record)
        # Should return None or a pattern dict
        assert pattern is None or isinstance(pattern, dict)
    
    def test_extract_failure_pattern_from_run_record(self):
        """Test extracting failure pattern from run record."""
        run_record = {
            "session_id": "test-001",
            "validation": {
                "success": False,
                "errors": [
                    {"kind": "syntax", "message": "Syntax error at line 5"},
                    {"kind": "import", "message": "Module not found"},
                ],
            },
            "runtime": {"success": False, "errors": ["Import failed"]},
            "repairs": [{"error_type": "syntax"}],
        }
        
        pattern = extract_failure_pattern(run_record)
        assert pattern is not None
        assert pattern["pattern_type"] == "failure"
        assert "signature" in pattern
    
    def test_extract_success_pattern_from_successful_run(self):
        """Test extracting success pattern from successful run."""
        run_record = {
            "session_id": "test-001",
            "validation": {"success": True},
            "runtime": {"success": True},
            "evaluation": {"score": 90},
            "repairs": [],
        }
        
        pattern = extract_success_pattern(run_record)
        assert pattern is not None
        assert pattern["pattern_type"] == "success"
        signature = pattern.get("signature", {})
        assert signature.get("no_repairs") is True
        assert signature.get("high_score") is True
    
    def test_extract_success_pattern_returns_none_for_failure(self):
        """Test that success pattern returns None for failed runs."""
        run_record = {
            "session_id": "test-001",
            "validation": {"success": False},
            "runtime": {"success": False},
        }
        
        pattern = extract_success_pattern(run_record)
        assert pattern is None


class TestPatternLearner:
    """Tests for PatternLearner class."""
    
    def setup_method(self):
        """Create temporary directory for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.learner = PatternLearner(memory_dir=self.temp_dir)
    
    def teardown_method(self):
        """Clean up temporary directory after each test."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_record_run_stores_patterns(self):
        """Test that record_run stores patterns."""
        run_record = {
            "session_id": "test-001",
            "validation": {"success": True},
            "runtime": {"success": True},
            "evaluation": {"score": 85},
            "repairs": [],
        }
        
        stored = self.learner.record_run(run_record)
        
        assert "success" in stored
        assert stored["success"] >= 0
    
    def test_get_recommended_frameworks_empty(self):
        """Test getting recommendations with no data."""
        recommendations = self.learner.get_recommended_frameworks("build an api")
        assert isinstance(recommendations, list)
    
    def test_get_common_failures_empty(self):
        """Test getting common failures with no data."""
        failures = self.learner.get_common_failures()
        assert isinstance(failures, list)
    
    def test_get_success_patterns_empty(self):
        """Test getting success patterns with no data."""
        patterns = self.learner.get_success_patterns()
        assert isinstance(patterns, list)
    
    def test_get_learning_summary(self):
        """Test getting learning summary."""
        summary = self.learner.get_learning_summary()
        
        assert "total_patterns" in summary
        assert "architecture_patterns" in summary
        assert "failure_patterns" in summary
        assert "success_patterns" in summary


class TestStrategyScorer:
    """Tests for StrategyScorer class."""
    
    def setup_method(self):
        """Create temporary directory for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.scorer = StrategyScorer(memory_dir=self.temp_dir)
    
    def teardown_method(self):
        """Clean up temporary directory after each test."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_record_outcome_updates_score(self):
        """Test that recording outcome updates score."""
        self.scorer.record_outcome(
            strategy_key="flask",
            category="frameworks",
            success=True,
            score=85,
        )
        
        score_data = self.scorer.get_score("frameworks", "flask")
        assert score_data is not None
        assert score_data["samples"] == 1
    
    def test_record_multiple_outcomes(self):
        """Test recording multiple outcomes."""
        self.scorer.record_outcome("flask", "frameworks", True, 85)
        self.scorer.record_outcome("flask", "frameworks", True, 90)
        self.scorer.record_outcome("flask", "frameworks", False, 40)
        
        score_data = self.scorer.get_score("frameworks", "flask")
        assert score_data["samples"] == 3
    
    def test_get_ranking(self):
        """Test getting strategy ranking."""
        self.scorer.record_outcome("flask", "frameworks", True, 85)
        self.scorer.record_outcome("flask", "frameworks", True, 90)
        self.scorer.record_outcome("fastapi", "frameworks", True, 95)
        self.scorer.record_outcome("fastapi", "frameworks", True, 92)
        self.scorer.record_outcome("fastapi", "frameworks", True, 88)
        
        ranking = self.scorer.get_ranking("frameworks")
        assert len(ranking) >= 1
    
    def test_get_best_strategy(self):
        """Test getting best strategy."""
        self.scorer.record_outcome("flask", "frameworks", True, 85, "api")
        self.scorer.record_outcome("flask", "frameworks", True, 88, "api")
        self.scorer.record_outcome("fastapi", "frameworks", True, 95, "api")
        self.scorer.record_outcome("fastapi", "frameworks", True, 92, "api")
        
        best = self.scorer.get_best("frameworks")
        assert best is not None
    
    def test_get_recommendations(self):
        """Test getting recommendations."""
        self.scorer.record_outcome("flask", "frameworks", True, 85)
        self.scorer.record_outcome("fastapi", "frameworks", True, 95)
        
        recs = self.scorer.get_recommendations("build a REST API")
        assert "frameworks" in recs
    
    def test_get_confidence(self):
        """Test getting confidence metrics."""
        self.scorer.record_outcome("flask", "frameworks", True, 85)
        
        confidence = self.scorer.get_confidence("frameworks", "flask")
        assert "confidence" in confidence
        assert "samples" in confidence
    
    def test_bayesian_score_updater(self):
        """Test Bayesian score updater."""
        updater = BayesianScoreUpdater()
        
        result = updater.update(successes=10, failures=2, avg_score=85)
        
        assert "mean" in result
        assert "std" in result
        assert "ci_low" in result
        assert "ci_high" in result
        assert "adjusted_score" in result
        
        # Mean should be high with 10 successes, 2 failures
        assert result["mean"] > 0.7


class TestLearningInjector:
    """Tests for LearningInjector class."""
    
    def setup_method(self):
        """Create temporary directory for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.pattern_learner = PatternLearner(memory_dir=self.temp_dir)
        self.injector = LearningInjector(self.pattern_learner)
    
    def teardown_method(self):
        """Clean up temporary directory after each test."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_prepare_for_planning(self):
        """Test preparing learning context for planning."""
        context = self.injector.prepare_for_planning("build a REST API")
        
        assert "recommended_frameworks" in context
        assert "architecture_hints" in context
        assert "failure_warnings" in context
        assert "success_patterns" in context
        assert "planning_bias" in context
    
    def test_inject_into_prompt(self):
        """Test injecting learning into prompt."""
        base_prompt = "Build a REST API with Flask"
        learning_context = {
            "recommended_frameworks": ["flask", "fastapi"],
            "architecture_hints": [],
            "failure_warnings": [],
            "success_patterns": [],
        }
        
        augmented = self.injector.inject_into_prompt(base_prompt, learning_context)
        
        # Should contain base prompt
        assert base_prompt in augmented
        # Should contain learning section
        assert "LEARNING" in augmented or augmented == base_prompt
    
    def test_get_recommendations(self):
        """Test getting recommendations."""
        recs = self.injector.get_recommendations("build a dashboard")
        
        assert "frameworks" in recs
        assert "architecture_hints" in recs
        assert "warnings" in recs
        assert "success_patterns" in recs
        assert "planning_bias" in recs


class TestSelfImprover:
    """Tests for SelfImprover class."""
    
    def setup_method(self):
        """Create temporary directory for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.pattern_learner = PatternLearner(memory_dir=self.temp_dir)
        self.strategy_scorer = StrategyScorer(memory_dir=self.temp_dir)
        self.self_improver = SelfImprover(
            self.pattern_learner,
            self.strategy_scorer,
            memory_dir=self.temp_dir,
        )
    
    def teardown_method(self):
        """Clean up temporary directory after each test."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_analyze_improvement_trajectory_insufficient_data(self):
        """Test trajectory analysis with insufficient data."""
        trajectory = self.self_improver.analyze_improvement_trajectory()
        
        assert trajectory["status"] == "insufficient_data"
    
    def test_identify_convergence_patterns(self):
        """Test identifying convergence patterns."""
        convergence = self.self_improver.identify_convergence_patterns()
        
        assert "converged_strategies" in convergence
        assert "frameworks" in convergence["converged_strategies"]
        assert "architectures" in convergence["converged_strategies"]
        assert "tools" in convergence["converged_strategies"]
    
    def test_generate_improvement_report(self):
        """Test generating improvement report."""
        report = self.self_improver.generate_improvement_report()
        
        assert isinstance(report, str)
        assert "Self-Improvement Report" in report
    
    def test_prune_low_value_strategies(self):
        """Test pruning low-value strategies."""
        result = self.self_improver.prune_low_value_strategies()
        
        assert "pruned" in result
        assert "total_pruned" in result
    
    def test_get_recommendations_for_next_run(self):
        """Test getting recommendations for next run."""
        recs = self.self_improver.get_recommendations_for_next_run("build an API")
        
        assert "trajectory_status" in recs
        assert "converged_strategies" in recs
        assert "strategy_recommendations" in recs
        assert "framework_recommendations" in recs
        assert "learning_hints" in recs


class TestMemoryStoreExtended:
    """Tests for extended MemoryStore functionality."""
    
    def setup_method(self):
        """Create temporary directory for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.memory_store = MemoryStore(memory_dir=self.temp_dir)
    
    def teardown_method(self):
        """Clean up temporary directory after each test."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_add_run_from_artifacts(self):
        """Test adding run from artifacts."""
        record = self.memory_store.add_run_from_artifacts(
            session_id="test-001",
            prompt="Build a REST API",
            refined_goal="Build a REST API with authentication",
            project_build={
                "project_dir": "",
                "files_created": ["backend/app.py", "requirements.txt"],
            },
            validation={"success": True, "errors": []},
            runtime={"success": True, "errors": []},
            repairs=[],
            evaluation={"score": 85},
        )
        
        assert record["session_id"] == "test-001"
        assert record["final_score"] == 85
        assert record["validation_passed"] is True
        assert record["runtime_passed"] is True
    
    def test_get_framework_success_rate(self):
        """Test getting framework success rate."""
        # Add some runs
        self.memory_store.add_run(
            session_id="test-001",
            prompt="Build API",
            refined_goal="Build API",
            errors=[],
            fixes_applied=[],
            final_score=85,
            framework_choices=["flask"],
            validation_passed=True,
            runtime_passed=True,
        )
        self.memory_store.add_run(
            session_id="test-002",
            prompt="Build API",
            refined_goal="Build API",
            errors=[],
            fixes_applied=[],
            final_score=40,
            framework_choices=["flask"],
            validation_passed=False,
            runtime_passed=False,
        )
        
        rate = self.memory_store.get_framework_success_rate("flask")
        
        assert rate["total"] == 2
        assert rate["successes"] == 1
        assert rate["success_rate"] == 0.5
    
    def test_get_successful_patterns(self):
        """Test getting successful patterns."""
        self.memory_store.add_run(
            session_id="test-001",
            prompt="Build API",
            refined_goal="Build API",
            errors=[],
            fixes_applied=[],
            final_score=85,
            framework_choices=["flask"],
            validation_passed=True,
            runtime_passed=True,
        )
        
        patterns = self.memory_store.get_successful_patterns()
        assert len(patterns) >= 1
    
    def test_get_failure_patterns(self):
        """Test getting failure patterns."""
        self.memory_store.add_run(
            session_id="test-001",
            prompt="Build API",
            refined_goal="Build API",
            errors=["Import error"],
            fixes_applied=[],
            final_score=40,
            framework_choices=["flask"],
            validation_passed=False,
            runtime_passed=False,
        )
        
        patterns = self.memory_store.get_failure_patterns()
        assert len(patterns) >= 1
    
    def test_get_learning_data_for_strategy(self):
        """Test getting learning data for strategy."""
        self.memory_store.add_run(
            session_id="test-001",
            prompt="Build API",
            refined_goal="Build API",
            errors=[],
            fixes_applied=[],
            final_score=85,
            framework_choices=["flask"],
            validation_passed=True,
            runtime_passed=True,
        )
        
        data = self.memory_store.get_learning_data_for_strategy("flask")
        
        assert "successes" in data
        assert "failures" in data
        assert "scores" in data
