"""
Configuration utility for the Turret server.
Loads secrets/configuration from the project root secrets.json file.
"""
import json
import os
from typing import Any, Dict


def _resolve_secrets_path() -> str:
    """Resolve the path to secrets.json, checking the cwd then a path relative to this module."""
    secrets_path = os.path.join("./secrets.json")

    if not os.path.exists(secrets_path):
        # Try alternative path relative to this module
        secrets_path = os.path.join(os.path.dirname(__file__), "..", "secrets.json")

    if not os.path.exists(secrets_path):
        raise FileNotFoundError(
            f"secrets.json not found at {secrets_path}. "
            "Please ensure secrets.json exists at the project root."
        )

    return secrets_path


def load_config() -> Dict[str, Any]:
    """Load and return the contents of secrets.json."""
    secrets_path = _resolve_secrets_path()
    with open(secrets_path, 'r') as f:
        return json.load(f)


# Cached configuration loaded once at import time
config: Dict[str, Any] = load_config()
