#!/bin/bash
# Log calendar events from iCloud to daily notes
# This script is designed for macOS

# Get the workspace path from environment or use default
WORKSPACE="${CODEX_WORKSPACE:-$HOME/codex}"

# Check if we're on macOS
if [[ "$(uname)" != "Darwin" ]]; then
    echo "Error: This script only works on macOS"
    exit 1
fi

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Export workspace path for AppleScript
export HOME

# Run the AppleScript
osascript "$SCRIPT_DIR/log-calendar-events.applescript"

exit $?
