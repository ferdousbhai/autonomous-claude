"""CLI for autonomous-claude."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from . import __version__
from .agent import run_agent_loop
from .client import generate_app_spec, generate_task_spec, verify_claude_cli

console = Console()


def confirm_app_spec(app_spec: str) -> str:
    """Display the app spec and ask user to confirm or modify it."""
    while True:
        console.print()
        console.print(Panel(
            Markdown(app_spec),
            title="App Spec",
            border_style="dim",
            padding=(1, 2),
        ))

        choice = typer.prompt("Accept?", default="y").lower().strip()

        if choice in ("y", "yes", ""):
            return app_spec
        else:
            feedback = choice if len(choice) > 1 else typer.prompt("What needs changing?")
            console.print("[dim]Updating spec...[/dim]")
            app_spec = generate_app_spec(f"{app_spec}\n\n## Changes Requested\n{feedback}")

app = typer.Typer(
    name="autonomous-claude",
    help="Build apps autonomously with Claude Code CLI.",
    add_completion=False,
)


def version_callback(value: bool):
    if value:
        print(f"autonomous-claude {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-v", callback=version_callback, is_eager=True,
        help="Show version and exit."
    ),
):
    """Build apps autonomously with Claude Code CLI."""
    pass


@app.command()
def build(
    spec: str = typer.Argument(..., help="App description or path to spec file"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Claude model (default: Claude Code's configured model)"),
    max_iterations: Optional[int] = typer.Option(None, "--max-iterations", "-n", help="Max iterations"),
    timeout: int = typer.Option(1800, "--timeout", "-t", help="Timeout per session (seconds)"),
):
    """Build an app from a description or spec file."""
    try:
        verify_claude_cli()
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)

    spec_path = Path(spec)
    is_file_spec = spec_path.exists() and spec_path.is_file()

    if is_file_spec:
        console.print(f"[dim]Reading spec from:[/dim] {spec_path}")
        description = spec_path.stem
    else:
        description = spec

    if output is None:
        project_name = typer.prompt("Project name")
        output = Path(project_name)

    if is_file_spec:
        app_spec = spec_path.read_text()
    else:
        console.print("[dim]Generating spec...[/dim]")
        app_spec = generate_app_spec(spec)

    app_spec = confirm_app_spec(app_spec)

    try:
        run_agent_loop(
            project_dir=output.resolve(),
            model=model,
            max_iterations=max_iterations,
            app_spec=app_spec,
            timeout=timeout,
        )
    except KeyboardInterrupt:
        typer.echo("\n\nInterrupted. Run 'autonomous-claude resume' to continue.")
        raise typer.Exit(0)


@app.command()
def resume(
    project_dir: Path = typer.Argument(..., help="Project directory to resume"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Claude model (default: Claude Code's configured model)"),
    max_iterations: Optional[int] = typer.Option(None, "--max-iterations", "-n", help="Max iterations"),
    timeout: int = typer.Option(1800, "--timeout", "-t", help="Timeout per session (seconds)"),
):
    """Resume building an existing project."""
    try:
        verify_claude_cli()
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)

    if not project_dir.exists():
        typer.echo(f"Error: Project directory not found: {project_dir}", err=True)
        raise typer.Exit(1)

    feature_list = project_dir / "feature_list.json"
    if not feature_list.exists():
        typer.echo(f"Error: No feature_list.json found in {project_dir}", err=True)
        typer.echo("Use 'autonomous-claude build' to start a new project.", err=True)
        raise typer.Exit(1)

    # Check if app_spec.txt exists, prompt for description if not
    app_spec = None
    spec_file = project_dir / "app_spec.txt"
    if not spec_file.exists():
        console.print("[dim]No app_spec.txt found in project.[/dim]")
        description = typer.prompt("Briefly describe this project")
        console.print("[dim]Generating spec...[/dim]")
        app_spec = generate_app_spec(description)
        app_spec = confirm_app_spec(app_spec)

    try:
        run_agent_loop(
            project_dir=project_dir.resolve(),
            model=model,
            max_iterations=max_iterations,
            app_spec=app_spec,
            timeout=timeout,
        )
    except KeyboardInterrupt:
        typer.echo("\n\nInterrupted. Run this command again to continue.")
        raise typer.Exit(0)


def confirm_task_spec(task_spec: str) -> str:
    """Display the task spec and ask user to confirm or modify it."""
    while True:
        console.print()
        console.print(Panel(
            Markdown(task_spec),
            title="Task Spec",
            border_style="dim",
            padding=(1, 2),
        ))

        choice = typer.prompt("Accept?", default="y").lower().strip()

        if choice in ("y", "yes", ""):
            return task_spec
        else:
            feedback = choice if len(choice) > 1 else typer.prompt("What needs changing?")
            console.print("[dim]Updating spec...[/dim]")
            task_spec = generate_task_spec(f"{task_spec}\n\n## Changes Requested\n{feedback}")


@app.command(name="continue")
def continue_project(
    project_dir: Path = typer.Argument(..., help="Existing project directory"),
    task: str = typer.Argument(..., help="What to work on (feature, bug fix, enhancement)"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Claude model (default: Claude Code's configured model)"),
    max_iterations: Optional[int] = typer.Option(None, "--max-iterations", "-n", help="Max iterations"),
    timeout: int = typer.Option(1800, "--timeout", "-t", help="Timeout per session (seconds)"),
):
    """Continue working on an existing project with new tasks.

    Works with any project - whether built with this tool or not.

    Examples:
        # Adopt an existing project
        autonomous-claude continue ./my-app "Add dark mode"

        # Add new features to a project built with this tool
        autonomous-claude continue ./my-app "Add user authentication"
    """
    try:
        verify_claude_cli()
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)

    if not project_dir.exists():
        typer.echo(f"Error: Project directory not found: {project_dir}", err=True)
        raise typer.Exit(1)

    if not project_dir.is_dir():
        typer.echo(f"Error: {project_dir} is not a directory", err=True)
        raise typer.Exit(1)

    feature_list = project_dir / "feature_list.json"
    has_feature_list = feature_list.exists()

    if has_feature_list:
        console.print(f"[dim]Adding new tasks to:[/dim] {project_dir}")
    else:
        console.print(f"[dim]Adopting project:[/dim] {project_dir}")

    console.print(f"[dim]Task:[/dim] {task}")
    console.print()

    console.print("[dim]Generating task spec...[/dim]")
    task_spec = generate_task_spec(task)
    task_spec = confirm_task_spec(task_spec)

    try:
        run_agent_loop(
            project_dir=project_dir.resolve(),
            model=model,
            max_iterations=max_iterations,
            app_spec=task_spec,
            timeout=timeout,
            is_adoption=not has_feature_list,
            is_enhancement=has_feature_list,
        )
    except KeyboardInterrupt:
        typer.echo("\n\nInterrupted. Run 'autonomous-claude resume' to continue.")
        raise typer.Exit(0)


if __name__ == "__main__":
    app()
