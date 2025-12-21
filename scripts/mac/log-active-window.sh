#!/bin/bash
# Log the currently active window to daily notes
# This script is designed for macOS

# Get the workspace path from environment or use default
WORKSPACE="${CODEX_WORKSPACE:-$HOME/codex}"

# Check if codex is installed
if ! command -v codex &> /dev/null; then
    echo "Error: codex command not found. Please install codex first."
    exit 1
fi

# Check if we're on macOS
if [[ "$(uname)" != "Darwin" ]]; then
    echo "Error: This script only works on macOS"
    exit 1
fi

# Log the active window
codex daily-note add-window --workspace "$WORKSPACE"

exit $?
