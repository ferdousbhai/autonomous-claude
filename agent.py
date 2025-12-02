"""
Agent Session Logic
===================

Core agent interaction functions for running autonomous coding sessions.
"""

import time
from pathlib import Path
from typing import Optional

from client import create_client
from progress import print_session_header, print_progress_summary
from prompts import get_initializer_prompt, get_coding_prompt, copy_spec_to_project


# Configuration
AUTO_CONTINUE_DELAY_SECONDS = 3


def run_agent_session(
    project_dir: Path,
    model: str,
    prompt: str,
) -> tuple[str, str]:
    """
    Run a single agent session using Claude Code CLI.

    Args:
        project_dir: Project directory path
        model: Claude model to use
        prompt: The prompt to send

    Returns:
        (status, response_text) where status is:
        - "continue" if agent should continue working
        - "error" if an error occurred
    """
    print("Sending prompt to Claude Code CLI...\n")

    try:
        # Create client and run query
        client = create_client(project_dir, model)
        stdout, stderr = client.query(prompt)

        # Print the response
        if stdout:
            print(stdout)

        if stderr:
            print(f"\n[stderr]: {stderr}")

        print("\n" + "-" * 70 + "\n")
        return "continue", stdout

    except TimeoutError:
        print("Session timed out (10 minutes)")
        return "error", "timeout"
    except Exception as e:
        print(f"Error during agent session: {e}")
        return "error", str(e)


def run_autonomous_agent(
    project_dir: Path,
    model: str,
    max_iterations: Optional[int] = None,
) -> None:
    """
    Run the autonomous agent loop.

    Args:
        project_dir: Directory for the project
        model: Claude model to use
        max_iterations: Maximum number of iterations (None for unlimited)
    """
    print("\n" + "=" * 70)
    print("  AUTONOMOUS CODING AGENT DEMO")
    print("=" * 70)
    print(f"\nProject directory: {project_dir}")
    print(f"Model: {model}")
    if max_iterations:
        print(f"Max iterations: {max_iterations}")
    else:
        print("Max iterations: Unlimited (will run until completion)")
    print()

    # Create project directory
    project_dir.mkdir(parents=True, exist_ok=True)

    # Check if this is a fresh start or continuation
    tests_file = project_dir / "feature_list.json"
    is_first_run = not tests_file.exists()

    if is_first_run:
        print("Fresh start - will use initializer agent")
        print()
        print("=" * 70)
        print("  NOTE: First session takes 10-20+ minutes!")
        print("  The agent is generating 200 detailed test cases.")
        print("  This may appear to hang - it's working.")
        print("=" * 70)
        print()
        # Copy the app spec into the project directory for the agent to read
        copy_spec_to_project(project_dir)
    else:
        print("Continuing existing project")
        print_progress_summary(project_dir)

    # Main loop
    iteration = 0

    while True:
        iteration += 1

        # Check max iterations
        if max_iterations and iteration > max_iterations:
            print(f"\nReached max iterations ({max_iterations})")
            print("To continue, run the script again without --max-iterations")
            break

        # Print session header
        print_session_header(iteration, is_first_run)

        # Choose prompt based on session type
        if is_first_run:
            prompt = get_initializer_prompt()
            is_first_run = False  # Only use initializer once
        else:
            prompt = get_coding_prompt()

        # Run session
        status, response = run_agent_session(project_dir, model, prompt)

        # Handle status
        if status == "continue":
            print(f"\nAgent will auto-continue in {AUTO_CONTINUE_DELAY_SECONDS}s...")
            print_progress_summary(project_dir)
            time.sleep(AUTO_CONTINUE_DELAY_SECONDS)

        elif status == "error":
            print("\nSession encountered an error")
            print("Will retry with a fresh session...")
            time.sleep(AUTO_CONTINUE_DELAY_SECONDS)

        # Small delay between sessions
        if max_iterations is None or iteration < max_iterations:
            print("\nPreparing next session...\n")
            time.sleep(1)

    # Final summary
    print("\n" + "=" * 70)
    print("  SESSION COMPLETE")
    print("=" * 70)
    print(f"\nProject directory: {project_dir}")
    print_progress_summary(project_dir)

    # Print instructions for running the generated application
    print("\n" + "-" * 70)
    print("  TO RUN THE GENERATED APPLICATION:")
    print("-" * 70)
    print(f"\n  cd {project_dir.resolve()}")
    print("  ./init.sh           # Run the setup script")
    print("  # Or manually:")
    print("  npm install && npm run dev")
    print("\n  Then open http://localhost:3000 (or check init.sh for the URL)")
    print("-" * 70)

    print("\nDone!")
