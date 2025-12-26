"""Configuration management."""

import sys
from dataclasses import dataclass, field
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

CONFIG_FILE = Path.home() / ".config" / "autonomous-claude" / "config.toml"

AUTONOMOUS_CLAUDE_DIR = ".autonomous-claude"
FEATURES_FILE = f"{AUTONOMOUS_CLAUDE_DIR}/features.json"
SPEC_FILE = f"{AUTONOMOUS_CLAUDE_DIR}/spec.md"
PROGRESS_FILE = f"{AUTONOMOUS_CLAUDE_DIR}/progress.txt"
LOGS_DIR = f"{AUTONOMOUS_CLAUDE_DIR}/logs"

SANDBOX_IMAGE = "ghcr.io/ferdousbhai/autonomous-claude"


@dataclass
class Config:
    timeout: int = 18000
    max_turns: int = 2000
    max_sessions: int = 100
    spec_timeout: int = 1800
    allowed_tools: list[str] = field(
        default_factory=lambda: ["Read", "Write", "Edit", "MultiEdit", "Glob", "Grep", "Bash", "WebSearch", "WebFetch"]
    )
    sandbox_enabled: bool = True
    sandbox_memory_limit: str = "8g"
    sandbox_cpu_limit: float = 4.0
    sandbox_image: str = SANDBOX_IMAGE
    sandbox_tag: str = ""
    pending_display_limit: int = 10
    notification_sound: str = "/usr/share/sounds/freedesktop/stereo/complete.oga"
    notification_dings: int = 5
    notification_interval: float = 0.3

    @classmethod
    def load(cls) -> "Config":
        config = cls()
        if not CONFIG_FILE.exists() or not tomllib:
            return config

        try:
            data = tomllib.loads(CONFIG_FILE.read_text())
        except Exception:
            return config

        # Map config file sections to dataclass fields
        mappings = {
            "session": ["timeout", "max_turns", "max_sessions", "spec_timeout"],
            "tools": {"allowed": "allowed_tools"},
            "sandbox": {"enabled": "sandbox_enabled", "memory_limit": "sandbox_memory_limit",
                       "cpu_limit": "sandbox_cpu_limit", "image": "sandbox_image", "tag": "sandbox_tag"},
            "ui": {"pending_display_limit": "pending_display_limit"},
            "notification": {"sound": "notification_sound", "dings": "notification_dings",
                           "interval": "notification_interval"},
        }

        for section, fields in mappings.items():
            if section not in data:
                continue
            if isinstance(fields, list):
                for f in fields:
                    if f in data[section]:
                        setattr(config, f, data[section][f])
            else:
                for file_key, attr in fields.items():
                    if file_key in data[section]:
                        setattr(config, attr, data[section][file_key])

        return config


_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config.load()
    return _config


def reset_config() -> None:
    global _config
    _config = None
