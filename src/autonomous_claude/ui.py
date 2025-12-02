"""Rich UI components for autonomous-claude."""

import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

console = Console()

LOGO = """[bold cyan]
╔═╗╦ ╦╔╦╗╔═╗╔╗╔╔═╗╔╦╗╔═╗╦ ╦╔═╗
╠═╣║ ║ ║ ║ ║║║║║ ║║║║║ ║║ ║╚═╗
╩ ╩╚═╝ ╩ ╚═╝╝╚╝╚═╝╩ ╩╚═╝╚═╝╚═╝
     [dim]Claude Code CLI[/dim][/bold cyan]
"""


def print_header(project_dir: Path, model: str | None, max_iterations: int | None) -> None:
    console.print(LOGO)

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="dim")
    table.add_column()
    table.add_row("Project", f"[bold]{project_dir}[/bold]")
    table.add_row("Model", model or "[dim]Claude Code default[/dim]")
    table.add_row("Iterations", str(max_iterations) if max_iterations else "[dim]unlimited[/dim]")

    console.print(table)
    console.print()


def print_session_header(is_initializer: bool) -> None:
    title = "INITIALIZER" if is_initializer else "CODING AGENT"
    console.print()
    console.print(Panel(f"[bold]{title}[/bold]", style="cyan"))
    console.print()


def print_new_project_notice() -> None:
    console.print("[yellow]Starting new project - initializer will run first[/yellow]")
    console.print()
    console.print(Panel(
        "[bold]First session may take 5-10 minutes[/bold]\n"
        "[dim]The agent is generating features and project structure.[/dim]",
        style="yellow",
    ))
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
    else:
        console.print("\n[dim]Progress: feature_list.json not yet created[/dim]")


def print_max_iterations(n: int) -> None:
    console.print(f"\n[yellow]Reached max iterations ({n})[/yellow]")


def print_complete(project_dir: Path) -> None:
    console.print()
    console.print(Panel("[bold green]COMPLETE[/bold green]", style="green"))
    console.print(f"\nProject: [bold]{project_dir}[/bold]")
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
