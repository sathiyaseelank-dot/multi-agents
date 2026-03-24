"""Load agent configuration from agents.yaml."""

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Default config path relative to project root
DEFAULT_CONFIG = Path(__file__).parent.parent / "config" / "agents.yaml"


def load_agent_configs(config_path: Optional[str] = None) -> dict:
    """Load agent configs from YAML. Returns dict keyed by agent name.

    Falls back to hardcoded defaults if YAML is unavailable.
    """
    path = Path(config_path) if config_path else DEFAULT_CONFIG

    if path.exists():
        try:
            import yaml
            data = yaml.safe_load(path.read_text())
            agents = data.get("agents", {})
            global_cfg = data.get("global", {})
            logger.info(f"Loaded {len(agents)} agent configs from {path}")
            return _normalize(agents, global_cfg)
        except ImportError:
            logger.debug("pyyaml not installed, using defaults")
        except Exception as e:
            logger.warning(f"Failed to load {path}: {e}, using defaults")

    return _defaults()


def _normalize(agents: dict, global_cfg: dict) -> dict:
    """Normalize YAML agent entries into a consistent dict format."""
    result = {}
    for key, cfg in agents.items():
        env_vars = {}
        for ev in cfg.get("env_vars", []):
            if isinstance(ev, dict) and "name" in ev:
                env_vars[ev["name"]] = ev.get("value", "")

        # Allow env var overrides for model
        model_env = os.environ.get(f"{key.upper()}_MODEL", "")
        if model_env and key != "codex":
            if key == "gemini":
                extra_args = ["-m", model_env]
            else:
                extra_args = ["--model", model_env]
        else:
            extra_args = []

        result[key] = {
            "name": cfg.get("name", key),
            "role": cfg.get("role", key),
            "command": cfg.get("command", key),
            "subcommand": cfg.get("subcommand"),
            "args": cfg.get("args", []) + extra_args,
            "timeout_seconds": cfg.get(
                "timeout_seconds",
                global_cfg.get("default_timeout", 120),
            ),
            "retry_count": cfg.get(
                "retry_count",
                global_cfg.get("default_retry_count", 2),
            ),
            "retry_backoff_seconds": cfg.get("retry_backoff_seconds", 5),
            "env_vars": env_vars,
        }
    return result


def _defaults() -> dict:
    """Hardcoded fallback configs (no YAML needed)."""
    return {
        "codex": {
            "name": "codex", "role": "planner",
            "command": "codex", "subcommand": "exec", "args": [],
            "timeout_seconds": 120, "retry_count": 3,
            "retry_backoff_seconds": 2, "env_vars": {},
        },
        "opencode": {
            "name": "opencode", "role": "backend",
            "command": "opencode", "subcommand": "run", "args": [],
            "timeout_seconds": 180, "retry_count": 2,
            "retry_backoff_seconds": 5, "env_vars": {},
        },
        "gemini": {
            "name": "gemini", "role": "frontend",
            "command": "gemini", "subcommand": None, "args": [],
            "timeout_seconds": 300, "retry_count": 2,
            "retry_backoff_seconds": 5, "env_vars": {},
        },
        "kilo": {
            "name": "kilo", "role": "testing",
            "command": "kilo", "subcommand": "run", "args": ["--auto"],
            "timeout_seconds": 180, "retry_count": 2,
            "retry_backoff_seconds": 5, "env_vars": {},
        },
    }
