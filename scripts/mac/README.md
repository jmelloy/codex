# Mac Scripts for Codex

This directory contains macOS-specific scripts for enhancing Codex functionality.

## log-active-window

Scripts that capture information about the currently active application window and log it to your daily note.

### Features

- **Auto-detection**: Automatically detects the currently focused application and window
- **Browser URL capture**: For web browsers (Safari, Chrome, Firefox, Brave, Edge, Arc), also captures the current URL
- **Daily note integration**: Seamlessly integrates with Codex daily notes
- **Timestamp**: Records the exact time when the window was logged

### Available Scripts

#### 1. Shell Script (`log-active-window.sh`)

Uses the Codex CLI to log active windows. Requires Codex to be installed.

**Usage:**
```bash
# Using default workspace ($HOME/codex)
./scripts/mac/log-active-window.sh

# Using custom workspace
CODEX_WORKSPACE=~/my-workspace ./scripts/mac/log-active-window.sh
```

**Setup:**
```bash
# Make executable (already done in repo)
chmod +x scripts/mac/log-active-window.sh

# Optional: Add to PATH or create an alias
alias log-window='~/path/to/codex/scripts/mac/log-active-window.sh'
```

#### 2. AppleScript (`log-active-window.applescript`)

Standalone AppleScript that doesn't require Codex CLI installation. Works independently.

**Usage:**
```bash
# Run directly
./scripts/mac/log-active-window.applescript

# Or with osascript
osascript scripts/mac/log-active-window.applescript
```

**Setup:**
```bash
# Make executable (already done in repo)
chmod +x scripts/mac/log-active-window.applescript

# Edit the script to change workspace location (default: ~/codex)
# Open in Script Editor and modify workspacePath property
```

**Convert to Application:**

You can convert the AppleScript to a standalone app that can be:
- Added to the Dock
- Triggered with keyboard shortcuts
- Run from the menu bar

```bash
# Using Script Editor
# 1. Open scripts/mac/log-active-window.applescript in Script Editor
# 2. File > Export
# 3. File Format: Application
# 4. Save as "Log Active Window.app"

# Or use command line
osacompile -o "Log Active Window.app" scripts/mac/log-active-window.applescript
```

### Codex CLI Command

If you have Codex installed, you can also use the CLI directly:

```bash
# Auto-detect active window (macOS only)
codex daily-note add-window

# Manually specify window information
codex daily-note add-window \
    --app "Visual Studio Code" \
    --window "main.py - myproject"

# With URL for browsers
codex daily-note add-window \
    --app "Safari" \
    --window "GitHub" \
    --url "https://github.com"

# Use custom workspace
codex daily-note add-window --workspace ~/my-workspace
```

### Daily Note Format

Window entries are logged in this format:

```markdown
## Active Windows

::: window
**Time**: 14:30:15
**App**: Safari
**Window**: GitHub - Pull Requests
**URL**: https://github.com/pulls
:::

::: window
**Time**: 14:35:22
**App**: Visual Studio Code
**Window**: main.py - myproject
:::
```

### Automation Ideas

#### Keyboard Shortcut

Use macOS Automator or a tool like [Keyboard Maestro](https://www.keyboardmaestro.com/) to trigger the script with a keyboard shortcut.

**With Automator:**
1. Open Automator
2. Create new "Quick Action"
3. Add "Run Shell Script" action
4. Paste: `~/path/to/codex/scripts/mac/log-active-window.sh`
5. Save as "Log Active Window"
6. Go to System Preferences > Keyboard > Shortcuts > Services
7. Assign a keyboard shortcut to "Log Active Window"

#### Periodic Logging

Use `launchd` to log active windows at regular intervals:

```bash
# Create a launchd plist file
cat > ~/Library/LaunchAgents/com.codex.log-window.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.codex.log-window</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/codex/scripts/mac/log-active-window.sh</string>
    </array>
    <key>StartInterval</key>
    <integer>300</integer>  <!-- Run every 5 minutes -->
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
EOF

# Load the launch agent
launchctl load ~/Library/LaunchAgents/com.codex.log-window.plist

# To unload later
launchctl unload ~/Library/LaunchAgents/com.codex.log-window.plist
```

#### Menu Bar App

Create a menu bar app using tools like:
- [SwiftBar](https://github.com/swiftbar/SwiftBar)
- [BitBar](https://github.com/matryer/bitbar)

Example SwiftBar script:
```bash
#!/bin/bash
# <bitbar.title>Codex Window Logger</bitbar.title>
# <bitbar.version>v1.0</bitbar.version>
# <bitbar.author>Your Name</bitbar.author>
# <bitbar.desc>Log active window to Codex</bitbar.desc>

echo "📝"
echo "---"
echo "Log Active Window | bash=/path/to/codex/scripts/mac/log-active-window.sh terminal=false"
```

### Supported Browsers

The scripts support URL detection for:
- Safari
- Google Chrome / Chromium
- Brave Browser
- Microsoft Edge
- Arc Browser
- Firefox (limited support - no URL detection)

### Troubleshooting

#### Permission Issues

If you get permission errors, you may need to grant accessibility permissions:
1. System Preferences > Security & Privacy > Privacy > Accessibility
2. Add Terminal (or your terminal app) to the list
3. If using the AppleScript app, add it to the list as well

#### Script Not Working

1. **Check if running on macOS:**
   ```bash
   uname  # Should output: Darwin
   ```

2. **Test AppleScript directly:**
   ```bash
   osascript -e 'tell application "System Events" to get name of first process whose frontmost is true'
   ```

3. **Check Codex installation (for shell script):**
   ```bash
   which codex
   codex --version
   ```

4. **Verify workspace exists:**
   ```bash
   ls -la ~/codex/daily-notes
   ```

#### URL Not Captured

If URLs aren't being captured for browsers:
- Ensure the browser is running and has a window open
- Some browsers require accessibility permissions
- Firefox doesn't support URL retrieval via AppleScript

### Related Documentation

- [Git Hooks Integration](../../GIT_HOOKS.md) - Automatic commit logging
- [Daily Notes](../../README.md#daily-notes) - Daily notes documentation
- [Codex CLI](../../backend/codex/cli/main.py) - CLI reference

## Contributing

Contributions to improve the Mac scripts are welcome! Some ideas:
- Support for more browsers
- Integration with time tracking tools
- Context detection (coding, browsing, writing, etc.)
- Smart filtering (exclude certain apps, etc.)

## License

MIT License - see [LICENSE](../../LICENSE) file for details.
