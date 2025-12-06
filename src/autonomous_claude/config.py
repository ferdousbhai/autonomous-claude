"""Configuration management for autonomous-claude."""

import sys
from dataclasses import dataclass, field
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None  # type: ignore


CONFIG_DIR = Path.home() / ".config" / "autonomous-claude"
CONFIG_FILE = CONFIG_DIR / "config.toml"


@dataclass
class Config:
    """Configuration for autonomous-claude."""

    # Session settings
    timeout: int = 18000  # 5 hours per session
    max_turns: int = 2000  # Max turns per Claude session
    max_sessions: int = 100  # Max Claude sessions before stopping
    spec_timeout: int = 600  # Timeout for spec generation (10 minutes)

    # Allowed tools for Claude
    allowed_tools: list[str] = field(
        default_factory=lambda: ["Read", "Write", "Edit", "MultiEdit", "Glob", "Grep", "Bash", "WebSearch", "WebFetch"]
    )

    # UI settings
    pending_display_limit: int = 10  # Max pending features to show

    # Notification settings
    notification_sound: str = "/usr/share/sounds/freedesktop/stereo/complete.oga"
    notification_dings: int = 5  # Number of times to play the sound
    notification_interval: float = 0.3  # Seconds between dings

    @classmethod
    def load(cls) -> "Config":
        """Load config from file, falling back to defaults."""
        config = cls()

        if not CONFIG_FILE.exists():
            return config

        if tomllib is None:
            return config

        try:
            with open(CONFIG_FILE, "rb") as f:
                data = tomllib.load(f)
        except Exception:
            return config

        # Session settings
        if "session" in data:
            session = data["session"]
            if "timeout" in session:
                config.timeout = session["timeout"]
            if "max_turns" in session:
                config.max_turns = session["max_turns"]
            if "max_sessions" in session:
                config.max_sessions = session["max_sessions"]
            if "spec_timeout" in session:
                config.spec_timeout = session["spec_timeout"]

        # Tools settings
        if "tools" in data:
            tools = data["tools"]
            if "allowed" in tools:
                config.allowed_tools = tools["allowed"]

        # UI settings
        if "ui" in data:
            ui = data["ui"]
            if "pending_display_limit" in ui:
                config.pending_display_limit = ui["pending_display_limit"]

        # Notification settings
        if "notification" in data:
            notif = data["notification"]
            if "sound" in notif:
                config.notification_sound = notif["sound"]
            if "dings" in notif:
                config.notification_dings = notif["dings"]
            if "interval" in notif:
                config.notification_interval = notif["interval"]

        return config


# Global config instance
_config: Config | None = None


def get_config() -> Config:
    """Get the global config instance, loading if needed."""
    global _config
    if _config is None:
        _config = Config.load()
    return _config


def reset_config() -> None:
    """Reset config (useful for testing)."""
    global _config
    _config = None
