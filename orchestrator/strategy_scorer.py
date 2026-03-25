"""Strategy scoring system for tracking and ranking architectural decisions.

This module maintains scores for:
- Frameworks (Flask, FastAPI, React, etc.)
- Architectures (layered, monolith, microservices, etc.)
- Tools (pytest, SQLAlchemy, etc.)

Scores are updated after each run based on outcomes.
"""

from __future__ import annotations

import json
import logging
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class BayesianScoreUpdater:
    """Bayesian score updater for strategy scoring.
    
    Uses Beta distribution to maintain confidence intervals.
    """
    
    def __init__(self, prior_alpha: float = 1.0, prior_beta: float = 1.0):
        """Initialize with Beta prior.
        
        Args:
            prior_alpha: Prior successes (default: 1 = uniform prior).
            prior_beta: Prior failures (default: 1 = uniform prior).
        """
        self.prior_alpha = prior_alpha
        self.prior_beta = prior_beta
    
    def update(
        self,
        successes: int,
        failures: int,
        avg_score: float = 50.0,
    ) -> dict:
        """Update posterior distribution.
        
        Args:
            successes: Number of successful outcomes.
            failures: Number of failed outcomes.
            avg_score: Average evaluation score (0-100).
            
        Returns:
            Dictionary with posterior statistics.
        """
        alpha = self.prior_alpha + successes
        beta = self.prior_beta + failures
        
        # Posterior mean (expected success rate)
        mean = alpha / (alpha + beta)
        
        # Posterior variance
        variance = (alpha * beta) / ((alpha + beta) ** 2 * (alpha + beta + 1))
        std = math.sqrt(variance)
        
        # 95% credible interval
        z = 1.96
        ci_low = max(0, mean - z * std)
        ci_high = min(1, mean + z * std)
        
        # Quality-adjusted score (combines success rate with avg evaluation score)
        quality_factor = avg_score / 100
        adjusted_score = mean * 0.7 + quality_factor * 0.3
        
        return {
            "mean": mean,
            "std": std,
            "ci_low": ci_low,
            "ci_high": ci_high,
            "adjusted_score": adjusted_score,
            "samples": successes + failures,
        }


