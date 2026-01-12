"""Configuration management for Google Docs CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Union

# Base paths
APP_DIR = Path.home() / ".claude" / "google-docs-cli"
CREDENTIALS_DIR = APP_DIR / "credentials"
CONFIG_FILE = APP_DIR / "config.json"
TOKEN_FILE = CREDENTIALS_DIR / "token.json"
CLIENT_SECRETS_FILE = CREDENTIALS_DIR / "credentials.json"

# Google API scopes
SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]

# Default configuration
DEFAULT_CONFIG = {
    "output_format": "table",
    "default_limit": 20,
}


def ensure_dirs() -> None:
    """Ensure required directories exist."""
    APP_DIR.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    """Load configuration from file."""
    ensure_dirs()
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> None:
    """Save configuration to file."""
    ensure_dirs()
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_config_value(key: str) -> Optional[Union[str, int]]:
    """Get a specific configuration value."""
    config = load_config()
    return config.get(key)


def set_config_value(key: str, value: Union[str, int]) -> None:
    """Set a specific configuration value."""
    config = load_config()
    config[key] = value
    save_config(config)
