"""Agent loop for autonomous coding sessions."""

import subprocess
from pathlib import Path
from typing import Optional

from .client import ClaudeCLIClient
from .prompts import get_initializer_prompt, get_coding_prompt, copy_spec_to_project
from . import ui


def run_with_spinner(func, *args, **kwargs):
    """Run a function while showing a spinner."""
    import threading

    result = [None]
    exception = [None]

    def target():
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            exception[0] = e

    thread = threading.Thread(target=target)

    with ui.Spinner():
        thread.start()
        while thread.is_alive():
            thread.join(timeout=0.1)

    if exception[0]:
        raise exception[0]
    return result[0]


def run_session(project_dir: Path, model: Optional[str], prompt: str, timeout: int = 1800) -> tuple[str, str]:
    """Run a single agent session. Returns (status, response)."""
    try:
        client = ClaudeCLIClient(project_dir=project_dir, model=model, timeout=timeout)
        stdout, stderr = run_with_spinner(client.query, prompt)

        ui.print_output(stdout, stderr)
        return "continue", stdout

    except subprocess.TimeoutExpired:
        ui.print_timeout(timeout)
        return "error", "timeout"
    except Exception as e:
        ui.print_error(e)
        return "error", str(e)


def run_agent_loop(
    project_dir: Path,
    model: Optional[str] = None,
    max_iterations: Optional[int] = None,
    app_spec: Optional[str] = None,
    timeout: int = 1800,
) -> None:
    """Run the autonomous agent loop."""
    project_dir.mkdir(parents=True, exist_ok=True)

    ui.print_header(project_dir, model, max_iterations)

    feature_list = project_dir / "feature_list.json"

    if not feature_list.exists():
        if app_spec:
            copy_spec_to_project(project_dir, app_spec)
        ui.print_new_project_notice()
    else:
        ui.print_resuming(project_dir)

    iteration = 0

    while True:
        iteration += 1

        if max_iterations and iteration > max_iterations:
            ui.print_max_iterations(max_iterations)
            break

        needs_init = not feature_list.exists()
        ui.print_session_header(needs_init)

        if needs_init:
            prompt = get_initializer_prompt()
        else:
            prompt = get_coding_prompt()

        status, _ = run_session(project_dir, model, prompt, timeout)

        ui.print_progress(project_dir)

    ui.print_complete(project_dir)
