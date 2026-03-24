"""Structured logging for the orchestrator."""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path


def setup_logging(log_dir: str = "logs", level: str = "INFO") -> logging.Logger:
    """Configure structured logging to both file and console."""
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger("orchestrator")
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Prevent duplicate handlers on repeated setup
    if root_logger.handlers:
        return root_logger

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    root_logger.addHandler(console)

    # File handler (session log)
    session_file = log_path / f"session-{datetime.now().strftime('%Y-%m-%d')}.log"
    file_handler = logging.FileHandler(session_file)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    return root_logger


def get_agent_logger(agent_name: str, log_dir: str = "logs") -> logging.Logger:
    """Create a per-agent logger that writes to its own file."""
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    agent_logger = logging.getLogger(f"orchestrator.agent.{agent_name}")

    if not agent_logger.handlers:
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler = logging.FileHandler(log_path / f"agent-{agent_name}.log")
        handler.setFormatter(formatter)
        agent_logger.addHandler(handler)

    return agent_logger
