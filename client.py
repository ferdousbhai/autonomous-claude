"""
Claude CLI Client Configuration
===============================

Functions for creating and configuring the Claude Code CLI client.
Uses the `claude -p` command to leverage your existing Claude Code subscription.
"""

import shutil
import subprocess
from pathlib import Path


# Puppeteer MCP tools for browser automation
PUPPETEER_TOOLS = [
    "mcp__puppeteer__puppeteer_navigate",
    "mcp__puppeteer__puppeteer_screenshot",
    "mcp__puppeteer__puppeteer_click",
    "mcp__puppeteer__puppeteer_fill",
    "mcp__puppeteer__puppeteer_select",
    "mcp__puppeteer__puppeteer_hover",
    "mcp__puppeteer__puppeteer_evaluate",
]

# Built-in tools
BUILTIN_TOOLS = [
    "Read",
    "Write",
    "Edit",
    "Glob",
    "Grep",
    "Bash",
]


class ClaudeCLIClient:
    """
    A client that wraps the Claude Code CLI for autonomous coding sessions.

    Uses `claude -p` to query Claude using your existing subscription authentication.
    This avoids the need for API keys entirely.
    """

    def __init__(
        self,
        project_dir: Path,
        model: str,
        system_prompt: str = "You are an expert full-stack developer building a production-quality web application.",
        max_turns: int = 1000,
        timeout: int = 600,  # 10 minute timeout per session
    ):
        self.project_dir = project_dir.resolve()
        self.model = model
        self.system_prompt = system_prompt
        self.max_turns = max_turns
        self.timeout = timeout
        self._verify_claude_cli()

    def _verify_claude_cli(self) -> str:
        """Verify claude CLI is installed and return its path."""
        claude_path = shutil.which("claude")
        if not claude_path:
            raise RuntimeError(
                "Claude Code CLI not found.\n"
                "Install it with: npm install -g @anthropic-ai/claude-code\n"
                "Then authenticate with: claude login"
            )
        return claude_path

    def query(self, prompt: str) -> tuple[str, str]:
        """
        Send a prompt to Claude and get the response.

        Args:
            prompt: The prompt to send

        Returns:
            Tuple of (stdout, stderr) from the CLI
        """
        # Ensure project directory exists
        self.project_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            "claude",
            "--print",
            "--dangerously-skip-permissions",
            "-p", prompt,
            "--model", self.model,
            "--max-turns", str(self.max_turns),
        ]

        # Add system prompt if provided
        if self.system_prompt:
            cmd.extend(["--system-prompt", self.system_prompt])

        # Add allowed tools
        allowed_tools = BUILTIN_TOOLS + PUPPETEER_TOOLS
        cmd.extend(["--allowedTools", ",".join(allowed_tools)])

        print(f"Running in: {self.project_dir}")
        print(f"Model: {self.model}")
        print(f"Timeout: {self.timeout}s")
        print()

        result = subprocess.run(
            cmd,
            cwd=str(self.project_dir),
            capture_output=True,
            text=True,
            timeout=self.timeout,
        )

        return result.stdout, result.stderr

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass


def create_client(project_dir: Path, model: str) -> ClaudeCLIClient:
    """
    Create a Claude CLI client.

    Args:
        project_dir: Directory for the project
        model: Claude model to use

    Returns:
        Configured ClaudeCLIClient
    """
    return ClaudeCLIClient(
        project_dir=project_dir,
        model=model,
        system_prompt="You are an expert full-stack developer building a production-quality web application.",
        max_turns=1000,
    )
