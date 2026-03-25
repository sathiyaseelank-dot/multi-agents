"""Self-improvement orchestration for the multi-agent system.

This module orchestrates the self-improvement cycle:
- Analyzes improvement trajectory over time
- Identifies convergence patterns
- Generates improvement reports
- Prunes low-value strategies
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .pattern_learner import PatternLearner
from .strategy_scorer import StrategyScorer

logger = logging.getLogger(__name__)


class SelfImprover:
    """Orchestrates self-improvement for the multi-agent system."""
    
    def __init__(
        self,
        pattern_learner: PatternLearner,
        strategy_scorer: StrategyScorer,
        memory_dir: str = "memory",
    ):
        self.pattern_learner = pattern_learner
        self.strategy_scorer = strategy_scorer
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.improvement_log_path = self.memory_dir / "improvement_log.json"
    
    def analyze_improvement_trajectory(self, window_days: int = 30) -> dict:
        """Analyze improvement trajectory over time.
        
        Args:
            window_days: Number of days to analyze.
            
        Returns:
            Trajectory analysis dictionary.
        """
        cutoff = datetime.now() - timedelta(days=window_days)
        
        # Load run history
        run_history = self._load_run_history()
        
        # Filter by date
        recent_runs = [
            run for run in run_history
            if self._parse_timestamp(run.get("timestamp", "")) >= cutoff
        ]
        
        if len(recent_runs) < 3:
            return {
                "status": "insufficient_data",
                "runs_analyzed": len(recent_runs),
                "message": "Need at least 3 runs in the analysis window",
            }
        
        # Compute metrics over time
        metrics = self._compute_trajectory_metrics(recent_runs)
        
        # Determine trend
        trend = self._determine_trend(metrics)
        
        return {
            "status": "analyzed",
            "runs_analyzed": len(recent_runs),
            "window_days": window_days,
            "trend": trend,
            "metrics": metrics,
        }
    
    def _load_run_history(self) -> list[dict]:
        """Load run history from memory store."""
        memory_file = self.memory_dir / "run-memory.json"
        if not memory_file.exists():
            return []
        
        try:
            return json.loads(memory_file.read_text())
        except json.JSONDecodeError:
            return []
    
    def _parse_timestamp(self, ts: str) -> datetime:
        """Parse ISO timestamp string."""
        try:
            return datetime.fromisoformat(ts)
        except (ValueError, TypeError):
            return datetime.min
    
    def _compute_trajectory_metrics(self, runs: list[dict]) -> dict:
        """Compute metrics from run history."""
        if not runs:
            return {}
        
        # Sort by timestamp
        runs = sorted(runs, key=lambda r: self._parse_timestamp(r.get("timestamp", "")))
        
        # Compute rolling averages
        scores = [run.get("final_score", 0) for run in runs]
        success_count = sum(1 for run in runs if run.get("final_score", 0) >= 70)
        
        # Split into first half and second half for trend analysis
        mid = len(runs) // 2
        first_half = runs[:mid]
        second_half = runs[mid:]
        
        first_avg_score = (
            sum(r.get("final_score", 0) for r in first_half) / len(first_half)
            if first_half else 0
        )
        second_avg_score = (
            sum(r.get("final_score", 0) for r in second_half) / len(second_half)
            if second_half else 0
        )
        
        first_success_rate = (
            sum(1 for r in first_half if r.get("final_score", 0) >= 70) / len(first_half)
            if first_half else 0
        )
        second_success_rate = (
            sum(1 for r in second_half if r.get("final_score", 0) >= 70) / len(second_half)
            if second_half else 0
        )
        
        # Repair frequency
        first_repairs = sum(len(r.get("repairs", [])) for r in first_half) / len(first_half) if first_half else 0
        second_repairs = sum(len(r.get("repairs", [])) for r in second_half) / len(second_half) if second_half else 0
        
        return {
            "total_runs": len(runs),
            "overall_avg_score": sum(scores) / len(scores) if scores else 0,
            "overall_success_rate": success_count / len(runs) if runs else 0,
            "first_half": {
                "avg_score": first_avg_score,
                "success_rate": first_success_rate,
                "avg_repairs": first_repairs,
            },
            "second_half": {
                "avg_score": second_avg_score,
                "success_rate": second_success_rate,
                "avg_repairs": second_repairs,
            },
            "score_change": second_avg_score - first_avg_score,
            "success_rate_change": second_success_rate - first_success_rate,
            "repair_change": second_repairs - first_repairs,
        }
    
    def _determine_trend(self, metrics: dict) -> dict:
        """Determine overall trend from metrics."""
        score_change = metrics.get("score_change", 0)
        success_change = metrics.get("success_rate_change", 0)
        repair_change = metrics.get("repair_change", 0)
        
        # Score trend
        if score_change > 10:
            score_trend = "strongly_improving"
        elif score_change > 5:
            score_trend = "improving"
        elif score_change < -10:
            score_trend = "strongly_declining"
        elif score_change < -5:
            score_trend = "declining"
        else:
            score_trend = "stable"
        
        # Repair trend (negative is good - fewer repairs needed)
        if repair_change < -0.5:
            repair_trend = "improving"
        elif repair_change > 0.5:
            repair_trend = "declining"
        else:
            repair_trend = "stable"
        
        # Overall assessment
        positive_signals = sum([
            score_change > 0,
            success_change > 0,
            repair_change < 0,
        ])
        
        if positive_signals >= 2:
            overall = "improving"
        elif positive_signals == 1:
            overall = "mixed"
        else:
            overall = "needs_attention"
        
        return {
            "score_trend": score_trend,
            "repair_trend": repair_trend,
            "overall": overall,
            "positive_signals": positive_signals,
        }
    
    def identify_convergence_patterns(self) -> dict:
        """Identify patterns where the system is converging to stable strategies.
        
        Returns:
            Convergence analysis dictionary.
        """
        # Get strategy rankings
        framework_ranking = self.strategy_scorer.get_ranking("frameworks")
        architecture_ranking = self.strategy_scorer.get_ranking("architectures")
        tool_ranking = self.strategy_scorer.get_ranking("tools")
        
        convergence = {
            "frameworks": [],
            "architectures": [],
            "tools": [],
        }
        
        # Analyze framework convergence
        for item in framework_ranking[:3]:
            trend = self.strategy_scorer.get_improvement_trend(
                "frameworks", item["strategy"]
            )
            confidence = self.strategy_scorer.get_confidence(
                "frameworks", item["strategy"]
            )
            
            if trend["trend"] in ("stable", "improving") and confidence["confidence"] in ("high", "medium"):
                convergence["frameworks"].append({
                    "strategy": item["strategy"],
                    "adjusted_score": item["adjusted_score"],
                    "trend": trend["trend"],
                    "confidence": confidence["confidence"],
                })
        
        # Analyze architecture convergence
        for item in architecture_ranking[:3]:
            trend = self.strategy_scorer.get_improvement_trend(
                "architectures", item["strategy"]
            )
            confidence = self.strategy_scorer.get_confidence(
                "architectures", item["strategy"]
            )
            
            if trend["trend"] in ("stable", "improving") and confidence["confidence"] in ("high", "medium"):
                convergence["architectures"].append({
                    "strategy": item["strategy"],
                    "adjusted_score": item["adjusted_score"],
                    "trend": trend["trend"],
                    "confidence": confidence["confidence"],
                })
        
        # Analyze tool convergence
        for item in tool_ranking[:3]:
            trend = self.strategy_scorer.get_improvement_trend(
                "tools", item["strategy"]
            )
            confidence = self.strategy_scorer.get_confidence(
                "tools", item["strategy"]
            )
            
            if trend["trend"] in ("stable", "improving") and confidence["confidence"] in ("high", "medium"):
                convergence["tools"].append({
                    "strategy": item["strategy"],
                    "adjusted_score": item["adjusted_score"],
                    "trend": trend["trend"],
                    "confidence": confidence["confidence"],
                })
        
        return {
            "converged_strategies": convergence,
            "total_converged": (
                len(convergence["frameworks"]) +
                len(convergence["architectures"]) +
                len(convergence["tools"])
            ),
        }
    
    def generate_improvement_report(self) -> str:
        """Generate a human-readable improvement report.
        
        Returns:
            Markdown-formatted report string.
        """
        trajectory = self.analyze_improvement_trajectory()
        convergence = self.identify_convergence_patterns()
        pattern_summary = self.pattern_learner.get_learning_summary()
        strategy_summary = self.strategy_scorer.get_summary()
        
        lines = [
            "# Self-Improvement Report",
            f"Generated: {datetime.now().isoformat()}",
            "",
            "## Overall Trajectory",
            f"Status: {trajectory.get('status', 'unknown')}",
        ]
        
        if trajectory.get("trend"):
            trend = trajectory["trend"]
            lines.extend([
                f"- Score Trend: {trend.get('score_trend', 'unknown')}",
                f"- Repair Trend: {trend.get('repair_trend', 'unknown')}",
                f"- Overall: {trend.get('overall', 'unknown')}",
            ])
        
        if trajectory.get("metrics"):
            metrics = trajectory["metrics"]
            lines.extend([
                "",
                "## Metrics",
                f"- Total Runs Analyzed: {metrics.get('total_runs', 0)}",
                f"- Overall Avg Score: {metrics.get('overall_avg_score', 0):.1f}",
                f"- Overall Success Rate: {metrics.get('overall_success_rate', 0):.1%}",
                f"- Score Change: {metrics.get('score_change', 0):+.1f}",
            ])
        
        lines.extend([
            "",
            "## Converged Strategies",
            f"Total Converged: {convergence.get('total_converged', 0)}",
        ])
        
        for category in ["frameworks", "architectures", "tools"]:
            strategies = convergence.get("converged_strategies", {}).get(category, [])
            if strategies:
                lines.append(f"\n### {category.title()}")
                for s in strategies:
                    lines.append(
                        f"- **{s['strategy']}**: score={s['adjusted_score']:.2f}, "
                        f"trend={s['trend']}, confidence={s['confidence']}"
                    )
        
        lines.extend([
            "",
            "## Pattern Learning Summary",
            f"- Total Patterns: {pattern_summary.get('total_patterns', 0)}",
            f"- Architecture Patterns: {pattern_summary.get('architecture_patterns', 0)}",
            f"- Failure Patterns: {pattern_summary.get('failure_patterns', 0)}",
            f"- Success Patterns: {pattern_summary.get('success_patterns', 0)}",
        ])
        
        top_frameworks = pattern_summary.get("top_frameworks", [])
        if top_frameworks:
            lines.append("\n### Top Recommended Frameworks")
            for fw in top_frameworks[:5]:
                lines.append(f"- {fw}")
        
        lines.extend([
            "",
            "## Strategy Score Summary",
        ])
        
        for category, data in strategy_summary.get("categories", {}).items():
            lines.append(f"\n### {category.title()}")
            lines.append(f"- Total Strategies: {data.get('count', 0)}")
            top_3 = data.get("top_3", [])
            if top_3:
                lines.append("- Top 3:")
                for s in top_3:
                    lines.append(
                        f"  - {s['strategy']}: {s['adjusted_score']:.2f} "
                        f"({s['successes']} successes, {s['failures']} failures)"
                    )
        
        return "\n".join(lines)
    
    def prune_low_value_strategies(self, min_samples: int = 3, min_score: float = 0.3) -> dict:
        """Prune strategies with consistently poor performance.
        
        Args:
            min_samples: Minimum samples before considering pruning.
            min_score: Minimum adjusted score to retain.
            
        Returns:
            Pruning results dictionary.
        """
        pruned = {
            "frameworks": [],
            "architectures": [],
            "tools": [],
        }
        
        for category in ["frameworks", "architectures", "tools"]:
            ranking = self.strategy_scorer.get_ranking(category, min_samples=1)
            
            for item in ranking:
                if item.get("samples", 0) >= min_samples:
                    if item.get("adjusted_score", 0) < min_score:
                        # Mark for pruning (don't actually delete, just flag)
                        pruned[category].append({
                            "strategy": item["strategy"],
                            "adjusted_score": item["adjusted_score"],
                            "samples": item["samples"],
                            "action": "flagged_for_pruning",
                        })
        
        total_pruned = sum(len(v) for v in pruned.values())
        
        logger.info("Pruned %d low-value strategies", total_pruned)
        
        return {
            "pruned": pruned,
            "total_pruned": total_pruned,
            "thresholds": {
                "min_samples": min_samples,
                "min_score": min_score,
            },
        }
    
    def get_recommendations_for_next_run(self, task_description: str) -> dict:
        """Get recommendations for the next run based on learning.
        
        Args:
            task_description: The upcoming task description.
            
        Returns:
            Recommendations dictionary.
        """
        trajectory = self.analyze_improvement_trajectory()
        convergence = self.identify_convergence_patterns()
        strategy_recs = self.strategy_scorer.get_recommendations(task_description)
        pattern_recs = self.pattern_learner.get_recommended_frameworks(task_description)
        
        return {
            "trajectory_status": trajectory.get("trend", {}).get("overall", "unknown"),
            "converged_strategies": convergence.get("converged_strategies", {}),
            "strategy_recommendations": strategy_recs,
            "framework_recommendations": pattern_recs,
            "learning_hints": self._generate_learning_hints(
                trajectory, convergence, strategy_recs
            ),
        }
    
    def _generate_learning_hints(
        self,
        trajectory: dict,
        convergence: dict,
        strategy_recs: dict,
    ) -> list[str]:
        """Generate actionable hints based on learning."""
        hints = []
        
        # Trajectory-based hints
        trend = trajectory.get("trend", {})
        if trend.get("overall") == "improving":
            hints.append("✓ System is on an improving trajectory - continue current approach")
        elif trend.get("overall") == "needs_attention":
            hints.append("⚠ System performance needs attention - review recent failures")
        
        # Convergence-based hints
        converged = convergence.get("converged_strategies", {})
        if converged.get("frameworks"):
            top_fw = converged["frameworks"][0]
            hints.append(f"✓ Consider {top_fw['strategy']} - highest confidence framework")
        
        # Strategy-based hints
        if strategy_recs.get("frameworks"):
            top_rec = strategy_recs["frameworks"][0]
            hints.append(
                f"✓ Recommended: {top_rec['strategy']} "
                f"(score: {top_rec['adjusted_score']:.2f})"
            )
        
        return hints
