"""Docker sandbox management for autonomous-claude.

Provides isolated execution environment for Claude Code CLI to prevent
access to sensitive credentials and limit system access.
"""

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from . import __version__

# Docker image configuration
DOCKER_IMAGE = "ghcr.io/ferdousbhai/autonomous-claude"


class DockerNotFoundError(RuntimeError):
    """Docker is not installed."""

    def __init__(self) -> None:
        super().__init__(
            "Docker is not installed.\n\n"
            "Install Docker:\n"
            "  https://docs.docker.com/get-docker/\n\n"
            "Or run without sandbox (not recommended):\n"
            "  autonomous-claude --no-sandbox"
        )


class DockerDaemonError(RuntimeError):
    """Docker daemon is not running or inaccessible."""

    def __init__(self, details: str = "") -> None:
        msg = "Docker daemon is not running or inaccessible.\n\n"
        if "permission denied" in details.lower():
            msg += (
                "Permission denied. Try:\n"
                "  sudo usermod -aG docker $USER\n"
                "  # Then log out and back in\n\n"
            )
        msg += (
            "Start Docker:\n"
            "  sudo systemctl start docker  # Linux\n"
            "  open -a Docker               # macOS\n\n"
            "Or run without sandbox (not recommended):\n"
            "  autonomous-claude --no-sandbox"
        )
        super().__init__(msg)


class ImagePullError(RuntimeError):
    """Failed to pull Docker image."""

    def __init__(self, image: str, details: str = "") -> None:
        super().__init__(
            f"Failed to pull Docker image: {image}\n\n"
            f"Details: {details}\n\n"
            "Make sure you have internet access and the image exists."
        )


@dataclass
class SandboxConfig:
    """Configuration for Docker sandbox."""

    memory_limit: str = "8g"
    cpu_limit: float = 4.0
    network_mode: str = "bridge"  # Allow outbound for npm, pypi, Claude API
    image: str = DOCKER_IMAGE
    tag: str = field(default_factory=lambda: f"v{__version__.split('+')[0]}")


def is_docker_available() -> bool:
    """Check if Docker binary is available."""
    return shutil.which("docker") is not None


def check_docker_daemon() -> tuple[bool, str]:
    """Check if Docker daemon is running.

    Returns:
        Tuple of (success, error_message). error_message is empty on success.
    """
    if not is_docker_available():
        return False, "Docker not installed"

    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return True, ""
        return False, result.stderr
    except subprocess.TimeoutExpired:
        return False, "Docker daemon not responding (timeout)"
    except Exception as e:
        return False, str(e)


