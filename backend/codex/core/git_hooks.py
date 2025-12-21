"""Git hooks integration for Codex."""

import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Optional


class GitHookManager:
    """Manager for Git hook operations."""

    @staticmethod
    def get_global_hooks_path() -> Optional[Path]:
        """Get the global git hooks path if configured."""
        try:
            result = subprocess.run(
                ["git", "config", "--global", "core.hooksPath"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                return Path(result.stdout.strip()).expanduser()
        except Exception:
            pass
        return None

    @staticmethod
    def set_global_hooks_path(hooks_path: Path) -> bool:
        """Set the global git hooks path."""
        try:
            hooks_path.mkdir(parents=True, exist_ok=True)
            result = subprocess.run(
                ["git", "config", "--global", "core.hooksPath", str(hooks_path)],
                capture_output=True,
                check=False,
            )
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def install_post_commit_hook(
        hooks_path: Path, workspace_path: Optional[Path] = None
    ) -> bool:
        """Install the post-commit hook.

        Args:
            hooks_path: Path to the hooks directory
            workspace_path: Optional workspace path for daily notes

        Returns:
            True if installation successful
        """
        hooks_path.mkdir(parents=True, exist_ok=True)
        post_commit_path = hooks_path / "post-commit"

        # Create the post-commit hook script
        hook_content = GitHookManager._generate_post_commit_script(workspace_path)

        try:
            post_commit_path.write_text(hook_content)
            post_commit_path.chmod(0o755)  # Make executable
            return True
        except Exception:
            return False

    @staticmethod
    def _generate_post_commit_script(workspace_path: Optional[Path] = None) -> str:
        """Generate the post-commit hook script content."""
        workspace_arg = f' --workspace "{workspace_path}"' if workspace_path else ""

        return f'''#!/bin/sh
# Codex post-commit hook
# Automatically log commits to daily notes

# Get commit information
COMMIT_SHA=$(git rev-parse HEAD)
COMMIT_MSG=$(git log -1 --pretty=%B)
BRANCH=$(git rev-parse --abbrev-ref HEAD)
REPO=$(basename "$(git rev-parse --show-toplevel)")

# Call codex to log the commit
codex daily-note add-commit \\
    --sha "$COMMIT_SHA" \\
    --message "$COMMIT_MSG" \\
    --branch "$BRANCH" \\
    --repo "$REPO"{workspace_arg} 2>/dev/null || true

# Exit successfully even if codex command fails
exit 0
'''

    @staticmethod
    def uninstall_post_commit_hook(hooks_path: Path) -> bool:
        """Uninstall the post-commit hook.

        Args:
            hooks_path: Path to the hooks directory

        Returns:
            True if uninstallation successful
        """
        post_commit_path = hooks_path / "post-commit"
        try:
            if post_commit_path.exists():
                post_commit_path.unlink()
            return True
        except Exception:
            return False


class DailyNoteManager:
    """Manager for daily note operations."""

    def __init__(self, workspace_path: Path):
        """Initialize the daily note manager.

        Args:
            workspace_path: Path to the workspace
        """
        self.workspace_path = workspace_path
        self.daily_notes_path = workspace_path / "daily-notes"
        self.daily_notes_path.mkdir(parents=True, exist_ok=True)

    def get_daily_note_path(self, date: Optional[datetime] = None) -> Path:
        """Get the path to the daily note for a given date.

        Args:
            date: Date for the note (defaults to today)

        Returns:
            Path to the daily note file
        """
        if date is None:
            date = datetime.now()
        date_str = date.strftime("%Y-%m-%d")
        return self.daily_notes_path / f"{date_str}.md"

    def add_commit_entry(
        self,
        commit_sha: str,
        commit_message: str,
        branch: str,
        repo: str,
        date: Optional[datetime] = None,
    ) -> Path:
        """Add a commit entry to the daily note.

        Args:
            commit_sha: Commit SHA hash
            commit_message: Commit message
            branch: Git branch name
            repo: Repository name
            date: Date for the note (defaults to today)

        Returns:
            Path to the updated daily note
        """
        note_path = self.get_daily_note_path(date)
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Check if file exists
        if note_path.exists():
            content = note_path.read_text()
        else:
            # Create new daily note with frontmatter
            date_str = (date or datetime.now()).strftime("%Y-%m-%d")
            content = f"""---
title: Daily Note - {date_str}
date: {date_str}
tags:
  - daily-note
  - auto-generated
---

# Daily Note - {date_str}

## Commits

"""

        # Create commit entry
        commit_entry = f"""
::: commit
**Time**: {timestamp}
**Repo**: {repo}
**Branch**: {branch}
**SHA**: `{commit_sha[:8]}`
**Message**: {commit_message}
:::
"""

        # Append to the commits section
        if "## Commits" in content:
            # Add after the commits header
            parts = content.split("## Commits", 1)
            content = parts[0] + "## Commits" + parts[1] + commit_entry
        else:
            # Add commits section if it doesn't exist
            content += "\n## Commits\n" + commit_entry

        # Write the updated content
        note_path.write_text(content)
        return note_path

    def create_daily_note(self, date: Optional[datetime] = None) -> Path:
        """Create a new daily note.

        Args:
            date: Date for the note (defaults to today)

        Returns:
            Path to the created daily note
        """
        note_path = self.get_daily_note_path(date)
        if not note_path.exists():
            date_str = (date or datetime.now()).strftime("%Y-%m-%d")
            content = f"""---
title: Daily Note - {date_str}
date: {date_str}
tags:
  - daily-note
---

# Daily Note - {date_str}

## Notes

Add your notes here.

## Commits

Commits will be automatically logged here by the git post-commit hook.

## Tasks

- [ ] Task 1
- [ ] Task 2

"""
            note_path.write_text(content)
        return note_path

    def list_daily_notes(self, limit: Optional[int] = None) -> List[Path]:
        """List daily notes in reverse chronological order.

        Args:
            limit: Maximum number of notes to return

        Returns:
            List of daily note paths
        """
        notes = sorted(self.daily_notes_path.glob("*.md"), reverse=True)
        if limit:
            notes = notes[:limit]
        return notes

    def add_window_entry(
        self,
        app_name: str,
        window_name: str,
        url: Optional[str] = None,
        date: Optional[datetime] = None,
    ) -> Path:
        """Add an active window entry to the daily note.

        Args:
            app_name: Application name
            window_name: Window title
            url: URL if it's a web browser (optional)
            date: Date for the note (defaults to today)

        Returns:
            Path to the updated daily note
        """
        note_path = self.get_daily_note_path(date)
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Check if file exists
        if note_path.exists():
            content = note_path.read_text()
        else:
            # Create new daily note with frontmatter
            date_str = (date or datetime.now()).strftime("%Y-%m-%d")
            content = f"""---
title: Daily Note - {date_str}
date: {date_str}
tags:
  - daily-note
  - auto-generated
---

# Daily Note - {date_str}

## Active Windows

"""

        # Create window entry
        window_entry = f"""
::: window
**Time**: {timestamp}
**App**: {app_name}
**Window**: {window_name}"""
        
        if url:
            window_entry += f"\n**URL**: {url}"
        
        window_entry += "\n:::\n"

        # Append to the Active Windows section
        if "## Active Windows" in content:
            # Find where to insert: after the section header, preserve existing entries
            # Split on the section header and append to that section
            parts = content.split("## Active Windows", 1)
            # Find the next section marker or end of content
            rest = parts[1]
            next_section = None
            for section_marker in ["\n## ", "\n# "]:
                if section_marker in rest:
                    idx = rest.index(section_marker)
                    next_section = rest[idx:]
                    rest = rest[:idx]
                    break
            
            if next_section:
                content = parts[0] + "## Active Windows" + rest + window_entry + next_section
            else:
                content = parts[0] + "## Active Windows" + rest + window_entry
        else:
            # Add Active Windows section if it doesn't exist
            # Try to add it before Commits section if it exists
            if "## Commits" in content:
                parts = content.split("## Commits", 1)
                content = parts[0] + "\n## Active Windows\n" + window_entry + "\n## Commits" + parts[1]
            else:
                content += "\n## Active Windows\n" + window_entry

        # Write the updated content
        note_path.write_text(content)
        return note_path
