"""API utility functions."""

import os
from pathlib import Path
from typing import Optional

DEFAULT_WORKSPACE_PATH = os.environ.get("CODEX_WORKSPACE_PATH", ".")


def get_workspace_path(workspace_path: Optional[str] = None) -> Path:
    """Get the workspace path, using default if not specified or if '.' is passed."""
    if not workspace_path or workspace_path == ".":
        return Path(DEFAULT_WORKSPACE_PATH)
    return Path(workspace_path)
