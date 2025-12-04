"""Rich UI components for autonomous-claude."""

import json
import select
import sys
import termios
import tty
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from .config import get_config

console = Console()


def format_duration(seconds: float) -> str:
    """Format duration in human-readable form."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if minutes < 60:
        return f"{minutes}m {secs}s"
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}h {mins}m"

LOGO = """[bold cyan]
╔═╗╦ ╦╔╦╗╔═╗╔╗╔╔═╗╔╦╗╔═╗╦ ╦╔═╗
╠═╣║ ║ ║ ║ ║║║║║ ║║║║║ ║║ ║╚═╗
╩ ╩╚═╝ ╩ ╚═╝╝╚╝╚═╝╩ ╩╚═╝╚═╝╚═╝
     [dim]Claude Code CLI[/dim][/bold cyan]
"""


def print_header(project_dir: Path, model: str | None) -> None:
    console.print(LOGO)

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="dim")
    table.add_column()
    table.add_row("Project", f"[bold]{project_dir}[/bold]")
    table.add_row("Model", model or "[dim]Claude Code default[/dim]")

    console.print(table)
    console.print()


def print_session_header(
    is_initializer: bool,
    is_adoption: bool = False,
    is_enhancement: bool = False,
    session_num: int | None = None,
    max_sessions: int | None = None,
) -> None:
    if is_initializer:
        if is_enhancement:
            title = "ENHANCEMENT INITIALIZER"
        elif is_adoption:
            title = "ADOPTION INITIALIZER"
        else:
            title = "INITIALIZER"
    else:
        title = "CODING AGENT"

    # Add session counter
    if session_num is not None:
        if max_sessions:
            counter = f" ({session_num}/{max_sessions})"
        else:
            counter = f" ({session_num})"
        title += counter

    console.print()
    console.print(f"[bold cyan]── {title} ──[/bold cyan]")
    console.print()


def print_new_project_notice() -> None:
    console.print("[yellow]Starting new project - initializer will run first[/yellow]")
    console.print("[dim]First session may take 5-10 minutes while generating features and project structure.[/dim]")
    console.print()


def print_adoption_notice() -> None:
    console.print("[yellow]Adopting existing project - analyzing codebase[/yellow]")
    console.print("[dim]First session will analyze the project and create a feature list for the requested tasks.[/dim]")
    console.print()


def print_enhancement_notice() -> None:
    console.print("[yellow]Adding new features to existing project[/yellow]")
    console.print("[dim]First session will add new features to the feature list, then implementation begins.[/dim]")
    console.print()


def print_resuming(project_dir: Path) -> None:
    console.print("[green]Resuming existing project[/green]")
    print_progress(project_dir)


def get_progress_stats(project_dir: Path) -> tuple[int, int]:
    """Return (passing_count, total_count) from feature_list.json."""
    feature_list = project_dir / "feature_list.json"
    if not feature_list.exists():
        return 0, 0
    try:
        features = json.loads(feature_list.read_text())
        total = len(features)
        passing = sum(1 for f in features if f.get("passes"))
        return passing, total
    except (json.JSONDecodeError, IOError):
        return 0, 0


def get_features(project_dir: Path) -> list[dict]:
    """Return all features from feature_list.json."""
    feature_list = project_dir / "feature_list.json"
    if not feature_list.exists():
        return []
    try:
        return json.loads(feature_list.read_text())
    except (json.JSONDecodeError, IOError):
        return []


def print_feature_status(project_dir: Path) -> None:
    """Print a clean list of features with their completion status."""
    features = get_features(project_dir)
    if not features:
        return

    config = get_config()
    completed = [f for f in features if f.get("passes")]
    pending = [f for f in features if not f.get("passes")]

    console.print()

    max_len = config.feature_name_max_length

    if completed:
        console.print("[bold green]Completed Features[/bold green]")
        for f in completed:
            name = f.get("description", "Unknown")
            if len(name) > max_len:
                name = name[:max_len] + "…"
            console.print(f"  [green]✓[/green] {name}")

    if pending:
        console.print()
        console.print("[bold yellow]Pending Features[/bold yellow]")
        display_limit = config.pending_display_limit
        for f in pending[:display_limit]:
            name = f.get("description", "Unknown")
            if len(name) > max_len:
                name = name[:max_len] + "…"
            console.print(f"  [dim]○[/dim] {name}")
        remaining = len(pending) - display_limit
        if remaining > 0:
            console.print(f"  [dim]... and {remaining} more[/dim]")


def print_pending_features(project_dir: Path) -> None:
    """Print only the pending features."""
    features = get_features(project_dir)
    if not features:
        return

    config = get_config()
    pending = [f for f in features if not f.get("passes")]
    max_len = config.feature_name_max_length

    if pending:
        console.print()
        console.print("[bold yellow]Pending Features[/bold yellow]")
        display_limit = config.pending_display_limit
        for f in pending[:display_limit]:
            name = f.get("description", "Unknown")
            if len(name) > max_len:
                name = name[:max_len] + "…"
            console.print(f"  [dim]○[/dim] {name}")
        remaining = len(pending) - display_limit
        if remaining > 0:
            console.print(f"  [dim]... and {remaining} more[/dim]")


def print_progress_bar(project_dir: Path, prev_passing: int | None = None) -> None:
    """Print the progress bar with optional delta."""
    passing, total = get_progress_stats(project_dir)
    if total > 0:
        pct = (passing / total) * 100
        filled = int(pct / 5)  # 20 chars total
        bar = "█" * filled + "░" * (20 - filled)

        if pct == 100:
            style = "bold green"
        elif pct >= 50:
            style = "yellow"
        else:
            style = "white"

        if prev_passing is not None and prev_passing != passing:
            console.print(f"[{style}]Progress: {bar} {prev_passing}/{total} → {passing}/{total} ({pct:.1f}%)[/{style}]")
        else:
            console.print(f"[{style}]Progress: {bar} {passing}/{total} ({pct:.1f}%)[/{style}]")


def print_session_progress(
    project_dir: Path,
    newly_completed: list[dict],
    session_duration: float,
    prev_passing: int | None = None,
    total_run_time: float | None = None,
) -> None:
    """Print progress after a coding session (shows only new completions)."""
    config = get_config()
    max_len = config.feature_name_max_length

    console.print()
    print_progress_bar(project_dir, prev_passing)

    if newly_completed:
        console.print()
        console.print(f"[bold green]Completed this session ({len(newly_completed)})[/bold green]")
        for f in newly_completed:
            name = f.get("description", "Unknown")
            if len(name) > max_len:
                name = name[:max_len] + "…"
            console.print(f"  [green]✓[/green] {name}")
    else:
        console.print()
        console.print("[dim]No features completed this session[/dim]")

    print_pending_features(project_dir)
    console.print()
    if total_run_time is not None:
        console.print(f"[dim]Session: {format_duration(session_duration)} | Total: {format_duration(total_run_time)}[/dim]")
    else:
        console.print(f"[dim]Session time: {format_duration(session_duration)}[/dim]")


def print_progress(project_dir: Path) -> None:
    passing, total = get_progress_stats(project_dir)
    if total > 0:
        pct = (passing / total) * 100
        filled = int(pct / 5)  # 20 chars total
        bar = "█" * filled + "░" * (20 - filled)

        if pct == 100:
            style = "bold green"
        elif pct >= 50:
            style = "yellow"
        else:
            style = "white"

        console.print(f"\n[{style}]Progress: {bar} {passing}/{total} ({pct:.1f}%)[/{style}]")
        print_feature_status(project_dir)


def print_max_sessions(n: int) -> None:
    console.print(f"\n[yellow]Reached max sessions ({n})[/yellow]")


def print_complete(
    project_dir: Path,
    total_sessions: int | None = None,
    total_run_time: float | None = None,
) -> None:
    passing, total = get_progress_stats(project_dir)

    console.print()
    console.print("[bold green]── COMPLETE ──[/bold green]")
    console.print()
    console.print(f"[green]All {total} features implemented![/green]")

    if total_sessions is not None and total_run_time is not None:
        console.print(f"[dim]{total_sessions} sessions | {format_duration(total_run_time)} total[/dim]")
    console.print()


def print_output(stdout: str, stderr: str) -> None:
    if stdout:
        console.print(stdout)
    if stderr:
        console.print(f"\n[red][stderr]: {stderr}[/red]")
    console.print("\n" + "─" * 70 + "\n")


def print_timeout(timeout: int) -> None:
    console.print(f"[red]Session timed out ({timeout}s)[/red]")


def print_error(e: Exception) -> None:
    console.print(f"[red]Error: {e}[/red]")


def print_warning(message: str) -> None:
    console.print(f"[yellow]Warning: {message}[/yellow]")


class Spinner:
    """Context manager for showing a spinner with elapsed time."""

    def __enter__(self):
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]Running...[/bold cyan]"),
            TimeElapsedColumn(),
            console=console,
            transient=True,
        )
        self._progress.start()
        self._task = self._progress.add_task("", total=None)
        return self

    def __exit__(self, *args):
        self._progress.stop()


def wait_for_stop_signal(timeout: float = 10.0) -> bool:
    """
    Wait for a keypress with timeout. Returns True if user wants to stop.

    Displays a countdown prompt and waits for any key.
    Returns True if key pressed (stop), False if timeout (continue).
    """
    import time

    # Play terminal bell to notify user
    sys.stdout.write("\a")
    sys.stdout.flush()

    # Check if stdin is a terminal
    if not sys.stdin.isatty():
        return False

    # Save terminal settings
    old_settings = termios.tcgetattr(sys.stdin)

    try:
        # Set terminal to raw mode (no echo, immediate input)
        tty.setraw(sys.stdin.fileno())

        start = time.time()
        remaining = timeout

        while remaining > 0:
            # Show countdown (use carriage return to update in place)
            msg = f"\r\033[K  Press any key to stop, or wait {remaining:.0f}s to continue... "
            sys.stdout.write(msg)
            sys.stdout.flush()

            # Check for input with 1 second timeout
            ready, _, _ = select.select([sys.stdin], [], [], min(1.0, remaining))

            if ready:
                # Key was pressed - consume it
                sys.stdin.read(1)
                sys.stdout.write("\r\033[K")  # Clear the line
                sys.stdout.flush()
                return True

            remaining = timeout - (time.time() - start)

        # Timeout - clear the prompt line
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()
        return False

    finally:
        # Restore terminal settings
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


def print_user_stopped() -> None:
    """Print message when user stops via keypress."""
    console.print("[yellow]Stopped by user. Run 'autonomous-claude resume' to continue.[/yellow]")
