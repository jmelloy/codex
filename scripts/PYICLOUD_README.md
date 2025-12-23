# iCloud Calendar Integration with PyiCloud

This script provides cross-platform access to iCloud calendar events using the PyiCloud library.

## Overview

Unlike the macOS-specific AppleScript version, this Python script works on **any platform** (macOS, Linux, Windows) where Python is available. It directly accesses iCloud's web services to fetch calendar events.

## Features

- ✅ **Cross-platform**: Works on macOS, Linux, and Windows
- ✅ **No Calendar.app required**: Direct iCloud API access
- ✅ **Secure credential storage**: Uses system keyring for credentials
- ✅ **2FA support**: Handles two-factor authentication
- ✅ **Same output format**: Compatible with existing daily notes

## Installation

```bash
# Install the required library
pip install pyicloud

# Or with the codex calendar extras
pip install -e ".[calendar]"
```

## Usage

### Basic Usage

```bash
python scripts/log-calendar-events-pyicloud.py
```

On first run, you'll be prompted for your Apple ID and password. If you have two-factor authentication enabled, you'll need to enter the verification code.

### With Custom Workspace

```bash
CODEX_WORKSPACE=~/my-workspace python scripts/log-calendar-events-pyicloud.py
```

### Automated Usage (with environment variables)

For automation purposes, you can provide credentials via environment variables:

```bash
ICLOUD_USERNAME=your@email.com \
ICLOUD_PASSWORD=your-password \
python scripts/log-calendar-events-pyicloud.py
```

**Note**: For security, avoid storing passwords in plain text. Use secrets management or credential storage solutions.

## Authentication

### First-Time Setup

1. Run the script: `python scripts/log-calendar-events-pyicloud.py`
2. Enter your Apple ID (email)
3. If prompted for password, enter your iCloud password
4. If you have 2FA enabled:
   - Enter the verification code sent to your trusted device
   - The script will ask to trust the session (recommended for future runs)

### Credentials Storage

The PyiCloud library uses your system's keyring to store credentials securely:

- **macOS**: Keychain
- **Linux**: Secret Service API (GNOME Keyring, KWallet)
- **Windows**: Windows Credential Locker

After the first successful authentication, subsequent runs won't require you to re-enter credentials.

## Two-Factor Authentication (2FA)

If you have 2FA enabled on your Apple ID:

1. Run the script
2. You'll receive a 6-digit code on your trusted Apple devices
3. Enter the code when prompted
4. Choose to trust the session for future runs

## Automation Examples

### Daily Cron Job (Linux/macOS)

```bash
# Run at 8 AM every day
0 8 * * * cd ~/codex && python scripts/log-calendar-events-pyicloud.py
```

### Windows Task Scheduler

Create a scheduled task that runs:
```
python C:\Users\YourName\codex\scripts\log-calendar-events-pyicloud.py
```

### Systemd Timer (Linux)

Create `~/.config/systemd/user/codex-calendar.service`:

```ini
[Unit]
Description=Log Calendar Events to Codex

[Service]
Type=oneshot
WorkingDirectory=%h/codex
ExecStart=/usr/bin/python3 %h/codex/scripts/log-calendar-events-pyicloud.py
Environment="CODEX_WORKSPACE=%h/codex"

[Install]
WantedBy=default.target
```

Create `~/.config/systemd/user/codex-calendar.timer`:

```ini
[Unit]
Description=Daily Calendar Event Logger

[Timer]
OnCalendar=daily
OnCalendar=08:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start:
```bash
systemctl --user enable codex-calendar.timer
systemctl --user start codex-calendar.timer
```

## Troubleshooting

### "pyicloud module not found"

Install the library:
```bash
pip install pyicloud
```

### Authentication Errors

- **Wrong password**: Re-run the script and enter the correct password
- **2FA required**: Make sure to enter the verification code exactly as received
- **Session not trusted**: Accept the trust prompt to avoid repeated 2FA

### Rate Limiting

If you see rate limiting errors from iCloud, reduce the frequency of script runs. Running once per day is typically sufficient.

### No Events Showing

- Check that you have events in your iCloud calendar by logging into iCloud.com
- Verify the script is checking the correct date (today)
- Ensure calendar permissions are granted

## Comparison with AppleScript Version

| Feature | PyiCloud Script | AppleScript |
|---------|----------------|-------------|
| **Platform** | Any (macOS, Linux, Windows) | macOS only |
| **Dependencies** | Python + pyicloud | None (built-in) |
| **Calendar Source** | iCloud web services | Calendar.app |
| **Setup Complexity** | Medium (pip install + auth) | Low (just run) |
| **Automation** | Easy on all platforms | Easy on macOS |
| **2FA Support** | Yes | Via Calendar.app |

## Security Considerations

- Credentials are stored in your system's secure credential store
- Avoid storing passwords in environment variables in production
- Use application-specific passwords if available for your Apple ID
- The script only reads calendar data, it doesn't modify anything

## See Also

- [PyiCloud Documentation](https://github.com/picklepete/pyicloud)
- [Main README](mac/README.md) - All calendar integration options
- [Quick Start Guide](mac/QUICK_START.md) - Quick reference
