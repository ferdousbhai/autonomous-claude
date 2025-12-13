"""Claude Code CLI wrapper."""

import shutil
import subprocess
from pathlib import Path
from typing import Optional

from .config import get_config
from .sandbox import DockerSandbox, SandboxConfig, is_docker_available, check_docker_daemon


def verify_claude_cli() -> str:
    """Verify claude CLI is installed and authenticated."""
    claude_path = shutil.which("claude")
    if not claude_path:
        raise RuntimeError(
            "Claude Code CLI not found.\n\n"
            "Install it with:\n"
            "  npm install -g @anthropic-ai/claude-code\n\n"
            "Then authenticate:\n"
            "  claude"
        )

    # Verify authentication by running a minimal test
    try:
        result = subprocess.run(
            ["claude", "-p", "hi", "--max-turns", "1"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            stderr = result.stderr.lower()
            if "auth" in stderr or "login" in stderr or "token" in stderr:
                raise RuntimeError(
                    "Claude Code CLI is not authenticated.\n\n"
                    "Run 'claude' and complete the login flow."
                )
            # Other errors might be transient, just warn
    except subprocess.TimeoutExpired:
        pass  # Timeout is fine, CLI is working

    return claude_path


def generate_app_spec(description: str, timeout: int | None = None) -> str:
    """Generate a detailed app spec using Claude."""
    verify_claude_cli()
    config = get_config()
    timeout = timeout or config.spec_timeout

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


def generate_task_spec(task: str, timeout: int | None = None) -> str:
    """Generate a task spec using Claude."""
    verify_claude_cli()
    config = get_config()
    timeout = timeout or config.spec_timeout

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
        max_turns: int | None = None,
        timeout: int | None = None,
        sandbox: bool = True,
    ):
        config = get_config()
        self.project_dir = project_dir.resolve()
        self.model = model
        self.system_prompt = system_prompt
        self.max_turns = max_turns or config.max_turns
        self.timeout = timeout or config.timeout
        self.allowed_tools = config.allowed_tools

        # Determine if we should use sandbox
        self.sandbox = sandbox and config.sandbox_enabled

        if self.sandbox:
            # Verify Docker is available
            if not is_docker_available():
                raise RuntimeError(
                    "Docker is required for sandbox mode but is not installed.\n\n"
                    "Install Docker:\n"
                    "  https://docs.docker.com/get-docker/\n\n"
                    "Or run without sandbox (not recommended):\n"
                    "  autonomous-claude --no-sandbox"
                )

            success, error = check_docker_daemon()
            if not success:
                raise RuntimeError(
                    f"Docker daemon is not running: {error}\n\n"
                    "Start Docker and try again, or run without sandbox:\n"
                    "  autonomous-claude --no-sandbox"
                )

            # Initialize sandbox
            sandbox_tag = config.sandbox_tag
            if not sandbox_tag:
                # Use package version as tag
                from . import __version__
                sandbox_tag = f"v{__version__.split('+')[0]}"

            self._sandbox = DockerSandbox(
                project_dir=self.project_dir,
                config=SandboxConfig(
                    memory_limit=config.sandbox_memory_limit,
                    cpu_limit=config.sandbox_cpu_limit,
                    image=config.sandbox_image,
                    tag=sandbox_tag,
                ),
                timeout=self.timeout,
            )
        else:
            # Verify host Claude CLI if not using sandbox
            verify_claude_cli()
            self._sandbox = None

    def _build_claude_args(self, prompt: str) -> list[str]:
        """Build argument list for claude command."""
        args = [
            "--print", "--dangerously-skip-permissions",
            "-p", prompt,
            "--max-turns", str(self.max_turns),
        ]

        if self.model:
            args.extend(["--model", self.model])

        if self.system_prompt:
            args.extend(["--system-prompt", self.system_prompt])

        args.extend(["--allowedTools", ",".join(self.allowed_tools)])

        return args

    def query(self, prompt: str) -> tuple[str, str]:
        """Send a prompt and return (stdout, stderr)."""
        self.project_dir.mkdir(parents=True, exist_ok=True)

        args = self._build_claude_args(prompt)

        if self.sandbox and self._sandbox:
            # Run in Docker sandbox
            return self._sandbox.run(args, timeout=self.timeout)
        else:
            # Run directly on host
            cmd = ["claude"] + args
            result = subprocess.run(
                cmd,
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            return result.stdout, result.stderr
