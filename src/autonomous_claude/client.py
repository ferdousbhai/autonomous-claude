"""Claude Code CLI wrapper."""

import shutil
import subprocess
from pathlib import Path

from .config import get_config
from .sandbox import DockerSandbox, SandboxConfig, is_docker_available, check_docker_daemon


def verify_claude_cli() -> str:
    """Verify claude CLI is installed."""
    path = shutil.which("claude")
    if not path:
        raise RuntimeError(
            "Claude Code CLI not found.\n\n"
            "Install: npm install -g @anthropic-ai/claude-code\n"
            "Then run: claude"
        )
    return path


_DOCS_PROMPT = "\n\nCheck for *.md files that might contain relevant context and incorporate useful information."


def generate_app_spec(description: str, project_dir: Path | None = None, timeout: int | None = None) -> str:
    """Generate application specification. Uses file tools if project_dir provided."""
    verify_claude_cli()
    timeout = timeout or get_config().spec_timeout
    docs = _DOCS_PROMPT if project_dir else ""

    prompt = f'''Write a concise application specification for: "{description}"
{docs}
Format:
# <App Name>

## Overview
One paragraph.

## Core Features
- Feature 1: Brief description
(3-6 features)

## Tech Stack
Appropriate technologies.

Output only the spec.'''

    cmd = ["claude", "--print", "-p", prompt]
    if project_dir:
        cmd.extend(["--dangerously-skip-permissions", "--allowedTools", "Read,Glob"])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           cwd=str(project_dir) if project_dir else None)
    return result.stdout.strip() or f"# Application\n\n## Overview\n{description}"


def generate_task_spec(task: str, project_dir: Path | None = None, timeout: int | None = None) -> str:
    """Generate task specification for enhancements. Uses file tools if project_dir provided."""
    verify_claude_cli()
    timeout = timeout or get_config().spec_timeout
    docs = _DOCS_PROMPT if project_dir else ""

    prompt = f'''Write a concise task specification for: "{task}"
{docs}
Format:
# Task: <Brief Title>

## Overview
One paragraph.

## Requirements
- Key requirements

## Guidelines
- Follow existing patterns

Output only the spec.'''

    cmd = ["claude", "--print", "-p", prompt]
    if project_dir:
        cmd.extend(["--dangerously-skip-permissions", "--allowedTools", "Read,Glob"])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           cwd=str(project_dir) if project_dir else None)
    return result.stdout.strip() or f"# Task\n\n## Overview\n{task}"


class ClaudeCLIClient:
    """Wrapper for Claude Code CLI sessions."""

    def __init__(
        self,
        project_dir: Path,
        model: str | None = None,
        system_prompt: str = "You are an expert full-stack developer.",
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
        self.sandbox = sandbox and config.sandbox_enabled
        self._sandbox = None

        if self.sandbox:
            if not is_docker_available():
                raise RuntimeError("Docker required for sandbox. Install Docker or use --no-sandbox")

            ok, err = check_docker_daemon()
            if not ok:
                raise RuntimeError(f"Docker daemon not running: {err}")

            from . import __version__
            tag = config.sandbox_tag or f"v{__version__.split('+')[0]}"

            self._sandbox = DockerSandbox(
                project_dir=self.project_dir,
                config=SandboxConfig(
                    memory_limit=config.sandbox_memory_limit,
                    cpu_limit=config.sandbox_cpu_limit,
                    image=config.sandbox_image,
                    tag=tag,
                ),
                timeout=self.timeout,
            )
        else:
            verify_claude_cli()

    def _build_args(self, prompt: str) -> list[str]:
        args = ["--print", "--dangerously-skip-permissions", "-p", prompt, "--max-turns", str(self.max_turns)]
        if self.model:
            args.extend(["--model", self.model])
        if self.system_prompt:
            args.extend(["--system-prompt", self.system_prompt])
        args.extend(["--allowedTools", ",".join(self.allowed_tools)])
        return args

    def query(self, prompt: str) -> tuple[str, str]:
        """Send prompt, return (stdout, stderr)."""
        self.project_dir.mkdir(parents=True, exist_ok=True)
        args = self._build_args(prompt)

        if self._sandbox:
            return self._sandbox.run(args, timeout=self.timeout)

        result = subprocess.run(["claude"] + args, cwd=str(self.project_dir),
                               capture_output=True, text=True, timeout=self.timeout)
        return result.stdout, result.stderr
