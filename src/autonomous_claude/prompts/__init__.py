"""Prompt loading and generation."""

from importlib import resources
from pathlib import Path


def _load_bundled_prompt(name: str) -> str:
    with resources.files("autonomous_claude.prompts").joinpath(f"{name}.md").open() as f:
        return f.read()


def get_initializer_prompt() -> str:
    return _load_bundled_prompt("initializer_prompt")


def get_coding_prompt() -> str:
    return _load_bundled_prompt("coding_prompt")


def get_adoption_initializer_prompt() -> str:
    return _load_bundled_prompt("adoption_initializer_prompt")


def get_enhancement_initializer_prompt() -> str:
    return _load_bundled_prompt("enhancement_initializer_prompt")


def create_app_spec(description: str) -> str:
    return f"""# Application Specification

## Overview
{description}

## Requirements
Build a complete, production-quality implementation of the application described above.

## Quality Standards
- Clean, maintainable code
- Responsive UI (if applicable)
- Error handling
- Good user experience
"""


def create_task_spec(task: str) -> str:
    return f"""# Task Specification

## Overview
This is an EXISTING project that needs maintenance/enhancement work.

## Tasks to Complete
{task}

## Guidelines
- Understand the existing codebase before making changes
- Follow existing code conventions and patterns
- Maintain backwards compatibility unless explicitly changing behavior
- Test thoroughly to avoid regressions

## Quality Standards
- Clean, maintainable code matching existing style
- Proper error handling
- Good user experience
"""


def copy_spec_to_project(project_dir: Path, spec_content: str) -> None:
    spec_file = project_dir / "app_spec.txt"
    if not spec_file.exists():
        spec_file.write_text(spec_content)
