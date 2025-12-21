# Mac Active Window Logger - Quick Reference

## Overview

The Mac Active Window Logger helps you automatically track which applications and windows you're working in throughout the day. This is especially useful for:
- Time tracking and productivity analysis
- Context switching awareness
- Creating a detailed work log
- Debugging "what was I doing when X happened?"

## Quick Start

### Basic Usage

```bash
# Log current window (auto-detect)
codex daily-note add-window

# Manually specify details
codex daily-note add-window \
    --app "Visual Studio Code" \
    --window "main.py - myproject"
```

### Standalone Scripts

#### Shell Script
```bash
# Run directly
./scripts/mac/log-active-window.sh

# With custom workspace
CODEX_WORKSPACE=~/my-workspace ./scripts/mac/log-active-window.sh
```

#### AppleScript
```bash
# Run with osascript
osascript scripts/mac/log-active-window.applescript

# Or make executable and run
./scripts/mac/log-active-window.applescript
```

## Automation Setup

### 1. Keyboard Shortcut (Recommended)

**Using Automator:**
1. Open Automator
2. File → New → Quick Action
3. Workflow receives: "no input" in "any application"
4. Add action: "Run Shell Script"
5. Shell: `/bin/bash`
6. Pass input: "to stdin"
7. Script:
   ```bash
   export PATH=/usr/local/bin:$PATH
   /path/to/codex/scripts/mac/log-active-window.sh
   ```
8. File → Save as "Log Active Window"
9. System Preferences → Keyboard → Shortcuts → Services
10. Find "Log Active Window" and assign a shortcut (e.g., ⌘⌥L)

**Using Keyboard Maestro:**
- Create new macro
- Trigger: Hot Key (e.g., ⌘⌥L)
- Action: Execute Shell Script
- Script: `/path/to/codex/scripts/mac/log-active-window.sh`

### 2. Periodic Logging

**Every 5 minutes using launchd:**

Create `~/Library/LaunchAgents/com.codex.log-window.plist`:
```xml
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
    <integer>300</integer>
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
```

Load it:
```bash
launchctl load ~/Library/LaunchAgents/com.codex.log-window.plist
```

**Using cron (alternative):**
```bash
# Edit crontab
crontab -e

# Add line to run every 5 minutes
*/5 * * * * /path/to/codex/scripts/mac/log-active-window.sh
```

### 3. Menu Bar App

**Using SwiftBar/BitBar:**

Create `~/Library/Application Support/SwiftBar/codex-logger.5m.sh`:
```bash
#!/bin/bash
# <swiftbar.title>Codex Logger</swiftbar.title>
# <swiftbar.version>v1.0</swiftbar.version>
# <swiftbar.author>Your Name</swiftbar.author>
# <swiftbar.desc>Log active window to Codex</swiftbar.desc>
# <swiftbar.dependencies>codex</swiftbar.dependencies>

echo "📝"
echo "---"
echo "Log Window Now | bash=/path/to/codex/scripts/mac/log-active-window.sh terminal=false refresh=true"
echo "View Today's Note | bash='codex daily-note view' terminal=true"
```

### 4. Application Trigger

**Using Hammerspoon:**

Add to `~/.hammerspoon/init.lua`:
```lua
-- Log window when switching applications
function logActiveWindow()
    os.execute("/path/to/codex/scripts/mac/log-active-window.sh")
end

-- Watch for application events
watcher = hs.application.watcher.new(function(appName, eventType, app)
    if eventType == hs.application.watcher.activated then
        logActiveWindow()
    end
end)
watcher:start()

-- Optional: Add keyboard shortcut
hs.hotkey.bind({"cmd", "alt"}, "L", logActiveWindow)
```

## Output Format

Window entries appear in your daily note like this:

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

## Supported Browsers

URL detection works for:
- ✅ Safari
- ✅ Google Chrome / Chromium
- ✅ Brave Browser
- ✅ Microsoft Edge
- ✅ Arc Browser
- ⚠️ Firefox (app detection only, no URL)

## Troubleshooting

### Permission Denied
```bash
chmod +x scripts/mac/log-active-window.sh
chmod +x scripts/mac/log-active-window.applescript
```

### Accessibility Permissions
1. System Preferences → Security & Privacy → Privacy → Accessibility
2. Add Terminal (or your terminal app)
3. Add the script or app you're using

### Command Not Found
Make sure `codex` is in your PATH:
```bash
which codex
# If not found, install codex or use full path
```

### No URL Captured
- Ensure browser is running with at least one window
- Some browsers need accessibility permissions
- Firefox doesn't support AppleScript URL detection

## Tips

1. **Combine with Git Hooks**: Use both commit logging and window logging for complete work tracking
2. **Filter Noise**: Consider only logging when you trigger it manually to avoid excessive entries
3. **Privacy**: Be aware that URLs and window titles may contain sensitive information
4. **Analysis**: Parse daily notes to analyze time spent in different apps

## Examples

### Morning Workflow
```bash
# Start your day
codex daily-note create

# Work session 1: Coding
codex daily-note add-window  # Auto-captures VS Code

# Work session 2: Research
codex daily-note add-window  # Auto-captures browser with URL

# Review your day
codex daily-note view
```

### Integration with Focus Modes
```bash
# When entering "Deep Work" focus mode
echo "## Deep Work Session Started" >> ~/codex/daily-notes/$(date +%Y-%m-%d).md
codex daily-note add-window

# Periodic checks during focus
watch -n 300 codex daily-note add-window  # Every 5 minutes

# When exiting focus mode
codex daily-note add-window
echo "## Deep Work Session Ended" >> ~/codex/daily-notes/$(date +%Y-%m-%d).md
```

## See Also

- [Mac Scripts README](README.md) - Full documentation
- [Git Hooks Integration](../../GIT_HOOKS.md) - Commit logging
- [Codex Main README](../../README.md) - Overall project documentation
