"""Agent loop for autonomous coding sessions."""

import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

from .client import ClaudeCLIClient
from .progress import print_session_header, print_progress_summary
from .prompts import get_initializer_prompt, get_coding_prompt, copy_spec_to_project


SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


def format_elapsed(seconds: int) -> str:
    if seconds < 3600:
        return f"{seconds // 60}:{seconds % 60:02d}"
    return f"{seconds // 3600}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"


def run_with_spinner(func, *args, **kwargs):
    """Run a function while showing a spinner with elapsed time."""
    result = [None]
    exception = [None]

    def target():
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            exception[0] = e

    thread = threading.Thread(target=target)
    thread.start()

    start_time = time.time()
    frame_idx = 0

    while thread.is_alive():
        elapsed = int(time.time() - start_time)
        spinner = SPINNER_FRAMES[frame_idx % len(SPINNER_FRAMES)]
        sys.stdout.write(f"\r{spinner} Running... {format_elapsed(elapsed)}  ")
        sys.stdout.flush()
        frame_idx += 1
        thread.join(timeout=0.1)

    sys.stdout.write("\r" + " " * 30 + "\r")
    sys.stdout.flush()

    if exception[0]:
        raise exception[0]
    return result[0]


def run_session(project_dir: Path, model: str, prompt: str, timeout: int = 600) -> tuple[str, str]:
    """Run a single agent session. Returns (status, response)."""
    try:
        client = ClaudeCLIClient(project_dir=project_dir, model=model, timeout=timeout)
        stdout, stderr = run_with_spinner(client.query, prompt)

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
        print(f"Error: {e}")
        return "error", str(e)


def run_agent_loop(
    project_dir: Path,
    model: str = "claude-sonnet-4-5-20250929",
    max_iterations: Optional[int] = None,
    app_spec: Optional[str] = None,
    timeout: int = 600,
) -> None:
    """Run the autonomous agent loop."""
    print("\n" + "=" * 70)
    print("  AUTONOMOUS CLAUDE")
    print("=" * 70)
    print(f"\nProject: {project_dir}")
    print(f"Model: {model}")
    print(f"Max iterations: {max_iterations or 'unlimited'}\n")

    project_dir.mkdir(parents=True, exist_ok=True)

    feature_list = project_dir / "feature_list.json"

    if not feature_list.exists():
        if app_spec:
            copy_spec_to_project(project_dir, app_spec)
        print("Starting new project - initializer agent will run first\n")
        print("=" * 70)
        print("  NOTE: First session may take 10-20+ minutes")
        print("  The agent is generating detailed test cases.")
        print("=" * 70 + "\n")
    else:
        print("Resuming existing project")
        print_progress_summary(project_dir)

    iteration = 0

    while True:
        iteration += 1

        if max_iterations and iteration > max_iterations:
            print(f"\nReached max iterations ({max_iterations})")
            break

        needs_init = not feature_list.exists()
        print_session_header(iteration, needs_init)

        if needs_init:
            prompt = get_initializer_prompt()
        else:
            prompt = get_coding_prompt()

        status, _ = run_session(project_dir, model, prompt, timeout)

        if status == "continue":
            print("\nAuto-continuing in 3s...")
            print_progress_summary(project_dir)
            time.sleep(3)
        else:
            print("\nSession error - retrying...")
            time.sleep(3)

        if max_iterations is None or iteration < max_iterations:
            print("\nPreparing next session...\n")
            time.sleep(1)

    print("\n" + "=" * 70)
    print("  COMPLETE")
    print("=" * 70)
    print(f"\nProject: {project_dir}")
    print_progress_summary(project_dir)
    print()
