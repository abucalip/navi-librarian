"""The running build's version label, shown in the page rail."""
import os
import subprocess
from pathlib import Path


def app_version() -> str:
    """APP_VERSION from the environment (set when an image is built), else the nearest git tag
    with the commits since it, else "dev"."""
    configured = os.environ.get("APP_VERSION", "").strip()
    if configured:
        return configured
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--always"],
            cwd=Path(__file__).resolve().parent.parent,
            capture_output=True, text=True, timeout=3, check=False,
        )
        label = result.stdout.strip()
        if result.returncode == 0 and label:
            return label
    except (OSError, subprocess.SubprocessError):
        pass
    return "dev"
