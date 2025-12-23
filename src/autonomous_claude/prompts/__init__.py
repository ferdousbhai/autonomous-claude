"""Prompt loading and generation."""

from importlib import resources
from pathlib import Path

from ..config import AUTONOMOUS_CLAUDE_DIR, SPEC_FILE


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


def copy_spec_to_project(project_dir: Path, spec_content: str) -> None:
    """Copy spec content to .autonomous-claude/spec.md, creating directory if needed."""
    autonomous_dir = project_dir / AUTONOMOUS_CLAUDE_DIR
    autonomous_dir.mkdir(parents=True, exist_ok=True)
    spec_file = project_dir / SPEC_FILE
    if not spec_file.exists():
        spec_file.write_text(spec_content)
