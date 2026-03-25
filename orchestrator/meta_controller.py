"""Meta Controller for governing learning and improvement decisions.

This module provides system-awareness for the self-improving orchestrator:
- Decides when to trust learned strategies
- Balances exploration vs exploitation
- Prevents overfitting to past patterns
- Improves long-term performance stability
"""

from __future__ import annotations

import json
import logging
import math
import random
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class StrategyDecision:
    """Represents a single strategy decision made by the meta controller."""
    category: str
    strategy: str
    mode: str  # "explore" or "exploit"
    score: float
    confidence: float
    exploration_rate: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    outcome: Optional[str] = None
    reasoning: str = ""

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "strategy": self.strategy,
            "mode": self.mode,
            "score": self.score,
            "confidence": self.confidence,
            "exploration_rate": self.exploration_rate,
            "timestamp": self.timestamp,
            "outcome": self.outcome,
            "reasoning": self.reasoning,
        }


class MetaController:
    """Governs learning and improvement decisions for the orchestrator.
    
    Responsibilities:
    - Analyze strategy scores and confidence
    - Decide which strategies to apply
    - Balance exploration vs exploitation
    - Prevent overfitting to past patterns
    """
    
    def __init__(
        self,
        memory_dir: str = "memory",
        initial_epsilon: float = 0.5,
        min_epsilon: float = 0.1,
        epsilon_decay: float = 0.95,
        confidence_threshold: float = 0.7,
    ):
        """Initialize the meta controller.
        
        Args:
            memory_dir: Directory for storing decision logs.
            initial_epsilon: Starting exploration rate (0.0-1.0).
            min_epsilon: Minimum exploration rate to maintain.
            epsilon_decay: Decay factor for exploration rate per run.
            confidence_threshold: Minimum confidence to exploit a strategy.
        """
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        # Exploration/exploitation parameters
        self.initial_epsilon = initial_epsilon
        self.min_epsilon = min_epsilon
        self.epsilon_decay = epsilon_decay
        self.confidence_threshold = confidence_threshold
        
        # State
        self.current_epsilon = initial_epsilon
        self.total_runs = 0
        self.decision_history: list[StrategyDecision] = []
        
        # Load state from disk
        self._load_state()
    
    def _load_state(self):
        """Load meta controller state from disk."""
        state_path = self.memory_dir / "meta_controller_state.json"
        if not state_path.exists():
            return
        
        try:
            data = json.loads(state_path.read_text())
            self.current_epsilon = data.get("current_epsilon", self.initial_epsilon)
            self.total_runs = data.get("total_runs", 0)
            
            # Load recent decision history
            decisions_data = data.get("decision_history", [])
            self.decision_history = [
                StrategyDecision(**d) for d in decisions_data[-100:]  # Keep last 100
            ]
            logger.info("Loaded meta controller state: epsilon=%.2f, runs=%d", 
                       self.current_epsilon, self.total_runs)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("Failed to load meta controller state: %s", e)
    
    def _save_state(self):
        """Save meta controller state to disk."""
        state = {
            "current_epsilon": self.current_epsilon,
            "total_runs": self.total_runs,
            "decision_history": [d.to_dict() for d in self.decision_history[-100:]],
            "last_updated": datetime.now().isoformat(),
        }
        state_path = self.memory_dir / "meta_controller_state.json"
        state_path.write_text(json.dumps(state, indent=2))
    
    def compute_exploration_rate(self) -> float:
        """Compute current exploration rate (epsilon).
        
        Decay formula: epsilon = max(min_epsilon, initial_epsilon * decay^runs)
        
        Returns:
            Current exploration rate (0.0-1.0).
        """
        # Exponential decay
        decayed = self.initial_epsilon * (self.epsilon_decay ** self.total_runs)
        
        # Ensure minimum exploration
        epsilon = max(self.min_epsilon, decayed)
        
        return round(epsilon, 4)
    
    def should_explore(self, strategy_key: str, strategy_data: dict) -> bool:
        """Determine if we should explore alternative strategies.
        
        Explore when:
        - Low confidence in current strategy
        - Few runs (insufficient data)
        - High uncertainty (wide confidence interval)
        - Random chance based on epsilon
        
        Args:
            strategy_key: Strategy identifier.
            strategy_data: Strategy statistics from scorer.
            
        Returns:
            True if should explore, False if should exploit.
        """
        epsilon = self.compute_exploration_rate()
        
        # Get strategy statistics
        runs = strategy_data.get("samples", 0)
        confidence = strategy_data.get("mean", 0.5)
        std = strategy_data.get("std", 0.5)
        ci_width = strategy_data.get("ci_high", 0.9) - strategy_data.get("ci_low", 0.1)
        
        # Always explore if insufficient data
        if runs < 3:
            logger.debug("Explore %s: insufficient data (runs=%d)", strategy_key, runs)
            return True
        
        # Explore if low confidence
        if confidence < self.confidence_threshold:
            logger.debug("Explore %s: low confidence (%.2f)", strategy_key, confidence)
            return True
        
        # Explore if high uncertainty (wide CI)
        if ci_width > 0.4:
            logger.debug("Explore %s: high uncertainty (ci_width=%.2f)", strategy_key, ci_width)
            return True
        
        # Epsilon-greedy: random exploration
        if random.random() < epsilon:
            logger.debug("Explore %s: epsilon-greedy (epsilon=%.2f)", strategy_key, epsilon)
            return True
        
        return False
    
    def should_exploit(self, strategy_key: str, strategy_data: dict) -> bool:
        """Determine if we should exploit the current best strategy.
        
        Exploit when:
        - High score
        - High confidence
        - Stable success rate (low std)
        - Sufficient runs
        
        Args:
            strategy_key: Strategy identifier.
            strategy_data: Strategy statistics from scorer.
            
        Returns:
            True if should exploit, False otherwise.
        """
        runs = strategy_data.get("samples", 0)
        confidence = strategy_data.get("mean", 0.5)
        std = strategy_data.get("std", 0.5)
        adjusted_score = strategy_data.get("adjusted_score", 0.5)
        
        # Need minimum data to exploit
        if runs < 5:
            return False
        
        # Need high confidence
        if confidence < self.confidence_threshold:
            return False
        
        # Need stable success rate (low std)
        if std > 0.2:
            return False
        
        # Need good adjusted score
        if adjusted_score < 0.6:
            return False
        
        logger.debug("Exploit %s: score=%.2f, confidence=%.2f, std=%.2f", 
                    strategy_key, adjusted_score, confidence, std)
        return True
    
    def select_strategy(
        self,
        category: str,
        candidates: list[dict],
        context: Optional[str] = None,
    ) -> StrategyDecision:
        """Select a strategy using meta-controller logic.
        
        Uses epsilon-greedy with confidence weighting:
        - With probability epsilon: explore (random weighted by potential)
        - With probability 1-epsilon: exploit (choose best confident strategy)
        
        Args:
            category: Strategy category (frameworks, architectures, tools).
            candidates: List of candidate strategies with scores.
            context: Optional context for decision.
            
        Returns:
            StrategyDecision with selected strategy and reasoning.
        """
        if not candidates:
            return StrategyDecision(
                category=category,
                strategy="unknown",
                mode="none",
                score=0.0,
                confidence=0.0,
                exploration_rate=self.compute_exploration_rate(),
                reasoning="No candidates available",
            )
        
        epsilon = self.compute_exploration_rate()
        
        # Filter candidates with sufficient confidence for exploitation
        exploitable = [
            c for c in candidates
            if c.get("samples", 0) >= 3 and c.get("mean", 0) >= self.confidence_threshold
        ]
        
        # Decide: explore or exploit
        if random.random() < epsilon or not exploitable:
            # EXPLORATION MODE
            selected = self._select_for_exploration(candidates, exploitable)
            mode = "explore"
            reasoning = f"Exploration mode (epsilon={epsilon:.2f})"
        else:
            # EXPLOITATION MODE
            selected = self._select_for_exploitation(exploitable)
            mode = "exploit"
            reasoning = f"Exploitation mode (confidence={selected.get('mean', 0):.2f})"
        
        # Apply anti-overfitting penalties
        selected = self._apply_anti_overfitting(selected, category)
        
        decision = StrategyDecision(
            category=category,
            strategy=selected.get("strategy", "unknown"),
            mode=mode,
            score=selected.get("adjusted_score", 0.0),
            confidence=selected.get("mean", 0.0),
            exploration_rate=epsilon,
            reasoning=reasoning,
        )
        
        self.decision_history.append(decision)
        logger.info("Meta decision: %s -> %s (mode=%s)", category, decision.strategy, mode)
        
        return decision
    
    def _select_for_exploration(
        self,
        candidates: list[dict],
        exploitable: list[dict],
    ) -> dict:
        """Select a strategy for exploration.
        
        Exploration strategy:
        - Prefer candidates with high potential (upper CI bound)
        - Give some weight to less-tried strategies
        """
        if not candidates:
            return {"strategy": "unknown", "adjusted_score": 0, "mean": 0}
        
        # Score by potential (upper CI bound)
        scored = []
        for c in candidates:
            ci_high = c.get("ci_high", c.get("adjusted_score", 0) + 0.2)
            runs = c.get("samples", 0)
            
            # Bonus for unexplored strategies
            exploration_bonus = 0.1 if runs < 5 else 0
            
            potential_score = ci_high + exploration_bonus
            scored.append((potential_score, c))
        
        # Softmax selection for exploration
        scores = [s[0] for s in scored]
        probs = self._softmax(scores)
        
        selected_idx = random.choices(range(len(scored)), weights=probs, k=1)[0]
        return scored[selected_idx][1]
    
    def _select_for_exploitation(self, exploitable: list[dict]) -> dict:
        """Select a strategy for exploitation.
        
        Exploitation strategy:
        - Choose highest adjusted score with high confidence
        - Prefer stable strategies (low std)
        """
        if not exploitable:
            return {"strategy": "unknown", "adjusted_score": 0, "mean": 0}
        
        # Sort by adjusted score (already confidence-weighted)
        exploitable_sorted = sorted(
            exploitable,
            key=lambda x: x.get("adjusted_score", 0),
            reverse=True
        )
        
        return exploitable_sorted[0]
    
    def _apply_anti_overfitting(
        self,
        candidate: dict,
        category: str,
        penalty_threshold: float = 0.3,
    ) -> dict:
        """Apply anti-overfitting penalties to prevent strategy lock-in.
        
        Penalties applied when:
        - Strategy has been chosen too frequently recently
        - Strategy has required many repairs
        - Strategy shows declining performance
        
        Args:
            candidate: Selected strategy candidate.
            category: Strategy category.
            penalty_threshold: Threshold for applying penalties.
            
        Returns:
            Potentially penalized candidate.
        """
        strategy = candidate.get("strategy", "")
        
        # Count recent selections
        recent_selections = sum(
            1 for d in self.decision_history[-20:]
            if d.category == category and d.strategy == strategy
        )
        
        # Penalty for over-selection
        if recent_selections > 10:
            penalty = min(0.3, (recent_selections - 10) * 0.05)
            candidate = candidate.copy()
            candidate["adjusted_score"] = candidate.get("adjusted_score", 0) * (1 - penalty)
            logger.debug("Anti-overfitting penalty for %s: %.2f (recent=%d)", 
                        strategy, penalty, recent_selections)
        
        return candidate
    
    def _softmax(self, scores: list[float], temperature: float = 1.0) -> list[float]:
        """Compute softmax probabilities for scores.
        
        Args:
            scores: List of scores.
            temperature: Temperature for softmax (higher = more uniform).
            
        Returns:
            List of probabilities summing to 1.
        """
        if not scores:
            return []
        
        # Numerical stability
        max_score = max(scores)
        exp_scores = [math.exp((s - max_score) / temperature) for s in scores]
        total = sum(exp_scores)
        
        return [e / total for e in exp_scores]
    
    def record_outcome(
        self,
        decision: StrategyDecision,
        success: bool,
        score: float,
        repair_count: int = 0,
    ):
        """Record the outcome of a strategy decision.
        
        Args:
            decision: The original strategy decision.
            success: Whether the run was successful.
            score: Evaluation score (0-100).
            repair_count: Number of repairs needed.
        """
        # Update decision with outcome
        decision.outcome = "success" if success else "failure"
        
        # Increment run counter
        self.total_runs += 1
        
        # Adjust exploration rate based on outcome
        self._adjust_exploration_rate(success, repair_count)
        
        # Decay confidence if many repairs needed
        if repair_count > 2:
            logger.warning("High repair count (%d) for %s - may need exploration", 
                          repair_count, decision.strategy)
        
        # Save state
        self._save_state()
        
        logger.info("Recorded outcome for %s: %s (score=%.1f, repairs=%d)", 
                   decision.strategy, decision.outcome, score, repair_count)
    
    def _adjust_exploration_rate(self, success: bool, repair_count: int):
        """Adjust exploration rate based on outcome.
        
        - Success with low repairs: slightly decrease exploration (more confident)
        - Failure or high repairs: slightly increase exploration (less confident)
        """
        if success and repair_count <= 1:
            # Good outcome: can be slightly more exploitative
            adjustment = -0.01
        elif success and repair_count <= 2:
            # Okay outcome: no change
            adjustment = 0
        else:
            # Bad outcome: need more exploration
            adjustment = +0.02
        
        # Apply adjustment with bounds
        new_epsilon = self.current_epsilon + adjustment
        self.current_epsilon = max(self.min_epsilon, min(1.0, new_epsilon))
        
        # Also apply decay
        self.current_epsilon = max(
            self.min_epsilon,
            self.current_epsilon * self.epsilon_decay
        )
    
    def get_decision_summary(self) -> dict:
        """Get summary of meta controller decisions.

        Returns:
            Summary dictionary with statistics.
        """
        if not self.decision_history:
            return {
                "total_decisions": 0,
                "exploration_count": 0,
                "exploitation_count": 0,
                "exploration_rate": 0,
                "success_rate": 0,
                "explore_success_rate": 0,
                "exploit_success_rate": 0,
                "current_epsilon": self.current_epsilon,
                "total_runs": self.total_runs,
            }

        explore_count = sum(1 for d in self.decision_history if d.mode == "explore")
        exploit_count = sum(1 for d in self.decision_history if d.mode == "exploit")
        success_count = sum(1 for d in self.decision_history if d.outcome == "success")

        # Compute success rate by mode
        explore_success = sum(
            1 for d in self.decision_history
            if d.mode == "explore" and d.outcome == "success"
        )
        exploit_success = sum(
            1 for d in self.decision_history
            if d.mode == "exploit" and d.outcome == "success"
        )

        return {
            "total_decisions": len(self.decision_history),
            "exploration_count": explore_count,
            "exploitation_count": exploit_count,
            "exploration_rate": explore_count / len(self.decision_history) if self.decision_history else 0,
            "success_rate": success_count / len(self.decision_history) if self.decision_history else 0,
            "explore_success_rate": explore_success / explore_count if explore_count > 0 else 0,
            "exploit_success_rate": exploit_success / exploit_count if exploit_count > 0 else 0,
            "current_epsilon": self.current_epsilon,
            "total_runs": self.total_runs,
        }
    
    def get_recommendations(self) -> dict:
        """Get recommendations based on decision history.
        
        Returns:
            Recommendations dictionary.
        """
        summary = self.get_decision_summary()
        
        recommendations = []
        
        # Analyze exploration vs exploitation balance
        if summary["exploration_rate"] < 0.15:
            recommendations.append({
                "type": "increase_exploration",
                "message": "Exploration rate is low. Consider increasing epsilon to discover better strategies.",
            })
        elif summary["exploration_rate"] > 0.5:
            recommendations.append({
                "type": "decrease_exploration",
                "message": "Exploration rate is high. System may benefit from more exploitation of known good strategies.",
            })
        
        # Analyze success rates
        if summary["explore_success_rate"] > summary["exploit_success_rate"] + 0.1:
            recommendations.append({
                "type": "exploration_effective",
                "message": "Exploration is yielding better results than exploitation. Current epsilon is appropriate.",
            })
        
        # Check for overfitting
        recent_strategies = [d.strategy for d in self.decision_history[-10:]]
        if len(set(recent_strategies)) < 3:
            recommendations.append({
                "type": "potential_overfitting",
                "message": "Low strategy diversity in recent runs. May be overfitting to specific strategies.",
            })
        
        return {
            "summary": summary,
            "recommendations": recommendations,
            "current_epsilon": self.current_epsilon,
        }
    
    def reset(self, keep_history: bool = False):
        """Reset meta controller state.
        
        Args:
            keep_history: If True, keep decision history.
        """
        self.current_epsilon = self.initial_epsilon
        self.total_runs = 0
        
        if not keep_history:
            self.decision_history = []
        
        self._save_state()
        logger.info("Meta controller reset (keep_history=%s)", keep_history)


