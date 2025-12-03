"""Agent loop for autonomous coding sessions."""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .client import ClaudeCLIClient
from .prompts import (
    get_initializer_prompt,
    get_coding_prompt,
    get_adoption_initializer_prompt,
    get_enhancement_initializer_prompt,
    copy_spec_to_project,
)
from . import ui


LOGS_DIR = ".autonomous-claude/logs"


def get_log_path(project_dir: Path, session_type: str) -> Path:
    """Get the log file path for a session."""
    logs_dir = project_dir / LOGS_DIR
    logs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return logs_dir / f"{timestamp}_{session_type}.log"


def write_session_log(
    log_path: Path,
    session_type: str,
    prompt: str,
    stdout: str,
    stderr: str,
    duration_seconds: float,
) -> None:
    """Write session output to a log file."""
    with open(log_path, "w") as f:
        f.write(f"Session Type: {session_type}\n")
        f.write(f"Timestamp: {datetime.now().isoformat()}\n")
        f.write(f"Duration: {duration_seconds:.1f}s\n")
        f.write("\n" + "=" * 70 + "\n")
        f.write("PROMPT:\n")
        f.write("=" * 70 + "\n\n")
        f.write(prompt)
        f.write("\n\n" + "=" * 70 + "\n")
        f.write("STDOUT:\n")
        f.write("=" * 70 + "\n\n")
        f.write(stdout or "(empty)")
        if stderr:
            f.write("\n\n" + "=" * 70 + "\n")
            f.write("STDERR:\n")
            f.write("=" * 70 + "\n\n")
            f.write(stderr)


def run_with_spinner(func, *args, **kwargs):
    """Run a function while showing a spinner."""
    import threading

    result: list[Any] = [None]
    exception: list[Optional[Exception]] = [None]

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


def is_project_complete(project_dir: Path) -> bool:
    """Check if all features in feature_list.json are passing."""
    feature_list = project_dir / "feature_list.json"
    if not feature_list.exists():
        return False

    try:
        features = json.loads(feature_list.read_text())
        return all(f.get("passes", False) for f in features)
    except (json.JSONDecodeError, TypeError):
        return False


def load_features(project_dir: Path) -> list[dict] | None:
    """Load feature_list.json, return None if doesn't exist or invalid."""
    feature_list = project_dir / "feature_list.json"
    if not feature_list.exists():
        return None
    try:
        return json.loads(feature_list.read_text())
    except (json.JSONDecodeError, TypeError):
        return None


def validate_feature_changes(before: list[dict] | None, after: list[dict] | None) -> tuple[bool, str]:
    """
    Validate that feature_list.json changes follow the rules:
    - Features cannot be removed
    - Feature descriptions cannot be modified

    Returns (is_valid, error_message).
    """
    if before is None:
        return True, ""  # First creation is always valid

    if after is None:
        return False, "feature_list.json was deleted or corrupted"

    # Build lookup by feature name
    before_by_name = {f.get("feature", ""): f for f in before}
    after_by_name = {f.get("feature", ""): f for f in after}

    # Check for removed features
    removed = set(before_by_name.keys()) - set(after_by_name.keys())
    if removed:
        return False, f"Features were removed: {removed}"

    # Check each original feature
    for name, before_feat in before_by_name.items():
        after_feat = after_by_name.get(name)
        if not after_feat:
            continue  # Already caught above

        # Check description wasn't modified
        if before_feat.get("description") != after_feat.get("description"):
            return False, f"Feature description was modified: {name}"

    return True, ""


def save_features(project_dir: Path, features: list[dict]) -> None:
    """Save features back to feature_list.json."""
    feature_list = project_dir / "feature_list.json"
    feature_list.write_text(json.dumps(features, indent=2))


def run_session(
    project_dir: Path,
    model: Optional[str],
    prompt: str,
    timeout: int = 1800,
    session_type: str = "session",
    verbose: bool = False,
) -> tuple[str, str]:
    """Run a single agent session. Returns (status, response)."""
    import time

    log_path = get_log_path(project_dir, session_type)
    start_time = time.time()

    try:
        client = ClaudeCLIClient(project_dir=project_dir, model=model, timeout=timeout)

        if verbose:
            stdout, stderr = client.query_streaming(prompt)
        else:
            stdout, stderr = run_with_spinner(client.query, prompt)

        duration = time.time() - start_time
        write_session_log(log_path, session_type, prompt, stdout, stderr, duration)

        if not verbose:
            ui.print_output(stdout, stderr)
        return "continue", stdout

    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        write_session_log(log_path, session_type, prompt, "", f"TIMEOUT after {timeout}s", duration)
        ui.print_timeout(timeout)
        return "error", "timeout"
    except Exception as e:
        duration = time.time() - start_time
        write_session_log(log_path, session_type, prompt, "", str(e), duration)
        ui.print_error(e)
        return "error", str(e)


def run_agent_loop(
    project_dir: Path,
    model: Optional[str] = None,
    max_iterations: Optional[int] = None,
    app_spec: Optional[str] = None,
    timeout: int = 1800,
    is_adoption: bool = False,
    is_enhancement: bool = False,
    verbose: bool = False,
) -> None:
    """Run the autonomous agent loop."""
    project_dir.mkdir(parents=True, exist_ok=True)

    ui.print_header(project_dir, model, max_iterations)

    feature_list = project_dir / "feature_list.json"

    # For enhancement mode, we need to run enhancement initializer first
    needs_enhancement_init = is_enhancement

    if not feature_list.exists():
        if app_spec:
            copy_spec_to_project(project_dir, app_spec)
        if is_adoption:
            ui.print_adoption_notice()
        else:
            ui.print_new_project_notice()
    elif is_enhancement:
        if app_spec:
            copy_spec_to_project(project_dir, app_spec)
        ui.print_enhancement_notice()
    else:
        ui.print_resuming(project_dir)

    iteration = 0

    while True:
        if is_project_complete(project_dir):
            break

        iteration += 1

        if max_iterations and iteration > max_iterations:
            ui.print_max_iterations(max_iterations)
            break

        needs_init = not feature_list.exists()

        # Determine which prompt and session type to use
        if needs_enhancement_init:
            ui.print_session_header(is_initializer=True, is_enhancement=True)
            prompt = get_enhancement_initializer_prompt()
            session_type = "enhancement_init"
            needs_enhancement_init = False  # Only run once
        elif needs_init:
            ui.print_session_header(is_initializer=True, is_adoption=is_adoption)
            prompt = get_adoption_initializer_prompt() if is_adoption else get_initializer_prompt()
            session_type = "adoption_init" if is_adoption else "initializer"
        else:
            ui.print_session_header(is_initializer=False)
            prompt = get_coding_prompt()
            session_type = "coding"

        # Snapshot features before session
        features_before = load_features(project_dir)

        _, _ = run_session(project_dir, model, prompt, timeout, session_type, verbose)

        # Validate feature_list.json wasn't tampered with
        features_after = load_features(project_dir)
        is_valid, error = validate_feature_changes(features_before, features_after)
        if not is_valid:
            ui.print_warning(f"Invalid feature_list.json change: {error}")
            if features_before is not None:
                ui.print_warning("Restoring previous feature_list.json")
                save_features(project_dir, features_before)

        ui.print_progress(project_dir)

    ui.print_complete(project_dir)
