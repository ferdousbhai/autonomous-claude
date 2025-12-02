"""
CLI Interface
=============

Command-line interface for autonomous-claude.
"""

from pathlib import Path
from typing import Optional

import typer

from . import __version__
from .agent import run_agent_loop
from .client import suggest_project_name, verify_claude_cli
from .prompts import create_app_spec

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
    spec: str = typer.Argument(
        ...,
        help="App description (text) or path to spec file (.txt/.md)",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Output directory (default: auto-generated name)",
    ),
    model: str = typer.Option(
        "claude-sonnet-4-5-20250929",
        "--model", "-m",
        help="Claude model to use",
    ),
    max_iterations: Optional[int] = typer.Option(
        None,
        "--max-iterations", "-n",
        help="Maximum iterations (default: unlimited)",
    ),
    features: int = typer.Option(
        50,
        "--features", "-f",
        help="Target number of features to generate",
    ),
    timeout: int = typer.Option(
        600,
        "--timeout", "-t",
        help="Timeout per session in seconds",
    ),
):
    """
    Build an app from a description or spec file.

    Examples:

        autonomous-claude build "A todo app with React and SQLite"

        autonomous-claude build ./my-spec.txt -o ./my-app

        autonomous-claude build "Blog with markdown support" -n 5 -f 30
    """
    # Verify Claude CLI is available
    try:
        verify_claude_cli()
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)

    # Determine if spec is a file path or description
    spec_path = Path(spec)
    if spec_path.exists() and spec_path.is_file():
        typer.echo(f"Reading spec from: {spec_path}")
        app_spec = spec_path.read_text()
        description = spec_path.stem  # Use filename for name suggestion
    else:
        typer.echo("Generating spec from description...")
        app_spec = create_app_spec(spec, features)
        description = spec

    # Determine output directory
    if output is None:
        typer.echo("Generating project name...")
        suggested_name = suggest_project_name(description)
        project_name = typer.prompt(
            "Project name",
            default=suggested_name,
        )
        output = Path(project_name)

    # Run the agent
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
    project_dir: Path = typer.Argument(
        ...,
        help="Project directory to resume",
    ),
    model: str = typer.Option(
        "claude-sonnet-4-5-20250929",
        "--model", "-m",
        help="Claude model to use",
    ),
    max_iterations: Optional[int] = typer.Option(
        None,
        "--max-iterations", "-n",
        help="Maximum iterations (default: unlimited)",
    ),
    timeout: int = typer.Option(
        600,
        "--timeout", "-t",
        help="Timeout per session in seconds",
    ),
):
    """
    Resume building an existing project.

    Example:

        autonomous-claude resume ./my-app
    """
    # Verify Claude CLI
    try:
        verify_claude_cli()
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)

    # Check project exists
    if not project_dir.exists():
        typer.echo(f"Error: Project directory not found: {project_dir}", err=True)
        raise typer.Exit(1)

    feature_list = project_dir / "feature_list.json"
    if not feature_list.exists():
        typer.echo(f"Error: No feature_list.json found in {project_dir}", err=True)
        typer.echo("Use 'autonomous-claude build' to start a new project.", err=True)
        raise typer.Exit(1)

    try:
        run_agent_loop(
            project_dir=project_dir.resolve(),
            model=model,
            max_iterations=max_iterations,
            timeout=timeout,
        )
    except KeyboardInterrupt:
        typer.echo("\n\nInterrupted. Run this command again to continue.")
        raise typer.Exit(0)


if __name__ == "__main__":
    app()