class MetaControllerContext:
    """Context builder for integrating meta controller decisions into planning."""
    
    def __init__(self, meta_controller: MetaController):
        self.meta_controller = meta_controller
    
    def build_planning_context(
        self,
        strategy_rankings: dict[str, list[dict]],
    ) -> dict:
        """Build planning context with meta-controller decisions.
        
        Args:
            strategy_rankings: Rankings from strategy scorer by category.
            
        Returns:
            Planning context dictionary.
        """
        context = {
            "selected_strategies": {},
            "exploration_mode": False,
            "meta_decisions": [],
            "confidence_summary": {},
        }
        
        for category, candidates in strategy_rankings.items():
            if not candidates:
                continue
            
            # Get meta-controller decision
            decision = self.meta_controller.select_strategy(category, candidates)
            
            context["selected_strategies"][category] = decision.strategy
            context["meta_decisions"].append(decision.to_dict())
            
            if decision.mode == "explore":
                context["exploration_mode"] = True
            
            context["confidence_summary"][category] = {
                "strategy": decision.strategy,
                "confidence": decision.confidence,
                "mode": decision.mode,
            }
        
        return context
    
    def format_planner_hint(self, context: dict) -> str:
        """Format meta-controller context as planner hint.
        
        Args:
            context: Planning context from build_planning_context().
            
        Returns:
            Hint string to inject into planner prompt.
        """
        hints = []
        
        # Strategy recommendations
        selected = context.get("selected_strategies", {})
        if selected:
            strategies_str = ", ".join(f"{k}:{v}" for k, v in selected.items())
            hints.append(f"Meta-controller recommends: {strategies_str}")
        
        # Exploration mode notice
        if context.get("exploration_mode"):
            hints.append("Note: System is in exploration mode - trying alternative approaches")
        
        # Confidence hints
        confidence = context.get("confidence_summary", {})
        for category, data in confidence.items():
            if data.get("confidence", 0) >= 0.8:
                hints.append(f"High confidence in {category}: {data['strategy']}")
        
        if not hints:
            return ""
        
        return "\n\n--- META-CONTROLLER GUIDANCE ---\n" + "\n".join(hints) + "\n--- END GUIDANCE ---\n"
