"""Pattern extraction and retrieval for self-learning system.

This module extracts patterns from historical runs:
- Architecture patterns (frameworks, project structure)
- Failure patterns (recurring error types)
- Success patterns (strategies that work well)
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Pattern types
PATTERN_ARCHITECTURE = "architecture"
PATTERN_FAILURE = "failure"
PATTERN_SUCCESS = "success"

# Framework detection patterns
FRAMEWORK_PATTERNS = {
    "flask": [r"flask", r"from flask import", r"Flask\("],
    "fastapi": [r"fastapi", r"from fastapi import", r"FastAPI\("],
    "django": [r"django", r"from django\.", r"django\.conf"],
    "react": [r"react", r"import React", r"from 'react'"],
    "vue": [r"vue", r"import Vue", r"from 'vue'"],
    "sqlalchemy": [r"sqlalchemy", r"from sqlalchemy", r"SQLAlchemy\("],
    "pytest": [r"pytest", r"import pytest", r"def test_"],
    "unittest": [r"unittest", r"import unittest"],
}

# Architecture type detection
ARCHITECTURE_PATTERNS = {
    "layered": ["backend", "frontend", "tests"],
    "monolith": ["app.py", "main.py"],
    "microservices": ["services", "api-gateway"],
    "mvc": ["models", "views", "controllers"],
}


def _compute_pattern_id(pattern_type: str, signature: dict) -> str:
    """Generate a unique ID for a pattern based on its signature."""
    sig_str = json.dumps(signature, sort_keys=True)
    hash_digest = hashlib.sha256(sig_str.encode()).hexdigest()[:12]
    return f"{pattern_type}-{hash_digest}"


def _tokenize(text: str) -> set[str]:
    """Extract meaningful tokens from text."""
    return {token.lower() for token in re.findall(r"[a-zA-Z0-9_]+", text) if len(token) > 2}


def extract_architecture_pattern(run_record: dict) -> Optional[dict]:
    """Extract architecture pattern from a run record.
    
    Args:
        run_record: Dictionary containing run data with project_build, validation, etc.
        
    Returns:
        Pattern dictionary or None if no pattern detected.
    """
    signature = {}
    
    # Extract framework from project build result
    build_result = run_record.get("project_build", {})
    files_created = build_result.get("files_created", [])
    
    # Detect frameworks from file content patterns
    frameworks = []
    project_dir = build_result.get("project_dir", "")
    
    if project_dir:
        for filepath in files_created:
            try:
                full_path = Path(project_dir) / filepath
                if full_path.exists() and full_path.suffix in (".py", ".js", ".jsx", ".ts", ".tsx"):
                    content = full_path.read_text(errors="replace").lower()
                    for framework, patterns in FRAMEWORK_PATTERNS.items():
                        if any(re.search(p, content) for p in patterns):
                            if framework not in frameworks:
                                frameworks.append(framework)
            except Exception:
                continue
    
    # Also check requirements.txt
    requirements_path = Path(project_dir) / "requirements.txt" if project_dir else None
    if requirements_path and requirements_path.exists():
        content = requirements_path.read_text().lower()
        for framework in FRAMEWORK_PATTERNS.keys():
            if framework in content and framework not in frameworks:
                frameworks.append(framework)
    
    if frameworks:
        signature["frameworks"] = sorted(frameworks)
    
    # Detect architecture type from directory structure
    if project_dir:
        root = Path(project_dir)
        for arch_type, markers in ARCHITECTURE_PATTERNS.items():
            if all((root / marker).exists() for marker in markers):
                signature["architecture"] = arch_type
                break
    
    # Detect tools
    tools = []
    if any("test" in f for f in files_created):
        tools.append("testing")
    if any("requirements.txt" in f for f in files_created):
        tools.append("pip")
    
    if tools:
        signature["tools"] = sorted(tools)
    
    if not signature:
        return None
    
    success = run_record.get("runtime", {}).get("success", False)
    if not success:
        success = run_record.get("validation", {}).get("success", False)
    
    score = run_record.get("evaluation", {}).get("score", 0) if run_record.get("evaluation") else 0
    
    return {
        "pattern_id": _compute_pattern_id(PATTERN_ARCHITECTURE, signature),
        "pattern_type": PATTERN_ARCHITECTURE,
        "signature": signature,
        "success": success,
        "score": score,
        "session_id": run_record.get("session_id", ""),
        "timestamp": run_record.get("timestamp", datetime.now().isoformat()),
    }


def extract_failure_pattern(run_record: dict) -> Optional[dict]:
    """Extract failure pattern from a run record.
    
    Args:
        run_record: Dictionary containing run data with errors, repairs, etc.
        
    Returns:
        Pattern dictionary or None if no failure detected.
    """
    # Check for validation failures
    validation = run_record.get("validation", {})
    runtime = run_record.get("runtime", {})
    
    errors = []
    error_types = []
    
    if validation and not validation.get("success"):
        for error in validation.get("errors", []):
            errors.append(error.get("message", ""))
            error_types.append(error.get("kind", "unknown"))
    
    if runtime and not runtime.get("success"):
        for error in runtime.get("errors", []):
            errors.append(error)
            if "import" in error.lower():
                error_types.append("import")
            elif "syntax" in error.lower():
                error_types.append("syntax")
            else:
                error_types.append("runtime")
    
    # Check repair history for patterns
    repairs = run_record.get("repairs", [])
    repair_types = [r.get("error_type", "unknown") for r in repairs]
    
    if not errors and not repairs:
        return None
    
    # Build signature from error types
    signature = {
        "error_types": sorted(set(error_types)),
        "repair_types": sorted(set(repair_types)),
    }
    
    # Extract common error keywords
    all_error_text = " ".join(errors).lower()
    keywords = set()
    for keyword in ["import", "syntax", "module", "dependency", "timeout", "connection", "auth"]:
        if keyword in all_error_text:
            keywords.add(keyword)
    
    if keywords:
        signature["keywords"] = sorted(keywords)
    
    return {
        "pattern_id": _compute_pattern_id(PATTERN_FAILURE, signature),
        "pattern_type": PATTERN_FAILURE,
        "signature": signature,
        "errors": errors[:5],  # Limit stored errors
        "repair_count": len(repairs),
        "session_id": run_record.get("session_id", ""),
        "timestamp": run_record.get("timestamp", datetime.now().isoformat()),
    }


def extract_success_pattern(run_record: dict) -> Optional[dict]:
    """Extract success pattern from a run record.
    
    Args:
        run_record: Dictionary containing run data with positive outcomes.
        
    Returns:
        Pattern dictionary or None if not a successful run.
    """
    validation = run_record.get("validation", {})
    runtime = run_record.get("runtime", {})
    evaluation = run_record.get("evaluation", {})
    
    # Check if run was successful
    is_successful = (
        validation.get("success", False) and
        runtime.get("success", False)
    )
    
    if not is_successful:
        return None
    
    # Extract success factors
    signature = {}
    
    # High evaluation score indicates success pattern
    score = evaluation.get("score", 0)
    if score >= 75:
        signature["high_score"] = True
    
    # No repairs needed indicates clean generation
    repairs = run_record.get("repairs", [])
    if not repairs:
        signature["no_repairs"] = True
    
    # Extract architecture pattern
    arch_pattern = extract_architecture_pattern(run_record)
    if arch_pattern:
        signature["architecture"] = arch_pattern.get("signature", {})
    
    if not signature:
        return None
    
    return {
        "pattern_id": _compute_pattern_id(PATTERN_SUCCESS, signature),
        "pattern_type": PATTERN_SUCCESS,
        "signature": signature,
        "score": score,
        "session_id": run_record.get("session_id", ""),
        "timestamp": run_record.get("timestamp", datetime.now().isoformat()),
    }


class PatternLearner:
    """Manages pattern extraction, storage, and retrieval."""
    
    def __init__(self, memory_dir: str = "memory"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.patterns_path = self.memory_dir / "patterns.json"
        self._pattern_cache: dict[str, list[dict]] = defaultdict(list)
        self._load_patterns()
    
    def _load_patterns(self):
        """Load patterns from disk."""
        if not self.patterns_path.exists():
            return
        
        try:
            data = json.loads(self.patterns_path.read_text())
            for pattern in data:
                pattern_type = pattern.get("pattern_type", "unknown")
                self._pattern_cache[pattern_type].append(pattern)
            logger.info("Loaded %d patterns from disk", sum(len(v) for v in self._pattern_cache.values()))
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("Failed to load patterns: %s", e)
    
    def _save_patterns(self):
        """Save patterns to disk."""
        all_patterns = []
        for patterns in self._pattern_cache.values():
            all_patterns.extend(patterns)
        
        # Keep only last 500 patterns to prevent unbounded growth
        all_patterns = all_patterns[-500:]
        
        self.patterns_path.write_text(json.dumps(all_patterns, indent=2))
    
    def record_run(self, run_record: dict) -> dict:
        """Extract and store patterns from a run record.
        
        Args:
            run_record: Complete run record with all artifacts.
            
        Returns:
            Dictionary with counts of patterns stored.
        """
        stored = {
            "architecture": 0,
            "failure": 0,
            "success": 0,
        }
        
        # Extract architecture pattern
        arch_pattern = extract_architecture_pattern(run_record)
        if arch_pattern:
            self._pattern_cache[PATTERN_ARCHITECTURE].append(arch_pattern)
            stored["architecture"] = 1
        
        # Extract failure pattern
        failure_pattern = extract_failure_pattern(run_record)
        if failure_pattern:
            self._pattern_cache[PATTERN_FAILURE].append(failure_pattern)
            stored["failure"] = 1
        
        # Extract success pattern
        success_pattern = extract_success_pattern(run_record)
        if success_pattern:
            self._pattern_cache[PATTERN_SUCCESS].append(success_pattern)
            stored["success"] = 1
        
        self._save_patterns()
        logger.info("Recorded patterns from run %s: %s", run_record.get("session_id", ""), stored)
        return stored
    
    def get_similar_architecture_patterns(self, task_description: str, limit: int = 5) -> list[dict]:
        """Get architecture patterns similar to the task description.
        
        Args:
            task_description: The user's task description.
            limit: Maximum number of patterns to return.
            
        Returns:
            List of similar architecture patterns, sorted by relevance.
        """
        task_tokens = _tokenize(task_description)
        patterns = self._pattern_cache.get(PATTERN_ARCHITECTURE, [])
        
        scored = []
        for pattern in patterns:
            signature = pattern.get("signature", {})
            
            # Score based on framework matches
            frameworks = signature.get("frameworks", [])
            framework_match = sum(1 for f in frameworks if f in task_tokens)
            
            # Score based on success
            success_bonus = 10 if pattern.get("success", False) else 0
            score_bonus = pattern.get("score", 0) // 25
            
            total_score = framework_match * 5 + success_bonus + score_bonus
            
            if total_score > 0:
                scored.append((total_score, pattern))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return [pattern for _, pattern in scored[:limit]]
    
    def get_common_failures(self, keywords: Optional[list[str]] = None, limit: int = 5) -> list[dict]:
        """Get common failure patterns, optionally filtered by keywords.
        
        Args:
            keywords: Optional keywords to filter failures.
            limit: Maximum number of patterns to return.
            
        Returns:
            List of failure patterns, sorted by frequency.
        """
        patterns = self._pattern_cache.get(PATTERN_FAILURE, [])
        
        if keywords:
            keyword_set = set(k.lower() for k in keywords)
            filtered = []
            for pattern in patterns:
                sig = pattern.get("signature", {})
                pattern_keywords = set(sig.get("keywords", []))
                if pattern_keywords & keyword_set:
                    filtered.append(pattern)
            patterns = filtered
        
        # Group by signature and count
        signature_counts = defaultdict(list)
        for pattern in patterns:
            sig_key = json.dumps(pattern.get("signature", {}), sort_keys=True)
            signature_counts[sig_key].append(pattern)
        
        # Sort by frequency
        grouped = [
            {"count": len(ps), "latest": ps[-1], "all": ps}
            for ps in signature_counts.values()
        ]
        grouped.sort(key=lambda x: x["count"], reverse=True)
        
        return [g["latest"] for g in grouped[:limit]]
    
    def get_success_patterns(self, min_score: int = 70, limit: int = 5) -> list[dict]:
        """Get patterns from successful runs.
        
        Args:
            min_score: Minimum evaluation score to consider.
            limit: Maximum number of patterns to return.
            
        Returns:
            List of success patterns, sorted by score.
        """
        patterns = self._pattern_cache.get(PATTERN_SUCCESS, [])
        
        # Filter by score
        filtered = [p for p in patterns if p.get("score", 0) >= min_score]
        
        # Sort by score
        filtered.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        return filtered[:limit]
    
    def get_recommended_frameworks(self, task_description: str) -> list[str]:
        """Get framework recommendations based on historical success.
        
        Args:
            task_description: The user's task description.
            
        Returns:
            List of recommended frameworks, sorted by success rate.
        """
        patterns = self._pattern_cache.get(PATTERN_ARCHITECTURE, [])
        
        # Aggregate success rate per framework
        framework_stats = defaultdict(lambda: {"successes": 0, "total": 0})
        
        for pattern in patterns:
            signature = pattern.get("signature", {})
            frameworks = signature.get("frameworks", [])
            success = pattern.get("success", False)
            
            for framework in frameworks:
                framework_stats[framework]["total"] += 1
                if success:
                    framework_stats[framework]["successes"] += 1
        
        # Calculate success rates
        recommendations = []
        for framework, stats in framework_stats.items():
            if stats["total"] >= 2:  # Minimum sample size
                success_rate = stats["successes"] / stats["total"]
                recommendations.append((framework, success_rate, stats["total"]))
        
        # Sort by success rate (with minimum sample size bias)
        recommendations.sort(key=lambda x: (x[1], x[2]), reverse=True)
        
        return [fw for fw, _, _ in recommendations[:5]]
    
    def compute_pattern_frequency(self, pattern_type: str) -> dict[str, int]:
        """Compute frequency of patterns by type.
        
        Args:
            pattern_type: Type of pattern to analyze.
            
        Returns:
            Dictionary mapping pattern signatures to their frequency.
        """
        patterns = self._pattern_cache.get(pattern_type, [])
        
        frequency = defaultdict(int)
        for pattern in patterns:
            sig_key = json.dumps(pattern.get("signature", {}), sort_keys=True)
            frequency[sig_key] += 1
        
        return dict(frequency)
    
    def get_learning_summary(self) -> dict:
        """Get a summary of all learned patterns.
        
        Returns:
            Dictionary with pattern statistics and insights.
        """
        arch_patterns = self._pattern_cache.get(PATTERN_ARCHITECTURE, [])
        failure_patterns = self._pattern_cache.get(PATTERN_FAILURE, [])
        success_patterns = self._pattern_cache.get(PATTERN_SUCCESS, [])
        
        # Compute framework success rates
        framework_stats = defaultdict(lambda: {"successes": 0, "total": 0})
        for pattern in arch_patterns:
            sig = pattern.get("signature", {})
            for fw in sig.get("frameworks", []):
                framework_stats[fw]["total"] += 1
                if pattern.get("success", False):
                    framework_stats[fw]["successes"] += 1
        
        framework_rates = {}
        for fw, stats in framework_stats.items():
            if stats["total"] > 0:
                framework_rates[fw] = stats["successes"] / stats["total"]
        
        return {
            "total_patterns": len(arch_patterns) + len(failure_patterns) + len(success_patterns),
            "architecture_patterns": len(arch_patterns),
            "failure_patterns": len(failure_patterns),
            "success_patterns": len(success_patterns),
            "framework_success_rates": framework_rates,
            "most_common_failures": self.get_common_failures(limit=3),
            "top_frameworks": self.get_recommended_frameworks(""),
        }
