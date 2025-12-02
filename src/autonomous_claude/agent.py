"""
Agent Session Logic
===================

Core agent loop for running autonomous coding sessions.
"""

import subprocess
import time
from pathlib import Path
from typing import Optional

from .client import ClaudeCLIClient
from .progress import print_session_header, print_progress_summary
from .prompts import get_initializer_prompt, get_coding_prompt, copy_spec_to_project


AUTO_CONTINUE_DELAY_SECONDS = 3


def run_session(
    project_dir: Path,
    model: str,
    prompt: str,
    timeout: int = 600,
) -> tuple[str, str]:
    """
    Run a single agent session.

    Returns:
        (status, response) where status is "continue" or "error"
    """
    print("Sending prompt to Claude Code CLI...\n")

    try:
        client = ClaudeCLIClient(
            project_dir=project_dir,
            model=model,
            timeout=timeout,
        )
        stdout, stderr = client.query(prompt)

        if stdout:
            print(stdout)
        if stderr:
            print(f"\n[stderr]: {stderr}")

        print("\n" + "-" * 70 + "\n")
        return "continue", stdout

    except subprocess.TimeoutExpired:
        print(f"Session timed out ({timeout}s)")
        return "error", "timeout"
    except Exception as e:
        print(f"Error during agent session: {e}")
        return "error", str(e)


def run_agent_loop(
    project_dir: Path,
    model: str = "claude-sonnet-4-5-20250929",
    max_iterations: Optional[int] = None,
    app_spec: Optional[str] = None,
    timeout: int = 600,
) -> None:
    """
    Run the autonomous agent loop.

    Args:
        project_dir: Directory for the project
        model: Claude model to use
        max_iterations: Maximum iterations (None for unlimited)
        app_spec: App specification content (for new projects)
        timeout: Timeout per session in seconds
    """
    print("\n" + "=" * 70)
    print("  AUTONOMOUS CLAUDE")
    print("=" * 70)
    print(f"\nProject: {project_dir}")
    print(f"Model: {model}")
    print(f"Max iterations: {max_iterations or 'unlimited'}")
    print()

    project_dir.mkdir(parents=True, exist_ok=True)

    # Check if continuing or starting fresh
    feature_list = project_dir / "feature_list.json"
    is_first_run = not feature_list.exists()

    if is_first_run:
        if app_spec:
            copy_spec_to_project(project_dir, app_spec)
        print("Starting new project - initializer agent will run first")
        print()
        print("=" * 70)
        print("  NOTE: First session may take 10-20+ minutes")
        print("  The agent is generating detailed test cases.")
        print("=" * 70)
        print()
    else:
        print("Resuming existing project")
        print_progress_summary(project_dir)

    iteration = 0

    while True:
        iteration += 1

        if max_iterations and iteration > max_iterations:
            print(f"\nReached max iterations ({max_iterations})")
            break

        print_session_header(iteration, is_first_run)

        if is_first_run:
            prompt = get_initializer_prompt()
            is_first_run = False
        else:
            prompt = get_coding_prompt()

        status, response = run_session(project_dir, model, prompt, timeout)

        if status == "continue":
            print(f"\nAuto-continuing in {AUTO_CONTINUE_DELAY_SECONDS}s...")
            print_progress_summary(project_dir)
            time.sleep(AUTO_CONTINUE_DELAY_SECONDS)
        elif status == "error":
            print("\nSession error - retrying with fresh session...")
            time.sleep(AUTO_CONTINUE_DELAY_SECONDS)

        if max_iterations is None or iteration < max_iterations:
            print("\nPreparing next session...\n")
            time.sleep(1)

    # Final summary
    print("\n" + "=" * 70)
    print("  COMPLETE")
    print("=" * 70)
    print(f"\nProject: {project_dir}")
    print_progress_summary(project_dir)
    print()
