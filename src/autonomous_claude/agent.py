"""Agent loop for autonomous coding sessions."""

import json
import shutil
import subprocess
from datetime import datetime
from importlib import resources
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
CLAUDE_SKILLS_DIR = Path.home() / ".claude" / "skills"


def install_bundled_skills() -> None:
    """Install bundled skills to ~/.claude/skills/ if not already present."""
    CLAUDE_SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    # Get the path to bundled skills
    with resources.as_file(resources.files("autonomous_claude") / "skills") as skills_src:
        if not skills_src.exists():
            return

        for skill_dir in skills_src.iterdir():
            if not skill_dir.is_dir():
                continue

            dest_dir = CLAUDE_SKILLS_DIR / skill_dir.name
            if dest_dir.exists():
                continue  # Skip if already installed

            # Copy skill directory
            shutil.copytree(skill_dir, dest_dir)

            # Run setup for playwright-skill
            if skill_dir.name == "playwright-skill":
                package_json = dest_dir / "package.json"
                if package_json.exists():
                    subprocess.run(
                        ["pnpm", "run", "setup"],
                        cwd=dest_dir,
                        capture_output=True,
                    )


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


def run_with_spinner(func, *args, label: str = "Running...", **kwargs):
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

    with ui.Spinner(label):
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

    # Check for removed features (description changed = feature removed + new one added)
    before_descriptions = {f.get("description", "") for f in before}
    after_descriptions = {f.get("description", "") for f in after}
    removed = before_descriptions - after_descriptions
    if removed:
        # Truncate long descriptions in error message
        removed_short = {d[:80] + "..." if len(d) > 80 else d for d in removed}
        return False, f"Features were removed or modified: {removed_short}"

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
    spinner_label: str = "Running...",
    sandbox: bool = True,
) -> float:
    """Run a single agent session. Returns duration in seconds."""
    import time

    log_path = get_log_path(project_dir, session_type)
    start_time = time.time()

    try:
        client = ClaudeCLIClient(project_dir=project_dir, model=model, timeout=timeout, sandbox=sandbox)
        stdout, stderr = run_with_spinner(client.query, prompt, label=spinner_label)

        duration = time.time() - start_time
        write_session_log(log_path, session_type, prompt, stdout, stderr, duration)
        ui.print_output(stdout, stderr)

    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        write_session_log(log_path, session_type, prompt, "", f"TIMEOUT after {timeout}s", duration)
        ui.print_timeout(timeout, duration)
    except Exception as e:
        duration = time.time() - start_time
        write_session_log(log_path, session_type, prompt, "", str(e), duration)
        ui.print_error(e, duration=duration, session_type=session_type)

    return duration


def run_agent_loop(
    project_dir: Path,
    model: Optional[str] = None,
    max_sessions: Optional[int] = None,
    app_spec: Optional[str] = None,
    timeout: int = 1800,
    is_adoption: bool = False,
    is_enhancement: bool = False,
    sandbox: bool = True,
) -> None:
    """Run the autonomous agent loop."""
    project_dir.mkdir(parents=True, exist_ok=True)

    # Create default .mcp.json if it doesn't exist
    mcp_json = project_dir / ".mcp.json"
    if not mcp_json.exists():
        mcp_json.write_text('{\n  "mcpServers": {}\n}\n')

    # Install bundled skills to ~/.claude/skills/
    feature_list = project_dir / "feature_list.json"
    if not feature_list.exists():
        run_with_spinner(install_bundled_skills, label="Installing Claude Code skills...")

    ui.print_header(project_dir, model)

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

    ui.print_separator()

    session_count = 0
    total_run_time = 0.0

    while True:
        if is_project_complete(project_dir):
            break

        session_count += 1

        if max_sessions and session_count > max_sessions:
            ui.print_max_sessions(max_sessions)
            break

        needs_init = not feature_list.exists()

        # Determine which prompt, session type, and spinner label to use
        if needs_enhancement_init:
            prompt = get_enhancement_initializer_prompt()
            session_type = "enhancement_init"
            spinner_label = "Running enhancement initializer..."
            needs_enhancement_init = False  # Only run once
        elif needs_init:
            prompt = get_adoption_initializer_prompt() if is_adoption else get_initializer_prompt()
            session_type = "adoption_init" if is_adoption else "initializer"
            spinner_label = "Running adoption initializer..." if is_adoption else "Running initializer..."
        else:
            prompt = get_coding_prompt()
            session_type = "coding"
            spinner_label = "Running coding agent..."

        # Snapshot features before session
        features_before = load_features(project_dir)
        prev_passing = sum(1 for f in (features_before or []) if f.get("passes"))

        print()  # Empty line before spinner
        duration = run_session(project_dir, model, prompt, timeout, session_type, spinner_label, sandbox)
        total_run_time += duration

        # Validate feature_list.json wasn't tampered with
        features_after = load_features(project_dir)
        is_valid, error = validate_feature_changes(features_before, features_after)
        if not is_valid:
            ui.print_warning(f"Invalid feature_list.json change: {error}")
            if features_before is not None:
                ui.print_warning("Restoring previous feature_list.json")
                save_features(project_dir, features_before)
                features_after = features_before  # Use restored for display

        # Find newly completed features
        before_passing = {f.get("description") for f in (features_before or []) if f.get("passes")}
        newly_completed = [
            f for f in (features_after or [])
            if f.get("passes") and f.get("description") not in before_passing
        ]

        ui.print_session_progress(project_dir, newly_completed, prev_passing, duration, total_run_time)
        ui.print_separator()

        # Check completion before waiting for stop signal
        if is_project_complete(project_dir):
            break

        # Check if user wants to stop (with timeout for keypress)
        if ui.wait_for_stop_signal():
            ui.print_user_stopped()
            return

    ui.print_complete(project_dir, session_count, total_run_time)
