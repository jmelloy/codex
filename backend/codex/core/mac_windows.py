"""Mac-specific functionality for detecting active windows and applications."""

import subprocess
from typing import Optional, Dict
import json


class MacWindowDetector:
    """Detect active windows and applications on macOS."""

    # Browser application names
    BROWSERS = [
        "Safari",
        "Google Chrome",
        "Chrome",
        "Firefox",
        "Microsoft Edge",
        "Edge",
        "Brave Browser",
        "Opera",
        "Arc",
    ]

    @staticmethod
    def get_active_window_info() -> Optional[Dict[str, str]]:
        """Get information about the currently active window.

        Returns:
            Dictionary with keys:
            - app_name: Name of the application
            - window_name: Title of the window
            - url: URL if it's a web browser (optional)

            Returns None if detection fails.
        """
        try:
            # AppleScript to get active application and window
            script = '''
                tell application "System Events"
                    set frontApp to name of first application process whose frontmost is true
                    set frontAppName to frontApp
                    
                    tell process frontApp
                        try
                            set windowTitle to name of front window
                        on error
                            set windowTitle to ""
                        end try
                    end tell
                end tell
                
                return frontAppName & "|" & windowTitle
            '''

            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )

            if result.returncode != 0:
                return None

            parts = result.stdout.strip().split("|", 1)
            app_name = parts[0] if len(parts) > 0 else ""
            window_name = parts[1] if len(parts) > 1 else ""

            info = {
                "app_name": app_name,
                "window_name": window_name,
            }

            # If it's a browser, try to get the URL
            if MacWindowDetector._is_browser(app_name):
                url = MacWindowDetector._get_browser_url(app_name)
                if url:
                    info["url"] = url

            return info

        except (subprocess.SubprocessError, subprocess.TimeoutExpired):
            return None

    @staticmethod
    def _is_browser(app_name: str) -> bool:
        """Check if the application is a web browser.

        Args:
            app_name: Name of the application

        Returns:
            True if it's a known browser
        """
        return any(
            browser.lower() in app_name.lower() for browser in MacWindowDetector.BROWSERS
        )

    @staticmethod
    def _get_browser_url(app_name: str) -> Optional[str]:
        """Get the current URL from a browser.

        Args:
            app_name: Name of the browser application

        Returns:
            Current URL or None if it can't be retrieved
        """
        # Try different browsers with their specific AppleScript commands
        if "Safari" in app_name:
            return MacWindowDetector._get_safari_url()
        elif "Chrome" in app_name or "Brave" in app_name or "Edge" in app_name:
            return MacWindowDetector._get_chrome_url(app_name)
        elif "Firefox" in app_name:
            return MacWindowDetector._get_firefox_url()
        elif "Arc" in app_name:
            return MacWindowDetector._get_arc_url()
        return None

    @staticmethod
    def _get_safari_url() -> Optional[str]:
        """Get current URL from Safari."""
        script = '''
            tell application "Safari"
                try
                    return URL of front document
                on error
                    return ""
                end try
            end tell
        '''
        return MacWindowDetector._run_applescript(script)

    @staticmethod
    def _get_chrome_url(app_name: str) -> Optional[str]:
        """Get current URL from Chrome-based browsers."""
        script = f'''
            tell application "{app_name}"
                try
                    return URL of active tab of front window
                on error
                    return ""
                end try
            end tell
        '''
        return MacWindowDetector._run_applescript(script)

    @staticmethod
    def _get_firefox_url() -> Optional[str]:
        """Get current URL from Firefox."""
        # Firefox doesn't support AppleScript well, so we can't reliably get the URL
        # Return None to indicate URL is not available
        return None

    @staticmethod
    def _get_arc_url() -> Optional[str]:
        """Get current URL from Arc browser."""
        script = '''
            tell application "Arc"
                try
                    return URL of active tab of front window
                on error
                    return ""
                end try
            end tell
        '''
        return MacWindowDetector._run_applescript(script)

    @staticmethod
    def _run_applescript(script: str) -> Optional[str]:
        """Run an AppleScript and return the result.

        Args:
            script: AppleScript code to execute

        Returns:
            Script output or None if it fails
        """
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            output = result.stdout.strip()
            return output if output else None
        except (subprocess.SubprocessError, subprocess.TimeoutExpired):
            return None

    @staticmethod
    def format_window_entry(window_info: Dict[str, str]) -> str:
        """Format window information for daily note entry.

        Args:
            window_info: Dictionary with app_name, window_name, and optional url

        Returns:
            Formatted string for daily note
        """
        app_name = window_info.get("app_name", "Unknown")
        window_name = window_info.get("window_name", "Unknown")
        url = window_info.get("url")

        entry = f"**App**: {app_name}  \n**Window**: {window_name}"
        if url:
            entry += f"  \n**URL**: {url}"

        return entry
