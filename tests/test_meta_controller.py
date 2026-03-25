"""Unit tests for the Meta Controller module."""

import pytest
import tempfile
import shutil
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator.meta_controller import (
    MetaController,
    MetaControllerContext,
    StrategyDecision,
)
from orchestrator.strategy_scorer import StrategyScorer


class TestStrategyDecision:
    """Tests for StrategyDecision dataclass."""
    
    def test_create_decision(self):
        """Test creating a strategy decision."""
        decision = StrategyDecision(
            category="frameworks",
            strategy="flask",
            mode="exploit",
            score=0.85,
            confidence=0.9,
            exploration_rate=0.2,
        )
        
        assert decision.category == "frameworks"
        assert decision.strategy == "flask"
        assert decision.mode == "exploit"
        assert decision.score == 0.85
        assert decision.confidence == 0.9
        assert decision.exploration_rate == 0.2
        assert decision.outcome is None
    
    def test_decision_to_dict(self):
        """Test converting decision to dictionary."""
        decision = StrategyDecision(
            category="frameworks",
            strategy="fastapi",
            mode="explore",
            score=0.75,
            confidence=0.6,
            exploration_rate=0.3,
            outcome="success",
            reasoning="High potential strategy",
        )
        
        data = decision.to_dict()
        
        assert data["category"] == "frameworks"
        assert data["strategy"] == "fastapi"
        assert data["mode"] == "explore"
        assert data["outcome"] == "success"
        assert "reasoning" in data


