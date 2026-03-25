#!/usr/bin/env python3
"""CLI entry point for the Multi-Agent Orchestrator."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator.logger import setup_logging
from orchestrator.orchestrator import Orchestrator
from __version__ import VERSION_DESCRIPTION


def parse_args():
    parser = argparse.ArgumentParser(
        description="Multi-Agent Orchestration System — AI Development Team OS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py "Build a login system"
  python main.py --file task.txt
  python main.py "Build a REST API" --verbose
  python main.py "Build a login system" --dry-run
        """,
    )
    parser.add_argument(
        "task",
        nargs="?",
        help="Task description (e.g., 'Build a login system')",
    )
    parser.add_argument(
        "--file", "-f",
        help="Read task description from a file",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose (DEBUG) logging",
    )
    parser.add_argument(
        "--log-dir",
        default="logs",
        help="Directory for log files (default: logs)",
    )
    parser.add_argument(
        "--memory-dir",
        default="memory",
        help="Directory for memory/state files (default: memory)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory for generated code output (default: output)",
    )
    parser.add_argument(
        "--resume",
        metavar="SESSION_ID",
        help="Resume a previously interrupted session (e.g. --resume 20260320-101850)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List previous sessions stored in memory/",
    )
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Only run the planning phase (show plan, don't execute workers)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show execution plan without calling any agents (no API calls)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=VERSION_DESCRIPTION,
    )
    return parser.parse_args()


def list_sessions(memory_dir: str) -> None:
    """List previous sessions from memory directory."""
    mem_path = Path(memory_dir)
    if not mem_path.exists():
        print("No sessions found.")
        return

    plans = sorted(mem_path.glob("plan-*.json"), reverse=True)
    if not plans:
        print("No sessions found.")
        return

    print(f"\n  Previous Sessions ({len(plans)}):")
    print("  " + "-" * 60)
    for plan_file in plans:
        try:
            data = json.loads(plan_file.read_text())
            sid = data.get("session_id", "?")
            ts = data.get("timestamp", "?")[:19]
            epic = data.get("plan", {}).get("epic", "Unknown task")
            task_count = len(data.get("plan", {}).get("tasks", []))

            # Check if results exist
            results_file = mem_path / f"results-{sid}.json"
            checkpoint_file = mem_path / f"checkpoint-{sid}.json"
            status = "completed" if results_file.exists() else "incomplete"
            resumable = " (resumable)" if checkpoint_file.exists() and status == "incomplete" else ""

            print(f"    {sid}  {ts}  [{status}{resumable}]")
            print(f"      {epic} ({task_count} tasks)")
        except Exception:
            print(f"    {plan_file.name}  (unreadable)")
    print()


def get_task_description(args) -> str:
    """Get the task description from args or file."""
    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        return path.read_text().strip()

    if args.task:
        return args.task

    # Try reading from stdin if piped
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()

    print("Error: No task provided. Usage: python main.py \"Your task here\"", file=sys.stderr)
    sys.exit(1)


async def main():
    args = parse_args()
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logging(log_dir=args.log_dir, level=log_level)

    if args.list:
        list_sessions(args.memory_dir)
        return

    task_description = "" if args.resume else get_task_description(args)

    orchestrator = Orchestrator(
        log_dir=args.log_dir,
        memory_dir=args.memory_dir,
        output_dir=args.output_dir,
        plan_only=args.plan_only or args.dry_run,
        resume_session_id=args.resume,
    )

    if args.resume:
        result = await orchestrator.resume()
    elif args.dry_run:
        # plan_only=True means Codex runs but workers don't — shows real plan with no code gen
        print("[DRY RUN] Running planner only — no worker agents will be called.\n")
        result = await orchestrator.run(task_description)
    else:
        result = await orchestrator.run(task_description)

    if args.json:
        print(json.dumps(result, indent=2))
    elif result["status"] == "failed":
        print(f"\n  Status: FAILED")
        print(f"  Error: {result.get('error', 'Unknown')}")
        sys.exit(1)
    else:
        print(f"\n  Status: {result['status'].upper()}")
        print(f"  Session: {result['session_id']}")
        if result.get("project_dir"):
            print(f"  Project: {result['project_dir']}")
        if result.get("validation_result"):
            validation_status = "passed" if result["validation_result"].get("success") else "failed"
            print(f"  Validation: {validation_status}")
        if result.get("runtime_result"):
            runtime_status = "passed" if result["runtime_result"].get("success") else "failed"
            print(f"  Runtime: {runtime_status}")


if __name__ == "__main__":
    asyncio.run(main())
