"""Tests for parsing.validator."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from parsing.validator import validate_review_feedback


class TestValidateReviewFeedback:
    def test_valid_review_feedback(self):
        issues = validate_review_feedback({
            "issues": ["missing task"],
            "suggestions": ["add tests"],
            "approval": False,
            "confidence": 0.55,
        })
        assert issues == []

    def test_invalid_review_feedback(self):
        issues = validate_review_feedback({
            "issues": "bad",
            "suggestions": [],
            "approval": "false",
            "confidence": 2,
        })
        assert "Review feedback 'issues' must be a list of strings" in issues
        assert "Review feedback 'approval' must be a boolean" in issues
        assert "Review feedback 'confidence' must be between 0.0 and 1.0" in issues