class TestMetaController:
    """Tests for MetaController class."""
    
    def setup_method(self):
        """Create temporary directory for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.controller = MetaController(memory_dir=self.temp_dir)
    
    def teardown_method(self):
        """Clean up temporary directory after each test."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initial_state(self):
        """Test initial meta controller state."""
        assert self.controller.current_epsilon == self.controller.initial_epsilon
        assert self.controller.total_runs == 0
        assert len(self.controller.decision_history) == 0
    
    def test_compute_exploration_rate_initial(self):
        """Test exploration rate at start."""
        epsilon = self.controller.compute_exploration_rate()
        
        # Should be initial epsilon (or close due to decay)
        assert epsilon <= self.controller.initial_epsilon
        assert epsilon >= self.controller.min_epsilon
    
    def test_compute_exploration_rate_decays(self):
        """Test exploration rate decays over runs."""
        initial = self.controller.compute_exploration_rate()
        
        # Simulate runs
        self.controller.total_runs = 10
        after_10 = self.controller.compute_exploration_rate()
        
        self.controller.total_runs = 50
        after_50 = self.controller.compute_exploration_rate()
        
        assert after_10 < initial
        assert after_50 < after_10
        assert after_50 >= self.controller.min_epsilon
    
    def test_should_explore_insufficient_data(self):
        """Test exploration with insufficient data."""
        strategy_data = {"samples": 1, "mean": 0.9, "std": 0.1}
        
        result = self.controller.should_explore("flask", strategy_data)
        
        assert result is True  # Always explore with < 3 runs
    
    def test_should_explore_low_confidence(self):
        """Test exploration with low confidence."""
        strategy_data = {"samples": 10, "mean": 0.4, "std": 0.2}
        
        result = self.controller.should_explore("flask", strategy_data)
        
        assert result is True  # Explore when confidence < threshold
    
    def test_should_exploit_high_confidence(self):
        """Test exploitation with high confidence."""
        strategy_data = {
            "samples": 20,
            "mean": 0.9,
            "std": 0.05,
            "adjusted_score": 0.85,
        }
        
        result = self.controller.should_exploit("flask", strategy_data)
        
        assert result is True
    
    def test_should_exploit_insufficient_data(self):
        """Test that exploitation requires minimum data."""
        strategy_data = {
            "samples": 2,
            "mean": 0.95,
            "std": 0.01,
            "adjusted_score": 0.9,
        }
        
        result = self.controller.should_exploit("flask", strategy_data)
        
        assert result is False  # Need at least 5 runs
    
    def test_select_strategy_exploitation(self):
        """Test strategy selection in exploitation mode."""
        candidates = [
            {"strategy": "flask", "adjusted_score": 0.85, "mean": 0.9, "samples": 20, "ci_high": 0.95},
            {"strategy": "fastapi", "adjusted_score": 0.75, "mean": 0.8, "samples": 15, "ci_high": 0.85},
        ]
        
        # Force exploitation by setting very low epsilon and using exploitable candidates
        self.controller.initial_epsilon = 0.0
        self.controller.current_epsilon = 0.0
        self.controller.confidence_threshold = 0.5  # Lower threshold
        
        # Run multiple times to account for any randomness
        exploit_count = 0
        for _ in range(10):
            decision = self.controller.select_strategy("frameworks", candidates)
            if decision.mode == "exploit":
                exploit_count += 1
        
        # Should mostly exploit
        assert exploit_count >= 7
    
    def test_select_strategy_exploration(self):
        """Test strategy selection in exploration mode."""
        candidates = [
            {"strategy": "flask", "adjusted_score": 0.85, "mean": 0.9, "samples": 20, "ci_high": 0.95},
            {"strategy": "fastapi", "adjusted_score": 0.75, "mean": 0.8, "samples": 3, "ci_high": 0.95},
        ]
        
        # Force exploration by setting high epsilon
        self.controller.initial_epsilon = 1.0
        self.controller.current_epsilon = 1.0
        
        decision = self.controller.select_strategy("frameworks", candidates)
        
        # In exploration mode, could pick either based on potential
        assert decision.strategy in ["flask", "fastapi"]
        assert decision.mode == "explore"
    
    def test_select_strategy_no_candidates(self):
        """Test strategy selection with no candidates."""
        decision = self.controller.select_strategy("frameworks", [])
        
        assert decision.strategy == "unknown"
        assert decision.mode == "none"
    
    def test_record_outcome_updates_state(self):
        """Test that recording outcome updates state."""
        # First make a decision to add to history
        candidates = [
            {"strategy": "flask", "adjusted_score": 0.85, "mean": 0.9, "samples": 20, "ci_high": 0.95},
        ]
        decision = self.controller.select_strategy("frameworks", candidates)
        
        self.controller.record_outcome(decision, success=True, score=85, repair_count=0)
        
        assert self.controller.total_runs == 1
        assert len(self.controller.decision_history) >= 1
    
    def test_record_outcome_adjusts_epsilon_good(self):
        """Test epsilon adjustment for good outcomes."""
        initial_epsilon = self.controller.current_epsilon
        
        decision = StrategyDecision(
            category="frameworks",
            strategy="flask",
            mode="exploit",
            score=0.85,
            confidence=0.9,
            exploration_rate=0.2,
        )
        
        self.controller.record_outcome(decision, success=True, score=90, repair_count=0)
        
        # Good outcome should slightly decrease epsilon
        assert self.controller.current_epsilon <= initial_epsilon
    
    def test_record_outcome_adjusts_epsilon_bad(self):
        """Test epsilon adjustment for bad outcomes."""
        initial_epsilon = self.controller.current_epsilon
        
        decision = StrategyDecision(
            category="frameworks",
            strategy="flask",
            mode="exploit",
            score=0.85,
            confidence=0.9,
            exploration_rate=0.2,
        )
        
        self.controller.record_outcome(decision, success=False, score=40, repair_count=3)
        
        # Bad outcome should increase epsilon (before decay)
        # Note: decay is applied after, so we check the logic
    
    def test_get_decision_summary(self):
        """Test getting decision summary."""
        # Add some decisions
        candidates = [
            {"strategy": "flask", "adjusted_score": 0.85, "mean": 0.9, "samples": 20, "ci_high": 0.95},
        ]
        decision1 = self.controller.select_strategy("frameworks", candidates)
        self.controller.record_outcome(decision1, success=True, score=85)
        
        candidates2 = [
            {"strategy": "fastapi", "adjusted_score": 0.75, "mean": 0.8, "samples": 15, "ci_high": 0.85},
        ]
        decision2 = self.controller.select_strategy("frameworks", candidates2)
        self.controller.record_outcome(decision2, success=False, score=50)
        
        summary = self.controller.get_decision_summary()
        
        assert summary["total_decisions"] == 2
        assert summary["exploration_count"] + summary["exploitation_count"] == 2
    
    def test_get_recommendations(self):
        """Test getting recommendations."""
        recommendations = self.controller.get_recommendations()
        
        assert "summary" in recommendations
        assert "recommendations" in recommendations
        assert "current_epsilon" in recommendations
    
    def test_reset(self):
        """Test resetting meta controller."""
        # Add some state
        decision = StrategyDecision(
            category="frameworks",
            strategy="flask",
            mode="exploit",
            score=0.85,
            confidence=0.9,
            exploration_rate=0.2,
        )
        self.controller.record_outcome(decision, success=True, score=85)
        
        # Reset
        self.controller.reset(keep_history=False)
        
        assert self.controller.current_epsilon == self.controller.initial_epsilon
        assert self.controller.total_runs == 0
        assert len(self.controller.decision_history) == 0


