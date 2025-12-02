"""
Prompt Management
=================

Functions for loading and generating prompts.
"""

from importlib import resources
from pathlib import Path


def _load_bundled_prompt(name: str) -> str:
    """Load a bundled prompt template."""
    with resources.files("autonomous_claude.prompts").joinpath(f"{name}.md").open() as f:
        return f.read()


def get_initializer_prompt() -> str:
    """Get the initializer agent prompt."""
    return _load_bundled_prompt("initializer_prompt")


def get_coding_prompt() -> str:
    """Get the coding agent prompt."""
    return _load_bundled_prompt("coding_prompt")


def create_app_spec(description: str, feature_count: int = 50) -> str:
    """
    Generate an app specification from a user description.

    Args:
        description: User's app description or requirements
        feature_count: Target number of features to generate

    Returns:
        A formatted app specification
    """
    return f"""# Application Specification

## Overview
{description}

## Requirements
Build a complete, production-quality implementation of the application described above.

## Feature Count Target
Generate approximately {feature_count} testable features for this application.
Prioritize core functionality first, then add polish and advanced features.

## Quality Standards
- Clean, maintainable code
- Responsive UI (if applicable)
- Error handling
- Good user experience
"""


def copy_spec_to_project(project_dir: Path, spec_content: str) -> None:
    """Write the app specification to the project directory."""
    spec_file = project_dir / "app_spec.txt"
    if not spec_file.exists():
        spec_file.write_text(spec_content)
        print(f"Created {spec_file}")
