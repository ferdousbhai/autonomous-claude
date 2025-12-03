"""Claude Code CLI wrapper."""

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional


FAST_MODEL = os.environ.get("AUTONOMOUS_CLAUDE_FAST_MODEL", "claude-haiku-4-5-20251001")
ALLOWED_TOOLS = ["Read", "Write", "Edit", "Glob", "Grep", "Bash"]


def verify_claude_cli() -> str:
    """Verify claude CLI is installed and return its path."""
    claude_path = shutil.which("claude")
    if not claude_path:
        raise RuntimeError(
            "Claude Code CLI not found.\n\n"
            "Install it with:\n"
            "  npm install -g @anthropic-ai/claude-code\n\n"
            "Then authenticate:\n"
            "  claude login"
        )
    return claude_path


def suggest_project_name(description: str, timeout: int = 30) -> str:
    """Generate a kebab-case project name from description."""
    verify_claude_cli()

    prompt = f"""Generate a kebab-case project name for: "{description}"

Rules:
- Lowercase and hyphens only
- 1-2 words, max 15 chars
- Output ONLY the name

Examples: notes-app, todo, budget-track"""

    result = subprocess.run(
        ["claude", "--print", "-p", prompt, "--model", FAST_MODEL],
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    name = result.stdout.strip().split('\n')[0].strip()
    name = re.sub(r'[^a-z0-9-]', '', name.lower())
    name = re.sub(r'-+', '-', name).strip('-')
    return name[:15] if name else "my-app"


def generate_app_spec(description: str, timeout: int = 60) -> str:
    """Generate a detailed app spec using Claude."""
    verify_claude_cli()

    prompt = f"""Write a concise application specification for:

"{description}"

Format as markdown with these sections:
# <App Name>

## Overview
One paragraph describing what this app does and who it's for.

## Core Features
- Feature 1: Brief description
- Feature 2: Brief description
(3-6 key features)

## Tech Stack
Recommend appropriate technologies for this type of app.

Keep it focused and actionable. Output only the spec, no preamble."""

    result = subprocess.run(
        ["claude", "--print", "-p", prompt],
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    spec = result.stdout.strip()
    if not spec:
        return f"""# Application

## Overview
{description}

## Core Features
- Build a complete, production-quality implementation

## Tech Stack
- Choose appropriate technologies based on requirements
"""
    return spec


def generate_task_spec(task: str, timeout: int = 60) -> str:
    """Generate a task spec using Claude."""
    verify_claude_cli()

    prompt = f"""Write a concise task specification for an existing project:

"{task}"

Format as markdown:
# Task: <Brief Title>

## Overview
One paragraph describing what needs to be done.

## Requirements
- Requirement 1
- Requirement 2
(key requirements)

## Guidelines
- Follow existing code patterns
- Maintain backwards compatibility

Keep it focused. Output only the spec, no preamble."""

    result = subprocess.run(
        ["claude", "--print", "-p", prompt],
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    spec = result.stdout.strip()
    if not spec:
        return f"""# Task

## Overview
{task}

## Requirements
- Complete the task as described

## Guidelines
- Follow existing code patterns
"""
    return spec


class ClaudeCLIClient:
    """Wrapper for Claude Code CLI sessions."""

    def __init__(
        self,
        project_dir: Path,
        model: Optional[str] = None,
        system_prompt: str = "You are an expert full-stack developer building a production-quality web application.",
        max_turns: int = 1000,
        timeout: int = 1800,
    ):
        self.project_dir = project_dir.resolve()
        self.model = model
        self.system_prompt = system_prompt
        self.max_turns = max_turns
        self.timeout = timeout
        verify_claude_cli()

    def query(self, prompt: str) -> tuple[str, str]:
        """Send a prompt and return (stdout, stderr)."""
        self.project_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            "claude", "--print", "--dangerously-skip-permissions",
            "-p", prompt,
            "--max-turns", str(self.max_turns),
        ]

        if self.model:
            cmd.extend(["--model", self.model])

        if self.system_prompt:
            cmd.extend(["--system-prompt", self.system_prompt])

        cmd.extend(["--allowedTools", ",".join(ALLOWED_TOOLS)])

        result = subprocess.run(
            cmd,
            cwd=str(self.project_dir),
            capture_output=True,
            text=True,
            timeout=self.timeout,
        )
        return result.stdout, result.stderr