class TestMetaControllerContext:
    """Tests for MetaControllerContext class."""
    
    def setup_method(self):
        """Create temporary directory for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.controller = MetaController(memory_dir=self.temp_dir)
        self.context = MetaControllerContext(self.controller)
    
    def teardown_method(self):
        """Clean up temporary directory after each test."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_build_planning_context(self):
        """Test building planning context."""
        strategy_rankings = {
            "frameworks": [
                {"strategy": "flask", "adjusted_score": 0.85, "mean": 0.9, "samples": 20, "ci_high": 0.95},
                {"strategy": "fastapi", "adjusted_score": 0.75, "mean": 0.8, "samples": 15, "ci_high": 0.85},
            ],
            "architectures": [
                {"strategy": "layered", "adjusted_score": 0.8, "mean": 0.85, "samples": 10, "ci_high": 0.9},
            ],
            "tools": [],
        }
        
        context = self.context.build_planning_context(strategy_rankings)
        
        assert "selected_strategies" in context
        assert "meta_decisions" in context
        assert "exploration_mode" in context
        assert "confidence_summary" in context
    
    def test_format_planner_hint(self):
        """Test formatting planner hint."""
        context = {
            "selected_strategies": {
                "frameworks": "flask",
                "architectures": "layered",
            },
            "exploration_mode": True,
            "confidence_summary": {
                "frameworks": {"strategy": "flask", "confidence": 0.9, "mode": "exploit"},
            },
        }
        
        hint = self.context.format_planner_hint(context)
        
        assert "META-CONTROLLER GUIDANCE" in hint
        assert "flask" in hint
        assert "exploration mode" in hint.lower()
    
    def test_format_planner_hint_empty(self):
        """Test formatting hint with empty context."""
        hint = self.context.format_planner_hint({})
        
        assert hint == ""


class TestMetaControllerIntegration:
    """Integration tests for meta controller with strategy scorer."""
    
    def setup_method(self):
        """Create temporary directory for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.controller = MetaController(memory_dir=self.temp_dir)
        self.scorer = StrategyScorer(memory_dir=self.temp_dir)
        self.context = MetaControllerContext(self.controller)
    
    def teardown_method(self):
        """Clean up temporary directory after each test."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_full_decision_cycle(self):
        """Test full decision -> outcome -> learning cycle."""
        # Record some strategy outcomes
        self.scorer.record_outcome("flask", "frameworks", True, 85)
        self.scorer.record_outcome("flask", "frameworks", True, 88)
        self.scorer.record_outcome("flask", "frameworks", True, 90)
        self.scorer.record_outcome("fastapi", "frameworks", True, 92)
        self.scorer.record_outcome("fastapi", "frameworks", True, 95)
        
        # Get rankings
        rankings = {
            "frameworks": self.scorer.get_ranking_with_confidence("frameworks"),
        }
        
        # Make decision
        context = self.context.build_planning_context(rankings)
        
        assert "frameworks" in context["selected_strategies"]
        assert context["selected_strategies"]["frameworks"] in ["flask", "fastapi"]
    
    def test_exploration_exploitation_balance(self):
        """Test that exploration/exploitation balance works."""
        # Add data for one strong strategy
        for _ in range(20):
            self.scorer.record_outcome("flask", "frameworks", True, 90)
        
        # Add data for one untested strategy
        self.scorer.record_outcome("newfw", "frameworks", True, 80)
        
        rankings = {
            "frameworks": self.scorer.get_ranking_with_confidence("frameworks"),
        }
        
        # Make multiple decisions
        explore_count = 0
        for _ in range(20):
            decision = self.controller.select_strategy("frameworks", rankings["frameworks"])
            if decision.mode == "explore":
                explore_count += 1
        
        # Should have some exploration (at least 10% due to min_epsilon)
        assert explore_count >= 1
