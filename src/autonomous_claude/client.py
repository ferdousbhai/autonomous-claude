"""
Claude CLI Client
=================

Wraps the Claude Code CLI for autonomous coding sessions.
Uses your existing Claude Code subscription - no API key required.
"""

import re
import shutil
import subprocess
from pathlib import Path


# Built-in tools
BUILTIN_TOOLS = [
    "Read",
    "Write",
    "Edit",
    "Glob",
    "Grep",
    "Bash",
]


def verify_claude_cli() -> str:
    """Verify claude CLI is installed and return its path."""
    claude_path = shutil.which("claude")
    if not claude_path:
        raise RuntimeError(
            "Claude Code CLI not found.\n\n"
            "Install it with:\n"
            "  npm install -g @anthropic-ai/claude-code\n\n"
            "Then authenticate with your subscription:\n"
            "  claude login"
        )
    return claude_path


def suggest_project_name(description: str, timeout: int = 30) -> str:
    """
    Use Claude to generate a suggested project name from a description.

    Args:
        description: The app description
        timeout: Timeout in seconds

    Returns:
        A suggested project name (kebab-case, e.g., "notes-app")
    """
    verify_claude_cli()

    prompt = f"""Generate a kebab-case project name for: "{description}"

Rules:
- Lowercase and hyphens only
- 1-2 words, max 15 chars
- Output ONLY the name

Examples: notes-app, todo, budget-track"""

    result = subprocess.run(
        ["claude", "--print", "-p", prompt, "--model", "claude-haiku-4-5-20251001"],
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    name = result.stdout.strip().split('\n')[0].strip()
    name = re.sub(r'[^a-z0-9-]', '', name.lower())
    name = re.sub(r'-+', '-', name).strip('-')

    return name[:15] if name else "my-app"


class ClaudeCLIClient:
    """
    A client that wraps the Claude Code CLI for autonomous coding sessions.

    Uses `claude -p` to query Claude using your existing subscription authentication.
    """

    def __init__(
        self,
        project_dir: Path,
        model: str = "claude-sonnet-4-5-20250929",
        system_prompt: str = "You are an expert full-stack developer building a production-quality web application.",
        max_turns: int = 1000,
        timeout: int = 600,
    ):
        self.project_dir = project_dir.resolve()
        self.model = model
        self.system_prompt = system_prompt
        self.max_turns = max_turns
        self.timeout = timeout
        verify_claude_cli()

    def query(self, prompt: str) -> tuple[str, str]:
        """
        Send a prompt to Claude and get the response.

        Args:
            prompt: The prompt to send

        Returns:
            Tuple of (stdout, stderr) from the CLI
        """
        self.project_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            "claude",
            "--print",
            "--dangerously-skip-permissions",
            "-p", prompt,
            "--model", self.model,
            "--max-turns", str(self.max_turns),
        ]

        if self.system_prompt:
            cmd.extend(["--system-prompt", self.system_prompt])

        cmd.extend(["--allowedTools", ",".join(BUILTIN_TOOLS)])

        result = subprocess.run(
            cmd,
            cwd=str(self.project_dir),
            capture_output=True,
            text=True,
            timeout=self.timeout,
        )

        return result.stdout, result.stderr
