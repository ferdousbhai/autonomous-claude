"""Agent loop for autonomous coding sessions."""

import json
import shutil
import subprocess
import threading
import time
from datetime import datetime
from importlib import resources
from pathlib import Path

from .client import ClaudeCLIClient
from .prompts import (
    get_initializer_prompt, get_coding_prompt,
    get_adoption_initializer_prompt, get_enhancement_initializer_prompt,
    copy_spec_to_project,
)
from . import ui
from .config import AUTONOMOUS_CLAUDE_DIR, LOGS_DIR, FEATURES_FILE, SPEC_FILE

CLAUDE_SKILLS_DIR = Path.home() / ".claude" / "skills"


def install_bundled_skills() -> None:
    """Install bundled skills to ~/.claude/skills/."""
    CLAUDE_SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    with resources.as_file(resources.files("autonomous_claude") / "skills") as skills_src:
        if not skills_src.exists():
            return

        for skill_dir in skills_src.iterdir():
            if not skill_dir.is_dir():
                continue
            dest = CLAUDE_SKILLS_DIR / skill_dir.name
            if dest.exists():
                continue
            shutil.copytree(skill_dir, dest)
            if skill_dir.name == "playwright-skill" and (dest / "package.json").exists():
                subprocess.run(["pnpm", "run", "setup"], cwd=dest, capture_output=True)


def run_with_spinner(func, *args, label: str = "Running...", **kwargs):
    """Run function with spinner, return result."""
    result, error = [None], [None]

    def target():
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            error[0] = e

    thread = threading.Thread(target=target)
    with ui.Spinner(label):
        thread.start()
        while thread.is_alive():
            thread.join(0.1)

    if error[0]:
        raise error[0]
    return result[0]


def load_features(project_dir: Path) -> list[dict] | None:
    """Load features.json, return None if missing/invalid."""
    path = project_dir / FEATURES_FILE
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, TypeError):
        return None


def save_features(project_dir: Path, features: list[dict]) -> None:
    (project_dir / FEATURES_FILE).write_text(json.dumps(features, indent=2))


def is_complete(project_dir: Path) -> bool:
    features = load_features(project_dir)
    return bool(features and all(f.get("passes") for f in features))


def validate_changes(before: list[dict] | None, after: list[dict] | None) -> tuple[bool, str]:
    """Validate features weren't removed or modified."""
    if before is None:
        return True, ""
    if after is None:
        return False, "features.json deleted"

    before_desc = {f.get("description", "") for f in before}
    after_desc = {f.get("description", "") for f in after}
    removed = before_desc - after_desc
    if removed:
        return False, f"Features removed: {list(removed)[:3]}"
    return True, ""


def write_log(path: Path, session_type: str, prompt: str, stdout: str, stderr: str, duration: float) -> None:
    with open(path, "w") as f:
        f.write(f"Type: {session_type}\nTime: {datetime.now().isoformat()}\nDuration: {duration:.1f}s\n")
        f.write(f"\n{'='*60}\nPROMPT:\n{'='*60}\n{prompt}\n")
        f.write(f"\n{'='*60}\nOUTPUT:\n{'='*60}\n{stdout or '(empty)'}\n")
        if stderr:
            f.write(f"\n{'='*60}\nSTDERR:\n{'='*60}\n{stderr}\n")


def run_session(project_dir: Path, model: str | None, prompt: str, timeout: int,
                session_type: str, spinner_label: str, sandbox: bool) -> float:
    """Run single session, return duration."""
    logs_dir = project_dir / LOGS_DIR
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{session_type}.log"

    start = time.time()
    try:
        client = ClaudeCLIClient(project_dir=project_dir, model=model, timeout=timeout, sandbox=sandbox)
        stdout, stderr = run_with_spinner(client.query, prompt, label=spinner_label)
        duration = time.time() - start
        write_log(log_path, session_type, prompt, stdout, stderr, duration)
        ui.print_output(stdout, stderr)
    except subprocess.TimeoutExpired:
        duration = time.time() - start
        write_log(log_path, session_type, prompt, "", f"TIMEOUT after {timeout}s", duration)
        ui.print_timeout(timeout, duration)
    except Exception as e:
        duration = time.time() - start
        write_log(log_path, session_type, prompt, "", str(e), duration)
        ui.print_error(e, duration, session_type)

    return duration


def run_agent_loop(
    project_dir: Path,
    model: str | None = None,
    max_sessions: int | None = None,
    app_spec: str | None = None,
    timeout: int = 1800,
    is_adoption: bool = False,
    is_enhancement: bool = False,
    sandbox: bool = True,
) -> None:
    """Run the autonomous agent loop."""
    project_dir.mkdir(parents=True, exist_ok=True)

    mcp = project_dir / ".mcp.json"
    if not mcp.exists():
        mcp.write_text('{"mcpServers": {}}\n')

    feature_file = project_dir / FEATURES_FILE
    if not feature_file.exists():
        run_with_spinner(install_bundled_skills, label="Installing skills...")

    ui.print_header(project_dir, model)

    needs_enhancement_init = is_enhancement

    if not feature_file.exists():
        if app_spec:
            copy_spec_to_project(project_dir, app_spec)
        ui.print_adoption_notice() if is_adoption else ui.print_new_project_notice()
    elif is_enhancement:
        if app_spec:
            copy_spec_to_project(project_dir, app_spec)
        ui.print_enhancement_notice()
    else:
        ui.print_resuming(project_dir)

    ui.print_separator()

    session_count = 0
    total_time = 0.0

    while True:
        if is_complete(project_dir):
            break

        session_count += 1
        if max_sessions and session_count > max_sessions:
            ui.print_max_sessions(max_sessions)
            break

        # Determine prompt type
        if needs_enhancement_init:
            prompt, stype, label = get_enhancement_initializer_prompt(), "enhancement_init", "Enhancement init..."
            needs_enhancement_init = False
        elif not feature_file.exists():
            if is_adoption:
                prompt, stype, label = get_adoption_initializer_prompt(), "adoption_init", "Adoption init..."
            else:
                prompt, stype, label = get_initializer_prompt(), "initializer", "Initializing..."
        else:
            prompt, stype, label = get_coding_prompt(), "coding", "Coding..."

        features_before = load_features(project_dir)
        prev_passing = sum(1 for f in (features_before or []) if f.get("passes"))

        print()
        duration = run_session(project_dir, model, prompt, timeout, stype, label, sandbox)
        total_time += duration

        # Validate and restore if needed
        features_after = load_features(project_dir)
        valid, err = validate_changes(features_before, features_after)
        if not valid:
            ui.print_warning(f"Invalid change: {err}")
            if features_before:
                save_features(project_dir, features_before)
                features_after = features_before

        # Find newly completed
        before_passing = {f.get("description") for f in (features_before or []) if f.get("passes")}
        newly_done = [f for f in (features_after or []) if f.get("passes") and f.get("description") not in before_passing]

        ui.print_session_progress(project_dir, newly_done, prev_passing, duration, total_time)
        ui.print_separator()

        if is_complete(project_dir):
            break

        if ui.wait_for_stop_signal():
            ui.print_user_stopped()
            return

    ui.print_complete(project_dir, session_count, total_time)
