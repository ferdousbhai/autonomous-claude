"""CLI for autonomous-claude."""

import json
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from . import __version__
from .agent import run_agent_loop
from .client import generate_app_spec, generate_task_spec, verify_claude_cli
from .config import get_config

console = Console()


def confirm_spec(spec: str, title: str = "Spec") -> str:
    """Display a spec and ask user to confirm or modify it."""
    while True:
        console.print()
        console.print(Panel(
            Markdown(spec),
            title=title,
            border_style="dim",
            padding=(1, 2),
        ))

        choice = typer.prompt("Accept?", default="y").lower().strip()

        if choice in ("y", "yes", ""):
            return spec
        else:
            feedback = choice if len(choice) > 1 else typer.prompt("What needs changing?")
            console.print("[dim]Updating spec...[/dim]")
            spec = generate_app_spec(f"{spec}\n\n## Changes Requested\n{feedback}")


app = typer.Typer(
    name="autonomous-claude",
    help="Build apps autonomously with Claude Code CLI.",
    add_completion=False,
    no_args_is_help=False,
)


def version_callback(value: bool):
    if value:
        print(f"autonomous-claude {__version__}")
        raise typer.Exit()


def run_default(
    instructions: Optional[str],
    model: Optional[str],
    max_sessions: Optional[int],
    timeout: Optional[int],
    verbose: bool,
):
    """Run the default command - start new project or add features."""
    try:
        verify_claude_cli()
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)

    project_dir = Path.cwd()
    feature_list = project_dir / "feature_list.json"
    has_feature_list = feature_list.exists()

    config = get_config()

    if has_feature_list:
        # Enhancement mode - adding features to existing project
        features = json.loads(feature_list.read_text())
        incomplete = [f for f in features if not f.get("passes", False)]

        if incomplete:
            console.print(f"[yellow]Warning:[/yellow] This project has {len(incomplete)} incomplete feature(s).")
            console.print("[dim]Use '--continue' to continue without adding new features.[/dim]")
            if not typer.confirm("Proceed with adding new features?", default=False):
                console.print("[dim]Run:[/dim] autonomous-claude --continue")
                raise typer.Exit(0)

        if instructions is None:
            instructions = typer.prompt("What do you want to add")

        console.print(f"[dim]Adding to project:[/dim] {project_dir}")
        console.print(f"[dim]Task:[/dim] {instructions}")
        console.print()

        console.print("[dim]Generating task spec...[/dim]")
        task_spec = generate_task_spec(instructions)
        task_spec = confirm_spec(task_spec, title="Task Spec")

        try:
            run_agent_loop(
                project_dir=project_dir.resolve(),
                model=model,
                max_sessions=max_sessions or config.max_sessions,
                app_spec=task_spec,
                timeout=timeout or config.timeout,
                is_enhancement=True,
                verbose=verbose,
            )
        except KeyboardInterrupt:
            typer.echo("\n\nInterrupted. Run 'autonomous-claude --continue' to continue.")
            raise typer.Exit(0)
    else:
        # New project mode
        if instructions is None:
            instructions = typer.prompt("Describe what you want to build")

        # Check if instructions is a file path
        spec_path = Path(instructions)
        is_file_spec = spec_path.exists() and spec_path.is_file()

        if is_file_spec:
            console.print(f"[dim]Reading spec from:[/dim] {spec_path}")
            app_spec = spec_path.read_text()
        else:
            console.print("[dim]Generating spec...[/dim]")
            app_spec = generate_app_spec(instructions)

        app_spec = confirm_spec(app_spec, title="App Spec")

        try:
            run_agent_loop(
                project_dir=project_dir.resolve(),
                model=model,
                max_sessions=max_sessions or config.max_sessions,
                app_spec=app_spec,
                timeout=timeout or config.timeout,
                verbose=verbose,
            )
        except KeyboardInterrupt:
            typer.echo("\n\nInterrupted. Run 'autonomous-claude --continue' to continue.")
            raise typer.Exit(0)


