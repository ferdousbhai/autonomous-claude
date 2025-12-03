"""Autonomous Claude - Build apps autonomously with Claude Code CLI."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("autonomous-claude")
except PackageNotFoundError:
    __version__ = "0.0.0+dev"