def image_exists_locally(image: str, tag: str) -> bool:
    """Check if Docker image exists locally."""
    try:
        result = subprocess.run(
            ["docker", "images", "-q", f"{image}:{tag}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


def pull_image(image: str, tag: str) -> tuple[bool, str]:
    """Pull Docker image from registry.

    Returns:
        Tuple of (success, error_message).
    """
    try:
        result = subprocess.run(
            ["docker", "pull", f"{image}:{tag}"],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes for pull
        )
        if result.returncode == 0:
            return True, ""
        return False, result.stderr
    except subprocess.TimeoutExpired:
        return False, "Image pull timed out"
    except Exception as e:
        return False, str(e)


class DockerSandbox:
    """Manages Docker container lifecycle for sandboxed Claude Code execution."""

    def __init__(
        self,
        project_dir: Path,
        config: Optional[SandboxConfig] = None,
        timeout: int = 18000,
    ) -> None:
        """Initialize Docker sandbox.

        Args:
            project_dir: Project directory to mount read-write
            config: Sandbox configuration (uses defaults if not provided)
            timeout: Default timeout for commands in seconds
        """
        self.project_dir = project_dir.resolve()
        self.config = config or SandboxConfig()
        self.timeout = timeout
        self.claude_dir = Path.home() / ".claude"
        self._verified = False

    def verify_docker(self) -> None:
        """Verify Docker is available and running.

        Raises:
            DockerNotFoundError: If Docker is not installed
            DockerDaemonError: If Docker daemon is not running
        """
        if self._verified:
            return

        if not is_docker_available():
            raise DockerNotFoundError()

        success, error = check_docker_daemon()
        if not success:
            raise DockerDaemonError(error)

        self._verified = True

    def ensure_image(self) -> None:
        """Ensure the sandbox image is available.

        Tries to pull from registry, falls back to local build.
        """
        image = self.config.image
        tag = self.config.tag

        # Check if image exists locally
        if image_exists_locally(image, tag):
            return

        # Try to pull from registry
        success, error = pull_image(image, tag)
        if success:
            return

        # Try latest tag as fallback
        if tag != "latest":
            success, _ = pull_image(image, "latest")
            if success:
                return

        # If pull fails, raise error (local build would need Dockerfile)
        raise ImagePullError(f"{image}:{tag}", error)

    def _build_docker_command(
        self,
        claude_args: list[str],
    ) -> list[str]:
        """Build the docker run command with all mounts and limits.

        Args:
            claude_args: Arguments to pass to claude CLI

        Returns:
            Complete docker command as list of strings
        """
        cmd = [
            "docker",
            "run",
            "--rm",  # Clean up container after exit
        ]

        # Resource limits
        cmd.extend(
            [
                f"--memory={self.config.memory_limit}",
                f"--cpus={self.config.cpu_limit}",
            ]
        )

        # Volume mounts
        # 1. Project directory (read-write)
        cmd.extend(["-v", f"{self.project_dir}:/workspace:rw"])

        # 2. Claude credentials (read-write for token refresh)
        # Claude Code needs to write to ~/.claude/debug, session-env, todos, etc.
        credentials_file = self.claude_dir / ".credentials.json"
        if credentials_file.exists():
            cmd.extend(
                ["-v", f"{credentials_file}:/home/node/.claude/.credentials.json:rw"]
            )

        # 3. Claude settings (read-only) - for user preferences
        settings_file = self.claude_dir / "settings.json"
        if settings_file.exists():
            cmd.extend(["-v", f"{settings_file}:/home/node/.claude/settings.json:ro"])

        settings_local = self.claude_dir / "settings.local.json"
        if settings_local.exists():
            cmd.extend(
                ["-v", f"{settings_local}:/home/node/.claude/settings.local.json:ro"]
            )

        # Working directory
        cmd.extend(["-w", "/workspace"])

        # Environment variables
        cmd.extend(
            [
                "-e",
                "HOME=/home/node",
                "-e",
                "USER=node",
            ]
        )

        # Network (allow outbound for npm, pypi, Claude API)
        cmd.extend(["--network", self.config.network_mode])

        # Security hardening
        cmd.extend(
            [
                "--cap-drop=ALL",  # Drop all Linux capabilities
                "--security-opt=no-new-privileges",  # Prevent privilege escalation
            ]
        )

        # Image and arguments (entrypoint is "claude" in the image)
        cmd.append(f"{self.config.image}:{self.config.tag}")
        cmd.extend(claude_args)

        return cmd

    def run(
        self,
        claude_args: list[str],
        timeout: Optional[int] = None,
    ) -> tuple[str, str]:
        """Execute claude command inside the sandbox.

        Args:
            claude_args: Arguments to pass to claude CLI
            timeout: Command timeout in seconds (uses instance default if None)

        Returns:
            Tuple of (stdout, stderr)

        Raises:
            DockerNotFoundError: If Docker is not installed
            DockerDaemonError: If Docker daemon is not running
            subprocess.TimeoutExpired: If command times out
        """
        self.verify_docker()
        self.ensure_image()

        cmd = self._build_docker_command(claude_args)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout or self.timeout,
        )

        return result.stdout, result.stderr