class StrategyScorer:
    """Maintains and updates scores for strategies."""
    
    def __init__(self, memory_dir: str = "memory"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.scores_path = self.memory_dir / "strategy_scores.json"
        
        self.updater = BayesianScoreUpdater()
        
        # Strategy data structure
        self.strategies: dict[str, dict] = {
            "frameworks": {},
            "architectures": {},
            "tools": {},
        }
        
        # Context-specific scores (e.g., "flask:crud_api")
        self.context_scores: dict[str, dict] = {}
        
        self._load_scores()
    
    def _load_scores(self):
        """Load scores from disk."""
        if not self.scores_path.exists():
            return
        
        try:
            data = json.loads(self.scores_path.read_text())
            self.strategies = data.get("strategies", self.strategies)
            self.context_scores = data.get("context_scores", {})
            logger.info("Loaded strategy scores from disk")
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("Failed to load strategy scores: %s", e)
    
    def _save_scores(self):
        """Save scores to disk."""
        data = {
            "strategies": self.strategies,
            "context_scores": self.context_scores,
            "last_updated": datetime.now().isoformat(),
        }
        self.scores_path.write_text(json.dumps(data, indent=2))
    
    def record_outcome(
        self,
        strategy_key: str,
        category: str,
        success: bool,
        score: float = 50.0,
        context: Optional[str] = None,
    ):
        """Record an outcome for a strategy.
        
        Args:
            strategy_key: Strategy identifier (e.g., "flask", "layered").
            category: Category (frameworks, architectures, tools).
            success: Whether the run was successful.
            score: Evaluation score (0-100).
            context: Optional context for context-specific scoring.
        """
        if category not in self.strategies:
            self.strategies[category] = {}
        
        if strategy_key not in self.strategies[category]:
            self.strategies[category][strategy_key] = {
                "successes": 0,
                "failures": 0,
                "scores": [],
                "last_updated": datetime.now().isoformat(),
            }
        
        strategy = self.strategies[category][strategy_key]
        
        if success:
            strategy["successes"] += 1
        else:
            strategy["failures"] += 1
        
        strategy["scores"].append(score)
        
        # Keep only last 100 scores to prevent unbounded growth
        strategy["scores"] = strategy["scores"][-100:]
        
        strategy["last_updated"] = datetime.now().isoformat()
        
        # Update context-specific score if provided
        if context:
            context_key = f"{strategy_key}:{context}"
            self._update_context_score(context_key, success, score)

        self._save_scores()
        logger.debug(
            "Recorded outcome for %s/%s: success=%s, score=%.1f",
            category, strategy_key, success, score
        )

    def record_outcome_with_repairs(
        self,
        strategy_key: str,
        category: str,
        success: bool,
        score: float = 50.0,
        repair_count: int = 0,
        context: Optional[str] = None,
    ):
        """Record outcome with repair count tracking.

        Args:
            strategy_key: Strategy identifier.
            category: Category (frameworks, architectures, tools).
            success: Whether the run was successful.
            score: Evaluation score (0-100).
            repair_count: Number of repairs needed.
            context: Optional context for context-specific scoring.
        """
        self.record_outcome(strategy_key, category, success, score, context)

        # Track repair count
        if category in self.strategies and strategy_key in self.strategies[category]:
            strategy = self.strategies[category][strategy_key]
            existing_repairs = strategy.get("repair_count", 0)
            # Exponential moving average of repairs
            alpha = 0.3
            strategy["repair_count"] = alpha * repair_count + (1 - alpha) * existing_repairs
            self._save_scores()
    
    def _update_context_score(self, context_key: str, success: bool, score: float):
        """Update context-specific score."""
        if context_key not in self.context_scores:
            self.context_scores[context_key] = {
                "successes": 0,
                "failures": 0,
                "scores": [],
            }
        
        ctx = self.context_scores[context_key]
        if success:
            ctx["successes"] += 1
        else:
            ctx["failures"] += 1
        
        ctx["scores"].append(score)
        ctx["scores"] = ctx["scores"][-50:]  # Keep last 50
    
    def get_score(self, category: str, strategy_key: str) -> Optional[dict]:
        """Get computed score for a strategy.

        Args:
            category: Category (frameworks, architectures, tools).
            strategy_key: Strategy identifier.

        Returns:
            Score dictionary or None if not found.
        """
        if category not in self.strategies:
            return None

        if strategy_key not in self.strategies[category]:
            return None

        strategy = self.strategies[category][strategy_key]

        return self.updater.update(
            successes=strategy["successes"],
            failures=strategy["failures"],
            avg_score=sum(strategy["scores"]) / len(strategy["scores"]) if strategy["scores"] else 50.0,
        )

    def get_strategy_with_confidence(
        self,
        category: str,
        strategy_key: str,
    ) -> Optional[dict]:
        """Get strategy data with full confidence information.

        Extended version that includes all meta-controller relevant data.

        Args:
            category: Category (frameworks, architectures, tools).
            strategy_key: Strategy identifier.

        Returns:
            Extended score dictionary with confidence metrics.
        """
        base_score = self.get_score(category, strategy_key)
        if not base_score:
            return None

        strategy = self.strategies[category][strategy_key]

        # Compute additional metrics
        scores = strategy.get("scores", [])
        repair_count = strategy.get("repair_count", 0)
        last_updated = strategy.get("last_updated", "")

        # Trend analysis (last 5 vs previous 5)
        trend = "stable"
        if len(scores) >= 10:
            recent_avg = sum(scores[-5:]) / 5
            older_avg = sum(scores[-10:-5]) / 5
            if recent_avg > older_avg + 5:
                trend = "improving"
            elif recent_avg < older_avg - 5:
                trend = "declining"

        return {
            "strategy": strategy_key,
            "category": category,
            **base_score,
            "successes": strategy["successes"],
            "failures": strategy["failures"],
            "avg_score": sum(scores) / len(scores) if scores else 0,
            "repair_count": repair_count,
            "trend": trend,
            "last_updated": last_updated,
        }

    def get_ranking_with_confidence(self, category: str, min_samples: int = 2) -> list[dict]:
        """Get ranked list with full confidence data.

        Args:
            category: Category to rank.
            min_samples: Minimum samples required for ranking.

        Returns:
            List of strategies with full confidence data, sorted by adjusted score.
        """
        if category not in self.strategies:
            return []

        rankings = []
        for strategy_key in self.strategies[category]:
            data = self.get_strategy_with_confidence(category, strategy_key)
            if data and data.get("samples", 0) >= min_samples:
                rankings.append(data)

        rankings.sort(key=lambda x: x.get("adjusted_score", 0), reverse=True)
        return rankings
    
    def get_ranking(self, category: str, min_samples: int = 2) -> list[dict]:
        """Get ranked list of strategies in a category.
        
        Args:
            category: Category to rank.
            min_samples: Minimum samples required for ranking.
            
        Returns:
            List of strategies with scores, sorted by adjusted score.
        """
        if category not in self.strategies:
            return []
        
        rankings = []
        for strategy_key, strategy in self.strategies[category].items():
            samples = strategy["successes"] + strategy["failures"]
            if samples < min_samples:
                continue
            
            score_data = self.get_score(category, strategy_key)
            if score_data:
                rankings.append({
                    "strategy": strategy_key,
                    "successes": strategy["successes"],
                    "failures": strategy["failures"],
                    "avg_score": sum(strategy["scores"]) / len(strategy["scores"]) if strategy["scores"] else 0,
                    **score_data,
                })
        
        rankings.sort(key=lambda x: x["adjusted_score"], reverse=True)
        return rankings
    
    def get_best(self, category: str, min_samples: int = 2) -> Optional[str]:
        """Get the best strategy in a category.
        
        Args:
            category: Category to query.
            min_samples: Minimum samples required.
            
        Returns:
            Strategy key or None if no qualifying strategies.
        """
        ranking = self.get_ranking(category, min_samples)
        if ranking:
            return ranking[0]["strategy"]
        return None
    
    def get_recommendations(
        self,
        task_description: str,
        top_n: int = 3,
    ) -> dict:
        """Get strategy recommendations based on task description.
        
        Args:
            task_description: User's task description.
            top_n: Number of recommendations per category.
            
        Returns:
            Dictionary with recommendations per category.
        """
        recommendations = {
            "frameworks": [],
            "architectures": [],
            "tools": [],
        }
        
        # Simple keyword-based context detection
        task_lower = task_description.lower()
        context = None
        
        if any(kw in task_lower for kw in ["api", "rest", "crud", "backend"]):
            context = "api"
        elif any(kw in task_lower for kw in ["dashboard", "ui", "frontend"]):
            context = "ui"
        elif any(kw in task_lower for kw in ["test", "testing"]):
            context = "testing"
        
        # Get rankings
        for category in recommendations.keys():
            ranking = self.get_ranking(category)
            
            # If context-specific scores exist, boost them
            if context:
                for item in ranking:
                    context_key = f"{item['strategy']}:{context}"
                    if context_key in self.context_scores:
                        ctx_data = self.context_scores[context_key]
                        ctx_samples = ctx_data["successes"] + ctx_data["failures"]
                        if ctx_samples >= 2:
                            # Boost score by 10% for context match
                            item["adjusted_score"] *= 1.1
            
            # Re-sort after boosting
            ranking.sort(key=lambda x: x["adjusted_score"], reverse=True)
            recommendations[category] = ranking[:top_n]
        
        return recommendations
    
    def get_confidence(self, category: str, strategy_key: str) -> dict:
        """Get confidence metrics for a strategy.
        
        Args:
            category: Category.
            strategy_key: Strategy identifier.
            
        Returns:
            Confidence dictionary.
        """
        score_data = self.get_score(category, strategy_key)
        if not score_data:
            return {"confidence": "unknown", "samples": 0}
        
        samples = score_data["samples"]
        ci_width = score_data["ci_high"] - score_data["ci_low"]
        
        # Confidence based on sample size and CI width
        if samples >= 20:
            confidence = "high"
        elif samples >= 5:
            confidence = "medium"
        else:
            confidence = "low"
        
        return {
            "confidence": confidence,
            "samples": samples,
            "ci_width": ci_width,
            "std": score_data["std"],
        }
    
    def get_improvement_trend(self, category: str, strategy_key: str) -> dict:
        """Analyze score trend over time for a strategy.
        
        Args:
            category: Category.
            strategy_key: Strategy identifier.
            
        Returns:
            Trend analysis dictionary.
        """
        if category not in self.strategies:
            return {"trend": "unknown", "data_points": 0}
        
        if strategy_key not in self.strategies[category]:
            return {"trend": "unknown", "data_points": 0}
        
        scores = self.strategies[category][strategy_key].get("scores", [])
        
        if len(scores) < 3:
            return {"trend": "insufficient_data", "data_points": len(scores)}
        
        # Compare first half vs second half
        mid = len(scores) // 2
        first_half_avg = sum(scores[:mid]) / mid if mid > 0 else 0
        second_half_avg = sum(scores[mid:]) / (len(scores) - mid) if len(scores) > mid else 0
        
        diff = second_half_avg - first_half_avg
        
        if diff > 5:
            trend = "improving"
        elif diff < -5:
            trend = "declining"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "data_points": len(scores),
            "first_half_avg": first_half_avg,
            "second_half_avg": second_half_avg,
            "change": diff,
        }
    
    def get_summary(self) -> dict:
        """Get summary of all strategy scores.
        
        Returns:
            Summary dictionary.
        """
        summary = {
            "categories": {},
            "top_strategies": {},
            "context_count": len(self.context_scores),
        }
        
        for category in self.strategies:
            ranking = self.get_ranking(category)
            summary["categories"][category] = {
                "count": len(self.strategies[category]),
                "top_3": ranking[:3],
            }
        
        return summary
    
    def export_scores(self) -> dict:
        """Export all scores for external analysis.
        
        Returns:
            Complete scores dictionary.
        """
        return {
            "strategies": self.strategies,
            "context_scores": self.context_scores,
            "summary": self.get_summary(),
        }