def continue_callback(ctx: typer.Context, value: bool):
    """Handle --continue flag."""
    if not value:
        return
    # Store that we want to continue, will be handled in main
    ctx.ensure_object(dict)
    ctx.obj["continue"] = True


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    instructions: Optional[str] = typer.Argument(None, help="What to build or add to the project"),
    continue_project_flag: bool = typer.Option(
        False, "--continue", "-c", callback=continue_callback, is_eager=True,
        help="Continue work on existing features."
    ),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Claude model (default: Claude Code's configured model)"),
    max_sessions: Optional[int] = typer.Option(None, "--max-sessions", "-n", help="Max sessions (Claude Code invocations)"),
    timeout: Optional[int] = typer.Option(None, "--timeout", "-t", help="Timeout per session (seconds)"),
    verbose: bool = typer.Option(False, "--verbose", help="Stream Claude output in real-time"),
    version: bool = typer.Option(
        False, "--version", "-v", callback=version_callback, is_eager=True,
        help="Show version and exit."
    ),
):
    """Build apps autonomously with Claude Code CLI.

    Run in a project directory to start building or add features.

    Examples:
        # Start a new project
        mkdir my-app && cd my-app
        autonomous-claude "A todo app with local storage"

        # Add features to an existing project
        cd my-app
        autonomous-claude "Add dark mode and user authentication"

        # Continue work on existing features
        cd my-app
        autonomous-claude --continue
    """
    # If a subcommand is invoked, don't run the default behavior
    if ctx.invoked_subcommand is not None:
        return

    # Handle --continue flag
    if continue_project_flag:
        run_continue(model=model, max_sessions=max_sessions, timeout=timeout, verbose=verbose)
        return

    # Handle the case where "update" is passed as instructions
    # This happens because typer parses positional args before subcommands
    if instructions == "update":
        update()
        return

    run_default(instructions, model, max_sessions, timeout, verbose)


def run_continue(
    model: Optional[str],
    max_sessions: Optional[int],
    timeout: Optional[int],
    verbose: bool,
):
    """Continue work on existing features."""
    try:
        verify_claude_cli()
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)

    project_dir = Path.cwd()
    feature_list = project_dir / "feature_list.json"

    if not feature_list.exists():
        typer.echo(f"Error: No feature_list.json found in {project_dir}", err=True)
        typer.echo("Run 'autonomous-claude \"description\"' to start a new project.", err=True)
        raise typer.Exit(1)

    # Check if app_spec.md exists, prompt for description if not
    app_spec = None
    spec_file = project_dir / "app_spec.md"
    if not spec_file.exists():
        console.print("[dim]No app_spec.md found in project.[/dim]")
        description = typer.prompt("Briefly describe this project")
        console.print("[dim]Generating spec...[/dim]")
        app_spec = generate_app_spec(description)
        app_spec = confirm_spec(app_spec, title="App Spec")

    config = get_config()
    try:
        run_agent_loop(
            project_dir=project_dir.resolve(),
            model=model,
            max_sessions=max_sessions or config.max_sessions,
            app_spec=app_spec,
            timeout=timeout or config.timeout,
            verbose=verbose,
        )
    except KeyboardInterrupt:
        typer.echo("\n\nInterrupted. Run 'autonomous-claude --continue' to continue.")
        raise typer.Exit(0)


@app.command()
def update():
    """Update autonomous-claude to the latest version."""
    console.print("[dim]Checking for updates...[/dim]")
    try:
        result = subprocess.run(
            ["uv", "tool", "upgrade", "autonomous-claude"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            console.print(result.stdout.strip() if result.stdout.strip() else "[green]autonomous-claude is up to date.[/green]")
        else:
            typer.echo(f"Error updating: {result.stderr}", err=True)
            raise typer.Exit(1)
    except FileNotFoundError:
        typer.echo("Error: 'uv' is not installed. Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
