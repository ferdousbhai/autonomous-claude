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
    sandbox: bool = True,
):
    """Run the default command - start new project or add features."""
    # Only verify host Claude CLI if not using sandbox
    if not sandbox:
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
                sandbox=sandbox,
            )
        except KeyboardInterrupt:
            typer.echo("\n\nInterrupted. Run 'autonomous-claude --continue' to continue.")
            raise typer.Exit(0)
    else:
        # New project mode
        if instructions is None:
            instructions = typer.prompt("Describe what you want to build")

        # Check if instructions is a file path (guard against invalid paths)
        try:
            spec_path = Path(instructions)
            is_file_spec = spec_path.exists() and spec_path.is_file()
        except OSError:
            is_file_spec = False

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
                sandbox=sandbox,
            )
        except KeyboardInterrupt:
            typer.echo("\n\nInterrupted. Run 'autonomous-claude --continue' to continue.")
            raise typer.Exit(0)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    instructions: Optional[str] = typer.Argument(None, help="What to build or add to the project"),
    continue_project: bool = typer.Option(
        False, "--continue", "-c",
        help="Continue work on existing features."
    ),
    no_sandbox: bool = typer.Option(
        False, "--no-sandbox",
        help="Run without Docker sandbox (not recommended for security)."
    ),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Claude model (default: Claude Code's configured model)"),
    max_sessions: Optional[int] = typer.Option(None, "--max-sessions", "-n", help="Max sessions (Claude Code invocations)"),
    timeout: Optional[int] = typer.Option(None, "--timeout", "-t", help="Timeout per session (seconds)"),
    version: bool = typer.Option(
        False, "--version", "-v", callback=version_callback, is_eager=True,
        help="Show version and exit."
    ),
):
    """Build apps autonomously with Claude Code CLI.

    Run in a project directory to start building or add features.
    By default, runs inside a Docker sandbox for security.

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

        # Run without sandbox (advanced users only)
        autonomous-claude --no-sandbox "A simple script"
    """
    # Determine sandbox mode from CLI flag and config
    config = get_config()
    sandbox = config.sandbox_enabled and not no_sandbox

    # If a subcommand is invoked, don't run the default behavior
    if ctx.invoked_subcommand is not None:
        return

    if continue_project:
        run_continue(model=model, max_sessions=max_sessions, timeout=timeout, sandbox=sandbox)
        return

    # Handle the case where "update" is passed as instructions
    # This happens because typer parses positional args before subcommands
    if instructions == "update":
        update()
        return

    run_default(instructions, model, max_sessions, timeout, sandbox=sandbox)


def run_continue(
    model: Optional[str],
    max_sessions: Optional[int],
    timeout: Optional[int],
    sandbox: bool = True,
):
    """Continue work on existing features."""
    # Only verify host Claude CLI if not using sandbox
    if not sandbox:
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
            sandbox=sandbox,
        )
    except KeyboardInterrupt:
        typer.echo("\n\nInterrupted. Run 'autonomous-claude --continue' to continue.")
        raise typer.Exit(0)


@app.command()
def update():
    """Update autonomous-claude to the latest version from PyPI."""
    import urllib.request
    import json

    console.print("[dim]Checking for updates...[/dim]")

    # Get current version
    current_version = __version__

    # Get latest version from PyPI
    try:
        with urllib.request.urlopen(
            "https://pypi.org/pypi/autonomous-claude/json", timeout=10
        ) as response:
            data = json.loads(response.read().decode())
            latest_version = data["info"]["version"]
    except Exception as e:
        console.print(f"[red]Error checking PyPI: {e}[/red]")
        raise typer.Exit(1)

    # Compare versions (strip any dev/local suffixes for comparison)
    current_base = current_version.split(".dev")[0].split("+")[0]

    if current_base == latest_version:
        console.print(f"[green]autonomous-claude {latest_version} is the latest version.[/green]")
        return

    console.print(f"[yellow]Current: {current_version} → Latest: {latest_version}[/yellow]")
    console.print("[dim]Updating...[/dim]")

    try:
        result = subprocess.run(
            ["uv", "tool", "install", "--force", "autonomous-claude"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            console.print(f"[green]Updated to {latest_version}[/green]")
        else:
            console.print(f"[red]Error updating: {result.stderr}[/red]")
            raise typer.Exit(1)
    except FileNotFoundError:
        typer.echo("Error: 'uv' is not installed. Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
