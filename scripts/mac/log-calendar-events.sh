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
APPLESCRIPT="$SCRIPT_DIR/log-calendar-events.applescript"

# Check if AppleScript exists
if [[ ! -f "$APPLESCRIPT" ]]; then
    echo "Error: AppleScript not found at $APPLESCRIPT"
    exit 1
fi

# Run the AppleScript
osascript "$APPLESCRIPT"

exit $?
