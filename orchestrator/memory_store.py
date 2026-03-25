"""Persistence and retrieval for past orchestration runs."""

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

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

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "prompt": self.prompt,
            "refined_goal": self.refined_goal,
            "errors": self.errors,
            "fixes_applied": self.fixes_applied,
            "final_score": self.final_score,
            "created_at": self.created_at,
        }


class MemoryStore:
    """Stores prior runs and retrieves similar histories for planning."""

    def __init__(self, memory_dir: str = "memory"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.memory_dir / "run-memory.json"

    def add_run(
        self,
        session_id: str,
        prompt: str,
        refined_goal: str,
        errors: list[str],
        fixes_applied: list[dict],
        final_score: int,
    ) -> dict:
        records = self._load_all()
        record = MemoryRecord(
            session_id=session_id,
            prompt=prompt,
            refined_goal=refined_goal,
            errors=errors,
            fixes_applied=fixes_applied,
            final_score=final_score,
            created_at=datetime.now().isoformat(),
        )
        records.append(record.to_dict())
        self.path.write_text(json.dumps(records[-100:], indent=2))
        logger.info("Stored run memory for session %s", session_id)
        return record.to_dict()

    def find_similar_runs(self, prompt: str, limit: int = 3) -> list[dict]:
        prompt_tokens = _tokenize(prompt)
        if not prompt_tokens:
            return []

        scored = []
        for record in self._load_all():
            text = " ".join([record.get("prompt", ""), record.get("refined_goal", "")])
            overlap = prompt_tokens & _tokenize(text)
            if not overlap:
                continue
            score = len(overlap) + int(record.get("final_score", 0) / 25)
            scored.append((score, record))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [record for _, record in scored[:limit]]

    def _load_all(self) -> list[dict]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text())
        except json.JSONDecodeError:
            logger.warning("Run memory is corrupt, ignoring %s", self.path)
            return []
        return data if isinstance(data, list) else []
