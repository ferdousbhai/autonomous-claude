"""CLI for autonomous-claude."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from . import __version__
from .agent import run_agent_loop
from .client import suggest_project_name, verify_claude_cli
from .prompts import create_app_spec

console = Console()


def confirm_app_spec(app_spec: str) -> str:
    """Display the app spec and ask user to confirm or modify it."""
    while True:
        console.print()
        console.print(Panel(app_spec, title="[bold]Generated App Spec[/bold]", border_style="cyan"))
        console.print()

        choice = typer.prompt(
            "Accept this spec? [y]es / [e]dit / [r]egenerate with feedback",
            default="y",
        ).lower().strip()

        if choice in ("y", "yes", ""):
            return app_spec
        elif choice in ("e", "edit"):
            console.print("[dim]Enter your modified spec (end with an empty line):[/dim]")
            lines = []
            while True:
                line = input()
                if line == "":
                    break
                lines.append(line)
            if lines:
                app_spec = "\n".join(lines)
                console.print("[green]Spec updated.[/green]")
            else:
                console.print("[yellow]No changes made.[/yellow]")
        elif choice in ("r", "regenerate"):
            feedback = typer.prompt("What would you like to change or add?")
            app_spec = create_app_spec(f"{app_spec}\n\n## Additional Requirements\n{feedback}")
            console.print("[green]Spec regenerated with your feedback.[/green]")
        else:
            console.print("[yellow]Please enter 'y', 'e', or 'r'.[/yellow]")

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
        typer.echo(f"Reading spec from: {spec_path}")
        description = spec_path.stem
    else:
        description = spec

    if output is None:
        typer.echo("Generating project name...")
        suggested_name = suggest_project_name(description)
        project_name = typer.prompt(
            f"Project name (Enter to accept '{suggested_name}')",
            default=suggested_name,
            show_default=False,
        )
        output = Path(project_name)

    if is_file_spec:
        app_spec = spec_path.read_text()
    else:
        typer.echo("Generating spec from description...")
        app_spec = create_app_spec(spec)

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
        typer.echo("No app_spec.txt found in project.")
        description = typer.prompt("Briefly describe this project")
        app_spec = create_app_spec(description)
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


if __name__ == "__main__":
    app()
