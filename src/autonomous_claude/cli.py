"""CLI for autonomous-claude."""

import json
import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from . import __version__
from .agent import run_agent_loop
from .client import generate_app_spec, generate_task_spec, verify_claude_cli
from .config import get_config, FEATURES_FILE, SPEC_FILE

console = Console()


def confirm_spec(spec: str, title: str = "Spec", project_dir: Path | None = None) -> str:
    """Display spec for user confirmation or modification."""
    while True:
        console.print()
        console.print(Panel(Markdown(spec), title=title, border_style="dim", padding=(1, 2)))
        choice = typer.prompt("Accept?", default="y").lower().strip()
        if choice in ("y", "yes", ""):
            return spec
        feedback = choice if len(choice) > 1 else typer.prompt("What needs changing?")
        console.print("[dim]Updating spec...[/dim]")
        spec = generate_app_spec(f"{spec}\n\n## Changes Requested\n{feedback}", project_dir=project_dir)


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
    instructions: str | None,
    model: str | None,
    max_sessions: int | None,
    timeout: int | None,
    sandbox: bool = True,
):
    """Start new project or add features to existing one."""
    if not sandbox:
        verify_claude_cli()

    project_dir = Path.cwd()
    feature_list = project_dir / FEATURES_FILE
    config = get_config()

    if feature_list.exists():
        # Enhancement mode
        features = json.loads(feature_list.read_text())
        incomplete = [f for f in features if not f.get("passes")]

        if incomplete:
            console.print(f"[yellow]Warning:[/yellow] {len(incomplete)} incomplete feature(s).")
            console.print("[dim]Use '--continue' to continue without adding new features.[/dim]")
            if not typer.confirm("Proceed with adding new features?", default=False):
                raise typer.Exit(0)

        if not instructions:
            instructions = typer.prompt("What do you want to add")

        console.print(f"[dim]Adding to:[/dim] {project_dir}")
        console.print("[dim]Generating task spec...[/dim]")
        spec = generate_task_spec(instructions, project_dir=project_dir)
        spec = confirm_spec(spec, title="Task Spec", project_dir=project_dir)

        run_agent_loop(
            project_dir=project_dir.resolve(),
            model=model,
            max_sessions=max_sessions or config.max_sessions,
            app_spec=spec,
            timeout=timeout or config.timeout,
            is_enhancement=True,
            sandbox=sandbox,
        )
    else:
        # New project mode
        if not instructions:
            instructions = typer.prompt("Describe what you want to build")

        # Check if instructions is a file path
        try:
            spec_path = Path(instructions)
            is_file = spec_path.exists() and spec_path.is_file()
        except OSError:
            is_file = False

        if is_file:
            console.print(f"[dim]Reading spec from:[/dim] {spec_path}")
            spec = spec_path.read_text()
        else:
            console.print("[dim]Generating spec...[/dim]")
            spec = generate_app_spec(instructions, project_dir=project_dir)

        spec = confirm_spec(spec, title="App Spec", project_dir=project_dir)

        run_agent_loop(
            project_dir=project_dir.resolve(),
            model=model,
            max_sessions=max_sessions or config.max_sessions,
            app_spec=spec,
            timeout=timeout or config.timeout,
            sandbox=sandbox,
        )


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    instructions: str | None = typer.Argument(None, help="What to build or add"),
    continue_project: bool = typer.Option(False, "--continue", "-c", help="Continue existing features"),
    no_sandbox: bool = typer.Option(False, "--no-sandbox", help="Run without Docker sandbox"),
    model: str | None = typer.Option(None, "--model", "-m", help="Claude model"),
    max_sessions: int | None = typer.Option(None, "--max-sessions", "-n", help="Max sessions"),
    timeout: int | None = typer.Option(None, "--timeout", "-t", help="Session timeout (seconds)"),
    version: bool = typer.Option(False, "--version", "-v", callback=version_callback, is_eager=True, help="Show version"),
):
    """Build apps autonomously with Claude Code CLI."""
    if ctx.invoked_subcommand:
        return

    # Handle "update" passed as positional arg
    if instructions == "update":
        update()
        return

    sandbox = get_config().sandbox_enabled and not no_sandbox

    if continue_project:
        run_continue(model, max_sessions, timeout, sandbox)
    else:
        run_default(instructions, model, max_sessions, timeout, sandbox)


def run_continue(model: str | None, max_sessions: int | None, timeout: int | None, sandbox: bool = True):
    """Continue work on existing features."""
    if not sandbox:
        verify_claude_cli()

    project_dir = Path.cwd()
    feature_list = project_dir / FEATURES_FILE

    if not feature_list.exists():
        typer.echo(f"No features.json in {project_dir}. Run 'autonomous-claude \"description\"' first.", err=True)
        raise typer.Exit(1)

    spec = None
    if not (project_dir / SPEC_FILE).exists():
        console.print("[dim]No spec.md found.[/dim]")
        description = typer.prompt("Briefly describe this project")
        console.print("[dim]Generating spec...[/dim]")
        spec = generate_app_spec(description, project_dir=project_dir)
        spec = confirm_spec(spec, title="App Spec", project_dir=project_dir)

    config = get_config()
    run_agent_loop(
        project_dir=project_dir.resolve(),
        model=model,
        max_sessions=max_sessions or config.max_sessions,
        app_spec=spec,
        timeout=timeout or config.timeout,
        sandbox=sandbox,
    )


@app.command()
def update():
    """Update to latest version from PyPI."""
    import urllib.request

    console.print(f"Current: {__version__}")
    console.print("Checking for updates...")

    with urllib.request.urlopen("https://pypi.org/pypi/autonomous-claude/json", timeout=10) as r:
        latest = json.loads(r.read().decode())["info"]["version"]

    current_base = __version__.split(".dev")[0].split("+")[0]
    if current_base == latest:
        console.print(f"Up to date ({latest})")
        return

    console.print(f"Updating {__version__} → {latest}...")
    result = subprocess.run(["uv", "tool", "install", "--force", "autonomous-claude"], capture_output=True, text=True)
    if result.returncode == 0:
        console.print(f"Updated to {latest}")
    else:
        console.print(f"[red]Update failed: {result.stderr}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
