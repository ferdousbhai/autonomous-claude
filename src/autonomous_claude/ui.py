"""Rich UI components for autonomous-claude."""

import json
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from .config import get_config

console = Console()

LOGO = """[bold cyan]
╔═╗╦ ╦╔╦╗╔═╗╔╗╔╔═╗╔╦╗╔═╗╦ ╦╔═╗
╠═╣║ ║ ║ ║ ║║║║║ ║║║║║ ║║ ║╚═╗
╩ ╩╚═╝ ╩ ╚═╝╝╚╝╚═╝╩ ╩╚═╝╚═╝╚═╝
     [dim]Claude Code CLI[/dim][/bold cyan]
"""


def print_header(project_dir: Path, model: str | None, max_sessions: int | None) -> None:
    console.print(LOGO)

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="dim")
    table.add_column()
    table.add_row("Project", f"[bold]{project_dir}[/bold]")
    table.add_row("Model", model or "[dim]Claude Code default[/dim]")
    table.add_row("Sessions", str(max_sessions) if max_sessions else "[dim]unlimited[/dim]")

    console.print(table)
    console.print()


def print_session_header(is_initializer: bool, is_adoption: bool = False, is_enhancement: bool = False) -> None:
    if is_initializer:
        if is_enhancement:
            title = "ENHANCEMENT INITIALIZER"
        elif is_adoption:
            title = "ADOPTION INITIALIZER"
        else:
            title = "INITIALIZER"
    else:
        title = "CODING AGENT"
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
    tests_file = project_dir / "feature_list.json"
    if not tests_file.exists():
        return 0, 0
    try:
        tests = json.loads(tests_file.read_text())
        total = len(tests)
        passing = sum(1 for t in tests if t.get("passes"))
        return passing, total
    except (json.JSONDecodeError, IOError):
        return 0, 0


def get_features(project_dir: Path) -> list[dict]:
    """Return all features from feature_list.json."""
    tests_file = project_dir / "feature_list.json"
    if not tests_file.exists():
        return []
    try:
        return json.loads(tests_file.read_text())
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
    else:
        console.print("\n[dim]Progress: feature_list.json not yet created[/dim]")


def print_max_sessions(n: int) -> None:
    console.print(f"\n[yellow]Reached max sessions ({n})[/yellow]")


def print_complete(project_dir: Path) -> None:
    console.print()
    console.print("[bold green]── COMPLETE ──[/bold green]")
    console.print(f"Project: [bold]{project_dir}[/bold]")
    print_progress(project_dir)
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
